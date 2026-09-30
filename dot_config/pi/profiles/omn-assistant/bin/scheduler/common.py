"""Shared vocabulary for the schedule redesign.

Everything here is pure data + time arithmetic: no Z3, no subprocesses. The
model in :mod:`scheduler.model` consumes :class:`WeekInput` and never reads
omn or Taskwarrior itself.

Time is measured in *minutes from Monday 00:00 of the selected week* so that
every temporal constraint reduces to integer arithmetic on a finite grid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")

DAYS_PER_WEEK = 7
MINUTES_PER_DAY = 1440
MINUTES_PER_WEEK = DAYS_PER_WEEK * MINUTES_PER_DAY

# The linter credits a requirement in a block even when its record est is 0h,
# but it needs *some* block to reference it. Give zero-est requirements a tiny
# nominal allocation so coverage is provable and the todo bullet is emitted.
MIN_ALLOC_MINUTES = 10

BLOCKING = "blocking"
WARNING = "warning"
INFO = "info"

_EST_RE = re.compile(r"^([0-9]*\.?[0-9]+)\s*([hdm])$")
_HHMM_RE = re.compile(r"^(\d{1,2}):(\d{2})$")

WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


# ------------------------------------------------------------------ time maths


def normalize_week_start(value) -> date:
    """Coerce any date to the Monday of its Monday-Sunday week."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    return value - timedelta(days=value.weekday())


def week_dates(week_start: date) -> list[date]:
    return [week_start + timedelta(days=offset) for offset in range(DAYS_PER_WEEK)]


def hhmm_to_minutes(value: str) -> int:
    match = _HHMM_RE.match(str(value).strip())
    if not match:
        raise ValueError(f"not an HH:MM clock value: {value!r}")
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 24 and 0 <= minute < 60):
        raise ValueError(f"clock value out of range: {value!r}")
    return hour * 60 + minute


def minutes_to_hhmm(minutes: int) -> str:
    minutes = int(minutes)
    if minutes == MINUTES_PER_DAY:
        # A block may legally end on the day boundary; Taskwarrior renders
        # midnight as 00:00 and the linter reads that as next-day midnight.
        return "00:00"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_est_minutes(value) -> int | None:
    """Parse a compact estimate (``2h``/``0.5h``/``45m``/``1d``) into minutes.

    Bare ints/floats and numeric strings are hours, matching the historic spec
    seam. ``1d`` is 24h here so the value agrees with
    ``taskwarrior_lint._omn_est_hours``.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value) * 60)
    text = str(value).strip()
    if not text:
        return None
    match = _EST_RE.match(text)
    if match:
        number = float(match.group(1))
        unit = match.group(2)
        if unit == "h":
            return round(number * 60)
        if unit == "m":
            return round(number)
        return round(number * MINUTES_PER_DAY)
    try:
        return round(float(text) * 60)
    except ValueError:
        return None


def format_est_minutes(minutes: int) -> str:
    """Compact Taskwarrior est string (``30m``/``1h``/``1.5h``)."""
    minutes = int(minutes)
    if minutes < 60:
        return f"{minutes}m"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    hours = minutes / 60
    text = f"{hours:.2f}".rstrip("0").rstrip(".")
    return f"{text}h"


def parse_iso_minutes(value, week_start: date, *, end_of_day: bool = False) -> int | None:
    """Convert an ISO date or RFC 3339 timestamp to week-relative minutes.

    Date-only values are placed at the start of that day; with ``end_of_day``
    they become the exclusive end of the day. Timestamps are converted to
    America/Chicago before the wall-clock time is taken, so a ``Z``/offset
    timestamp lines up with the user's actual day.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if "T" in text:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            dt = dt.astimezone(TZ)
            offset_days = (dt.date() - week_start).days
            return offset_days * MINUTES_PER_DAY + dt.hour * 60 + dt.minute
        day = date.fromisoformat(text[:10])
    except ValueError:
        return None
    offset_days = (day - week_start).days
    base = offset_days * MINUTES_PER_DAY
    return base + (MINUTES_PER_DAY if end_of_day else 0)


def local_iso_timestamp(value, week_start: date) -> str | None:
    """Normalize a deadline into a concrete local ``YYYY-MM-DDTHH:MM:SS``.

    Date-only deadlines mean end-of-day (23:59), never midnight: midnight
    would elapse at the start of the due date and paint the block overdue all
    day. Timestamps keep their wall-clock time in America/Chicago.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if "T" in text:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            dt = dt.astimezone(TZ)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        day = date.fromisoformat(text[:10])
    except ValueError:
        return None
    return f"{day.isoformat()}T23:59:00"


# ----------------------------------------------------------------- diagnostics


@dataclass
class Diagnostic:
    tag: str
    severity: str
    message: str
    refs: list = field(default_factory=list)
    assumption: str | None = None

    @property
    def blocking(self) -> bool:
        return self.severity == BLOCKING

    def to_dict(self) -> dict:
        out = {
            "tag": self.tag,
            "severity": self.severity,
            "message": self.message,
            "refs": list(self.refs),
        }
        if self.assumption:
            out["assumption"] = self.assumption
        return out


def blocking_diagnostics(diagnostics) -> list[Diagnostic]:
    return [item for item in diagnostics if item.blocking]


# ------------------------------------------------------------ week input model


@dataclass
class Requirement:
    """One externally satisfiable omn requirement (a flexible block target)."""

    id: str
    title: str
    kind: str
    required_minutes: int
    effective_minutes: int
    window_start: int
    window_end: int
    topic: str
    location: str
    due: str | None = None
    due_local: str | None = None
    available: str | None = None
    est_raw: str | None = None
    weekend_allowed: bool = True
    transport: str = "no-car"
    travel: str | None = None
    indivisible: bool = False
    source: str = "omn"

    @property
    def group_key(self) -> tuple[str, str, str]:
        # A block has one topic, place, and transport mode. Two requirements at
        # the same place but requiring different transport cannot truthfully
        # share one Taskwarrior block.
        return (self.topic, self.location, self.transport)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "required_minutes": self.required_minutes,
            "effective_minutes": self.effective_minutes,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "window": [
                _minutes_iso(self.window_start),
                _minutes_iso(self.window_end),
            ],
            "topic": self.topic,
            "location": self.location,
            "due": self.due,
            "due_local": self.due_local,
            "available": self.available,
            "est": self.est_raw,
            "weekend_allowed": self.weekend_allowed,
            "transport": self.transport,
            "travel": self.travel,
            "indivisible": self.indivisible,
            "source": self.source,
        }


@dataclass
class FixedInterval:
    """An authoritative unavailable window (event, +fixed task, sleep)."""

    id: str
    label: str
    start: int
    end: int
    source: str
    refs: list = field(default_factory=list)
    location: str | None = None
    buffer_before: int = 0
    buffer_after: int = 0
    cohort: str | None = None

    def overlaps(self, other: FixedInterval) -> bool:
        return self.start < other.end and other.start < self.end

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "start_local": _minutes_iso(self.start),
            "end_local": _minutes_iso(self.end),
            "source": self.source,
            "refs": list(self.refs),
            "location": self.location,
            "buffer_before": self.buffer_before,
            "buffer_after": self.buffer_after,
            "cohort": self.cohort,
        }


@dataclass
class SupportWindow:
    """A pushable/shrinkable support interval (meals, breaks, cooking).

    Supports occupy real time but are not work blocks: no todo bullets, no
    omn requirement behind them. Each one has its own daily time window and
    duration bounds so it can be pushed or trimmed as the day demands —
    unlike fixed intervals, which are authoritative and immovable.
    """

    id: str
    label: str
    description: str
    day: int
    dur_min: int
    dur_max: int
    earliest: int
    latest: int
    location: str | None = None
    after: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "day": self.day,
            "dur_min": self.dur_min,
            "dur_max": self.dur_max,
            "earliest": self.earliest,
            "latest": self.latest,
            "location": self.location,
            "after": self.after,
        }


@dataclass
class LegacyTask:
    """A pending Taskwarrior task that predates the composer."""

    uuid: str
    id: object
    description: str
    scheduled: str | None
    due: str | None
    est: str | None
    todo_refs: list
    reconciled: bool
    carried: bool
    refs_resolvable: bool = False

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "id": self.id,
            "description": self.description,
            "scheduled": self.scheduled,
            "due": self.due,
            "est": self.est,
            "todo_refs": list(self.todo_refs),
            "reconciled": self.reconciled,
            "refs_resolvable": self.refs_resolvable,
            "carried": self.carried,
        }


@dataclass
class WeekInput:
    week_start: date
    requirements: list
    fixed_intervals: list
    diagnostics: list
    step: int = 30
    min_block: int = 30
    max_block: int = 240
    day_cap: int = 6
    wake_hour: int = 6
    work_start_hour: int = 10
    work_end_hour: int = 18
    daily_budget_minutes: int = 8 * 60
    max_blocks: int = 24
    supports: list = field(default_factory=list)
    legacy: list = field(default_factory=list)
    source: str = "live"
    metadata: dict = field(default_factory=dict)

    @property
    def days(self) -> list[date]:
        return week_dates(self.week_start)

    @property
    def has_blocking(self) -> bool:
        return bool(blocking_diagnostics(self.diagnostics))

    def blocking(self) -> list[Diagnostic]:
        return blocking_diagnostics(self.diagnostics)

    def to_dict(self) -> dict:
        return {
            "week_start": self.week_start.isoformat(),
            "days": [day.isoformat() for day in self.days],
            "source": self.source,
            "metadata": dict(self.metadata),
            "step_minutes": self.step,
            "minimum_block_minutes": self.min_block,
            "maximum_block_minutes": self.max_block,
            "blocks_per_day_cap": self.day_cap,
            "max_blocks": self.max_blocks,
            "wake_hour": self.wake_hour,
            "work_start_hour": self.work_start_hour,
            "work_end_hour": self.work_end_hour,
            "daily_budget_minutes": self.daily_budget_minutes,
            "supports": [item.to_dict() for item in self.supports],
            "requirements": [item.to_dict() for item in self.requirements],
            "fixed_intervals": [item.to_dict() for item in self.fixed_intervals],
            "legacy_managed_tasks": [item.to_dict() for item in self.legacy],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "has_blocking_diagnostics": self.has_blocking,
        }


def _minutes_iso(minutes: int) -> str:
    """Render week-relative minutes as a local ``YYYY-MM-DD HH:MM`` label.

    Only used for human diagnostics; the exact date depends on the week, which
    is not known here, so callers that need a date use the week-aware helpers.
    """
    minutes = max(0, int(minutes))
    day, rem = divmod(minutes, MINUTES_PER_DAY)
    return f"+{day}d {rem // 60:02d}:{rem % 60:02d}"


def window_label(week_start: date, start: int, end: int) -> str:
    def render(value: int) -> str:
        if value <= 0:
            return f"{week_start.isoformat()} 00:00"
        if value >= MINUTES_PER_WEEK:
            return f"{(week_start + timedelta(days=6)).isoformat()} 24:00"
        day = week_start + timedelta(days=value // MINUTES_PER_DAY)
        rem = value % MINUTES_PER_DAY
        return f"{day.isoformat()} {rem // 60:02d}:{rem % 60:02d}"

    return f"{render(start)} .. {render(end)}"


@dataclass
class ComposerConfig:
    """Tunables shared by the source reader, model and CLI."""

    step: int = 30
    min_block: int = 30
    max_block: int = 240
    day_cap: int = 6
    wake_hour: int = 6
    work_start_hour: int = 10
    work_end_hour: int = 18
    daily_budget_minutes: int = 8 * 60
    max_blocks: int = 24
    candidates: int = 3
    solver_timeout_ms: int = 15_000
    group_block_slack: int = 2
    seed: int = 11
    # Zero-LLM operation: a requirement with no meta.est (or a placeholder
    # est_status) uses this deterministic fallback instead of blocking the
    # whole plan. Every fallback is surfaced as a diagnostic so the agent or
    # the user can correct it later.
    default_est_minutes: int = 120

    def validate(self) -> None:
        if self.step <= 0 or MINUTES_PER_DAY % self.step:
            raise ValueError("step must be a positive divisor of 1440")
        if self.min_block <= 0 or self.min_block % self.step:
            raise ValueError("min_block must be a positive multiple of step")
        if self.max_block < self.min_block or self.max_block % self.step:
            raise ValueError("max_block must be a multiple of step >= min_block")
        if self.day_cap <= 0:
            raise ValueError("day_cap must be positive")
        if self.max_blocks <= 0:
            raise ValueError("max_blocks must be positive")
        if not (0 <= self.wake_hour <= 24):
            raise ValueError("wake_hour must be in [0, 24]")
        if not (0 <= self.work_start_hour < self.work_end_hour <= 24):
            raise ValueError("work hours must satisfy 0 <= start < end <= 24")


def normalize_location(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _building(location: str) -> str:
    return location.split()[0].lower() if location else ""


def _is_campus(location: str) -> bool:
    text = location.lower()
    campus_markers = (
        "ecss", "ecs", "fo ", "jo ", "gr ", "mc ", "su ", "ssb",
        "activity center", "utd", "on campus", "library",
    )
    return any(marker in text for marker in campus_markers)


def transit_minutes(origin: str | None, destination: str | None) -> int:
    """Return the standing 0/10/20/30-minute location transition."""
    first, second = normalize_location(origin), normalize_location(destination)
    if not first or not second:
        return 30
    if first.casefold() == second.casefold():
        return 0
    pair = {first.casefold(), second.casefold()}
    if (any("ecss" in item for item in pair)
            and any("activity center" in item for item in pair)):
        return 5
    if _is_campus(first) and _is_campus(second):
        return 10 if _building(first) == _building(second) else 20
    return 30

