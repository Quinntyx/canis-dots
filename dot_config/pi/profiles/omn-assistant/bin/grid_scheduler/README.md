# Grid week scheduler (`grid-week/v1`)

The default `../schedule_composer.py` now uses this engine. The previous interval
engine, including its day-binning prepass, is frozen at `../legacy/interval-v1/`
and runs only through `../schedule_composer_legacy.py`. Native specs and plans
are versioned; legacy interval specs/plans are deliberately not auto-converted.

## Pipeline

1. Read source facts and expand recurrence in ordinary Python.
2. Compile a 96-row × 7-column grid (672 wall-clock quarter-hours, Monday first).
   Prepaint sleep, fixed commitments, unavailable time and the sealed prefix.
   Exact event times remain in reservation overlays; only occupancy rounds out.
3. Z3 colors the remaining cells. It has Boolean cell-color variables and
   pseudo-Boolean cardinality rules, not item identities, interval start/end
   variables, modulo arithmetic, duration variables or chosen day buckets.
4. Python certifies item allocation within each semantic color's capacity.
   Lower/upper-bound flow handles totals and eligibility. Bounded exact packing
   enforces whole items and minimum piece lengths. It never silently drops required work.
5. A certified capacity shortage learns a necessary color-count restriction.
   A proved topology failure excludes that color's precise occupancy mask.
   These are sound counterexamples, not heuristic day assignments. A layout
   timeout is UNKNOWN, never INFEASIBLE.
6. Extract day-bounded runs and chronological, duration-pinned todo bullets.
   Reserved travel runs are named from their endpoints and following goal;
   they never receive academic item allocation or completion credit.
   Normally one semantic run becomes one block; split records at owner changes
   only when an item's eligibility/deadline does not cover the whole run.
7. Independently verify the grid and allocation again before publishing.

A semantic key may have physical variants for incompatible locations or transport.
For example, remote and in-person email cannot share one supposedly single-location
block. Item IDs remain Python-side todo identities, never solver colors. Grouping
uses omn `meta.color`, then `meta.activity_type`, then the existing topic; email
verbs supply an email default. Every todo retains its `[omn:<id>]` reference.

## Coloring rules

- Exactly one color per cell, including `free`; immutable cells are constants.
- Exact or minimum/maximum suffix counts per color; optional per-day counts.
- Half-open availability ranges and true per-item deadline cutoffs. Bare-date
  deadlines mean the end of the Chicago day. A whole quarter must finish by due.
- Day-bounded minimum/maximum run lengths and optional immediate predecessor.
- `travel` is a reserved color. Each activity has minimum `travel_before` and
  `travel_after` cell counts; neighboring activities share the larger demand,
  not a sum. FREE cells never count as travel; longer travel runs are allowed.
  Fixed-only and continuous multi-day visits retain these requirements without
  inventing a midnight arrival or departure.
- Optional quantities marked `prefer_maximum` are maximized first (the afternoon
  break defaults to 2h when feasible, with a 1h hard minimum). Then optimization
  minimizes fragmented runs and separate car outings, then reserved travel-cell
  count, then the sum of work-cell positions to pull work earlier. Car clustering is a preference, not a false
  ban on unavoidable trips on separate days. Objective probes
  are never locked as hard limits. A feasible incumbent survives optimization
  timeout and is labeled approximate. This remains an NP-hard coloring problem;
  a small grid does not guarantee low latency on every workload.

The live compiler takes exact/ranged estimates from `meta.est`, `meta.min_est`
and `meta.max_est`, plus existing unlock, day, hour, recurrence and location data.
Exact estimates/minima round up to quarters; explicit hard maxima and
availability round inward. Empty representable ranges are refused, not widened.
Notes expose rounding.
Assignments are weekday-only unless `meta.weekend_allowed` is explicitly true.
Default work availability is 08:00–24:00; the grid also prepaints 00:00–06:00 sleep.
Unknown source estimates block publication instead of accepting an arbitrary legacy
2h default. Small (at most 2h) live requirements are whole; split assignment pieces
are at least 1h. Support colors have daily counts, one contiguous run per day,
cooking immediately before breakfast, and a shared daily dinner start. Completed
or intentionally removed support actions are not recreated. A partly elapsed
support window still carries its demand; elapsed time is not evidence of completion.
A multi-day away commitment can absorb a whole meal within its window, but travel
blocking a required meal is an explicit infeasibility, not permission to skip it.

Structured `meta.daily_est`, `meta.daily_min_est`, `meta.daily_max_est` maps
(weekday `0`–`6` → durations) expand to Python item occurrences sharing a semantic
color. Their todo references retain the parent omn identity. `meta.open_hours`
(day/date → pairs of opening/closing times) intersects availability; `requires_open`
without researched hours blocks. Research and provenance remain caller responsibilities.
`week_overrides[YYYY-MM-DD]`, `target_week`, recurrence cancellations, fixed-event
identity matching, minimum travel requirements and source-registration mismatches are compiled
without changing stored defaults. Existing imperative fixed registrations for a
cancelled occurrence are surfaced as blockers, never silently deleted.

Dated meal/break exceptions belong in `meta.support_overrides` on a user-authored
record, for example `{"2026-10-02": {"break": {"waived": true}, "breakfast":
{"skipped": true}, "lunch": {"hours": "10:15-11:15"}}}`. Valid names are `cook`,
`breakfast`, `lunch`, `break`, and `dinner`; only `waived`, `skipped`, and `hours`
are supported. These affect one calendar date, never recurrence defaults or
completion credit. Conflicting records or malformed rules fail closed.

An explicitly identified Canvas in-class assessment can carry
`meta.in_class_assessment_for: "<fixed-event omn id>"`. Compilation validates an
active, uncancelled, non-recurring event with an end exactly matching the Canvas
deadline. That occurrence covers the exam time, not additional flexible prep;
the raw assessment remains real, and no completion is inferred. Missing or
inconsistent links fail closed.

### Reserved travel metadata

A real destination event, not a separate "Drive to …" event, owns travel:

```json
{"meta": {"location": "San Antonio, Texas", "travel_time": {
  "before": "5h", "after": "5h", "mode": "car", "origin": "At home"
}}}
```

Durations round upward to cells; integer values are already cell counts. Five
hours is 20 cells before and 20 after. `mode` is `car` or `no-car`. The Python
renderer derives `Drive to Rowdy Hacks`, `Drive home`, or walking names and
explicit origin → destination locations. Reserved travel bridges car outings
without consuming their FREE-gap allowance, and never credits homework.

Positive legacy pairwise `gaps` and reservation FREE buffers are rejected for new specs. The historical
reader alone verifies old FREE-gap certificates for copying a sealed prefix;
`source=history` cannot be solved or published. No FREE-gap constraints remain
in the Z3 model.

Old route records may be archived as inactive notes with
`meta.travel_replaced_by={"event": "parent-id", "side": "before"}` (or `after`).
`--replace-travel` is the explicit publication opt-in: only exact pending,
owned, future legacy trips linked to that parent's declared duration can be
retired. Completed/unmanaged/prefix trips, unrelated fixed events, and changed
snapshots remain protected. Archiving a note does not edit Taskwarrior.

Dated `support_overrides` also accept a quarter-hour `duration` and an
`independent_start` exception to the normal shared dinner start. Whole blocks
move for fixed commitments; these exceptions never alter the standing pattern.
The cell model includes a necessary contiguous-color patch for each indivisible
item, but Python remains responsible for disjoint allocation.

## Commands

```sh
# Read-only planning from current omn + Taskwarrior facts.
../schedule_composer.py plan --week 2026-10-05 --out plan.json
../schedule_composer.py show --plan plan.json

# Preview only; confirmation is separate.
../schedule_composer.py apply --plan plan.json
../schedule_composer.py apply --plan plan.json --yes
# Explicitly migrate exact legacy trip registrations after approving the plan.
../schedule_composer.py apply --plan plan.json --yes --replace-travel

# Midweek: seal the prior coloring through the current system time.
../schedule_composer.py plan --week 2026-10-05 --previous plan.json --out revised.json

# Lossless native schema seam; spec plans cannot be published to live tasks.
../schedule_composer.py plan --spec fixture.json --out test-plan.json
../schedule_composer.py plan --spec fixture.json --previous test-plan.json \
  --from-minute 4501 --out revised-test.json
```

`--timeout-ms` is an overall coloring/layout/optimization budget (default 10000).
`--no-optimize` asks for the first certifiable coloring. The JSON preserves the
problem, flat 672-cell grid, display matrix, layout owners, runs and decoded
records. There is one certified candidate per invocation, not legacy soft-bucket
candidate enumeration. `--candidates`, `--candidate`, `soft` and `unsat_core` are
not part of this new CLI.

## Midweek and completion semantics

The current fractional minute rounds **up**, including seconds. Cells before
that boundary are copied exactly from the prior grid; the suffix is cleared and
recolored. Previous versions and their records are retained in `sealed_history`.
Historical colors whose sources disappeared remain unavailable palette entries.
With no prior grid, elapsed time is unavailable, not invented completed work.

Remaining demand comes from source facts and explicitly completed Taskwarrior
work. Calendar colors are never completion credit. Completed todos' pins split
credit by source; multiple unpinned references are refused as ambiguous. Existing
completed, deleted, fixed and unmanaged actions are not restored or modified.
Prior pending-action snapshots detect intentional removals. Their source identities
are omitted, not recreated or treated as completed; this is conservative when a
removed block contained several sources. Successful CLI publication atomically
records replacement UUIDs in the plan's `task_receipt`, so the engine's own old-block
deletions do not look like user cancellations. Cancellation state persists across
that week's revisions. Deletions before the first recorded snapshot cannot be
inferred reliably from unchanged omn facts.

## Publication safety and current boundaries

- Planning never writes omn, Taskwarrior or Google Calendar. Source refresh and
  mail triage remain the caller's responsibility.
- Apply defaults to a dry run. Live source fingerprints must still match and
  no new block may begin in elapsed time. Native spec publication is refused.
  The production Python apply entrypoint enforces source fingerprints and spec
  refusal too; injected fake transports are an explicit testing seam.
- Only pending `+managed` blocks bearing this week's `+grid-YYYY-MM-DD` tag are
  replaceable. `--replace-legacy` explicitly adopts this week's pending composer
  suffix blocks; ordinary plans do not silently take them over.
  `--replace-carried` explicitly retires covered pending owned blocks earlier
  in this week, including obsolete plans crossing the prefix. All their source
  identities must be represented; mixed/unresolved bullets are not discarded.
- Completed/unmanaged tasks and other weeks are always protected. Fixed tasks
  are protected except exact future legacy trips explicitly authorized via
  `--replace-travel` and linked to a certified parent visit. Without
  explicit carry-forward, prefix blocks remain protected and crossing-prefix
  replacement is refused. Retiring a pending plan never rewrites the sealed
  coloring or claims actual completion. No recurrence templates are created.
- Add and round-trip verify new records (including due dates) before deleting
  old blocks by UUID. Failed creation rolls back new records; failed old deletion
  reports possible duplicates rather than pretending the transaction succeeded.
- Fixed events retain exact reservation overlays. Previously unstaged attendance
  records are synthesized in Python with authoritative times/location and ordinary
  `+fixed` tags; existing matched registrations are not duplicated. Publication
  checks exact attendance records against protected tasks as well as work runs.
- Native JSON is the complete coloring-rule interface. The live adapter reuses
  legacy source parsing and transport helpers, **not** the interval model,
  heuristic support placement, legacy decoding or legacy apply policy. Not every
  prose/artifact policy is automatically compiled. Structured venue-hour and car
  grouping rules are supported, but never claim researched opening hours, opaque
  people-busy notes, or unrecorded weekly-load/completion facts merely from grid SAT.
- A 96×7 grid is ambiguous during DST transition weeks. This engine refuses
  those weeks explicitly until a wall-clock policy is specified.

## Verification

From the parent `bin` directory:

```sh
uv run --with z3-solver --with pytest pytest -q \
  tests/test_grid_scheduler.py tests/test_grid_edges.py \
  tests/test_grid_integration.py tests/test_grid_policies.py \
  tests/test_grid_support_overrides.py tests/test_grid_assessment_links.py \
  tests/test_grid_carry_publication.py tests/test_grid_travel.py \
  tests/test_grid_travel_migration.py tests/test_grid_history_readback.py \
  tests/test_taskwarrior_lint.py
uv run --with ruff ruff check grid_scheduler tests/test_grid*.py
```

The 113 grid tests plus 10 linter tests (123 total) use fake stores and Taskwarrior
transports; they do not change live data. Linter regressions cover exclusive
24:00 endpoints, date-only recurrence carry windows, and fixed-assessment links
that still fail coverage when the actual exam registration is absent or wrong.
Legacy fixed registrations without todo references require an exact title,
location, and interval match; a declared assessment link alone is not coverage.
The frozen legacy suite still has its existing `test_one_block_covers_many_requirements`
grouping failure (two blocks instead of one); the snapshot's 14 manifest hashes
are unchanged. It is not a failure of this engine, and was not patched here.
Exhaustive small instances cross-check flow and strict packing. Regression tests
cover reserved/shared travel, deleted-trip protection, legacy readback, deadline
cuts, fixed rounding overlays, exact seconds, multi-day attendance, history,
optional/ranged amounts, indivisibility, minimum pieces, chronological pins,
certificate tampering, CLI version checks, rollback and ownership protections.
