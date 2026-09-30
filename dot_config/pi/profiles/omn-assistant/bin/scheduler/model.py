"""The Z3 model: first-class flexible blocks with per-requirement allocations.

Hard layer (all enforced, the important ones tracked by name so an UNSAT core
can name them):

* every active requirement's allocated minutes sum to at least its need;
* a block never allocates more minutes than its duration;
* a positive allocation implies the block is used, sits in the requirement's
  own cohesion group, and is fully inside its availability/deadline window;
* block start/duration live on a finite grid, never cross midnight, meet the
  min/max duration bounds, avoid every fixed interval, obey the per-day block
  cap, and every pair of used blocks is nonoverlapping;
* block symmetry is broken with a used prefix + ordered starts per group, and
  the total number of blocks is bounded for performance.

Soft layer (3 nonnegative buckets, plus an optional project/free-time bucket):
each bucket is probed with a small target ladder and the first satisfying
threshold is locked. No hard constraint is ever relaxed to reach a target, and
the buckets are never collapsed into one global score.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import z3

from .common import (
    MIN_ALLOC_MINUTES,
    MINUTES_PER_WEEK,
    ComposerConfig,
    WeekInput,
    transit_minutes,
    window_label,
)

# Soft tuning: each bucket is probed with a bounded bisection "target ladder".
# It starts from a known-satisfying value and walks down, remembering the best
# satisfying target; when the gap closes to half a grid step (or the probe
# budget runs out) the best target is locked. Variants are documented so a
# candidate's soft tuning is reproducible from the plan file alone.
LADDER_VARIANTS = [
    {"name": "ladder-a", "divisor": 4,
     "order": ["timing", "load", "cohesion", "project_free"]},
    {"name": "ladder-b", "divisor": 2,
     "order": ["timing", "cohesion", "load", "project_free"]},
    {"name": "ladder-c", "divisor": 8,
     "order": ["load", "timing", "cohesion", "project_free"]},
    {"name": "ladder-d", "divisor": 3,
     "order": ["timing", "load", "project_free", "cohesion"]},
]

MAX_LADDER_PROBES = 10

BUCKET_ORDER = ["timing", "load", "cohesion", "project_free"]


@dataclass
class Block:
    group_key: tuple
    req_indexes: list
    index: int = 0


@dataclass
class ModelData:
    week: WeekInput
    config: ComposerConfig
    requirements: list
    needs: list
    blocks: list
    solver: object
    used: dict
    start: dict
    dur: dict
    day: dict
    alloc: dict
    buckets: dict
    tracked: dict = field(default_factory=dict)
    blocks_of_req: dict = field(default_factory=dict)


def _sum(terms):
    return z3.Sum(terms) if terms else z3.IntVal(0)


def _assign_blocks(requirements, config: ComposerConfig):
    groups: dict = {}
    for index, requirement in enumerate(requirements):
        groups.setdefault(requirement.group_key, []).append(index)
    group_items = sorted(groups.items())

    needs = [max(req.required_minutes, MIN_ALLOC_MINUTES) for req in requirements]

    counts = {}
    for key, indexes in group_items:
        total = sum(needs[index] for index in indexes)
        base = max(1, math.ceil(total / config.max_block))
        for index in indexes:
            base = max(base, math.ceil(needs[index] / config.max_block))
        counts[key] = base
    total_base = sum(counts.values())
    target = max(config.max_blocks, total_base)
    slack_caps = {
        key: max(1, len(indexes) + config.group_block_slack)
        for key, indexes in group_items
    }
    remaining = target - total_base
    keys = [key for key, _ in group_items]
    while remaining > 0:
        progressed = False
        for key in keys:
            if remaining <= 0:
                break
            if counts[key] < slack_caps[key]:
                counts[key] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            break

    blocks: list = []
    for key, indexes in group_items:
        for _ in range(counts[key]):
            blocks.append(Block(group_key=key, req_indexes=list(indexes)))
    for position, block in enumerate(blocks):
        block.index = position
    return blocks, needs


def build_model(week: WeekInput, config: ComposerConfig) -> ModelData:
    requirements = week.requirements
    blocks, needs = _assign_blocks(requirements, config)
    step, min_block, max_block = config.step, config.min_block, config.max_block

    solver = z3.Solver()
    solver.set("timeout", config.solver_timeout_ms)

    used, start, dur, day, alloc = {}, {}, {}, {}, {}
    tracked: dict = {}
    blocks_of_req: dict = {index: [] for index in range(len(requirements))}

    def track(expression, name, text):
        solver.assert_and_track(expression, name)
        tracked[name] = text

    for block in blocks:
        b = block.index
        used[b] = z3.Bool(f"used_{b}")
        start[b] = z3.Int(f"start_{b}")
        dur[b] = z3.Int(f"dur_{b}")
        day[b] = z3.Int(f"day_{b}")
        alloc[b] = {r: z3.Int(f"alloc_{b}_{r}") for r in block.req_indexes}
        solver.add(start[b] >= 0, start[b] <= MINUTES_PER_WEEK - min_block)
        solver.add(dur[b] >= min_block, dur[b] <= max_block)
        solver.add(start[b] % step == 0, dur[b] % step == 0)
        solver.add(day[b] >= 0, day[b] <= 6)
        solver.add(start[b] >= day[b] * 1440, start[b] < (day[b] + 1) * 1440)
        solver.add(z3.Implies(
            used[b], start[b] % 1440 >= config.work_start_hour * 60))
        solver.add(z3.Implies(
            used[b], start[b] % 1440 + dur[b] <= config.work_end_hour * 60))
        for r, variable in alloc[b].items():
            solver.add(variable >= 0)
            solver.add(variable <= needs[r])
            blocks_of_req[r].append(b)
        solver.add(used[b] == z3.Or([alloc[b][r] > 0 for r in block.req_indexes]))
        solver.add(z3.Implies(
            z3.Not(used[b]),
            z3.And(start[b] == 0, dur[b] == min_block, day[b] == 0),
        ))
        solver.add(_sum(list(alloc[b].values())) <= dur[b])

    # Symmetry: within a group, used blocks form a prefix ordered by start.
    for indexes in _grouped_blocks(blocks).values():
        group = [block.index for block in indexes]
        for first, second in itertools.pairwise(group):
            solver.add(z3.Implies(
                used[second], z3.And(used[first], start[first] <= start[second])))

    # Nonoverlap plus the standing location-based transit gap for every pair
    # of used blocks. Same-place blocks may touch; all other transitions leave
    # 5/10/20/30 minutes unallocated according to the location model.
    all_indexes = [block.index for block in blocks]
    for position, a in enumerate(all_indexes):
        for b in all_indexes[position + 1:]:
            gap = transit_minutes(blocks[a].group_key[1], blocks[b].group_key[1])
            solver.add(z3.Implies(
                z3.And(used[a], used[b]),
                z3.Or(start[a] + dur[a] + gap <= start[b],
                      start[b] + dur[b] + gap <= start[a]),
            ))

    # Hard: avoid every fixed interval (tracked per interval). Explicit fixed
    # buffers remain unavailable; when they are shorter than the location
    # transition, reserve the remaining difference as well.
    for fixed in week.fixed_intervals:
        clauses = []
        for b in all_indexes:
            transit = (transit_minutes(blocks[b].group_key[1], fixed.location)
                       if fixed.location else 0)
            extra_before = max(0, transit - fixed.buffer_before)
            extra_after = max(0, transit - fixed.buffer_after)
            clauses.append(z3.Implies(
                used[b],
                z3.Or(start[b] + dur[b] + extra_before <= fixed.start,
                      fixed.end + extra_after <= start[b]),
            ))
        expression = z3.And(clauses) if clauses else z3.BoolVal(True)
        track(expression, f"fixed:{fixed.id}",
              f"fixed interval '{fixed.label}' ("
              f"{window_label(week.week_start, fixed.start, fixed.end)})")

    # Hard: requirement windows and coverage.
    for r, requirement in enumerate(requirements):
        members = blocks_of_req[r]
        window = z3.And([
            z3.Implies(
                alloc[b][r] > 0,
                z3.And(start[b] >= requirement.window_start,
                       start[b] + dur[b] <= requirement.window_end),
            )
            for b in members
        ]) if members else z3.BoolVal(True)
        track(window, f"window:{requirement.id}",
              f"requirement '{requirement.title}' window "
              f"({window_label(week.week_start, requirement.window_start, requirement.window_end)})")
        coverage = _sum([alloc[b][r] for b in members]) >= needs[r]
        track(coverage, f"coverage:{requirement.id}",
              f"requirement '{requirement.title}' needs {needs[r]} minutes")
        # Over-allocation is never useful; pinning the total at the need keeps
        # the waste metric meaningful and the decoded pins exact.
        solver.add(_sum([alloc[b][r] for b in members]) <= needs[r])

    # Hard: global and per-day block caps. _assign_blocks may create more
    # symbolic slots than max_blocks to expose a useful coverage/core failure,
    # but no satisfying calendar may use more than the configured maximum.
    track(_sum([z3.If(used[b], 1, 0) for b in all_indexes]) <= config.max_blocks,
          "cap:week", f"weekly block cap of {config.max_blocks}")
    for weekday in range(7):
        count = _sum([
            z3.If(z3.And(used[b], day[b] == weekday), 1, 0)
            for b in all_indexes
        ])
        track(count <= config.day_cap, f"cap:{weekday}",
              f"day {weekday} block cap of {config.day_cap}")

    buckets = _build_buckets(week, config, requirements, blocks, used, start, dur,
                             day, alloc)
    return ModelData(
        week=week, config=config, requirements=requirements, needs=needs,
        blocks=blocks, solver=solver, used=used, start=start, dur=dur, day=day,
        alloc=alloc, buckets=buckets, tracked=tracked, blocks_of_req=blocks_of_req,
    )


def _grouped_blocks(blocks):
    grouped: dict = {}
    for block in blocks:
        grouped.setdefault(block.group_key, []).append(block)
    return grouped


def _build_buckets(week, config, requirements, blocks, used, start, dur, day, alloc):
    indexes = [block.index for block in blocks]
    total_alloc = _sum([alloc[b][r] for b in indexes for r in blocks[b].req_indexes])
    used_duration = _sum([z3.If(used[b], dur[b], 0) for b in indexes])
    block_count = _sum([z3.If(used[b], 1, 0) for b in indexes])

    timing_terms = []
    for b in indexes:
        for r in blocks[b].req_indexes:
            if requirements[r].kind == "assignment":
                timing_terms.append(z3.If(day[b] >= 5, alloc[b][r], 0))
                timing_terms.append(z3.If(day[b] >= 4, alloc[b][r], 0))
    timing = _sum(timing_terms)

    late_terms = [
        z3.If(z3.And(used[b], start[b] - day[b] * 1440 >= 21 * 60), 1, 0)
        for b in indexes
    ]
    daily_over = []
    for weekday in range(7):
        minutes = _sum([
            z3.If(z3.And(used[b], day[b] == weekday), alloc[b][r], 0)
            for b in indexes for r in blocks[b].req_indexes
        ])
        daily_over.append(z3.If(minutes > config.daily_budget_minutes,
                                minutes - config.daily_budget_minutes, 0))
    load = _sum(late_terms) + _sum(daily_over)

    cohesion = used_duration - total_alloc + block_count * 15

    project_terms = [
        alloc[b][r]
        for b in indexes for r in blocks[b].req_indexes
        if requirements[r].kind != "assignment"
    ]
    project_free = _sum(project_terms)

    return {
        "timing": timing,
        "load": load,
        "cohesion": cohesion,
        "project_free": project_free,
    }


# ------------------------------------------------------------------ solving


def _probe_bucket(solver, expression, current: int, divisor: int):
    """Bounded bisection ladder for one nonnegative bucket.

    ``current`` is a known-satisfying value. Each probe tightens the target and
    records either the new best satisfying bound or the first unsatisfiable
    floor. Hard constraints are never touched — only ``expression <= target``
    is added. Returns ``(locked, probes, exact)``.
    """
    low, high = int(current), None
    locked = int(current)
    probes = []
    exact = True
    divisor = max(2, int(divisor))
    for _ in range(MAX_LADDER_PROBES):
        if low <= 0:
            break
        if high is None:
            target = low - max(1, low // divisor)
        else:
            if low - high <= 1:
                break
            target = (low + high) // 2
        target = max(0, target)
        if target >= low:
            break
        probes.append(target)
        solver.push()
        solver.add(expression <= target)
        outcome = solver.check()
        if outcome == z3.sat:
            low = target
            locked = target
        else:
            solver.pop()
            high = target
            if outcome == z3.unknown:
                exact = False
                break
    return locked, probes, exact


def _evaluate(model, expression) -> int:
    return model.eval(expression, model_completion=True).as_long()


def _extract_blocks(data: ModelData, model) -> list:
    out = []
    for block in data.blocks:
        b = block.index
        if not bool(model.eval(data.used[b], model_completion=True)):
            continue
        allocations = {}
        for r, variable in data.alloc[b].items():
            minutes = _evaluate(model, variable)
            if minutes > 0:
                allocations[r] = minutes
        out.append({
            "block_index": b,
            "group": list(block.group_key),
            "start": _evaluate(model, data.start[b]),
            "duration": _evaluate(model, data.dur[b]),
            "day": _evaluate(model, data.day[b]),
            "allocations": allocations,
        })
    out.sort(key=lambda item: (item["start"], item["group"]))
    return out


def _core_text(data: ModelData) -> list:
    try:
        names = [str(item) for item in data.solver.unsat_core()]
    except z3.Z3Exception:
        names = []
    core = []
    for name in names:
        core.append({"assumption": name, "message": data.tracked.get(name, name)})
    return core


def _diversity_clause(data: ModelData, values: dict):
    """Forbid exactly the previous used/start/duration configuration.

    Fingerprints are canonical because block indexes are fixed by the symmetry
    breaking (used prefix + ordered starts) in :func:`build_model`.
    """
    terms = []
    for block in data.blocks:
        b = block.index
        record = values.get(b)
        if record is None:
            terms.append(data.used[b])
            continue
        _prev_used, prev_start, prev_dur = record
        terms.append(z3.Or(
            z3.Not(data.used[b]),
            data.start[b] != z3.IntVal(prev_start),
            data.dur[b] != z3.IntVal(prev_dur),
        ))
    return z3.Or(terms) if terms else z3.BoolVal(True)


def solve_candidates(week: WeekInput, config: ComposerConfig) -> list:
    # Source failures are part of the hard layer. Do not solve a weakened
    # subset when an estimate, carried identity, recurrence, or fixed conflict
    # is unresolved; return a semantic preprocessing core instead.
    if week.has_blocking:
        core = [
            {
                "assumption": f"diagnostic:{item.tag}:{index}",
                "message": item.message,
                "refs": list(item.refs),
            }
            for index, item in enumerate(week.blocking())
        ]
        return [{
            "candidate_index": 0,
            "ladder_profile": None,
            "bucket_order": [],
            "status": "INFEASIBLE",
            "optimization_exact": False,
            "soft": {},
            "blocks": [],
            "unsat_core": core,
            "note": "blocking source diagnostics; solver was not run",
            "diagnostics": [item.to_dict() for item in week.diagnostics],
        }]

    candidates = []
    previous_values: list = []
    for index in range(config.candidates):
        variant = LADDER_VARIANTS[index % len(LADDER_VARIANTS)]
        data = build_model(week, config)
        for values in previous_values:
            data.solver.add(_diversity_clause(data, values))
        candidate = _solve_one(data, week, config, variant)
        candidate["candidate_index"] = index
        candidate["ladder_profile"] = variant["name"]
        candidate["bucket_order"] = variant["order"]
        if candidate.get("status") == "ok":
            values = {
                item["block_index"]: (
                    True, item["start"], item["duration"],
                )
                for item in candidate["blocks"]
            }
            previous_values.append(values)
        candidates.append(candidate)
    return candidates


def _solve_one(data: ModelData, week: WeekInput, config: ComposerConfig,
               variant: dict) -> dict:
    solver = data.solver
    result = solver.check()
    if result == z3.unsat:
        return _infeasible(week, data)
    if result != z3.sat:
        return {
            "status": "UNKNOWN",
            "note": solver.reason_unknown(),
            "unsat_core": [],
            "diagnostics": [item.to_dict() for item in week.diagnostics],
        }

    soft = {}
    exact = True
    locked_model = solver.model()
    divisor = int(variant.get("divisor", 4))
    for name in variant.get("order", BUCKET_ORDER):
        expression = data.buckets[name]
        current = _evaluate(locked_model, expression)
        locked, probes, probe_exact = _probe_bucket(
            solver, expression, current, divisor)
        exact = exact and probe_exact
        soft[name] = {"initial": current, "locked": locked, "probes": probes}
        # Keep the best known-satisfying bound active so the final model cannot
        # silently regress to a worse (but still legal) placement.
        solver.add(expression <= locked)

    # Re-check so the returned model reflects every locked soft bound; fall
    # back to the last known-good model if the final check is inconclusive.
    final = solver.check()
    model = solver.model() if final == z3.sat else locked_model
    if final != z3.sat:
        exact = False
    return {
        "status": "ok",
        "optimization_exact": exact,
        "soft": soft,
        "blocks": _extract_blocks(data, model),
        "unsat_core": [],
        "diagnostics": [item.to_dict() for item in week.diagnostics],
    }


def _infeasible(week: WeekInput, data: ModelData) -> dict:
    core = _core_text(data)
    return {
        "status": "INFEASIBLE",
        "optimization_exact": False,
        "soft": {},
        "blocks": [],
        "unsat_core": core,
        "note": "hard constraints are unsatisfiable",
        "diagnostics": [item.to_dict() for item in week.diagnostics],
    }
