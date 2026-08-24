---
name: plan-assignments
description: "Use when the user asks to plan, schedule, or set up next week's
  assignments, or to move assignments from omn into Taskwarrior as scheduled
  work blocks with per-assignment time estimates."
metadata:
  type: procedure
---

# Contract

## Input Contract
- A request to plan the next week's work from the omn store.
- A populated store with assignment `task` records carrying `meta.due`, class
  `event` records carrying `meta.start`/`meta.end` and `meta.rrule`, and any
  `type:project` records for side projects and hobbies.
- Taskwarrior with the `est` UDA configured (`uda.est.type=duration` and
  `uda.est.label` in the task configuration); create it before planning if the
  `est:` duration is not recognized.
- Conversation with the user supplying availability, project preferences, and a
  per-assignment estimate.
- The current date and time in America/Chicago (UTD is in Dallas, TX).

## Output Contract
- A confirmed day-by-day plan for the target week, each day at roughly 8h total.
- Taskwarrior tasks created or updated only for `+managed` work: one deliverable
  task per assignment with `due` and total `est`, plus one or more work-block
  tasks with `scheduled` and per-day `est`.
- A per-assignment `est` value written back into omn as `meta.est`.
- Newly mentioned side projects recorded in omn as `type:project` records.
- The created or moved task IDs reported, and a verification summary.

# Entrypoint

## Stage 1: Establish ground truth
1. Run `date` and record the current weekday.
2. Read the store with `omn list` and `omn export`; collect assignment tasks and
   class events, and note every `type:project` record.
3. Read existing tasks with `task export status:pending` and split them into
   `+managed` and unmanaged; note unmanaged tasks that carry `est:`, because
   each occupies its day's budget and is un-reschedulable.
4. If the store is empty or stale, re-ingest the Canvas feed (see omn-search,
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
   pull-forward rules in the Guidelines.
3. Add side projects to the lightest days to round each day toward the budget.
4. Present the proposed plan as a table of day, class hours, tasks, estimates,
   and deadlines, with per-day totals.
5. If the user accepts the plan, proceed to Stage 5; otherwise revise the plan
   from the user's feedback and repeat Stage 4.

## Stage 5: Register in Taskwarrior
1. For each assignment, add one deliverable task with `due`, total `est`, and
   `+managed`, and one work-block task per scheduled day with `scheduled`, that
   day's `est`, `+managed`, and `+workblock`.
2. Add side-project work blocks with `scheduled`, `est`, `+managed`, and a
   project value indicating a hobby.
3. Modify only `+managed` tasks; never modify or delete an unmanaged task.
4. Record each created task id; proceed to Stage 6.

## Stage 6: Verify
1. Run `task ready` and confirm the day's work is visible.
2. Run `task list` and confirm future work, with nothing scheduled after its
   `due`.
3. Run `task export status:pending` and confirm per-day totals stay near the
   budget, no assignment scheduled past its deadline, small items unsplit, and
   large items split.
4. Fix any violation by moving `+managed` work blocks only, then repeat Stage 6.

# Guidelines

## Daily budget
- Treat each weekday's total of class hours plus scheduled `est` hours as the
  budget, nominally 8 hours.
- On a given day, schedule assignment and project work only up to the remaining
  capacity after class and unmanaged `est`.
- Allow exceeding the budget only when a real deadline cannot otherwise be met,
  and only by the minimum needed; state the exception before applying it.

## Managed and unmanaged tasks
- Tag every task you create with `+managed`.
- Treat a task without `+managed` as unmanaged: never modify, move, or delete
  it unless the user explicitly asks, and say you are doing so first.
- Count an unmanaged task's `est:` toward its day's budget and treat it as fixed
  and un-reschedulable.

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

## Side projects and hobbies
- Record a project the user mentions that is not in omn as a `type:project`
  record before scheduling it.
- Fit projects onto the lightest days to round each day up to the budget.
- Never move or delay an assignment to make room for a project.

## Estimates
- Write every agreed `est` back into omn as `meta.est` so future runs can offer
  it as a historical estimate.
- Prefer prompting with the existing historical estimate attached.
