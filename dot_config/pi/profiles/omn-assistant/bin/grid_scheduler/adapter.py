"""Read-only omn/Taskwarrior -> grid compiler.

Reuses legacy *source parsing* and recurrence utilities, never its model,
heuristics, decode, or apply policy. All amount rounding is explicit; fixed
clock authority is retained separately from its conservative grid envelope.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta

from scheduler import sources
from scheduler.common import (
    TZ,
    ComposerConfig,
    hhmm_to_minutes,
    normalize_week_start,
    parse_est_minutes,
)

from .schema import (
    CELLS,
    ROWS,
    STEP,
    TRAVEL,
    Color,
    Group,
    Item,
    Problem,
    Reservation,
    ceil_slot,
)


def digest(omn, tasks):
    # Taskwarrior recomputes `urgency` from due-date proximity on every export,
    # so it drifts with wall-clock time without any real source change. Hash
    # only real source state; derived values must not invalidate a plan.
    stable = [{k: v for k, v in task.items() if k != "urgency"} for task in tasks]
    payload = {"omn": sorted(omn, key=lambda r: str(r.get("id"))),
               "tasks": sorted(stable, key=lambda r: str(r.get("uuid")))}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def task_date(task):
    value = str(task.get("scheduled") or "")
    if not value:
        return None
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z", value):
            from datetime import timezone
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(TZ).date()
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return (parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)).astimezone(TZ).date()
        from datetime import date
        return date.fromisoformat(value) if "-" in value else datetime.strptime(value, "%Y%m%d").replace(tzinfo=TZ).date()
    except ValueError:
        return None


def task_snapshot(tasks, week_start):
    return [t for t in tasks if t.get("status") == "pending" and (task_date(t) is None
            or 0 <= (task_date(t) - week_start).days < 7)]


def completed_credit(tasks, week_start):
    """Pins apportion completed work, rather than crediting every ref the block."""
    credit = {}
    for task in tasks:
        if task.get("status") != "completed" or "travel" in task.get("tags", []):
            continue
        day = task_date(task)
        if day is None or not 0 <= (day - week_start).days < 7:
            continue
        duration = parse_est_minutes(task.get("est"))
        if duration is None and task.get("starttime") and task.get("endtime"):
            duration = (hhmm_to_minutes(task["endtime"]) - hhmm_to_minutes(task["starttime"])) % 1440
        if duration is None:
            continue
        pinned, open_ids = {}, []
        for line in str(task.get("todo") or "").splitlines():
            ref = re.search(r"\[omn:([^\]]+)\]", line)
            if not ref:
                continue
            pin = re.search(r"@(\d+)m\b", line)
            if pin:
                pinned[ref[1]] = pinned.get(ref[1], 0) + int(pin[1])
            else:
                open_ids.append(ref[1])
        if sum(pinned.values()) > duration or len(open_ids) > 1:
            raise ValueError(f"ambiguous completed allocation: {task.get('uuid')}")
        for rid, minutes in pinned.items():
            credit[rid] = credit.get(rid, 0) + minutes
        if open_ids:
            rid = open_ids[0]
            credit[rid] = credit.get(rid, 0) + duration - sum(pinned.values())
    return credit


def load_live(week: str, *, now: datetime | None = None, work_start: int = 8,
              work_end: int = 24, previous: dict | None = None,
              omn_records=None, task_records=None) -> Problem:
    current = (now or datetime.now(TZ)).astimezone(TZ)
    week_start = normalize_week_start(week)
    omn = sources.read_omn_export() if omn_records is None else omn_records
    tasks = sources.read_task_export() if task_records is None else task_records
    # Normalize wall-clock dates before calling the old source parser: its
    # compact timestamp helper does not accept ISO dates or convert UTC dates.
    parsed_tasks = [dict(t, scheduled=task_date(t).strftime("%Y%m%d"))
                    if task_date(t) is not None else t for t in tasks]
    cfg = ComposerConfig(step=15, min_block=60, max_block=1440, work_start_hour=work_start,
                         preferred_end_hour=min(18, work_end), work_end_hour=work_end)
    cfg.validate()
    import math
    elapsed = ((current.date() - week_start).days * 1440 + current.hour * 60 + current.minute
               + (current.second + current.microsecond / 1_000_000) / 60)
    prefix = min(CELLS, max(0, math.ceil(elapsed / STEP)))
    if elapsed >= CELLS * STEP:
        raise ValueError("selected week has elapsed")
    if previous and previous["problem"]["week_start"] != week_start.isoformat():
        raise ValueError("previous schedule belongs to another week")
    from scheduler.common import BLOCKING, Diagnostic

    from .facts import reconcile_fixed, week_records
    diagnostics = []
    facts = week_records(omn, week_start)
    for record in facts:
        coverage = (record.get("meta") or {}).get("planning_coverage")
        if coverage:
            diagnostics.append(Diagnostic("fixed-assessment-linked", "info",
                f"{record.get('title')}: covered by fixed exam occurrence, not extra prep or completion",
                [record["id"], coverage["fixed_event"]]))
    from .policies import daily_bounds, intersect_windows, opening_windows
    # Daily occurrences are Python item identities, never solver colors.
    for record in facts:
        meta = record.get("meta") or {}
        if any(k in meta for k in ("daily_est", "daily_min_est", "daily_max_est")):
            quota = daily_bounds(meta, str(record["id"]), week_start, [])
            meta.setdefault("est", f"{sum(hi for _lo, hi in quota.values()) * STEP}m")
            meta.setdefault("min_est", f"{sum(lo for lo, _hi in quota.values()) * STEP}m")
            meta.setdefault("max_est", f"{sum(hi for _lo, hi in quota.values()) * STEP}m")
    credit = completed_credit(tasks, week_start)
    requirements = sources.requirements_from_omn(
        facts, week_start, cfg, diagnostics, completed_credit=credit)
    cancelled_ids, cancelled_support, cancelled_occurrences = set(), set(), set()
    cancelled_travel_windows = []
    if previous:
        old_meta = previous["problem"].get("metadata", {})
        cancelled_travel_windows.extend(old_meta.get("cancelled_travel_windows", []))
        cancelled_ids.update(old_meta.get("cancelled_ids", []))
        cancelled_support.update(old_meta.get("cancelled_support", []))
        cancelled_occurrences.update(old_meta.get("cancelled_occurrences", []))
        # An apply receipt distinguishes the engine's own approved replacement
        # deletions from an action the user subsequently removed. Do not restore
        # vanished actions from unchanged source facts.
        snapshot = previous.get("task_receipt", old_meta.get("source_task_snapshot", []))
        present_ids = {t.get("uuid") for t in tasks if t.get("status") != "deleted"}
        for task in snapshot:
            if task.get("uuid") not in present_ids:
                day = task_date(task)
                refs = sources._todo_refs(task)
                if "travel" in task.get("tags", []) and day is not None:
                    delta = (day - week_start).days
                    if 0 <= delta < 7 and task.get("starttime") and task.get("endtime"):
                        a, b = hhmm_to_minutes(task["starttime"]), hhmm_to_minutes(task["endtime"])
                        if b <= a:
                            b += 1440
                        offset = delta * ROWS
                        cancelled_travel_windows.append([offset + a // STEP, min(CELLS, offset + ceil_slot(b))])
                    continue  # never cancel its destination's work or recreate this trip
                if "fixed" in task.get("tags", []):
                    if day is not None:
                        cancelled_occurrences.update(f"{rid}@{day}" for rid in refs)
                    for rid, uuids in old_meta.get("fixed_task_bindings", {}).items():
                        if task.get("uuid") in uuids:
                            cancelled_occurrences.add(rid)
                else:
                    cancelled_ids.update(refs)
                if day is not None:
                    cancelled_support.add(f"{day}:{str(task.get('description', '')).lower()}")
    requirements = [r for r in requirements if r.id not in cancelled_ids]
    fact_map = {str(r.get("id")): r for r in facts}
    for req in requirements:
        meta = (fact_map.get(req.id, {}).get("meta") or {})
        if not any(k in meta for k in ("est", "estimate", "min_est", "max_est")):
            diagnostics.append(Diagnostic("estimate-unconfirmed", BLOCKING,
                f"{req.title}: no recorded estimate; legacy default is not an approved quantity", [req.id]))
    fixed = sources.fixed_from_omn(facts, week_start, cfg, diagnostics)
    # The shared parser selects by start date. Recover intervals starting
    # before Monday by parsing them at their own origin, then translate their
    # exact endpoints into this grid's coordinate system.
    present = {f.id for f in fixed}
    week_begin = datetime.combine(week_start, datetime.min.time(), TZ)
    for record in facts:
        meta = record.get("meta") or {}
        if record.get("type") != "event" or meta.get("rrule") or not meta.get("start") or not meta.get("end"):
            continue
        try:
            begin, end = sources._aware(meta["start"]), sources._aware(meta["end"])
        except ValueError:
            continue  # shared parser already reports malformed facts
        if begin < week_begin < end:
            for f in sources.fixed_from_omn([record], begin.date(), cfg, diagnostics):
                shift = (begin.date() - week_start).days * 1440
                f.start += shift
                f.end += shift
                if f.id not in present:
                    fixed.append(f)
                    present.add(f.id)
    # A completed +fixed action still anchors its authoritative window.
    from .travel import migrated_bindings
    retired_travel = migrated_bindings(facts, tasks, week_start)
    fixed_tasks = [dict(t, status="pending") if t.get("status") == "completed"
                   and "fixed" in t.get("tags", []) else t for t in parsed_tasks
                   if t.get("uuid") not in retired_travel]
    fixed += sources.fixed_from_tasks(fixed_tasks, week_start, cfg, diagnostics)
    present = {f.id for f in fixed}
    for f in sources.fixed_from_tasks(fixed_tasks, week_start - timedelta(days=1), cfg, diagnostics):
        f.start -= 1440
        f.end -= 1440
        if f.id not in present and f.start < 7 * 1440 and f.end > 0:
            fixed.append(f)
            present.add(f.id)
    fixed, fixed_bindings, fixed_issues = reconcile_fixed(
        fixed, facts, week_start, cfg, diagnostics, tasks=parsed_tasks)
    fixed = [f for f in fixed if f.id not in cancelled_occurrences]
    fixed += sources.sleep_intervals(week_start, 6)
    sources.detect_fixed_collisions(fixed, week_start, diagnostics)
    reconciliation = sources.legacy_from_tasks(parsed_tasks, {r.id for r in requirements}, week_start,
                                      diagnostics, now=current,
                                      active_omn_ids=sources.active_omn_ids(omn))
    # Keep reconciliation evidence in a replayable test plan. The engine and
    # publication adapter fail closed; they never hide it behind a generic SAT.
    records = {str(r.get("id")): r for r in facts}
    colors, items, reservations, notes = {}, [], [], [
        f"{rid}: omitted after a previously pending action was intentionally removed"
        for rid in sorted(cancelled_ids)]
    from .travel import rules as travel_rules
    for req in requirements:
        meta = (records.get(req.id, {}).get("meta") or {})
        before, after, origin, mode = travel_rules(meta, req.location)
        semantic = str(meta.get("color") or meta.get("activity_type") or meta.get("topic") or req.topic)
        if not meta.get("color") and not meta.get("activity_type"):
            course = re.search(r"\b(CS|CE|MATH|ECS)[-\s]+(\d{4})", req.title, re.IGNORECASE)
            if req.title.lower().startswith(("email ", "reply ", "send email")):
                semantic = "email"
            elif not meta.get("topic") and course:
                semantic = course[1].lower() + "-" + course[2]
            elif not meta.get("topic") and semantic == req.id.split(":")[-1]:
                semantic = req.kind
        # Location/transport incompatibility is physical, not semantic. It is
        # never safe to paint one email run that implies two simultaneous venues.
        key = "work:" + json.dumps([semantic, req.location, req.transport], separators=(",", ":"))
        if meta.get("travel_time"):
            key += f":travel:{before}:{after}:{origin}:{mode}"
        minimum_minutes = req.minimum_minutes if req.minimum_minutes is not None else req.required_minutes
        if "min_est" in meta:
            declared_min = parse_est_minutes(meta["min_est"])
            if declared_min is None:
                raise ValueError(f"{req.id}: invalid min_est")
            minimum_minutes = max(0, declared_min - credit.get(req.id, 0))
        lower = max(0, ceil_slot(minimum_minutes))
        hard_max = "max_est" in meta
        maximum_minutes = parse_est_minutes(meta.get("max_est"))
        if hard_max and maximum_minutes is None:
            raise ValueError(f"{req.id}: invalid max_est")
        maximum_minutes = req.required_minutes if maximum_minutes is None else max(0, maximum_minutes - credit.get(req.id, 0))
        upper = maximum_minutes // STEP if hard_max else ceil_slot(maximum_minutes)
        if upper < lower:
            raise ValueError(f"{req.id}: empty quarter-hour amount range ({minimum_minutes}..{maximum_minutes}m)")
        if upper == 0:
            continue
        if minimum_minutes % STEP or maximum_minutes % STEP:
            notes.append(f"{req.id}: amount rounded {'inward' if hard_max else 'up'} to {lower}..{upper} quarter-hour cells")
        allowed_days = set(req.allowed_days if req.allowed_days is not None else range(7))
        if req.kind == "assignment" and not meta.get("weekend_allowed", False):
            allowed_days &= set(range(5))
        day_lo, day_hi = req.day_window or (work_start * 60, work_end * 60)
        windows = []
        start_minute = req.window_start
        if req.available:
            availability = sources._aware(req.available)
            exact_start = ((availability.date() - week_start).days * 1440 + availability.hour * 60
                           + availability.minute + (availability.second + availability.microsecond / 1_000_000) / 60)
            start_minute = max(start_minute, exact_start)
        for d in sorted(allowed_days):
            lo = max(prefix, math.ceil(max(start_minute, d * 1440 + max(day_lo, work_start * 60)) / STEP))
            hi = min(CELLS, min(req.window_end, d * 1440 + min(day_hi, work_end * 60)) // STEP)
            if lo < hi:
                windows.append((lo, hi))
        if meta.get("requires_open") and not meta.get("open_hours"):
            from scheduler.common import BLOCKING, Diagnostic
            diagnostics.append(Diagnostic("venue-hours-missing", BLOCKING,
                f"{req.title}: target-date venue hours have not been supplied", [req.id]))
        windows = intersect_windows(windows, opening_windows(meta, week_start))
        from .people import participant_windows
        windows = intersect_windows(windows, participant_windows(meta, facts))
        quota = daily_bounds(meta, req.id, week_start, tasks)
        if quota:
            for day, (day_min, day_max) in quota.items():
                if day_max == 0:
                    continue
                eligible_day = intersect_windows(windows, [(day * ROWS, (day + 1) * ROWS)])
                piece = min(4, day_max) if req.kind == "assignment" else 1
                items.append(Item(f"{req.id}@{week_start + timedelta(days=day)}", req.title, key,
                    day_min, day_max, tuple(eligible_day), req.indivisible or day_max <= 8,
                    piece, req.due_local, req.travel, req.id))
        else:
            min_piece = min(4, upper) if req.kind == "assignment" or upper > 8 else 1
            items.append(Item(req.id, req.title, key, lower, upper, tuple(windows),
                              req.indivisible or req.required_minutes <= 120, min_piece, req.due_local, req.travel))
        colors[key] = Color(key, "work", location=req.location, transport=mode if meta.get("travel_time") else req.transport,
                            topic=semantic, travel_before=before, travel_after=after, travel_origin=origin)
    for key, color in list(colors.items()):
        members = [i for i in items if i.color == key]
        minimum, maximum = sum(i.minimum for i in members), sum(i.maximum for i in members)
        windows = tuple(sorted({w for i in members for w in i.windows}))
        smallest_piece = min(max(1, i.minimum) if i.indivisible else i.min_piece for i in members)
        colors[key] = Color(key, "work", minimum, maximum, windows,
                            min_run=smallest_piece, max_run=96,
                            location=color.location, transport=color.transport, topic=color.topic,
                            prefer_maximum=any((records.get(i.reference or i.id, {}).get("meta") or {}).get("prefer_maximum", False)
                                               for i in members), travel_before=color.travel_before,
                            travel_after=color.travel_after, travel_origin=color.travel_origin)
    # Exact fixed intervals are prepainted; travel minima belong to colors.
    fixed_attendance = []
    for f in fixed:
        source_record = records.get(f.refs[0], {}) if f.refs else {}
        meta = source_record.get("meta") or {}
        explicit = any(name in meta for name in ("buffer_before", "buffer_after"))
        is_class = "class" in source_record.get("tags", [])
        role = "class" if is_class else "fixed"
        key = "sleep" if f.source == "sleep" else "fixed:" + (f.location or "unknown")
        before, after, origin, mode = (0, 0, "At home", "no-car") if f.source == "sleep" else travel_rules(meta, f.location, is_class=is_class)
        if explicit:
            key += f":buffers:{before * STEP}:{after * STEP}"
        if key in colors and (colors[key].travel_before, colors[key].travel_after, colors[key].travel_origin,
                              colors[key].transport) != (before, after, origin, mode):
            key += f":travel:{before}:{after}:{origin}:{mode}"
        if is_class and key in colors:
            from dataclasses import replace
            colors[key] = replace(colors[key], topic="class")
        colors.setdefault(key, Color(key, "sleep" if f.source == "sleep" else "fixed",
                                     location=f.location or "", topic=role,
                                     transport=mode, travel_before=before, travel_after=after, travel_origin=origin))
        reservations.append(Reservation(f.id, key, f.start + f.buffer_before,
            f.end - f.buffer_after, f.label, f.location,
            0, 0))
        if f.source == "omn-event" and f.refs:
            fixed_attendance.append({"reservation": f.id, "source": f.refs[0], "kind": role})
    # Direct transfers: walking home between two same-day campus commitments
    # wastes up to an hour per gap. Eligible pairs get a solver choice — a
    # direct venue-to-venue route, or the classic home detour when a home
    # support block (lunch, break) needs the gap.
    travel_transfers = []
    reservation_by_id = {r.id: r for r in reservations}
    source_by_reservation = {entry["reservation"]: entry["source"] for entry in fixed_attendance}
    omn_fixed = sorted((f for f in fixed if f.source == "omn-event" and f.location),
                       key=lambda f: (f.start, f.end))
    from scheduler.common import transit_minutes
    for a, b in zip(omn_fixed, omn_fixed[1:]):
        if a.start // 1440 != b.start // 1440:
            continue
        ra, rb = reservation_by_id[a.id], reservation_by_id[b.id]
        ca, cb = colors[ra.color], colors[rb.color]
        after_edge, before_edge = ceil_slot(ra.end_minute), rb.start_minute // 15
        if after_edge < prefix:
            continue  # elapsed outing: its travel is sealed history, not a choice
        direct = transit_minutes(a.location, b.location)
        slots = ceil_slot(direct)
        if (direct >= STEP and slots < before_edge - after_edge
                and slots < ca.travel_after + cb.travel_before):
            travel_transfers.append({"after_edge": after_edge, "before_edge": before_edge,
                "slots": slots, "from_color": ra.color, "to_color": rb.color,
                "from_location": a.location, "to_location": b.location,
                "to_label": b.label, "to_source": source_by_reservation.get(b.id),
                "mode": cb.transport})
    # Support colors repeat by day; per-day counts + one run of exact length
    # model the meal, not a named block with solver start/end variables.
    from .facts import away_spans
    from .policies import support_overrides
    support_rules = support_overrides(facts, week_start)
    away = away_spans(fixed)
    patterns = [("cook", "Cook breakfast", 4, (390, 450), "At home", None),
                ("breakfast", "Eat breakfast", 3, (450, 495), "At home", "support:cook"),
                ("lunch", "Eat lunch", 4, (660, 840), "At home", None),
                ("break", "Take afternoon break", 4, (840, 1080), "At home", None),
                ("dinner", "Eat dinner", 3, (1020, 1215), "At home", None)]
    for name, label, count, (lo, hi), location, follows in patterns:
        windows, daily = [], {}
        for d in range(7):
            # 08:30 class mornings use 06:15 cook + 07:15 breakfast.
            early = any(f.start == d * 1440 + 510 for f in fixed if f.source != "sleep")
            a, b = (375, 435) if early and name == "cook" else ((435, 480) if early and name == "breakfast" else (lo, hi))
            rule = support_rules.get((d, name), {})
            if rule.get("waived") or rule.get("skipped"):
                reason = "reported skipped" if rule.get("skipped") else "explicitly waived"
                notes.append(f"{label}/{d}: {reason} for this date only; not inferred completion")
                continue
            day_count = (parse_est_minutes(rule["duration"]) // STEP) if "duration" in rule else count
            if "hours" in rule:
                a, b = (hhmm_to_minutes(v) for v in rule["hours"].split("-"))
            start, end = max(prefix, d * ROWS + ceil_slot(a)), d * ROWS + b // STEP
            if end <= prefix:
                notes.append(f"{label}/{d}: elapsed window, not inferred completion")
                continue
            if f"{week_start + timedelta(days=d)}:{label.lower()}" in cancelled_support:
                notes.append(f"{label}/{d}: user removed the action; do not recreate")
                continue
            completed = any(t.get("status") == "completed" and task_date(t) == week_start + timedelta(days=d)
                            and str(t.get("description", "")).lower() == label.lower() for t in tasks)
            if completed:
                notes.append(f"{label}/{d}: user marked complete; do not recreate")
                continue
            # Multi-day away event owns meals inside its authoritative window.
            if any(min(end * STEP, b) - max(start * STEP, a) >= count * STEP for a, b in away):
                notes.append(f"{label}/{d}: within multi-day away event")
                continue
            windows.append((start, end))
            daily[d] = (day_count, count * 2 if name == "break" and "duration" not in rule else day_count)
        if windows:
            cooking_done = tuple(d for d in daily if
                f"{week_start + timedelta(days=d)}:cook breakfast" in cancelled_support
                or any(t.get("status") == "completed"
                    and task_date(t) == week_start + timedelta(days=d)
                    and str(t.get("description", "")).lower() == "cook breakfast" for t in tasks))
            colors["support:" + name] = Color("support:" + name, "support", sum(lo for lo, _hi in daily.values()),
                sum(hi for _lo, hi in daily.values()), tuple(windows), count,
                count * 2 if name == "break" else count, daily, location, "no-car", label, follows if follows in colors else None,
                daily_max_runs=1, same_start_daily=name == "dinner", prefer_maximum=name == "break",
                follows_exceptions=cooking_done if name == "breakfast" else (),
                travel_before=travel_rules({}, location)[0], travel_after=travel_rules({}, location)[1],
                same_start_exceptions=tuple(d for d in daily if support_rules.get((d, name), {}).get("independent_start")))
    colors[TRAVEL] = Color(TRAVEL, "travel", 0, CELLS, max_run=CELLS, location="", topic="Travel")
    # A historical-only color stays in the palette when its source disappears.
    old_grid = None
    if previous:
        if previous["candidate"].get("status") != "ok":
            raise ValueError("previous schedule must have a certified candidate")
        old_grid = previous["candidate"]["grid"]
        old_palette = {c["key"]: c for c in previous["problem"]["colors"]}
        for key in set(old_grid[:prefix]) - {"free"} - set(colors):
            old = old_palette[key]
            colors[key] = Color(key, old.get("kind", "unavailable"),
                                location=old.get("location", ""),
                                transport=old.get("transport", "no-car"),
                                topic=old.get("topic", ""))
    sealed_records = []
    if previous is None and prefix:
        from .history import seed_legacy_prefix
        history = Problem(week_start, list(colors.values()), items, reservations, prefix=prefix)
        try:
            seed_legacy_prefix(history, tasks)
            old_grid = history.previous
            colors = {c.key: c for c in history.colors}
            sealed_records = history.metadata.get("sealed_legacy_records", [])
        except ValueError as exc:
            from scheduler.common import BLOCKING, Diagnostic
            diagnostics.append(Diagnostic("historical-coloring-conflict", BLOCKING, str(exc)))
    gaps = {}  # travel-colored runs replace all live pairwise FREE-gap rules
    problem = Problem(week_start, list(colors.values()), items, reservations, gaps, prefix,
                      old_grid, "live", {"loaded_at": current.isoformat(),
                      "source_digest": digest(omn, tasks), "rounding_notes": notes,
                      "cancelled_ids": sorted(cancelled_ids),
                      "cancelled_support": sorted(cancelled_support),
                      "support_overrides": {f"{week_start + timedelta(days=d)}:{name}": value
                                            for (d, name), value in support_rules.items()},
                      "cancelled_occurrences": sorted(cancelled_occurrences),
                      "cancelled_travel_windows": sorted({tuple(w) for w in cancelled_travel_windows}),
                      "source_task_snapshot": task_snapshot(tasks, week_start),
                      "completed_credit_minutes": credit,
                      "fixed_task_bindings": fixed_bindings,
                      "retired_travel_bindings": retired_travel,
                      "fixed_reconciliation": fixed_issues,
                      "fixed_attendance": fixed_attendance,
                      "travel_transfers": travel_transfers,
                      "sealed_legacy_records": sealed_records,
                      "diagnostics": [d.to_dict() for d in diagnostics],
                      "reconciliation": [entry.to_dict() for entry in reconciliation],
                      "work_start": work_start, "work_end": work_end},
                      daily_max_work_runs={d: cfg.day_cap for d in range(7)},
                      groups=[Group("car-errands", tuple(c.key for c in colors.values()
                              if c.kind == "work" and c.transport == "car" and c.maximum),
                              max_runs_per_day=96, prefer_fewer_runs=True)]
                             if any(c.kind == "work" and c.transport == "car" and c.maximum
                                    for c in colors.values()) else [])
    problem.validate()
    return problem
