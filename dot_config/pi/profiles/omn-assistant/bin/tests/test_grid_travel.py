"""Explicit travel cells, shared minima, overnight visits and pure decoding."""
from dataclasses import replace
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from grid_scheduler.adapter import completed_credit, load_live
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve
from grid_scheduler.schema import CELLS, TRAVEL, Color, Problem, Reservation
from grid_scheduler.travel import certificate_errors, rules
from grid_scheduler.verify import verify

WEEK = date(2026, 9, 28)


def visits(a=2, b=1, distance=2):
    return Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                         Color("a", "fixed", location="A", travel_before=a, travel_after=a),
                         Color("b", "fixed", location="B", travel_before=b, travel_after=b)],
                   reservations=[Reservation("a", "a", 40 * 15, 42 * 15, "Event A", "A"),
                                 Reservation("b", "b", (42 + distance) * 15, (44 + distance) * 15, "Event B", "B")])


def test_two_cell_and_one_cell_minima_share_maximum_not_sum():
    p = visits()
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and verify(p, c) == []
    assert c["grid"][38:40] == [TRAVEL] * 2
    assert c["grid"][42:44] == [TRAVEL] * 2
    assert c["grid"][46:47] == [TRAVEL]
    assert c["grid"].count(TRAVEL) == 5
    assert c["travel_optimization_exact"]


def test_one_cell_cannot_satisfy_two_cell_requirement():
    assert solve(visits(distance=1), timeout_ms=3000)["status"] == "INFEASIBLE"


def test_more_than_minimum_is_valid_and_uncolored_gap_is_not_travel():
    p = visits(distance=3)
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][42:45] == [TRAVEL] * 3
    broken = list(c["grid"])
    broken[42] = "free"
    assert any("required travel violated" in e for e in certificate_errors(p, broken))


def test_overnight_event_has_only_outer_travel_edges():
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("away", "fixed", location="San Antonio", transport="car",
                            travel_before=20, travel_after=20)],
                reservations=[Reservation("away", "away", 5 * 1440 + 690,
                                          6 * 1440 + 1020, "RowdyHacks", "San Antonio")],
                metadata={"fixed_attendance": [{"reservation": "away", "source": "rowdy"}]})
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][506:526] == [TRAVEL] * 20  # Sat 06:30–11:30
    assert c["grid"][644:664] == [TRAVEL] * 20  # Sun 17:00–22:00
    assert c["grid"][575:577] == ["away", "away"]  # midnight is not a fresh visit
    rows = [r for r in decode(p, c) if "travel" in r["tags"]]
    assert rows[0]["description"] == "Drive to RowdyHacks"
    assert rows[0]["location"] == "At home → San Antonio"
    assert rows[1]["description"] == "Drive home"
    assert rows[1]["location"] == "San Antonio → At home"
    assert not any(r["description"].startswith("Attend Drive") for r in rows)


def test_prefix_is_not_repainted_and_past_arrival_is_not_recreated():
    p = visits()
    previous = ["free"] * CELLS
    previous[40:42] = ["a"] * 2
    p.prefix, p.previous = 41, previous
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and c["grid"][:41] == previous[:41]
    assert c["grid"][38:40] == ["free"] * 2
    assert c["grid"][42:44] == [TRAVEL] * 2


def test_missing_prefix_travel_cannot_be_fabricated_before_future_visit():
    p = visits()
    p.prefix, p.previous = 39, ["free"] * CELLS
    assert solve(p, timeout_ms=3000)["status"] == "INFEASIBLE"


def test_unjustified_idle_travel_is_invalid():
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS)])
    c = solve(p, timeout_ms=3000, optimize=False)
    assert c["status"] == "ok" and TRAVEL not in c["grid"]
    c["grid"][40] = TRAVEL
    assert "unjustified travel run" in certificate_errors(p, c["grid"])


def test_rounding_hidden_fixed_event_still_requires_its_travel():
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("a", "fixed"), Color("b", "fixed", travel_before=1)],
                reservations=[Reservation("a", "a", 600, 603), Reservation("b", "b", 603, 609)])
    assert solve(p, timeout_ms=3000)["status"] == "INFEASIBLE"


def test_overnight_travel_decoding_keeps_the_same_destination():
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("a", "fixed", location="Venue", travel_before=20)],
                reservations=[Reservation("a", "a", 1440 + 180, 1440 + 240, "Event A", "Venue")])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    travel = [r for r in decode(p, c) if "travel" in r["tags"]]
    assert len(travel) == 2
    assert all(r["description"] == "Walk to Venue" for r in travel)
    assert sum(int(r["est"][:-1]) for r in travel) == 300


def test_live_compiler_has_reserved_travel_and_no_pairwise_free_rules():
    record = {"id": "e", "record": "item", "type": "event", "title": "Visit",
              "tags": [], "meta": {"start": "2026-09-28T10:00:00-05:00",
                "end": "2026-09-28T11:00:00-05:00", "location": "Venue",
                "travel_time": {"before": "30m", "after": "15m", "origin": "At home", "mode": "car"}}}
    p = load_live(str(WEEK), now=datetime(2026, 9, 28, tzinfo=ZoneInfo("America/Chicago")),
                  omn_records=[record], task_records=[])
    assert p.gaps == {}
    visit = next(c for c in p.colors if c.kind == "fixed")
    assert (visit.travel_before, visit.travel_after, visit.transport) == (2, 1, "car")
    assert any(c.key == TRAVEL and c.kind == "travel" for c in p.colors)
    assert all(r.buffer_before == r.buffer_after == 0 for r in p.reservations)


def test_travel_never_credits_assignment_work_even_with_its_reference():
    task = {"status": "completed", "scheduled": "20261002T050000Z", "est": "5h",
            "tags": ["managed", "travel"], "todo": "- Drive [omn:assignment]"}
    assert completed_credit([task], WEEK) == {}


def test_replan_midway_through_return_keeps_the_remaining_trip():
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("a", "fixed", location="Venue", travel_after=20)],
                reservations=[Reservation("a", "a", 480, 600, "Event", "Venue")])
    old = solve(p, timeout_ms=3000)
    assert old["status"] == "ok"
    p.prefix, p.previous = 48, old["grid"]  # noon, two hours into a 10:00–15:00 return
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and verify(p, c) == []
    assert c["grid"][48:60] == [TRAVEL] * 12
    assert c["grid"][:48] == old["grid"][:48]


@pytest.mark.parametrize("span", [(-60, 60), (CELLS * 15 - 60, CELLS * 15 + 60)])
def test_cross_week_continuation_is_not_a_new_arrival_or_departure(span):
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("a", "fixed", travel_before=1, travel_after=1)],
                reservations=[Reservation("a", "a", *span)])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and verify(p, c) == []
    assert c["grid"].count(TRAVEL) == 1


def test_deleted_travel_windows_are_not_repainted_or_assignment_cancellation():
    previous = {"problem": {"week_start": str(WEEK), "colors": [], "metadata": {"source_task_snapshot": [{"uuid": "deleted", "status": "pending", "tags": ["travel", "managed"],
        "scheduled": "20261002T050000Z", "starttime": "22:00", "endtime": "23:00", "todo": "- Drive [omn:hw]"}]}},
        "candidate": {"status": "ok", "grid": ["free"] * CELLS}}
    fact = {"id": "hw", "record": "item", "type": "task", "title": "Homework", "tags": [],
            "meta": {"due": "2026-10-02", "est": "1h"}}
    p = load_live(str(WEEK), now=datetime(2026, 9, 28, tzinfo=ZoneInfo("America/Chicago")),
                  omn_records=[fact], task_records=[], previous=previous)
    assert "hw" not in p.metadata["cancelled_ids"]
    assert [472, 476] in [list(w) for w in p.metadata["cancelled_travel_windows"]]
    assert any(i.id == "hw" and i.minimum == 4 for i in p.items)
    p = visits()
    p.metadata["cancelled_travel_windows"] = [[38, 40]]
    assert solve(p, timeout_ms=3000)["status"] == "INFEASIBLE"


@pytest.mark.parametrize("direction", ["after", "before"])
def test_long_gap_routes_use_home_not_the_distant_venue(direction):
    # A full hour of travel is its own prep-worthy item; naming still routes
    # through home rather than pretending a direct venue-to-venue hop.
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("a", "fixed", location="Venue A", transport="car", travel_after=4 if direction == "after" else 0),
                      Color("b", "fixed", location="Venue B", transport="car", travel_before=4 if direction == "before" else 0)],
                reservations=[Reservation("a", "a", 600, 660), Reservation("b", "b", 2040, 2100)])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    trip = next(r for r in decode(p, c) if "travel" in r["tags"])
    if direction == "after":
        assert trip["description"] == "Drive home"
        assert trip["location"] == "Venue A → At home"
    else:
        assert trip["description"] == "Drive to Venue B"
        assert trip["location"] == "At home → Venue B"


def test_shared_travel_preserves_one_car_outing_without_counting_as_idle():
    from grid_scheduler.metrics import group_counts
    from grid_scheduler.schema import Group
    p = Problem(WEEK, [Color(TRAVEL, "travel", maximum=CELLS),
                      Color("a", "fixed", location="Venue A", transport="car", travel_after=2),
                      Color("b", "fixed", location="Venue B", transport="car", travel_before=1)],
                reservations=[Reservation("a", "a", 600, 660), Reservation("b", "b", 690, 750)],
                groups=[Group("car", ("a", "b"), max_free_gap=0, max_runs_per_day=1)])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and verify(p, c) == []
    assert c["grid"][44:46] == [TRAVEL, TRAVEL]
    assert group_counts(p, c["grid"])["car"][0] == 1


def test_invalid_travel_metadata_and_self_recursive_color_are_rejected():
    with pytest.raises(ValueError):
        rules({"travel_time": {"before": "-5h"}}, "Venue")
    with pytest.raises(ValueError):
        rules({"travel_time": {"mode": "teleport"}}, "Venue")
    with pytest.raises(ValueError):
        Problem(WEEK, [replace(Color(TRAVEL, "travel"), travel_before=1)]).validate()
