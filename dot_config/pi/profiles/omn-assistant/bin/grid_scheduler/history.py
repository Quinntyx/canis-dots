"""Adopt only elapsed legacy coloring; never infer that its work was done."""
import hashlib
import json

from scheduler import sources
from scheduler.common import hhmm_to_minutes

from .grid import prepare
from .schema import CELLS, FREE, STEP, Color, ceil_slot


def seed_legacy_prefix(problem, tasks):
    from .adapter import task_date
    painted, _ = prepare(problem)
    grid = [c if c is not None else FREE for c in painted]
    palette = {c.key: c for c in problem.colors}
    sealed = []
    occupied = set()
    for task in sorted(tasks, key=lambda t: str(t.get("uuid"))):
        if task.get("status") not in {"pending", "completed"} or "managed" not in task.get("tags", []):
            continue
        day = task_date(task)
        if day is None or not task.get("starttime") or not task.get("endtime"):
            continue
        base = (day - problem.week_start).days * 1440
        start, end = hhmm_to_minutes(task["starttime"]), hhmm_to_minutes(task["endtime"])
        if end <= start:
            end += 1440
        lo, hi = max(0, (base + start) // STEP), min(problem.prefix, ceil_slot(base + end))
        if lo >= hi:
            continue
        sealed.append(dict(task))
        if "fixed" in task.get("tags", []):
            # Authoritative overlays already paint registrations; don't invent
            # a second event/color from a stale derived task label or room.
            continue
        physical = [task.get("location") or "At home", task.get("transport") or "no-car"]
        refs = sorted(sources._todo_refs(task))
        role = ["work" if refs else "support", refs or task.get("description"), *physical]
        key = "history:" + hashlib.sha256(json.dumps(role, sort_keys=True).encode()).hexdigest()[:16]
        if key not in palette:
            color = Color(key, "work" if refs else "support", windows=(),
                          location=physical[0], transport=physical[1])
            problem.colors.append(color)
            palette[key] = color
        for cell in range(lo, hi):
            if cell in occupied:
                raise ValueError(f"historical managed blocks overlap at cell {cell}")
            if grid[cell] != FREE:
                raise ValueError(f"historical managed block contradicts fixed occupancy at cell {cell}")
            grid[cell] = key
            occupied.add(cell)
    problem.previous = grid[:problem.prefix] + [FREE] * (CELLS - problem.prefix)
    problem.metadata["sealed_legacy_records"] = sealed
    problem.metadata["history_note"] = "Elapsed legacy coloring retained; pending calendar time gives zero completion credit."
