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
2. Read Taskwarrior's complete pending state after the refresh.
3. Compare every omn item dated anywhere within the current
   Monday-through-Sunday week against concrete Taskwarrior actions.
4. Never limit reconciliation to the resolved day, `today`, or `tomorrow`; an
   item later in the current week can require work on an earlier day.
5. Include fixed event occurrences in the comparison, not only deadline-bearing
   assignments.
6. Treat any newly discovered current-week item as a planning change even when
   its date differs from the requested day.
7. Reconsider the remaining week's action dates and estimates so work can be
   placed before the item's final day rather than deferred to its deadline.
8. Treat omn as durable source state and Taskwarrior as imperative actions; do
   not mirror facts as hierarchy or deadline-tracker tasks.
9. Avoid duplicates by matching source identity, description, date, deadline,
   and existing action coverage.
10. If any current-week item lacks an estimate or action date, load
   `plan-assignments` and proceed through its planning flow for the whole week.
11. If pending managed work is carried from an earlier day, load `reschedule`
   and proceed through its carried-work flow.
12. Do not stop after naming the skill; execute it until user input or approval
   is genuinely required by its contract.

### Determine whether a daily schedule is current

1. Read `task ready`, `task daily`, and `task schedule` after reconciliation.
2. A schedule exists only when every managed action ready for the resolved date
   has `starttime`, `endtime`, and `transport` populated.
3. Require all fixed events to retain their authoritative time and location.
4. Require lunch, the afternoon break, non-overlap, car-trip and same-type
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
8. When the verified schedule is current, publish it to Google Calendar by
   loading `gcal-sync` and following its procedure; a failed sync is reported
   as one status line and never blocks or replaces the final schedule table.

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
