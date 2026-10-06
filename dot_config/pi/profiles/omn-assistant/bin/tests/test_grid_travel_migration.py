"""Explicit travel migration may replace only exact owned future legacy trips."""
import copy
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from test_grid_scheduler import FakeTasks

from grid_scheduler.adapter import load_live
from grid_scheduler.apply import apply
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve
from grid_scheduler.travel import migrated_bindings

WEEK = date(2026, 9, 28)
NOW = datetime(2026, 9, 28, tzinfo=ZoneInfo("America/Chicago"))


def fixture():
    event = {"id": "event", "record": "item", "type": "event", "title": "Actual Event", "tags": [],
             "meta": {"start": "2026-09-28T10:00:00-05:00", "end": "2026-09-28T11:00:00-05:00",
                      "location": "Venue", "travel_time": {"before": "30m", "after": "0m", "mode": "car"}}}
    alias = {"id": "old-trip", "record": "item", "type": "note", "title": "Drive to Event", "tags": ["legacy"],
             "meta": {"active": False, "start": "2026-09-28T09:30:00-05:00", "end": "2026-09-28T10:00:00-05:00",
                      "travel_replaced_by": {"event": "event", "side": "before"}}}
    exceptions = {"id": "fixture-waivers", "record": "item", "type": "note", "tags": [],
                  "meta": {"support_overrides": {
                      (WEEK + timedelta(days=d)).isoformat(): {name: {"waived": True}
                          for name in ("cook", "breakfast", "lunch", "break", "dinner")} for d in range(7)}}}
    task = {"uuid": "old", "status": "pending", "tags": ["managed", "fixed"],
            "description": "Attend Drive to Event", "scheduled": "20260928T050000Z",
            "starttime": "09:30", "endtime": "10:00", "todo": "- Attend Drive [omn:old-trip]"}
    return [event, alias, exceptions], task


def test_live_compiler_retires_exact_alias_not_other_fixed_blocks():
    records, task = fixture()
    p = load_live(str(WEEK), now=NOW, omn_records=records, task_records=[task])
    assert p.metadata["retired_travel_bindings"]["old"]["span"] == [570, 600]
    assert not any(r.id == "task:old" for r in p.reservations)
    modified = copy.deepcopy(task)
    modified["endtime"] = "10:15"
    assert migrated_bindings(records, [modified], WEEK) == {}
    modified = copy.deepcopy(task)
    modified["status"] = "completed"
    assert migrated_bindings(records, [modified], WEEK) == {}


def test_migration_flag_is_required_and_ordinary_fixed_attendance_is_protected():
    facts, old = fixture()
    p = load_live(str(WEEK), now=NOW, omn_records=facts, task_records=[old])
    p.source = "spec"  # production refuses spec; injected fake transport is the test seam
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    rows = decode(p, c)
    fake = FakeTasks([old])
    refused = apply(p, c, rows, confirmed=True, taskwarrior=fake, now=NOW, post_publish=False)
    assert any("protected" in error for error in refused["refused"])
    assert fake.calls == []
    other = {**old, "uuid": "ordinary", "starttime": "13:00", "endtime": "14:00", "todo": "- Attend [omn:other]"}
    fake = FakeTasks([old, other])
    result = apply(p, c, rows, confirmed=True, replace_travel=True,
                   taskwarrior=fake, now=NOW, post_publish=False)
    assert result["deleted"] == ["old"]
    assert any(t["uuid"] == "ordinary" for t in fake.tasks)
    # Sub-hour travel is no longer its own item: the old alias is retired and
    # the reserved grid cells speak for the drive instead.
    assert not any(t["description"] == "Drive to Actual Event" for t in fake.tasks)


def test_event_reference_does_not_authorize_replacing_unknown_nontravel_work():
    records, _ = fixture()
    p = load_live(str(WEEK), now=NOW, omn_records=records, task_records=[])
    p.source = "spec"
    c = solve(p, timeout_ms=3000)
    actor = {"uuid": "unresolved", "status": "pending", "tags": ["managed", "grid-2026-09-28"],
             "scheduled": "20260928T050000Z", "starttime": "09:30", "endtime": "10:00",
             "description": "Follow up on event", "todo": "- Follow up [omn:event]"}
    fake = FakeTasks([actor])
    result = apply(p, c, decode(p, c), confirmed=True, taskwarrior=fake, now=NOW, post_publish=False)
    assert result["refused"] and fake.calls == []


@pytest.mark.parametrize("legacy_buffers", [False, True])
def test_multiday_parent_reuses_exact_daily_registrations_without_duplicate_attendance(legacy_buffers):
    records, _ = fixture()
    event = records[0]
    event["meta"].update(start="2026-10-03T11:30:00-05:00", end="2026-10-04T17:00:00-05:00",
                         travel_time={"before": "5h", "after": "5h", "mode": "car"})
    if legacy_buffers:
        event["meta"].update(buffer_before="30m", buffer_after="30m")
    tasks = [
        {"uuid": "sat", "status": "pending", "tags": ["managed", "fixed"], "description": "Attend Actual Event",
         "scheduled": "20261003T050000Z", "starttime": "11:30", "endtime": "24:00", "location": "Venue"},
        {"uuid": "sun", "status": "pending", "tags": ["managed", "fixed"], "description": "Attend Actual Event",
         "scheduled": "20261004T050000Z", "starttime": "00:00", "endtime": "17:00", "location": "Venue"},
    ]
    p = load_live(str(WEEK), now=NOW, omn_records=[event, records[2]], task_records=tasks)
    assert sorted(p.metadata["fixed_task_bindings"].values()) == [["sat"], ["sun"]]
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert not any("fixed" in r["tags"] for r in decode(p, c))
    trips = [r for r in decode(p, c) if "travel" in r["tags"]]
    assert [(r["starttime"], r["endtime"]) for r in trips] == [("06:30", "11:30"), ("17:00", "22:00")]
    p.metadata["fixed_task_bindings"].pop("event@2026-10-04")
    assert any(r["scheduled"] == "2026-10-04" and "fixed" in r["tags"] for r in decode(p, c))


def test_day_segments_keep_away_semantics_but_recurring_day_gaps_do_not():
    from types import SimpleNamespace

    from grid_scheduler.facts import away_spans
    def frame(a, b):
        return SimpleNamespace(start=a, end=b, buffer_before=0, buffer_after=0,
                               refs=["same"], location="Venue", label="Event", id="segment")
    assert away_spans([frame(7890, 8640), frame(8640, 9660)]) == [(7890, 9660)]
    assert away_spans([frame(60, 120), frame(3 * 1440 + 60, 3 * 1440 + 120)]) == []


def test_previous_week_archived_trip_does_not_block_new_week():
    records, task = fixture()
    # The committed prior-week visit differed from the standing source time.
    records[0]["meta"]["start"] = "2026-09-28T08:00:00-05:00"
    assert migrated_bindings(records, [task], date(2026, 10, 5)) == {}


def test_bad_alias_span_fails_closed_and_past_trip_cannot_be_retired():
    facts, old = fixture()
    facts[1]["meta"]["start"] = "2026-09-28T09:15:00-05:00"
    with pytest.raises(ValueError, match="does not match declared travel"):
        migrated_bindings(facts, [old], WEEK)
    facts, old = fixture()
    p = load_live(str(WEEK), now=NOW, omn_records=facts, task_records=[old])
    p.source = "spec"
    c = solve(p, timeout_ms=3000)
    rows = decode(p, c)
    past = copy.deepcopy(old)
    past["scheduled"] = "20260927T050000Z"
    fake = FakeTasks([past])
    result = apply(p, c, rows, confirmed=True, replace_travel=True,
                   taskwarrior=fake, now=NOW, post_publish=False)
    assert result["deleted"] == [] and any(t["uuid"] == "old" for t in fake.tasks)
