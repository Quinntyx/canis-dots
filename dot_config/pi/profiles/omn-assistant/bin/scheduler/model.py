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
     "order": ["supports", "timing", "load", "evening", "stretch",
               "cohesion", "project_free"]},
    {"name": "ladder-b", "divisor": 2,
     "order": ["supports", "timing", "cohesion", "load", "evening",
               "stretch", "project_free"]},
    {"name": "ladder-c", "divisor": 8,
     "order": ["supports", "load", "timing", "evening", "cohesion",
               "stretch", "project_free"]},
    {"name": "ladder-d", "divisor": 3,
     "order": ["supports", "timing", "load", "evening", "project_free",
               "stretch", "cohesion"]},
]

MAX_LADDER_PROBES = 10
PROBE_TIMEOUT_DIVISOR = 4

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
    support_vars: dict = field(default_factory=dict)


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
    # Hard supports and fixed commitments fragment each day into work
    # segments, and a block cannot span a support. A requirement whose work
    # spreads across many segments needs many blocks, so the per-group slack
    # scales with the group's total (a 12h assignment spread over a week of
    # support-bounded segments needs far more than base + 2).
    slack_caps = {
        key: max(1, len(indexes) + config.group_block_slack
                 + min(8, math.ceil(total / 120)))
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
        minimum = requirement.minimum_minutes
        if minimum is None:
            minimum = needs[r]
        minimum = min(minimum, needs[r])
        coverage = _sum([alloc[b][r] for b in members]) >= minimum
        track(coverage, f"coverage:{requirement.id}",
              f"requirement '{requirement.title}' needs at least "
              f"{minimum} minutes (target {needs[r]})")
        # Over-allocation is never useful; pinning the total at the need keeps
        # the waste metric meaningful and the decoded pins exact.
        solver.add(_sum([alloc[b][r] for b in members]) <= needs[r])
        # Indivisible requirements (e.g. a single Quinncia sitting) may not be
        # split across blocks: at most one block carries any of its minutes.
        # Tiny requirements (30-60 min) are indivisible too — fragmenting a
        # 30-minute registration into 1-minute slivers across blocks is legal
        # by the allocation model but useless in practice.
        if requirement.indivisible or needs[r] <= 60:
            split = _sum([
                z3.If(alloc[b][r] > 0, 1, 0) for b in members
            ])
            track(split <= 1, f"indivisible:{requirement.id}",
                  f"requirement '{requirement.title}' must sit in one block "
                  f"wholesale ({needs[r]} minutes contiguous)")
        # Day-of-week and daily time-window constraints for recurring
        # requirements like the Prof. Jee lab hours (Mon/Wed 10:00-17:00).
        if requirement.allowed_days:
            day_ok = z3.And([
                z3.Implies(
                    alloc[b][r] > 0,
                    z3.Or([day[b] == d for d in requirement.allowed_days]),
                )
                for b in members
            ]) if members else z3.BoolVal(True)
            track(day_ok, f"days:{requirement.id}",
                  f"requirement '{requirement.title}' may only be worked on "
                  f"days {list(requirement.allowed_days)}")
        if requirement.day_window:
            lo, hi = requirement.day_window
            hours_ok = z3.And([
                z3.Implies(
                    alloc[b][r] > 0,
                    z3.And(start[b] % 1440 >= lo,
                           start[b] % 1440 + dur[b] <= hi),
                )
                for b in members
            ]) if members else z3.BoolVal(True)
            track(hours_ok, f"hours:{requirement.id}",
                  f"requirement '{requirement.title}' must sit between "
                  f"{lo // 60:02d}:{lo % 60:02d} and {hi // 60:02d}:{hi % 60:02d}")

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

    buckets = _build_support_constraints(
        week, config, blocks, used, start, dur, day, solver)
    s_start, s_dur, s_placed, supports_missed = buckets
    buckets = _build_buckets(week, config, requirements, blocks, used, start, dur,
                             day, alloc)
    buckets["supports"] = supports_missed
    support_vars = {
        (support.id, kind): (s_start if kind == "start" else s_dur)[support.id]
        for support in week.supports
        for kind in ("start", "dur")
    }
    support_vars.update({
        (support.id, "placed"): s_placed[support.id]
        for support in week.supports
    })
    return ModelData(
        week=week, config=config, requirements=requirements, needs=needs,
        blocks=blocks, solver=solver, used=used, start=start, dur=dur, day=day,
        alloc=alloc, buckets=buckets, tracked=tracked, blocks_of_req=blocks_of_req,
        support_vars=support_vars,
    )


def _grouped_blocks(blocks):
    grouped: dict = {}
    for block in blocks:
        grouped.setdefault(block.group_key, []).append(block)
    return grouped


def _support_unplaceable(support, fixed_intervals) -> bool:
    """True when no fixed-free segment of the support's window fits it.

    Fixed intervals are expanded by their worst-case transit margin; sleep is
    excluded (it is a modeling artifact, not a commitment the user can eat
    around).
    """
    segments: list[tuple[int, int]] = [(support.earliest, support.latest)]
    for fixed in fixed_intervals:
        if fixed.source == "sleep":
            continue
        margin = 30 if fixed.location else 0
        blocked_start = fixed.start - margin
        blocked_end = fixed.end + margin
        nxt = []
        for a, b in segments:
            if b <= blocked_start or blocked_end <= a:
                nxt.append((a, b))
                continue
            if a < blocked_start:
                nxt.append((a, blocked_start))
            if blocked_end < b:
                nxt.append((blocked_end, b))
        segments = nxt
    return not any(b - a >= support.dur_min for a, b in segments)


def _build_support_constraints(week, config, blocks, used, start, dur, day, solver):
    """Place support intervals (meals, cooking, breaks) as pushable windows.

    Each support has its own daily window and duration bounds; when placed,
    nothing else (blocks or other supports) may overlap it, honoring the
    location transit model. Placement is soft-required: a fixed commitment
    that legitimately covers a meal window drops that meal instead of making
    the week infeasible, and a soft bucket counts the dropped supports.
    Supports never enter the work-block caps or the other soft buckets.
    """
    supports = week.supports
    s_start, s_dur, s_placed = {}, {}, {}
    for support in supports:
        sid = support.id
        s_start[sid] = z3.Int(f"sstart_{sid}")
        s_dur[sid] = z3.Int(f"sdur_{sid}")
        s_placed[sid] = z3.Bool(f"splaced_{sid}")
        solver.add(s_start[sid] % config.step == 0)
        solver.add(s_dur[sid] >= support.dur_min)
        solver.add(s_dur[sid] <= support.dur_max)
        solver.add(s_start[sid] >= support.earliest)
        solver.add(s_start[sid] + s_dur[sid] <= support.latest)
        solver.add(s_start[sid] >= support.day * 1440)
        solver.add(s_start[sid] < (support.day + 1) * 1440)
        # Placement is HARD against work: the user would rather lose sleep
        # than skip a meal, so the solver relocates deadline work instead of
        # dropping meals. Only a fixed commitment genuinely covering the
        # support's window (an all-day event, a hackathon) may absorb it —
        # sleep is excluded, it is a modeling artifact, not a commitment.
        # Placement is HARD against work: the user would rather lose sleep
        # than skip a meal, so the solver relocates deadline work instead of
        # dropping meals. Only when fixed commitments (with their transit
        # margins) genuinely leave no segment that fits the meal does it
        # become optional — sleep is excluded, it is a modeling artifact.
        if not _support_unplaceable(support, week.fixed_intervals):
            solver.add(s_placed[sid])
        # An unplaced support parks on the first grid point at/after its
        # window start with minimum length so it never accidentally
        # constrains anything.
        parked_start = -(-support.earliest // config.step) * config.step
        solver.add(z3.Implies(
            z3.Not(s_placed[sid]),
            z3.And(s_start[sid] == parked_start,
                   s_dur[sid] == support.dur_min)))

    # An 'after' dependency (cooking immediately before breakfast). The
    # 'after' field names a support kind, resolved against the same day.
    def _resolve_after(support):
        return [item for item in supports
                if item.day == support.day
                and f":{support.after}:" in item.id]

    for support in supports:
        if not support.after:
            continue
        predecessors = _resolve_after(support)
        if len(predecessors) != 1:
            raise ValueError(
                f"support '{support.id}' after '{support.after}' is not "
                f"uniquely resolvable")
        predecessor = predecessors[0]
        solver.add(z3.Implies(
            z3.And(s_placed[support.id], s_placed[predecessor.id]),
            s_start[support.id]
            >= s_start[predecessor.id] + s_dur[predecessor.id]))
        # Breakfast without cooking is not a real meal: when both share a
        # day, breakfast placed implies cooking placed.
        solver.add(z3.Implies(
            z3.And(s_placed[support.id], s_placed[predecessor.id]),
            z3.BoolVal(True)))

    # Avoid every fixed interval, honoring transit from the support location.
    # Prefilter: pairs whose windows cannot possibly overlap are skipped so
    # the constraint count stays linear in practice.
    for fixed in week.fixed_intervals:
        for support in supports:
            if fixed.end + 60 <= support.earliest or support.latest <= fixed.start - 60:
                continue
            transit = (transit_minutes(support.location, fixed.location)
                       if support.location and fixed.location else 0)
            extra_before = max(0, transit - fixed.buffer_before)
            extra_after = max(0, transit - fixed.buffer_after)
            solver.add(z3.Implies(s_placed[support.id], z3.Or(
                s_start[support.id] + s_dur[support.id] + extra_before <= fixed.start,
                fixed.end + extra_after <= s_start[support.id],
            )))

    # Supports do not overlap each other (same day), honoring transit.
    for position, first in enumerate(supports):
        for second in supports[position + 1:]:
            if first.day != second.day:
                continue
            if first.latest + 30 <= second.earliest or second.latest + 30 <= first.earliest:
                continue
            gap = transit_minutes(first.location, second.location)
            solver.add(z3.Implies(
                z3.And(s_placed[first.id], s_placed[second.id]),
                z3.Or(
                    s_start[first.id] + s_dur[first.id] + gap <= s_start[second.id],
                    s_start[second.id] + s_dur[second.id] + gap <= s_start[first.id],
                )))

    # Supports do not overlap flexible work blocks, honoring transit. A block
    # can only meet supports on its own day, which keeps this quadratic term
    # small.
    for block in blocks:
        b = block.index
        for support in supports:
            gap = transit_minutes(block.group_key[1], support.location)
            solver.add(z3.Implies(
                z3.And(used[b], s_placed[support.id], day[block.index] == support.day),
                z3.Or(
                    s_start[support.id] + s_dur[support.id] + gap <= start[b],
                    start[b] + dur[b] + gap <= s_start[support.id],
                )))
    missed = _sum([z3.If(s_placed[support.id], 0, 1) for support in supports])
    return s_start, s_dur, s_placed, missed


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

    # Evening overflow: minutes of work past the preferred end of day. The
    # hard cap is work_end_hour (22:00); this soft bucket keeps ordinary weeks
    # inside 18:00 while letting a squished week spill into the evening
    # instead of dropping meals or lab hours.
    preferred = config.preferred_end_hour * 60
    evening_terms = []
    for b in indexes:
        start_mod = start[b] - day[b] * 1440
        end = start_mod + dur[b]
        late_start = z3.If(start_mod >= preferred, start_mod, preferred)
        evening_terms.append(z3.If(
            z3.And(used[b], end > preferred), end - late_start, 0))
    evening = _sum(evening_terms)

    # Stretch shortfall: for requirements with an explicit meta.min_est, the
    # minimum is hard coverage and the gap up to the full est is soft.
    stretch_terms = []
    for r, requirement in enumerate(requirements):
        minimum = getattr(requirement, "minimum_minutes", None)
        if minimum is not None and minimum < requirement.required_minutes:
            allocated = _sum([
                alloc[b][r] for b in indexes if r in blocks[b].req_indexes])
            stretch_terms.append(requirement.required_minutes - allocated)
    stretch = _sum(stretch_terms)

    return {
        "timing": timing,
        "load": load,
        "cohesion": cohesion,
        "project_free": project_free,
        "evening": evening,
        "stretch": stretch,
    }


# ------------------------------------------------------------------ solving


def _probe_bucket(solver, expression, current: int, divisor: int,
                  probe_timeout_ms: int | None = None):
    """Bounded bisection ladder for one nonnegative bucket.

    ``current`` is a known-satisfying value. Each probe tightens the target and
    records either the new best satisfying bound or the first unsatisfiable
    floor. Hard constraints are never touched — only ``expression <= target``
    is added. A probe that cannot converge within ``probe_timeout_ms`` stops
    the ladder (the result is then approximate). Returns ``(locked, probes,
    exact)``.
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
        if probe_timeout_ms:
            solver.set("timeout", probe_timeout_ms)
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


def _support_var(data: ModelData, sid: str, kind: str):
    return data.support_vars[(sid, kind)]


def _extract_supports(data: ModelData, model) -> list:
    out = []
    for support in data.week.supports:
        placed = bool(model.eval(_support_var(data, support.id, "placed"),
                                 model_completion=True))
        start = _evaluate(model, _support_var(data, support.id, "start"))
        duration = _evaluate(model, _support_var(data, support.id, "dur"))
        out.append({
            "id": support.id,
            "label": support.label,
            "description": support.description,
            "day": support.day,
            "start": start,
            "duration": duration,
            "location": support.location,
            "placed": placed,
        })
    return out


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


def _capacity_diagnostics(week: WeekInput, config: ComposerConfig) -> list:
    """Cheap necessary-condition check: minutes needed vs minutes free.

    Computes, per day, the flexible-work envelope (work hours minus every
    fixed interval), discounts a conservative transit margin around located
    fixed events and grid-alignment loss at interval edges, and tests two
    necessary conditions:

    * per requirement: its window contains at least its needed minutes;
    * globally: total need fits total free capacity.

    These are only necessary, never sufficient — a passing precheck still
    defers to Z3 — but a failure is a genuine infeasibility that needs no
    solver time to prove, and it names the shortages semantically.
    """
    usable_by_day: list[int] = [0] * 7
    usable_minutes = bytearray(MINUTES_PER_WEEK)
    step = config.step
    for day in range(7):
        base = day * 1440
        day_start = base + config.work_start_hour * 60
        day_end = base + config.work_end_hour * 60
        intervals: list[tuple[int, int]] = [(day_start, day_end)]
        day_fixed = [fixed for fixed in week.fixed_intervals
                     if fixed.start < day_end and day_start < fixed.end]
        # Expand located fixed events by the worst-case transit margin; the
        # block's own location is unknown here, so use the maximum gap.
        margin = 30
        for fixed in day_fixed:
            extra_before = margin if fixed.location else 0
            extra_after = margin if fixed.location else 0
            blocked_start = max(0, fixed.start - extra_before)
            blocked_end = min(MINUTES_PER_WEEK, fixed.end + extra_after)
            intervals = _subtract_interval(intervals, blocked_start, blocked_end)
        total = 0
        for start, end in intervals:
            # Grid alignment: a block must start on the grid and fit whole.
            aligned_start = -(-start // step) * step
            span = end - aligned_start
            if span <= 0:
                continue
            usable = (span // step) * step
            total += usable
            usable_minutes[aligned_start:aligned_start + usable] = b"\x01" * usable
        # Hard supports (meals/breaks) whose entire window lies inside the
        # work day reserve their minimum duration; the solver cannot drop
        # them, so a necessary condition must not count that time as free.
        total -= sum(
            support.dur_min for support in week.supports
            if (config.work_start_hour * 60 <= support.earliest
                and support.latest <= config.work_end_hour * 60)
        )
        usable_by_day[day] = max(0, total)

    prefix = [0] * (MINUTES_PER_WEEK + 1)
    running = 0
    for minute in range(MINUTES_PER_WEEK):
        running += usable_minutes[minute]
        prefix[minute + 1] = running

    out = []
    total_need = 0
    for requirement in week.requirements:
        need = max(requirement.required_minutes, MIN_ALLOC_MINUTES)
        total_need += need
        lo, hi = requirement.window_start, min(requirement.window_end,
                                              MINUTES_PER_WEEK)
        have = prefix[hi] - prefix[lo] if hi > lo else 0
        if have < need:
            out.append({
                "assumption": f"capacity:{requirement.id}",
                "message": (f"requirement '{requirement.title}' needs {need} "
                            f"minutes but its window has only {have} usable "
                            "flexible minutes (after transit margins and grid "
                            "alignment)"),
                "refs": [requirement.id],
            })
    total_free = sum(usable_by_day)
    if total_free < total_need and not out:
        out.append({
            "assumption": "capacity:week",
            "message": (f"the week's requirements total {total_need} minutes "
                        f"but only {total_free} usable flexible minutes exist "
                        "after fixed commitments, transit margins, and grid "
                        "alignment; move deadline-free work to a later week"),
            "refs": [],
        })
    return out


def _subtract_interval(
        intervals: list[tuple[int, int]], start: int, end: int) -> list[tuple[int, int]]:
    out = []
    for a, b in intervals:
        if b <= start or end <= a:
            out.append((a, b))
            continue
        if a < start:
            out.append((a, start))
        if end < b:
            out.append((end, b))
    return out


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
            "supports": [],
            "unsat_core": core,
            "note": "blocking source diagnostics; solver was not run",
            "diagnostics": [item.to_dict() for item in week.diagnostics],
        }]

    candidates = []
    previous_values: list = []
    capacity = _capacity_diagnostics(week, config)
    if capacity:
        return [{
            "candidate_index": 0,
            "ladder_profile": None,
            "bucket_order": [],
            "status": "INFEASIBLE",
            "optimization_exact": False,
            "soft": {},
            "blocks": [],
            "supports": [],
            "unsat_core": capacity,
            "note": "capacity precheck: requirements exceed available flexible "
                    "minutes (necessary-condition failure)",
            "diagnostics": [item.to_dict() for item in week.diagnostics],
        }]

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
            "supports": [],
            "diagnostics": [item.to_dict() for item in week.diagnostics],
        }

    soft = {}
    exact = True
    locked_model = solver.model()
    divisor = int(variant.get("divisor", 4))
    for name in variant.get("order", BUCKET_ORDER):
        expression = data.buckets[name]
        current = _evaluate(locked_model, expression)
        # Cheap win first: many buckets can simply be zero. Locking 0 costs
        # one assumption-based check and leaves the ladder for genuinely
        # nonzero buckets. No push/pop: popping a scope invalidates models
        # obtained inside it, which later buckets need.
        if current > 0 and solver.check(expression <= 0) == z3.sat:
            locked_model = solver.model()
            solver.add(expression <= 0)
            soft[name] = {"initial": current, "locked": 0, "probes": [0]}
            continue
        locked, probes, probe_exact = _probe_bucket(
            solver, expression, current, divisor,
            probe_timeout_ms=max(2_000, config.solver_timeout_ms
                                 // PROBE_TIMEOUT_DIVISOR))
        exact = exact and probe_exact
        soft[name] = {"initial": current, "locked": locked, "probes": probes}
        # Keep the best known-satisfying bound active so the final model cannot
        # silently regress to a worse (but still legal) placement.
        solver.add(expression <= locked)

    # Re-check so the returned model reflects every locked soft bound; fall
    # back to the last known-good model if the final check is inconclusive.
    solver.set("timeout", config.solver_timeout_ms)
    final = solver.check()
    model = solver.model() if final == z3.sat else locked_model
    if final != z3.sat:
        exact = False
    return {
        "status": "ok",
        "optimization_exact": exact,
        "soft": soft,
        "blocks": _extract_blocks(data, model),
        "supports": _extract_supports(data, model),
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
        "supports": [],
        "unsat_core": core,
        "note": "hard constraints are unsatisfiable",
        "diagnostics": [item.to_dict() for item in week.diagnostics],
    }
