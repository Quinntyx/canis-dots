"""Item layout in colored capacity, entirely ordinary Python.

A lower/upper-bound bipartite flow certifies shared-color coverage. Its
residual min-cut yields a *color capacity* rule when a coloring misses item
windows. Run-topology requirements (whole items / minimum pieces) use a
bounded exact search; timeout is UNKNOWN, never proof of infeasibility.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from .schema import ROWS, Item, Problem, eligible


@dataclass
class Layout:
    status: str
    owners: dict[int, str]
    cut: tuple[str, set[int], int] | None = None
    note: str | None = None
    rejected_color: str | None = None


class Flow:
    def __init__(self, n: int):
        self.edges = [[] for _ in range(n)]

    def add(self, u: int, v: int, capacity: int):
        forward = [v, capacity, len(self.edges[v])]
        reverse = [u, 0, len(self.edges[u])]
        self.edges[u].append(forward)
        self.edges[v].append(reverse)
        return forward

    def augment(self, source: int, sink: int) -> int:
        total = 0
        while True:
            levels = [-1] * len(self.edges)
            levels[source] = 0
            queue = deque([source])
            while queue:
                u = queue.popleft()
                for v, capacity, _ in self.edges[u]:
                    if capacity and levels[v] < 0:
                        levels[v] = levels[u] + 1
                        queue.append(v)
            if levels[sink] < 0:
                return total
            indexes = [0] * len(self.edges)

            def push(u, amount, indexes=indexes, levels=levels):
                if u == sink:
                    return amount
                while indexes[u] < len(self.edges[u]):
                    edge = self.edges[u][indexes[u]]
                    v, capacity, reverse = edge
                    if capacity and levels[v] == levels[u] + 1:
                        sent = push(v, min(amount, capacity))
                        if sent:
                            edge[1] -= sent
                            self.edges[v][reverse][1] += sent
                            return sent
                    indexes[u] += 1
                return 0

            while sent := push(source, 100000):
                total += sent

    def reachable(self, source: int) -> set[int]:
        seen = {source}
        queue = deque([source])
        while queue:
            for v, capacity, _ in self.edges[queue.popleft()]:
                if capacity and v not in seen:
                    seen.add(v)
                    queue.append(v)
        return seen


def flow_layout(color: str, members: list[Item], cells: set[int]) -> Layout:
    ordered = sorted(cells)
    source, sink = 0, 1
    item_nodes = {item.id: n + 2 for n, item in enumerate(members)}
    cell_nodes = {cell: n + 2 + len(members) for n, cell in enumerate(ordered)}
    network = Flow(2 + len(members) + len(ordered))
    source_edges = {}
    assignments = {}
    for item in members:
        node = item_nodes[item.id]
        source_edges[item.id] = network.add(source, node, item.minimum)
        for cell in sorted(cells & eligible(item.windows)):
            assignments[(item.id, cell)] = network.add(node, cell_nodes[cell], 1)
    for cell in ordered:
        network.add(cell_nodes[cell], sink, 1)
    sent = network.augment(source, sink)
    if sent < sum(item.minimum for item in members):
        reachable = network.reachable(source)
        subset = [item for item in members if item_nodes[item.id] in reachable]
        union = set().union(*(eligible(item.windows) for item in subset))
        return Layout("invalid", {}, (color, union, sum(i.minimum for i in subset)),
                      "shared-color capacity misses item windows")
    # Mandatory lower bounds were met. Add optional capacity, preserving the
    # lower bounds: residual rerouting changes cells, never source inflow.
    for item in members:
        source_edges[item.id][1] += item.maximum - item.minimum
    sent += network.augment(source, sink)
    if sent != len(cells):
        return Layout("invalid", {}, note="colored cells exceed eligible item upper bounds")
    owners = {cell: rid for (rid, cell), edge in assignments.items() if edge[1] == 0}
    return Layout("ok", owners)


def segments(cells: set[int]) -> list[tuple[int, int]]:
    result = []
    for cell in sorted(cells):
        if result and result[-1][1] == cell and (cell - 1) // ROWS == cell // ROWS:
            result[-1] = (result[-1][0], cell + 1)
        else:
            result.append((cell, cell + 1))
    return result


def pieces(owners: dict[int, str], rid: str) -> list[tuple[int, int]]:
    return segments({cell for cell, owner in owners.items() if owner == rid})


def topology_valid(items: list[Item], owners: dict[int, str]) -> bool:
    for item in items:
        chunks = pieces(owners, item.id)
        if item.indivisible and (len(chunks) > 1 or (not chunks and item.minimum)):
            return False
        if any(end - start < item.min_piece for start, end in chunks):
            return False
    return True


def pack_color(color: str, items: list[Item], cells: set[int], deadline: float) -> Layout:
    initial = flow_layout(color, items, cells)
    if initial.status != "ok" or topology_valid(items, initial.owners):
        return initial
    strict = sorted([i for i in items if i.indivisible or i.min_piece > 1],
                    key=lambda i: (len(eligible(i.windows) & cells), -i.minimum, i.id))
    loose = [i for i in items if i not in strict]
    memo = set()

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError("item-layout search timed out")

    def placements(item: Item, available: set[int]):
        allowed = eligible(item.windows) & available
        # Select chronological contiguous pieces. Enumerate *all* positions,
        # not just run edges; another item may need the edge for its deadline.
        def choose(left, lower, selected):
            check_time()
            if left == 0:
                yield selected
                return
            for a, b in segments(allowed):
                for start in range(max(a, lower), b):
                    check_time()
                    for length in range(min(b - start, left), item.min_piece - 1, -1):
                        remainder = left - length
                        if remainder and (item.indivisible or remainder < item.min_piece):
                            continue
                        # A one-cell gap between pieces of the same item avoids
                        # duplicate representations of a single contiguous run.
                        next_start = start + length
                        if next_start % ROWS:
                            next_start += 1
                        yield from choose(remainder, next_start,
                                          selected | set(range(start, start + length)))
        for amount in range(min(item.maximum, len(allowed)), item.minimum - 1, -1):
            yield from choose(amount, 0, set())

    def search(index, available, owners):
        check_time()
        key = (index, frozenset(available))
        if key in memo:
            return None
        if index == len(strict):
            result = flow_layout(color, loose, available)
            return {**owners, **result.owners} if result.status == "ok" else None
        item = strict[index]
        for selected in placements(item, available):
            remaining = available - selected
            rest = strict[index + 1:] + loose
            # Cheap valid pruning; no layout cut from this conditional branch.
            if flow_layout(color, rest, remaining).status != "ok":
                continue
            found = search(index + 1, remaining, {**owners, **{c: item.id for c in selected}})
            if found is not None:
                return found
        memo.add(key)
        return None

    try:
        owners = search(0, cells, {})
    except TimeoutError as exc:
        return Layout("unknown", {}, note=str(exc))
    return (Layout("ok", owners) if owners is not None else
            Layout("invalid", {}, note="no whole-item/minimum-piece layout for this coloring"))


def allocate(problem: Problem, grid: list[str], deadline: float) -> Layout:
    owners = {}
    for color in problem.colors:
        if color.kind != "work":
            continue
        cells = {i for i in range(problem.prefix, len(grid)) if grid[i] == color.key}
        members = [item for item in problem.items if item.color == color.key]
        result = pack_color(color.key, members, cells, deadline)
        if result.status != "ok":
            result.rejected_color = color.key
            return result
        owners.update(result.owners)
    return Layout("ok", owners)
