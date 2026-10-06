"""Pure grid vocabulary. No solver, source access, or Taskwarrior writes.

Slots are half-open wall-clock quarters of an America/Chicago Monday-Sunday
week. Bounds are *remaining* demand in the mutable suffix, never inferred
completion credit from old calendar colors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

STEP = 15
ROWS = 96
DAYS = 7
CELLS = ROWS * DAYS
FREE = "free"
TRAVEL = "travel"


def ceil_slot(minutes: int) -> int:
    return -(-minutes // STEP)


def eligible(windows: list[tuple[int, int]]) -> set[int]:
    return {i for lo, hi in windows for i in range(max(0, lo), min(CELLS, hi))}


@dataclass(frozen=True)
class Color:
    key: str
    kind: str = "work"  # work/support/fixed/sleep/unavailable/free
    minimum: int = 0
    maximum: int = 0
    windows: tuple[tuple[int, int], ...] = ((0, CELLS),)
    min_run: int = 1
    max_run: int = ROWS
    daily: dict[int, tuple[int, int]] = field(default_factory=dict)
    location: str = "At home"
    transport: str = "no-car"
    topic: str = ""
    follows: str | None = None  # every new run immediately follows this color
    daily_max_runs: int | None = None
    same_start_daily: bool = False
    prefer_maximum: bool = False
    follows_exceptions: tuple[int, ...] = ()
    travel_before: int = 0  # adjacent TRAVEL cells, shared by neighboring runs
    travel_after: int = 0
    travel_origin: str = "At home"
    same_start_exceptions: tuple[int, ...] = ()

    @property
    def movable(self) -> bool:
        return self.kind in {"work", "support", "travel"}


@dataclass(frozen=True)
class Item:
    id: str
    title: str
    color: str
    minimum: int
    maximum: int
    windows: tuple[tuple[int, int], ...] = ((0, CELLS),)
    indivisible: bool = False
    min_piece: int = 1
    due: str | None = None
    travel: str | None = None
    reference: str | None = None  # Python occurrence identity may differ from durable source ID


@dataclass(frozen=True)
class Reservation:
    id: str
    color: str
    start_minute: int
    end_minute: int
    label: str = ""
    # Exact authority lives here, NOT in the rounded occupancy envelope.
    location: str | None = None
    buffer_before: int = 0
    buffer_after: int = 0


@dataclass(frozen=True)
class Group:
    key: str
    colors: tuple[str, ...]
    max_runs_per_day: int = 1
    max_free_gap: int = 2
    prefer_fewer_runs: bool = False


@dataclass
class Problem:
    week_start: date
    colors: list[Color]
    items: list[Item] = field(default_factory=list)
    reservations: list[Reservation] = field(default_factory=list)
    gaps: dict[tuple[str, str], int] = field(default_factory=dict)
    prefix: int = 0
    previous: list[str] | None = None
    source: str = "spec"
    metadata: dict = field(default_factory=dict)
    daily_max_work_runs: dict[int, int] = field(default_factory=dict)
    daily_max_work_cells: dict[int, int] = field(default_factory=dict)
    groups: list[Group] = field(default_factory=list)

    def validate(self) -> None:
        if self.week_start.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
        offsets = {datetime.combine(self.week_start + timedelta(days=d), datetime.min.time(), tz).utcoffset()
                   for d in range(8)}
        if len(offsets) != 1:
            raise ValueError("DST-transition weeks need an explicit wall-clock policy; 96x7 engine refuses them")
        keys = [c.key for c in self.colors]
        if len(keys) != len(set(keys)) or FREE in keys:
            raise ValueError("color keys must be unique; 'free' is reserved")
        if not 0 <= self.prefix <= CELLS:
            raise ValueError("prefix must be in 0..672")
        if self.previous is not None:
            if len(self.previous) != CELLS:
                raise ValueError("previous grid must contain exactly 672 cells")
            if any(c not in set(keys) | {FREE} for c in self.previous[:self.prefix]):
                raise ValueError("historical palette entries must remain in the palette")
        self._windows(self.metadata.get("cancelled_travel_windows", []))
        if len({i.id for i in self.items}) != len(self.items):
            raise ValueError("item IDs must be unique")
        for c in self.colors:
            if c.kind not in {"work", "support", "fixed", "sleep", "unavailable", "travel"}:
                raise ValueError(f"unknown kind for {c.key}")
            if any(not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= CELLS
                   for n in (c.travel_before, c.travel_after)):
                raise ValueError(f"invalid travel cells for {c.key}")
            if c.kind == "travel" and (c.key != TRAVEL or c.travel_before or c.travel_after):
                raise ValueError("travel is a reserved color and cannot require travel itself")
            if c.key == TRAVEL and c.kind != "travel":
                raise ValueError("travel is a reserved color")
            if (c.travel_before or c.travel_after) and not any(t.key == TRAVEL and t.kind == "travel" for t in self.colors):
                raise ValueError("travel requirements need the reserved travel color")
            if not 0 <= c.minimum <= c.maximum <= CELLS:
                raise ValueError(f"invalid amount bounds for {c.key}")
            if not 1 <= c.min_run <= c.max_run <= (CELLS if c.kind == "travel" else ROWS):
                raise ValueError(f"invalid run bounds for {c.key}")
            if c.follows is not None and c.follows not in keys:
                raise ValueError(f"unknown predecessor for {c.key}")
            if c.daily_max_runs is not None and not 0 <= c.daily_max_runs <= ROWS:
                raise ValueError(f"invalid daily run limit for {c.key}")
            if any(not 0 <= d < DAYS for d in c.same_start_exceptions):
                raise ValueError("invalid same-start exception date")
            if any(not 0 <= d < DAYS for d in c.follows_exceptions):
                raise ValueError(f"invalid predecessor exception for {c.key}")
            if c.prefer_maximum and not c.movable:
                raise ValueError(f"immutable color cannot have an amount objective: {c.key}")
            self._windows(c.windows)
            for d, (lo, hi) in c.daily.items():
                if not (0 <= d < DAYS and 0 <= lo <= hi <= ROWS):
                    raise ValueError(f"invalid daily amount for {c.key}")
        palette = {c.key: c for c in self.colors}
        # Deadlines are hard eligibility restrictions, not display-only due
        # annotations. Clamp each item's windows before the color-domain and
        # external layout stages; whole quarters must finish before due.
        from dataclasses import replace
        bounded = []
        for item in self.items:
            self._windows(item.windows)
            if item.due:
                value = str(item.due)
                if "T" in value:
                    due = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    due = (due if due.tzinfo else due.replace(tzinfo=tz)).astimezone(tz)
                else:
                    due = datetime.combine(date.fromisoformat(value), datetime.max.time(), tz)
                minutes = ((due.date() - self.week_start).days * 1440 + due.hour * 60 + due.minute
                           + (due.second + due.microsecond / 1_000_000) / 60)
                cutoff = min(CELLS, max(0, int(minutes // STEP)))
                item = replace(item, windows=tuple((lo, min(hi, cutoff)) for lo, hi in item.windows if lo < min(hi, cutoff)))
            bounded.append(item)
        self.items = bounded
        for item in self.items:
            if item.color not in palette or palette[item.color].kind != "work":
                raise ValueError(f"item {item.id} needs a work color")
            if not item.title.strip():
                raise ValueError(f"item {item.id} needs a nonempty title")
            if not 0 <= item.minimum <= item.maximum <= CELLS or item.maximum == 0:
                raise ValueError(f"invalid amount bounds for {item.id}")
            if not 1 <= item.min_piece <= item.maximum:
                raise ValueError(f"invalid minimum piece for {item.id}")
            self._windows(item.windows)
        for c in self.colors:
            members = [i for i in self.items if i.color == c.key]
            if c.kind == "work" and not members and c.maximum:
                raise ValueError(f"work color {c.key} has no todo items")
            if members and (c.minimum < sum(i.minimum for i in members)
                            or c.maximum > sum(i.maximum for i in members)):
                raise ValueError(f"color {c.key} amounts must fit its item amounts")
        for r in self.reservations:
            if r.color not in palette or palette[r.color].movable:
                raise ValueError(f"reservation {r.id} needs an immovable color")
            if not (r.start_minute < r.end_minute and r.end_minute > 0 and r.start_minute < CELLS * STEP):
                raise ValueError(f"reservation {r.id} must overlap the selected week")
            if (not isinstance(r.buffer_before, int) or not isinstance(r.buffer_after, int)
                    or min(r.buffer_before, r.buffer_after) < 0):
                raise ValueError(f"reservation {r.id} has invalid buffers")
            if (r.buffer_before or r.buffer_after) and self.source != "history":
                raise ValueError("reservation FREE buffers are legacy; declare travel on the activity color")
        for limits in (self.daily_max_work_runs, self.daily_max_work_cells):
            if any(not 0 <= d < DAYS or not 0 <= limit <= ROWS for d, limit in limits.items()):
                raise ValueError("daily work limits require day 0..6 and limit 0..96")
        if len({g.key for g in self.groups}) != len(self.groups):
            raise ValueError("group keys must be unique")
        for group in self.groups:
            if (not group.colors or any(c not in keys for c in group.colors)
                    or not 0 <= group.max_free_gap <= ROWS
                    or not 0 <= group.max_runs_per_day <= ROWS):
                raise ValueError(f"invalid color group {group.key}")
        for (a, b), gap in self.gaps.items():
            if a not in keys or b not in keys or not 0 <= gap <= ROWS or (a == b and gap):
                raise ValueError("gap rules need known colors and 0..96 cells")
            if gap and self.source != "history":
                raise ValueError("pairwise FREE gaps are legacy; use travel_before/travel_after and the travel color")

    @staticmethod
    def _windows(windows):
        if any(not (0 <= lo <= hi <= CELLS) for lo, hi in windows):
            raise ValueError("windows must be half-open slot ranges within 0..672")

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return {
            "schema": "grid-week/v1", "week_start": self.week_start.isoformat(),
            "resolution_minutes": STEP, "shape": [ROWS, DAYS],
            "colors": [asdict(c) for c in self.colors],
            "items": [asdict(i) for i in self.items],
            "reservations": [asdict(r) for r in self.reservations],
            "gaps": [{"from": a, "to": b, "cells": n}
                     for (a, b), n in sorted(self.gaps.items())],
            "prefix": self.prefix, "previous": self.previous,
            "source": self.source, "metadata": self.metadata,
            "daily_max_work_runs": self.daily_max_work_runs,
            "daily_max_work_cells": self.daily_max_work_cells,
            "groups": [asdict(g) for g in self.groups],
        }

    @classmethod
    def from_dict(cls, data: dict, *, history_only: bool = False) -> Problem:
        if data.get("resolution_minutes", STEP) != STEP:
            raise ValueError("the grid resolution is fixed at 15 minutes")
        if data.get("shape", [ROWS, DAYS]) != [ROWS, DAYS]:
            raise ValueError("the grid shape is fixed at 96 x 7")
        colors = []
        for raw in data["colors"]:
            raw = dict(raw)
            raw["windows"] = tuple(tuple(w) for w in raw.get("windows", [(0, CELLS)]))
            raw["daily"] = {int(d): tuple(bounds) for d, bounds in raw.get("daily", {}).items()}
            raw["follows_exceptions"] = tuple(raw.get("follows_exceptions", ()))
            raw["same_start_exceptions"] = tuple(raw.get("same_start_exceptions", ()))
            colors.append(Color(**raw))
        items = []
        for raw in data.get("items", []):
            raw = dict(raw)
            raw["windows"] = tuple(tuple(w) for w in raw.get("windows", [(0, CELLS)]))
            items.append(Item(**raw))
        problem = cls(
            week_start=date.fromisoformat(data["week_start"]), colors=colors, items=items,
            reservations=[Reservation(**r) for r in data.get("reservations", [])],
            gaps={(g["from"], g["to"]): int(g["cells"]) for g in data.get("gaps", [])},
            prefix=int(data.get("prefix", 0)), previous=data.get("previous"),
            source="history" if history_only else data.get("source", "spec"), metadata=dict(data.get("metadata", {})),
            daily_max_work_runs={int(d): int(n) for d, n in data.get("daily_max_work_runs", {}).items()},
            daily_max_work_cells={int(d): int(n) for d, n in data.get("daily_max_work_cells", {}).items()},
            groups=[Group(**dict(g, colors=tuple(g["colors"]))) for g in data.get("groups", [])],
        )
        problem.validate()
        return problem
