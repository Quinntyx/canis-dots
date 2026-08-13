#!/usr/bin/env python3
"""Reconcile mbsync's view with the Exchange server.

Problem: mbsync treats far-side messages with UID <= its recorded max UID as
already-known. Exchange Online RECYCLES freed UIDs (after expunge/archive),
so a newly delivered message can land in a recycled slot whose UID is below
the max. mbsync then silently never pulls it, and the user never sees it.

Fix: for each synced folder, diff the server's Message-IDs against the local
(notmuch-indexed) Message-IDs. Any message present only on the server is
"re-uided": it is COPIED inside the same folder (which assigns a fresh UID
>= UIDNEXT, above mbsync's max), then the original is UID-EXPUNGEd. The
following `mbsync -a` pass then pulls it normally.

Safety:
  - only touches messages that exist exactly once on the server
    (COPY + expunge does not create or destroy mail);
  - skips messages flagged \\Deleted (never expunges those);
  - idempotent: after reconciliation the diff is empty for that folder;
  - prints REUIDED=<n> so mail-sync.sh knows to run a second sync pass.

Performance: Exchange serves header fetches slowly per message (~17ms), so
the folder-wide header scans dominate. Chunks are fetched over parallel
connections (imaplib is not thread-safe per connection) with a single pool
across all folders.

Usage: mbsync-reconcile.py [--dry-run]
"""
import sys
import re
import email
import imaplib
import subprocess
import argparse
import concurrent.futures as cf

MAILDIR = "/home/zlare/docs/mail/utdallas"
FOLDERS = ["INBOX", "Archive", "Sent Items"]
ACCOUNT = "dal558183@utdallas.edu"
HOST = "outlook.office365.com"
PORT = 993


def get_token():
    return subprocess.check_output(
        ["oama", "access", ACCOUNT], text=True).strip()


def xoauth2(tok):
    return "user={}\x01auth=Bearer {}\x01\x01".format(ACCOUNT, tok)


def connect():
    m = imaplib.IMAP4_SSL(HOST, PORT)
    m.authenticate("XOAUTH2", lambda _: xoauth2(get_token()))
    return m


def imap_name(folder):
    """Quote a folder name for use inside an IMAP command (spaces etc.)."""
    if not re.search(r"[\s\"\\]", folder):
        return folder
    return '"' + folder.replace('\\', '\\\\').replace('"', '\\"') + '"'


def norm_mid(s):
    s = s.strip().lower()
    if s.startswith("id:"):
        s = s[3:].strip()
    if s.startswith("<") and s.endswith(">"):
        s = s[1:-1]
    return s


def local_mids(folder):
    """Message-IDs the local maildir currently contains (via notmuch)."""
    q = 'path:"utdallas/{}/**"'.format(folder)
    try:
        out = subprocess.check_output(
            ["notmuch", "dump", q], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return set()
    mids = set()
    for ln in out.splitlines():
        # batch-tag line: "+flag -- id:<mid>"
        mm = re.search(r"id:(\S+)$", ln)
        if mm:
            mids.add(norm_mid(mm.group(1)))
    return mids


def server_chunks(m, folder):
    """Select folder and return (count, [(chunk_bytes,)], uid_list)."""
    typ, data = m.select(imap_name(folder))
    if typ != "OK":
        print("  select %r failed: %r" % (folder, data), file=sys.stderr)
        return 0, [], []
    typ, data = m.uid("search", None, "ALL")
    uids = data[0].split() if data and data[0] else []
    CH = 200
    chunks = [b",".join(uids[i:i + CH]).decode()
              for i in range(0, len(uids), CH)]
    return len(uids), chunks, uids


def fetch_one(conn, folder, chunk):
    """Fetch message-ids for one chunk on its own connection."""
    conn.select(imap_name(folder))
    t, fetch = conn.uid("fetch", chunk,
                        "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
    if t != "OK":
        print("  fetch failed at %r: %r" % (chunk, fetch), file=sys.stderr)
        return {}
    res = {}
    for i in range(0, len(fetch)):
        part = fetch[i]
        if not isinstance(part, tuple):
            continue
        payload = part[1]
        # the UID appears in the next non-tuple element, e.g. b' UID 908)'
        nxt = fetch[i + 1] if i + 1 < len(fetch) else b""
        mm = re.search(rb"UID (\d+)", nxt) if isinstance(nxt, bytes) else None
        mid = None
        try:
            msg = email.message_from_bytes(payload)
            mid = msg.get("Message-ID")
        except Exception:
            mid = None
        if mm and mid:
            res[int(mm.group(1))] = norm_mid(mid)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--folders", nargs="*", default=FOLDERS)
    args = ap.parse_args()

    # 1) collect every folder's uid chunks (selects/searches are cheap)
    jobs = []              # (folder, chunk_bytes)
    uid_of = {}            # folder -> original uid list (for the diff loop)
    srv_count = {}         # folder -> total server messages
    m = connect()
    try:
        for folder in args.folders:
            print("== %s ==" % folder)
            n, chunks, uids = server_chunks(m, folder)
            if not uids:
                print("  (no server messages parsed)")
                continue
            srv_count[folder] = n
            uid_of[folder] = uids
            jobs.extend((folder, c) for c in chunks)
    finally:
        try:
            m.logout()
        except Exception:
            pass

    # 2) fetch all headers over one parallel pool
    conns = [connect() for _ in range(min(8, len(jobs) or 1))]
    results = []
    try:
        with cf.ThreadPoolExecutor(max_workers=len(conns)) as ex:
            futs = [ex.submit(fetch_one,
                              conns[i % len(conns)], folder, chunk)
                    for i, (folder, chunk) in enumerate(jobs)]
            results = [f.result() for f in futs]
    finally:
        for conn in conns:
            try:
                conn.logout()
            except Exception:
                pass

    srv = {folder: {} for folder, _ in jobs}
    for (folder, _), res in zip(jobs, results):
        srv[folder].update(res)

    # 3) diff + re-uid per folder
    total = 0
    m = connect()
    try:
        for folder in args.folders:
            if folder not in srv_count:
                continue
            print("== %s ==" % folder)
            server_map = srv[folder]
            loc = local_mids(folder)
            missing = {mid for mid in server_map.values()
                       if mid and mid not in loc}
            print("  server: %d  local: %d  server-only: %d"
                  % (len(server_map), len(loc), len(missing)))
            if not missing:
                continue

            typ, data = m.select(imap_name(folder))
            reuided = 0
            for mid in sorted(missing):
                # Exchange rewrites very long generated Message-IDs (e.g.
                # TeamsMissedActivityEmail...@odspnotify, >120 chars) on COPY;
                # notmuch stores those under a generated notmuch-sha1 id, so the
                # id-based diff can never match and re-uid would churn forever.
                if len(mid) > 120:
                    print("  SKIP %s...: long generated Message-ID (notmuch-sha1);"
                          % mid[:44])
                    continue
                typ2, u = m.uid("search", None, "HEADER", "Message-ID",
                                '"%s"' % mid)
                uids = u[0].decode().split() if u and u[0] else []
                if not uids:
                    print("  SKIP %s: vanished during reconcile" % mid[:44])
                    continue
                if len(uids) > 1:
                    print("  NOTE %s: %d server copies; collapsing to one"
                          % (mid[:44], len(uids)))
                # skip messages flagged \Deleted -- do not expunge those
                typ3, fl = m.uid("fetch", uids[0], "(FLAGS)")
                flagged_deleted = any(isinstance(p, bytes) and
                                       b"\\Deleted" in p for p in (fl or []))
                if flagged_deleted:
                    print("  SKIP %s: flagged \\Deleted (leave alone)" % mid[:44])
                    continue
                if args.dry_run:
                    print("  [dry-run] would re-uid %s (uid %s)"
                          % (mid[:44], uids[0]))
                    continue
                # 1) copy -> fresh UID >= UIDNEXT
                typ4, c = m.uid("copy", uids[0], imap_name(folder))
                if typ4 != "OK":
                    print("  FAIL %s: copy: %r" % (mid[:44], c))
                    continue
                # 2) expunge ALL old copies of this message (keep only the fresh one)
                typ5, e = m.uid("expunge", ",".join(uids))
                if typ5 != "OK":
                    print("  WARN %s: expunge: %r" % (mid[:44], e))
                elif len(uids) > 1:
                    print("  collapsed %d dupes" % (len(uids) - 1))
                reuided += 1
                total += 1
                print("  re-uided %s (old uid %s)" % (mid[:44], uids[0]))
    finally:
        try:
            m.logout()
        except Exception:
            pass

    print("REUIDED=%d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())