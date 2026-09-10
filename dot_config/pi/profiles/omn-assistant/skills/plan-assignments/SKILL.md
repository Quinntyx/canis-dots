---
name: plan-assignments
description: "Use when the user asks to plan, schedule, or set up next week's
  assignments, or to turn assignments from omn into concrete Taskwarrior tasks
  with deadlines, scheduled dates, and estimates."
metadata:
  type: procedure
---

# Contract

## Input Contract
- A request to plan the next week's work from the omn store.
- A populated store with assignment `task` records carrying `meta.due`, class
  `event` records carrying `meta.start`/`meta.end` and `meta.rrule`, and any
  `type:project` records for side projects and hobbies.
- Taskwarrior with string UDAs `est`, `starttime`, `endtime`, `location`, and
  `travel` configured; create them before planning when they are unavailable.
- Conversation with the user supplying availability, project preferences, and a
  per-assignment estimate.
- The current date and time in America/Chicago (UTD is in Dallas, TX).

## Output Contract
- A confirmed day-by-day plan for the target week, each day at roughly 8h total.
- Taskwarrior contains every target-week fixed event occurrence and concrete
  work action needed for `task ready` to be a complete daily agenda.
- Each task carries its real `due`, planned `scheduled` date, and action-specific
  `est`; fixed-time tasks also carry `starttime`, `endtime`, `location`,
  `+class`, and `+fixed`.
- A per-assignment `est` value written back into omn as `meta.est`.
- Newly mentioned side projects recorded in omn as `type:project` records.
- The created or moved task IDs reported, and a verification summary.

# Entrypoint

## Stage 1: Establish ground truth
1. Run `date` and record the current weekday.
2. Read the store with `omn list` and `omn export`; collect assignment tasks and
   class events, and note every `type:project` record.
3. Read existing pending tasks and split them into flexible `+managed`, fixed
   `+managed +fixed`, and unmanaged tasks.
4. Note every scheduled `est`; fixed and unmanaged tasks consume capacity and
   cannot be moved automatically.
5. If the store is empty or stale, re-ingest the Canvas feed (see omn-search,
   optional depth) and return to the start of Stage 1; otherwise proceed to
   Stage 2.

## Stage 2: Agree the target week
1. Define the target week as the next full Monday-to-Sunday span unless the user
   names another range; state the start and end explicitly.
2. Confirm the range with the user and proceed to Stage 3.

## Stage 3: Collect estimates
1. For each assignment to schedule, ask the user for an `est` value in hours.
2. When a record already has `meta.est`, reuse it to anchor the question as a
   historical estimate rather than asking blindly.
3. After each answer, write `est` back into the assignment record in omn by
   re-importing it with `meta.est` set, preserving every other field; import is
   idempotent by record id.
4. If the user declines an estimate, record an explicit placeholder and flag it
   in the summary rather than dropping the assignment.
5. Sum the estimates into a weekly workload total; proceed to Stage 4.

## Stage 4: Build the proposed schedule
1. Compute each day's class hours from the event `meta.rrule`, then each day's
   assignment capacity as the budget minus class hours minus any unmanaged
   `est:` on that day.
2. Place every assignment on days before its `due`, applying the splitting and
   pull-forward rules in the Guidelines; claim the earliest capacity first
   (aggressive early scheduling) and keep weekends free of assignment work
   unless the deadline forces it.
2a. Allocate the weekly lab time before placing other work: 6 hours at Prof.
   Jee's lab centered on Monday/Wednesday 10:00-17:00, including the 1h
   PyLingual meeting, with the remaining 5 hours as contiguous as possible.
3. Add side projects to the lightest days to round each day toward the budget.
4. Present the proposed plan as a table of day, class hours, tasks, estimates,
   and deadlines, with per-day totals.
5. If the user accepts the plan, proceed to Stage 5; otherwise revise the plan
   from the user's feedback and repeat Stage 4.

## Stage 5: Register in Taskwarrior
1. Expand each active fixed event into one concrete action per occurrence in the
   target week.
2. Begin every event description with an imperative verb; use `Attend` for
   classes, club meetings, and other attendance commitments.
3. Give each fixed event task `scheduled` equal to its occurrence date,
   local `starttime` and `endtime`, `location`, duration as `est`, and tags
   `+managed +fixed`; add `+class` only for classes. Do **not** give event tasks
   a bare-date `due`: Taskwarrior stores it as midnight, which paints the task
   red as imminent/overdue in `task schedule`. Attendance events carry no `due`;
   only deadline-bearing items get one (encoded 23:59 local per item 8).
4. When a location varies or is unknown, write an explicit instruction to check
   the authoritative schedule instead of leaving `location` blank.
5. Do not create duplicate event tasks when the same description, date, and time
   window already exist.
6. Convert each planned assignment into one or more concrete action tasks.
7. Give every action the assignment's actual Canvas `meta.due` as its real
   `due`, its planned `scheduled` date set to the day the action is meant to
   happen, its own `est`, `+managed`, and `travel` when the action requires
   travel.
8. When a deadline is day-granularity (Canvas gives a date with no meaningful
   time, or the user names a bare day), encode `due` as **23:59 local time on
   that day** — never midnight. Midnight makes the deadline elapse at the
   start of the day, which falsely paints the task as overdue all day. Verify
   Canvas times before assuming: Canvas "due <date>" means 11:59 PM that day,
   not 12:00 AM.
9. Represent a single-action assignment with exactly one Taskwarrior task.
10. Represent multiple actions as independent tasks with descriptive names and
   the same assignment deadline; do not create parent or tracking tasks.
11. Add concrete side-project tasks with `scheduled`, `est`, and `+managed`; add
   `due` only when a real deadline exists.
12. Never add `deliverable` or `workblock` tags or create hierarchy-only entries.
13. Modify only `+managed` tasks; never modify or delete an unmanaged task.
14. Record each created task id; proceed to Stage 6.

## Stage 6: Verify
1. Run `task ready` and confirm every remaining class and work action for today
   is visible, with fixed commitments showing their time windows.
2. Run `task list` and confirm future work, with nothing scheduled after its
   `due`.
3. Run `task export status:pending` and confirm per-day totals stay near the
   budget, no assignment scheduled past its deadline, small items unsplit, and
   large items split.
4. Run the schedule linter for the target week:
   `python3 ~/.config/pi/profiles/omn-assistant/bin/taskwarrior_lint.py --week <monday>`.
5. Triage every linter warning before touching anything: classify it as an
   expected exception the user asked for (explicit times, shifted meal blocks,
   deadline-forced weekend work, a waived break) or a genuine violation; fix
   the genuine ones and state the accepted exceptions in the reply.
6. Fix any remaining violation by moving `+managed` tasks only, then repeat
   Stage 6. The linter is advisory — you are the final judge, never apply its
   output blindly.

# Guidelines

## Schedule linter

After the week's tasks are registered (and again after any rebalance), run:

    python3 ~/.config/pi/profiles/omn-assistant/bin/taskwarrior_lint.py --week <monday>

The linter checks the standing guidelines (recurrence-template ban, duplicate
tasks, midnight dues, omn assignment coverage, class occurrence registration,
lab hours, weekend protection, start boundary, transit buffers, car-trip
grouping, meal blocks, venue-hours hints, and more) and emits advisory
warnings.

- The linter is **not authoritative**. Triage every warning into an expected
  exception the user asked for (explicit times, shifted meals,
  deadline-forced weekend work, a waived break) or a genuine violation, then
  fix only the genuine ones and state the accepted exceptions in the reply.
- Never apply fixes blindly because the linter flagged them; the agent, with
  the user, is the final judge.

## Daily budget
- Treat each weekday's total of class hours plus scheduled `est` hours as the
  budget, nominally 8 hours.
- On a given day, schedule assignment and project work only up to the remaining
  capacity after class and unmanaged `est`.
- Allow exceeding the budget only when a real deadline cannot otherwise be met,
  and only by the minimum needed; state the exception before applying it.

## Taskwarrior task model
- Every Taskwarrior entry must describe a concrete action or attendance
  commitment the user can perform.
- Begin every description with an imperative verb so it reads as a direct action.
- Keep durable existence, recurrence, and source state in omn; convert only each
  actionable occurrence or work unit into Taskwarrior.
- Use `due` only for the real deadline and `scheduled` only for the planned day.
- Set `due` on Canvas-backed assignments exactly from the omn `meta.due` value;
  never replace it with a planning target, a safety margin, or the scheduled
  date.
- Set `scheduled` to the day the action is actually meant to happen, matching
  the accepted plan; do not default it to the due date or another placeholder.
- Treat attending a class as a concrete task due and scheduled on its occurrence
  date.
- Put fixed local times in `starttime` and `endtime` using 24-hour `HH:MM`.
- Copy the authoritative place into `location` for every fixed event task.
- Tag every immovable event with `+fixed`; add `+class` only for classes and never
  move fixed tasks to balance capacity.
- When work needs multiple actions, create independent tasks with the same real
  deadline and schedule each action on its intended day.
- Do not create deadline trackers, parent tasks, work blocks, deliverables,
  hierarchy, or relationship tags in Taskwarrior.
- Make descriptions sufficient for the user to know what action to take.
- Store `est` as a compact human-readable string using decimal hours or days.
- Treat 0.5 hours as the minimum estimate for any allocated task; never create
  0h tasks, and merge or consolidate smaller actions into 0.5h or larger tasks.
- Never write ISO 8601 duration forms into Taskwarrior `est`.
- Expand day-scale estimates against the current daily budget during capacity
  calculations.

## Managed and unmanaged tasks
- Tag every task you create with `+managed` only as an ownership safety marker.
- Treat a task without `+managed` as unmanaged: never modify, move, or delete
  it unless the user explicitly asks, and say you are doing so first.
- Count unmanaged and `+fixed` task estimates toward their scheduled day's
  budget and treat them as un-reschedulable.

## Splitting
- Keep an assignment at or under 2 hours on a single day, because context
  switching costs more than the split saves.
- Split an assignment of 4 hours or more across two or more days, front-loaded
  so the bulk lands well before the due date.
- Treat an assignment between 2 and 4 hours as a single-day item, splitting only
  when it is the only way to fit the week.

## Pull-forward
- Pull a future same-week assignment earlier only when a day has spare capacity.
- Never pull work into a week earlier than its own week, because the lectures
  the assignment depends on may not have happened yet.

## Weekends are protected
- Avoid scheduling assignment work on weekends. Weekends are rest, personal
  projects, going out, and events such as hackathons.
- Schedule weekend-due homework in advance on weekdays. Doing homework on a
  weekend is acceptable only when the deadline is that weekend and no
  earlier capacity remains.

## Aggressive early scheduling
- Schedule assignments the moment they become known; the first planning pass
  after new assignments appear allocates them before anything else.
- Front-load work as early as capacity allows so an emergency or event can
  never cost a deadline.
- Errands and flexible items are pushable; assignments are not, so assignments
  claim early capacity ahead of errands and projects.

## Venue hours
- Before scheduling an action that depends on a place being open (bank branch,
  office, store, clinic), web-search that place's hours for the target date.
- Never place such an action on a day or at a time the venue is closed
  (example: Regions branches close on weekends).

## Locations and transit
- Every task that gets a time block also gets a `location`; untimed tasks stay
  location-free until they are staged. Use real places so transit can be
  computed: `ECSS 3.226` (Prof. Jee's lab), `SU Starbucks` (the usual hangout
  between classes), lecture rooms, or `At home` (the dorm — off campus).
- Transit between neighboring blocks: **0 min** same place, **10 min** same
  building, **20 min** different buildings both on campus, **30 min** whenever
  a leg goes off campus. The dorm counts as off campus for everything.
- Work blocks can sit in campus spots (SU Starbucks, the library, an empty
  lecture room) to stay on campus between classes.
- Default a between-class block to **SU Starbucks**, and only count the gap as
  work time when the usable window fits a whole piece after transit; see the
  schedule-day skill. Never use a vague location such as "near room X" or
  "(near classroom)".

## Splitting tasks
- Prefer one contiguous block on a later day over splitting a task across days.
- Never create a piece shorter than one hour when a task is split; name the
  pieces `Start <task>` / `Continue <task>` / `Finish <task>` and keep the
  pieces of one task in order.
- When re-planning pushes a deadline-free item past the week, say which item
  moved rather than fragmenting the task under it.

## Prof. Jee lab time
- Schedule 6 hours of lab time per week at Prof. Jee's lab.
- Center the lab hours on Monday and Wednesday between 10:00 and 17:00, when
  others are in the lab; any distribution across those days works.
- The weekly PyLingual meeting (11:00-12:00) counts as one lab hour; schedule
  5 additional hours, as contiguous as the week allows.
- The lab room is **ECSS 3.226** — use it as the `location` on every lab block
  and on the PyLingual meeting task.

## Daily meals
- Schedule breakfast and dinner every day in consistent time blocks:
  breakfast between 06:00 and 08:00, dinner between 17:00 and 20:00.
- Default to breakfast 07:00-07:45 and dinner 18:00-18:45 every day; shift the
  whole block (never scatter it) when a fixed commitment requires, and keep
  the same block across days.

## Side projects and hobbies
- Record a project the user mentions that is not in omn as a `type:project`
  record before scheduling it.
- Fit projects onto the lightest days to round each day up to the budget.
- Never move or delay an assignment to make room for a project.

## Recurrence artifacts

- Before arranging any record's tasks across the week, read its `artifacts.rrule`
  artifact when one exists; the file is named by replacing the record id's
  colons with underscores and appending `_rrule.md`.
- Honor the recurrence, duration, sequencing, and placement constraints written
  in that artifact when allocating days and blocks; they override default
  placement heuristics for that record's tasks.
- Do not schedule a record against its rrule artifact; when the artifact cannot
  be satisfied, report the specific conflict instead of silently ignoring it.
- **Never create Taskwarrior recurrence templates.** Recurrence is an omn-side
  concern (`meta.rrule`); register each week's occurrences as individual plain
  tasks. This keeps week-to-week changes (a cancelled meeting, a one-week time
  shift) frictionless.

## People schedules

- When arranging shared work that names another person, look up that person in
  omn (`type:person` records) and place the block outside their `meta.busy`
  intervals; treat approximate intervals with a 15-minute margin.
- If no record exists for that person, ask for their schedule before placing
  shared work rather than assuming availability.

## Estimates

- Write every agreed `est` back into omn as `meta.est` so future runs can offer
  it as a historical estimate.
- Normalize estimates to compact decimal-hour or day strings with explicit units.
- Prefer prompting with the existing historical estimate attached.
