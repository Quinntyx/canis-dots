#!/bin/sh
# Serialized mail sync: see mail-sync-cycle.sh for the actual steps.
# Used by goimapnotify (onNewMail), aerc (check-mail-cmd) and the systemd
# fallback timer. flock serializes concurrent invocations (mbsync has no
# built-in locking), so the last writer always wins cleanly.
exec flock ~/.local/state/mail-router/sync.lock /bin/sh /home/zlare/.local/bin/mail-sync-cycle.sh