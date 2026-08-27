---
name: gcal-sync
description: "Use after a verified Taskwarrior schedule exists for the current week,
  or when the user asks to sync, push, publish, or update their Google Calendar
  from Taskwarrior."
metadata:
  type: procedure
---

# gcal-sync: publish the managed week to Google Calendar

The bundled script `bin/gcal-sync` (relative to this skill's root) mirrors the
current Monday-through-Sunday week from Taskwarrior into the dedicated
`managed` Google Calendar.

## Ownership boundaries

- Taskwarrior is authoritative; the calendar is a view.
- Each run deletes **every** event inside the current week window from the
  `managed` calendar and recreates all of them from the non-deleted Taskwarrior
  export, including completed tasks, so items finished earlier in the week
  survive later pushes. Completed events carry a check-mark prefix and gray
  color. Edits made on the Google side during the week are intentionally
  discarded on the next run; never "preserve" them by trying to merge.
- Events outside the window are never read, modified, or deleted, so previous
  weeks' schedules remain available as history.
- Never touch any calendar other than `managed`, and never write calendar state
  back into Taskwarrior or omn.

## Procedure

1. Confirm the weekly or daily schedule has just been verified (the daily brief's
   final `task schedule` check, Stage 5 of `schedule-day`, or Stage 6 of
   `plan-assignments`). Do not sync an unverified or stale schedule; rebuild it
   first with the owning skill.
2. Run this skill's bundled script at its skill-root-relative path,
   `bin/gcal-sync`;
   on this machine that resolves to
   `~/.config/pi/profiles/omn-assistant/skills/gcal-sync/bin/gcal-sync`.
3. On exit code 2 (not authorized), tell the user to run `gcal-sync --auth`
   themselves in an interactive terminal so they can complete the browser
   consent; do not attempt to authenticate on their behalf.
4. Report deleted and created event counts per day. Treat any
   `CREATE FAILED`/`DELETE FAILED` line as a required fix-and-rerun, not as
   success.
5. Tasks that carry `scheduled` within the week but lack `starttime`/`endtime`
   are skipped and reported. If such tasks should be timed, return them to
   `schedule-day`; never invent times here so they can be pushed.
6. Skipped-task rows mention nothing about due dates: `due` travels in the event
   description only; it never becomes a calendar deadline popup unless the user
   asks for one.
