#!/usr/bin/env python3
"""aerc archive: move selected message(s) from INBOX to Archive on Exchange.

This makes aerc's archive action consistent with the Outlook web/phone
"Archive" button: it performs a real server-side folder move (INBOX -> Archive)
using XOAUTH2 (via `oama access`), then triggers a fast local sync so the
message is re-downloaded into the local Archive maildir and re-tagged by the
notmuch post-new hook.

Invocation:
  - from aerc:   :pipe -b /home/zlare/.local/bin/aerc-archive.sh
                 (raw message(s) arrive on stdin; single = RFC822, batch = mbox)
  - by hand:     aerc-archive.sh 'id:...@...' [more ids ...] [--dry-run]
                 (Message-IDs on argv instead of stdin)

Options:
  --dry-run      connect + search only; do not move anything
  --no-sync      skip the local sync after a successful move
"""
import sys
import re
import subprocess
import imaplib
import email
import mailbox
import io
import argparse
import os

ACCOUNT = "dal558183@utdallas.edu"
HOST = "outlook.office365.com"
PORT = 993
SOURCE = "INBOX"
DEST = "Archive"
SYNC = "/home/zlare/.local/bin/mail-sync.sh"



def lean_sync():
    """Fast post-move mirror update (INBOX+Archive only), serialized with
    the regular sync via flock. Waits briefly for the lock, but never blocks
    forever: if another sync is running, report and let the next cycle catch
    up (the move already happened server-side)."""
    lock = os.path.expanduser("~/.local/state/mail-router/sync.lock")
    cwd = os.path.expanduser("~/docs/mail")
    cmd = "mbsync utdallas:INBOX utdallas:Archive && notmuch new"
    r = subprocess.run(["flock", "-w", "25", "-E", "2", lock, "sh", "-c", cmd],
                       cwd=cwd)
    if r.returncode == 2:
        print("note: another mail sync holds the lock; the archive move is done",
              "and will reach the local mirror on the next sync cycle",
              file=sys.stderr)
        return False
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, cmd)
    return True
def get_token():
    return subprocess.check_output(
        ["oama", "access", ACCOUNT], text=True, timeout=30).strip()


def xoauth2(tok):
    # imaplib base64-encodes whatever the authobject returns, so return the
    # raw SASL payload here.
    return "user={}\x01auth=Bearer {}\x01\x01".format(ACCOUNT, tok)


def connect():
    # hard socket timeout: a stalled Exchange connection must never leave
    # the script hanging in the aerc pipe.
    m = imaplib.IMAP4_SSL(HOST, PORT, timeout=90)
    tok = get_token()
    m.authenticate("XOAUTH2", lambda _: xoauth2(tok))
    return m


def extract_ids(stdin_bytes, arg_ids):
    ids = list(arg_ids)
    if stdin_bytes and stdin_bytes.strip():
        text = stdin_bytes.decode("utf-8", "replace")
        if text.lstrip().startswith("From "):
            # aerc pipes a marked batch as mbox
            mb = mailbox.mbox(io.StringIO(text))
            for msg in mb:
                mid = msg.get("Message-ID")
                if mid:
                    ids.append(mid)
        else:
            try:
                msg = email.message_from_bytes(stdin_bytes)
                mid = msg.get("Message-ID")
                if mid:
                    ids.append(mid)
            except Exception:
                print("warning: could not parse stdin message", file=sys.stderr)
    seen, out = set(), []
    for i in ids:
        i = i.strip()
        if i and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def norm_id(i):
    i = i.strip()
    if i.startswith("id:"):
        i = i[3:].strip()
    if i.startswith("<") and i.endswith(">"):
        i = i[1:-1]
    return i


def find_server_uids(m, msgid):
    """Locate the Exchange UID(s) of msgid inside INBOX by Message-ID."""
    typ, data = m.uid("search", None, "HEADER", "Message-ID",
                      '"%s"' % norm_id(msgid))
    if typ != "OK":
        raise RuntimeError("search failed: %r" % (data,))
    return [u.decode("ascii") for u in
            (data[0].split() if data and data[0] else [])]


def move_message(m, msgid):
    typ, data = m.select(SOURCE)
    if typ != "OK":
        return False, "select %s failed: %r" % (SOURCE, data)
    uids = find_server_uids(m, msgid)
    if not uids:
        return False, "not found in INBOX (already archived/moved?): %s" % msgid
    ok = True
    msg_txt = ""
    for u in uids:
        typ, d = m.uid("MOVE", u, DEST)
        if typ != "OK":
            ok = False
            msg_txt = "MOVE failed for uid %s: %r" % (u, d)
        else:
            msg_txt = "moved uid %s to %s" % (u, DEST)
    return ok, "%s [%d found]" % (msg_txt, len(uids))
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="Message-IDs to move (alt to stdin)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-sync", action="store_true")
    args = ap.parse_args()

    stdin = sys.stdin.buffer.read() if not sys.stdin.isatty() else b""
    ids = extract_ids(stdin, args.ids)
    if not ids:
        print("no messages to archive (no Message-ID on stdin or argv)")
        return 0

    m = connect()
    try:
        moved = 0
        for msgid in ids:
            if args.dry_run:
                m.select(SOURCE)
                suids = find_server_uids(m, msgid)
                print("%s: [dry-run] server uid(s)=%s" % (msgid, ",".join(suids) if suids else "(none)"))
                continue
            ok, note = move_message(m, msgid)
            print("%s : %s" % (msgid, note))
            if ok:
                moved += 1
    finally:
        try:
            m.logout()
        except Exception:
            pass

    if not args.dry_run and not args.no_sync and moved:
        print("triggering local mail sync ...")
        try:
            synced = lean_sync()
        except subprocess.CalledProcessError as e:
            print("warning: local sync failed: %s" % e, file=sys.stderr)
            return 1
        if not synced:
            return 0  # busy; move done, mirror follows on next cycle


if __name__ == "__main__":
    sys.exit(main())
