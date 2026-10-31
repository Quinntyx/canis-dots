# Route Scheduler — design document

Status: approved design 2026-10-06, implementation not started.
Replaces: `grid_scheduler/` (z3 cell-painting engine) after migration.
Unchanged: `scheduler/sources.py` ingestion, omn store, Taskwarrior apply
layer, `gcal-sync`, decode/export — all solver-agnostic.

## Goal

A scheduling engine usable for a decade with **zero code changes** — all
semantics live in omn records; the engine is a stable interpreter of a small
declarative constraint vocabulary. Rejected alternative: incrementally
patching the z3 grid engine (this week demonstrated that ordinal/relational
semantics do not fit the cell-painting abstraction).

## Core model

Each **day** is a single-vehicle route (circuit) through locations.

- **Node** = doing something at a location for a duration.
- **Edge (arc)** = movement between consecutive nodes; length from the
  routing table (walk/drive times, via-home rules). Travel is an edge
  property, never a node.
- **Depot** = day start/end (home). Overnight trips (RowdyHacks-style) =
  days whose depot is elsewhere.
- **Fixed nodes**: classes, meetings, events — mandatory, exact windows.
- **Support nodes**: meals, breaks — **squeezable**: optional (presence
  literal), duration range, ordering relations (e.g. break after last fixed
  node of the day, before work; dinner window 17:00–20:15).
- **Work chunks**: item of est E hours → `n = ceil(E / 2h)` optional nodes,
  each with **variable size ∈ [min_piece, 2h]** (min_piece = 1h standing),
  plus a remainder chunk for exact totals (5h = 2h+2h+1h). Presence literals
  make chunks squeezable under deadline pressure.

Everything the user does is a node in omn — there are no "gaps" and no
interruption special cases.

## Constraints (the vocabulary)

| Type | Meaning | CP-SAT mechanism |
|---|---|---|
| `window` | node may start only within window | interval start domain |
| `exact` | fixed start/end (classes) | fixed interval |
| `presence` | optional node | optional interval var |
| `amount` | Σ chunk sizes ∈ [min, max] per item | linear over size vars |
| `order` | relational: `after_last_fixed_of_day`, `before: [work, dinner]`, `after: [...]` | conditional precedences (OnlyEnforceIf) |
| `travel` | arc length A→B per mode | circuit arc costs + transition constraints |
| `daily_cap` | max work minutes/runs per day | linear over presence/size |
| `lex_tier` | lexicographic priority tiers | staged optimization |

**Adjacency reward (literal back-to-back).** For each ordered pair of
same-item chunks on the same day: boolean `adjacent(A,B) ⟺ direct circuit
arc A→B` (no intervening node). Consecutive same-location nodes have
zero-length arcs, so adjacency ⟺ zero-gap continuation. Reward weight in the
objective. Meal/errand/task between chunks ⇒ no direct arc ⇒ no reward
(context lost). No exceptions, no judgment calls.

## Objectives (lexicographic tiers, each a staged CP-SAT solve)

1. **Feasibility**: all hard constraints, deadlines met.
2. **Priority tier** (user-set in omn): e.g. lab hours ≥ target beats break
   duration. This resolves priority inversions *in data*, not in code.
3. **Travel minimization**: total arc time (route efficiency is native —
   kills walk-home-and-back waste by construction).
4. **Adjacency rewards** (context switching).
5. **Fragmentation** (fewest work blocks; `prefer_fewer_runs` per group).
6. **Earliness / stability** vs previous week's schedule.

## Post-processing

- **Merge pass**: adjacent same-item chunks (zero gap) merge into one block.
  Provably safe: merged interval = union; NoOverlap/circuit/amount all hold.
- Travel arcs render as yellow calendar blocks ≥1h (sub-hour travel stays
  implicit, per 2026-10-06 policy note 1).

## omn schema additions (data, not code)

```
location            # node in the routing graph
route_edge          # (from, to, mode, minutes, via_home_ok)  — routing table
policy:squeezable   # {after, before, duration_min/max, priority}
policy:lex_tier     # named priority tiers, ordering
item (existing)     # est/min/max/due/location/topic + chunk_cap, min_piece
```

Test for decade-readiness: a new special case must be a **new record**; only
a genuinely new constraint *type* justifies code.

## Migration plan

1. **Golden test**: this week's (2026-10-05) real data — both engines run,
   results compared for constraint satisfaction (not identical output).
2. Build engine core: day circuits, chunks, presence, lexicographic stages.
3. Port adapter: omn records → model (sources layer reused).
4. Port decode/apply: model output → Taskwarrior blocks (+merge pass).
5. Delete list (from grid engine): travel.py transfer/certificate machinery,
   run automata, idle/fragmentation PbLe tricks, same_start exception
   patches, support_overrides duration/independent_start special cases.
6. Keep grid engine frozen as fallback until the route engine passes a full
   live week end-to-end (plan → apply → gcal-sync).

## Known risks

- Multi-day car trips (depot away from home) — expressible, fiddly; defer to
  v1.1 if needed.
- Circuit scale: ~15–20 nodes/day × 7 days — well within CP-SAT comfort.
- Chunk symmetry: 2–3 chunks/item; negligible.
- CP-SAT dependency: add `ortools` via uv; pin version.
