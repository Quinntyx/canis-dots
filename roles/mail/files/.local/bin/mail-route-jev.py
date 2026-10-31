#!/usr/bin/env python3
"""Jev-based mail router (successor to `ppi use mail -- @mail_rules.md`).

Reads a raw RFC-822 message on stdin (or --replay FILE), sends it as `state`
plus typed questions to the TypeSafe Jev API, applies the routing decision in
code, and fires a desktop notification via notify-send when the message needs
attention.

Decision contract (ported from mail_rules.md, "when in doubt -> notify"):
  * action signals (needs_attention / sender_important / claims_urgency) use a
    LOW threshold, so uncertain signal still notifies;
  * suppressors (mailing list / automated) must be HIGHLY confident to drop a
    message, and explicit urgency or personal importance overrides them.

Exit codes (contract with docs/mail/.notmuch/hooks/post-new):
  0 - routed: a decision was made (notify OR ignore)
  1 - failure: API/network/parse/key error -> hook tags the message +failed
"""

import argparse
import email
import html.parser
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from email import policy
from email.utils import parseaddr

# --------------------------------------------------------------------------
# Configuration (single block - tune routing behaviour here)
# --------------------------------------------------------------------------

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
KEY_FILE = os.path.expanduser("~/.config/mail-router/jev.env")

NOTIFY_T = 0.5        # action signal >= this -> notify (bias toward notify)
SUPPRESS_T = 0.75     # list/automated must be >= this confident to suppress
URGENCY_CONF_T = 0.8  # urgency choice confidence below this -> "normal"
BODY_CAP = 24000      # max body characters sent as state (end-truncated)
HTTP_TIMEOUT = 15     # seconds per API attempt
RETRIES = 3           # attempts on 429/529/network errors (exp. backoff)
HEADER_CAP = 100      # max notification header length
SUMMARY_CAP = 240     # max notification summary length

# All questions are asked in ONE request against the same state.
QUESTIONS = {
    "is_mailing_list": {
        "type": "noul",
        "instructions": (
            "This message is a mailing-list or discussion-group posting: it has "
            "List-Id/List-Post/List-Unsubscribe headers, comes from a list's "
            "posting address, or is a broadcast sent to a list audience - not a "
            "personal message addressed to the user."
        ),
        "criteria": {
            "true": "It is list/broadcast mail rather than a personal message",
            "false": "It is a personal message addressed to the user",
        },
    },
    "is_automated": {
        "type": "noul",
        "instructions": (
            "This message is automated: a newsletter, marketing promotion, "
            "CI/build bot, digest, or sent by a no-reply address - it was not "
            "written by a person specifically to the user."
        ),
        "criteria": {
            "true": "Machine-generated or broadcast marketing/notification mail",
            "false": "Written by a person to the user",
        },
    },
    "needs_attention": {
        "type": "noul",
        "instructions": (
            "The user must act on this message: it asks the user a question, "
            "makes a request, requires a reply or decision, states a deadline, "
            "or something (account, server, security, coursework) will fail if "
            "it is ignored."
        ),
        "criteria": {
            "true": "Requires action, a reply, or will cause harm if ignored",
            "false": "Purely informational; nothing happens if ignored",
        },
    },
    "sender_important": {
        "type": "noul",
        "instructions": (
            "The sender is a high-priority person in the user's life: a "
            "professor, academic advisor, supervisor, or family member."
        ),
        "criteria": {
            "true": "Professor, advisor, supervisor, family, or similar",
            "false": "An ordinary or unknown correspondent",
        },
    },
    "claims_urgency": {
        "type": "noul",
        "instructions": (
            "The message explicitly claims urgency with words like urgent, "
            "ASAP, deadline, today, immediately, action required, or important."
        ),
        "criteria": {
            "true": "Explicit urgency/time-pressure language is present",
            "false": "No explicit urgency claimed",
        },
    },
    "urgency": {
        "type": "choice",
        "instructions": (
            "If this message needs a desktop notification, how urgent is it?"
        ),
        "criteria": {
            "critical": (
                "Time-sensitive: deadline today, service down, security issue, "
                "or immediate action required"
            ),
            "normal": "Requires attention and a reply, but not immediately",
            "low": (
                "Informational with no time pressure, from someone the user "
                "cares about"
            ),
        },
    },
}

# --------------------------------------------------------------------------
# State building (MIME parsing)
# --------------------------------------------------------------------------


class _HTMLText(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.chunks.append(data)


def _html_to_text(raw):
    p = _HTMLText()
    try:
        p.feed(raw)
    except Exception:
        return raw
    return " ".join(p.chunks)


def extract_body(msg):
    """Concatenate text parts (prefer text/plain), skipping attachments."""
    plain, rich = [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = part.get_content_disposition()
        if disp == "attachment":
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        try:
            text = part.get_content()
        except Exception:
            raw = part.get_payload(decode=True) or b""
            text = raw.decode(part.get_content_charset() or "utf-8", "replace")
        if not isinstance(text, str):
            continue
        (plain if ctype == "text/plain" else rich).append(text)
    body = "\n".join(plain) if plain else ("\n".join(rich) and _html_to_text("\n".join(rich)))
    return body or ""


def build_state(raw: bytes):
    msg = email.message_from_bytes(raw, policy=policy.default)

    def hdr(name):
        v = msg.get(name)
        return str(v) if v is not None else ""

    headers = {
        k: v
        for k, v in (
            ("from", hdr("From")),
            ("to", hdr("To")),
            ("cc", hdr("Cc")),
            ("subject", hdr("Subject")),
            ("date", hdr("Date")),
            ("list-id", hdr("List-Id")),
            ("list-post", hdr("List-Post")),
            ("list-unsubscribe", hdr("List-Unsubscribe")),
            ("reply-to", hdr("Reply-To")),
            ("return-path", hdr("Return-Path")),
            ("precedence", hdr("Precedence")),
            ("message-id", hdr("Message-ID")),
        )
        if v
    }
    body = extract_body(msg)
    truncated = len(body) > BODY_CAP
    if truncated:
        body = body[:BODY_CAP] + "\n...[truncated]"
    state = {"headers": headers, "body": body}
    return msg, state, truncated


# --------------------------------------------------------------------------
# Notification templates (no LLM: header/summary composed from message fields)
# --------------------------------------------------------------------------


DEADLINE_RE = re.compile(
    r"(?i)\b(deadline|due|expire[sd]?|asap|eod|cob|today|tomorrow|tonight|"
    r"noon|midnight|immediately|by\s+\d|end of (day|week)|"
    r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?|"
    r"(mon|tues|wednes|thurs|fri|satur|sun)day|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
)


def clean_subject(subject: str) -> str:
    s = re.sub(r"(?i)\s*((re|fwd?|aw)\s*:\s*)+", "", subject).strip()
    return s or "(no subject)"


def sender_name(msg) -> str:
    _, addr = parseaddr(str(msg.get("From", "")))
    name = str(msg.get("From", "")).split("<")[0].strip().strip('"').strip("'")
    if name:
        return name
    return addr or "(unknown sender)"


def _sentences(text: str):
    for chunk in re.split(r"(?<=[.!?])\s+", text):
        s = " ".join(chunk.split())
        if s:
            yield s


SALUTATION_RE = re.compile(r"(?i)^(hi|hello|hey|dear|greetings|good\s+(morning|afternoon|evening)|to whom)\b[\w\s,.@'-]{0,40}[,:]?$")


def substantive_lines(body: str):
    """Body lines excluding quotes, reply headers, and signatures."""
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s in ("--", "-- "):
            break
        if s.startswith((">", "|", "On ")) or "wrote:" in s:
            continue
        if s.startswith(("-- ", "== ", "~~ ")):
            break
        if SALUTATION_RE.match(s):
            continue
        yield s


def build_summary(body: str) -> str:
    """Richer templates, in priority order:
    1. first direct question, 2. first deadline/date sentence,
    3. first substantive body line."""
    lines = list(substantive_lines(body))
    text = " ".join(lines)
    sentences = list(_sentences(text))
    chosen = next((s for s in sentences if s.endswith("?") and len(s) > 15), None)
    if chosen is None:
        chosen = next((s for s in sentences if DEADLINE_RE.search(s)), None)
    if chosen is None:
        chosen = lines[0] if lines else "(no text body)"
    if len(chosen) > SUMMARY_CAP:
        chosen = chosen[: SUMMARY_CAP - 1].rstrip() + "…"
    return chosen


def build_header(msg) -> str:
    name = sender_name(msg)
    subject = clean_subject(str(msg.get("Subject", "")))
    header = f"{name}: {subject}"
    return header[:HEADER_CAP]


# --------------------------------------------------------------------------
# API call + decision
# --------------------------------------------------------------------------


def load_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(KEY_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("TYPESAFE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def call_jev(key: str, state, questions):
    payload = json.dumps(
        {"state": state, "model": MODEL, "questions": questions}
    ).encode()
    req = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    last_err = "unknown error"
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code in (429, 529):
                last_err = f"HTTP {e.code}: {body}"
            else:
                raise RuntimeError(f"HTTP {e.code}: {body}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"network: {e}"
        if attempt < RETRIES - 1:
            time.sleep(2**attempt)
    raise RuntimeError(f"retries exhausted ({RETRIES} attempts): {last_err}")


def decide(answers):
    """Returns (decision, reason, urgency). Thresholds at top of file."""
    def noul(k):
        return float(answers.get(k, {}).get("noul", 0.0))

    im, ia = noul("is_mailing_list"), noul("is_automated")
    na, si, cu = noul("needs_attention"), noul("sender_important"), noul("claims_urgency")

    choice = answers.get("urgency", {})
    urgency = choice.get("choice", "normal")
    conf = float(choice.get("confidence", 0.0))
    if urgency not in ("critical", "normal", "low") or conf < URGENCY_CONF_T:
        urgency = "normal"

    if im >= SUPPRESS_T and si < NOTIFY_T and cu < NOTIFY_T:
        return "ignore", "mailing-list", urgency
    if ia >= SUPPRESS_T and cu < NOTIFY_T and na < NOTIFY_T:
        return "ignore", "automated", urgency
    if max(na, si, cu) < NOTIFY_T:
        return "ignore", "no-action", urgency
    return "notify", "action-needed", urgency


def notify_send(urgency: str, header: str, summary: str) -> None:
    args = ["notify-send", "-a", "aerc-mail", "-u", urgency,
            "-h", "int:transient:1", "--", header, summary]
    subprocess.run(args, timeout=10, check=True)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Route one email through Jev")
    ap.add_argument("msgid", nargs="?", default="-", help="notmuch message id (for logging)")
    ap.add_argument("--replay", metavar="FILE", help="read raw message from FILE instead of stdin")
    ap.add_argument("--dry-run", action="store_true",
                    help="evaluate and log, but do not send a notification")
    ap.add_argument("--dump-state", action="store_true",
                    help="parse only: print state stats, no API call (no credits)")
    args = ap.parse_args()

    if args.replay:
        with open(args.replay, "rb") as f:
            raw = f.read()
    else:
        raw = sys.stdin.buffer.read()
    try:
        msg, state, truncated = build_state(raw)
    except Exception as e:
        print(f"ERROR parse failed: {e}", file=sys.stderr)
        return 1

    if args.dump_state:
        hdrs = state["headers"]
        print(f"state ok: headers={sorted(hdrs)} body_chars={len(state['body'])} "
              f"truncated={truncated} subject_len={len(hdrs.get('subject',''))}")
        return 0

    key = load_key()
    if not key:
        print(f"ERROR no API key (env TYPESAFE_API_KEY or {KEY_FILE})", file=sys.stderr)
        return 1

    t0 = time.monotonic()
    try:
        resp = call_jev(key, state, QUESTIONS)
    except RuntimeError as e:
        print(f"ERROR jev api: {e}", file=sys.stderr)
        return 1
    latency_ms = int((time.monotonic() - t0) * 1000)

    answers = resp.get("answers", {})
    decision, reason, urgency = decide(answers)
    header = build_header(msg)
    summary = build_summary(state["body"])
    usage = resp.get("usage", {})

    sent = False
    if decision == "notify" and not args.dry_run:
        try:
            notify_send(urgency, header, summary)
            sent = True
        except Exception as e:
            print(f"ERROR notify-send failed: {e}", file=sys.stderr)
            return 1

    noul = {k: round(float(answers.get(k, {}).get("noul", 0.0)), 3)
            for k in ("is_mailing_list", "is_automated", "needs_attention",
                      "sender_important", "claims_urgency")}
    j = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "msgid": args.msgid, "decision": decision, "reason": reason,
        "urgency": urgency, "sent": sent or args.dry_run and decision == "notify",
        "noul": noul,
        "urgency_choice": answers.get("urgency", {}).get("choice"),
        "urgency_conf": answers.get("urgency", {}).get("confidence"),
        "latency_ms": latency_ms, "input_tokens": usage.get("input_tokens"),
        "truncated": truncated, "header": header, "summary": summary,
        "model": resp.get("model"),
    }
    if args.dry_run:
        j["dry_run"] = True
    print(f"[{j['ts']}] {args.msgid} {decision}/{urgency} ({reason}) "
          f"latency={latency_ms}ms tokens={usage.get('input_tokens')} "
          f"truncated={truncated} header={header!r} summary={summary!r}")
    print("route_json=" + json.dumps(j, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
