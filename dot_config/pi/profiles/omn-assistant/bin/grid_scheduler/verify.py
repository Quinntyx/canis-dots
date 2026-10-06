"""Independent certificate checker. Used again before any Taskwarrior write."""
from collections import Counter

from .grid import matrix, prepare, runs
from .layout import pieces
from .schema import CELLS, FREE, ROWS, Problem, eligible


def verify(problem: Problem, candidate: dict) -> list[str]:
    from .checks import policy_errors, source_errors
    errors = source_errors(problem)
    try:
        _, domains = prepare(problem)
    except ValueError as exc:
        return [str(exc)]
    grid = candidate.get("grid", [])
    if len(grid) != CELLS or any(not isinstance(c, str) for c in grid):
        return ["grid must contain 672 color keys"]
    if any(color not in domains[cell] for cell, color in enumerate(grid)):
        return ["grid violates prepainting, sealed prefix, or eligibility"]
    palette = {c.key: c for c in problem.colors}
    counts = Counter(grid[problem.prefix:])
    for color in problem.colors:
        if not color.movable:
            continue
        if not color.minimum <= counts[color.key] <= color.maximum:
            errors.append(f"amount bounds violated: {color.key}")
        for day, (minimum, maximum) in color.daily.items():
            amount = grid[max(problem.prefix, day * ROWS):(day + 1) * ROWS].count(color.key)
            if not minimum <= amount <= maximum:
                errors.append(f"daily bounds violated: {color.key}/{day}")
    extracted = runs(grid, start=problem.prefix, kinds=palette)
    for run in extracted:
        color = palette[run["color"]]
        if not color.min_run <= run["cells"] <= color.max_run:
            errors.append(f"run length violated: {color.key}/{run['start']}")
        if (color.follows and run["start"] // ROWS not in color.follows_exceptions
                and (run["start"] == 0 or grid[run["start"] - 1] != color.follows)):
            errors.append(f"predecessor violated: {color.key}")
    errors.extend(policy_errors(problem, grid, extracted))
    if candidate.get("runs") != extracted:
        errors.append("run extraction differs from grid")
    if candidate.get("matrix") != matrix(grid):
        errors.append("matrix differs from grid")
    from .travel import certificate_errors
    errors.extend(certificate_errors(problem, grid))
    # Old FREE-gap certificates can prove historical occupancy for sealing,
    # never enter the current solver or publication path.
    if problem.source == "history":
        previous = None
        for cell, color in enumerate(grid):
            if color == FREE:
                continue
            if previous is not None:
                old_cell, old_color = previous
                if cell >= problem.prefix:
                    gap = problem.gaps.get((old_color, color), 0)
                    if cell - old_cell - 1 < gap:
                        errors.append(f"historical transition gap violated: {old_color}->{color}/{cell}")
            previous = cell, color
    try:
        owners = {int(cell): rid for cell, rid in candidate.get("owners", {}).items()}
    except (ValueError, TypeError):
        return errors + ["malformed item owners"]
    work_cells = {i for i in range(problem.prefix, CELLS) if palette.get(grid[i]) and palette[grid[i]].kind == "work"}
    if set(owners) != work_cells:
        errors.append("item layout does not own exactly the mutable work cells")
    items = {item.id: item for item in problem.items}
    for cell, rid in owners.items():
        item = items.get(rid)
        if item is None or not 0 <= cell < CELLS:
            errors.append("item layout contains unknown item/cell")
        elif grid[cell] != item.color or cell not in eligible(item.windows):
            errors.append(f"item window/color violated: {rid}")
    for item in problem.items:
        chunks = pieces(owners, item.id)
        amount = sum(b - a for a, b in chunks)
        if not item.minimum <= amount <= item.maximum:
            errors.append(f"item amount violated: {item.id}")
        if item.indivisible and (len(chunks) > 1 or (not chunks and item.minimum)):
            errors.append(f"whole-item rule violated: {item.id}")
        if any(b - a < item.min_piece for a, b in chunks):
            errors.append(f"minimum-piece rule violated: {item.id}")
    return errors
