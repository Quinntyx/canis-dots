"""Z3 sees only Boolean cell colors and local/pseudo-Boolean coloring rules.

No start/end/duration variables, item allocation variables, day binning,
modulo arithmetic, or disjunctive interval packing. Item-window capacity
cuts are learned from the ordinary-Python layout certifier.
"""
from __future__ import annotations

import time

import z3

from .grid import matrix, prepare, runs
from .layout import allocate
from .metrics import fragmentation_cost, preferred_amount
from .schema import CELLS, FREE, ROWS, TRAVEL, Problem


class Coloring:
    def __init__(self, problem: Problem):
        self.problem = problem
        _, self.domains = prepare(problem)
        self.solver = z3.Solver()
        self.bits = {}
        self.starts = []
        self.preferred_group_starts = []
        work_starts = {d: [] for d in range(7)}
        self.rule_count = 0
        self.variables = 0
        for cell, domain in enumerate(self.domains):
            if len(domain) == 1:
                self.bits[cell] = {next(iter(domain)): z3.BoolVal(True)}
            else:
                self.bits[cell] = {c: z3.Bool(f"cell_{cell}_{n}")
                                   for n, c in enumerate(sorted(domain))}
                self.variables += len(domain)
                self.add(z3.PbEq([(b, 1) for b in self.bits[cell].values()], 1))
        for color in problem.colors:
            if not color.movable:
                continue
            self.amount(color.key, range(problem.prefix, CELLS), color.minimum, color.maximum)
            for day, bounds in color.daily.items():
                self.amount(color.key, range(max(day * ROWS, problem.prefix), (day + 1) * ROWS), *bounds)
            color_starts = {}
            for cell in range(problem.prefix, CELLS):
                here = self.at(cell, color.key)
                if color.key not in self.domains[cell]:
                    continue
                # A suffix starting mid-run is a new planned block; history is
                # fixed but isn't counted as newly done work or free capacity.
                boundary = cell == problem.prefix or cell % ROWS == 0
                before = z3.BoolVal(False) if boundary else self.at(cell - 1, color.key)
                beginning = z3.And(here, z3.Not(before))
                self.starts.append(beginning)
                color_starts[cell] = beginning
                if color.kind == "work":
                    work_starts[cell // ROWS].append(beginning)
                if color.follows and cell // ROWS not in color.follows_exceptions:
                    self.add(z3.Implies(beginning, self.at(cell - 1, color.follows)))
                if color.min_run > 1:
                    if cell % ROWS + color.min_run > ROWS or cell + color.min_run > CELLS:
                        self.add(z3.Not(beginning))
                    else:
                        self.add(z3.Implies(beginning, z3.And(
                            [self.at(j, color.key) for j in range(cell, cell + color.min_run)])))
                if cell % ROWS + color.max_run < ROWS:
                    self.add(z3.Not(z3.And([self.at(j, color.key)
                                           for j in range(cell, cell + color.max_run + 1)])))
            if color.daily_max_runs is not None:
                for day in range(7):
                    terms = [(b, 1) for i, b in color_starts.items() if i // ROWS == day]
                    if terms:
                        self.add(z3.PbLe(terms, color.daily_max_runs))
            if color.same_start_daily:
                days = [d for d, quota in color.daily.items() if quota[0] > 0 and d not in color.same_start_exceptions]
                for day in days[1:]:
                    for row in range(ROWS):
                        self.add(color_starts.get(day * ROWS + row, z3.BoolVal(False)) ==
                                 color_starts.get(days[0] * ROWS + row, z3.BoolVal(False)))
        for day, limit in problem.daily_max_work_runs.items():
            terms = [(b, 1) for b in work_starts[day]]
            if terms:
                self.add(z3.PbLe(terms, limit))
        work_colors = [c.key for c in problem.colors if c.kind == "work"]
        for day, limit in problem.daily_max_work_cells.items():
            terms = [(self.at(i, c), 1) for i in range(max(problem.prefix, day * ROWS), (day + 1) * ROWS)
                     for c in work_colors if c in self.domains[i]]
            if terms:
                self.add(z3.PbLe(terms, limit))
        # Necessary whole-item capacity, expressed only as Boolean colors.
        # Each indivisible item needs at least one contiguous patch in its own
        # windows. No item placement/day decision variable is introduced; Python
        # still certifies disjoint allocation. This avoids learning one entire
        # color mask at a time for an obviously fragmented two-hour todo.
        for item in problem.items:
            if not item.indivisible or item.minimum <= 1:
                continue
            size = item.minimum
            patches = []
            for lo, hi in item.windows:
                for start in range(max(lo, problem.prefix), hi - size + 1):
                    if start // ROWS != (start + size - 1) // ROWS:
                        continue
                    cells = range(start, start + size)
                    if all(item.color in self.domains[i] for i in cells):
                        patches.append(z3.And([self.at(i, item.color) for i in cells]))
            self.add(z3.Or(patches))
        # Linear local automata: reserved travel bridges an outing without
        # consuming its FREE-gap allowance; unrelated activities reset it.
        for group in problem.groups:
            for day in range(7):
                floor, end = max(problem.prefix, day * ROWS), (day + 1) * ROWS
                beginnings = []
                states = [z3.BoolVal(False)] * (group.max_free_gap + 1)
                for i in range(floor, end):
                    here = z3.Or([self.at(i, c) for c in group.colors])
                    if set(group.colors) & self.domains[i]:
                        beginnings.append(z3.And(here, z3.Not(z3.Or(states))))
                    old = states
                    states = [z3.Or(here, z3.And(self.at(i, TRAVEL), old[0]))]
                    states.extend(z3.Or(z3.And(self.at(i, TRAVEL), old[n]),
                                        z3.And(self.at(i, FREE), old[n - 1]))
                                  for n in range(1, group.max_free_gap + 1))
                if beginnings:
                    self.add(z3.PbLe([(b, 1) for b in beginnings], group.max_runs_per_day))
                    if group.prefer_fewer_runs:
                        self.preferred_group_starts.extend(beginnings)
        # Travel is a real reserved color, not FREE padding. Minimum demands
        # on either end share the same contiguous run (max, never a sum).
        from .travel import anchors, transfers
        fixed_edges = [edge for edge in anchors(problem)]
        left_seeds, right_seeds = set(), set()
        for edge, side, count in fixed_edges:
            cells = range(edge - count, edge) if side == "before" else range(edge, edge + count)
            self.add(z3.And([self.at(i, TRAVEL) for i in cells]))
            (right_seeds if side == "before" else left_seeds).add(edge - 1 if side == "before" else edge)
        # Direct transfers: solver picks per gap between direct venue-to-venue
        # routing (travel painted immediately before the later event) or the
        # classic home detour on both outer edges.
        transfer_flags = {}
        palette_all = {c.key: c for c in problem.colors}
        for n, t in enumerate(transfers(problem)):
            lo, hi, slots = t["after_edge"], t["before_edge"], t["slots"]
            tcells = list(range(hi - slots, hi))
            outside = list(range(lo, hi - slots))
            flag = z3.Bool(f"direct_transfer_{n}")
            from_color, to_color = palette_all[t["from_color"]], palette_all[t["to_color"]]
            self.add(z3.Implies(flag, z3.And(
                [self.at(i, TRAVEL) for i in tcells if TRAVEL in self.domains[i]] +
                [z3.Not(self.at(i, TRAVEL)) for i in outside if TRAVEL in self.domains[i]] +
                [z3.Not(self.at(i, c.key)) for i in outside for c in problem.colors
                 if c.kind == "support" and c.key in self.domains[i]])))
            self.add(z3.Implies(z3.Not(flag), z3.And(
                [self.at(i, TRAVEL) for i in range(lo, lo + from_color.travel_after)
                 if TRAVEL in self.domains[i]] +
                [self.at(i, TRAVEL) for i in range(hi - to_color.travel_before, hi)
                 if TRAVEL in self.domains[i]])))
            transfer_flags[(t["from_color"], "after", lo)] = flag
            transfer_flags[(t["to_color"], "before", hi)] = flag
        for color in problem.colors:
            if not color.travel_before and not color.travel_after:
                continue
            for i in range(CELLS):
                if color.key not in self.domains[i]:
                    continue
                inherited = i == 0 and any(r.color == color.key and r.start_minute < 0 < r.end_minute
                                            for r in problem.reservations)
                continuing = i + 1 == CELLS and any(r.color == color.key and r.end_minute > CELLS * 15
                                                   for r in problem.reservations)
                if i >= problem.prefix and color.travel_before and not inherited:
                    beginning = z3.And(self.at(i, color.key), z3.Not(self.at(i - 1, color.key)))
                    guard = transfer_flags.get((color.key, "before", i))
                    trigger = beginning if guard is None else z3.And(beginning, z3.Not(guard))
                    self.add(z3.Implies(trigger, z3.And(
                        [self.at(j, TRAVEL) for j in range(i - color.travel_before, i)])))
                if i + 1 + color.travel_after > problem.prefix and color.travel_after and not continuing:
                    ending = z3.And(self.at(i, color.key), z3.Not(self.at(i + 1, color.key)))
                    guard = transfer_flags.get((color.key, "after", i + 1))
                    trigger = ending if guard is None else z3.And(ending, z3.Not(guard))
                    self.add(z3.Implies(trigger, z3.And(
                        [self.at(j, TRAVEL) for j in range(i + 1, i + 1 + color.travel_after)])))
        # Linear local propagation: every travel cell connects to an adjacent
        # visit needing travel. No quadratic lookahead or invented idle trips.
        left, right = {}, {}
        for i in range(CELLS):
            seed = z3.Or(z3.BoolVal(i in left_seeds), *[
                self.at(i - 1, c.key) for c in problem.colors if c.travel_after])
            left[i] = z3.And(self.at(i, TRAVEL), z3.Or(seed, left.get(i - 1, z3.BoolVal(False))))
        for i in reversed(range(CELLS)):
            seed = z3.Or(z3.BoolVal(i in right_seeds), *[
                self.at(i + 1, c.key) for c in problem.colors if c.travel_before])
            right[i] = z3.And(self.at(i, TRAVEL), z3.Or(seed, right.get(i + 1, z3.BoolVal(False))))
            if i >= problem.prefix and TRAVEL in self.domains[i]:
                self.add(z3.Implies(self.at(i, TRAVEL), z3.Or(left[i], right[i])))
    def at(self, cell: int, color: str):
        return self.bits.get(cell, {}).get(color, z3.BoolVal(False))

    def add(self, rule):
        self.solver.add(rule)
        self.rule_count += 1

    def amount(self, color, cells, minimum, maximum):
        terms = [(self.at(cell, color), 1) for cell in cells if color in self.domains[cell]]
        if not terms:
            self.add(z3.BoolVal(minimum == 0))
        else:
            self.add(z3.PbGe(terms, minimum))
            self.add(z3.PbLe(terms, maximum))

    def read(self) -> list[str]:
        model = self.solver.model()
        return [next(color for color, bit in self.bits[i].items()
                     if z3.is_true(model.eval(bit, model_completion=True))) for i in range(CELLS)]

    def run_bound(self, bound):
        terms = [(s, 1) for s in self.starts] + [(s, CELLS) for s in self.preferred_group_starts]
        return z3.PbLe(terms, bound) if terms else z3.BoolVal(bound >= 0)

    def travel_bound(self, maximum):
        terms = [(self.at(i, TRAVEL), 1) for i in range(self.problem.prefix, CELLS)
                 if TRAVEL in self.domains[i]]
        return z3.PbLe(terms, maximum) if terms else z3.BoolVal(maximum >= 0)

    def amount_floor(self, minimum):
        terms = [(self.at(i, c.key), 1) for c in self.problem.colors if c.prefer_maximum
                 for i in range(self.problem.prefix, CELLS) if c.key in self.domains[i]]
        return z3.PbGe(terms, minimum) if terms else z3.BoolVal(minimum <= 0)

    def early_bound(self, bound):
        terms = [(self.at(i, c.key), i + 1) for c in self.problem.colors if c.kind == "work"
                 for i in range(self.problem.prefix, CELLS) if c.key in self.domains[i]]
        return z3.PbLe(terms, bound) if terms else z3.BoolVal(bound >= 0)

    def exclude(self, grid, color=None):
        # Reject precisely the failed color's occupancy mask. Other colors
        # cannot rescue a todo packing failure for these same cells; excluding
        # their arrangements one by one would merely enumerate irrelevant
        # symmetries. This is a proved nogood, never a chosen day assignment.
        if color is None:
            changed = [z3.Not(self.at(i, grid[i])) for i in range(self.problem.prefix, CELLS)]
        else:
            changed = [self.at(i, color) != z3.BoolVal(grid[i] == color)
                       for i in range(self.problem.prefix, CELLS) if color in self.domains[i]]
        self.add(z3.Or(changed))


def solve(problem: Problem, *, timeout_ms: int = 10000, optimize: bool = True) -> dict:
    if problem.source == "history":
        raise ValueError("historical certificates are read-only; reload current sources to solve")
    started = time.monotonic()
    deadline = started + timeout_ms / 1000
    if timeout_ms <= 0:
        raise ValueError("timeout_ms must be positive")
    from .checks import capacity_errors, source_errors
    problem.validate()
    blockers = source_errors(problem)
    preparation_error = None
    try:
        _, domains = prepare(problem)
        shortages = capacity_errors(problem, domains)
    except ValueError as exc:
        preparation_error, shortages = str(exc), []
    if blockers or shortages or preparation_error:
        return {"status": "BLOCKED" if blockers else "INFEASIBLE", "engine": "grid-week/v1",
            "note": "; ".join(blockers) or preparation_error or "necessary coloring capacity is insufficient",
            "source_errors": blockers, "capacity_errors": shortages,
            "preparation_error": preparation_error, "optimization_exact": False,
            "fragmentation_exact": False,
            "stats": {"seconds": round(time.monotonic() - started, 4), "boolean_variables": 0,
                      "rules": 0, "solver_checks": 0, "layout_cuts": 0}}
    model = Coloring(problem)
    learned, checks = 0, 0
    palette = {c.key: c for c in problem.colors}
    # A proved lower bound on day-bounded color runs, not a day assignment.
    # Preferring long runs *before* todo packing avoids presenting the layout
    # stage with hundreds of arbitrary, heavily fragmented SAT colorings.
    run_floor = sum(max((c.minimum + c.max_run - 1) // c.max_run,
                        sum(lo > 0 for lo, _hi in c.daily.values()))
                    for c in problem.colors if c.movable)

    run_floor += CELLS * sum(any(palette[c].minimum for c in g.colors)
                             for g in problem.groups if g.prefer_fewer_runs)
    preferred_floor = None
    travel_ceiling = None

    def next_valid(bound=None, early=None, amount=None, travel=None):
        nonlocal learned, checks
        while time.monotonic() < deadline:
            remaining = max(1, int((deadline - time.monotonic()) * 1000))
            model.solver.set(timeout=remaining)
            checks += 1
            assumptions = [] if bound is None else [model.run_bound(bound)]
            if early is not None:
                assumptions.append(model.early_bound(early))
            if travel_ceiling is not None:
                assumptions.append(model.travel_bound(travel_ceiling))
            if travel is not None:
                assumptions.append(model.travel_bound(travel))
            if preferred_floor is not None:
                assumptions.append(model.amount_floor(preferred_floor))
            if amount is not None:
                assumptions.append(model.amount_floor(amount))
            preferred = False
            if optimize and bound is None and early is None and amount is None and preferred_floor is None and travel is None and travel_ceiling is None:
                # This is an objective probe, never a hard limit. UNSAT or
                # UNKNOWN here falls back to the complete unconstrained model.
                model.solver.set(timeout=min(remaining, 1000))
                result = model.solver.check(model.run_bound(run_floor))
                if result == z3.sat:
                    preferred = True
                else:
                    remaining = max(1, int((deadline - time.monotonic()) * 1000))
                    model.solver.set(timeout=remaining)
                    checks += 1
                    result = model.solver.check(*assumptions)
            else:
                result = model.solver.check(*assumptions)
            if result == z3.unsat:
                return "INFEASIBLE", None, None
            if result == z3.unknown:
                return "UNKNOWN", None, model.solver.reason_unknown()
            grid = model.read()
            if (optimize and bound is None and early is None and amount is None
                    and preferred_floor is None and travel is None and travel_ceiling is None and not preferred):
                lo, hi = run_floor, fragmentation_cost(problem, grid)
                # Keep some of the hard budget for external certification.
                preference_deadline = time.monotonic() + max(0, deadline - time.monotonic()) * 0.6
                while lo < hi and time.monotonic() < preference_deadline:
                    trial_bound = (lo + hi - 1) // 2
                    model.solver.set(timeout=max(1, int((preference_deadline - time.monotonic()) * 1000)))
                    checks += 1
                    trial_result = model.solver.check(model.run_bound(trial_bound))
                    if trial_result == z3.sat:
                        grid = model.read()
                        hi = fragmentation_cost(problem, grid)
                    elif trial_result == z3.unsat:
                        lo = trial_bound + 1
                    else:
                        break
            layout = allocate(problem, grid, deadline)
            if layout.status == "ok":
                return "ok", (grid, layout.owners), None
            if layout.status == "unknown":
                return "UNKNOWN", None, layout.note
            if layout.cut:
                color, cells, minimum = layout.cut
                cells = {c for c in cells if c >= problem.prefix}
                terms = [(model.at(c, color), 1) for c in sorted(cells) if color in model.domains[c]]
                model.add(z3.PbGe(terms, minimum) if terms else z3.BoolVal(minimum == 0))
            else:
                model.exclude(grid, layout.rejected_color)
            learned += 1
        return "UNKNOWN", None, "overall solve/layout budget exhausted"

    status, best, note = next_valid()
    travel_exact = not any(c.kind == "travel" for c in problem.colors)
    if best is not None and optimize and any(c.kind == "travel" for c in problem.colors):
        low, high = 0, best[0][problem.prefix:].count(TRAVEL)
        while low < high and time.monotonic() < deadline:
            trial_status, trial, trial_note = next_valid(travel=(low + high) // 2)
            if trial_status == "ok":
                best, high = trial, trial[0][problem.prefix:].count(TRAVEL)
            elif trial_status == "INFEASIBLE":
                low = (low + high) // 2 + 1
            else:
                note = trial_note
                break
        travel_ceiling, travel_exact = high, low == high
    amount_exact = not any(c.prefer_maximum for c in problem.colors)
    if best is not None and optimize and any(c.prefer_maximum for c in problem.colors):
        low = preferred_amount(problem, best[0])
        high = sum(c.maximum for c in problem.colors if c.prefer_maximum)
        while low < high and time.monotonic() < deadline:
            midpoint = (low + high + 1) // 2
            trial_status, trial, trial_note = next_valid(amount=midpoint)
            if trial_status == "ok":
                best, low = trial, preferred_amount(problem, trial[0])
            elif trial_status == "INFEASIBLE":
                high = midpoint - 1
            else:
                note = trial_note
                break
        preferred_floor, amount_exact = low, low == high
    exact = False
    if best is not None and optimize:
        low = run_floor
        high = fragmentation_cost(problem, best[0])
        while low < high and time.monotonic() < deadline:
            midpoint = (low + high - 1) // 2
            trial_status, trial, trial_note = next_valid(midpoint)
            if trial_status == "ok":
                best = trial
                high = fragmentation_cost(problem, best[0])
            elif trial_status == "INFEASIBLE":
                low = midpoint + 1
            else:
                note = trial_note
                break
        exact = low == high
        fragmentation_exact = exact
        if exact:
            run_limit = high
            low = 0
            high = sum(cell + 1 for cell in best[1])
            while low < high and time.monotonic() < deadline:
                midpoint = (low + high - 1) // 2
                trial_status, trial, trial_note = next_valid(run_limit, midpoint)
                if trial_status == "ok":
                    best = trial
                    high = sum(cell + 1 for cell in best[1])
                elif trial_status == "INFEASIBLE":
                    low = midpoint + 1
                else:
                    note = trial_note
                    break
            exact = low == high
    else:
        fragmentation_exact = False
    output = {
        "status": status, "engine": "grid-week/v1", "optimization_exact": exact and amount_exact and travel_exact,
        "travel_optimization_exact": travel_exact,
        "amount_optimization_exact": amount_exact,
        "fragmentation_exact": fragmentation_exact,
        "note": note, "stats": {"seconds": round(time.monotonic() - started, 4),
        "boolean_variables": model.variables, "rules": model.rule_count,
        "solver_checks": checks, "layout_cuts": learned},
    }
    if best is not None:
        grid, owners = best
        output.update(grid=grid, matrix=matrix(grid),
                      runs=runs(grid, start=problem.prefix, kinds=palette),
                      owners={str(c): rid for c, rid in sorted(owners.items())})
        # Independent regular-code certificate, not another invocation of SMT.
        from .verify import verify
        errors = verify(problem, output)
        if errors:
            raise RuntimeError("internal grid certificate failure: " + "; ".join(errors))
    return output
