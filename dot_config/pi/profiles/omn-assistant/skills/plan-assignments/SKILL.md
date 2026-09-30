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
1. Let the composer read ground truth directly rather than hand-building a
   spec: it reads `omn export` and the Taskwarrior export for the selected
   Monday-to-Sunday week. It expands active omn events (and their RFC 5545
   weekly `rrule`s, honoring `cancelled` dates) plus pending `+fixed`
   Taskwarrior windows and the 00:00-06:00 sleep block into authoritative fixed
   intervals. `+fixed` items are unavailable windows, never work.
2. It turns each active omn task into a flexible requirement from its
   `meta.est`, `meta.due`, `meta.target_week`, `meta.available`/`unlock`,
   `kind`, derived topic, and `location`. A requirement with no estimate, an
   ambiguous/placeholder estimate, or a `due` before the week is a BLOCKING
   diagnostic — never guess an `est`; fill it in (Stage 3) or reconcile it in
   omn. A pending `+managed` task whose `todo` refs do not resolve to plan ids
   is BLOCKING carried work, never grounds for silent deletion.
3. Run the candidate proposer:

   ```sh
   ~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py plan \
     --week <monday> --candidates 3 --out CANDIDATES.json
   ```

   Pass `--spec FILE` only for deterministic tests/debugging, never for real
   planning. Requirement coverage, availability/deadline windows, fixed
   intervals, the 30-minute grid, 10:00–18:00 flexible-work boundary,
   minimum/maximum block length, location-based transit gaps, the per-day and
   weekly block caps, and block non-overlap are HARD tracked constraints.
   Blocking source diagnostics short-circuit before Z3 with a semantic core;
   the composer never solves a smaller, misleading subset. The solver
   then minimizes a few nonnegative soft buckets — assignment timing/weekend
   pressure, rest/daily-load intrusions, and cohesion/context/waste — probing a
   small target ladder per bucket and locking the first satisfiable threshold;
   "good enough" beats optimal. `--candidates` offers placements that differ by
   fingerprint and/or documented threshold ladder, never by weakening a hard
   constraint.

   Additional hard/soft machinery: a requirement with `meta.indivisible: true`
   must sit in one block wholesale (used for single-sitting items like a
   Quinncia recording session; requirements of 60 minutes or less are treated
   as indivisible automatically so small errands never fragment). Standing
   support windows (cook breakfast, breakfast, lunch, afternoon break, dinner)
   are placed as pushable, shrinkable intervals with their own daily windows
   and duration bounds; they are decoded into `+managed +schedule +composer`
   records with no todo, and are dropped (not failed) when a fixed commitment
   or a deadline-forced week leaves no room, at a soft cost. A minute-grid
   capacity precheck runs before Z3: it subtracts fixed commitments, transit
   margins, and grid alignment, and when requirements exceed the usable
   minutes it returns an instant INFEASIBLE whose core names the shortage
   (per requirement or aggregate), instead of burning solver time or silently
   dropping work.

## Carried work and deferral (standing rules)

- Carried work does NOT have to complete inside the selected week. It only
  has to land sometime before its due date.
- A requirement enters this week's plan only when its `meta.due` falls in the
  week, its `meta.target_week` covers the week, or it is explicitly pending
  with an elapsed due (that last one is a BLOCKING diagnostic — reconcile it).
- On apply, carried managed blocks are reallocated automatically from their
  `[omn:<id>]` todo refs: refs planned this week → the old block is replaced
  by fresh coverage; refs that exist in omn but are not needed this week →
  the block is DEFERRED (rescheduled to next Monday, time window cleared) so
  the next week's plan picks it up; `+schedule` support blocks with no refs
  are deleted and recreated from the plan's support windows.
- To pull deferred work into a specific week, set its omn `meta.target_week`;
  to defer, clear it or push it forward. The Taskwarrior block follows the
  plan, never the reverse.

## Manual (zero-agent) workflow

The composer is fully autonomous; the agent is optional glue.

```sh
~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py plan \
  --week <monday> --candidates 3 --out plan.json --quiet
~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py show \
  --plan plan.json            # readable calendars; pick one
~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py apply \
  --plan plan.json --candidate N          # dry-run preview
~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py apply \
  --plan plan.json --candidate N --yes    # write + lint + gcal
```

Requirements without a reliable `meta.est` use a deterministic 2h default
(`--default-est-minutes` to change) surfaced as an info diagnostic rather
than blocking the run. The agent's remaining value: reading mail into omn,
natural-language omn entry, and reasoning about which candidate to pick.
4. Reject an `INFEASIBLE` candidate and read its `unsat_core`: it names the
   requirement, fixed interval, or daily cap that made the week impossible.
   Never auto-drop a requirement to manufacture a satisfiable week. A plan with
   `has_blocking_diagnostics: true` is not applicable as-is. When
   `optimization_exact` is false, rerun with a larger `--timeout-ms` before
   calling a candidate best, and label an approximate candidate as approximate.
5. Compare candidates by their `soft` bucket report and `fingerprint`, and
   explain the tradeoff. Coverage is hard, so no candidate hides estimate
   shortfall; never present one that would sit work past its real deadline.
6. Allocate the weekly lab time before flexible work: 6 hours at Prof. Jee's
   lab centered on Monday/Wednesday 10:00-17:00, including the 1h PyLingual
   meeting, with the remaining 5 hours as contiguous as possible.
7. Present the strongest candidates as a table of day, fixed hours, composed
   blocks, and estimate coverage. Explain why one is preferred; the user
   remains the final chooser.
8. If the user accepts the plan, proceed to Stage 5; otherwise revise the
   inputs (omn estimates, availability) from the user's feedback and rerun
   Stage 4. Do not edit the composer's hard constraints to force a fit.

## Stage 5: Register in Taskwarrior
0. Prefer the composer's own apply path for the accepted candidate:

   ```sh
   # preview (dry-run is the default)
   ~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py apply \
     --plan CANDIDATES.json --candidate N
   # write
   ~/.config/pi/profiles/omn-assistant/bin/schedule_composer.py apply \
     --plan CANDIDATES.json --candidate N --yes
   ```

   It refuses to write when any diagnostic is blocking, the candidate's
   optimization status is unknown, a pending managed task cannot be reconciled,
   or fixed intervals conflict. It reloads omn and Taskwarrior, refuses a stale
   plan, validates exact allocations/windows/transit, matches tasks by UUID
   (never the mutable numeric id), and preserves unmanaged and `+fixed` tasks
   plus composer blocks from other weeks. It replaces only the selected week's
   solver-owned `+managed +composer` blocks (plus reconciled carried blocks),
   creating and verifying replacements before deleting old blocks. Then it
   re-exports to
   verify, runs `taskwarrior_lint.py`, then the gcal-sync skill; a failed
   calendar sync is reported, not rolled back. Steps 1-14 below remain the
   model for anything the composer does not cover (unmanaged/`+fixed` tasks and
   hand fixes).
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
6. Compose every remaining omn requirement into **cohesive blocks**. A block is
   one topic worked in one sitting; its `description` is a one-glance title for
   that topic, and its `todo` UDA carries one bullet per covered omn record,
   each ending `[omn:<record id>]`:

   ```
   description: "Follow up with recruiters after career fair"
   todo:        "- Micron - intern pipeline and resume review @10m [omn:manual:contact:micron]"
                "- Crescent Systems - entry-level SWE reqs @10m [omn:manual:contact:crescent]"
   ```

   Cohesion is absolute: never mix unrelated topics in one block, and never
   drop a due-soon item into an unrelated block to save a slot - give it its
   own block instead, even a 0.5h solo one. The glance title must be a perfect
   summary of the bullets, because that title is what the Google Calendar
   block shows.
7. Requirements do not map 1:1 to blocks. Several small items (a reply, a
   signup, a purchase) belong as bullets inside one topical block; one large
   requirement may span several blocks, including across days. Pin a small
   todo's own expected duration as `@10m` or `@0.5h`; leave the large or
   open-ended requirement unpinned. Coverage consumes pinned bullets in todo
   order and attributes the block's remainder to the open-ended requirement(s)
   by their remaining est. Never pin a requirement's full multi-hour est on
   every piece. Granularity lives in omn; blocks are the schedule built to
   satisfy it. Give every block its `scheduled` date, `est` equal to its
   window, `+managed`, `location`, `transport`, and `travel` when the action
   requires travel. A block's `due` is optional; omit it unless useful, and
   never let it sit later than the earliest due among its todos.
8. When a deadline is day-granularity (Canvas gives a date with no meaningful
   time, or the user names a bare day), encode `due` as **23:59 local time on
   that day** — never midnight. Midnight makes the deadline elapse at the
   start of the day, which falsely paints the task as overdue all day. Verify
   Canvas times before assuming: Canvas "due <date>" means 11:59 PM that day,
   not 12:00 AM.
9. Cap the number of blocks per day: every block costs a full
   context-switching tax (transit, settling in, remembering where you were),
   so pack cohesive work into as few blocks as the day allows. Target at
   most six non-meal, non-class blocks per day; more than that means the day
   needs consolidating, not more scheduling.
10. Represent a multi-day requirement as consecutive same-topic blocks named
   `Start X` / `Continue X` / `Finish X`; never as unrelated separate tasks.
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

## Scoped requests

- Do exactly what the user asked for; never reschedule or re-plan other work
  on the side. A reschedule pass happens only when the user requests one.

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
- omn owns the *requirements*: every satisfiable external item exists as an
  omn record (assignment, event, signup, reply). Taskwarrior owns the
  *schedule* built to satisfy them. There is deliberately no 1:1 mapping.
- A Taskwarrior entry is a **block**: one topic, one location, one sitting. Its
  `description` is a one-glance title; its `todo` UDA holds one bullet per
  covered omn record, each ending `[omn:<record id>]`. Add `@10m` / `@0.5h`
  before the ref only for fixed-duration small todos; an unpinned todo is an
  open-ended consumer of the block's remaining time.
- Begin every description with an imperative verb so it reads as a direct action.
- Keep durable existence, recurrence, and source state in omn; reference them
  from blocks by id in the `todo` UDA rather than mirroring them.
- Use `due` only for a real deadline the block must respect and `scheduled`
  only for the planned day; a block's `due`, when set, must never fall later
  than the earliest due among its todos.
- Set `scheduled` to the day the block is actually meant to happen, matching
  the accepted plan; do not default it to a due date or another placeholder.
- Treat attending a class as a concrete task on its occurrence date; fixed
  events stay 1:1 with omn occurrences because attendance occupies a fixed
  slot that no other work can absorb.
- Put fixed local times in `starttime` and `endtime` using 24-hour `HH:MM`.
- Copy the authoritative place into `location` for every fixed event task.
- Tag every immovable event with `+fixed`; add `+class` only for classes and never
  move fixed tasks to balance capacity.
- Do not create deadline trackers, parent tasks, work blocks, deliverables,
  hierarchy, or relationship tags in Taskwarrior.
- Store `est` as a compact human-readable string using decimal hours or days.
- Treat 0.5 hours as the minimum block length; never create 0h blocks, and
  fold smaller items into a cohesive block as bullets.
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
- Homework lives on weekdays. Weekends are for driving, errands, groceries,
  personal projects, going out, and events such as hackathons — so front-load
  assignment work into Mon-Fri even when the deadline lands on a weekend.
- Budget the standing weekend anchors on Saturday: a grocery run (car, ~1.5h)
  and laundry (~1h). The user cancels a given week when they are not needed.
- Wednesday carries a 3h swimming block after lab time (UTD Activity Center
  natatorium, Mon-Thu 4-10 PM).

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
- The user cooks every meal: budget one hour of cooking before breakfast, then
  breakfast 07:30-08:15 (on 08:30-class mornings: cook 06:15-07:15, breakfast
  07:15-08:00). Dinner stays 18:00-18:45 by default, shifted as one block when a
  fixed commitment requires.
- Prefer home/packed food over eating out when choosing lunch locations.

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
