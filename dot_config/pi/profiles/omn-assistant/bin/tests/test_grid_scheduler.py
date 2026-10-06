"""New grid engine tests. No live omn/task/mail/calendar subprocesses."""
import copy
import itertools
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from grid_scheduler.adapter import completed_credit, load_live
from grid_scheduler.apply import apply
from grid_scheduler.cli import main
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve
from grid_scheduler.grid import prepare
from grid_scheduler.layout import flow_layout
from grid_scheduler.schema import CELLS, STEP, Color, Item, Problem, Reservation
from grid_scheduler.verify import verify

WEEK = date(2026, 9, 28)


def one(*, minimum=4, maximum=None, windows=((40, 60),), min_run=1, max_run=96,
        indivisible=False, min_piece=1, reservations=(), extra_colors=(), gaps=None, prefix=0, previous=None):
    maximum = minimum if maximum is None else maximum
    return Problem(WEEK, [Color("work", minimum=minimum, maximum=maximum, windows=windows,
                               min_run=min_run, max_run=max_run, topic="email"), *extra_colors],
                   [Item("a", "Email Alice", "work", minimum, maximum, windows,
                         indivisible=indivisible, min_piece=min_piece)],
                   list(reservations), gaps or {}, prefix, previous)


def test_counts_runs_layout_and_earliness():
    p = one(min_run=4)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["optimization_exact"]
    assert c["grid"][40:44] == ["work"] * 4
    assert len(c["matrix"]) == 96 and all(len(row) == 7 for row in c["matrix"])
    assert c["runs"] == [{"color": "work", "start": 40, "end": 44, "cells": 4}]
    assert verify(p, c) == []
    r = decode(p, c)[0]
    assert r["starttime"] == "10:00" and r["endtime"] == "11:00"
    assert r["todo"] == "- Email Alice @60m [omn:a]"


def test_multiple_items_share_semantic_color_and_one_block():
    p = one()
    p.items = [Item("a", "Email Alice", "work", 2, 2, ((40, 60),)),
               Item("b", "Email Bob", "work", 2, 2, ((40, 60),))]
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and len(c["runs"]) == 1
    records = decode(p, c)
    assert len(records) == 1
    assert "[omn:a]" in records[0]["todo"] and "[omn:b]" in records[0]["todo"]


def test_color_amount_range_and_item_bounds():
    p = one(minimum=2, maximum=6)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert 2 <= c["grid"].count("work") <= 6
    assert c["grid"].count("work") == 2  # earliest-work objective doesn't invent work


def test_run_minimum_and_maximum():
    p = one(minimum=8, min_run=4, max_run=4)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert len(c["runs"]) == 2 and all(r["cells"] == 4 for r in c["runs"])


def test_fixed_rounding_preserves_authoritative_times():
    p = one(minimum=2, windows=((40, 48),), extra_colors=[Color("class", "fixed")],
            reservations=[Reservation("f", "class", 602, 643, "Class", "ECSN 2.120")])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][40:43] == ["class"] * 3
    assert p.to_dict()["reservations"][0]["start_minute"] == 602
    assert all(r["start"] >= 43 for r in c["runs"])


def test_partial_availability_and_deadline_rounded_inward():
    # Item may start only after minute 607 and finish before 658 -> 41..43.
    p = one(minimum=2, windows=((41, 43),))
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and c["runs"][0]["start"] == 41
    assert c["runs"][0]["end"] == 43


@pytest.mark.parametrize("gap", [1, 2])
def test_transitions_are_actual_reserved_travel_cells(gap):
    p = one(minimum=2, windows=((40, 50),), min_run=2,
            extra_colors=[Color("class", "fixed", location="Campus", travel_before=gap, travel_after=gap),
                          Color("travel", "travel", maximum=CELLS)],
            reservations=[Reservation("class", "class", 40 * STEP, 42 * STEP)])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][42:42 + gap] == ["travel"] * gap
    assert next(r for r in c["runs"] if r["color"] == "work")["start"] == 42 + gap


def test_work_cannot_substitute_for_reserved_travel():
    p = one(minimum=1, windows=((42, 43),),
            extra_colors=[Color("a", "fixed"), Color("b", "fixed", travel_after=1),
                          Color("travel", "travel", maximum=CELLS)],
            reservations=[Reservation("a", "a", 40 * STEP, 41 * STEP),
                          Reservation("b", "b", 41 * STEP, 42 * STEP)])
    assert solve(p, timeout_ms=3000)["status"] == "INFEASIBLE"


def test_daily_afternoon_restrictions():
    windows = tuple((d * 96 + 56, d * 96 + 64) for d in range(7))
    p = one(minimum=14, windows=windows, min_run=2)
    p.colors[0] = Color("work", minimum=14, maximum=14, windows=windows,
                        min_run=2, daily={d: (2, 2) for d in range(7)})
    c = solve(p, timeout_ms=4000)
    assert c["status"] == "ok"
    assert len(c["runs"]) == 7
    assert all(56 <= r["start"] % 96 < r["end"] % 96 <= 64 for r in c["runs"])


def test_shared_color_flow_has_hall_cut_not_false_coverage():
    items = [Item("early", "Early", "email", 2, 2, ((40, 42),)),
             Item("late", "Late", "email", 2, 2, ((40, 48),))]
    failed = flow_layout("email", items, {44, 45, 46, 47})
    assert failed.status == "invalid" and failed.cut == ("email", {40, 41}, 2)
    p = Problem(WEEK, [Color("email", minimum=4, maximum=4, windows=((40, 48),))], items)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["owners"]["40"] == "early" and c["owners"]["41"] == "early"


def test_shared_color_incompatible_deadlines_are_infeasible():
    items = [Item("a", "A", "email", 2, 2, ((40, 42),)),
             Item("b", "B", "email", 2, 2, ((40, 42),))]
    p = Problem(WEEK, [Color("email", minimum=4, maximum=4, windows=((40, 50),))], items)
    assert solve(p, timeout_ms=3000)["status"] == "INFEASIBLE"


def test_whole_item_is_not_credited_by_fragments():
    p = one(minimum=4, windows=((40, 42), (44, 46)), indivisible=True)
    c = solve(p, timeout_ms=3000)
    # Necessary whole-patch capacity now rejects this before Python mask cuts.
    assert c["status"] == "INFEASIBLE" and c["stats"]["layout_cuts"] == 0


def test_minimum_piece_packing_does_not_shrink_task():
    p = one(minimum=8, windows=((40, 44), (48, 52)), min_piece=4)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert sum(r["cells"] for r in c["runs"]) == 8
    assert [r["description"].split()[0] for r in decode(p, c)] == ["Start", "Finish"]


def test_prefix_is_exactly_copied_and_not_completion_credit():
    previous = ["free"] * CELLS
    previous[40:44] = ["work"] * 4
    previous[80:84] = ["work"] * 4  # this suffix must be cleared, not retained
    p = one(minimum=4, windows=((44, 60),), min_run=4, prefix=44, previous=previous)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][:44] == previous[:44]
    assert c["grid"].count("work") == 8  # remaining-demand input still needs 4 new cells
    assert c["grid"][80:84] == ["free"] * 4
    assert all(r["start"] >= 44 for r in c["runs"])


def test_history_only_palette_and_source_conflict():
    previous = ["free"] * CELLS
    previous[0] = "old"
    p = one(prefix=1, previous=previous, extra_colors=[Color("old", "unavailable")])
    assert solve(p, timeout_ms=3000)["grid"][0] == "old"
    p.reservations.append(Reservation("new", "old", 15, 30))
    prepare(p)
    p.reservations.append(Reservation("bad", "sleep", 0, 15))
    p.colors.append(Color("sleep", "sleep"))
    with pytest.raises(ValueError, match="contradicts sealed history"):
        prepare(p)


def test_verify_rejects_tampered_grid_owner_runs_and_records():
    p = one()
    c = solve(p, timeout_ms=3000)
    changed = copy.deepcopy(c)
    changed["owners"]["0"] = "a"
    assert verify(p, changed)
    changed = copy.deepcopy(c)
    changed["grid"][40] = "fixed"
    assert verify(p, changed)
    changed = copy.deepcopy(c)
    changed["runs"] = []
    assert verify(p, changed)
    records = decode(p, c)
    records[0]["todo"] = "- bogus [omn:a]"
    assert apply(p, c, records, taskwarrior=object())["refused"]


def test_flow_matches_exhaustive_small_layouts():
    slots = {0, 1, 2}
    windows = [((0, 1),), ((1, 3),), ((0, 3),)]
    for wa, wb, mina, minb, maxa, maxb in itertools.product(windows, windows, (1, 2), (1, 2), (2, 3), (2, 3)):
        items = [Item("a", "A", "c", mina, maxa, wa), Item("b", "B", "c", minb, maxb, wb)]
        brute = False
        for assignment in itertools.product("ab", repeat=3):
            allowed = all(any(a <= slot < b for a, b in items[0 if rid == "a" else 1].windows)
                          for slot, rid in enumerate(assignment))
            brute |= allowed and mina <= assignment.count("a") <= maxa and minb <= assignment.count("b") <= maxb
        assert (flow_layout("c", items, slots).status == "ok") == brute


def test_completed_credit_apportions_pins_not_full_block():
    tasks = [{"uuid": "x", "status": "completed", "scheduled": "2026-09-28", "est": "1h",
              "todo": "- Email @15m [omn:a]\n- Read [omn:b]"}]
    assert completed_credit(tasks, WEEK) == {"a": 15, "b": 45}
    tasks[0]["todo"] = "- A [omn:a]\n- B [omn:b]"
    with pytest.raises(ValueError, match="ambiguous"):
        completed_credit(tasks, WEEK)


def test_live_adapter_is_readonly_compiles_windows_and_rounding():
    records = [{"id": "a", "type": "task", "title": "Email professor", "meta": {
        "est": "20m", "due": "2026-10-02T16:08:00-05:00", "unlock": "2026-10-01T14:08:00-05:00",
        "hours": "14:00-17:00", "topic": "school", "location": "At home"}}]
    p = load_live("2026-09-28", now=datetime(2026, 10, 1, 14, 11, tzinfo=ZoneInfo("America/Chicago")),
                  omn_records=records, task_records=[])
    assert p.prefix == 3 * 96 + 57
    assert p.items[0].minimum == 2
    assert p.items[0].windows[0][0] == p.prefix
    assert p.items[0].windows[-1][1] == 4 * 96 + 64
    assert p.colors[0].topic == "email"
    assert p.metadata["rounding_notes"]


def test_cli_native_schema_and_legacy_is_explicit(tmp_path, capsys):
    spec = tmp_path / "input.json"
    plan = tmp_path / "plan.json"
    spec.write_text(json.dumps(one(min_run=4).to_dict()))
    assert main(["plan", "--spec", str(spec), "--out", str(plan), "--quiet"]) == 0
    assert main(["show", "--plan", str(plan)]) == 0
    assert "Email Alice" in capsys.readouterr().out
    assert main(["apply", "--plan", str(plan), "--yes"]) == 1
    assert "spec plans are dry-run only" in capsys.readouterr().out
    spec.write_text(json.dumps({"week_start": "2026-09-28", "requirements": []}))
    assert main(["plan", "--spec", str(spec), "--quiet"]) == 1


class FakeTasks:
    def __init__(self, tasks=()):
        self.tasks = [copy.deepcopy(t) for t in tasks]
        self.calls = []
    def export(self):
        return copy.deepcopy(self.tasks)
    def add_command(self, r):
        return ["task", "add", r["description"]]
    def delete_command(self, uuid):
        return ["task", uuid, "delete"]
    def add(self, r):
        uuid = f"new-{len(self.tasks)}"
        self.calls.append(("add", uuid))
        self.tasks.append({**copy.deepcopy(r), "uuid": uuid, "status": "pending"})
        return uuid
    def delete(self, uuid):
        self.calls.append(("delete", uuid))
        self.tasks = [t for t in self.tasks if t["uuid"] != uuid]


def test_dryrun_and_apply_preserve_prefix_fixed_and_other_weeks():
    p = one(windows=((44, 60),), prefix=44)
    c = solve(p, timeout_ms=3000)
    records = decode(p, c)
    old = {"uuid": "old", "status": "pending", "tags": ["managed", "composer", "grid-2026-09-28"],
           "scheduled": "2026-09-28", "starttime": "11:00", "endtime": "12:00",
           "todo": "- Email Alice @60m [omn:a]", "est": "60m"}
    past = {**old, "uuid": "past", "starttime": "10:00", "endtime": "11:00"}
    fixed = {**old, "uuid": "fixed", "starttime": "14:00", "endtime": "15:00", "tags": ["managed", "fixed"]}
    other = {**old, "uuid": "other", "scheduled": "2026-10-05", "tags": ["managed", "composer", "grid-2026-10-05"]}
    fake = FakeTasks([old, past, fixed, other])
    report = apply(p, c, records, taskwarrior=fake, post_publish=False)
    assert report["dry_run"] and fake.calls == []
    report = apply(p, c, records, taskwarrior=fake, confirmed=True, post_publish=False)
    assert report["applied"] and report["deleted"] == ["old"]
    assert {t["uuid"] for t in fake.tasks} >= {"past", "fixed", "other"}


def test_live_apply_refuses_elapsed_start():
    p = one()
    p.source = "live"
    c = solve(p, timeout_ms=3000)
    report = apply(p, c, decode(p, c), taskwarrior=object(), now=datetime(2026, 9, 28, 12, tzinfo=ZoneInfo("America/Chicago")))
    assert "elapsed time" in str(report["refused"])


def test_digest_ignores_time_drifted_urgency():
    from grid_scheduler.adapter import digest
    task = {"uuid": "u1", "description": "HW", "urgency": 6.83}
    baseline = digest([], [task])
    drifted = digest([], [dict(task, urgency=12.0)])
    assert baseline == drifted and baseline != digest([], [])
