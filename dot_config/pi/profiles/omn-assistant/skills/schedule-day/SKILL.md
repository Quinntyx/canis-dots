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
- Nothing (except meals) starts before the later of 10:00 and the end of the
  day's first fixed class plus its travel buffer; mornings are flex time.
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
10. If scheduling a future date without a supplied day start, use the morning
    boundary (the later of 10:00 and that day's first class end plus its
    travel buffer), never 08:00.
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
7a. Give every staged task a `location` — real places like lecture rooms,
    `ECSS 3.226` (Prof. Jee's lab), `SU Starbucks` (the usual hangout between
    classes), or `At home` (the dorm) — so transit can be computed from place
    to place. An untimed task stays location-free until it gets a time block.
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
6. Book nothing (except meals) before the later of 10:00 and the end of the
   day's first fixed class plus its travel buffer; the pre-boundary morning
   stays unallocated as flex time.
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
15. Leave the location-based transit gap (0/10/20/30 minutes) unallocated
    between adjacent non-car, non-class items whenever slack permits.
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

1. Run `task schedule` and confirm chronological ordering by `starttime`. The
   report is unscoped by design (past days stay visible so the user can mark
   carried work complete); the invariant is that no *pending* task may sit on
   a past `scheduled` date — reschedule those forward before reporting, and
   let the linter's `stale-scheduling` ERROR enforce it. Never hide the
   problem by narrowing the report.
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
10. Confirm location-based transit buffers surround every fixed class block
    (0/10/20/30 minutes per the Travel time rules).
11. Confirm nothing except meals starts before the later of 10:00 and the end
    of the day's first fixed class plus its travel buffer (morning boundary).
12. Confirm same-type flexible tasks form contiguous clusters.
13. Confirm flexible work ends by 18:00.
14. Confirm there are no overlaps and unallocated gaps exist where feasible,
    using 15 minutes between ordinary items and 30 minutes around class blocks
    and car trips.
15. Run the schedule linter for the day's week:
    `python3 ~/.config/pi/profiles/omn-assistant/bin/taskwarrior_lint.py --week <monday>`.
16. Triage every linter warning before touching anything: classify it as an
    expected exception the user asked for (explicit times, shifted meal
    blocks, deadline-forced weekend work, a waived break) or a genuine
    violation; fix the genuine ones and state the accepted exceptions in the
    reply.
17. Fix violations and repeat Stage 5.

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

- Compute transit from `location` to `location`, not from a flat estimate:
  **0 min** when neighboring blocks share the same place, **10 min** same
  building, **20 min** different buildings both on campus, **30 min** whenever
  a leg moves off campus. The dorm (`At home`) is off campus for everything.
- Track the home↔campus commute cost per task in the string UDA `travel` using
  compact minute values such as `30m`; leave it empty on tasks that require no
  travel.
- Represent travel only as unallocated buffer time around task windows; never
  create travel tasks and never book other work into a class block's buffers.
- Replace the location-based estimate with measured travel times, such as a
  Google Maps API lookup, only when the user explicitly asks for that upgrade.
- Default campus commutes to walking even though the user owns a parking
  permit; the user walks for the exercise. Reserve driving to campus for
  imminent-late situations, and treat it as the exception rather than the
  default.

## Weekends
- Do not place assignment work on Saturdays or Sundays unless the deadline is
  that weekend and no weekday capacity remains; weekends are for rest,
  personal projects, going out, and events.

## Meals
- The user cooks every meal themselves: place an hour of cooking immediately
  before breakfast (`Cook breakfast`), so breakfast defaults to 07:30-08:15;
  on mornings with an 08:30 class use cook 06:15-07:15 and breakfast
  07:15-08:00 so the commute still fits.
- Dinner defaults to 18:00-18:45 and stays within 17:00-20:00.
- Shift the whole meal block as one unit when a fixed commitment requires;
  tag generated meal actions with `+schedule` like lunch.

## Venue hours
- Before scheduling an action that depends on a place being open, verify that
  place's hours for the target date by web search; never book a closed venue
  (example: bank branches on weekends).

## Morning boundary

- Do not schedule anything before the later of 10:00 and the end of the day's
  first fixed class plus its travel buffer; mornings are flex time. This is
  provisional while the user's sleep schedule settles and may change.
- Only meals (breakfast) and the class blocks themselves may live in the
  pre-boundary morning.
- Work in the same building as the day's first class may start at the
  same-building transit offset after that class ends.
- Venue-forced exceptions (a place that closes early) may start earlier; say
  so explicitly when applying one.

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

## Early completion and reallocation

- When the user completes a task in less time than its scheduled block, first
  edit the completed task to the actual usage — shorten `starttime`, `endtime`,
  and `est` to what the work really took — then allocate the freed remainder to
  other work. The shortened `est` becomes the historical estimate for future
  planning (write it back to `meta.est` when the task came from an omn record).
- A completed `+fixed` block keeps its authoritative window and still anchors
  the schedule: never place pending work on top of it and never move it, even
  though it is complete. The freed time after an early-completed fixed block is
  only the slack that was scheduled around it.

## Between-class blocks

- A class-to-class gap is not automatically work time. Compute transit out of
  the first class and into the next one, and treat the remainder as the usable
  window.
- The default location for a between-class block is **SU Starbucks**. Never
  schedule work at a vague location such as "near room X", "(near
  classroom)", or "somewhere in <building>": the user cannot easily settle
  into work outside a classroom, and walks to the SU instead.
- A gap is work time only when the usable window can hold a whole piece — a
  single-part task, or one full hour of a split task. Anything shorter stays
  unallocated: the user walks to the SU and settles in rather than starting a
  piece that cannot finish.

## Split tasks

- Prefer one contiguous block on a later day over splitting a task across
  days. Split only when no single block fits before the deadline.
- Never break a multi-part task into a piece shorter than one hour.
- Name the pieces `Start <task>` and `Finish <task>` (with three pieces:
  `Start`, `Continue`, `Finish`) so the order is visible in the schedule, and
  keep them in that order across days.
- When a piece is moved or cancelled, re-plan the whole task instead of
  sliding that one block: find the task's other pieces, keep the total hours
  the same, re-divide, and rename the pieces to match the new division (see
  the reschedule skill).
- Prefer merging two pieces into one longer block over adding a third piece to
  fit the week. Pushing an unrelated deadline-free task to a later day, or
  into the following week, is the accepted cost of keeping a task whole.

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

## Scoped requests

- Do exactly what the user asked for; never reschedule or re-plan unrelated
  items on the side. Rescheduling is its own request.

## Ownership

- Modify only `+managed` tasks.
- Treat `+fixed` tasks as immutable schedule anchors.
- Tag generated lunch and afternoon-break actions with `+schedule` so reruns can
  replace them safely.
- Never represent downtime gaps as Taskwarrior tasks.
