---
name: reschedule
description: "Use when the user has fallen behind and asks to reschedule, when
  scheduled work has piled up, or when past scheduled tasks remain pending and
  need to be rebalanced forward."
metadata:
  type: procedure
---

# Contract

## Input Contract
- A request to reschedule after the user has fallen behind on their plan.
- Taskwarrior state with pending flexible `+managed` tasks, immovable
  `+managed +fixed` commitments, and unmanaged tasks carrying `est:`.
- A populated omn store with assignment deadlines (`meta.due`) and class events
  (`meta.rrule`) for capacity math.
- The current date and time in America/Chicago (UTD is in Dallas, TX).

## Output Contract
- Carried `+managed` work moved onto future days, none left scheduled on or
  before the current date, none scheduled past its real deadline.
- A rebuilt plan with each day near the budget, exceeding it only by the minimum
  needed to meet a deadline and only after proposing to squash side projects.
- Unmanaged and `+fixed` tasks left untouched unless the user explicitly asks
  for a factual correction.
- A before-and-after summary with the modified task ids and per-day totals.

# Entrypoint

## Stage 1: Establish ground truth
1. Run `date` and record the current date and weekday.
2. Read the store with `omn list` and `omn export` for assignment deadlines and
   the class schedule.
3. Read pending tasks and separate flexible `+managed`, immovable
   `+managed +fixed`, and unmanaged tasks.
4. Count scheduled fixed and unmanaged `est` values as unavailable capacity.

## Stage 2: Identify carried work
1. Select flexible `+managed` pending tasks that are overdue or have a
   `scheduled` date on or before the current date.
2. Exclude `+fixed` tasks from movement; report a past pending class as missed or
   unresolved rather than rescheduling it.
3. Determine remaining work per selected task: the full `est` when a portion was
   not done, or the user's stated remaining amount when they partially worked
   it.
4. Account for fixed and unmanaged tasks on candidate days without modifying
   them.
5. Sum carried hours by deadline so the minimum work per day is known; proceed
   to Stage 3.

## Stage 3: Ripple forward and rebalance
1. Sort carried work by deadline, earliest first.
2. Reassign each item to the earliest future day with remaining capacity, where
   capacity is the budget minus fixed scheduled `est`, unmanaged scheduled
   `est`, and already-planned flexible `+managed` work.
3. Keep small items unsplit; prefer one contiguous block on a later day over
   splitting a task, and never create a piece shorter than one hour.
4. For any item that is part of a split task (a `Start`/`Finish` pair, or any
   task with sibling pieces), re-plan the whole family in one pass instead of
   sliding the single block: keep the task's total hours the same, re-divide it
   across the week, and rename the pieces to match the new division.
5. If a day would exceed the budget, first propose squashing non-assignment
   tasks on that day and later days to free the room.
6. If a deadline still cannot be met at the budget, exceed it by the minimum
   needed and only for the days and items that require it. If no deadline
   requires it, push the item past this week rather than fragmenting it.
7. If the rebuild satisfies the checks, proceed to Stage 4; otherwise recompute
   with the user's priorities and repeat Stage 3.

## Stage 4: Propose, confirm, apply
1. Present a before-and-after table of each carried item's old and new scheduled
   date, estimate, and deadline, with per-day totals, and note any proposed
   squashing. For split tasks, show the whole family's before-and-after and the
   renames, not just the moved piece.
2. On confirmation, move each carried `+managed` task with one modify per task,
   using its id from the export, adjusting `est` only when the remaining portion
   changed. Rename pieces as planned.
3. Never modify, move, or delete an unmanaged, `+fixed`, or already-completed
   task.
4. Record every modified task id; proceed to Stage 5.

## Stage 5: Verify
1. Run `task ready` and confirm the rebuilt day's work.
2. Run `task list` and confirm no `+managed` item is scheduled on or before the
   current date or after its `due`.
3. Run `task export status:pending` and confirm each day stays near the budget
   except the explicit deadline-driven exceptions.
4. Run `task schedule` (the report is unscoped, so past-day items stay
   visible) and confirm no pending task is left on a past `scheduled` date:
   the linter's `stale-scheduling` policy raises any that remain as an ERROR.
   Reschedule those items forward (or complete/cancel them with the user)
   until that policy is silent. Never fix this by changing the report's
   display filter — the user wants stale work visible, not hidden.
4. Fix any violation by moving `+managed` work only, then repeat Stage 5.

# Guidelines

## Flexible, fixed, and unmanaged tasks
- Move or modify only flexible `+managed` tasks.
- Treat `+managed +fixed` class, meeting, appointment, and event tasks as
  immovable commitments.
- Treat unmanaged tasks as fixed: never move or delete them unless the user
  explicitly asks, and say you are doing so first.
- Count fixed and unmanaged scheduled `est` values toward the day's budget.

## Daily budget
- Treat each weekday's total scheduled `est`, including every fixed event task,
  as the budget, nominally 8 hours.
- Parse compact decimal-hour and day estimates; expand day units against the
  current daily budget.
- Never replace compact estimates with ISO 8601 duration forms.
- Stay at or under the budget; exceed it only by the minimum needed to meet a
  real deadline.

## Squashing non-assignment work
- When a day is over budget, first offer to squash non-assignment work, namely
  side-project and hobby tasks, on that day and later days.
- Preserve assignment work above project work whenever room must be made.

## Multi-part (split) tasks
- Treat every piece of a split task as one unit: `Start X` / `Continue X` /
  `Finish X` are the same task divided in time, not independent items.
- When the user asks to move or cancel one piece, scan the whole week for the
  task's other pieces, decide the new division, and keep the total estimated
  hours the same across the pieces.
- Re-divide before moving: prefer merging pieces into one contiguous block (on
  a later day when needed) over keeping the same number of pieces, and never
  produce a piece shorter than one hour.
- Rename the pieces to match the new division (`Start`, `Continue`, `Finish`),
  preserving the imperative verb-first style, and re-derive start/end times so
  a `Start` piece is never scheduled at or after its `Finish` piece.
- Never slide a piece naively: moving one block without re-planning its
  siblings produces nonsense such as a `Finish` piece before its `Start`.
- When the whole task cannot fit before its deadline, prefer dropping unrelated
  deadline-free work out of the week over fragmenting the task further.

## Rippling and deadlines
- Reassign carried work to the earliest day with capacity, earliest deadlines
  first.
- Preserve imperative verb-first descriptions when moving tasks.
- Begin every newly split task description with an imperative verb describing
  its concrete action.
- Never schedule a task after its real deadline.
- Keep small items unsplit and split large items across days, front-loaded.
- Pieces of a split task are never shorter than one hour; prefer one
  contiguous block on a later day over a fresh split.

- Treat 0.5 hours as the minimum estimate for any task reallocation; merge
  smaller carried actions into 0.5h or larger tasks rather than moving many
  sub-0.5h fragments.
- Before reallocating a record's tasks, read its `artifacts.rrule` artifact
  when one exists (named by replacing the record id's colons with underscores
  and appending `_rrule.md`) and honor its recurrence and placement constraints
  when choosing new days.

## Scoped requests
- When the user asks for something specific (a lookup, a placement, a single
  change), do exactly that — do not silently reschedule or re-plan other items
  on the side. Run the reschedule flow only when the user asks for it.

## Completeness
- Never drop carried work silently; if it cannot fit, report the shortfall and
  the reason rather than leaving a return task unscheduled.
