#!/bin/sh
# Serialized mail sync: see mail-sync-cycle.sh for the actual steps.
# Used by goimapnotify (onNewMail), aerc (check-mail-cmd) and the systemd
# flock serializes concurrent invocations (mbsync has no built-in locking),
# so the last writer always wins cleanly. If the lock is held by a stuck
# sync, wait at most 5 minutes then give up so callers (aerc's check-mail,
# goimapnotify, the timer) never queue forever behind a hung cycle.
exec flock -w 300 ~/.local/state/mail-router/sync.lock /bin/sh /home/zlare/.local/bin/mail-sync-cycle.sh