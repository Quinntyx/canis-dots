"""Ordinary-Python policy and capacity checks; no placement heuristics."""
from .schema import CELLS, ROWS, eligible


def source_errors(problem):
    return [d["message"] for d in problem.metadata.get("diagnostics", [])
            if d.get("severity") == "blocking"]


def capacity_errors(problem, domains):
    """Necessary bounds only. Failure is proof; success is not certification."""
    errors = []
    for color in problem.colors:
        if not color.movable:
            continue
        available = {i for i in range(problem.prefix, CELLS) if color.key in domains[i]}
        if len(available) < color.minimum:
            errors.append({"kind": "color-capacity", "color": color.key,
                "required_cells": color.minimum, "available_cells": len(available)})
        for day, (minimum, _maximum) in color.daily.items():
            supply = len(available & set(range(day * ROWS, (day + 1) * ROWS)))
            if supply < minimum:
                errors.append({"kind": "daily-capacity", "color": color.key, "day": day,
                    "required_cells": minimum, "available_cells": supply})
    for item in problem.items:
        supply = sum(i >= problem.prefix and item.color in domains[i] for i in eligible(item.windows))
        if supply < item.minimum:
            errors.append({"kind": "item-capacity", "item": item.id, "title": item.title,
                "required_cells": item.minimum, "available_cells": supply})
    # Each cell supplies at most one color, including support obligations.
    movable = {c.key for c in problem.colors if c.movable}
    supply = sum(bool(domain & movable) for domain in domains[problem.prefix:])
    demand = sum(c.minimum for c in problem.colors if c.movable)
    if supply < demand:
        errors.append({"kind": "total-capacity", "required_cells": demand, "available_cells": supply})
    return errors


def policy_errors(problem, grid, extracted):
    palette = {c.key: c for c in problem.colors}
    work = [r for r in extracted if palette[r["color"]].kind == "work"]
    errors = []
    for color in problem.colors:
        own = [r for r in extracted if r["color"] == color.key]
        if color.daily_max_runs is not None:
            for day in range(7):
                if sum(r["start"] // ROWS == day for r in own) > color.daily_max_runs:
                    errors.append(f"daily color run limit violated: {color.key}/{day}")
        if color.same_start_daily:
            starts = [{r["start"] % ROWS for r in own if r["start"] // ROWS == day}
                      for day, quota in color.daily.items() if quota[0] > 0 and day not in color.same_start_exceptions]
            if starts and any(value != starts[0] for value in starts[1:]):
                errors.append(f"same daily start violated: {color.key}")
    for day, limit in problem.daily_max_work_runs.items():
        if sum(r["start"] // ROWS == day for r in work) > limit:
            errors.append(f"daily work run limit violated: {day}")
    for day, limit in problem.daily_max_work_cells.items():
        amount = sum(palette.get(grid[i]) is not None and palette[grid[i]].kind == "work"
                     for i in range(max(problem.prefix, day * ROWS), (day + 1) * ROWS))
        if amount > limit:
            errors.append(f"daily work cell limit violated: {day}")
    from .metrics import group_counts
    counts = group_counts(problem, grid)
    for group in problem.groups:
        for day in range(7):
            if counts[group.key][day] > group.max_runs_per_day:
                errors.append(f"color group limit violated: {group.key}/{day}")
    return errors
