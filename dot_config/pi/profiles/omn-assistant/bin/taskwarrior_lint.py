#!/usr/bin/env python3
"""Taskwarrior schedule linter for the omn-assistant pipeline.

Reads the schedule state through the primary interfaces only — `task export`
and `omn export` — and checks it against the standing scheduling guidelines.
Each policy is a small object in the POLICIES array; add new policies there.

IMPORTANT: this linter is advisory, not authoritative. Its warnings are a
prompt for judgment, not verdicts: the agent (with the user) is the final
judge. Many warnings are expected exceptions the user explicitly asked for
(explicit times, shifted meal blocks, deadline-forced weekend work, a skipped
afternoon break). Triage every warning into "expected exception" or "genuine
violation needs correction" before changing anything.

Usage:
  taskwarrior_lint.py                 # lint the current Mon-Sun week
  taskwarrior_lint.py --week 2026-09-07
  taskwarrior_lint.py --json          # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")

# ------------------------------------------------------------------ warnings


@dataclass
class Warning:
    policy: str
    severity: str  # ERROR | WARN | INFO
    message: str
    refs: list = field(default_factory=list)  # task ids / omn record ids

    def render(self) -> str:
        refs = f" [{', '.join(map(str, self.refs))}]" if self.refs else ""
        return f"{self.severity:<5} {self.policy}: {self.message}{refs}"


class Policy:
    """One lint rule. Subclass and implement check(); register in POLICIES."""

    id = "policy"
    description = ""

    def check(self, ctx: "Context") -> list[Warning]:
        raise NotImplementedError


# ------------------------------------------------------------------- context


def parse_tw_date(value) -> datetime | None:
    """Taskwarrior export timestamps -> aware local datetime."""
    if not value:
        return None
    text = str(value)
    try:
        if text.endswith("Z"):
            dt = datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        elif "T" in text:
            dt = datetime.strptime(text, "%Y%m%dT%H%M%S").replace(tzinfo=TZ)
        else:
            dt = datetime.strptime(text[:8], "%Y%m%d").replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except ValueError:
        return None


def parse_est(value) -> timedelta | None:
    """Compact human estimates like 1h, 2.5h, 0.75h, 3d; ISO forms -> None."""
    if not value:
        return None
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)([hd])", str(value).strip())
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2)
    return timedelta(hours=number) if unit == "h" else timedelta(days=number)


CAMPUS_LOCATION = re.compile(
    r"(ECSS|ECSN|FO|FN|EC)\s*\d|Jee's lab|on campus|SU\b|library", re.IGNORECASE
)
VENUE_LOCATION = re.compile(
    r"post office|bank|branch|office|store|mall|clinic|dentist|orthodont", re.IGNORECASE
)
IMPERATIVE = {
    "attend", "eat", "complete", "start", "finish", "practice", "cancel",
    "attempt", "check", "renew", "work", "research", "write", "talk",
    "calculate", "set", "download", "sign", "lab", "discuss", "revisit",
    "register", "email", "contact", "buy", "go", "call", "schedule",
}


class Context:
    def __init__(self, week_monday: date):
        self.week_monday = week_monday
        self.week_sunday = week_monday + timedelta(days=6)
        self.tasks = run_task_export()
        self.pending = [t for t in self.tasks if t.get("status") == "pending"]
        self.completed = [t for t in self.tasks if t.get("status") == "completed"]
        self.omn = run_omn_export()
        self.now = datetime.now(TZ)

    # -- helpers ------------------------------------------------------------

    def in_week(self, t: dict) -> bool:
        sched = parse_tw_date(t.get("scheduled"))
        return sched is not None and self.week_monday <= sched.date() <= self.week_sunday

    def week_tasks(self, statuses=None) -> list[dict]:
        pool = self.tasks if statuses is None else [
            t for t in self.tasks if t.get("status") in statuses
        ]
        return [t for t in pool if self.in_week(t)]

    def week_pending(self) -> list[dict]:
        return self.week_tasks(["pending"])

    def timed(self, tasks: list[dict]) -> list[dict]:
        return [t for t in tasks if t.get("starttime") and t.get("endtime")]

    def by_day(self, tasks: list[dict]) -> dict[date, list[dict]]:
        days: dict[date, list[dict]] = defaultdict(list)
        for t in tasks:
            sched = parse_tw_date(t.get("scheduled"))
            if sched:
                days[sched.date()].append(t)
        return days

    def duration(self, t: dict) -> timedelta | None:
        span = self.datetimes(t)
        return None if span is None else span[1] - span[0]

    @staticmethod
    def clock(value) -> time | None:
        if not value:
            return None
        return datetime.strptime(value, "%H:%M").time()

    def datetimes(self, t: dict) -> tuple[datetime, datetime] | None:
        sched = parse_tw_date(t.get("scheduled"))
        start = self.clock(t.get("starttime"))
        end = self.clock(t.get("endtime"))
        if not (sched and start and end):
            return None
        begin = datetime.combine(sched.date(), start, tzinfo=TZ)
        finish = datetime.combine(sched.date(), end, tzinfo=TZ)
        if finish <= begin:  # endtime may be stored past midnight
            finish += timedelta(days=1)
        return begin, finish

    def est_of(self, t: dict) -> timedelta | None:
        est = parse_est(t.get("est"))
        if est is None and str(t.get("est", "")).startswith("PT"):
            return iso_duration(t.get("est"))
        return est

    def lectures(self) -> list[dict]:
        out = []
        for r in self.omn:
            meta = r.get("meta", {})
            if r.get("type") == "event" and meta.get("rrule") and "lecture" in r.get("title", "").lower():
                out.append(r)
        return out

    def recurring_events(self) -> list[dict]:
        out = []
        for r in self.omn:
            meta = r.get("meta", {})
            if r.get("type") == "event" and meta.get("rrule") and meta.get("active", True):
                out.append(r)
        return out

    def omn_assignments(self) -> list[dict]:
        out = []
        for r in self.omn:
            if r.get("type") != "task":
                continue
            due = parse_omn_date(r.get("meta", {}).get("due"))
            if due:
                out.append((r, due))
        return out


def run_task_export() -> list[dict]:
    out = subprocess.run(
        ["task", "rc.verbose=nothing", "status.not:deleted", "export"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"task export failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def run_omn_export() -> list[dict]:
    out = subprocess.run(["omn", "export"], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"omn export failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def iso_duration(value: str) -> timedelta | None:
    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?", str(value or "").strip())
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return timedelta(hours=hours, minutes=minutes)


def parse_omn_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


BYDAY = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def expand_rrule(rrule: str, window_start: date, days: int = 7) -> list[date]:
    """Minimal WEEKLY rrule expansion over a window; enough for omn records."""
    if "WEEKLY" not in (rrule or "").upper():
        return []
    parts = dict(
        piece.split("=", 1) for piece in rrule.split(";") if "=" in piece
    )
    weekdays = [BYDAY[d] for d in re.findall(r"MO|TU|WE|TH|FR|SA|SU", parts.get("BYDAY", "").upper())]
    until = parse_omn_date(parts.get("UNTIL", ""))
    out = []
    for offset in range(days):
        day = window_start + timedelta(days=offset)
        if until and day > until:
            continue
        if day.weekday() in weekdays:
            out.append(day)
    return out


def event_times(record: dict) -> tuple[datetime, datetime] | None:
    meta = record.get("meta", {})
    try:
        start = datetime.fromisoformat(meta["start"])
        end = datetime.fromisoformat(meta["end"])
        return start.astimezone(TZ), end.astimezone(TZ)
    except (KeyError, ValueError, TypeError):
        return None


# ------------------------------------------------------------------ policies


class NoRecurrenceTemplates(Policy):
    """Taskwarrior recurrence templates are banned; recurrence lives in omn."""

    id = "no-recurrence-templates"

    def check(self, ctx):
        out = []
        for t in ctx.tasks:
            if t.get("recur") and t.get("status") in ("pending", "recurring", "waiting"):
                out.append(Warning(
                    self.id, "ERROR",
                    f"recurrence template present ('{t['description'][:40]}'); "
                    "recurrence must live in omn and each week's occurrence must "
                    "be an individual plain task",
                    [t.get("id")],
                ))
        return out


class NoDuplicateTasks(Policy):
    """No two pending tasks with the same description and scheduled day."""

    id = "no-duplicate-tasks"

    def check(self, ctx):
        groups = defaultdict(list)
        for t in ctx.pending:
            sched = parse_tw_date(t.get("scheduled"))
            if sched:
                groups[(t["description"].strip().lower(), sched.date())].append(t)
        out = []
        for (desc, day), tasks in sorted(groups.items()):
            if len(tasks) > 1:
                out.append(Warning(
                    self.id, "ERROR",
                    f"{len(tasks)} duplicate pending tasks '{desc[:40]}' on {day}",
                    [t.get("id") for t in tasks],
                ))
        return out


class NoOverlaps(Policy):
    """Pending timed tasks must not overlap."""

    id = "no-overlaps"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(ctx.timed(ctx.week_pending())).items()):
            spans = sorted(
                (ctx.datetimes(t) for t in tasks), key=lambda s: s[0]
            )
            for (a_begin, a_end), (b_begin, b_end) in zip(spans, spans[1:]):
                if b_begin < a_end:
                    out.append(Warning(
                        self.id, "ERROR",
                        f"overlapping tasks on {day}: {a_begin:%H:%M}-{a_end:%H:%M} "
                        f"and {b_begin:%H:%M}-{b_end:%H:%M}",
                    ))
        return out


class DueNotMidnight(Policy):
    """Day-granularity dues must be 23:59 local, never 00:00 (which reads as
    the previous night and paints the task red / overdue)."""

    id = "due-not-midnight"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            due = parse_tw_date(t.get("due"))
            if due and due.time() == time(0, 0):
                out.append(Warning(
                    self.id, "ERROR",
                    f"'{t['description'][:40]}' has a 00:00 due; day-granularity "
                    "dues must be 23:59 local (or no due for attendance events)",
                    [t.get("id")],
                ))
        return out


class PlannedAfterDue(Policy):
    """Never plan work on a day after its real deadline."""

    id = "planned-after-due"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            due = parse_tw_date(t.get("due"))
            sched = parse_tw_date(t.get("scheduled"))
            if due and sched and sched.date() > due.date():
                out.append(Warning(
                    self.id, "ERROR",
                    f"'{t['description'][:40]}' scheduled {sched:%Y-%m-%d} is "
                    f"past its due {due:%Y-%m-%d}",
                    [t.get("id")],
                ))
        return out


class OverduePending(Policy):
    """Pending work whose deadline already passed."""

    id = "overdue-pending"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            due = parse_tw_date(t.get("due"))
            if due and due < ctx.now:
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' is pending but due "
                    f"{due:%Y-%m-%d %H:%M} already passed",
                    [t.get("id")],
                ))
        return out


class OmnAssignmentsCovered(Policy):
    """Every omn assignment with a due date must exist in Taskwarrior (pending
    or completed) with the same due date."""

    id = "omn-assignments-covered"

    def check(self, ctx):
        tw_by_due = defaultdict(list)
        for t in ctx.tasks:
            due = parse_tw_date(t.get("due"))
            if due:
                tw_by_due[due.date()].append(t)
        out = []
        for record, due in ctx.omn_assignments():
            matches = tw_by_due.get(due, [])
            title = record.get("title", "")[:40]
            if not matches:
                    near = due <= ctx.week_sunday + timedelta(days=7)
                    out.append(Warning(
                        self.id, "ERROR" if near else "INFO",
                        f"omn assignment '{title}' due {due} has no Taskwarrior "
                        "task with that due date"
                        + ("" if near else " (far future; fine to leave for weekly planning)"),
                        [record.get("id")],
                    ))
        return out


class OmnAssignmentDueAccuracy(Policy):
    """Canvas-backed Taskwarrior tasks must carry the omn assignment's exact
    due (23:59 local of the omn due day), not a planning target."""

    id = "omn-assignment-due-accuracy"

    def check(self, ctx):
        due_days = {due for _, due in ctx.omn_assignments()}
        out = []
        for t in ctx.pending:
            due = parse_tw_date(t.get("due"))
            if not due:
                continue
            if due.date() in due_days and due.time() != time(23, 59):
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' due {due:%Y-%m-%d} {due:%H:%M} "
                    "does not match the omn assignment due (expected 23:59 local)",
                    [t.get("id")],
                ))
        return out


class ClassesScheduled(Policy):
    """Every omn lecture occurrence in the week must exist as a pending
    +fixed +class task with matching date, start time, and location."""

    id = "classes-scheduled"

    def check(self, ctx):
        out = []
        classes = [
            t for t in ctx.pending
            if "class" in t.get("tags", []) and ctx.in_week(t)
        ]
        for record in ctx.lectures():
            times = event_times(record)
            if not times:
                continue
            start = times[0]
            occ_days = expand_rrule(
                record["meta"]["rrule"], ctx.week_monday)
            for day in occ_days:
                same_day = [
                    t for t in classes
                    if parse_tw_date(t.get("scheduled")).date() == day
                ]
                hit = next(
                    (t for t in same_day
                     if t.get("starttime") == start.strftime("%H:%M")),
                    None)
                if hit is None:
                    out.append(Warning(
                        self.id, "ERROR",
                        f"lecture '{record['title']}' on {day} "
                        f"{start:%H:%M} missing from Taskwarrior",
                        [record.get("id")],
                    ))
                elif (hit.get("location") or "") != (record["meta"].get("location") or ""):
                    out.append(Warning(
                        self.id, "WARN",
                        f"lecture '{record['title']}' on {day} location "
                        f"'{hit.get('location')}' != omn "
                        f"'{record['meta'].get('location')}'",
                        [hit.get("id"), record.get("id")],
                    ))
        return out


class RecurringEventsPresent(Policy):
    """Active recurring omn events (non-class, e.g. the PyLingual meeting) must
    have this week's occurrence scheduled as an individual plain task."""

    id = "recurring-events-present"

    def check(self, ctx):
        out = []
        for record in ctx.recurring_events():
            if "lecture" in record.get("title", "").lower():
                continue
            times = event_times(record)
            if not times:
                continue
            start_time = times[0].strftime("%H:%M")
            for day in expand_rrule(record["meta"]["rrule"], ctx.week_monday):
                hit = next(
                    (t for t in ctx.pending
                     if ctx.in_week(t)
                     and parse_tw_date(t.get("scheduled")).date() == day
                     and t.get("starttime") == start_time
                     and "fixed" in t.get("tags", [])),
                    None)
                if hit is None:
                    out.append(Warning(
                        self.id, "WARN",
                        f"recurring omn event '{record['title']}' has no "
                        f"scheduled occurrence on {day} {start_time}",
                        [record.get("id")],
                    ))
        return out


class LabHours(Policy):
    """Six hours of lab time per week at Prof. Jee's lab, centered on
    Monday/Wednesday 10:00-17:00; the Wednesday PyLingual meeting counts."""

    id = "lab-hours"

    def check(self, ctx):
        out = []
        lab = [
            t for t in ctx.pending if ctx.in_week(t)
            and "PyLingual" not in t["description"]
            and ("Jee's lab" in (t.get("location") or "")
                 or t["description"].lower().startswith("lab work"))
        ]
        meeting = [
            t for t in ctx.pending if ctx.in_week(t)
            and "PyLingual lab meeting" in t["description"]
        ]
        total = sum(
            (ctx.est_of(t) or ctx.duration(t) or timedelta()
             for t in lab + meeting), timedelta())
        days_used = sorted({
            parse_tw_date(t.get("scheduled")).weekday()
            for t in lab + meeting
        })
        if total < timedelta(hours=6):
            out.append(Warning(
                self.id, "WARN",
                f"only {total.total_seconds()/3600:.2f}h lab time this week "
                "(target 6h including the PyLingual meeting)",
            ))
        if total > timedelta(hours=6, minutes=30):
            out.append(Warning(
                self.id, "INFO",
                f"{total.total_seconds()/3600:.2f}h lab time this week "
                "(above the 6h target; fine if intentional)",
            ))
        if any(d not in (0, 2) for d in days_used):
            out.append(Warning(
                self.id, "WARN",
                f"lab time falls outside Monday/Wednesday "
                f"(days {[d for d in days_used if d not in (0, 2)]})",
            ))
        return out


class WeekendAssignmentWork(Policy):
    """Weekends are protected: no deadline-bearing (assignment) work on Sat/Sun
    unless the weekend deadline forces it. Personal projects are fine."""

    id = "weekend-assignment-work"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            sched = parse_tw_date(t.get("scheduled"))
            if not sched or sched.weekday() not in (5, 6):
                continue
            if t.get("due"):
                out.append(Warning(
                    self.id, "WARN",
                    f"deadline-bearing task '{t['description'][:40]}' scheduled "
                    f"{sched:%a %Y-%m-%d}; weekends are protected unless the "
                    "weekend deadline forces it",
                    [t.get("id")],
                ))
        return out


class AssignmentStartBoundary(Policy):
    """No assignment work before the later of 10:00 and the day's first class
    end + 30m travel buffer; mornings are for sleep, personal projects, or
    downtime. Explicit user times override this."""

    id = "assignment-start-boundary"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(ctx.week_pending()).items()):
            classes = [
                t for t in tasks
                if "class" in t.get("tags", []) and t.get("endtime")
            ]
            boundary = time(10, 0)
            if classes:
                first_end = min(t["endtime"] for t in classes)
                hh, mm = map(int, first_end.split(":"))
                b = (datetime.combine(day, time(hh, mm)) + timedelta(minutes=30)).time()
                boundary = max(boundary, b)
            for t in tasks:
                if not t.get("due") or not t.get("starttime"):
                    continue
                start = ctx.clock(t["starttime"])
                if start < boundary:
                    out.append(Warning(
                        self.id, "WARN",
                        f"assignment '{t['description'][:40]}' starts "
                        f"{start:%H:%M} before the {boundary:%H:%M} boundary "
                        f"on {day} (fine if user-approved)",
                        [t.get("id")],
                    ))
        return out


class DayBudget(Policy):
    """Nominal 8h weekday budget of class hours plus scheduled est; exceeding
    it needs a real deadline reason."""

    id = "day-budget"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(ctx.week_pending()).items()):
            if day.weekday() >= 5:
                continue
            total = timedelta()
            for t in tasks:
                total += (ctx.est_of(t) or ctx.duration(t)
                          or (t.get("est") and iso_duration(t["est"]))
                          or timedelta())
            if total > timedelta(hours=8):
                out.append(Warning(
                    self.id, "INFO",
                    f"{day} carries {total.total_seconds()/3600:.2f}h "
                    "(above the nominal 8h budget; fine if intentional)",
                ))
        return out


class EstWindowMatch(Policy):
    """A timed task's est should match its start/end window."""

    id = "est-window-match"

    def check(self, ctx):
        out = []
        for t in ctx.timed(ctx.pending):
            est = ctx.est_of(t)
            span = ctx.duration(t)
            if est is None or span is None:
                continue
            if abs((est - span).total_seconds()) > 300:
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' est {est} != window {span}",
                    [t.get("id")],
                ))
        return out


class MinimumEstimate(Policy):
    """0.5h is the minimum estimate; merge or consolidate smaller actions."""

    id = "minimum-estimate"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            est = ctx.est_of(t)
            if est and timedelta() < est < timedelta(minutes=30):
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' est {est} below the 0.5h minimum",
                    [t.get("id")],
                ))
        return out


class EstFormat(Policy):
    """Estimates use compact human form (1h, 2.5h), never ISO PT2H."""

    id = "est-format"

    def check(self, ctx):
        out = []
        for t in ctx.tasks:
            if t.get("status") not in ("pending", "completed"):
                continue
            if str(t.get("est", "")).startswith("PT"):
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' est '{t['est']}' is ISO 8601; "
                    "use compact form (1h, 2.5h)",
                    [t.get("id")],
                ))
        return out


class TransportSet(Policy):
    """Managed pending tasks should declare car/no-car."""

    id = "transport-set"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            if ("managed" in t.get("tags", [])
                    and "schedule" not in t.get("tags", [])
                    and not t.get("transport")):
                out.append(Warning(
                    self.id, "INFO",
                    f"'{t['description'][:40]}' has no transport set",
                    [t.get("id")],
                ))
        return out


class ClassTravelUda(Policy):
    """Classes carry travel:30m (walking commute); car errands too."""

    id = "class-travel-uda"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            tags = t.get("tags", [])
            if "class" in tags and t.get("travel") != "30m":
                out.append(Warning(
                    self.id, "WARN",
                    f"lecture '{t['description'][:40]}' missing travel:30m",
                    [t.get("id")],
                ))
        return out


class TransitBuffers(Policy):
    """Timed tasks need unallocated gaps around transit: a task's `travel`
    minutes must exist between it and a neighbor at a different place.
    Consecutive campus blocks (class -> class, lab blocks) need no gap."""

    id = "transit-buffers"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(ctx.timed(ctx.week_pending())).items()):
            tasks.sort(key=lambda t: t["starttime"])
            for prev, nxt in zip(tasks, tasks[1:]):
                prev_end = ctx.clock(prev["endtime"])
                nxt_start = ctx.clock(nxt["starttime"])
                gap = (datetime.combine(day, nxt_start)
                       - datetime.combine(day, prev_end)).total_seconds() / 60
                if gap < 0:
                    continue
                prev_campus = CAMPUS_LOCATION.search(prev.get("location") or "")
                nxt_campus = CAMPUS_LOCATION.search(nxt.get("location") or "")
                travel = nxt.get("travel") or prev.get("travel") or ""
                need = 0
                if travel.endswith("m"):
                    need = int(travel[:-1])
                if prev_campus and nxt_campus:
                    continue  # same-campus walk, no buffer needed
                if nxt_campus != prev_campus and gap < need:
                    out.append(Warning(
                        self.id, "WARN",
                        f"only {gap:.0f}m between '{prev['description'][:28]}' "
                        f"and '{nxt['description'][:28]}' on {day}; transit "
                        f"needs ~{need}m (or user-approved tight transition)",
                        [prev.get("id"), nxt.get("id")],
                    ))
        return out


class CarTripGrouping(Policy):
    """Car errands form one contiguous trip with 30m buffers around it."""

    id = "car-trip-grouping"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(ctx.timed(ctx.week_pending())).items()):
            cars = [t for t in tasks if t.get("transport") == "car"]
            if len(cars) < 2:
                continue
            cars.sort(key=lambda t: t["starttime"])
            for prev, nxt in zip(cars, cars[1:]):
                between = [
                    t for t in tasks
                    if prev["starttime"] < t["starttime"] < nxt["starttime"]
                    and t.get("transport") != "car"
                ]
                if between:
                    out.append(Warning(
                        self.id, "WARN",
                        f"non-car task between car errands on {day} "
                        f"('{between[0]['description'][:30]}'); group the trip",
                        [t.get("id") for t in between],
                    ))
        return out


class Meals(Policy):
    """Breakfast (06:00-08:00) and dinner (17:00-20:00) every day in the same
    block; lunch (11:00-14:00) daily, one hour."""

    id = "meals"

    def check(self, ctx):
        out = []
        week = ctx.by_day(ctx.week_pending())
        active_days = [d for d in sorted(week) if week[d]]
        breakfasts, dinners, lunches = [], [], []
        for day in active_days:
            kinds = defaultdict(list)
            for t in week[day]:
                desc = t["description"].lower()
                for kind in ("breakfast", "lunch", "dinner"):
                    if desc.startswith(f"eat {kind}"):
                        kinds[kind].append(t)
            if not kinds["breakfast"]:
                out.append(Warning(self.id, "WARN", f"no breakfast scheduled {day}"))
            else:
                breakfasts.append((day, kinds["breakfast"][0]))
            if not kinds["dinner"]:
                out.append(Warning(self.id, "WARN", f"no dinner scheduled {day}"))
            else:
                dinners.append((day, kinds["dinner"][0]))
            if not kinds["lunch"]:
                out.append(Warning(self.id, "WARN", f"no lunch scheduled {day}"))
            else:
                lunches.append((day, kinds["lunch"][0]))

        def consistency(pairs, name, lo, hi):
            blocks = {(t.get("starttime"), t.get("endtime")) for _, t in pairs}
            if len(blocks) > 1:
                out.append(Warning(
                    self.id, "INFO",
                    f"{name} block varies across the week ({sorted(blocks)}); "
                    "same block each day unless a fixed event forces a shift",
                ))
            for day, t in pairs:
                start = ctx.clock(t.get("starttime")) or time(0, 0)
                if not (lo <= start <= hi):
                    out.append(Warning(
                        self.id, "WARN",
                        f"{name} on {day} starts {start:%H:%M}, outside "
                        f"{lo:%H:%M}-{hi:%H:%M} (fine if user-approved)",
                        [t.get("id")],
                    ))

        consistency(breakfasts, "breakfast", time(6, 0), time(8, 0))
        consistency(dinners, "dinner", time(17, 0), time(20, 0))
        consistency(lunches, "lunch", time(11, 0), time(14, 0))
        for day, t in lunches:
            span = ctx.duration(t)
            if span and abs(span - timedelta(hours=1)) > timedelta(minutes=5):
                out.append(Warning(
                    self.id, "WARN",
                    f"lunch on {day} is {span}, not one hour",
                    [t.get("id")],
                ))
        return out


class AfternoonBreak(Policy):
    """Weekdays should have an afternoon break (~16:00, 1-2h) when there is
    slack; often waived by the user, so this is informational."""

    id = "afternoon-break"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(ctx.week_pending()).items()):
            if day.weekday() >= 5 or not tasks:
                continue
            has_break = any(
                "break" in t["description"].lower() for t in tasks)
            if not has_break:
                out.append(Warning(
                    self.id, "INFO",
                    f"no afternoon break on {day} (waivable)",
                ))
        return out


class VenueHours(Policy):
    """Place-dependent errands must respect venue hours; the linter can only
    flag suspicious daytimes - verify actual hours by web search."""

    id = "venue-hours"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            location = t.get("location") or ""
            if not VENUE_LOCATION.search(location):
                continue
            sched = parse_tw_date(t.get("scheduled"))
            if not sched:
                continue
            end = ctx.clock(t.get("endtime")) or time(0, 0)
            if sched.weekday() >= 5 or end >= time(17, 0):
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' at '{location}' on "
                    f"{sched:%a} ends {end:%H:%M}; verify the venue is open",
                    [t.get("id")],
                ))
        return out


class ForbiddenTags(Policy):
    """No workblock/deliverable/hierarchy tags; no deadline trackers."""

    id = "forbidden-tags"

    def check(self, ctx):
        banned = {"workblock", "deliverable"}
        out = []
        for t in ctx.tasks:
            hit = banned & set(t.get("tags", []))
            if hit:
                out.append(Warning(
                    self.id, "ERROR",
                    f"'{t['description'][:40]}' carries forbidden tags {hit}",
                    [t.get("id")],
                ))
        return out


class ImperativeVerb(Policy):
    """Task descriptions read as direct actions (imperative verb first)."""

    id = "imperative-verb"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            if "managed" not in t.get("tags", []):
                continue
            first = t["description"].split(None, 1)[0].lower().strip(",;")
            if first not in IMPERATIVE:
                out.append(Warning(
                    self.id, "INFO",
                    f"'{t['description'][:40]}' does not start with an "
                    "imperative verb (advisory)",
                    [t.get("id")],
                ))
        return out


class PianoSplitting(Policy):
    """Piano never stacks into one 2h+ contiguous block; split sessions."""

    id = "piano-splitting"

    def check(self, ctx):
        out = []
        for day, tasks in sorted(ctx.by_day(
                [t for t in ctx.pending if "piano" in t["description"].lower()]).items()):
            spans = sorted(ctx.datetimes(t) for t in tasks if ctx.datetimes(t))
            for (a_begin, a_end), (b_begin, b_end) in zip(spans, spans[1:]):
                if b_begin <= a_end + timedelta(minutes=5):
                    total = (b_end - a_begin).total_seconds() / 3600
                    if total >= 2:
                        out.append(Warning(
                            self.id, "WARN",
                            f"contiguous piano {total:.1f}h on {day}; user "
                            "prefers separated sessions",
                        ))
        return out


class StaleScheduling(Policy):
    """Pending tasks still scheduled on past days (carried work); they need
    rebalancing or an explicit keep."""

    id = "stale-scheduling"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            sched = parse_tw_date(t.get("scheduled"))
            if sched and sched.date() < ctx.now.date():
                out.append(Warning(
                    self.id, "INFO",
                    f"'{t['description'][:40]}' still scheduled for "
                    f"{sched:%Y-%m-%d} (in the past); reschedule or confirm",
                    [t.get("id")],
                ))
        return out


POLICIES: list[Policy] = [
    NoRecurrenceTemplates(),
    NoDuplicateTasks(),
    NoOverlaps(),
    DueNotMidnight(),
    PlannedAfterDue(),
    ForbiddenTags(),
    OmnAssignmentsCovered(),
    OmnAssignmentDueAccuracy(),
    ClassesScheduled(),
    RecurringEventsPresent(),
    LabHours(),
    WeekendAssignmentWork(),
    AssignmentStartBoundary(),
    OverduePending(),
    StaleScheduling(),
    EstWindowMatch(),
    MinimumEstimate(),
    EstFormat(),
    TransportSet(),
    ClassTravelUda(),
    TransitBuffers(),
    CarTripGrouping(),
    Meals(),
    AfternoonBreak(),
    VenueHours(),
    ImperativeVerb(),
    PianoSplitting(),
    DayBudget(),
]


# --------------------------------------------------------------------- main


def week_monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", help="Monday of the week to lint (YYYY-MM-DD)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when ERROR-level warnings exist")
    args = parser.parse_args()

    if args.week:
        monday = week_monday_of(date.fromisoformat(args.week))
    else:
        monday = week_monday_of(datetime.now(TZ).date())

    ctx = Context(monday)
    warnings: list[Warning] = []
    for policy in POLICIES:
        try:
            warnings.extend(policy.check(ctx))
        except Exception as exc:  # a broken policy must not sink the run
            warnings.append(Warning(
                "linter", "INFO",
                f"policy {policy.id} crashed: {exc}", []))

    warnings.sort(key=lambda w: ({"ERROR": 0, "WARN": 1, "INFO": 2}[w.severity],
                                 w.policy))

    if args.json:
        print(json.dumps([
            {"policy": w.policy, "severity": w.severity,
             "message": w.message, "refs": w.refs}
            for w in warnings
        ], indent=1))
    else:
        week = f"{ctx.week_monday:%Y-%m-%d} .. {ctx.week_sunday:%Y-%m-%d}"
        counts = defaultdict(int)
        for w in warnings:
            counts[w.severity] += 1
        print(f"taskwarrior_lint: week {week} | "
              f"{len(ctx.pending)} pending, {len(ctx.completed)} completed | "
              f"{counts['ERROR']} error, {counts['WARN']} warn, "
              f"{counts['INFO']} info")
        for w in warnings:
            print("  " + w.render())
        print("Advisory only: triage each warning as an expected exception "
              "or a genuine violation; the agent is the final judge.")

    if args.strict and any(w.severity == "ERROR" for w in warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
