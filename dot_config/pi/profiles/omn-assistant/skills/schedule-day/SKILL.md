---
name: schedule-day
description: "Use when turning date-planned Taskwarrior tasks into a chronological
  daily schedule with fixed times, meals, breaks, travel grouping, and downtime gaps."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A request to time-block one day of existing Taskwarrior work.
- The current `task ready` agenda as the set of actions to schedule.
- Every carried managed task shown by `task ready`, regardless of its prior
  scheduled date.
- Ready tasks with `scheduled`, compact `est`, and verb-first descriptions.
- String UDAs named `starttime`, `endtime`, `location`, and `transport`.
- Fixed commitments tagged `+fixed` with authoritative time windows.
- The selected date, defaulting to today in America/Chicago.
- Current transportation availability and any user-supplied day-start constraint.

## Output Contract

- Every selected actionable task has a non-overlapping `starttime` and `endtime`.
- Fixed tasks retain their authoritative date, time, estimate, and location.
- Flexible work ends by 18:00.
- Higher-urgency flexible tasks occupy earlier available work periods.
- Every selected task has `transport` set to `car` or `no-car`.
- Car tasks form one contiguous errand trip whenever constraints allow.
- One one-hour lunch action occurs wholly between 11:00 and 14:00.
- One afternoon-break action lasts from one through two hours.
- Unallocated downtime gaps separate scheduled items whenever capacity permits.
- Overflow is moved or reported explicitly rather than silently omitted.
- `task schedule` contains the same pending task set as `task daily`.
- Created and modified Taskwarrior IDs and the chronological schedule are reported.

# Entrypoint

## Stage 1: Establish staged Taskwarrior state

1. Run `date` in America/Chicago and state the selected date.
2. Run `task ready` and treat its listed actions as the scheduling input.
3. Run `task export` to retrieve complete fields for those ready tasks.
4. Select fixed tasks scheduled on the selected date.
5. Select every flexible `+managed` task shown by `task ready`, including all
   tasks carried from earlier scheduled dates.
6. Treat carried tasks as mandatory scheduling input rather than leaving their
   old time windows in place.
7. Never modify an unmanaged task without explicit permission.
8. On a rerun, identify pending `+managed +schedule` support actions for the date
   so they can be replaced rather than duplicated.
9. If scheduling today, set the earliest planning cursor to the later of 08:00
   or the current time rounded up to the next 15-minute boundary.
10. If scheduling a future date without a supplied day start, use 08:00.
11. Parse compact hour and day estimates; preserve zero-duration actions.
12. Proceed to Stage 2.

## Stage 2: Classify tasks and reserve hard constraints

1. Separate `+fixed` tasks from flexible tasks.
2. Preserve every fixed task's `scheduled`, `starttime`, `endtime`, `location`,
   and `est` values.
3. Set `transport` to `car` when performing the action requires a car trip.
4. Set `transport` to `no-car` when the action can be performed without a car.
5. Ask the user only when transportation cannot be inferred from Taskwarrior or
   the current conversation.
6. If transportation required by a task is unavailable, do not assign it a time
   window; move it only when a feasible date is known, otherwise report it as
   blocked.
7. Reserve all fixed time intervals before placing flexible work.
8. Proceed to Stage 3.

## Stage 3: Place lunch, travel, break, and work

1. Place one `Eat lunch` action lasting exactly one hour, starting no earlier
   than 11:00 and ending no later than 14:00.
2. Group all `transport:car` tasks into one contiguous trip when deadlines,
   locations, and fixed commitments permit.
3. Reserve 30 minutes immediately before the car-task group and 30 minutes
   immediately after it.
4. Use 15-minute transitions between car tasks when slack permits without
   splitting the group into separate trips.
5. Place the afternoon break immediately after the car trip when one occurs.
6. Otherwise place the afternoon break after the last afternoon fixed event.
7. When neither condition applies, place the afternoon break near 16:00.
8. Make the afternoon break two hours when slack permits and reduce it toward
   one hour only as needed to fit higher-urgency work.
9. Sort flexible work by descending Taskwarrior urgency.
10. Place each flexible task in the earliest available interval that can contain
   its full estimate and ends no later than 18:00.
11. Leave 15 minutes unallocated between adjacent non-car items whenever slack
   permits.
12. Treat lunch or the afternoon break as sufficient separation from an
   immediately adjacent item.
13. Never move or resize a `+fixed` task to create capacity.
14. If all work cannot fit, move the lowest-urgency non-carried flexible task to
   the earliest feasible later date before its due date.
15. Never roll carried work forward again without explicit user confirmation.
16. If only carried or fixed work remains and it cannot fit, report the conflict
   and request a priority or deadline decision.
17. Recompute until no interval overlaps and proceed to Stage 4.

## Stage 4: Write the daily schedule

1. Remove pending `+managed +schedule` support actions being replaced for the
   selected date.
2. Set every selected task, including carried work, to the selected date.
3. Write local 24-hour `HH:MM` values to `starttime` and `endtime`.
4. Write `transport` as exactly `car` or `no-car`.
5. Preserve real due dates, descriptions, estimates, locations, and unrelated
   fields.
6. Create `Eat lunch` and `Take afternoon break` as independent verb-first tasks
   tagged `+managed +schedule`.
7. Give both support actions the selected `scheduled` date, compact `est`,
   `transport:no-car`, and matching start and end times.
8. Represent downtime only as unallocated gaps; never create downtime tasks.
9. Do not assign artificial due dates to lunch or the afternoon break.
10. Record every created and modified task ID and proceed to Stage 5.

## Stage 5: Verify

1. Run `task schedule` and confirm chronological ordering by `starttime`.
2. Confirm the report uses the same columns as `task ready`.
3. Compare `task daily` and `task schedule` and confirm their pending task IDs
   are identical.
4. Confirm every selected task has a transport category and time window.
5. Confirm no carried managed task retains an earlier scheduled date.
6. Confirm fixed tasks match their original authoritative fields.
7. Confirm lunch lies wholly inside 11:00 through 14:00 and lasts one hour.
8. Confirm the afternoon break follows the placement rule and lasts one through
   two hours.
9. Confirm car tasks are contiguous with 30-minute outer transitions.
10. Confirm flexible work ends by 18:00.
11. Confirm there are no overlaps and 15-minute unallocated gaps exist where
   feasible.
12. Fix violations and repeat Stage 5.

# Scheduling Guidelines

## Priority

- Use Taskwarrior's numeric urgency as the priority number.
- Place higher urgency earlier among flexible tasks.
- Fixed times override urgency ordering because they cannot move.
- Move lower-urgency non-carried work first when the day overflows.
- Keep carried work on the selected day unless the user explicitly moves it.

## Time semantics

- `scheduled` identifies the day of action.
- `starttime` and `endtime` define the local time interval.
- `due` remains the real deadline and must never be replaced by a time-block end.
- A zero-duration action may use identical start and end times.

## Transportation

- `transport:car` means the action belongs to the car errand trip.
- `transport:no-car` means it does not require the car trip.
- Do not infer that a location alone requires a car when transportation is
  ambiguous.
- Do not schedule an impossible car trip when the user lacks transportation.

## Ownership

- Modify only `+managed` tasks.
- Treat `+fixed` tasks as immutable schedule anchors.
- Tag generated lunch and afternoon-break actions with `+schedule` so reruns can
  replace them safely.
- Never represent downtime gaps as Taskwarrior tasks.
