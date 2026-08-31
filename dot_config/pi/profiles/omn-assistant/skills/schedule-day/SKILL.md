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
- String UDAs named `starttime`, `endtime`, `location`, `transport`, and
  `travel`; create `travel` before scheduling when it is unavailable.
- Fixed commitments tagged `+fixed` with authoritative time windows.
- The selected date, defaulting to today in America/Chicago.
- Current transportation availability and any user-supplied day-start constraint.
- Any user-declared explicit times, which act as authoritative anchors.

## Output Contract

- Every selected actionable task has a non-overlapping `starttime` and `endtime`.
- Fixed tasks retain their authoritative date, time, estimate, and location.
- Every travel-bearing task carries a compact `travel` duration estimate, and
  travel buffers surround class blocks and car trips as unallocated gaps.
- No assignment work starts before the later of 10:00 and the end of the day's
  first fixed class plus its travel buffer; the pre-class morning holds only
  personal-project work or unallocated downtime.
- Flexible work ends by 18:00.
- Higher-urgency flexible tasks occupy earlier available work periods.
- Every selected task has `transport` set to `car` or `no-car`.
- Car tasks form one contiguous errand trip whenever constraints allow.
- Flexible tasks of the same type or working environment form contiguous blocks
  whenever constraints allow, even at the cost of extra dead time.
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
9. If scheduling today, set the earliest planning cursor to the later of 10:00
   or the current time rounded up to the next 15-minute boundary; the user
   sleeps in until roughly 10:00 or their first class, so nothing is scheduled
   before this cursor.
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
7. Set `travel` on every task whose execution requires travel: `30m` by default
   for class attendance and car errands, extended in conversation when the user
   supplies a better figure.
8. Mark each flexible task as assignment work or personal-project work, using
   the task's origin (course assignment versus side project) when tags do not
   already distinguish them.
9. Reserve all fixed time intervals before placing flexible work.
10. Treat user-declared explicit times as authoritative anchors: apply them
    exactly as given and do not insert travel buffers, transition gaps, or
    placement adjustments around their boundaries, even when they violate the
    standard buffer or placement rules.
11. Proceed to Stage 3.

## Stage 3: Place lunch, travel, break, and work

1. Place one `Eat lunch` action lasting exactly one hour, starting no earlier
   than 11:00 and ending no later than 14:00.
2. Group all `transport:car` tasks into one contiguous trip when deadlines,
   locations, and fixed commitments permit.
3. Reserve 30 minutes immediately before the car-task group and 30 minutes
   immediately after it.
4. Use 15-minute transitions between car tasks when slack permits without
   splitting the group into separate trips.
5. Reserve at least 30 minutes of unallocated travel buffer immediately before
   and immediately after every fixed class block; between consecutive class
   blocks, reserve one 30-minute buffer instead of two.
6. Never book assignment work before the later of 10:00 and the end of the
   day's first fixed class plus its travel buffer; place only personal-project
   work or unallocated downtime in that morning window.
7. Place the afternoon break immediately after the car trip when one occurs.
8. Otherwise place the afternoon break after the last afternoon fixed event.
9. When neither condition applies, place the afternoon break near 16:00.
10. Make the afternoon break two hours when slack permits and reduce it toward
    one hour only as needed to fit higher-urgency work.
11. Cluster the remaining flexible tasks by type and working environment, such
    as all email tasks into one block and same-project work into one block.
12. Place each cluster as one contiguous span, accepting extra dead time over
    interleaving task types across the day.
13. Order clusters by their highest-urgency member; order tasks inside a
    cluster by descending Taskwarrior urgency.
14. Place each cluster in the earliest available interval that can contain it
    and ends no later than 18:00.
15. Leave 15 minutes unallocated between adjacent non-car, non-class items
    whenever slack permits.
16. Treat lunch, the afternoon break, or a travel buffer as sufficient
    separation from an immediately adjacent item.
17. Never move or resize a `+fixed` task to create capacity.
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
4. Confirm every selected task has a transport category, a time window, and a
   `travel` value when travel is required.
5. Confirm no carried managed task retains an earlier scheduled date.
6. Confirm fixed tasks match their original authoritative fields.
7. Confirm lunch lies wholly inside 11:00 through 14:00 and lasts one hour.
8. Confirm the afternoon break follows the placement rule and lasts one through
   two hours.
9. Confirm car tasks are contiguous with 30-minute outer transitions.
10. Confirm 30-minute travel buffers surround every fixed class block.
11. Confirm no assignment work starts before the later of 10:00 and the end of
    the day's first fixed class plus its travel buffer.
12. Confirm same-type flexible tasks form contiguous clusters.
13. Confirm flexible work ends by 18:00.
14. Confirm there are no overlaps and unallocated gaps exist where feasible,
    using 15 minutes between ordinary items and 30 minutes around class blocks
    and car trips.
15. Fix violations and repeat Stage 5.

# Scheduling Guidelines

## Priority

- Use Taskwarrior's numeric urgency as the priority number.
- Order task clusters by their highest-urgency member and place higher urgency
  earlier among flexible tasks.
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

## Travel time

- Track travel cost per task in the string UDA `travel` using compact minute
  values such as `30m`; leave it empty on tasks that require no travel.
- Default `travel` to `30m` for class attendance, because classes require
  walking, and for car errands; extend it in conversation when the user
  supplies a better estimate.
- Represent travel only as unallocated buffer time around task windows; never
  create travel tasks and never book other work into a class block's buffers.
- Replace the flat 30-minute estimate with measured travel times, such as a
  Google Maps API lookup, only when the user explicitly asks for that upgrade.

## Assignment start boundary

- Never schedule assignment work before the later of 10:00 and the end of the
  day's first fixed class plus its travel buffer; the user sleeps in until
  roughly then.
- Fill the pre-boundary morning only with personal-project work or leave it
  unallocated as downtime.
- Treat this boundary as the current default; revise it in conversation when
  the user's sleep schedule changes.

## Explicit user times

- When the user supplies explicit start and end times for an event or work
  block, apply them exactly as declared.
- Do not pad user-declared boundaries with travel buffers or transition gaps
  and do not reshuffle their contents, even when they violate the standard
  buffer or placement rules.
- Treat only the intervals the user declared as authoritative; schedule
  surrounding flexible work normally around them.

## Grouping

- Group flexible tasks of the same type or working environment into one
  contiguous block rather than scattering them across the day to fill space.
- Prefer a suboptimal space fit that keeps same-type tasks adjacent over an
  optimal fit that interleaves task types.
- Treat this as a generalization of car-trip grouping: email tasks form one
  email block, errands form the car trip, and same-project work stays adjacent.

## Recurrence artifacts

- Before placing a record's tasks, read its `artifacts.rrule` artifact when one
  exists; the file is named by replacing the record id's colons with
  underscores and appending `_rrule.md`.
- Honor the sequencing and placement directives in that artifact, such as a
  preferred slot directly after the afternoon break, when they do not collide
  with fixed commitments.
- When the artifact's constraints cannot be satisfied, report the specific
  conflict rather than silently deviating.

## People schedules

- When a task or session names another person, look up that person in omn
  (`type:person` records, search by name in `meta.name` or the title) and avoid
  placing the shared block inside any `meta.busy` interval for that weekday.
- Treat `times_approximate` busy blocks with a 15-minute margin on each side.
- If no person record exists for the named person, say so and ask for their
  schedule instead of guessing at their availability.

## Ownership

- Modify only `+managed` tasks.
- Treat `+fixed` tasks as immutable schedule anchors.
- Tag generated lunch and afternoon-break actions with `+schedule` so reruns can
  replace them safely.
- Never represent downtime gaps as Taskwarrior tasks.
