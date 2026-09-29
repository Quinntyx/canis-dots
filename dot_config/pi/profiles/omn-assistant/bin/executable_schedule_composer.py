#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["z3-solver>=4.12"]
# ///
"""Propose Taskwarrior-shaped week schedules from omn requirements.

The solver separates rules into three layers:

1. Hard constraints
   - no work before availability or after a deadline;
   - no overlap with fixed events, their explicit travel buffers, or sleep;
   - at most one requirement occupies a slot;
   - no more than the configured number of cohesive blocks per day;
   - every block meets the system's minimum-block duration.

2. System priorities, optimized lexicographically (never folded together)
   - minimize assignment estimate shortfall;
   - then minimize assignment work on weekends (therefore it appears only
     when preserving assignment coverage requires it);
   - then front-load assignment work;
   - then minimize non-assignment estimate shortfall;
   - then minimize the number of cohesive blocks.

3. Profile preferences
   - optimize the profile's named primary metric;
   - then use a fuzzed integer-weight tie-break score over the remaining
     placement metrics. The fuzz affects only ties after the system priorities
     above, so it cannot buy a deadline violation, assignment shortfall,
     weekend homework, delayed assignment work, lost project time, or extra
     blocks.

Each lexicographic objective is minimized independently with a SAT cost-bound
search, then its optimum is locked before moving to the next objective. This
avoids pretending that one arbitrary scalar cost defines the whole schedule.

A block is a maximal contiguous run with the same (topic, location), so several
same-topic requirements can compose into one Taskwarrior block and todo list.
Nothing here writes to Taskwarrior; candidates are proposals.

Usage:
  schedule_composer.py SPEC.json [--out FILE] [--candidates-per-profile 3]

SPEC.json shape:
{
  "week_start": "2026-09-28",
  "days": ["2026-09-28", "..."],
  "slot_minutes": 30,
  "minimum_block_minutes": 30,
  "blocks_per_day_cap": 6,
  "wake_hour": 6,
  "sleep_hour": 24,
  "fixed": [
    {"desc": "Attend CS 3345", "day": "2026-09-28",
     "start": "10:00", "end": "11:15", "location": "FO 2.404",
     "kind": "class", "buffer_before": 15, "buffer_after": 15}
  ],
  "requirements": [
    {"omn_id": "canvasical:...:359958", "title": "Homework 3",
     "est": 3.0, "available": "2026-09-28T00:00:00",
     "due": "2026-10-04T23:59:00", "kind": "assignment",
     "topic": "math-homework", "location": "At home"}
  ]
}

Travel, meal, class, lab, swim, piano-rest, and other authoritative windows are
fixed anchors. Their source adapter/spec generator owns those facts; this
solver only composes flexible work around them.
"""

import argparse
import json
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

from z3 import And, Bool, BoolVal, If, Implies, IntVal, Not, Or, Solver, sat, unsat
from z3 import Sum as ZSum

SLOT_DEFAULT = 30


# -------------------------------------------------------------------- parsing

def load_spec(path):
    with open(path) as f:
        return json.load(f)


def day_list(spec):
    return [date.fromisoformat(d) for d in spec["days"]]


def _step(spec):
    step = int(spec.get("slot_minutes", SLOT_DEFAULT))
    if step <= 0 or 1440 % step:
        raise ValueError("slot_minutes must be a positive divisor of 1440")
    return step


def _minutes(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m


def _day_offset(spec, day):
    return (date.fromisoformat(day) - date.fromisoformat(spec["week_start"])).days


def _slot_floor(spec, day, hhmm):
    step = _step(spec)
    per_day = 1440 // step
    return _day_offset(spec, day) * per_day + _minutes(hhmm) // step


def _slot_ceil(spec, day, hhmm):
    step = _step(spec)
    per_day = 1440 // step
    return _day_offset(spec, day) * per_day + math.ceil(_minutes(hhmm) / step)


def fixed_slots(spec):
    """slot -> fixed events occupying it, including explicit travel buffers."""
    blocked = defaultdict(list)
    step = _step(spec)
    per_day = 1440 // step
    n_slots = len(day_list(spec)) * per_day
    for event in spec.get("fixed", []):
        start = _slot_floor(spec, event["day"], event["start"])
        end = _slot_ceil(spec, event["day"], event["end"])
        if end <= start:
            end = start + (per_day - start % per_day)
        start -= math.ceil(float(event.get("buffer_before", 0)) / step)
        end += math.ceil(float(event.get("buffer_after", 0)) / step)
        for slot in range(max(0, start), min(n_slots, end)):
            blocked[slot].append(event)
    return blocked


def req_slots(spec, requirement):
    return max(1, math.ceil(float(requirement["est"]) * 60 / _step(spec)))


def _parse_timestamp(value, end_of_day=False):
    if not value:
        return None
    if "T" in value:
        return datetime.fromisoformat(value)
    day = date.fromisoformat(value)
    if end_of_day:
        return datetime.combine(day, datetime.min.time()) + timedelta(days=1)
    return datetime.combine(day, datetime.min.time())


def _datetime_slot(spec, value, *, start):
    """Slot boundary for an availability (ceil) or deadline (floor/end)."""
    dt = _parse_timestamp(value, end_of_day=not start)
    if dt is None:
        return None
    step = _step(spec)
    per_day = 1440 // step
    base = date.fromisoformat(spec["week_start"])
    offset = (dt.date() - base).days * per_day
    minutes = dt.hour * 60 + dt.minute
    # Availability permits only slots starting at/after the instant. A due
    # permits slots whose end is no later than it. Date-only dues are parsed as
    # next-day midnight, correctly allowing the final slot of the due date.
    return offset + (math.ceil(minutes / step) if start else minutes // step)


def requirement_group(requirement):
    """The cohesion key: a block never mixes topics or locations."""
    return (
        requirement.get("topic") or requirement["title"],
        requirement.get("location") or "At home",
    )


# ------------------------------------------------------------------- profiles
# These weights only break ties after estimate coverage, weekend homework, and
# block count have already been independently optimized and locked.
PROFILES = {
    "baseline": {
        "primary": "crunch",
        "weights": {"crunch": 8, "free_loss": 4, "project_late": 5,
                    "weekend_all": 12, "changes": 10},
    },
    "assignments-first": {
        "primary": "crunch",
        "weights": {"crunch": 30, "free_loss": 1, "project_late": 6,
                    "weekend_all": 30, "changes": 6},
    },
    "free-time-first": {
        "primary": "free_loss",
        "weights": {"crunch": 6, "free_loss": 40, "project_late": 5,
                    "weekend_all": 8, "changes": 8},
    },
    "projects-first": {
        "primary": "project_late",
        "weights": {"crunch": 8, "free_loss": 3, "project_late": 60,
                    "weekend_all": 10, "changes": 8},
    },
    "cohesion-max": {
        "primary": "changes",
        "weights": {"crunch": 10, "free_loss": 6, "project_late": 8,
                    "weekend_all": 12, "changes": 40},
    },
}


def fuzz_weights(weights, rng, spread=0.25):
    """Jitter once and return non-negative *integer* solver weights."""
    return {
        name: max(0, round(value * (1.0 + rng.uniform(-spread, spread))))
        for name, value in weights.items()
    }


# --------------------------------------------------------------------- model

def _sum_int(terms):
    return ZSum(terms) if terms else IntVal(0)


def build_model(spec, tie_weights, timeout_ms=20_000):
    step = _step(spec)
    per_day = 1440 // step
    days = day_list(spec)
    n_slots = len(days) * per_day
    requirements = spec["requirements"]
    blocked = fixed_slots(spec)
    wake = float(spec.get("wake_hour", 6))
    sleep = float(spec.get("sleep_hour", 24))

    solver = Solver()
    solver.set("timeout", timeout_ms)

    occ = {
        i: [Bool(f"occ_{i}_{slot}") for slot in range(n_slots)]
        for i in range(len(requirements))
    }

    awake = []
    for slot in range(n_slots):
        hour = (slot % per_day) * step / 60
        awake.append(wake <= hour < sleep)

    assignment_shortfall_terms = []
    other_shortfall_terms = []
    assignment_delay_terms = []
    allowed_by_req = {}
    for i, requirement in enumerate(requirements):
        available = _datetime_slot(spec, requirement.get("available"), start=True)
        due = _datetime_slot(spec, requirement["due"], start=False)
        lo = max(0, available if available is not None else 0)
        hi = min(n_slots, due)
        due_day = date.fromisoformat(requirement["due"][:10])
        weekend_forced = (
            requirement.get("weekend_allowed", False)
            or (due_day in days and due_day.weekday() >= 5)
        )
        allowed = {
            slot for slot in range(lo, max(lo, hi))
            if awake[slot]
            and slot not in blocked
            and not (
                requirement.get("kind") == "assignment"
                and days[slot // per_day].weekday() >= 5
                and not weekend_forced
            )
        }
        allowed_by_req[i] = allowed
        for slot in range(n_slots):
            if slot not in allowed:
                solver.add(Not(occ[i][slot]))
        assigned = _sum_int([If(occ[i][slot], 1, 0) for slot in sorted(allowed)])
        need = req_slots(spec, requirement)
        solver.add(assigned <= need)
        shortfall = need - assigned
        if requirement.get("kind") == "assignment":
            assignment_shortfall_terms.append(shortfall)
            if allowed:
                first_allowed = min(allowed)
                assignment_delay_terms.extend(
                    (slot - first_allowed) * If(occ[i][slot], 1, 0)
                    for slot in sorted(allowed)
                )
        else:
            other_shortfall_terms.append(shortfall)

    # A slot belongs to at most one requirement.
    for slot in range(n_slots):
        solver.add(_sum_int([If(occ[i][slot], 1, 0)
                             for i in range(len(requirements))]) <= 1)

    occupied = [Or([occ[i][slot] for i in range(len(requirements))])
                if requirements else BoolVal(False)
                for slot in range(n_slots)]

    # Blocks are maximal runs of one (topic, location), not one requirement.
    groups = defaultdict(list)
    for i, requirement in enumerate(requirements):
        groups[requirement_group(requirement)].append(i)
    group_keys = list(groups)
    group_occ = {}
    group_start = {}
    for g, key in enumerate(group_keys):
        members = groups[key]
        group_occ[g] = [Or([occ[i][slot] for i in members])
                        for slot in range(n_slots)]
        group_start[g] = []
        for slot in range(n_slots):
            begins_day = slot == 0 or slot % per_day == 0
            previous_same = BoolVal(False) if begins_day else group_occ[g][slot - 1]
            starts = Bool(f"start_{g}_{slot}")
            solver.add(starts == And(group_occ[g][slot], Not(previous_same)))
            group_start[g].append(starts)

    # Hard daily block cap.
    cap = int(spec.get("blocks_per_day_cap", 6))
    for day_index in range(len(days)):
        starts = [
            group_start[g][slot]
            for g in range(len(group_keys))
            for slot in range(day_index * per_day, (day_index + 1) * per_day)
        ]
        solver.add(_sum_int([If(value, 1, 0) for value in starts]) <= cap)

    # Hard minimum block duration. At 30-minute resolution this is one slot;
    # at 15-minute resolution it prevents isolated 15-minute blocks.
    min_minutes = int(spec.get("minimum_block_minutes", 30))
    min_slots = max(1, math.ceil(min_minutes / step))
    if min_slots > 1:
        for g in range(len(group_keys)):
            for slot in range(n_slots):
                day_end = (slot // per_day + 1) * per_day
                if slot + min_slots > day_end:
                    solver.add(Not(group_start[g][slot]))
                    continue
                solver.add(Implies(
                    group_start[g][slot],
                    And([group_occ[g][slot + offset]
                         for offset in range(min_slots)]),
                ))

    assignment_shortfall = _sum_int(assignment_shortfall_terms)
    other_shortfall = _sum_int(other_shortfall_terms)
    total_shortfall = assignment_shortfall + other_shortfall
    assignment_delay = _sum_int(assignment_delay_terms)
    block_count = _sum_int([
        If(group_start[g][slot], 1, 0)
        for g in range(len(group_keys)) for slot in range(n_slots)
    ])

    # Weekend assignment work is its own exact objective. Optimizing it after
    # shortfall implements "weekends protected unless assignment coverage
    # cannot fit earlier" without an unsafe profile weight.
    weekend_assignment = _sum_int([
        If(occ[i][slot], 1, 0)
        for i, requirement in enumerate(requirements)
        if requirement.get("kind") == "assignment"
        for slot in range(n_slots)
        if days[slot // per_day].weekday() >= 5
    ])

    # Placement metrics; all are non-negative and therefore independently
    # binary-searchable.
    crunch_terms = []
    for i, requirement in enumerate(requirements):
        allowed = sorted(allowed_by_req[i])
        if not allowed:
            continue
        first, last = allowed[0], allowed[-1] + 1
        crunch_start = first + math.floor((last - first) * 0.75)
        crunch_terms.extend(If(occ[i][slot], 1, 0)
                            for slot in allowed if slot >= crunch_start)
    crunch = _sum_int(crunch_terms)

    project_late = _sum_int([
        If(occ[i][slot], 1, 0)
        for i, requirement in enumerate(requirements)
        if requirement.get("kind") == "project"
        for slot in range(n_slots // 2, n_slots)
    ])

    weekend_all = _sum_int([
        If(occ[i][slot], 1, 0)
        for i in range(len(requirements))
        for slot in range(n_slots)
        if days[slot // per_day].weekday() >= 5
    ])

    changes = _sum_int([
        If(And(group_occ[g][slot], group_occ[h][slot + 1]), 1, 0)
        for slot in range(n_slots - 1)
        if (slot + 1) % per_day != 0
        for g in range(len(group_keys))
        for h in range(len(group_keys)) if g != h
    ])

    # Count lost eligible 2-hour free windows. Sleep and fixed events are not
    # "free time" and are excluded from the denominator entirely.
    free_window_slots = max(1, math.ceil(
        int(spec.get("free_window_minutes", 120)) / step))
    free_windows = []
    for day_index in range(len(days)):
        day_start = day_index * per_day
        day_end = day_start + per_day
        for start in range(day_start, day_end - free_window_slots + 1):
            window = range(start, start + free_window_slots)
            if all(awake[slot] and slot not in blocked for slot in window):
                free_windows.append(And([Not(occupied[slot]) for slot in window]))
    free_loss = len(free_windows) - _sum_int([If(window, 1, 0)
                                               for window in free_windows])

    metrics = {
        "assignment_shortfall": assignment_shortfall,
        "weekend_assignment": weekend_assignment,
        "assignment_delay": assignment_delay,
        "other_shortfall": other_shortfall,
        "shortfall": total_shortfall,
        "blocks": block_count,
        "crunch": crunch,
        "project_late": project_late,
        "weekend_all": weekend_all,
        "changes": changes,
        "free_loss": free_loss,
    }
    tie_score = _sum_int([
        int(tie_weights[name]) * metrics[name]
        for name in sorted(tie_weights)
    ])
    metrics["tie_score"] = tie_score

    return {
        "solver": solver,
        "metrics": metrics,
        "occ": occ,
        "per_day": per_day,
        "group_keys": group_keys,
        "timeout_ms": timeout_ms,
    }


# ---------------------------------------------------------------- optimization

def _int_value(model, expression):
    return model.eval(expression, model_completion=True).as_long()


def _minimize_and_lock(model_data, model, metric_name):
    """Minimize one non-negative integer metric and lock its best bound."""
    solver = model_data["solver"]
    expression = model_data["metrics"][metric_name]
    best_model = model
    best = _int_value(model, expression)
    low, high = 0, best
    exact = True

    while low < high:
        middle = (low + high) // 2
        solver.push()
        solver.add(expression <= middle)
        result = solver.check()
        if result == sat:
            best_model = solver.model()
            best = _int_value(best_model, expression)
            high = best
        elif result == unsat:
            low = middle + 1
        else:
            exact = False
            solver.pop()
            break
        solver.pop()

    solver.add(expression <= best)
    result = solver.check()
    if result == sat:
        best_model = solver.model()
        best = _int_value(best_model, expression)
    else:
        exact = False
    return best_model, best, exact


def solve_once(spec, profile, tie_weights, timeout_ms=20_000):
    model_data = build_model(spec, tie_weights, timeout_ms)
    solver = model_data["solver"]
    result = solver.check()
    if result == unsat:
        return {"status": "INFEASIBLE"}
    if result != sat:
        return {"status": "UNKNOWN", "note": solver.reason_unknown()}

    model = solver.model()
    values = {}
    exact = True
    order = [
        "assignment_shortfall",
        "weekend_assignment",
        "assignment_delay",
        "other_shortfall",
        "blocks",
    ]
    primary = profile["primary"]
    if primary not in order:
        order.append(primary)
    order.append("tie_score")

    for metric_name in order:
        model, value, metric_exact = _minimize_and_lock(
            model_data, model, metric_name)
        values[metric_name] = value
        exact = exact and metric_exact
    for metric_name, expression in model_data["metrics"].items():
        values.setdefault(metric_name, _int_value(model, expression))

    placement = {}
    for i, variables in model_data["occ"].items():
        placement[i] = {
            slot for slot, variable in enumerate(variables)
            if bool(model.eval(variable, model_completion=True))
        }

    decoded = decode(spec, placement, model_data["per_day"])
    decoded.update({
        "status": "ok",
        "objectives": values,
        "optimization_exact": exact,
    })
    return decoded


# --------------------------------------------------------------------- decode

def decode(spec, placement, per_day):
    days = day_list(spec)
    requirements = spec["requirements"]
    step = _step(spec)
    n_slots = len(days) * per_day
    owner = {}
    for i, slots in placement.items():
        for slot in slots:
            owner[slot] = i

    blocks = []
    slot = 0
    while slot < n_slots:
        i = owner.get(slot)
        if i is None:
            slot += 1
            continue
        group = requirement_group(requirements[i])
        day_index = slot // per_day
        day_end = (day_index + 1) * per_day
        start = slot
        req_indexes = []
        while slot < day_end:
            current = owner.get(slot)
            if current is None or requirement_group(requirements[current]) != group:
                break
            if current not in req_indexes:
                req_indexes.append(current)
            slot += 1
        start_min = (start % per_day) * step
        end_min = (slot % per_day) * step if slot < day_end else 1440
        blocks.append({
            "day": days[day_index].isoformat(),
            "start": f"{start_min // 60:02d}:{start_min % 60:02d}",
            "end": f"{end_min // 60:02d}:{end_min % 60:02d}",
            "topic": group[0],
            "location": group[1],
            "requirements": [requirements[j] for j in req_indexes],
        })

    per_day_blocks = defaultdict(int)
    for block in blocks:
        per_day_blocks[block["day"]] += 1

    sacrifices = []
    for i, requirement in enumerate(requirements):
        got = len(placement.get(i, set())) * step / 60
        expected = float(requirement["est"])
        if got + 1e-9 < expected:
            sacrifices.append(
                f"'{requirement['title']}' gets {got:.2f}h of {expected:.2f}h")
        weekend = sum(
            1 for slot in placement.get(i, set())
            if days[slot // per_day].weekday() >= 5
        ) * step / 60
        if requirement.get("kind") == "assignment" and weekend > 0:
            sacrifices.append(
                f"'{requirement['title']}' needs {weekend:.2f}h of weekend work")

    return {
        "blocks": blocks,
        "per_day_blocks": dict(per_day_blocks),
        "sacrifices": sacrifices or ["nothing obvious"],
    }


# ----------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--out")
    parser.add_argument("--candidates-per-profile", type=int, default=3)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--timeout-ms", type=int, default=20_000)
    args = parser.parse_args()

    spec = load_spec(args.spec)
    rng = random.Random(args.seed)
    output = {"week_start": spec["week_start"], "candidates": []}

    for profile_name, profile in PROFILES.items():
        for _ in range(args.candidates_per_profile):
            weights = fuzz_weights(profile["weights"], rng)
            solved = solve_once(spec, profile, weights, args.timeout_ms)
            candidate = {
                "profile": profile_name,
                "weights": weights,
                **solved,
            }
            if solved["status"] == "INFEASIBLE":
                candidate["note"] = "hard constraints cannot be satisfied"
            output["candidates"].append(candidate)

    text = json.dumps(output, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
