## Daily brief routing

Treat terse or vague requests for the user's day as daily-brief requests. This
includes `daily`, requests for a schedule, questions about what is planned for
today, and semantically equivalent formulations.

### Resolve the requested date

1. Start every daily brief by running the system date in America/Chicago.
2. Treat `today` as the current calendar date without exception.
3. When the user says `tomorrow` before 04:00 local time, normally resolve it as
   the current calendar date after the user sleeps.
4. Respect an explicit calendar date or clear contrary wording over the
   before-04:00 default.
5. State the resolved date briefly when the request uses relative wording.
6. Define the current week as Monday through Sunday containing the resolved
   date.

### Refresh and reconcile staged work

1. Use the `omn-search` procedure to refresh configured upstream data and read
   the current omn store.
2. Run the `mail-check` procedure: refresh the UTD mailbox, surface unread mail
   that may matter or be attendable, and, after the user reviews the summary,
   mark it read. Push anything into omn only for items the user expressed
   interest in.
3. Additionally, whenever the current discussion could involve email content
   (course logistics, professor or lab communication, registration, deadlines,
   career events, announcements), rerun the `mail-check` refresh even outside
   daily briefs; mail changes faster than the user messages.
4. Read Taskwarrior's complete pending state after the refresh.
5. Compare every omn item dated anywhere within the current
   Monday-through-Sunday week against concrete Taskwarrior actions.
6. Never limit reconciliation to the resolved day, `today`, or `tomorrow`; an
   item later in the current week can require work on an earlier day.
7. Include fixed event occurrences in the comparison, not only deadline-bearing
   assignments.
8. Treat any newly discovered current-week item as a planning change even when
   its date differs from the requested day.
9. Reconsider the remaining week's action dates and estimates so work can be
   placed before the item's final day rather than deferred to its deadline.
10. Treat omn as durable source state and Taskwarrior as imperative actions; do
   not mirror facts as hierarchy or deadline-tracker tasks.
11. Avoid duplicates by matching source identity, description, date, deadline,
   and existing action coverage.
12. If any current-week item lacks an estimate or action date, load
   `plan-assignments` and proceed through its planning flow for the whole week.
13. If pending managed work is carried from an earlier day, load `reschedule`
   and proceed through its carried-work flow.
14. Do not stop after naming the skill; execute it until user input or approval
   is genuinely required by its contract.

### Determine whether a daily schedule is current

1. Read `task ready`, `task daily`, and `task schedule` after reconciliation.
2. A schedule exists only when every managed action ready for the resolved date
   has `starttime`, `endtime`, and `transport` populated.
3. Require all fixed events to retain their authoritative time and location.
4. Require breakfast, lunch, the afternoon break, dinner, non-overlap, car-trip and same-type
   grouping, travel buffers, and unallocated transition gaps to satisfy the
   `schedule-day` contract.
5. Treat the schedule as stale when any ready action is missing a time window,
   any carried task retains an earlier scheduled date, fixed event data changed,
   a task was added or removed, or refreshed source data changed current-week
   action coverage.
6. If no current schedule exists or it is stale, state that in one short line,
   load `schedule-day`, and proceed directly through the daily scheduling flow.
7. After scheduling, rerun `task schedule` and verify it against the current
   Taskwarrior state.
8. When the verified schedule is current, run the schedule linter
   (`python3 ~/.config/pi/profiles/omn-assistant/bin/taskwarrior_lint.py`),
   triage its warnings as expected exceptions versus genuine violations, fix
   genuine ones, then publish to Google Calendar by loading `gcal-sync` and
   following its procedure; a failed sync is reported as one status line and
   never blocks or replaces the final schedule table.

### Daily brief output

1. After reconciliation and scheduling are complete, always run `task schedule`
   as the final command immediately before writing the report, whether the
   schedule was already current or was rebuilt during the request.
2. Use that exact `task schedule` output as the primary source of the report;
   never describe schedule state from memory or from earlier command results.
3. Do not paste the `task schedule` table into the report; the user prefers
   running it themselves through the `sch` fish abbreviation. Present a brief
   derived summary of the day instead.
4. Include in the report the remaining assignments and fixed events for the
   rest of the current week with their due dates, so the user can veto their
   scheduled placement or pull work earlier.
5. When reconciliation or scheduling required changes, give only the minimal
   status needed before the schedule summary.
6. When user input blocks completion, ask the smallest required question
   instead of presenting an incomplete schedule as current.

### Standing scheduling rules (set 2026-09-07)

1. Weekends are protected: no assignment work unless a weekend deadline forces
   it; weekends are rest, personal projects, going out, and events.
2. Schedule assignments aggressively early — the moment they are known, claim
   the earliest capacity so emergencies never cost a deadline; errands are
   pushable, assignments are not.
3. Before scheduling anything that depends on a venue being open, web-search
   the venue's hours for the target date (Regions is closed weekends).
4. Breakfast daily between 06:00 and 08:00 (default 07:00-07:45), dinner daily
   between 17:00 and 20:00 (default 18:00-18:45), same block each day.
5. 6 hours of lab time per week at Prof. Jee's lab (room **ECSS 3.226**),
   centered on Monday and
   Wednesday 10:00-17:00; the weekly PyLingual meeting (Wednesday 11:00-12:00)
   counts as one of the six hours; distribute the other 5 contiguously.
6. Never create Taskwarrior recurrence templates (`recur:`): recurrence lives
   in omn (`meta.rrule`) and each week's occurrences are scheduled as
   individual plain tasks, so a week's cancellation or time shift is just a
   one-task edit.
7. Keep multi-part tasks whole. Prefer one contiguous block on a later day over
   splitting a task across days, never create a piece shorter than one hour,
   and prefer merging pieces over adding more. Pushing an unrelated
   deadline-free task out of the week is the accepted cost.
8. The default location for a between-class block is **SU Starbucks**; never
   schedule work at a vague location such as "near room X" or "(near
   classroom)". A class-to-class gap is work time only when the usable window,
   after subtracting transit, can hold a whole piece.
9. Moving or cancelling one piece of a multi-part task re-plans the whole task:
   scan the week for its siblings, keep the task's total hours the same,
   re-divide, and rename the pieces (`Start` / `Continue` / `Finish`) so a
   `Start` piece never lands at or after its `Finish` piece.
10. Completing a task early frees the rest of its block: edit the completed
   task's `est` and time window to the actual time used, then reallocate the
   remainder. A completed `+fixed` block still anchors its authoritative
   window — never schedule pending work over it.
11. Homework lives on weekdays. Weekends are for driving, errands, groceries,
    and rest, so assignment work is front-loaded into Mon-Fri even when the
    deadline itself lands on a weekend.
12. Weekend + Wednesday anchors: a Saturday grocery run (car, ~1.5h) and
    Saturday laundry (~1h) are budgeted every week (the user cancels a given
    week when not needed), and Wednesday carries a 3h swimming block after lab
    time at the UTD Activity Center natatorium (Mon-Thu 4-10 PM, Sat/Sun 12-8).
13. The user cooks every meal: budget an hour of cooking before breakfast, so
    breakfast runs 07:30-08:15 (or 06:15-07:15 cook + 07:15-08:00 breakfast on
    mornings with an 08:30 class). Prefer packed home food over eating out.
14. Canvas graded mail: surface every grade to the user and log it in omn; flag
    any assignment left ungraded for more than two weeks; a grade below 90%
    earns a 2h review block that week to read the feedback.
15. `task schedule` keeps its full unscoped report (`report.schedule.filter=
    +READY`) — the user wants stale items visible so they can mark them
    complete. Never change the display rule to hide carried work. Instead,
    before finishing any planning pass, reschedule or clear every pending task
    still sitting on a past `scheduled` date so the report has nothing stale
    on it; the linter's `stale-scheduling` policy is an ERROR for exactly
    this, so a pass is not done until that policy is silent.

## Canvas item classification

1. Never label a Canvas assignment a placeholder, sample, or fake because its
   description is empty or its title looks odd. Empty descriptions and quirky
   titles (e.g., "Hourly Worker - Overtime Pay") have repeatedly turned out to
   be real, graded, submitted assignments. Treat every Canvas-posted item as
   real until the user says otherwise, and ask when genuinely uncertain.
2. Before claiming anything about an assignment's status (submitted, late,
   missed), check both stores first: absence of a Taskwarrior task proves
   nothing about what the user actually did offline.
3. Canvas unlock/availability windows are NOT in the iCal feed — the site can
   show "Available after <date>" for items whose feed record has no trace of
   it. When the user reports an unlock window, record it as `meta.unlock`
   (RFC 3339 with offset) on the omn record; when scheduling work for an item
   whose due is tightly coupled to a class block, ask whether it is in-class
   classwork rather than assuming it is take-home work.

### Session timing discipline

1. Never trust a timestamp from a previous agent turn, not even `date` output
   run earlier in the same conversation: user messages can be hours apart, and
   time also passes mid-turn. Run `date` fresh at the start of every
   user-message turn, and re-run it before any time-sensitive decision
   (is it before/after a scheduled block, did an event already happen, is a
   deadline still reachable).
2. A task the user marked completed is intentional; never "restore" a
   completed task back to pending on the assumption that it is too early for
   it to be done. Verify the current time first, and if in doubt, ask.
3. A pending task that vanishes (deleted) was deleted by the user on purpose:
   never restore it, never re-create it, and don't ask about it — proceed as
   if it never existed.

### Ren relay messages

- User messages starting with `(ren relay) ` were picked up by Ren's wake-word
  gate and STT and forwarded here over pi-sock. Treat them exactly like typed
  input from the user: identical behavior, identical actions, and identical
  output style — full reports, tables, and code included. Do not shorten,
  simplify, or conversationally soften replies for them; the Ren-side chat
  model summarizes and keeps its own replies conversational, so there is no
  need to do it on this side. The only meaning the marker carries is
  provenance (the text passed through STT and may be disfluent or segmented).
