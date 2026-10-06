"""Independent integer metrics on a coloring, including outing boundaries."""
from .grid import runs
from .schema import CELLS, FREE, ROWS, TRAVEL


def group_counts(problem, grid):
    result = {}
    for group in problem.groups:
        members = set(group.colors)
        counts = []
        for day in range(7):
            starts, active, idle = 0, False, 0
            for cell in range(max(problem.prefix, day * ROWS), (day + 1) * ROWS):
                color = grid[cell]
                if color in members:
                    starts += not active
                    active, idle = True, 0
                elif color == TRAVEL:
                    continue
                elif color == FREE:
                    idle += 1
                    active = active and idle <= group.max_free_gap
                else:
                    active, idle = False, 0
            counts.append(starts)
        result[group.key] = counts
    return result


def fragmentation_cost(problem, grid):
    counts = group_counts(problem, grid)
    return len(runs(grid, start=problem.prefix, kinds={c.key: c for c in problem.colors})) + CELLS * sum(
        sum(counts[g.key]) for g in problem.groups if g.prefer_fewer_runs)


def preferred_amount(problem, grid):
    return sum(grid[problem.prefix:].count(c.key) for c in problem.colors if c.prefer_maximum)
