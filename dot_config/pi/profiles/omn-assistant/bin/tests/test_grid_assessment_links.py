"""Canvas in-class exam and preparation must never consume two exam slots."""
from datetime import date

import pytest

from grid_scheduler.facts import week_records


def records():
    return [
        {"id": "canvas-exam", "type": "task", "meta": {"due": "2026-10-02T23:00:00Z",
         "in_class_assessment_for": "fixed-exam"}},
        {"id": "fixed-exam", "type": "event", "meta": {"active": True,
         "start": "2026-10-02T16:00:00-05:00", "end": "2026-10-02T18:00:00-05:00"}},
        {"id": "prep", "type": "task", "meta": {"est": "2h", "due": "2026-10-02T16:00:00-05:00"}},
    ]


def test_link_removes_extra_quantity_without_claiming_completion_or_mutating_store():
    original = records()
    normalized = week_records(original, date(2026, 9, 28))
    assert normalized[0]["meta"]["active"] is False
    assert normalized[0]["meta"]["planning_coverage"] == {"fixed_event": "fixed-exam", "not_completion": True}
    assert "active" not in original[0]["meta"]
    assert "status" not in normalized[0]["meta"]
    assert normalized[2]["meta"]["est"] == "2h"


def test_missing_event_is_blocked():
    with pytest.raises(ValueError, match="active fixed event"):
        week_records(records()[:1], date(2026, 9, 28))


def test_inconsistent_deadline_is_blocked():
    data = records()
    data[0]["meta"]["due"] = "2026-10-02T23:59:00-05:00"
    with pytest.raises(ValueError, match="deadline differs"):
        week_records(data, date(2026, 9, 28))


def test_cancelled_occurrence_is_blocked():
    data = records()
    data[1]["meta"]["cancelled"] = ["2026-10-02"]
    with pytest.raises(ValueError, match="uncancelled"):
        week_records(data, date(2026, 9, 28))


def test_live_compiler_reports_link_and_keeps_preparation_separate():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from grid_scheduler.adapter import load_live

    p = load_live("2026-09-28", omn_records=records(), task_records=[],
                  now=datetime(2026, 9, 28, 6, tzinfo=ZoneInfo("America/Chicago")))
    assert all(i.id != "canvas-exam" for i in p.items)
    assert next(i for i in p.items if i.id == "prep").minimum == 8
    assert any(d["tag"] == "fixed-assessment-linked" for d in p.metadata["diagnostics"])
