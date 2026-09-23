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
import urllib.parse
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
    """Compact human estimates like 1h, 2.5h, 0.75h, 3d, 55m; ISO -> None."""
    if not value:
        return None
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)([hdm])", str(value).strip())
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2)
    if unit == "h":
        return timedelta(hours=number)
    if unit == "m":
        return timedelta(minutes=number)
    return timedelta(days=number)


CAMPUS_LOCATION = re.compile(
    r"on campus|\bSU\b|library|Jee's lab", re.IGNORECASE
)
VENUE_LOCATION = re.compile(
    r"post office|bank|branch|office|store|mall|clinic|dentist|orthodont", re.IGNORECASE
)


PAREN = re.compile(r"\s*\([^)]*\)")


def normalize_location(location) -> str:
    """Location with trailing parentheticals dropped, so 'At home (Zoom)'
    equals 'At home' and 'ECSS 3.226 (Prof. Jee's lab)' equals 'ECSS 3.226'."""
    return PAREN.sub("", location or "").strip()


def building_code(location) -> str | None:
    """UTD-style building code from a location like 'ECSS 3.226' or 'FN 2.214'."""
    match = re.search(r"\b([A-Z]{2,4})\s*\d", normalize_location(location).upper())
    return match.group(1) if match else None


def zone_of(location) -> str | None:
    """Classify a location: building code, generic 'campus', or 'off'."""
    location = normalize_location(location)
    if not location:
        return None
    code = building_code(location)
    if code:
        return code
    if CAMPUS_LOCATION.search(location) or "campus" in location.lower():
        return "campus"
    return "off"


# Legs the user has stated explicitly; they override the generic model.
STATED_TRANSIT: list[tuple[str, str, int]] = [
    ("ecss", "activity center", 5),  # user: natatorium is ~5 min from ECSS
]


def transit_minutes(origin: str | None, destination: str | None) -> int:
    """Standing transit rule: 0m same place, 10m same building, 20m different
    buildings both on campus, 30m whenever the trip goes off campus. Legs the
    user has stated explicitly win over the model."""
    if origin is None or destination is None:
        return 30
    a_low, b_low = normalize_location(origin).lower(), normalize_location(destination).lower()
    for x, y, minutes in STATED_TRANSIT:
        if (x in a_low and y in b_low) or (y in a_low and x in b_low):
            return minutes
    if normalize_location(origin).lower() == normalize_location(destination).lower():
        return 0
    a, b = zone_of(origin), zone_of(destination)
    if a is None or b is None:
        return 30
    if a == b:  # identical building or both generic campus
        return 10 if a != "campus" else 20
    if a == "off" or b == "off":
        return 30
    return 20
IMPERATIVE = {
    "attend", "eat", "complete", "start", "finish", "practice", "cancel",
    "attempt", "check", "renew", "work", "research", "write", "talk",
    "calculate", "set", "download", "sign", "lab", "discuss", "revisit",
    "register", "email", "contact", "buy", "go", "call", "schedule",
    "verify", "attend", "renew", "apply", "take",
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
            meta = r.get("meta", {})
            if meta.get("kind") == "in-class":
                continue  # completed in class; no take-home Taskwarrior work
            due = parse_omn_date(meta.get("due"))
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
            if len(tasks) < 2:
                continue
            # Same description twice a day is only a duplicate when the windows
            # collide (or times are missing); distinct sessions are intentional.
            spans = [ctx.datetimes(t) for t in tasks]
            if all(spans) and not any(
                a[0] < b[1] and b[0] < a[1]
                for i, a in enumerate(spans) for b in spans[i + 1:]
            ):
                continue
            out.append(Warning(
                self.id, "ERROR",
                f"{len(tasks)} duplicate pending tasks '{desc[:40]}' on {day}",
                [t.get("id") for t in tasks],
            ))
        return out


class NoOverlaps(Policy):
    """Timed tasks must not overlap. A completed +fixed block still anchors
    its authoritative window (classes happen even when logged complete), so a
    pending task may not sit on one. A completed non-fixed task that still
    spans its original window should have been shortened to the actual time
    used before its remainder was reallocated."""

    id = "no-overlaps"

    def check(self, ctx):
        out = []
        week = ctx.week_tasks(["pending", "completed"])
        for day, tasks in sorted(ctx.by_day(ctx.timed(week)).items()):
            spans = sorted(
                ((ctx.datetimes(t), t) for t in tasks),
                key=lambda s: s[0][0],
            )
            for i in range(len(spans) - 1):
                (a_begin, a_end), a = spans[i]
                (b_begin, b_end), b = spans[i + 1]
                if b_begin >= a_end:
                    continue
                a_pending = a.get("status") == "pending"
                b_pending = b.get("status") == "pending"
                if not (a_pending or b_pending):
                    continue  # completed-vs-completed is historical noise
                if a_pending and b_pending:
                    pending, other = a, b
                else:
                    pending = a if a_pending else b
                    other = b if a_pending else a
                other = b if pending is a else a
                if "fixed" in other.get("tags", []):
                    out.append(Warning(
                        self.id, "ERROR",
                        f"pending '{pending['description'][:36]}' overlaps "
                        f"completed +fixed '{other['description'][:36]}' on "
                        f"{day} ({a_begin:%H:%M}-{max(a_end, b_end):%H:%M}); "
                        "fixed blocks anchor the schedule even when complete, "
                        "so move the pending task",
                        [pending.get("id"), other.get("id")],
                    ))
                elif other.get("status") == "completed":
                    out.append(Warning(
                        self.id, "WARN",
                        f"pending '{pending['description'][:36]}' overlaps "
                        f"completed '{other['description'][:36]}' on {day} "
                        f"({a_begin:%H:%M}-{a_end:%H:%M}); shorten the "
                        "completed task's window and est to the actual time "
                        "used, then reallocate the remainder",
                        [pending.get("id"), other.get("id")],
                    ))
                else:
                    out.append(Warning(
                        self.id, "ERROR",
                        f"overlapping tasks on {day}: "
                        f"{a_begin:%H:%M}-{a_end:%H:%M} "
                        f"and {b_begin:%H:%M}-{b_end:%H:%M}",
                        [a.get("id"), b.get("id")],
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

    # In-class work is done during the lecture and needs no take-home task.
    # The omn annotation (meta.kind = "in-class") is the source of truth, but
    # provider re-ingest replaces meta wholesale, so ids are pinned here too.
    IN_CLASS_IDS = {
        "canvasical:elearning.utdallas.edu:event-assignment-357594",  # Methods and Strings
        "canvasical:elearning.utdallas.edu:event-assignment-359033",  # 3_StringsLab
        "canvasical:elearning.utdallas.edu:event-assignment-361430",  # Class Activity 4 - Arrays
    }

    def check(self, ctx):
        tw_by_due = defaultdict(list)
        for t in ctx.tasks:
            due = parse_tw_date(t.get("due"))
            if due:
                tw_by_due[due.date()].append(t)
        out = []
        for record, due in ctx.omn_assignments():
            if record.get("id") in self.IN_CLASS_IDS:
                continue
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
        """Every omn lecture occurrence in the week must exist as a +fixed +class
        task with matching date, start time, and location; past occurrences may be
        satisfied by completed tasks."""
    
        id = "classes-scheduled"
    
        def check(self, ctx):
            out = []
            classes = [
                t for t in ctx.tasks
                if t.get("status") in ("pending", "completed")
                and "class" in t.get("tags", []) and ctx.in_week(t)
            ]
            for record in ctx.lectures():
                times = event_times(record)
                if not times:
                    continue
                start = times[0]
                occ_days = expand_rrule(
                    record["meta"]["rrule"], ctx.week_monday)
                cancelled = set((record["meta"].get("cancelled") or []))
                for day in occ_days:
                    if str(day) in cancelled:
                        continue  # instructor cancelled this occurrence
                    same_day = [
                        t for t in classes
                        if parse_tw_date(t.get("scheduled")).date() == day
                    ]
                    hit = next(
                        (t for t in same_day
                         if t.get("starttime") == start.strftime("%H:%M")),
                        None)
                    if hit is None:
                        past = day < ctx.now.date()
                        out.append(Warning(
                            self.id, "INFO" if past else "ERROR",
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
                    (t for t in ctx.tasks
                     if t.get("status") in ("pending", "completed")
                     and ctx.in_week(t)
                     and parse_tw_date(t.get("scheduled")).date() == day
                     and (record["meta"].get("flexible_time")
                         or t.get("starttime") == start_time)
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
            t for t in ctx.tasks
            if t.get("status") in ("pending", "completed")
            and ctx.in_week(t)
            and "PyLingual" not in t["description"]
            and ("Jee's lab" in (t.get("location") or "")
                 or t["description"].lower().startswith("lab work"))
        ]
        meeting = [
            t for t in ctx.tasks
            if t.get("status") in ("pending", "completed")
            and ctx.in_week(t)
            and "PyLingual lab meeting" in t["description"]
        ]
        total = sum(
            (ctx.est_of(t) or ctx.duration(t) or timedelta()
             for t in lab + meeting), timedelta())
        days_used = sorted({
            parse_tw_date(t.get("scheduled")).weekday()
            for t in lab + meeting
        })
        if total < timedelta(hours=5, minutes=45):  # ~6h target, 15m tolerance
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
    """Homeworks belong on weekdays. Weekends are for driving, errands,
    groceries, and rest, so assignment work scheduled on Sat/Sun is a warning
    even when a deadline lands there: front-load it into the weekdays instead.
    Personal projects (Petals, novel, piano) and errands are fine on weekends."""

    id = "weekend-assignment-work"

    HOMEWORK = re.compile(
        r"\b(homework|assignment|problem set|theory assignment|"
        r"programming assignment|memo|essay|report|paper|quiz|exam prep|"
        r"ps\d|hw\d|ta\d)\b",
        re.IGNORECASE)

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            sched = parse_tw_date(t.get("scheduled"))
            if not sched or sched.weekday() not in (5, 6):
                continue
            if "fixed" in t.get("tags", []):
                continue  # exams, appointments and events anchor the weekend
            desc = t["description"]
            if not (t.get("due") or self.HOMEWORK.search(desc)):
                continue
            if not self.HOMEWORK.search(desc):
                continue  # errands with a due date are weekend-appropriate
            out.append(Warning(
                self.id, "WARN",
                f"homework '{desc[:40]}' scheduled {sched:%a %Y-%m-%d}; schedule "
                "homework on weekdays and keep weekends for errands, driving, "
                "groceries, and rest",
                [t.get("id")],
            ))
        return out


class MorningBoundary(Policy):
    """Nothing is scheduled before the later of 10:00 and the day's first
    class end + transit: mornings are flex time (meals exempt, classes are
    the anchors). Provisional while the user's sleep schedule settles."""

    id = "morning-boundary"

    def check(self, ctx):
        out = []
        by_day_all = ctx.by_day(ctx.week_tasks(["pending", "completed"]))
        for day, tasks in sorted(ctx.by_day(ctx.week_pending()).items()):
            classes = [
                t for t in by_day_all.get(day, tasks)
                if "class" in t.get("tags", []) and t.get("endtime")
            ]
            boundary = time(10, 0)
            if classes:
                first_end = min(t["endtime"] for t in classes)
                hh, mm = map(int, first_end.split(":"))
                b = (datetime.combine(day, time(hh, mm)) + timedelta(minutes=30)).time()
                boundary = max(boundary, b)
            first_class = min(
                (t for t in classes if t.get("starttime")),
                key=lambda t: t["starttime"], default=None)
            for t in tasks:
                if not t.get("starttime"):
                    continue
                if "class" in t.get("tags", []):
                    continue  # classes anchor the boundary
                desc = t["description"].lower()
                if desc.startswith(("eat breakfast", "eat lunch", "eat dinner")):
                    continue  # meals are allowed in the morning
                if desc.startswith("cook"):
                    continue  # the user cooks before breakfast by request
                start = ctx.clock(t["starttime"])
                same_building = (
                    first_class is not None
                    and building_code(t.get("location"))
                    and building_code(t.get("location"))
                    == building_code(first_class.get("location"))
                )
                if same_building and start >= ctx.clock(first_class["endtime"]):
                    continue  # staying in the same building after class
                if start < boundary:
                    out.append(Warning(
                        self.id, "WARN",
                        f"'{t['description'][:40]}' starts {start:%H:%M} before "
                        f"the {boundary:%H:%M} morning boundary on {day} "
                        "(mornings are flex time; fine if venue-forced or "
                        "user-approved)",
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
    """Timed tasks need unallocated gaps matching the location-based transit
    rule between neighbors at different places: 0m same place, 10m same
    building, 20m different buildings on campus, 30m off-campus moves."""

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
                need = transit_minutes(prev.get("location"), nxt.get("location"))
                if gap < need:
                    out.append(Warning(
                        self.id, "WARN",
                        f"only {gap:.0f}m between '{prev['description'][:28]}' "
                        f"({prev.get('location') or 'no location'}) and "
                        f"'{nxt['description'][:28]}' ({nxt.get('location') or 'no location'}) "
                        f"on {day}; transit needs ~{need}m (or user-approved tight transition)",
                        [prev.get("id"), nxt.get("id")],
                    ))
        return out


class MissingLocation(Policy):
    """Every scheduled (timed) task must carry a location so transit can be
    computed; untimed tasks are exempt until they get a time block."""

    id = "missing-location"

    def check(self, ctx):
        out = []
        for t in ctx.timed(ctx.week_pending()):
            if not (t.get("location") or "").strip():
                out.append(Warning(
                    self.id, "WARN",
                    f"timed task '{t['description'][:40]}' has no location; "
                    "set one (e.g. 'SU Starbucks', 'ECSS 3.226', 'At home')",
                    [t.get("id")],
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
        week = ctx.by_day(ctx.week_tasks(["pending", "completed"]))
        active_days = [d for d in sorted(week) if week[d] and d >= ctx.now.date()]
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
        # The user cooks every meal: an hour of cooking precedes breakfast.
        for day in active_days:
            cooks = [t for t in week[day] if t["description"].lower().startswith("cook")]
            if not cooks:
                out.append(Warning(
                    self.id, "WARN",
                    f"no cooking block scheduled on {day}; the user cooks every "
                    "meal and budgets an hour before breakfast",
                ))
            breakfast = [t for t in week[day] if t["description"].lower().startswith("eat breakfast")]
            if cooks and breakfast:
                cook_end = max((ctx.clock(t.get("endtime")) for t in cooks if t.get("endtime")), default=None)
                eat_start = ctx.clock(breakfast[0].get("starttime"))
                if cook_end and eat_start and cook_end > eat_start:
                    out.append(Warning(
                        self.id, "WARN",
                        f"cooking on {day} ends {cook_end:%H:%M} but breakfast "
                        f"starts {eat_start:%H:%M}; cooking precedes breakfast",
                        [t.get("id") for t in cooks + breakfast],
                    ))
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
    """`task schedule` shows today's plan and nothing else. A pending task left
    on a past date is carried work that was never rescheduled: it pollutes the
    daily agenda and loses its time slot. This is an error, not a note, because
    every planning pass must move unfinished work forward before it reports."""

    id = "stale-scheduling"

    def check(self, ctx):
        out = []
        for t in ctx.pending:
            sched = parse_tw_date(t.get("scheduled"))
            if sched and sched.date() < ctx.now.date():
                days = (ctx.now.date() - sched.date()).days
                out.append(Warning(
                    self.id, "ERROR",
                    f"'{t['description'][:40]}' is still scheduled for "
                    f"{sched:%Y-%m-%d} ({days}d ago); reschedule it forward so "
                    "`task schedule` stays today-only",
                    [t.get("id")],
                ))
        return out


# ---------------------------------------------------- split-task helpers
    
# Descriptions that mark a task as one piece of a deliberately split task.
SPLIT_PREFIX = re.compile(
    r"^(start|finish|continue|complete|work on|part \d+ of|step \d+ of)\s+",
    re.IGNORECASE)
    
    
def split_family_key(description: str) -> str | None:
    """Return the family key for a split piece, or None if the description
    does not look like a piece of a larger task."""
    text = (description or "").strip()
    if not SPLIT_PREFIX.match(text):
        return None
    key = SPLIT_PREFIX.sub("", text)
    key = re.sub(r"\s*\((?:(?:part|chunk|piece)\s*\d+)\)\s*$", "", key,
                 flags=re.IGNORECASE)
    return key.strip().lower() or None
    
    
def split_families(ctx) -> dict[str, list[dict]]:
    """Group this week's pending tasks into split-task families (>=2 pieces)."""
    families: dict[str, list[dict]] = defaultdict(list)
    for t in ctx.week_pending():
        key = split_family_key(t.get("description"))
        if key:
            families[key].append(t)
    return {k: v for k, v in families.items() if len(v) >= 2}
    
    
def piece_span(ctx, t: dict) -> timedelta | None:
    return ctx.duration(t) or ctx.est_of(t)
    
    
# ------------------------------------------------------------ split policies
    
    
class VagueLocation(Policy):
    """Timed tasks must name a real place, not an area 'near' one."""
    
    id = "vague-location"
    
    PATTERN = re.compile(
        r"\b(near|nearby|around|somewhere|tbd|unspecified|anywhere|"
        r"outside|classroom|wherever)\b|\bn/?a\b",
        re.IGNORECASE)
    
    def check(self, ctx):
        out = []
        for t in ctx.week_pending():
            loc = t.get("location") or ""
            if loc and self.PATTERN.search(loc):
                out.append(Warning(
                    self.id, "WARN",
                    f"'{t['description'][:40]}' has vague location '{loc}'; "
                    "name a real place (default to SU Starbucks for "
                    "between-class blocks)",
                    [t.get("id")],
                ))
        return out
    
    
class MultipartChunkMinimum(Policy):
    """Pieces of a split task stay whole: no chunk shorter than one hour."""
    
    id = "multipart-chunk-minimum"
    
    MINIMUM = timedelta(hours=1)
    
    def check(self, ctx):
        out = []
        for key, pieces in sorted(split_families(ctx).items()):
            for t in pieces:
                span = piece_span(ctx, t)
                if span is not None and span < self.MINIMUM:
                    sched = parse_tw_date(t.get("scheduled"))
                    out.append(Warning(
                        self.id, "WARN",
                        f"split task '{key[:32]}' has a {span} piece "
                        f"('{t['description'][:32]}', {sched.date() if sched else '?'}); "
                        "pieces are at least 1h or the task is done in one block",
                        [t.get("id")],
                    ))
        return out
    
    
class MultipartOrder(Policy):
    """A 'start' piece is never scheduled after its 'finish' piece."""
    
    id = "multipart-order"
    
    def check(self, ctx):
        out = []
        for key, pieces in sorted(split_families(ctx).items()):
            starts, finishes = [], []
            for t in pieces:
                desc = (t.get("description") or "").strip().lower()
                span = ctx.datetimes(t)
                if span is None:
                    continue
                if desc.startswith("start"):
                    starts.append((span[0], t))
                elif desc.startswith("finish"):
                    finishes.append((span[0], t))
            for s_begin, s_task in starts:
                for f_begin, f_task in finishes:
                    if s_begin >= f_begin:
                        out.append(Warning(
                            self.id, "ERROR",
                            f"'{s_task['description'][:36]}' is scheduled at "
                            f"{s_begin:%a %H:%M} but "
                            f"'{f_task['description'][:36]}' at "
                            f"{f_begin:%a %H:%M}; reorder the pieces",
                            [s_task.get("id"), f_task.get("id")],
                        ))
        return out
    
    
class MultipartMerge(Policy):
    """Prefer one contiguous block over splitting a task across days."""
    
    id = "multipart-merge"
    
    def check(self, ctx):
        out = []
        for key, pieces in sorted(split_families(ctx).items()):
            days = sorted({
                parse_tw_date(t.get("scheduled")).date()
                for t in pieces if parse_tw_date(t.get("scheduled"))
            })
            if len(days) < 2:
                continue
            total = sum(
                (piece_span(ctx, t) or timedelta(0) for t in pieces),
                timedelta(0))
            out.append(Warning(
                self.id, "WARN",
                f"split task '{key[:36]}' is spread over {len(days)} days "
                f"({total} total); merge it into one block on a later day "
                "unless a deadline forbids it",
                [t.get("id") for t in pieces],
            ))
        return out
    
    
class RecurrenceArtifactsCovered(Policy):
    """Records carrying an `artifacts.rrule` artifact state durable recurrence
    quotas (for example "at least 4 sessions per calendar week" for piano).
    Those quotas were invisible to the linter, so a whole week could pass with
    no sessions scheduled. Read each artifact, parse its minimum, and count the
    week's matching tasks.

    Matching is deliberately simple: the record title's first word appears in
    the task description. An artifact declaring something "is separate from"
    the sessions (the Friday piano lesson) contributes an exclusion term.
    """

    id = "recurrence-artifacts-covered"

    MINIMUM_RE = re.compile(r"at least (\d+) sessions? per", re.IGNORECASE)
    EXCLUSION_RE = re.compile(
        r"([A-Za-z][A-Za-z ]{2,30}?)\s+(?:is|are) separate from", re.IGNORECASE)

    def check(self, ctx):
        out = []
        for record in ctx.omn:
            meta = record.get("meta", {})
            if meta.get("active") is False:
                continue
            uri = (record.get("artifacts") or {}).get("rrule")
            if not uri or not uri.startswith("file://"):
                continue
            try:
                with open(urllib.parse.unquote(uri[len("file://"):])) as f:
                    text = f.read()
            except OSError:
                continue  # a missing artifact is another policy's problem
            match = self.MINIMUM_RE.search(text)
            if not match:
                continue
            minimum = int(match.group(1))
            title = record.get("title") or ""
            keyword = title.split()[0].lower() if title else ""
            if not keyword:
                continue
            exclusion = self.EXCLUSION_RE.search(text)
            exclude_terms = []
            if exclusion:
                exclude_terms = [
                    w for w in exclusion.group(1).strip().lower().split()
                    if w not in ("the", "weekly", keyword)
                ]
            sessions = [
                t for t in ctx.week_tasks(["pending", "completed"])
                if keyword in t["description"].lower()
                and not any(x in t["description"].lower() for x in exclude_terms)
            ]
            if len(sessions) >= minimum:
                continue
            out.append(Warning(
                self.id, "ERROR",
                f"'{title}': {len(sessions)} of >= {minimum} sessions this week; "
                "schedule the remaining sessions from the artifact in the week's "
                "free afternoon slots",
                [t.get("id") for t in sessions] or [record.get("id")],
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
    MorningBoundary(),
    OverduePending(),
    StaleScheduling(),
    EstWindowMatch(),
    MinimumEstimate(),
    EstFormat(),
    TransportSet(),
    ClassTravelUda(),
    TransitBuffers(),
    MissingLocation(),
    CarTripGrouping(),
    Meals(),
    AfternoonBreak(),
    VenueHours(),
    ImperativeVerb(),
    PianoSplitting(),
    VagueLocation(),
    MultipartChunkMinimum(),
    MultipartOrder(),
    MultipartMerge(),
    RecurrenceArtifactsCovered(),
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
