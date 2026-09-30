"""Apply-path tests: dry-run safety, UUID ownership, refusal gates."""

from __future__ import annotations

import json

from scheduler.apply import apply_candidate
from scheduler.common import ComposerConfig
from scheduler.sources import load_live, load_spec

WEEK = "2026-09-28"


def config():
    return ComposerConfig(candidates=1, solver_timeout_ms=8_000)


def record(omn_id="a", **overrides):
    base = {
        "description": "Work on A",
        "scheduled": "2026-09-28",
        "starttime": "10:00",
        "endtime": "11:00",
        "location": "home",
        "transport": "no-car",
        "est": "1h",
        "todo": f"- A @10m [omn:{omn_id}]",
        "tags": ["managed", "composer"],
    }
    base.update(overrides)
    return base


def candidate(records, **overrides):
    base = {
        "status": "ok",
        "optimization_exact": True,
        "records": records,
        "blocks": [{
            "group": ["m", "home"],
            "transport": "no-car",
            "day": WEEK,
            "start_minute": 10 * 60,
            "start": "10:00",
            "end": "11:00",
            "duration_minutes": 60,
            "allocations": [{"omn_id": "a", "minutes": 60}],
        }],
    }
    base.update(overrides)
    return base


class FakeTaskwarrior:
    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.deleted = []
        self.added = []
        self.delete_args = []
        self._counter = 0

    def export(self):
        return list(self.tasks)

    def delete_command(self, uuid):
        return ["task", "delete", uuid]

    def delete(self, uuid):
        self.delete_args.append(uuid)
        self.deleted.append(uuid)
        self.tasks = [t for t in self.tasks if t.get("uuid") != uuid]

    def add_command(self, rec):
        return ["task", "add", rec["description"]]

    def add(self, rec):
        self._counter += 1
        uuid = f"aaaaaaaa-aaaa-aaaa-aaaa-{self._counter:012d}"
        self.added.append((uuid, rec))
        exported = dict(rec)
        exported.update({
            "uuid": uuid, "status": "pending",
            "scheduled": rec["scheduled"].replace("-", "") + "T050000Z",
        })
        self.tasks.append(exported)
        return uuid


def spec_week(tmp_path, spec):
    spec.setdefault("week_start", WEEK)
    if spec.get("requirements") == []:
        spec["requirements"] = [{
            "omn_id": "a", "title": "A", "est": "1h",
            "due": "2026-10-04T23:59:00", "topic": "m",
            "location": "home", "transport": "no-car",
        }]
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    return load_spec(path, config())


def live_week(omn=(), tasks=()):
    return load_live(WEEK, config(), omn_records=list(omn), task_records=list(tasks))


def test_dry_run_makes_no_changes(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    gateway = FakeTaskwarrior([])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=True)
    assert report.refused is None
    assert gateway.deleted == [] and gateway.added == []
    assert report.commands


def test_apply_requires_confirmation(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    gateway = FakeTaskwarrior([])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=False)
    assert report.refused is not None
    assert gateway.added == []


def test_apply_uses_uuid_not_numeric_id(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    legacy = {"uuid": "99999999-9999-9999-9999-999999999999", "id": 7,
              "status": "pending", "description": "old",
              "scheduled": "20260928T050000Z",
              "tags": ["managed", "composer"]}
    gateway = FakeTaskwarrior([legacy])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True, run_lint=False,
                             run_gcal=False)
    assert report.applied
    assert gateway.delete_args == ["99999999-9999-9999-9999-999999999999"]
    assert "7" not in gateway.delete_args


def test_apply_preserves_unmanaged_and_fixed(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    unmanaged = {"uuid": "u1", "id": 1, "status": "pending",
                 "description": "unmanaged", "tags": [], "est": "1h"}
    fixed = {"uuid": "f1", "id": 2, "status": "pending",
             "description": "class", "tags": ["managed", "fixed"],
             "starttime": "10:00", "endtime": "11:00",
             "scheduled": "20260928T050000Z"}
    gateway = FakeTaskwarrior([unmanaged, fixed])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True, run_lint=False,
                             run_gcal=False)
    assert report.applied
    assert gateway.deleted == []
    uuids = {t["uuid"] for t in gateway.tasks}
    assert {"u1", "f1"} <= uuids


def test_apply_replaces_composer_blocks(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    composer = {"uuid": "c1", "id": 3, "status": "pending",
                "description": "old composer", "tags": ["managed", "composer"],
                "scheduled": "20260928T050000Z"}
    gateway = FakeTaskwarrior([composer])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True, run_lint=False,
                             run_gcal=False)
    assert gateway.delete_args == ["c1"]
    assert report.applied and report.verification[0]["ok"]


def test_apply_refuses_blocking_diagnostics(tmp_path):
    week = spec_week(tmp_path, {
        "fixed": [
            {"id": "f1", "desc": "A", "day": WEEK, "start": "10:00", "end": "11:00"},
            {"id": "f2", "desc": "B", "day": WEEK, "start": "10:30", "end": "11:30"},
        ],
        "requirements": [],
    })
    gateway = FakeTaskwarrior([])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True)
    assert report.refused and "fixed-collision" in report.refused
    assert gateway.added == []


def test_apply_refuses_unknown_optimization(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    gateway = FakeTaskwarrior([])
    report = apply_candidate(week, candidate([record()], optimization_exact=False),
                             taskwarrior=gateway, dry_run=False, confirmed=True)
    assert report.refused and "unknown" in report.refused
    assert gateway.added == []


def test_apply_refuses_unmatched_legacy(tmp_path):
    task = {"uuid": "55555555-5555-5555-5555-555555555555", "id": 9,
            "status": "pending", "description": "orphan", "tags": ["managed"],
            "est": "1h", "scheduled": "20260928T050000Z"}
    week = live_week(tasks=[task])
    gateway = FakeTaskwarrior([task])
    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True)
    assert report.refused and "legacy-managed-unmatched" in report.refused
    assert gateway.added == []


def test_calendar_failure_is_reported_not_rollback(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    gateway = FakeTaskwarrior([])

    def lint_runner(argv):
        return 0, "[]", ""

    def gcal_runner(argv):
        return 1, "", "SYNC FAILED"

    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True, lint_runner=lint_runner,
                             gcal_runner=gcal_runner)
    assert report.applied
    assert report.gcal["returncode"] == 1
    assert any("not a rollback" in note for note in report.notes)
    assert report.created  # Taskwarrior writes survive the calendar failure


def test_apply_preserves_composer_blocks_from_other_weeks(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    future = {
        "uuid": "future", "status": "pending", "description": "future block",
        "tags": ["managed", "composer"], "scheduled": "20261012T050000Z",
    }
    gateway = FakeTaskwarrior([future])
    report = apply_candidate(
        week, candidate([record()]), taskwarrior=gateway,
        dry_run=False, confirmed=True, run_lint=False, run_gcal=False,
    )
    assert report.applied
    assert "future" not in gateway.deleted
    assert any(task.get("uuid") == "future" for task in gateway.tasks)


def test_apply_refuses_tampered_support_placement(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    bad = candidate([record()])
    bad["supports"] = [{
        "id": "support:dinner:2026-10-01", "start": 21 * 60 + 3 * 1440,
        "duration": 45, "location": "At home",
    }]
    gateway = FakeTaskwarrior([])
    report = apply_candidate(
        week, bad, taskwarrior=gateway,
        dry_run=False, confirmed=True, run_lint=False, run_gcal=False,
    )
    assert report.refused and "support" in report.refused
    assert gateway.added == []


def test_apply_refuses_tampered_candidate_coverage(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    bad = candidate([record()])
    bad["blocks"][0]["allocations"][0]["minutes"] = 30
    gateway = FakeTaskwarrior([])
    report = apply_candidate(
        week, bad, taskwarrior=gateway,
        dry_run=False, confirmed=True, run_lint=False, run_gcal=False,
    )
    assert report.refused and "coverage" in report.refused
    assert gateway.added == []


def test_lint_result_reported(tmp_path):
    week = spec_week(tmp_path, {"requirements": []})
    gateway = FakeTaskwarrior([])
    warnings = [{"policy": "x", "severity": "WARN", "message": "m", "refs": []}]

    def lint_runner(argv):
        return 0, json.dumps(warnings), ""

    report = apply_candidate(week, candidate([record()]), taskwarrior=gateway,
                             dry_run=False, confirmed=True, lint_runner=lint_runner,
                             run_gcal=False)
    assert report.lint["warnings"] == warnings
