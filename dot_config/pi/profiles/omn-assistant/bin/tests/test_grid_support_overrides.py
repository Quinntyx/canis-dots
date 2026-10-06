"""One-day user exceptions must survive refresh without becoming patterns."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from grid_scheduler.adapter import load_live
from grid_scheduler.policies import support_overrides

WEEK = date(2026, 9, 28)


def note(rules, *, rid="exception", stamp="2026-10-02"):
    return {"id": rid, "record": "item", "type": "note", "tags": ["manual"],
            "meta": {"support_overrides": {stamp: rules}}}


def test_date_only_waiver_early_lunch_and_skipped_breakfast():
    records = [note({"break": {"waived": True}, "breakfast": {"skipped": True},
                     "lunch": {"hours": "10:15-11:15"}})]
    p = load_live(str(WEEK), omn_records=records, task_records=[],
                  now=datetime(2026, 10, 2, 9, 20, tzinfo=ZoneInfo("America/Chicago")))
    colors = {c.key: c for c in p.colors}
    assert 4 not in colors["support:break"].daily
    assert 5 in colors["support:break"].daily
    assert (425, 429) in colors["support:lunch"].windows
    assert (524, 536) in colors["support:lunch"].windows  # Saturday defaults unchanged
    assert any("reported skipped" in n for n in p.metadata["rounding_notes"])
    assert records[0]["meta"]["support_overrides"]["2026-10-02"]["lunch"]["hours"] == "10:15-11:15"


def test_exception_does_not_repeat_the_following_week():
    records = [note({"break": {"waived": True}})]
    assert support_overrides(records, date(2026, 10, 5)) == {}


def test_conflicting_records_fail_closed():
    with pytest.raises(ValueError, match="conflicting support overrides"):
        support_overrides([note({"break": {"waived": True}}),
                           note({"break": {"waived": False}}, rid="other")], WEEK)


def test_unknown_support_name_and_nonboolean_waivers_are_rejected():
    with pytest.raises(ValueError, match="invalid support override"):
        support_overrides([note({"brunch": {"waived": True}})], WEEK)
    with pytest.raises(TypeError, match="must be boolean"):
        support_overrides([note({"break": {"waived": "yes"}})], WEEK)


def test_invalid_hours_and_unsupported_fields_are_rejected():
    with pytest.raises(ValueError, match="same-day interval"):
        support_overrides([note({"lunch": {"hours": "11:15-10:15"}})], WEEK)
    with pytest.raises(ValueError, match="unsupported support fields"):
        support_overrides([note({"lunch": {"est": "30m"}})], WEEK)
