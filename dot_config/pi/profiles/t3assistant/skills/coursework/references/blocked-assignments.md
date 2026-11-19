# Blocked assignments and release-window continuation

Read when an assignment cannot yet be prepared or handed off. A known release window is a pause
in the existing assignment, not a completed preparation or a request for the user to return later.
This procedure authorizes only that assignment's continuation in its existing T3 Code thread.

## Choose the next action

1. Verify the blocker against the assignment source and a fresh America/Chicago date. Record the
   assignment IDs/URL, observed availability, unlock time with timezone, due/lock bounds, last
   verification, prepared artifacts, and remaining work using the supported progress interface.
2. For a future unlock time, finish any preparation possible now, then schedule the continuation
   below. Use the opening time, not the due date, review date, daily preparation cap or 22:00 stop.
   If the opening has already passed, re-check access now. Resolve conflicting/missing times from
   the source rather than inventing a wake-up time.
3. For authentication, consent, missing permissions or another human-action blocker, preserve the
   appropriate handoff and name the needed action. A timer cannot complete sign-in or supply
   missing information. If no justified retry time is available, report that boundary explicitly.

## Schedule and await the release

1. Discover T3 Code's `schedule_task`, `list_scheduled_tasks`, and `t3_background_wait` tools and
   inspect their current schemas. Use supported tools, not database edits, shell sleeps, polling
   loops, systemd/cron jobs or a new thread. If scheduling or awaiting is unavailable or fails,
   report which step failed; claim Working/Waiting only after awaiting succeeds.
2. On the initial blocked turn, inspect existing automations for this assignment and thread.
   Reuse/update the matching automation with `scheduledTaskId`, or create one if none exists.
   Keep one pending release wake-up per assignment. On an automation-triggered run, use the
   supplied task identity and continuation prompt directly rather than listing tasks to find it.
3. Call `schedule_task` with `schedule: {type: "once", runAt: "<opening instant>"}`,
   `bindToCurrentThread: true`, `freshSession: false`, and `enabled: true`. Encode `runAt` as
   an absolute ISO 8601 timestamp with the verified UTC offset (or convert it to UTC), accounting
   for America/Chicago daylight saving time on the release date. For example, a source-verified
   November 19, 2026 opening at 15:00 CST is `2026-11-19T15:00:00-06:00`.
4. Give the automation a self-contained prompt: assignment/course identity and canonical URL,
   verified opening and due/lock times, blocker, private artifact paths, and the exact unfinished
   preparation/handoff. Instruct it to re-check live availability and resume the existing request
   under the `coursework` skill, retaining the human-only assessment/submission boundary.
5. Save the returned automation ID and confirmed next run time with the assignment's blocked
   progress and next action. Report that time with its timezone and the blocker. Then call
   `t3_background_wait` with `taskIds: ["<returned automation ID>"]` and `waiting: true`, and end
   the turn. Await the automation's ID, not an assignment/thread ID. The bound automation keeps
   the thread under **Working** with **Waiting** status while the turn is idle.

## Resume and finish

1. On waking, read current assignment/progress facts and re-check actual access before resuming
   preparation. A scheduled time passing is not evidence that the assignment opened. Preserve
   existing artifacts, concurrent user changes, browser context and original task scope.
2. If the assignment is still time-blocked, verify its current release information and re-arm
   the same automation for the next source-supported time, or a bounded retry before the due/lock
   window closes. Record the new check time and await it again. If no useful retry remains or
   human action is now required, report that blocker instead of scheduling an indefinite loop.
3. Once access is verified, finish the authorized preparation/handoff. If its automation is still
   enabled, disable it with `schedule_task` using its `scheduledTaskId` and `enabled: false`.
   Release any remaining wait with `t3_background_wait`, the same `taskIds`, and `waiting: false`.
   Apply the same cleanup when the continuation is cancelled or no longer needed. Save progress
   and leave the thread unsettled for the user; learning follow-up remains separately authorized.
