"""Dry-run-default publication of a certified grid. Never recolors or schedules.

Taskwarrior's transport wrapper is reused, not interval-v1's apply policy.
Only this week's suffix-owned blocks are replaced; fixed/completed/unmanaged
and sealed-prefix actions are never changed. Legacy adoption is opt-in.
"""
from datetime import datetime

from scheduler.apply import Taskwarrior, _verify, lint_week, sync_calendar
from scheduler.common import TZ, hhmm_to_minutes

from .decode import decode
from .schema import STEP, TRAVEL, Problem
from .verify import verify


def task_span(task, problem):
    scheduled = task.get("scheduled")
    if not scheduled or not task.get("starttime") or not task.get("endtime"):
        return None
    from .adapter import task_date
    day = task_date(task)
    if day is None:
        return None
    offset = (day - problem.week_start).days * 1440
    a, b = hhmm_to_minutes(task["starttime"]), hhmm_to_minutes(task["endtime"])
    if b <= a:
        b += 1440
    return offset + a, offset + b


def apply(problem: Problem, candidate: dict, records: list[dict], *, confirmed=False,
          replace_legacy=False, replace_carried=False, replace_travel=False,
          taskwarrior=None, now=None, post_publish=True) -> dict:
    errors = verify(problem, candidate)
    if candidate.get("status") != "ok":
        errors.append("candidate is not certified feasible")
    if not errors and records != decode(problem, candidate):
        errors.append("records do not match certified grid/layout")
    current = (now or datetime.now(TZ)).astimezone(TZ)
    if problem.source == "live":
        elapsed = ((current.date() - problem.week_start).days * 1440 + current.hour * 60 + current.minute
                   + (current.second + current.microsecond / 1_000_000) / 60)
        from datetime import date
        if (any(r["start"] * STEP < elapsed for r in candidate.get("runs", []))
                or any((date.fromisoformat(r["scheduled"]) - problem.week_start).days * 1440
                       + hhmm_to_minutes(r["starttime"]) < elapsed for r in records)):
            errors.append("plan starts in elapsed time; replan the suffix")
    if errors:
        return {"refused": errors, "dry_run": not confirmed}
    # The CLI checks these too, but direct callers must not bypass production
    # publication safety. An injected transport is an explicit test seam.
    if taskwarrior is None:
        if confirmed and problem.source != "live":
            return {"refused": ["spec plans are dry-run only; publish a fresh live plan"],
                    "dry_run": False}
        if problem.source == "live":
            from scheduler.sources import read_omn_export, read_task_export

            from .adapter import digest
            if digest(read_omn_export(), read_task_export()) != problem.metadata.get("source_digest"):
                return {"refused": ["source state changed; replan before applying"],
                        "dry_run": not confirmed}
    tw = taskwarrior or Taskwarrior()
    tasks = tw.export()
    owned, protected = [], []
    import re
    represented = {item.reference or item.id for item in problem.items}
    fixed_sources = {event["source"] for event in problem.metadata.get("fixed_attendance", [])}
    travel_refs = set().union(*(set(re.findall(r"\[omn:([^\]]+)\]", str(r.get("todo", ""))))
                               for r in records if "travel" in r.get("tags", [])))
    for task in tasks:
        tags = set(task.get("tags") or [])
        span = task_span(task, problem)
        in_suffix = (span is not None and span[0] >= problem.prefix * STEP
                     and span[1] <= 7 * 1440 and span[0] >= 0)
        ownership = ("grid-" + problem.week_start.isoformat() in tags or
                     (replace_legacy and "composer" in tags))
        refs = set(re.findall(r"\[omn:([^\]]+)\]", str(task.get("todo") or "")))
        allowed_refs = represented | fixed_sources if "travel" in tags else represented
        covered = (bool(refs) and refs <= allowed_refs) or (not refs and "schedule" in tags)
        # Explicit carry-forward retires superseded pending plans, not actual
        # history. The grid prefix remains sealed; completed/fixed/unmanaged
        # actions and unresolved identities remain protected.
        carried = (replace_carried and span is not None
                   and 0 <= span[0] < span[1] <= 7 * 1440)
        migration = problem.metadata.get("retired_travel_bindings", {}).get(task.get("uuid"), {})
        span_cells = range(span[0] // STEP, span[1] // STEP) if span is not None else ()
        # Sub-hour travel is reserved on the grid but deliberately not its own
        # item, so a retired alias can bind to painted cells alone; hour-plus
        # travel still requires the fresh record to exist.
        travel_owned = (replace_travel and in_suffix and "fixed" in tags
                        and tuple(migration.get("span", [])) == span
                        and (migration.get("event") in travel_refs
                             or all(candidate["grid"][i] == TRAVEL for i in span_cells)))
        ordinary_owned = "fixed" not in tags and ownership and (in_suffix or carried) and covered
        if task.get("status") == "pending" and "managed" in tags and (travel_owned or ordinary_owned):
            owned.append(task)
        else:
            protected.append(task)
    for task in protected:
        if task.get("status") not in {"pending", "completed"}:
            continue
        span = task_span(task, problem)
        if span is None:
            continue
        # Runs omit constant-colored fixed reservations. Check both grid work
        # and exact attendance records: publishing a new fixed registration
        # must not overwrite or double-book an unrelated protected task.
        windows = [(run['start'] * STEP, run['end'] * STEP)
                   for run in candidate.get('runs', [])]
        windows += [r_span for record in records if (r_span := task_span(record, problem)) is not None]
        if any(span[0] < end and start < span[1] for start, end in windows):
            return {"refused": [f"new block overlaps protected task {task.get('uuid')}"],
                    "dry_run": not confirmed}
    report = {"dry_run": not confirmed, "created": [], "deleted": [],
              "protected": [t.get("uuid") for t in protected],
              "commands": [tw.add_command(r) for r in records] +
                          [tw.delete_command(t["uuid"]) for t in owned]}
    if problem.source == "history":
        raise ValueError("historical certificates cannot be published")
    if not confirmed:
        return report
    try:
        for record in records:
            report["created"].append({"uuid": tw.add(record), "record": record})
        report["verification"] = _verify(tw, report["created"])
        # The reusable legacy round-trip check omits due. Verify it here too.
        from datetime import timezone
        exported = {t["uuid"]: t for t in tw.export()}
        def normalized_due(value):
            if not value:
                return None
            import re
            if re.fullmatch(r"\d{8}T\d{6}Z", str(value)):
                return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return (parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)).astimezone(timezone.utc)
        for item, result in zip(report["created"], report["verification"]):
            if normalized_due(exported.get(item["uuid"], {}).get("due")) != normalized_due(item["record"].get("due")):
                result["ok"] = False
                result.setdefault("mismatches", []).append("due")
        if not all(v["ok"] for v in report["verification"]):
            raise RuntimeError("Taskwarrior round-trip verification failed")
    except Exception as exc:  # noqa: BLE001 - rollback on any failed transaction step
        report["error"] = str(exc)
        report["rollback_errors"] = []
        for item in reversed(report["created"]):
            try:
                tw.delete(item["uuid"])
            except Exception as rollback:  # noqa: BLE001 - record every rollback failure
                report["rollback_errors"].append(str(rollback))
        return report
    try:
        for task in owned:
            tw.delete(task["uuid"])
            report["deleted"].append(task["uuid"])
    except Exception as exc:  # noqa: BLE001 - report partial mutation rather than claim success
        report["error"] = f"new blocks created; old deletion failed: {exc}; inspect duplicates"
        return report
    report["applied"] = True
    if post_publish:
        for key, callback in (("lint", lambda: lint_week(problem.week_start.isoformat())),
                              ("calendar", sync_calendar)):
            try:
                report[key] = callback()
            except Exception as exc:  # noqa: BLE001 - publication failure must not hide the schedule
                report[key] = {"error": str(exc)}
    return report
