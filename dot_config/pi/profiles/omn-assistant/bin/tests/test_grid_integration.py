"""Source boundaries, generic coloring policies, and safe publication."""
from datetime import date, datetime

from grid_scheduler.adapter import load_live
from grid_scheduler.checks import policy_errors
from grid_scheduler.engine import solve
from grid_scheduler.facts import identity, reconcile_fixed, week_records
from grid_scheduler.grid import prepare
from grid_scheduler.history import seed_legacy_prefix
from grid_scheduler.schema import Color, Group, Item, Problem, Reservation
from grid_scheduler.verify import verify
from scheduler.common import TZ, ComposerConfig, FixedInterval

WEEK = date(2026, 9, 28)


def small(**kwargs):
    return Problem(WEEK, [Color("email", "work", 4, 4, ((40, 48),), min_run=4,
                              location="At home"), *kwargs.pop("colors", [])],
                   [Item("mail", "Send email", "email", 4, 4, ((40, 48),), min_piece=4)], **kwargs)


def test_work_cell_budget_and_run_budget_are_hard():
    assert solve(small(daily_max_work_cells={0: 3}))["status"] == "INFEASIBLE"
    assert solve(small(daily_max_work_runs={0: 0}))["status"] == "INFEASIBLE"
    p = small(daily_max_work_cells={0: 4}, daily_max_work_runs={0: 1})
    c = solve(p)
    assert c["status"] == "ok" and not verify(p, c)


def test_car_group_permits_short_free_gap_not_unrelated_activity():
    p = Problem(WEEK, [Color("car1", "work", 2, 2, ((40, 42),)),
                      Color("car2", "work", 2, 2, ((44, 46),)),
                      Color("other", "fixed")],
                [Item("a", "First errand", "car1", 2, 2, ((40, 42),)), Item("b", "Second errand", "car2", 2, 2, ((44, 46),))],
                groups=[Group("outing", ("car1", "car2"), max_free_gap=2)])
    good = solve(p)
    assert good["status"] == "ok" and not verify(p, good)
    p.reservations = [Reservation("interruption", "other", 42 * 15, 43 * 15)]
    assert solve(p)["status"] == "INFEASIBLE"
    assert any("group" in e for e in policy_errors(p,
        good["grid"][:42] + ["other"] + good["grid"][43:], good["runs"]))


def test_schema_roundtrip_keeps_new_policies_and_exact_anchor_travel():
    p = small(colors=[Color("event", "fixed", travel_before=2, travel_after=1),
                      Color("travel", "travel", maximum=672)],
              reservations=[Reservation("anchor", "event", 607, 620, "Meeting", "At home")],
              daily_max_work_runs={0: 6}, daily_max_work_cells={0: 32},
              groups=[Group("emails", ("email",))])
    assert Problem.from_dict(p.to_dict()).to_dict() == p.to_dict()
    painted, _ = prepare(p)
    assert painted[39] is None and painted[40] == "event" and painted[41] == "event"
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][38:40] == ["travel", "travel"] and c["grid"][42] == "travel"
    assert p.reservations[0].start_minute == 607


def test_preflight_proves_elapsed_deadline_without_invoking_z3():
    p = small(prefix=48)
    c = solve(p)
    assert c["status"] == "INFEASIBLE"
    assert c["stats"]["solver_checks"] == 0
    assert any(e.get("item") == "mail" and e["available_cells"] == 0 for e in c["capacity_errors"])


def test_source_errors_fail_closed_even_if_grid_would_fit():
    p = small(metadata={"diagnostics": [{"severity": "blocking", "message": "unknown status"}]})
    c = solve(p)
    assert c["status"] == "BLOCKED" and c["source_errors"] == ["unknown status"]
    p.metadata = {}
    c = solve(p)
    p.metadata = {"diagnostics": [{"severity": "blocking", "message": "unknown status"}]}
    assert "unknown status" in verify(p, c)


def test_week_overrides_and_recurring_cancellation_never_edit_default():
    records = [{"id": "piano", "type": "task", "meta": {
        "rrule": "FREQ=WEEKLY;BYDAY=TH", "start": "2026-09-28T00:00:00-05:00",
        "days": [3], "hours": [14, 18], "cancelled": True}},
        {"id": "later", "type": "task", "meta": {
            "target_week": "2026-10-05", "rrule": "FREQ=WEEKLY;BYDAY=MO"}},
        {"id": "meeting", "type": "event", "meta": {"hours": [11, 12],
            "week_overrides": {"2026-09-28": {"hours": [12, 13]}}}}]
    actual = week_records(records, WEEK)
    assert actual[0]["meta"]["active"] is False
    assert actual[1]["meta"]["active"] is False
    assert actual[2]["meta"]["hours"] == [12, 13]
    assert records[2]["meta"]["hours"] == [11, 12]
    assert "active" not in records[0]["meta"]


def test_fixed_identity_dedupe_does_not_erase_unrelated_nested_commitment():
    event = FixedInterval("event@2026-09-28", "Seminar", 600, 720, "omn-event", ["event"], "ECSS 3.226")
    same = FixedInterval("task:registered", "Attend Seminar", 600, 720, "task-fixed", ["registered"], "ECSS 3.226")
    other = FixedInterval("task:other", "Call professor", 615, 645, "task-fixed", ["other"], "ECSS 3.226")
    fixed, bindings, issues = reconcile_fixed([event, same, other], [], WEEK, ComposerConfig(), [])
    assert fixed == [event, other]
    assert bindings == {event.id: ["registered"]} and not issues
    assert identity("Buy weekly groceries") == identity("Grocery run")


def test_cancelled_authoritative_occurrence_is_not_restored_from_taskwarrior():
    record = {"id": "groceries", "type": "event", "title": "Weekly groceries", "meta": {
        "start": "2026-10-03T10:00:00-05:00", "end": "2026-10-03T11:30:00-05:00",
        "location": "Grocery store", "cancelled": ["2026-10-03"]}}
    task = FixedInterval("task:old", "Buy weekly groceries", 5 * 1440 + 600,
                         5 * 1440 + 690, "task-fixed", ["old"], "Grocery store")
    diagnostics = []
    fixed, _bindings, issues = reconcile_fixed([task], [record], WEEK, ComposerConfig(), diagnostics)
    assert fixed == [] and issues[0]["kind"] == "cancelled"
    assert diagnostics[0].blocking


def test_legacy_history_is_frozen_but_pending_time_is_not_completion():
    p = small(prefix=40)
    tasks = [{"uuid": "past", "status": "pending", "scheduled": "2026-09-28",
              "starttime": "09:00", "endtime": "10:00", "est": "1h",
              "description": "Send earlier email", "todo": "- Earlier email @60m [omn:earlier]",
              "location": "At home", "transport": "no-car", "tags": ["managed", "composer"]}]
    seed_legacy_prefix(p, tasks)
    prefix = p.previous[:40]
    assert len(set(prefix[36:40])) == 1 and prefix[36].startswith("history:")
    c = solve(p)
    assert c["status"] == "ok" and c["grid"][:40] == prefix
    assert len(c["owners"]) == 4
    assert p.metadata["sealed_legacy_records"][0]["uuid"] == "past"


def test_live_fixed_event_materialization_is_exact_and_skips_registered(monkeypatch):
    from scheduler import sources
    records = [{"id": "event:meeting", "type": "event", "title": "Seminar", "meta": {
        "start": "2026-09-28T12:07:00-05:00", "end": "2026-09-28T12:20:00-05:00",
        "location": "At home", "buffer_before": "20m", "buffer_after": "10m"}}]
    monkeypatch.setattr(sources, "read_omn_export", lambda: records)
    monkeypatch.setattr(sources, "read_task_export", list)
    problem = load_live(WEEK.isoformat(), now=datetime(2026, 9, 28, tzinfo=TZ))
    event = next(r for r in problem.reservations if r.id.startswith("event:meeting"))
    assert (event.start_minute, event.end_minute) == (727, 740)
    from grid_scheduler.facts import attendance_records
    rows = attendance_records(problem)
    assert rows[0]["starttime"] == "12:07" and rows[0]["endtime"] == "12:20"
    assert "fixed" in rows[0]["tags"]
    task = {"uuid": "registered", "status": "pending", "description": "Attend Seminar",
        "scheduled": "2026-09-28", "starttime": "12:07", "endtime": "12:20",
        "location": "At home", "tags": ["managed", "fixed"]}
    monkeypatch.setattr(sources, "read_task_export", lambda: [task])
    registered = load_live(WEEK.isoformat(), now=datetime(2026, 9, 28, tzinfo=TZ))
    assert not attendance_records(registered)


def test_live_same_course_assignments_share_a_semantic_color(monkeypatch):
    from scheduler import sources
    records = [{"id": f"canvas:{n}", "type": "task",
        "title": f"Homework {n} [MATH 3351.501 - F26]", "meta": {
            "est": "1h", "due": "2026-10-02T23:59:00-05:00"}}
        for n in (1, 2)]
    monkeypatch.setattr(sources, "read_omn_export", lambda: records)
    monkeypatch.setattr(sources, "read_task_export", list)
    p = load_live(WEEK.isoformat(), now=datetime(2026, 9, 28, tzinfo=TZ))
    assert len(p.items) == 2 and p.items[0].color == p.items[1].color
