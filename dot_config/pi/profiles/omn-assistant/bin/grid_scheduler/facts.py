"""Pure source normalization and identity-based fixed-event reconciliation.

No source writes and no solver calls. Cancellations/one-week overrides affect
only this compilation, never the stored recurrence default.
"""
import re
from copy import deepcopy
from dataclasses import replace

from scheduler import sources
from scheduler.common import BLOCKING, Diagnostic


def week_records(records, week_start):
    result = deepcopy(records)
    for record in result:
        meta = record.setdefault("meta", {})
        overrides = meta.get("week_overrides", {})
        if not isinstance(overrides, dict):
            raise TypeError(f"{record.get('id')}: week_overrides must be an object")
        override = overrides.get(week_start.isoformat(), {})
        if not isinstance(override, dict):
            raise TypeError(f"{record.get('id')}: week override must be an object")
        meta.update(override)
        if record.get("type") != "task":
            continue
        target = meta.get("target_week")
        if target and "/" not in str(target):
            start = sources.date.fromisoformat(str(target)[:10])
            start -= sources.timedelta(days=start.weekday())
            meta["target_week"] = f"{start}/{start + sources.timedelta(days=6)}"
        span = sources._target_week_span(record)
        if span and not (span[0] <= week_start + sources.timedelta(days=6) and week_start <= span[1]):
            # An explicitly deferred recurring action isn't work for this week.
            meta["active"] = False
            continue
        if meta.get("rrule") and meta.get("cancelled"):
            start = sources._aware(meta.get("start") or f"{week_start}T00:00:00")
            days = sources.rrule_mod.expand_weekly(meta["rrule"], start, week_start,
                                                  week_start + sources.timedelta(days=6))
            cancelled = ({d.isoformat() for d in days} if meta["cancelled"] is True
                         else sources._cancelled_dates(meta["cancelled"]))
            remaining = [d for d in days if d.isoformat() not in cancelled]
            if days and not remaining:
                meta["active"] = False
            elif remaining:
                meta["days"] = sorted({d.weekday() for d in remaining})
    # Explicitly linked in-class assessments consume their fixed occurrence,
    # not another flexible preparation quantity. This is not completion credit.
    by_id = {r["id"]: r for r in result}
    for record in result:
        meta = record.get("meta") or {}
        event_id = meta.get("in_class_assessment_for")
        if record.get("type") != "task" or not event_id:
            continue
        event = by_id.get(event_id)
        if not event or event.get("type") != "event" or sources.is_inactive(event)[0]:
            raise ValueError(f"{record['id']}: assessment must reference an active fixed event")
        event_meta = event.get("meta") or {}
        if event_meta.get("rrule") or event_meta.get("cancelled"):
            raise ValueError(f"{record['id']}: assessment requires a specific uncancelled occurrence")
        if sources._aware(meta.get("due")) != sources._aware(event_meta.get("end")):
            raise ValueError(f"{record['id']}: assessment deadline differs from fixed event end")
        if sources._aware(event_meta.get("start")) >= sources._aware(event_meta.get("end")):
            raise ValueError(f"{record['id']}: assessment event has no positive interval")
        meta["active"] = False
        meta["planning_coverage"] = {"fixed_event": event_id, "not_completion": True}
    # Feed refreshes can omit local `attending` fields. A stored user-authored
    # arrival note explicitly saying "joining <event>" and a matching return
    # anchor are independent durable attendance evidence, not a registration
    # guess. Compile the one-week window from those facts without store writes.
    def token(text):
        return re.sub(r"[^a-z0-9]", "", str(text).lower())
    for record in result:
        meta = record.get("meta") or {}
        if (record.get("type") != "event" or meta.get("source") != "mlh"
                or "attending" in meta or "attending" in record.get("tags", [])
                or sources.is_inactive(record)[0]):
            continue
        name = token(record.get("title"))
        trips = [r for r in result if r.get("type") == "event"
                 and "travel" in r.get("tags", []) and not sources.is_inactive(r)[0]
                 and name and name in token(str(r.get("title")) + str(r.get("meta")))]
        arrivals = [r for r in trips if re.search(r"arrival\s*=\s*joining", (r.get("meta") or {}).get("note", ""), re.IGNORECASE)]
        departures = [r for r in trips if "depart immediately" in str(r.get("meta", {})).lower()]
        if len(arrivals) != 1 or len(departures) != 1:
            continue
        start = max(sources._aware(meta["start"]), sources._aware(arrivals[0]["meta"]["end"]))
        end = min(sources._aware(meta["end"]), sources._aware(departures[0]["meta"]["start"]))
        if start < end and start.date() <= week_start + sources.timedelta(days=6) and end.date() >= week_start:
            meta.update(attending=True, start=start.isoformat(), end=end.isoformat(),
                        derived_attendance=[arrivals[0]["id"], departures[0]["id"]])
    return result


def identity(label):
    """Conservative registration alias: action verb/plural/weekly decoration."""
    text = re.sub(r"\s+\([^)]*\)\s*$", "", str(label).lower())
    words = re.findall(r"[a-z0-9]+", text)
    stop = {"attend", "buy", "do", "weekly", "run"}
    return tuple(w[:-3] + "y" if w.endswith("ies") else w
                 for w in words if w not in stop)


def reconcile_fixed(fixed, records, week_start, config, diagnostics, tasks=()):
    """Deduplicate by identity, not containment; retain cancellations as issues."""
    # Canonical day segments are exact registrations, not arbitrary contained
    # tasks. One multi-day occurrence can already have separate Taskwarrior
    # rows for each day; match each without duplicating the entire event.
    segmented = []
    for f in fixed:
        begin, finish = f.start + f.buffer_before, f.end - f.buffer_after
        if f.source != "omn-event" or finish <= begin or begin // 1440 == (finish - 1) // 1440:
            segmented.append(f)
            continue
        cursor = begin
        while cursor < finish:
            end = min(finish, (cursor // 1440 + 1) * 1440)
            if end > 0 and cursor < 7 * 1440:
                # Preserve out-of-week continuation edges so travel does not
                # invent a fresh Monday arrival or Sunday-night departure.
                part_begin = begin if cursor == 0 and begin < 0 else cursor
                part_end = finish if end == 7 * 1440 and finish > end else end
                before = f.buffer_before if part_begin == begin else 0
                after = f.buffer_after if part_end == finish else 0
                stamp = (week_start + sources.timedelta(days=max(0, cursor // 1440))).isoformat()
                segmented.append(replace(f, id=f.id.rsplit("@", 1)[0] + "@" + stamp,
                                         start=part_begin - before, end=part_end + after,
                                         buffer_before=before, buffer_after=after))
            cursor = end
    fixed = segmented
    authoritative = [f for f in fixed if f.source == "omn-event"]
    cancelled = []
    for record in records:
        meta = record.get("meta") or {}
        if record.get("type") != "event" or not meta.get("cancelled"):
            continue
        copy = deepcopy(record)
        copy["meta"].pop("cancelled", None)
        expanded = sources.fixed_from_omn([copy], week_start, config, [])
        dates = set() if meta["cancelled"] is True else sources._cancelled_dates(meta["cancelled"]) 
        cancelled.extend(f for f in expanded if meta["cancelled"] is True
                         or f.id.rsplit("@", 1)[-1] in dates)
    task_references = {t.get("uuid"): set(sources._todo_refs(t)) for t in tasks}
    output, bindings, issues = [], {}, []
    for f in fixed:
        if f.source != "task-fixed":
            output.append(f)
            continue
        def matches(event, f=f):
            source_ids = {ref.rsplit("@", 1)[0] for ref in event.refs}
            same_identity = bool(task_references.get(f.id.removeprefix("task:"), set()) & source_ids) or identity(f.label) == identity(event.label)
            return (same_identity
                    and f.start == max(0, event.start + event.buffer_before)
                    and f.end == min(7 * 1440, event.end - event.buffer_after))
        removed = next((event for event in cancelled if matches(event)), None)
        if removed:
            message = f"cancelled occurrence still has pending fixed registration: {f.label} ({f.id})"
            diagnostics.append(Diagnostic("cancelled-fixed-registration", BLOCKING, message, f.refs))
            issues.append({"kind": "cancelled", "task": f.id.removeprefix("task:"),
                           "source": removed.id, "message": message})
            continue
        event = next((event for event in authoritative if matches(event)), None)
        if event:
            bindings.setdefault(event.id, []).append(f.id.removeprefix("task:"))
            if f.location != event.location:
                message = f"fixed registration location differs from source: {f.label}: {f.location!r} -> {event.location!r}"
                diagnostics.append(Diagnostic("fixed-location-mismatch", BLOCKING, message, f.refs + event.refs))
                issues.append({"kind": "location", "task": f.id.removeprefix("task:"),
                               "source": event.id, "message": message})
            continue
        # An unrelated commitment nested inside an event isn't its registration.
        output.append(f)
    return output, bindings, issues


def away_spans(fixed):
    """Merge adjacent day segments of one identity, not recurring-day gaps."""
    groups = {}
    for f in fixed:
        key = (tuple(f.refs) or (f.id,), f.location, identity(f.label))
        groups.setdefault(key, []).append((f.start + f.buffer_before, f.end - f.buffer_after))
    result = []
    for windows in groups.values():
        merged = []
        for a, b in sorted(windows):
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        result.extend((a, b) for a, b in merged if b - a >= 1440)
    return result


def attendance_records(problem):
    """Materialize exact, unregistered authoritative occurrences outside Z3."""
    from .decode import clock
    from .schema import STEP
    by_id = {r.id: r for r in problem.reservations}
    palette = {c.key: c for c in problem.colors}
    bindings = problem.metadata.get("fixed_task_bindings", {})
    output = []
    for event in problem.metadata.get("fixed_attendance", []):
        r = by_id[event["reservation"]]
        if bindings.get(r.id) or r.start_minute < problem.prefix * STEP:
            continue
        # Cross-day/overnight events become exact day segments, with shared
        # source identity; never round their actual clock endpoints to a grid.
        start = max(0, r.start_minute)
        end = min(7 * 1440, r.end_minute)
        while start < end:
            day = start // 1440
            finish = min(end, (day + 1) * 1440)
            color = palette[r.color]
            tags = ["managed", "fixed", "grid", "grid-" + problem.week_start.isoformat()]
            if event.get("kind") == "class":
                tags.append("class")
            output.append({"description": "Attend " + r.label,
                "scheduled": (problem.week_start + sources.timedelta(days=day)).isoformat(),
                "starttime": clock(start % 1440), "endtime": clock(finish % 1440),
                "est": f"{finish-start}m", "location": r.location or color.location,
                "transport": color.transport, "todo": "- Attend " + r.label +
                    " [omn:" + event["source"] + "]",
                "tags": tags})
            start = finish
    return output
