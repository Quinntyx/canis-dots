"""Deterministic prepainting, domains, and run extraction (no Z3)."""
from itertools import pairwise

from .schema import CELLS, FREE, ROWS, STEP, Color, Problem, ceil_slot, eligible


def prepare(problem: Problem) -> tuple[list[str | None], list[set[str]]]:
    problem.validate()
    painted: list[str | None] = [None] * CELLS
    if problem.prefix:
        # Without an old version, elapsed time is unavailable, not invented work.
        painted[:problem.prefix] = (problem.previous[:problem.prefix]
                                   if problem.previous is not None else [FREE] * problem.prefix)
    palette = {c.key: c for c in problem.colors}
    reservations = sorted(problem.reservations, key=lambda r: (r.start_minute, r.end_minute, r.id))
    for n, first in enumerate(reservations):
        for second in reservations[n + 1:]:
            if second.start_minute >= first.end_minute:
                break
            if (first.color != second.color and
                    all(palette[c].kind not in {"sleep", "unavailable"} for c in (first.color, second.color))):
                raise ValueError(f"exact fixed collision: {first.id}/{second.id}")
    exact_commitments = [r for r in reservations if palette[r.color].kind not in {"sleep", "unavailable"}]
    for first, second in pairwise(exact_commitments):
        legacy_gap = problem.gaps.get((first.color, second.color), 0)
        contiguous_visit = first.color == second.color and first.end_minute == second.start_minute
        travel = 0 if contiguous_visit else max(palette[first.color].travel_after,
                                               palette[second.color].travel_before)
        gap = max(legacy_gap, travel)
        if second.end_minute <= problem.prefix * STEP or not gap:
            continue
        free_cells = second.start_minute // STEP - ceil_slot(first.end_minute)
        if free_cells < gap:
            noun = "travel" if travel else "gap"
            raise ValueError(f"fixed transition {noun}: {first.id}->{second.id} needs {gap} cells")
    covering = [[] for _ in range(CELLS)]
    for reservation in reservations:
        for i in range(max(0, reservation.start_minute // STEP), min(CELLS, ceil_slot(reservation.end_minute))):
            covering[i].append(reservation.color)
    for i, fixed_colors in enumerate(covering):
        if not fixed_colors:
            continue
        if i < problem.prefix and problem.previous is not None:
            if painted[i] not in fixed_colors:
                raise ValueError(f"fixed reservation contradicts sealed history at {i}")
            continue
        # Adjacent exact events can share a rounding envelope. Its visible
        # color is deterministic; *all* identities and times remain in the
        # reservation overlay, and all their transition restrictions apply.
        painted[i] = min(fixed_colors, key=lambda c: palette[c].kind in {"sleep", "unavailable"})
    # Declared travel buffers remain genuinely FREE, not fake activities.
    # Their fixed endpoints stay exact in the overlay.
    for reservation in reservations:
        before = range(max(0, (reservation.start_minute - reservation.buffer_before) // STEP),
                       max(0, reservation.start_minute // STEP))
        after = range(min(CELLS, ceil_slot(reservation.end_minute)),
                      min(CELLS, ceil_slot(reservation.end_minute + reservation.buffer_after)))
        for i in (*before, *after):
            if i < problem.prefix:
                continue
            if painted[i] not in (None, FREE):
                raise ValueError(f"fixed buffer collision: {reservation.id} at cell {i}")
            painted[i] = FREE
    domains = [{FREE} if p is None else {p} for p in painted]
    for color in problem.colors:
        if not color.movable:
            continue
        slots = eligible(color.windows)
        if color.kind == "travel":
            slots -= eligible(problem.metadata.get("cancelled_travel_windows", []))
        if color.kind == "work":
            slots &= set().union(*(eligible(i.windows) for i in problem.items if i.color == color.key))
        for i in slots:
            if i < problem.prefix or painted[i] is not None:
                continue
            allowed = True
            for r in reservations:
                lo, hi = r.start_minute // STEP, ceil_slot(r.end_minute)
                before = problem.gaps.get((color.key, r.color), 0)
                after = problem.gaps.get((r.color, color.key), 0)
                if (i < lo and i + 1 + before > lo) or (i >= hi and i < hi + after):
                    allowed = False
                    break
            if allowed:
                domains[i].add(color.key)
    return painted, domains


def runs(grid: list[str], *, start: int = 0, kinds: dict[str, Color] | None = None) -> list[dict]:
    """Day-bounded runs; there is never a block spanning midnight."""
    output = []
    i = start
    while i < CELLS:
        end = i + 1
        while end < CELLS and end // ROWS == i // ROWS and grid[end] == grid[i]:
            end += 1
        if grid[i] != FREE and (kinds is None or kinds[grid[i]].movable):
            output.append({"color": grid[i], "start": i, "end": end, "cells": end - i})
        i = end
    return output


def matrix(grid: list[str]) -> list[list[str]]:
    """96 rows (time of day), 7 columns (Monday to Sunday)."""
    return [[grid[d * ROWS + row] for d in range(7)] for row in range(ROWS)]
