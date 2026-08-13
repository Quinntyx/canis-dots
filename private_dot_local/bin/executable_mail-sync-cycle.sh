#!/bin/sh
# Full serialized mail sync cycle:
#   mbsync (IMAP <-> Maildir) -> notmuch index -> reconcile server-only mail
#   (fixes mbsync blind spots from Exchange UID recycling), then a second
#   mbsync + notmuch pass if the reconcile moved anything.
#
# The reconcile step is gated to run at most once every 10 minutes (stamp
# file): it scans every folder's headers on the server (expensive, ~15-30s),
# while blind spots are rare. The frequent triggers (goimapnotify on new
# mail, aerc's 1m poll, the 5m timer) stay fast and never hold the sync lock
# for long, so the archive script's lean sync does not starve.
set -e

mbsync -a
notmuch new

STAMP="${XDG_STATE_HOME:-$HOME/.local/state}/mail-router/reconcile.last"
if [ -n "$MAIL_SYNC_FORCE_RECONCILE" ] || [ ! -f "$STAMP" ] ||
   [ $(( $(date +%s) - $(stat -c %Y "$STAMP" 2>/dev/null || echo 0) )) -ge 600 ]; then
    set +e
    REC=$(/home/zlare/.local/bin/mbsync-reconcile.py 2>&1)
    rc=$?
    set -e
    printf '%s\n' "$REC"
    # only refresh the stamp on success, so a failed run retries next cycle
    if [ $rc -eq 0 ]; then
        touch "$STAMP"
    fi
    case "$REC" in
      *'REUIDED='[1-9]*)
        mbsync -a
        notmuch new
        ;;
    esac
fi