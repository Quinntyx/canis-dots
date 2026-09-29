#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["z3-solver>=4.12"]
# ///
"""Generate candidate week schedules from an omn-requirements spec.

omn is the source of requirements (deadlines, quotas, events); this script
proposes Taskwarrior-shaped weeks that satisfy them. Fixed events (classes,
meals, appointments) are hard anchors. Deadline-bearing requirements must be
scheduled in 15-minute slots on or before their due date. Co-scheduled
requirements that run back-to-back share a block - that is batching, and it is
rewarded. Every maximal run of occupied slots is a *block*; adjacency between
*different* requirements is a context switch, which profiles trade off
differently.

Each profile is a named weighting of soft costs, fuzzed with small weight
jitter, producing several structurally different candidates per profile. Every
candidate reports what it sacrificed, so a human (or the agent) can pick with
the tradeoffs visible. Nothing here writes to Taskwarrior: candidates are
proposals.

Usage:
  schedule_composer.py SPEC.json [--out DIR] [--candidates-per-profile 3]

SPEC.json shape (see make_spec.py for a generator from live stores):
{
  "week_start": "2026-09-28",
  "days": ["2026-09-28", ...],
  "slot_minutes": 15,
  "blocks_per_day_cap": 6,
  "wake_hour": 6,
  "sleep_hour": 24,
  "fixed": [
    {"desc": "Attend CS 3345", "day": "2026-09-28", "start": "10:00",
     "end": "11:15", "location": "FO 2.404", "kind": "class"}
  ],
  "requirements": [
    {"omn_id": "canvasical:...:359958", "title": "Homework 3", "est": 3.0,
     "due": "2026-10-04", "kind": "assignment", "topic": "math-homework",
     "location": "At home"}
  ]
}
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

from z3 import And, Bool, BoolVal, If, PbEq, Solver, sat
from z3 import Sum as ZSum

SLOT_DEFAULT = 15


# ----------------------------------------------------------------- spec load

def load_spec(path):
    with open(path) as f:
        return json.load(f)


def day_list(spec):
    return [date.fromisoformat(d) for d in spec["days"]]


def slot_index(spec, day, hhmm):
    """Absolute slot index for a day/time, relative to week_start 00:00."""
    start = date.fromisoformat(spec["week_start"])
    d = date.fromisoformat(day)
    day_offset = (d - start).days
    h, m = (int(x) for x in hhmm.split(":"))
    per_day = 24 * 60 // spec.get("slot_minutes", SLOT_DEFAULT)
    return day_offset * per_day + (h * 60 + m) // spec.get("slot_minutes", SLOT_DEFAULT)


def fixed_slots(spec):
    """slot -> list of fixed event dicts occupying it."""
    occ = defaultdict(list)
    per_day = 24 * 60 // spec.get("slot_minutes", SLOT_DEFAULT)
    for ev in spec.get("fixed", []):
        s = slot_index(spec, ev["day"], ev["start"])
        e = slot_index(spec, ev["day"], ev["end"])
        if e <= s:  # wraps past midnight: clamp to day end
            e = s + (per_day - s % per_day)
        for slot in range(s, e):
            occ[slot].append(ev)
    return occ


def req_slots(spec, req):
    """est in slots, rounded up to the minimum block granularity."""
    step = spec.get("slot_minutes", SLOT_DEFAULT) / 60.0
    return max(1, int(-(-req["est"] // step)))


def deadline_slot(spec, req):
    """First slot strictly after the requirement's due moment."""
    step = spec.get("slot_minutes", SLOT_DEFAULT)
    due = datetime.fromisoformat(req["due"]) if "T" in req["due"] else \
        datetime.combine(date.fromisoformat(req["due"]), datetime.min.time()) + timedelta(hours=23, minutes=59)
    per_day = 24 * 60 // step
    base = date.fromisoformat(spec["week_start"])
    day_off = (due.date() - base).days
    return day_off * per_day + (due.hour * 60 + due.minute) // step


# ------------------------------------------------------------------- profiles

PROFILES = {
    "baseline": {
        "switches": 10, "assignment_late": 0, "free_time": 4,
        "project_late": 5, "cohesion": 3, "weekend": 12,
    },
    "assignments-first": {
        "switches": 6, "assignment_late": 60, "free_time": 1,
        "project_late": 6, "cohesion": 2, "weekend": 30,
    },
    "free-time-first": {
        "switches": 8, "assignment_late": 20, "free_time": 40,
        "project_late": 5, "cohesion": 3, "weekend": 8,
    },
    "projects-first": {
        "switches": 8, "assignment_late": 10, "free_time": 3,
        "project_late": 60, "cohesion": 3, "weekend": 10,
    },
    "cohesion-max": {
        "switches": 3, "assignment_late": 15, "free_time": 6,
        "project_late": 8, "cohesion": 40, "weekend": 12,
    },
}


def fuzz_weights(weights, rng, spread=0.35):
    out = {}
    for k, v in weights.items():
        factor = 1.0 + rng.uniform(-spread, spread)
        out[k] = max(0.0, round(v * factor, 2))
    return out


# --------------------------------------------------------------------- solver

def build_model(spec, weights, timeout_ms=30000):
    step = spec.get("slot_minutes", SLOT_DEFAULT)
    per_day = 24 * 60 // step
    days = day_list(spec)
    n_slots = len(days) * per_day
    fslots = fixed_slots(spec)
    reqs = spec["requirements"]

    solver = Solver()
    solver.set("timeout", timeout_ms)

    # occ[r][s]: requirement r occupies slot s.
    occ = {i: [Bool(f"occ_{i}_{s}") for s in range(n_slots)]
           for i in range(len(reqs))}
    # free[s]: no requirement and no fixed event in slot s.
    free = [And([fslots.get(s) is None, *[~occ[i][s] for i in range(len(reqs))]])
            for s in range(n_slots)]

    # Requirement sizing: work in proportion to est, by deadline.
    for i, r in enumerate(reqs):
        need = req_slots(spec, r)
        dl = min(deadline_slot(spec, r), n_slots)
        allowed = [occ[i][s] for s in range(min(dl, n_slots)) if fslots.get(s) is None]
        if not allowed:
            continue
        # Exactly `need` slots of requirement i, all before the deadline.
        solver.add(PbEq([(a, 1) for a in allowed], need))

    # At most one requirement per slot (batching shows up as adjacency).
    for s in range(n_slots):
        holders = [occ[i][s] for i in range(len(reqs))]
        if len(holders) > 1:
            solver.add(ZSum([If(h, 1, 0) for h in holders]) <= 1)

    # Soft costs folded into ONE integer objective: lexicographic Optimize is
    # far too slow at week scale, and fuzzing only perturbs weights anyway.
    w_sw = int(round(weights["switches"]))
    w_late = int(round(weights["assignment_late"]))
    w_proj = int(round(weights["project_late"]))
    w_wknd = int(round(weights["weekend"]))
    w_free = int(round(weights["free_time"]))
    w_coh = int(round(weights["cohesion"]))
    cost = 0

    # Context switches: a boundary where the occupant requirement changes.
    for s in range(n_slots - 1):
        terms = []
        for i in range(len(reqs)):
            for j in range(len(reqs)):
                if i != j:
                    terms.append(If(And(occ[i][s], occ[j][s + 1]), 1, 0))
        if terms:
            cost = cost + w_sw * ZSum(terms)

    # Deadline pressure: work landing in the last quarter of the runway.
    for i, r in enumerate(reqs):
        dl = min(deadline_slot(spec, r), n_slots)
        runway = max(1, dl // 4)
        for s in range(max(0, dl - runway), dl):
            cost = cost + w_late * If(occ[i][s], 1, 0)

    # Project work drifting into the back half of the week.
    for i, r in enumerate(reqs):
        if r.get("kind") == "project":
            for s in range(n_slots // 2, n_slots):
                cost = cost + w_proj * If(occ[i][s], 1, 0)

    # Weekend work costs more (the last two days of the week).
    for i in range(len(reqs)):
        for s in range(n_slots):
            if (s // per_day) >= len(days) - 2:
                cost = cost + w_wknd * If(occ[i][s], 1, 0)

    # Rewards (negative): long free runs, long single-topic runs.
    long_free = max(1, 120 // step)
    if long_free > 1:
        for s in range(n_slots - long_free + 1):
            cost = cost - w_free * If(And([free[s + k] for k in range(long_free)]), 1, 0)

    run = max(1, 60 // step)
    if run > 1:
        for s in range(n_slots - run + 1):
            for i in range(len(reqs)):
                cost = cost - w_coh * If(And([occ[i][s + k] for k in range(run)]), 1, 0)

    # Block starts: a slot is a block start when something is occupied there and
    # the previous slot is not. The daily cap is a hard constraint, not a
    # penalty - it is the budget the user actually spends.
    per_day_cap = spec.get("blocks_per_day_cap", 6)
    occupied = [ZSum([If(occ[i][s], 1, 0) for i in range(len(reqs))]) >= 1
                for s in range(n_slots)]
    blockstart = [Bool(f"bs_{s}") for s in range(n_slots)]
    for s in range(n_slots):
        prev_empty = BoolVal(True) if (s == 0 or s % per_day == 0) else occupied[s - 1]
        solver.add(blockstart[s] == And(occupied[s], prev_empty))
    for d in range(len(days)):
        starts = [blockstart[s] for s in range(d * per_day, (d + 1) * per_day)]
        if starts:
            solver.add(ZSum([If(b, 1, 0) for b in starts]) <= per_day_cap)

    # Sleeping hours: never schedule work. `wake_hour`/`sleep_hour` are local
    # clock hours (sleep_hour may exceed 24 to mean e.g. 01:00 next day).
    wake = spec.get("wake_hour", 6)
    sleep = spec.get("sleep_hour", 24)
    for s in range(n_slots):
        hour = (s % per_day) * step / 60.0
        if hour < wake or hour >= sleep:
            for i in range(len(reqs)):
                solver.add(Not(occ[i][s]))

    return solver, cost, occ, free, fslots, per_day

    # 6. Weekend work: last two days of the week cost more.


def solve_once(spec, weights, timeout_ms=20000, max_cost=20000):
    """Find a low-cost placement by binary-searching the cost bound.

    Optimize is too slow at week scale; a plain SAT solver with a cost bound,
    probed from the bottom up, is dramatically faster and gives the same
    "good enough under this profile" answer. Returns None only when the hard
    requirements are genuinely unsatisfiable.
    """
    solver, cost, occ, free, fslots, per_day = build_model(spec, weights, timeout_ms)
    days = day_list(spec)
    step = spec.get("slot_minutes", SLOT_DEFAULT)
    reqs = spec["requirements"]

    # Feasibility first, independent of cost.
    if solver.check() != sat:
        return None
    best_model = solver.model()
    lo, hi = 0, max_cost
    while lo <= hi:
        mid = (lo + hi) // 2
        solver.push()
        solver.add(cost <= mid)
        if solver.check() == sat:
            best_model = solver.model()
            solver.pop()
            hi = mid - 1
        else:
            solver.pop()
            lo = mid + 1

    placement = {}
    for i, r in enumerate(reqs):
        placement[i] = [s for s in range(len(days) * per_day)
                        if best_model.eval(occ[i][s], model_completion=True)]
    return decode(spec, placement, per_day, step)


def decode(spec, placement, per_day, step):
    """Turn slot placement into blocks + a compromise report."""
    days = day_list(spec)
    reqs = spec["requirements"]
    fslots = fixed_slots(spec)
    blocks = []
    sacrifices = []

    for s in range(len(days) * per_day):
        occupant = next((i for i in placement if s in placement[i]), None)
        if occupant is None:
            continue
        # start of a block: nothing of any requirement in the previous slot
        prev = [i for i in placement if (s - 1) in placement[i]]
        if s > 0 and prev:
            continue
        run = []
        cur = s
        while cur in placement[occupant]:
            run.append(cur)
            cur += 1
        i = occupant
        d = (s // per_day)
        start_min = (s % per_day) * step
        end_min = ((cur - 1) % per_day) * step + step
        start = (start_min // 60, start_min % 60)
        end = (end_min // 60, end_min % 60)
        blocks.append({
            "day": days[d].isoformat(),
            "start": f"{start[0]:02d}:{start[1]:02d}",
            "end": f"{end[0]:02d}:{end[1]:02d}",
            "topic": reqs[i].get("topic", reqs[i]["title"]),
            "requirements": [reqs[i]],
            "location": reqs[i].get("location", "At home"),
        })

    # Per-day block counts (excluding fixed class/meal anchors).
    cap = spec.get("blocks_per_day_cap", 6)
    per_day_blocks = defaultdict(int)
    for b in blocks:
        per_day_blocks[b["day"]] += 1
    for d, n in sorted(per_day_blocks.items()):
        if n > cap:
            sacrifices.append(f"{d} carries {n} blocks (cap {cap})")

    # Coverage vs est.
    for i, r in enumerate(reqs):
        got = len(placement.get(i, [])) * step / 60.0
        if got + 1e-6 < r["est"]:
            sacrifices.append(
                f"'{r['title']}' gets {got:.2f}h of {r['est']}h")
    return {"blocks": blocks, "sacrifices": sacrifices,
            "per_day_blocks": dict(per_day_blocks)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default=None)
    ap.add_argument("--candidates-per-profile", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    spec = load_spec(args.spec)
    rng = random.Random(args.seed)
    out = {"week_start": spec["week_start"], "candidates": []}

    for pname, base in PROFILES.items():
        for k in range(args.candidates_per_profile):
            w = fuzz_weights(base, rng)
            sol = solve_once(spec, w)
            if sol is None:
                out["candidates"].append({
                    "profile": pname, "weights": w,
                    "status": "INFEASIBLE",
                    "note": "hard requirements cannot all be scheduled this week",
                })
                continue
            out["candidates"].append({
                "profile": pname, "weights": w, "status": "ok",
                "blocks": sol["blocks"],
                "per_day_blocks": sol["per_day_blocks"],
                "sacrifices": sol["sacrifices"] or ["nothing obvious"],
            })

    text = json.dumps(out, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
