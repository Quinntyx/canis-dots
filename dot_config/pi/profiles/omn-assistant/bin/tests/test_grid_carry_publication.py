"""Explicitly replace stale plans without rewriting actual history."""
import pytest
from test_grid_scheduler import FakeTasks, one

from grid_scheduler.apply import apply
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve


def old(**changes):
    return {"uuid": "old", "status": "pending", "tags": ["managed", "composer"],
            "scheduled": "2026-09-28", "starttime": "12:00", "endtime": "14:00",
            "todo": "- Work @120m [omn:a]", "est": "2h", **changes}


def plan():
    p = one(windows=((52, 60),), prefix=52)
    c = solve(p, timeout_ms=3000)
    return p, c, decode(p, c)


def test_crossing_prefix_plan_needs_explicit_carry_opt_in():
    p, c, rows = plan()
    fake = FakeTasks([old()])
    assert apply(p, c, rows, replace_legacy=True, taskwarrior=fake,
                 confirmed=True, post_publish=False).get("refused")
    assert fake.calls == []
    report = apply(p, c, rows, replace_legacy=True, replace_carried=True,
                   taskwarrior=fake, confirmed=True, post_publish=False)
    assert report["applied"] and report["deleted"] == ["old"]


@pytest.mark.parametrize("changes", [
    {"status": "completed"}, {"tags": ["managed", "composer", "fixed"]},
    {"tags": ["composer"]}, {"scheduled": "2026-10-05"},
])
def test_carry_cannot_retire_completed_fixed_unmanaged_or_other_weeks(changes):
    p, c, rows = plan()
    fake = FakeTasks([old(**changes)])
    apply(p, c, rows, replace_legacy=True, replace_carried=True,
          taskwarrior=fake, confirmed=True, post_publish=False)
    assert ("delete", "old") not in fake.calls
    assert any(t["uuid"] == "old" for t in fake.tasks)


def test_carry_cannot_drop_unrepresented_source_bullets():
    p, c, rows = plan()
    fake = FakeTasks([old(todo="- Mixed [omn:a]\n- Unresolved [omn:b]")])
    report = apply(p, c, rows, replace_legacy=True, replace_carried=True,
                   taskwarrior=fake, confirmed=True, post_publish=False)
    assert report.get("refused") and fake.calls == []
