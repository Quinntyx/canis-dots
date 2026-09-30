"""Apply a selected candidate to Taskwarrior, then lint and sync.

Safety model:

* dry-run is the default; a real apply needs an explicit candidate selection
  and a confirmation flag supplied by the CLI;
* apply refuses outright when any blocking diagnostic exists, a fixed-fixed
  collision is present, the optimization status is unknown, or an unmatched
  legacy managed task cannot be reconciled;
* existing tasks are identified by UUID (never the mutable numeric id);
* unmanaged and ``+fixed`` tasks are never touched;
* only solver-owned managed blocks are replaced — ``+composer`` tasks plus
  reconciled legacy blocks scheduled inside the week whose omni refs are all in
  this plan;
* a failed Google Calendar sync is reported, never treated as a rollback of
  the Taskwarrior writes.
"""

from __future__ import annotations

import itertools
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from .common import (
    MIN_ALLOC_MINUTES,
    MINUTES_PER_DAY,
    WeekInput,
    hhmm_to_minutes,
    transit_minutes,
)

UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
TODO_REF = re.compile(r"\[omn:([^\]\s]+)\]")
REFUSAL_TAGS = {"fixed-collision", "missing-estimate", "ambiguous-estimate",
                "fixed-missing-time", "unsupported-rrule",
                "legacy-managed-unmatched", "overdue-requirement"}


def _default_runner(argv):
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


class Taskwarrior:
    """Thin, injectable wrapper around the ``task`` CLI."""

    def __init__(self, runner=_default_runner, task_bin: str = "task"):
        self._runner = runner
        self._bin = task_bin

    def export(self) -> list:
        code, out, err = self._runner(
            [self._bin, "rc.verbose=nothing", "status.not:deleted", "export"])
        if code != 0:
            raise RuntimeError(f"task export failed: {err.strip()}")
        return json.loads(out or "[]")

    def delete_command(self, uuid: str) -> list:
        return [self._bin, "rc.confirmation=off", "rc.verbose=nothing",
                uuid, "delete"]

    def delete(self, uuid: str) -> None:
        code, _out, err = self._runner(self.delete_command(uuid))
        if code != 0:
            raise RuntimeError(f"task delete {uuid} failed: {err.strip()}")

    def modify_command(self, uuid: str, updates: dict) -> list:
        command = [self._bin, "rc.confirmation=off", "rc.verbose=nothing",
                   uuid, "modify"]
        for key, value in updates.items():
            command.append(f"{key}:{value}")
        return command

    def modify(self, uuid: str, updates: dict) -> None:
        code, _out, err = self._runner(self.modify_command(uuid, updates))
        if code != 0:
            raise RuntimeError(f"task modify {uuid} failed: {err.strip()}")

    def add_command(self, record: dict) -> list:
        command = [self._bin, "rc.confirmation=off", "rc.verbose=new-uuid",
                   "add", record["description"]]
        command.append(f"scheduled:{record['scheduled']}")
        for key in ("starttime", "endtime", "location", "transport", "travel",
                    "est", "due"):
            if record.get(key):
                command.append(f"{key}:{record[key]}")
        if record.get("todo"):
            command.append("todo:" + record["todo"])
        for tag in record.get("tags", []):
            command.append(f"+{tag}")
        return command

    def add(self, record: dict) -> str:
        code, out, err = self._runner(self.add_command(record))
        if code != 0:
            raise RuntimeError(f"task add failed: {err.strip()}")
        # `task rc.verbose=new-uuid add` prints "Created task <uuid>." — search
        # for the uuid anywhere in the output rather than matching the whole
        # line. A wrong capture here can alias two same-description blocks
        # (e.g. two pieces of one assignment on one day), so never fall back
        # to export-matching while freshly created tasks are still pending.
        match = UUID_RE.search(out)
        if match:
            return match.group(0)
        raise RuntimeError(f"could not determine uuid of created task: {out!r}")


@dataclass
class ApplyReport:
    applied: bool = False
    refused: str | None = None
    dry_run: bool = False
    deleted: list = field(default_factory=list)
    created: list = field(default_factory=list)
    deferred: list = field(default_factory=list)
    protected: list = field(default_factory=list)
    verification: list = field(default_factory=list)
    commands: list = field(default_factory=list)
    lint: dict | None = None
    gcal: dict | None = None
    notes: list = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "applied": self.applied,
            "refused": self.refused,
            "dry_run": self.dry_run,
            "deleted": self.deleted,
            "created": self.created,
            "deferred": self.deferred,
            "protected": self.protected,
            "verification": self.verification,
            "commands": self.commands,
            "lint": self.lint,
            "gcal": self.gcal,
            "notes": self.notes,
            "error": self.error,
        }


def _scheduled_date(task: dict) -> str | None:
    value = task.get("scheduled")
    if not value:
        return None
    text = str(value)
    if "T" in text:
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    return text[:10]


def _todo_refs(task: dict) -> list:
    return TODO_REF.findall(task.get("todo") or "")


def _candidate_validation_error(week: WeekInput, candidate: dict) -> str | None:
    requirements = {item.id: item for item in week.requirements}
    blocks = candidate.get("blocks")
    records = candidate.get("records")
    if not isinstance(blocks, list) or not isinstance(records, list):
        return "candidate is missing decoded blocks or Taskwarrior records"
    if len(blocks) != len(records):
        return "candidate block/record counts differ"

    totals = {rid: 0 for rid in requirements}
    spans = []
    day_counts = {}
    for block, record in zip(blocks, records, strict=True):
        try:
            start = int(block["start_minute"])
            duration = int(block["duration_minutes"])
            allocations = block["allocations"]
            group = block["group"]
        except (KeyError, TypeError, ValueError):
            return "candidate contains a malformed decoded block"
        if duration < week.min_block or duration > week.max_block:
            return "candidate contains an out-of-range block duration"
        day = start // MINUTES_PER_DAY
        minute = start % MINUTES_PER_DAY
        if not (0 <= day <= 6):
            return "candidate contains a block outside the selected week"
        if (minute < week.work_start_hour * 60
                or minute + duration > week.work_end_hour * 60):
            return "candidate contains a block outside flexible work hours"
        day_counts[day] = day_counts.get(day, 0) + 1
        refs = set()
        allocated = 0
        for allocation in allocations:
            rid = str(allocation.get("omn_id"))
            minutes = int(allocation.get("minutes", 0))
            requirement = requirements.get(rid)
            if requirement is None or minutes <= 0:
                return f"candidate contains an invalid allocation for {rid}"
            if not (requirement.window_start <= start
                    and start + duration <= requirement.window_end):
                return f"candidate block violates the window for {rid}"
            if list(requirement.group_key[:2]) != list(group[:2]):
                return f"candidate block violates cohesion for {rid}"
            block_transport = block.get("transport", record.get("transport"))
            if requirement.transport != block_transport:
                return f"candidate block violates transport cohesion for {rid}"
            totals[rid] += minutes
            allocated += minutes
            refs.add(rid)
        if allocated > duration:
            return "candidate allocations exceed a block duration"
        if set(_todo_refs(record)) != refs:
            return "candidate todo refs do not match its decoded allocations"
        if record.get("transport") not in {"car", "no-car"}:
            return "candidate record has no valid transport mode"
        expected_day = (week.week_start + timedelta(days=day)).isoformat()
        try:
            record_start = hhmm_to_minutes(record.get("starttime"))
            record_end = hhmm_to_minutes(record.get("endtime"))
        except ValueError:
            return "candidate record has an invalid time window"
        if record_end == 0:
            record_end = MINUTES_PER_DAY
        if (record.get("scheduled") != expected_day or record_start != minute
                or record_end - record_start != duration):
            return "candidate record does not match its decoded block"
        tags = {str(tag).lower() for tag in record.get("tags", [])}
        if not {"managed", "composer"} <= tags:
            return "candidate record is not solver-owned"
        spans.append((start, start + duration, str(group[1]) if len(group) > 1 else None))

    if len(blocks) > week.max_blocks:
        return "candidate exceeds the weekly block cap"
    if any(count > week.day_cap for count in day_counts.values()):
        return "candidate exceeds a daily block cap"
    for rid, requirement in requirements.items():
        # The hard contract is the minimum (meta.min_est); the full est is the
        # target whose shortfall shows up as the candidate's stretch bucket.
        minimum = (requirement.minimum_minutes
                   if requirement.minimum_minutes is not None
                   else requirement.required_minutes)
        need = max(min(minimum, requirement.required_minutes), MIN_ALLOC_MINUTES)
        if totals[rid] < need:
            return (f"candidate coverage for {rid} is {totals[rid]}m, "
                    f"expected at least {need}m")
    spans.sort()
    for first, second in itertools.pairwise(spans):
        gap = transit_minutes(first[2], second[2])
        if first[1] + gap > second[0]:
            return "candidate blocks overlap or omit their transit gap"
    for start, end, location in spans:
        for fixed in week.fixed_intervals:
            transit = transit_minutes(location, fixed.location) if fixed.location else 0
            before = max(0, transit - fixed.buffer_before)
            after = max(0, transit - fixed.buffer_after)
            if not (end + before <= fixed.start or fixed.end + after <= start):
                return f"candidate overlaps fixed interval {fixed.id}"
    return None


def _validate_supports(week: WeekInput, supports: list) -> str | None:
    by_id = {item.id: item for item in week.supports}
    spans = []
    for support in supports:
        spec = by_id.get(support.get("id"))
        if spec is None:
            return "candidate places an unknown support window"
        try:
            start, duration = int(support["start"]), int(support["duration"])
        except (KeyError, TypeError, ValueError):
            return "candidate contains a malformed support placement"
        if not (spec.dur_min <= duration <= spec.dur_max):
            return "candidate support duration is out of bounds"
        if not (spec.earliest <= start and start + duration <= spec.latest):
            return "candidate support sits outside its window"
        spans.append((start, start + duration,
                      support.get("location"), spec.after, spec.id))
    spans.sort()
    for first, second in itertools.pairwise(spans):
        gap = transit_minutes(first[2], second[2])
        if first[1] + gap > second[0]:
            return "candidate supports overlap or omit their transit gap"
    for start, _end, _location, after, _sid in spans:
        if not after:
            continue
        predecessor = next((item for item in spans
                            if f":{after}:" in item[4]), None)
        if predecessor is None or predecessor[1] > start:
            return "candidate support violates its ordering dependency"
    return None


def refuse_reason(week: WeekInput, candidate: dict) -> str | None:
    blocking = week.blocking()
    for diagnostic in blocking:
        if diagnostic.tag in REFUSAL_TAGS or diagnostic.blocking:
            return (f"refusing to apply: blocking diagnostic "
                    f"[{diagnostic.tag}] {diagnostic.message}")
    if candidate.get("status") != "ok":
        return f"refusing to apply: candidate status is {candidate.get('status')}"
    # An approximate candidate still satisfies every hard constraint; only its
    # soft tuning is incomplete. It is pickable, and `show` labels it
    # (APPROXIMATE) so the choice is informed. An UNKNOWN status is a real
    # refusal: hard feasibility itself is unproven.
    validation_error = _candidate_validation_error(week, candidate)
    if validation_error:
        return f"refusing to apply: {validation_error}"
    support_error = _validate_supports(week, candidate.get("supports", []))
    if support_error:
        return f"refusing to apply: {support_error}"
    return None


def apply_candidate(
    week: WeekInput,
    candidate: dict,
    *,
    taskwarrior: Taskwarrior | None = None,
    dry_run: bool = True,
    confirmed: bool = False,
    lint_runner=_default_runner,
    gcal_runner=_default_runner,
    run_lint: bool = True,
    run_gcal: bool = True,
) -> ApplyReport:
    taskwarrior = taskwarrior or Taskwarrior()
    report = ApplyReport(dry_run=dry_run)

    reason = refuse_reason(week, candidate)
    if reason:
        report.refused = reason
        return report
    if not dry_run and not confirmed:
        report.refused = "refusing to apply: --yes confirmation flag is required"
        return report

    week_start = week.week_start.isoformat()
    plan_ids = {requirement.id for requirement in week.requirements}

    try:
        export = taskwarrior.export()
    except Exception as exc:  # noqa: BLE001 - surfaced as a report field
        report.error = str(exc)
        return report

    owned, deferred, stale_support, protected = _classify_owned(export, plan_ids, week)
    defer_date = (week.week_start + timedelta(days=7)).isoformat()
    created_records = (list(candidate.get("support_records", []))
                       + list(candidate.get("records", [])))
    for record in created_records:
        report.commands.append(" ".join(taskwarrior.add_command(record)))
    for task in owned + stale_support:
        report.commands.append(" ".join(taskwarrior.delete_command(task["uuid"])))
    for task in deferred:
        report.commands.append(" ".join(taskwarrior.modify_command(
            task["uuid"], {"scheduled": defer_date, "starttime": "", "endtime": ""})))

    if dry_run:
        report.deleted = [task["uuid"] for task in owned + stale_support]
        report.deferred = [{
            "uuid": task["uuid"],
            "description": task.get("description"),
            "scheduled": defer_date,
        } for task in deferred]
        report.protected = [task["uuid"] for task in protected]
        report.notes.append(
            "dry-run: no Taskwarrior changes made; rerun this apply command with --yes")
        return report

    try:
        # Create and verify the replacement before deleting any existing work.
        # A partial add can be rolled back; deleting first cannot be undone.
        for record in created_records:
            uuid = taskwarrior.add(record)
            report.created.append({"uuid": uuid, "record": record})
        report.verification = _verify(taskwarrior, report.created)
        if not all(item.get("ok") for item in report.verification):
            raise RuntimeError("created Taskwarrior blocks failed re-export verification")
    except Exception as exc:  # noqa: BLE001
        for item in reversed(report.created):
            try:
                taskwarrior.delete(item["uuid"])
            except Exception as rollback_exc:  # noqa: BLE001
                report.notes.append(f"rollback failed for {item['uuid']}: {rollback_exc}")
        report.error = str(exc)
        return report

    try:
        for task in owned + stale_support:
            taskwarrior.delete(task["uuid"])
    except Exception as exc:  # noqa: BLE001
        report.error = (f"replacement blocks were created, but an old block could not "
                        f"be deleted: {exc}")
        report.notes.append("old work was preserved; inspect duplicates before retrying")
        return report

    for task in deferred:
        try:
            taskwarrior.modify(task["uuid"], {
                "scheduled": defer_date, "starttime": "", "endtime": ""})
        except Exception as exc:  # noqa: BLE001
            report.notes.append(
                f"defer failed for {task['uuid']}: {exc} — the carried block "
                "keeps its old date and stays pending")
            continue
        report.deferred.append({
            "uuid": task["uuid"],
            "description": task.get("description"),
            "scheduled": defer_date,
        })
    if deferred and len(report.deferred) == len(deferred):
        report.notes.append(
            f"deferred {len(deferred)} carried block(s) to {defer_date}; the next "
            "week's plan picks them up")

    report.deleted = [task["uuid"] for task in owned + stale_support]
    report.protected = [task["uuid"] for task in protected]
    report.applied = True

    if run_lint:
        try:
            report.lint = lint_week(week_start, lint_runner)
        except Exception as exc:  # noqa: BLE001
            report.lint = {"error": str(exc)}
    if run_gcal:
        try:
            report.gcal = sync_calendar(gcal_runner)
        except Exception as exc:  # noqa: BLE001
            report.gcal = {"error": str(exc)}
        if report.gcal and report.gcal.get("returncode") not in (0, None):
            report.notes.append(
                "calendar sync failed; Taskwarrior changes are kept "
                "(a failed sync is not a rollback)")
    return report


def _classify_owned(export: list, plan_ids: set, week: WeekInput):
    """Split pending managed tasks into apply actions.

    owned:   this week's solver-owned blocks, replaced by the new plan.
    deferred: carried blocks whose omn refs exist but are not required this
             week — rescheduled to next Monday, never deleted.
    stale_support: ``+schedule`` blocks with no omn refs — scaffolding the
             plan recreates, deleted wholesale.
    protected: everything else (unmanaged, +fixed, other weeks).
    """
    owned, deferred, stale_support, protected = [], [], [], []
    legacy_by_uuid = {item.uuid: item for item in week.legacy}
    week_end = (week.week_start + timedelta(days=6)).isoformat()
    for task in export:
        if task.get("status") != "pending":
            continue
        tags = {str(tag).lower() for tag in (task.get("tags") or [])}
        if "managed" not in tags or "fixed" in tags:
            protected.append(task)
            continue
        refs = _todo_refs(task)
        scheduled = _scheduled_date(task)
        in_week = (scheduled is not None and scheduled <= week_end)
        if not in_week:
            # Blocks scheduled beyond this week belong to another plan. Older
            # carried blocks stay in scope: they are owned, deferred, or
            # refused, exactly like in-week blocks.
            protected.append(task)
            continue
        # +composer denotes ownership, not global scope: applying one week
        # must never delete composer blocks belonging to another week.
        if "composer" in tags or (refs and all(ref in plan_ids for ref in refs)):
            owned.append(task)
            continue
        entry = legacy_by_uuid.get(str(task.get("uuid")))
        if entry is not None and entry.refs_resolvable:
            deferred.append(task)
            continue
        if not refs and "schedule" in tags:
            stale_support.append(task)
            continue
        # Unmatched carried work: the sources emitted the blocking
        # diagnostic; refuse_reason() stops the apply before any write.
        protected.append(task)
    return owned, deferred, stale_support, protected


def _verify(taskwarrior: Taskwarrior, created: list) -> list:
    export = taskwarrior.export()
    by_uuid = {str(task.get("uuid")): task for task in export}
    results = []
    for item in created:
        task = by_uuid.get(item["uuid"])
        if task is None:
            results.append({"uuid": item["uuid"], "ok": False,
                            "reason": "not found after re-export"})
            continue
        expected = item["record"]
        mismatches = []
        if task.get("description") != expected["description"]:
            mismatches.append("description")
        if _scheduled_date(task) != expected["scheduled"]:
            mismatches.append("scheduled")
        for key in ("starttime", "endtime", "location", "transport", "travel",
                    "est", "todo"):
            if (task.get(key) or None) != (expected.get(key) or None):
                mismatches.append(key)
        actual_tags = {str(tag).lower() for tag in task.get("tags", [])}
        expected_tags = {str(tag).lower() for tag in expected.get("tags", [])}
        if not expected_tags <= actual_tags:
            mismatches.append("tags")
        results.append({
            "uuid": item["uuid"],
            "ok": not mismatches,
            "description": task.get("description"),
            "mismatches": mismatches,
        })
    return results


def lint_week(week_start: str, runner=_default_runner) -> dict:
    lint_path = Path(__file__).resolve().parents[1] / "taskwarrior_lint.py"
    code, out, err = runner(["python3", str(lint_path), "--week", week_start,
                             "--json"])
    warnings = []
    try:
        warnings = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        warnings = []
    return {"returncode": code, "warnings": warnings, "stderr": err.strip()}


def sync_calendar(runner=_default_runner) -> dict:
    gcal_path = (Path(__file__).resolve().parents[2]
                 / "skills" / "gcal-sync" / "bin" / "gcal-sync")
    code, out, err = runner([str(gcal_path)])
    return {"returncode": code, "stdout": out.strip(), "stderr": err.strip()}
