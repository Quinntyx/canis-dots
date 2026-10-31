# Scheduling preferences — classified rulebook

Source: chronological extraction of omn-assistant sessions (Aug 24–Oct 6 2026),
deduped to 324 unique preference-bearing user messages, refined through a
3-round questionnaire (Oct 6 2026). Full chronological draft with supersession
history: /tmp/route-week/preferences-draft.md (session artifacts may be wiped;
the canonical copy of THIS file lives with the solver).

Layers:
- **HARD** — CP-SAT constraint. Violation = infeasible, solver must retry.
- **SOFT** — CP-SAT objective term (weighted; fuzzed per candidate). Trade-offs
  are legal; the agent judges the final pick.
- **PREF** — NOT in CP-SAT. Agent-side rules used when staging and when picking
  among the candidate schedules.

Solver reads `[hard]`/`[solver]`/`[weights]` from `prefs.toml` (same dir).
This file documents intent; prefs.toml is the machine truth the solver reads.

## HARD (constraints)

1. **Morning boundary** — no assignment/work before the first class on class
   days; no work before ~10:15 on free days. Cooking + breakfast always exempt.
   (R1-Q1b; the Oct 6 violation that triggered this list.)
2. **Daily stop** — hard 22:00 America/Chicago cutoff every night, including
   deadline days. No late-night overflow. Permanent user rule 2026-10-09,
   superseding the former 23:00 sleep floor.
3. **Meals** — required, never skipped: fresh-cooked 1h each (R2-Q2b, R3-Q1a).
   Crush valve: when 1h meals make the week provably INFEASIBLE, lunch/dinner
   may compress to 45m — still required, and every candidate built this way is
   flagged `crush=true` and disclosed to the user. Off-switch:
   `crush_allowed = false` in prefs.toml.
4. **Break** — floor 30m/day, never zero; 1–2h on free days (R1-Q5a). Shrinks
   before lab hours or assignments do (Oct 2: breaks rank below lab time).
5. **Piano** — ≥4 sessions/week, 30–60m each (1h preferred), max 1h straight,
   never directly after the Friday lesson (R1-Q3a).
6. **Lab (Prof. Jee)** — 6h/week across any 3 weekdays, maximize Wednesday
   (already on campus for the meeting); blocks ≥2h (R2-Q3); ≥1h of lab before
   the weekly meeting; the meeting itself can never be missed.
7. **Deadlines** — assignment deadline minutes are hard (assignment_late is a
   solver failure); finish by the earlier of the academic deadline and the
   daily 22:00 cutoff. Before-class requirements remain binding; the cutoff
   never postpones them.
8. **Canvas data** — due dates authoritative; 11:59 PM same-day convention
   (00:00 belongs to the previous day).
9. **Travel time** — reserved around every location change: 10m same building,
   20m same campus, 30m off-campus. Travel <1h is never its own item; ≥1h
   travel (packed day-trip) gets its own block. No phantom walk-home — travel
   happens only when the next block is actually elsewhere.
10. **Venue rules** — between classes: SU Starbucks by default, never a vague
    "near room X"; Tu/Th exception: go home for lunch (cooking). Work at home
    is located "At home"; Teams/online events still get a physical location.
11. **Chunking** — pieces ≥1h (lab ≥2h); a 4h+ task prefers one day with
    adjacent ~2h chunks (R2-Q5a) over cross-day splits; same-task chunks stay
    ordered; Quinncia-style indivisible items have `chunks=1` (one sitting).
12. **Errands** — grocery + laundry scheduled every weekend, Sat or Sun,
    solver's choice (R1-Q4c); car errands grouped into one trip; no car to
    campus (walk) unless about to be late.
13. **Swim** — 3h block, strongly prefer Wednesday after lab (natatorium is 5m
    from ECSS); move only if a +fixed item or assignment blocks Wednesday
    (R2-Q4). Before dinner, never after.
14. **Weekend work** — none unless a deadline forces it (weekend minutes are a
    soft penalty, errands exempt); assignments front-loaded Mon–Fri.
15. **Completeness** — once a week is scheduled, every `+fixed` event is timed
    (no untimed fixed stragglers); completed +fixed blocks keep their window
    and are never overlapped; completed non-fixed blocks free their time.
18. **Day-attached flexible work** (permanent user rule 2026-10-19) —
    flexible (non-fixed) work is NEVER time-blocked. It is attached to a day:
    `scheduled` date + `est` + `+managed` (+`todo` refs), no
    `starttime`/`endtime`, no `location`/`transport`/`travel` unless the item
    is venue-bound (lab blocks keep `ECSS 3.226 (Prof. Jee's lab)`; car
    errands keep their venue). Only `+fixed` events and meal/support blocks
    carry clock times. gcal-sync renders flexible items as ◑ all-day
    previews. Day capacity math is unchanged: the day's est sum (fixed +
    flexible + support) must still fit the budget — the user executes the
    pool in any order.
    EXCEPTION (user rule 2026-10-19, later the same day): trip-requiring
    tasks (post office, package pickup, venue errands, driving) DO get real
    time blocks — `starttime`/`endtime` + `location` + `transport` +
    `travel` — like `+fixed` items, while staying `+managed` and movable.
    A trip's cost is the travel; the block keeps it visible and car errands
    groupable. Verify venue hours before placing.
16. **Block cohesion** — a block's title matches its todo list exactly
    (glance-readable in gcal); due-tomorrow items get their own block; blocks
    per day capped.

17. **Assignment budget** — exactly 120 minutes TOTAL per assignment across
    all its blocks. Permanent user rule 2026-10-09, replacing historical
    estimates unless the user overrides it. This is not a minimum block size
    or a single-sitting requirement; normal chunking and independently stated
    indivisibility constraints still apply.

## SOFT (weighted objectives; fuzzed per candidate)

- weekend homework minutes (weight `weekend_homework`)
- earliness of work starts (`earliness`) — earlier-in-day preference
- evening overflow: work minutes past 20:00 (`late_evening`) — evenings are the
  valve; prefer daytime, evenings only when squished (R1-Q2c)
- fragmentation: extra days spanned per item (`fragmentation`)
- lab-on-Wednesday minutes (`lab_wednesday`)
- total travel minutes (`travel`)
- meal lateness vs window start (fixed weight `meal_lateness`)
- same-type/same-context grouping: reward literal back-to-back chunks of the
  same task; a meal legitimately breaks context between two chunks
- break placement: after the last fixed item of the day, before evening work
- afternoon-break length on free days (toward the hi bound when nothing is
  crushed)

## PREF (agent-side; used to pick among candidates and while staging)

- MTG nights: stream is the last thing of the day; nothing after.
- Piano goes in the afternoon, after the afternoon break, never between
  classes (walk-back).
- Consolidate eating out / errands onto car trips.
- Hackathon/workshop-type fillers only if the week stays free enough (no
  squished breaks, no sleep loss).
- "With person X" → check that person's omn schedule first.
- Reports: derive from a fresh `task schedule` run; never paste the table
  (user runs `sch`); weekly brief covers the whole week with due dates so the
  user can veto placements.
- Show the current schedule before asking the user to move anything.
- Grade <90% → 2h review block that week; grades always surfaced + logged;
  flag anything ungraded >2 weeks.
- User-veto workflow: solver output → gcal push → user vetoes in calendar;
  agent never hand-edits solver output in Taskwarrior — rerun with new
  constraints instead.

## Candidate generation (the fuzzing contract)

Per candidate: fuzz SOFT weights (multiplicative noise around `[weights]`
base), solve phase 1 (maximize priority under HARD constraints) then phase 2
(minimize weighted SOFT sum) with reduced budgets from `[solver]`
(`phase1_seconds`/`phase2_seconds` — deliberately small; many cheap candidates
beat one over-optimized schedule). Agent then picks the candidate that best
satisfies the PREF list and discloses per-candidate compromises + any
`crush=true` flags.

## Timing discipline (reaffirmed 2026-10-07)

- Deletion operation semantics (user-set contract, 2026-10-07): agent-side
  cleanup uses `agent-task-del` (delete hooks-off + purge — task gone
  entirely, event removed, no trace); `task delete` is the user's operation
  (or the agent's at their explicit request) — it leaves a deleted record,
  and gcal-sync recolors the event purple (✗ grape). Never convert one into
  the other.
- A deleted task is intentional. NEVER restore or re-create it, and never ask
  about it. (Violated 2026-10-07: wrongly re-created the CS 3341 lecture the
  user had deleted on purpose.)
- Before any restore/recreate/schedule decision, run `date` fresh and compare
  against the task's time window — a "scheduled today" block may already be
  hours in the past by the time the user prompts. Do not infer clock state
  from an earlier turn's output.
