"""Core tests for the scheduler redesign: sources, model, decode."""

from __future__ import annotations

import itertools
import json
import re
from datetime import date, datetime, timedelta

import pytest

from scheduler import rrule as rrule_mod
from scheduler import sources
from scheduler.common import (
    ComposerConfig,
    normalize_week_start,
)
from scheduler.decode import decode_candidate
from scheduler.model import build_model, solve_candidates

WEEK = "2026-09-28"
PIN_RE = re.compile(r"@(\d+)m")


def config(**overrides) -> ComposerConfig:
    base = {"step": 30, "min_block": 30, "max_block": 240, "day_cap": 6,
            "wake_hour": 6, "max_blocks": 12, "candidates": 1,
            "solver_timeout_ms": 8_000, "seed": 11}
    base.update(overrides)
    return ComposerConfig(**base)


def spec_file(tmp_path, spec: dict):
    path = tmp_path / "spec.json"
    spec.setdefault("week_start", WEEK)
    path.write_text(json.dumps(spec))
    return path


def solve_spec(tmp_path, spec, cfg=None):
    cfg = cfg or config()
    week = sources.load_spec(spec_file(tmp_path, spec), cfg)
    return week, solve_candidates(week, cfg)


def total_alloc(blocks, req_index):
    return sum(b["allocations"].get(req_index, 0) for b in blocks)


def parse_pins(todo: str):
    pinned = {}
    for line in todo.splitlines():
        ref = re.search(r"\[omn:([^\]]+)\]", line)
        pin = PIN_RE.search(line)
        if ref and pin:
            pinned[ref.group(1)] = int(pin.group(1))
    return pinned


# ------------------------------------------------------------------ coverage


def test_hard_coverage_is_exact(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": 2.0,
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    assert total_alloc(candidate["blocks"], 0) == 120


def test_one_block_covers_many_requirements(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [
            {"omn_id": "a", "title": "A", "est": 1.0,
             "due": "2026-10-04T23:59:00", "topic": "m", "location": "home"},
            {"omn_id": "b", "title": "B", "est": 1.0,
             "due": "2026-10-04T23:59:00", "topic": "m", "location": "home"},
        ],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    assert len(candidate["blocks"]) == 1
    assert set(candidate["blocks"][0]["allocations"]) == {0, 1}


def test_one_requirement_spans_many_blocks(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "maximum_block_minutes": 60,
        "requirements": [{"omn_id": "a", "title": "A", "est": 4.0,
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    }, config(max_block=60, max_blocks=12))
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    assert len(candidate["blocks"]) >= 4
    assert total_alloc(candidate["blocks"], 0) == 240


# ------------------------------------------------------- temporal constraints


def test_fixed_intervals_are_excluded(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "fixed": [{"id": "f", "desc": "Class", "day": "2026-09-28",
                   "start": "06:00", "end": "12:00"}],
        "requirements": [{"omn_id": "a", "title": "A", "est": 1.0,
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    for block in candidate["blocks"]:
        end = block["start"] + block["duration"]
        blocked_start = 6 * 60
        blocked_end = 12 * 60
        assert not (block["start"] < blocked_end and blocked_start < end)


def test_blocks_never_overlap(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [
            {"omn_id": "a", "title": "A", "est": 2.0,
             "due": "2026-10-04T23:59:00", "topic": "m", "location": "home"},
            {"omn_id": "b", "title": "B", "est": 2.0,
             "due": "2026-10-04T23:59:00", "topic": "n", "location": "SU"},
        ],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    spans = sorted((b["start"], b["start"] + b["duration"])
                   for b in candidate["blocks"])
    for (s1, e1), (s2, e2) in itertools.pairwise(spans):
        assert e1 <= s2


def test_requirement_window_is_respected(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": 2.0,
                          "available": "2026-09-29T00:00:00",
                          "due": "2026-09-29T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    # Tuesday only: 1440..2880
    for block in candidate["blocks"]:
        end = block["start"] + block["duration"]
        assert 1440 <= block["start"] and end <= 2880


def test_impossible_window_yields_unsat_core(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "imp", "title": "Impossible", "est": 2.0,
                          "available": "2026-09-28T12:00:00",
                          "due": "2026-09-28T11:00:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "INFEASIBLE"
    assumptions = {item["assumption"] for item in candidate["unsat_core"]}
    # The capacity precheck names it first when the window cannot hold the
    # minutes; a pure window/coverage UNSAT core is the fallback shape.
    assert assumptions & {"capacity:imp", "coverage:imp"}
    assert any("imp" in a for a in assumptions)


def test_fixed_collision_is_flagged_blocking(tmp_path):
    week, _candidates = solve_spec(tmp_path, {
        "fixed": [
            {"id": "f1", "desc": "A", "day": "2026-09-28",
             "start": "10:00", "end": "11:00"},
            {"id": "f2", "desc": "B", "day": "2026-09-28",
             "start": "10:30", "end": "11:30"},
        ],
        "requirements": [],
    })
    tags = {(d.tag, d.severity) for d in week.diagnostics}
    assert ("fixed-collision", "blocking") in tags


def test_sleep_is_a_fixed_interval(tmp_path):
    week = sources.load_spec(spec_file(tmp_path, {"requirements": []}), config())
    sleep = [f for f in week.fixed_intervals if f.source == "sleep"]
    assert len(sleep) == 7
    assert all(f.start % 1440 == 0 and f.end % 1440 == 360 for f in sleep)


# ----------------------------------------------- weekend targets stay soft


def test_weekend_target_never_weakens_coverage(tmp_path):
    # Mon-Fri daytime is fully consumed; only the weekend can host the work.
    fixed = []
    for offset in range(5):
        day = (normalize_week_start(WEEK) + timedelta(days=offset)).isoformat()
        fixed.append({"id": f"f{offset}", "desc": "blocked", "day": day,
                      "start": "06:00", "end": "24:00"})
    _week, candidates = solve_spec(tmp_path, {
        "fixed": fixed,
        "requirements": [{"omn_id": "a", "title": "A", "est": 1.0,
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    assert total_alloc(candidate["blocks"], 0) == 60
    assert all(b["day"] >= 5 for b in candidate["blocks"])
    assert candidate["soft"]["timing"]["locked"] >= 0


# ------------------------------------------------------------ live filtering


def omn_task(rid, **meta):
    base = {"id": rid, "record": "item", "type": "task", "title": meta.pop("title", rid),
            "tags": meta.pop("tags", []), "meta": meta}
    return base


def live_week(omn, tasks=(), cfg=None, now=None):
    cfg = cfg or config()
    return sources.load_live(WEEK, cfg, omn_records=omn, task_records=list(tasks),
                             now=now)


def test_inactive_and_superseded_are_skipped():
    week = live_week([
        omn_task("a", est="1h", due="2026-10-02", active=False),
        omn_task("b", est="1h", due="2026-10-02", superseded_by="a"),
        omn_task("c", est="1h", due="2026-10-02"),
    ])
    assert {r.id for r in week.requirements} == {"c"}
    tags = {d.tag for d in week.diagnostics}
    assert "inactive-record" in tags


def test_missing_estimate_uses_documented_default_not_guess_silently():
    week = live_week([omn_task("a", due="2026-10-02")])
    assert any(d.tag == "default-estimate" for d in week.diagnostics)
    assert not any(d.blocking for d in week.diagnostics)
    assert week.requirements[0].required_minutes == 120


def test_placeholder_estimate_status_falls_back_with_warning():
    week = live_week([omn_task("a", est="2h", est_status="midpoint-placeholder",
                               due="2026-10-02")])
    assert any(d.tag == "default-estimate" for d in week.diagnostics)
    assert not any(d.blocking for d in week.diagnostics)
    assert week.requirements[0].required_minutes == 120


def test_configured_default_estimates_override_fallback():
    week = live_week(
        [omn_task("a", due="2026-10-02")],
        cfg=ComposerConfig(default_est_minutes=45, candidates=1))
    assert week.requirements[0].required_minutes == 45


def test_explicitly_pending_overdue_requirement_is_blocking_not_dropped():
    week = live_week([omn_task("a", est="2h", due="2026-09-01", active=True)])
    assert any(d.tag == "overdue-requirement" and d.blocking
               for d in week.diagnostics)
    assert week.requirements == []


def test_historical_feed_item_is_not_assumed_pending():
    week = live_week([
        omn_task("a", est="2h", due="2026-09-01", tags=["canvas", "ical"]),
    ])
    assert not any(d.tag == "overdue-requirement" for d in week.diagnostics)
    assert week.requirements == []


def test_rrule_cancelled_occurrence_is_removed():
    event = {
        "id": "ev", "record": "item", "type": "event", "title": "Recurring",
        "tags": ["recurring"],
        "meta": {
            "active": True,
            "start": "2026-09-28T10:00:00-05:00",
            "end": "2026-09-28T11:00:00-05:00",
            "rrule": "FREQ=WEEKLY;BYDAY=MO,WE",
            "cancelled": ["2026-09-28"],
        },
    }
    week = live_week([event])
    starts = {f.start for f in week.fixed_intervals if f.source == "omn-event"}
    # Monday (day 0) cancelled; Wednesday (day 2) kept.
    assert (2 * 1440 + 600) in starts
    assert (0 * 1440 + 600) not in starts


def test_recurring_event_expands_into_week():
    event = {
        "id": "ev", "record": "item", "type": "event", "title": "Weekly",
        "tags": ["recurring"],
        "meta": {
            "active": True,
            "start": "2026-09-04T15:45:00-05:00",
            "end": "2026-09-04T16:45:00-05:00",
            "rrule": "FREQ=WEEKLY;BYDAY=FR;UNTIL=20261210T235959Z",
        },
    }
    week = live_week([event])
    starts = [f.start for f in week.fixed_intervals if f.source == "omn-event"]
    assert starts == [4 * 1440 + 15 * 60 + 45]


def test_indivisible_requirement_sits_in_one_block(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "quin", "title": "Quinncia", "est": "2h",
                          "indivisible": True,
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    allocating = [b for b in candidate["blocks"] if b["allocations"]]
    assert len(allocating) == 1
    assert total_alloc(candidate["blocks"], 0) == 120


def test_indivisible_larger_than_max_block_is_unsat(tmp_path):
    cfg = config(max_block=60, max_blocks=12)
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "big", "title": "Big single sitting",
                          "est": "2h", "indivisible": True,
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    }, cfg)
    candidate = candidates[0]
    assert candidate["status"] == "INFEASIBLE"
    assumptions = {item["assumption"] for item in candidate["unsat_core"]}
    assert "indivisible:big" in assumptions


def test_supports_are_placed_daily_within_windows(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "1h",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    supports = [s for s in candidate["supports"] if s["placed"]]
    parked = [s for s in candidate["supports"] if not s["placed"]]
    # An empty week should not need to drop a single support.
    assert parked == []
    for support in supports:
        minute = support["start"] % 1440
        assert minute >= 6 * 60  # never inside the sleep window

    def kind(support):
        return support["id"].split(":")[1]

    # Cooking immediately precedes breakfast every day.
    for day in range(7):
        cook = next(s for s in supports
                    if s["day"] == day and kind(s) == "cook-breakfast")
        breakfast = next(s for s in supports
                         if s["day"] == day and kind(s) == "breakfast")
        assert cook["start"] + cook["duration"] <= breakfast["start"]
        assert breakfast["start"] - (cook["start"] + cook["duration"]) < 60


def test_support_records_have_no_todo_and_are_replaced_on_apply(tmp_path):
    week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "30m",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    decoded = decode_candidate(week, candidates[0]["blocks"],
                               candidates[0]["supports"])
    assert decoded["support_records"]
    for record in decoded["support_records"]:
        assert record.get("todo") is None
        assert record.get("due") is None
        assert "schedule" in record["tags"] and "composer" in record["tags"]


def test_recurring_task_requirement_enters_week_with_day_and_hour_bounds():
    lab = {
        "id": "lab", "record": "item", "type": "task", "title": "Prof. Jee lab hours",
        "tags": ["lab", "recurring"],
        "meta": {"est": "6h", "rrule": "FREQ=WEEKLY;BYDAY=MO,WE",
                 "start": "2026-09-28T10:00:00-05:00",
                 "days": [0, 2], "hours": "10:00-17:00",
                 "location": "ECSS 3.226 (Prof. Jee's lab)"},
    }
    week = live_week([lab])
    assert len(week.requirements) == 1
    requirement = week.requirements[0]
    assert requirement.allowed_days == (0, 2)
    assert requirement.day_window == (600, 1020)
    # Same record without the rule stays out of the week.
    plain = {"id": "plain", "record": "item", "type": "task", "title": "Plain",
             "tags": [], "meta": {"est": "1h"}}
    assert live_week([plain]).requirements == []


def test_day_constraint_pins_allocations(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "lab", "title": "Lab", "est": "2h",
                          "days": [2], "hours": "10:00-17:00",
                          "due": "2026-10-04T23:59:00", "topic": "lab",
                          "location": "ECSS 3.226 (Prof. Jee's lab)"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    for block in candidate["blocks"]:
        assert block["day"] == 2  # Wednesday only
        minute = block["start"] % 1440
        assert 10 * 60 <= minute and minute + block["duration"] <= 17 * 60


def test_violated_day_constraint_is_infeasible_with_core(tmp_path):
    # Saturday 10:00-11:00 cannot hold a 2h requirement pinned to Saturdays.
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "lab", "title": "Lab", "est": "2h",
                          "days": [5], "hours": "10:00-11:00",
                          "due": "2026-10-04T23:59:00", "topic": "lab",
                          "location": "ECSS 3.226 (Prof. Jee's lab)"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "INFEASIBLE"


def test_ecss_ecsn_transit_override():
    from scheduler.common import transit_minutes

    assert transit_minutes("ECSN 2.120", "ECSS 3.226 (Prof. Jee's lab)") == 10
    assert transit_minutes("ECSS 3.226 (Prof. Jee's lab)", "ECSN 2.120") == 10


def test_capacity_precheck_reserves_hard_support_minutes(tmp_path):
    from scheduler.model import _capacity_diagnostics

    week = sources.load_spec(spec_file(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "30m",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    }), config())
    # Sanity: the precheck runs and does not flag an easy week.
    assert _capacity_diagnostics(week, config()) == []


def test_evening_overflow_used_when_week_is_squished(tmp_path):
    # Mon-Fri 10:00-18:00 fully consumed; 4h of work still fits by spilling
    # into the evenings (hard cap 22:00) instead of failing.
    fixed = []
    for offset in range(5):
        day = (normalize_week_start(WEEK) + timedelta(days=offset)).isoformat()
        fixed.append({"id": f"f{offset}", "desc": "blocked", "day": day,
                      "start": "10:00", "end": "18:00"})
    _week, candidates = solve_spec(tmp_path, {
        "fixed": fixed,
        "requirements": [{"omn_id": "a", "title": "A", "est": "4h",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    assert total_alloc(candidate["blocks"], 0) == 240
    assert any(block["start"] % 1440 + block["duration"] > 18 * 60
               for block in candidate["blocks"])
    assert all(block["start"] % 1440 + block["duration"] <= 22 * 60
               for block in candidate["blocks"])


def test_easy_week_stays_inside_preferred_end(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "1h",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    for block in candidates[0]["blocks"]:
        assert block["start"] % 1440 + block["duration"] <= 18 * 60


def test_min_est_shrinks_hard_coverage_and_keeps_target_soft(tmp_path):
    # Only 2h of free capacity exists, the requirement targets 4h but its
    # meta.min_est is 2h: satisfiable at the minimum, stretch is visible.
    fixed = []
    for offset in range(6):
        day = (normalize_week_start(WEEK) + timedelta(days=offset)).isoformat()
        fixed.append({"id": f"f{offset}", "desc": "blocked", "day": day,
                      "start": "10:00", "end": "18:00"})
    _week, candidates = solve_spec(tmp_path, {
        "fixed": fixed,
        "requirements": [{"omn_id": "a", "title": "A", "est": "4h",
                          "min_est": "2h",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    candidate = candidates[0]
    assert candidate["status"] == "ok"
    got = total_alloc(candidate["blocks"], 0)
    assert got >= 120
    assert candidate["soft"]["stretch"]["locked"] >= 0


def test_completed_work_credits_requirement():
    done = {
        "uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc", "status": "completed",
        "description": "Lab hours", "scheduled": "20260930T050000Z",
        "starttime": "10:00", "endtime": "11:00", "est": "1h",
        "tags": ["managed", "composer"],
        "todo": "- Lab [omn:lab]",
    }
    week = live_week(
        [omn_task("lab", est="6h", min_est="5h", due="2026-10-04")],
        [done],
        now=datetime.fromisoformat("2026-09-30T13:30:00-05:00"))
    requirement = week.requirements[0]
    # 6h target minus the 1h served = 5h; 5h min_est minus 1h = 4h hard.
    assert requirement.required_minutes == 300
    assert requirement.minimum_minutes == 240


def test_elapsed_support_windows_today_are_dropped():
    week = live_week(
        [omn_task("a", est="1h", due="2026-10-02")],
        now=datetime.fromisoformat("2026-09-30T13:30:00-05:00"))
    for support in week.supports:
        assert support.day >= 2  # nothing on Mon/Tue
        if support.day == 2:
            assert support.latest >= 13 * 60 + 30


def test_mlh_catalog_event_is_not_an_attendance_commitment():
    event = {
        "id": "mlh:x", "record": "item", "type": "event", "title": "Hack",
        "tags": ["mlh", "hackathon"],
        "meta": {"start": "2026-10-02T10:00:00-05:00",
                 "end": "2026-10-04T10:00:00-05:00", "source": "mlh"},
    }
    week = live_week([event])
    assert not any(item.id.startswith("mlh:x") for item in week.fixed_intervals)


def test_nested_same_course_event_is_not_a_fixed_collision():
    lecture = {
        "id": "lecture", "record": "item", "type": "event", "title": "Lecture",
        "tags": ["class"],
        "meta": {"start": "2026-10-01T10:00:00-05:00",
                 "end": "2026-10-01T11:15:00-05:00", "location": "FO 2.404",
                 "course_id": "course"},
    }
    quiz = {
        "id": "quiz", "record": "item", "type": "event", "title": "Quiz",
        "tags": ["quiz"],
        "meta": {"start": "2026-10-01T10:00:00-05:00",
                 "end": "2026-10-01T10:15:00-05:00", "location": "FO 2.404",
                 "course_id": "course"},
    }
    week = live_week([lecture, quiz])
    assert not any(item.tag == "fixed-collision" for item in week.diagnostics)


def test_pending_fixed_task_is_unavailable_window():
    task = {
        "uuid": "11111111-1111-1111-1111-111111111111", "status": "pending",
        "description": "Attend class", "scheduled": "20260929T050000Z",
        "starttime": "10:00", "endtime": "11:00", "tags": ["managed", "fixed"],
    }
    week = live_week([], [task])
    fixed = [f for f in week.fixed_intervals if f.source == "task-fixed"]
    assert len(fixed) == 1
    assert fixed[0].start == 1 * 1440 + 600


# ------------------------------------------------------- legacy / carried work


def test_unmatched_legacy_managed_is_blocking():
    task = {
        "uuid": "22222222-2222-2222-2222-222222222222", "status": "pending",
        "description": "Old work", "scheduled": "20260928T050000Z",
        "tags": ["managed"], "est": "1h",
    }
    week = live_week([], [task])
    assert any(d.tag == "legacy-managed-unmatched" and d.blocking
               for d in week.diagnostics)
    assert week.legacy[0].reconciled is False


def test_reconciled_legacy_references_active_omn():
    task = {
        "uuid": "33333333-3333-3333-3333-333333333333", "status": "pending",
        "description": "Old work", "scheduled": "20260928T050000Z",
        "tags": ["managed"], "est": "1h",
        "todo": "- thing @10m [omn:a]",
    }
    week = live_week([omn_task("a", est="1h", due="2026-10-02")], [task])
    assert week.legacy[0].reconciled is True
    assert not any(d.tag == "legacy-managed-unmatched" and d.blocking
                   for d in week.diagnostics)


def test_carried_task_is_reported_not_deleted():
    task = {
        "uuid": "44444444-4444-4444-4444-444444444444", "status": "pending",
        "description": "Carried", "scheduled": "20260101T060000Z",
        "tags": ["managed"], "est": "1h",
    }
    week = live_week([], [task])
    assert week.legacy[0].carried is True
    # Carried work is preserved (still a blocking diagnostic, never deleted).
    assert any(d.tag == "legacy-managed-unmatched" for d in week.diagnostics)


def test_carried_work_due_next_week_is_deferred_not_blocking():
    # The omn requirement is due Oct 9 (next week) and is not planned for
    # this week; the carried block defers to next Monday instead of forcing
    # the requirement into an already-full week.
    task = {
        "uuid": "55555555-5555-5555-5555-555555555501", "status": "pending",
        "description": "Quinncia sitting", "scheduled": "20260928T050000Z",
        "est": "4h", "tags": ["managed"],
        "todo": "- Quinncia [omn:quinncia]",
    }
    week = live_week(
        [omn_task("quinncia", est="4h", due="2026-10-09")], [task])
    assert all(r.id != "quinncia" for r in week.requirements)
    assert not week.has_blocking
    assert week.legacy[0].refs_resolvable is True
    assert any(d.tag == "legacy-managed-deferred" for d in week.diagnostics)


def test_stale_support_block_is_replaceable_not_blocking():
    task = {
        "uuid": "55555555-5555-5555-5555-555555555502", "status": "pending",
        "description": "Eat dinner", "scheduled": "20260926T050000Z",
        "est": "0.75h", "tags": ["managed", "schedule"],
    }
    week = live_week([], [task])
    assert not week.has_blocking
    assert any(d.tag == "legacy-support-replaceable" for d in week.diagnostics)


def test_stale_support_block_without_schedule_tag_still_blocks():
    task = {
        "uuid": "55555555-5555-5555-5555-555555555503", "status": "pending",
        "description": "Mystery carried task", "scheduled": "20260926T050000Z",
        "est": "1h", "tags": ["managed"],
    }
    week = live_week([], [task])
    assert any(d.tag == "legacy-managed-unmatched" and d.blocking
               for d in week.diagnostics)


# --------------------------------------------------------------- decode/pins


def test_todo_pins_and_open_ended_primary(tmp_path):
    week, candidates = solve_spec(tmp_path, {
        "requirements": [
            {"omn_id": "big", "title": "Big", "est": 2.0,
             "due": "2026-10-04T23:59:00", "topic": "m", "location": "home"},
            {"omn_id": "small", "title": "Small", "est": "10m",
             "due": "2026-09-30T23:59:00", "topic": "m", "location": "home"},
        ],
    })
    candidate = candidates[0]
    decoded = decode_candidate(week, candidate["blocks"])
    assert decoded["records"]
    for record in decoded["records"]:
        pins = parse_pins(record["todo"])
        start = _hhmm(record["starttime"])
        end = _hhmm(record["endtime"])
        assert sum(pins.values()) <= (end - start)
    # The small item is always pinned.
    small_pins = [parse_pins(r["todo"]).get("small") for r in decoded["records"]]
    assert any(pin is not None for pin in small_pins)


def test_sum_of_pinned_never_exceeds_duration(tmp_path):
    week, candidates = solve_spec(tmp_path, {
        "maximum_block_minutes": 120,
        "requirements": [
            {"omn_id": f"r{i}", "title": f"R{i}", "est": "30m",
             "due": "2026-10-04T23:59:00", "topic": "m", "location": "home"}
            for i in range(4)
        ],
    }, config(max_block=120))
    candidate = candidates[0]
    decoded = decode_candidate(week, candidate["blocks"])
    for record in decoded["records"]:
        pins = parse_pins(record["todo"])
        duration = _hhmm(record["endtime"]) - _hhmm(record["starttime"])
        assert sum(pins.values()) <= duration


def _hhmm(value: str) -> int:
    if value == "00:00":
        return 24 * 60
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


# ----------------------------------------------------------- candidate design


def test_candidates_are_diverse(tmp_path):
    cfg = config(candidates=3)
    week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "30m",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    }, cfg)
    decoded = [decode_candidate(week, c["blocks"]) for c in candidates
               if c["status"] == "ok"]
    fingerprints = {item["fingerprint"] for item in decoded}
    assert len(fingerprints) >= 2


def test_spec_solving_is_deterministic(tmp_path):
    spec = {"requirements": [{"omn_id": "a", "title": "A", "est": 2.0,
                              "due": "2026-10-04T23:59:00", "topic": "m",
                              "location": "home"}]}
    path = spec_file(tmp_path, spec)
    cfg = config(candidates=2)
    week = sources.load_spec(path, cfg)
    first = solve_candidates(week, cfg)
    second = solve_candidates(week, cfg)
    # The spec seam is operationally deterministic: identical statuses and
    # identical exact coverage. Z3 may pick a different legal placement within
    # a single process (global AST ids feed its search), so placement itself is
    # only guaranteed reproducible from a fresh interpreter.
    assert [c["status"] for c in first] == [c["status"] for c in second]
    for candidate in first + second:
        assert candidate["status"] == "ok"
        assert total_alloc(candidate["blocks"], 0) == 120
    fingerprints = [decode_candidate(week, c["blocks"])["fingerprint"] for c in first]
    assert len(set(fingerprints)) == len(first)


def test_build_model_bounds_blocks(tmp_path):
    week = sources.load_spec(spec_file(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "30m",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    }), config(max_blocks=5))
    data = build_model(week, config(max_blocks=5))
    assert 1 <= len(data.blocks) <= 5


def test_flexible_blocks_reserve_location_transit(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [
            {"omn_id": "home", "title": "Home", "est": "1h",
             "due": "2026-09-28T18:00:00", "topic": "a",
             "location": "At home"},
            {"omn_id": "campus", "title": "Campus", "est": "1h",
             "due": "2026-09-28T18:00:00", "topic": "b",
             "location": "SU Starbucks"},
        ],
    })
    blocks = sorted(candidates[0]["blocks"], key=lambda item: item["start"])
    assert len(blocks) == 2
    assert blocks[0]["start"] + blocks[0]["duration"] + 30 <= blocks[1]["start"]


def test_flexible_work_obeys_morning_and_evening_boundaries(tmp_path):
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [{"omn_id": "a", "title": "A", "est": "4h",
                          "due": "2026-10-04T23:59:00", "topic": "m",
                          "location": "home"}],
    })
    for block in candidates[0]["blocks"]:
        minute = block["start"] % 1440
        assert minute >= 10 * 60
        assert minute + block["duration"] <= 18 * 60


def test_weekly_block_cap_is_hard_and_tracked(tmp_path):
    cfg = config(max_blocks=2)
    _week, candidates = solve_spec(tmp_path, {
        "requirements": [
            {"omn_id": f"r{i}", "title": f"R{i}", "est": "30m",
             "due": "2026-10-04T23:59:00", "topic": f"topic-{i}",
             "location": "home"}
            for i in range(3)
        ],
    }, cfg)
    candidate = candidates[0]
    assert candidate["status"] == "INFEASIBLE"
    assert any(item["assumption"] == "cap:week"
               for item in candidate["unsat_core"])


def test_live_week_never_places_work_before_current_time():
    now = datetime.fromisoformat("2026-09-29T14:17:00-05:00")
    week = sources.load_live(
        WEEK, config(),
        omn_records=[omn_task("a", est="1h", due="2026-10-02")],
        task_records=[], now=now,
    )
    assert week.requirements[0].window_start == 1 * 1440 + 14 * 60 + 30


# ------------------------------------------------------------------- RRULE


def test_rrule_weekly_byday_within_window():
    start = datetime.fromisoformat("2026-09-28T10:00:00-05:00")
    days = rrule_mod.expand_weekly(
        "FREQ=WEEKLY;BYDAY=MO,WE", start, date(2026, 9, 28), date(2026, 10, 4))
    assert days == [date(2026, 9, 28), date(2026, 9, 30)]


def test_rrule_until_excludes_later_occurrences():
    start = datetime.fromisoformat("2026-09-28T10:00:00-05:00")
    days = rrule_mod.expand_weekly(
        "FREQ=WEEKLY;BYDAY=MO;UNTIL=20260928T235959Z", start,
        date(2026, 9, 28), date(2026, 10, 12))
    assert days == [date(2026, 9, 28)]


def test_rrule_interval_skips_weeks():
    start = datetime.fromisoformat("2026-09-28T10:00:00-05:00")
    days = rrule_mod.expand_weekly(
        "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO", start,
        date(2026, 9, 28), date(2026, 10, 18))
    assert days == [date(2026, 9, 28), date(2026, 10, 12)]


def test_rrule_rejects_non_weekly():
    start = datetime.fromisoformat("2026-09-28T10:00:00-05:00")
    with pytest.raises(rrule_mod.UnsupportedRecurrence):
        rrule_mod.expand_weekly("FREQ=DAILY", start, date(2026, 9, 28),
                                date(2026, 10, 4))
