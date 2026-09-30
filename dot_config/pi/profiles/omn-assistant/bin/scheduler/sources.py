"""Read the week's requirements and fixed intervals.

Live mode reads ``omn export`` and ``task export`` directly; a JSON spec file is
retained purely as a deterministic testing/debugging seam (``--spec``).

The reader never guesses: a missing or ambiguous estimate becomes a blocking
diagnostic, an inactive/superseded record is skipped with an info note, an
overdue requirement is surfaced as blocking rather than silently dropped, and
two overlapping fixed intervals are reported as a tagged hard failure.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from datetime import date, datetime, timedelta

from . import rrule as rrule_mod
from .common import (
    BLOCKING,
    INFO,
    MINUTES_PER_WEEK,
    TZ,
    ComposerConfig,
    Diagnostic,
    FixedInterval,
    LegacyTask,
    Requirement,
    SupportWindow,
    WeekInput,
    hhmm_to_minutes,
    local_iso_timestamp,
    normalize_week_start,
    parse_est_minutes,
    parse_iso_minutes,
    week_dates,
)

GENERIC_TAGS = {
    "canvas", "ical", "manual", "todo", "this-week", "utd", "fall-2026",
    "active", "inactive", "backlog", "optional", "personal", "event",
    "recurring", "lab", "class", "course", "project", "homework",
}
SKIP_STATUS = {"completed", "cancelled", "canceled", "superseded", "deleted"}
AMBIGUOUS_EST_MARKERS = ("placeholder", "unknown", "ambiguous", "tbd", "rough")


# ------------------------------------------------------------------- runners


def read_omn_export() -> list:
    result = subprocess.run(["omn", "export"], capture_output=True, text=True,
                            check=False)
    if result.returncode != 0:
        raise RuntimeError(f"omn export failed: {result.stderr.strip()}")
    return json.loads(result.stdout or "[]")


def read_task_export() -> list:
    result = subprocess.run(
        ["task", "rc.verbose=nothing", "status.not:deleted", "export"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"task export failed: {result.stderr.strip()}")
    return json.loads(result.stdout or "[]")


# --------------------------------------------------------------- derivations


def derive_topic(record: dict) -> str:
    meta = record.get("meta") or {}
    if meta.get("topic"):
        return str(meta["topic"])
    for key in ("course_id", "project_id"):
        if meta.get(key):
            return str(meta[key]).split(":")[-1]
    tags = [str(tag) for tag in (record.get("tags") or [])]
    for tag in tags:
        if tag in GENERIC_TAGS:
            continue
        if re.search(r"\d", tag) or "-" in tag:
            return tag
    for tag in tags:
        if tag not in GENERIC_TAGS:
            return tag
    return str(record.get("id", "general")).split(":")[-1] or "general"


def derive_location(record: dict) -> str:
    meta = record.get("meta") or {}
    return str(meta.get("location") or "At home")


def derive_transport(record: dict) -> str:
    meta = record.get("meta") or {}
    value = str(meta.get("transport") or "no-car").lower()
    return value if value in {"car", "no-car"} else "no-car"


def derive_travel(record: dict, location: str) -> str | None:
    meta = record.get("meta") or {}
    if meta.get("travel"):
        return str(meta["travel"])
    # `travel` records the usual home commute cost. Work at home needs none;
    # campus and venue blocks conservatively use the standing 30m commute.
    return None if location.casefold() in {"at home", "home"} else "30m"


def is_inactive(record: dict) -> tuple[bool, str | None]:
    meta = record.get("meta") or {}
    if meta.get("active") is False:
        return True, "inactive"
    if meta.get("superseded_by"):
        return True, "superseded"
    status = str(meta.get("status", "")).lower()
    if status in SKIP_STATUS:
        return True, status
    tags = {str(tag).lower() for tag in (record.get("tags") or [])}
    if "superseded" in tags or "inactive" in tags:
        return True, "superseded" if "superseded" in tags else "inactive"
    return False, None


def active_omn_ids(omn: list) -> set:
    ids = set()
    for record in omn:
        inactive, _ = is_inactive(record)
        if not inactive:
            ids.add(record.get("id"))
    return ids


def _target_week_span(record: dict) -> tuple[date, date] | None:
    raw = (record.get("meta") or {}).get("target_week")
    if not raw:
        return None
    try:
        start_text, _, end_text = str(raw).partition("/")
        return date.fromisoformat(start_text[:10]), date.fromisoformat(end_text[:10])
    except ValueError:
        return None


# ------------------------------------------------------- requirement readers


def requirements_from_omn(
    omn: list,
    week_start: date,
    config: ComposerConfig,
    diagnostics: list,
    *,
    forced_ids: set | None = None,
) -> list:
    week_end = week_start + timedelta(days=6)
    forced_ids = forced_ids or set()
    out: list = []
    for record in omn:
        if record.get("type") != "task":
            continue
        inactive, reason = is_inactive(record)
        if inactive:
            diagnostics.append(Diagnostic(
                "inactive-record", INFO,
                f"skipping {reason} omn task '{record.get('title', record.get('id'))}'",
                [record.get("id")],
            ))
            continue
        meta = record.get("meta") or {}
        if meta.get("kind") == "in-class":
            diagnostics.append(Diagnostic(
                "in-class", INFO,
                f"'{record.get('title', '')}' is in-class work; no take-home block",
                [record.get("id")],
            ))
            continue

        span = _target_week_span(record)
        target_this_week = bool(span and span[0] <= week_end and week_start <= span[1])
        due_minutes = parse_iso_minutes(meta.get("due"), week_start, end_of_day=True)
        due_in_week = (due_minutes is not None
                       and 0 < due_minutes <= MINUTES_PER_WEEK)
        forced = record.get("id") in forced_ids
        if due_minutes is not None and due_minutes <= 0:
            # A historical Canvas feed item is not evidence that the work is
            # still pending. Only explicit target/current state or a carried
            # Taskwarrior ref makes an elapsed deadline actionable here.
            explicitly_pending = (forced or target_this_week
                                  or meta.get("active") is True
                                  or str(meta.get("status", "")).lower() == "pending")
            if explicitly_pending:
                diagnostics.append(Diagnostic(
                    "overdue-requirement", BLOCKING,
                    f"'{record.get('title', '')}' is due {meta.get('due')} before the "
                    f"selected week; reconcile it in omn (complete or reschedule) "
                    f"before planning",
                    [record.get("id")],
                    assumption="overdue requirements are not silently dropped or "
                    "pretended into the week",
                ))
            continue
        if not target_this_week and not due_in_week and not forced:
            continue

        est_minutes = parse_est_minutes(meta.get("est"))
        if est_minutes is None:
            diagnostics.append(Diagnostic(
                "missing-estimate", BLOCKING,
                f"'{record.get('title', '')}' has no estimable meta.est; supply an "
                f"estimate before planning",
                [record.get("id")],
            ))
            continue
        est_status = str(meta.get("est_status", "")).lower()
        if any(marker in est_status for marker in AMBIGUOUS_EST_MARKERS):
            diagnostics.append(Diagnostic(
                "ambiguous-estimate", BLOCKING,
                f"'{record.get('title', '')}' has est_status '{meta.get('est_status')}'; "
                f"confirm the estimate instead of trusting a placeholder",
                [record.get("id")],
                assumption="ambiguous estimates are flagged, never silently accepted",
            ))

        window_start = parse_iso_minutes(meta.get("unlock"), week_start)
        if window_start is None:
            window_start = parse_iso_minutes(meta.get("available"), week_start)
        window_end = due_minutes
        if window_end is None:
            window_end = MINUTES_PER_WEEK
        window_end = min(window_end, MINUTES_PER_WEEK)
        start_bound = max(0, window_start if window_start is not None else 0)

        kind = "assignment" if due_minutes is not None else "project"
        due_local = local_iso_timestamp(meta.get("due"), week_start)
        location = derive_location(record)

        out.append(Requirement(
            id=str(record.get("id")),
            title=str(record.get("title") or record.get("id")),
            kind=kind,
            required_minutes=est_minutes,
            effective_minutes=max(est_minutes, 0),
            window_start=start_bound,
            window_end=window_end,
            topic=derive_topic(record),
            location=location,
            due=meta.get("due"),
            due_local=due_local,
            available=meta.get("unlock") or meta.get("available"),
            est_raw=meta.get("est"),
            transport=derive_transport(record),
            travel=derive_travel(record, location),
            indivisible=bool(meta.get("indivisible")),
            source="omn",
        ))
    return out


def requirements_from_spec(spec: dict, week_start: date, config: ComposerConfig,
                           diagnostics: list) -> list:
    out: list = []
    for item in spec.get("requirements", []):
        est_minutes = parse_est_minutes(item.get("est"))
        rid = str(item.get("omn_id") or item.get("id"))
        if est_minutes is None:
            diagnostics.append(Diagnostic(
                "missing-estimate", BLOCKING,
                f"spec requirement '{item.get('title', rid)}' has no parseable est",
                [rid],
            ))
            continue
        window_start = parse_iso_minutes(item.get("available"), week_start)
        if window_start is None:
            window_start = parse_iso_minutes(item.get("unlock"), week_start)
        due_minutes = parse_iso_minutes(item.get("due"), week_start, end_of_day=True)
        if due_minutes is not None and due_minutes <= 0:
            diagnostics.append(Diagnostic(
                "overdue-requirement", BLOCKING,
                f"spec requirement '{item.get('title', rid)}' is due "
                f"{item.get('due')} before the selected week",
                [rid],
            ))
        window_end = due_minutes if due_minutes is not None else MINUTES_PER_WEEK
        topic = str(item.get("topic") or derive_topic({"id": rid, "meta": item}))
        out.append(Requirement(
            id=rid,
            title=str(item.get("title") or rid),
            kind=str(item.get("kind") or ("assignment" if due_minutes is not None else "project")),
            required_minutes=est_minutes,
            effective_minutes=max(est_minutes, 0),
            window_start=max(0, window_start if window_start is not None else 0),
            window_end=min(window_end, MINUTES_PER_WEEK),
            topic=topic,
            location=str(item.get("location") or "At home"),
            due=item.get("due"),
            due_local=local_iso_timestamp(item.get("due"), week_start),
            available=item.get("available"),
            est_raw=str(item.get("est")),
            transport=str(item.get("transport") or "no-car"),
            travel=item.get("travel"),
            indivisible=bool(item.get("indivisible")),
            source="spec",
        ))
    return out


# Standing support patterns (the user cooks every meal). Windows mirror the
# linter's Meals policy: breakfast 06:00-08:00, lunch 11:00-14:00 (1h),
# dinner 17:00-20:00, one hour of cooking before breakfast, and a 1-2h
# afternoon break. Supports are pushable/shrinkable inside these bounds.
SUPPORT_SPECS = [
    {"kind": "cook-breakfast", "label": "Cook breakfast", "dur_min": 60,
     "dur_max": 60, "clock": (6 * 60, 7 * 60 + 30), "location": "At home"},
    {"kind": "breakfast", "label": "Eat breakfast", "dur_min": 45,
     "dur_max": 45, "clock": (6 * 60 + 45, 8 * 60), "location": "At home",
     "after": "cook-breakfast"},
    {"kind": "lunch", "label": "Eat lunch", "dur_min": 60, "dur_max": 60,
     "clock": (11 * 60, 14 * 60), "location": "At home"},
    {"kind": "afternoon-break", "label": "Take afternoon break", "dur_min": 60,
     "dur_max": 120, "clock": (14 * 60, 18 * 60), "location": "SU Starbucks"},
    {"kind": "dinner", "label": "Eat dinner", "dur_min": 45, "dur_max": 45,
     "clock": (17 * 60, 20 * 60), "location": "At home"},
]


def default_supports(week_start: date) -> list:
    out = []
    for day, _date in enumerate(week_dates(week_start)):
        for spec in SUPPORT_SPECS:
            day_base = day * 1440
            out.append(SupportWindow(
                id=f"support:{spec['kind']}:{_date.isoformat()}",
                label=spec["label"],
                description=spec["label"],
                day=day,
                dur_min=spec["dur_min"],
                dur_max=spec["dur_max"],
                earliest=day_base + spec["clock"][0],
                latest=day_base + spec["clock"][1],
                location=spec.get("location"),
                after=spec.get("after"),
            ))
    return out


def supports_from_spec(spec: dict, week_start: date) -> list:
    out = []
    for item in spec.get("supports", []):
        out.append(SupportWindow(
            id=str(item["id"]),
            label=str(item.get("label") or item["id"]),
            description=str(item.get("description") or item.get("label") or item["id"]),
            day=int(item["day"]),
            dur_min=int(item.get("dur_min", item.get("duration", 30))),
            dur_max=int(item.get("dur_max", item.get("duration", 30))),
            earliest=int(item["earliest"]),
            latest=int(item["latest"]),
            location=item.get("location"),
            after=item.get("after"),
        ))
    return out


# ----------------------------------------------------------- fixed intervals


def sleep_intervals(week_start: date, wake_hour: int) -> list:
    out = []
    if wake_hour <= 0:
        return out
    for offset, day in enumerate(week_dates(week_start)):
        base = offset * 1440
        out.append(FixedInterval(
            id=f"sleep:{day.isoformat()}",
            label=f"Sleep 00:00-{wake_hour:02d}:00",
            start=base,
            end=base + wake_hour * 60,
            source="sleep",
            refs=[day.isoformat()],
            location=None,
        ))
    return out


def _event_buffers(meta: dict) -> tuple[int, int]:
    before = parse_est_minutes(meta.get("buffer_before")) or 0
    after = parse_est_minutes(meta.get("buffer_after")) or 0
    return before, after


def fixed_from_omn(omn: list, week_start: date, config: ComposerConfig,
                   diagnostics: list) -> list:
    out: list = []
    window_start = week_start
    window_end = week_start + timedelta(days=6)
    for record in omn:
        if record.get("type") != "event":
            continue
        meta = record.get("meta") or {}
        tags = {str(tag).lower() for tag in (record.get("tags") or [])}
        if ("mlh" in tags and meta.get("attending") is not True
                and str(meta.get("planning_status", "")).lower()
                not in {"attending", "confirmed-attending"}):
            # MLH ingestion is a catalog of opportunities, not a declaration
            # that the user will attend every event in the season.
            continue
        if meta.get("active") is False:
            diagnostics.append(Diagnostic(
                "inactive-event", INFO,
                f"skipping inactive event '{record.get('title', record.get('id'))}'",
                [record.get("id")],
            ))
            continue
        if meta.get("cancelled") is True:
            diagnostics.append(Diagnostic(
                "cancelled-event", INFO,
                f"skipping cancelled event '{record.get('title', record.get('id'))}'",
                [record.get("id")],
            ))
            continue
        start_raw, end_raw = meta.get("start"), meta.get("end")
        if not start_raw or not end_raw:
            diagnostics.append(Diagnostic(
                "fixed-missing-time", BLOCKING,
                f"event '{record.get('title', record.get('id'))}' has no start/end",
                [record.get("id")],
            ))
            continue
        try:
            start_dt = _aware(start_raw)
            end_dt = _aware(end_raw)
        except ValueError:
            diagnostics.append(Diagnostic(
                "fixed-missing-time", BLOCKING,
                f"event '{record.get('title', record.get('id'))}' has an unparseable "
                f"start/end",
                [record.get("id")],
            ))
            continue
        if not meta.get("rrule") and not (window_start <= start_dt.date() <= window_end):
            continue
        duration = int((end_dt - start_dt).total_seconds() // 60)
        if duration <= 0:
            diagnostics.append(Diagnostic(
                "fixed-missing-time", BLOCKING,
                f"event '{record.get('title', record.get('id'))}' has a non-positive "
                f"duration",
                [record.get("id")],
            ))
            continue
        before, after = _event_buffers(meta)
        tour = start_dt.hour * 60 + start_dt.minute
        title = str(record.get("title") or record.get("id"))

        if meta.get("rrule"):
            cancelled = _cancelled_dates(meta.get("cancelled"))
            try:
                occurrences = rrule_mod.expand_weekly(
                    meta["rrule"], start_dt, window_start, window_end)
            except rrule_mod.UnsupportedRecurrence as exc:
                diagnostics.append(Diagnostic(
                    "unsupported-rrule", BLOCKING,
                    f"event '{title}' recurrence is not supported: {exc}",
                    [record.get("id")],
                ))
                continue
            for occurrence in occurrences:
                if occurrence.isoformat() in cancelled:
                    diagnostics.append(Diagnostic(
                        "cancelled-occurrence", INFO,
                        f"'{title}' cancelled on {occurrence.isoformat()}",
                        [record.get("id")],
                    ))
                    continue
                base = (occurrence - week_start).days * 1440
                out.append(FixedInterval(
                    id=f"{record.get('id')}@{occurrence.isoformat()}",
                    label=title,
                    start=base + tour - before,
                    end=base + tour + duration + after,
                    source="omn-event",
                    refs=[record.get("id")],
                    location=derive_location(record),
                    buffer_before=before,
                    buffer_after=after,
                    cohort=meta.get("course_id"),
                ))
        else:
            day = start_dt.date()
            if not (window_start <= day <= window_end):
                continue
            if day.isoformat() in _cancelled_dates(meta.get("cancelled")):
                diagnostics.append(Diagnostic(
                    "cancelled-occurrence", INFO,
                    f"'{title}' cancelled on {day.isoformat()}",
                    [record.get("id")],
                ))
                continue
            base = (day - week_start).days * 1440
            out.append(FixedInterval(
                id=f"{record.get('id')}@{day.isoformat()}",
                label=title,
                start=base + tour - before,
                end=base + tour + duration + after,
                source="omn-event",
                refs=[record.get("id")],
                location=derive_location(record),
                buffer_before=before,
                buffer_after=after,
                cohort=meta.get("course_id"),
            ))
    return out


def fixed_from_spec(spec: dict, week_start: date, config: ComposerConfig,
                    diagnostics: list) -> list:
    out: list = []
    for index, item in enumerate(spec.get("fixed", [])):
        try:
            day = date.fromisoformat(str(item["day"])[:10])
            start_min = hhmm_to_minutes(item["start"])
            end_min = hhmm_to_minutes(item["end"])
        except (KeyError, ValueError) as exc:
            diagnostics.append(Diagnostic(
                "fixed-missing-time", BLOCKING,
                f"spec fixed item {index} is malformed: {exc}",
                [item.get("id", str(index))],
            ))
            continue
        base = (day - week_start).days * 1440
        before = int(item.get("buffer_before", 0) or 0)
        after = int(item.get("buffer_after", 0) or 0)
        out.append(FixedInterval(
            id=str(item.get("id") or f"spec-fixed-{index}"),
            label=str(item.get("desc") or item.get("title") or f"fixed {index}"),
            start=base + start_min - before,
            end=base + end_min + after,
            source="spec",
            refs=[str(item.get("id") or f"spec-fixed-{index}")],
            location=item.get("location"),
            buffer_before=before,
            buffer_after=after,
            cohort=item.get("cohort"),
        ))
    return out


def fixed_from_tasks(tasks: list, week_start: date, config: ComposerConfig,
                     diagnostics: list) -> list:
    """Pending +fixed tasks and unmanaged timed tasks are unavailable windows."""
    out: list = []
    week_end = week_start + timedelta(days=6)
    for task in tasks:
        if task.get("status") != "pending":
            continue
        tags = {str(tag).lower() for tag in (task.get("tags") or [])}
        is_fixed = "fixed" in tags
        unmanaged = "managed" not in tags
        timed = bool(task.get("starttime") and task.get("endtime"))
        if not (is_fixed or (unmanaged and timed)):
            continue
        if not timed:
            if is_fixed:
                diagnostics.append(Diagnostic(
                    "fixed-missing-time", BLOCKING,
                    f"+fixed task '{task.get('description', '')}' has no "
                    f"starttime/endtime",
                    [task.get("uuid")],
                ))
            continue
        day = _task_scheduled_date(task)
        if day is None or not (week_start <= day <= week_end):
            continue
        try:
            start_min = hhmm_to_minutes(task["starttime"])
            end_min = hhmm_to_minutes(task["endtime"])
        except ValueError:
            diagnostics.append(Diagnostic(
                "fixed-missing-time", BLOCKING,
                f"task '{task.get('description', '')}' has invalid starttime/endtime",
                [task.get("uuid")],
            ))
            continue
        base = (day - week_start).days * 1440
        end_absolute = base + end_min
        if end_absolute <= base + start_min:
            end_absolute += 1440
        out.append(FixedInterval(
            id=f"task:{task.get('uuid')}",
            label=str(task.get("description") or task.get("uuid")),
            start=base + start_min,
            end=end_absolute,
            source="task-fixed" if is_fixed else "task-unmanaged",
            refs=[task.get("uuid")],
            location=task.get("location"),
        ))
    return out


# ------------------------------------------------------------- legacy tasks


def legacy_from_tasks(tasks: list, plan_ids: set, week_start: date,
                      diagnostics: list, *, now: datetime | None = None) -> list:
    """Reconcile pending managed non-fixed tasks against omn.

    A task carrying ``[omn:<id>]`` refs that all resolve to active omn records
    is solver-owned (or an absorbed hand-authored block) and may be replaced on
    apply. Anything else is an unmatched legacy block: a blocking diagnostic,
    never a silent migration into omn.
    """
    out: list = []
    today = (now or datetime.now(TZ)).astimezone(TZ).date()
    week_end = week_start + timedelta(days=6)
    for task in tasks:
        if task.get("status") != "pending":
            continue
        tags = {str(tag).lower() for tag in (task.get("tags") or [])}
        if "managed" not in tags or "fixed" in tags:
            continue
        refs = _todo_refs(task)
        scheduled = task.get("scheduled")
        day = _task_scheduled_date(task)
        # A selected-week plan owns blocks in that week plus older pending
        # blocks that must be carried into it. Future blocks after this week
        # belong to another plan and are intentionally out of scope.
        if day is not None and day > week_end:
            continue
        carried = day is not None and day < today
        reconciled = bool(refs) and all(ref in plan_ids for ref in refs)
        entry = LegacyTask(
            uuid=str(task.get("uuid")),
            id=task.get("id"),
            description=str(task.get("description") or ""),
            scheduled=scheduled,
            due=task.get("due"),
            est=task.get("est"),
            todo_refs=refs,
            reconciled=reconciled,
            carried=carried,
        )
        out.append(entry)
        if reconciled:
            diagnostics.append(Diagnostic(
                "legacy-managed-reconciled", INFO,
                f"pending managed task '{entry.description[:48]}' reconciles to omn "
                f"and is superseded by the new plan",
                [entry.uuid],
            ))
        else:
            reason = ("no [omn:<id>] todo refs" if not refs
                      else "todo refs do not resolve to active omn records")
            diagnostics.append(Diagnostic(
                "legacy-managed-unmatched", BLOCKING,
                f"pending managed task '{entry.description[:48]}' cannot be "
                f"reconciled ({reason}); create or correct its omn record first — "
                f"it is never deleted or silently migrated",
                [entry.uuid],
                assumption="carried work is preserved until omn owns it",
            ))
    return out


# ------------------------------------------------------------- assembly


def detect_fixed_collisions(intervals: list, week_start: date,
                            diagnostics: list) -> None:
    ordered = sorted(intervals, key=lambda item: (item.start, item.end))
    for index, first in enumerate(ordered):
        for second in ordered[index + 1:]:
            if second.start >= first.end:
                break
            if first.overlaps(second):
                same_nested_commitment = (
                    first.cohort and first.cohort == second.cohort
                    and first.location == second.location
                    and ((first.start <= second.start and second.end <= first.end)
                         or (second.start <= first.start and first.end <= second.end))
                )
                if same_nested_commitment:
                    continue
                diagnostics.append(Diagnostic(
                    "fixed-collision", BLOCKING,
                    f"fixed intervals overlap: '{first.label}' "
                    f"[{first.start}..{first.end}] and '{second.label}' "
                    f"[{second.start}..{second.end}]",
                    list(dict.fromkeys(first.refs + second.refs)),
                    assumption="two authoritative windows cannot both occupy one "
                    "instant; resolve the source data",
                ))


def _assemble(week_start: date, config: ComposerConfig, requirements, fixed,
              legacy, diagnostics, source: str, metadata=None,
              supports=None) -> WeekInput:
    config.validate()
    intervals = list(fixed)
    intervals.extend(sleep_intervals(week_start, config.wake_hour))
    detect_fixed_collisions(intervals, week_start, diagnostics)
    return WeekInput(
        week_start=week_start,
        requirements=requirements,
        fixed_intervals=intervals,
        diagnostics=diagnostics,
        step=config.step,
        min_block=config.min_block,
        max_block=config.max_block,
        day_cap=config.day_cap,
        wake_hour=config.wake_hour,
        work_start_hour=config.work_start_hour,
        work_end_hour=config.work_end_hour,
        daily_budget_minutes=config.daily_budget_minutes,
        max_blocks=config.max_blocks,
        supports=list(supports) if supports is not None else default_supports(week_start),
        legacy=legacy,
        source=source,
        metadata=metadata or {},
    )


def load_spec(path, config: ComposerConfig | None = None) -> WeekInput:
    import dataclasses

    config = dataclasses.replace(config) if config is not None else ComposerConfig()
    with open(path) as handle:
        spec = json.load(handle)
    week_start = normalize_week_start(spec["week_start"])
    diagnostics: list = [Diagnostic(**item) for item in spec.get("diagnostics", [])]
    requirements = requirements_from_spec(spec, week_start, config, diagnostics)
    fixed = fixed_from_spec(spec, week_start, config, diagnostics)
    legacy = [LegacyTask(**item) for item in spec.get("legacy_managed_tasks", [])]
    if spec.get("sleep", True) is False:
        config.wake_hour = 0
    supports = (supports_from_spec(spec, week_start)
                if "supports" in spec else default_supports(week_start))
    return _assemble(week_start, config, requirements, fixed, legacy, diagnostics,
                     source="spec", metadata={"spec_path": str(path)},
                     supports=supports)


def load_live(
    week: str | date,
    config: ComposerConfig | None = None,
    *,
    omn_records: list | None = None,
    task_records: list | None = None,
    omn_runner=read_omn_export,
    task_runner=read_task_export,
    now: datetime | None = None,
) -> WeekInput:
    config = config or ComposerConfig()
    week_start = normalize_week_start(week)
    omn = omn_records if omn_records is not None else omn_runner()
    tasks = task_records if task_records is not None else task_runner()
    current = (now or datetime.now(TZ)).astimezone(TZ)
    week_end = week_start + timedelta(days=6)
    diagnostics: list = []

    # Pending managed work in or before this week is mandatory input even when
    # its omn due/target_week would not otherwise select it.
    forced_ids = set()
    for task in tasks:
        if task.get("status") != "pending":
            continue
        tags = {str(tag).lower() for tag in (task.get("tags") or [])}
        if "managed" not in tags or "fixed" in tags:
            continue
        scheduled_day = _task_scheduled_date(task)
        if scheduled_day is None or scheduled_day <= week_end:
            forced_ids.update(_todo_refs(task))

    requirements = requirements_from_omn(
        omn, week_start, config, diagnostics, forced_ids=forced_ids)

    # Never generate a live candidate in elapsed time. Tests/specs stay fully
    # deterministic; only direct live ingestion applies the current-time floor.
    if week_start <= current.date() <= week_end:
        elapsed = ((current.date() - week_start).days * 1440
                   + current.hour * 60 + current.minute)
        floor = math.ceil(elapsed / config.step) * config.step
        for requirement in requirements:
            requirement.window_start = max(requirement.window_start, floor)
    elif current.date() > week_end:
        diagnostics.append(Diagnostic(
            "selected-week-past", BLOCKING,
            f"selected week {week_start.isoformat()}..{week_end.isoformat()} "
            "has already elapsed",
            [week_start.isoformat()],
        ))

    fixed = fixed_from_omn(omn, week_start, config, diagnostics)
    fixed.extend(fixed_from_tasks(tasks, week_start, config, diagnostics))
    plan_ids = {requirement.id for requirement in requirements}
    legacy = legacy_from_tasks(
        tasks, plan_ids, week_start, diagnostics, now=current)
    return _assemble(week_start, config, requirements, fixed, legacy, diagnostics,
                     source="live", metadata={"loaded_at": current.isoformat()})


# ------------------------------------------------------------------ helpers


def _aware(value) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def _cancelled_dates(value) -> set:
    if not value:
        return set()
    if isinstance(value, str):
        value = [value]
    return {str(item)[:10] for item in value}


def _todo_refs(task: dict) -> list:
    return re.findall(r"\[omn:([^\]\s]+)\]", task.get("todo") or "")


def _task_scheduled_date(task: dict):
    value = task.get("scheduled")
    if not value:
        return None
    text = str(value)
    try:
        if text.endswith("Z"):
            return datetime.strptime(
                text, "%Y%m%dT%H%M%SZ").replace(tzinfo=TZ).date()
        if "T" in text:
            return datetime.strptime(text[:15], "%Y%m%dT%H%M%S").date()  # noqa: DTZ007
        return datetime.strptime(text[:8], "%Y%m%d").date()  # noqa: DTZ007
    except ValueError:
        return None
