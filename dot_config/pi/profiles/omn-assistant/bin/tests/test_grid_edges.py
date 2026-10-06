import itertools
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from test_grid_scheduler import FakeTasks, one

from grid_scheduler.adapter import load_live, task_date
from grid_scheduler.apply import apply
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve
from grid_scheduler.layout import eligible, pack_color, topology_valid
from grid_scheduler.schema import Color, Item, Reservation


def test_exact_cutoff_includes_seconds():
    for second, expected in ((0, 3 * 96 + 60), (1, 3 * 96 + 61)):
        p = load_live("2026-09-28", now=datetime(2026, 10, 1, 15, 0, second, tzinfo=ZoneInfo("America/Chicago")),
                      omn_records=[], task_records=[])
        assert p.prefix == expected


def test_task_dates_are_local_not_utc_date():
    assert task_date({"scheduled": "20260929T010000Z"}) == date(2026, 9, 28)
    assert task_date({"scheduled": "2026-09-28"}) == date(2026, 9, 28)


def test_adjacent_exact_reservations_can_share_rounding_envelope():
    p = one(minimum=1, windows=((40, 50),), extra_colors=[Color("a", "fixed"), Color("b", "fixed")],
            reservations=[Reservation("a", "a", 600, 607), Reservation("b", "b", 608, 615)])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok" and c["runs"][0]["start"] == 41


def test_cross_week_reservations_preserve_exact_authority_and_clip_occupancy():
    p = one(minimum=1, extra_colors=[Color("away", "fixed")],
            reservations=[Reservation("a", "away", -60, 600), Reservation("b", "away", 10000, 10100)])
    c = solve(p, timeout_ms=3000)
    assert c["status"] == "ok"
    assert c["grid"][0] == "away" and c["grid"][-1] == "away"
    assert p.reservations[0].start_minute == -60


def test_dst_weeks_fail_explicitly():
    p = one()
    p.week_start = date(2026, 10, 26)
    with pytest.raises(ValueError, match="DST-transition"):
        solve(p)


def test_zero_minimum_optional_item_does_not_force_work():
    p = one(minimum=0, maximum=4)
    c = solve(p, timeout_ms=3000)
    # Optional work is never *required*: capacity errors must stay silent. It
    # may still be painted to fill idle capacity the objective now charges for.
    assert c["status"] == "ok"
    assert all(rid == "a" for rid in c["owners"].values())


def test_layout_deadline_is_unknown_not_invalid():
    # Flow creates A in both disjoint chunks; exact whole-item search is needed.
    items = [Item("a", "A", "c", 2, 2, ((0, 5),), indivisible=True),
             Item("b", "B", "c", 1, 1, ((0, 5),))]
    result = pack_color("c", items, {0, 2, 4}, time.monotonic() - 1)
    assert result.status == "unknown"


def test_packing_matches_exhaustive_owners_with_topology():
    windows = [((0, 4),), ((0, 2), (3, 5)), ((1, 5),)]
    cells = {0, 1, 3, 4}
    for wa, wb, whole_a, whole_b in itertools.product(windows, windows, (False, True), (False, True)):
        items = [Item("a", "A", "c", 2, 2, wa, indivisible=whole_a, min_piece=2),
                 Item("b", "B", "c", 2, 2, wb, indivisible=whole_b, min_piece=1)]
        brute = False
        for values in itertools.product("ab", repeat=4):
            owners = dict(zip(sorted(cells), values))
            if values.count("a") != 2 or values.count("b") != 2:
                continue
            if not all(cell in eligible(items[0 if rid == "a" else 1].windows) for cell, rid in owners.items()):
                continue
            brute |= topology_valid(items, owners)
        result = pack_color("c", items, cells, time.monotonic() + 2)
        assert (result.status == "ok") == brute


def test_minimum_piece_can_continue_directly_across_midnight():
    item = Item("a", "A", "c", 4, 4, ((94, 98),), min_piece=2)
    result = pack_color("c", [item], {94, 95, 96, 97}, time.monotonic() + 2)
    assert result.status == "ok"


def test_layout_decode_pins_remain_chronological_even_when_item_repeats():
    p = one(minimum=4, windows=((40, 44),))
    p.items = [Item("a", "Email Alice", "work", 2, 2, ((40, 44),)),
               Item("b", "Email Bob", "work", 2, 2, ((40, 44),))]
    c = solve(p, timeout_ms=3000)
    c["owners"] = {"40": "a", "41": "b", "42": "a", "43": "b"}
    record = decode(p, c)[0]
    assert record["todo"].splitlines() == ["- Email Alice @15m [omn:a]", "- Email Bob @15m [omn:b]",
                                          "- Email Alice @15m [omn:a]", "- Email Bob @15m [omn:b]"]


def test_decode_never_slices_whole_item_at_other_items_window():
    p = one(minimum=6, windows=((40, 46),))
    p.items = [Item("early", "Early", "work", 2, 2, ((40, 42),)),
               Item("whole", "Whole", "work", 4, 4, ((40, 46),), indivisible=True)]
    c = solve(p, timeout_ms=3000)
    r = decode(p, c)
    assert [x["est"] for x in r] == ["30m", "60m"]


def test_due_roundtrip_failure_rolls_back_adds_without_deleting_old():
    p = one()
    p.items[0] = Item("a", "Email Alice", "work", 4, 4, ((40, 60),), due="2026-09-28T16:00:00-05:00")
    c = solve(p, timeout_ms=3000)
    class BadDue(FakeTasks):
        def add(self, record):
            uuid = super().add(record)
            self.tasks[-1].pop("due", None)
            return uuid
    old = {"uuid": "old", "status": "pending", "tags": ["managed", "composer", "grid-2026-09-28"],
           "scheduled": "2026-09-28", "starttime": "10:00", "endtime": "11:00",
           "todo": "- Email Alice @60m [omn:a]", "est": "60m"}
    tw = BadDue([old])
    report = apply(p, c, decode(p, c), confirmed=True, taskwarrior=tw, post_publish=False)
    assert report["error"] and {x["uuid"] for x in tw.tasks} == {"old"}


def test_hidden_fixed_overlay_transition_is_rejected():
    p = one(minimum=1, windows=((44, 50),),
            extra_colors=[Color("a", "fixed", travel_after=1), Color("b", "fixed", travel_before=1),
                          Color("travel", "travel", maximum=672)],
            reservations=[Reservation("a", "a", 600, 607), Reservation("b", "b", 608, 615)])
    result = solve(p, timeout_ms=1000)
    assert result["status"] == "INFEASIBLE"
    assert "fixed transition travel" in result["preparation_error"]


def test_cross_week_away_event_and_overnight_task_are_reserved():
    now = datetime(2026, 9, 28, 0, 0, tzinfo=ZoneInfo("America/Chicago"))
    event = {"id": "away", "type": "event", "title": "Away", "meta": {
        "start": "2026-09-27T12:00:00-05:00", "end": "2026-09-29T12:00:00-05:00",
        "location": "Away"}}
    p = load_live("2026-09-28", now=now, omn_records=[event], task_records=[])
    overlays = [r for r in p.reservations if r.id.startswith("away@")]
    assert [(r.start_minute, r.end_minute) for r in overlays] == [(-720, 1440), (1440, 2160)]
    assert len({r.color for r in overlays}) == 1  # one continuous occurrence, not a new midnight arrival
    overnight = {"uuid": "night", "status": "pending", "tags": ["fixed"],
                 "scheduled": "2026-09-27", "starttime": "22:00", "endtime": "07:00"}
    p = load_live("2026-09-28", now=now, omn_records=[], task_records=[overnight])
    overlay = next(r for r in p.reservations if r.id == "task:night")
    assert (overlay.start_minute, overlay.end_minute) == (-120, 420)


def test_declared_maximum_rounds_down_and_empty_range_is_refused():
    now = datetime(2026, 9, 28, tzinfo=ZoneInfo("America/Chicago"))
    record = {"id": "range", "type": "task", "title": "Email Alice", "meta": {
        "est": "15m", "min_est": "15m", "max_est": "20m", "due": "2026-09-30T23:59:00-05:00"}}
    p = load_live("2026-09-28", now=now, omn_records=[record], task_records=[])
    assert (p.items[0].minimum, p.items[0].maximum) == (1, 1)
    record["meta"].update(est="20m", min_est="20m", max_est="20m")
    with pytest.raises(ValueError, match="empty quarter-hour amount range"):
        load_live("2026-09-28", now=now, omn_records=[record], task_records=[])


def test_adoption_preserves_deferred_and_mixed_reference_work():
    p = one(minimum=4, windows=((40, 44),))
    c = solve(p, timeout_ms=3000)
    deferred = {"uuid": "deferred", "status": "pending", "tags": ["managed", "composer"],
                "scheduled": "2026-09-28", "starttime": "15:00", "endtime": "16:00",
                "todo": "- Later project @60m [omn:next-week]"}
    fake = FakeTasks([deferred])
    report = apply(p, c, decode(p, c), confirmed=True, replace_legacy=True,
                   taskwarrior=fake, post_publish=False)
    assert report["applied"] and report["deleted"] == []
    assert "deferred" in report["protected"]
    mixed = {**deferred, "uuid": "mixed", "starttime": "10:00", "endtime": "11:00",
             "todo": "- Email @30m [omn:a]\n- Later project @30m [omn:next-week]"}
    fake = FakeTasks([mixed])
    report = apply(p, c, decode(p, c), confirmed=True, replace_legacy=True,
                   taskwarrior=fake, post_publish=False)
    assert report["refused"] and fake.calls == []


def test_overnight_protected_span_and_completed_fixed_authority():
    from grid_scheduler.apply import task_span
    p = one()
    t = {"uuid": "fixed", "status": "completed", "tags": ["fixed"],
         "scheduled": "2026-09-28", "starttime": "23:00", "endtime": "01:00"}
    assert task_span(t, p) == (1380, 1500)
    t.update(starttime="10:00", endtime="11:00")
    now = datetime(2026, 9, 28, tzinfo=ZoneInfo("America/Chicago"))
    live = load_live("2026-09-28", now=now, omn_records=[], task_records=[t])
    assert any(r.id == "task:fixed" and (r.start_minute, r.end_minute) == (600, 660)
               for r in live.reservations)


def test_deleted_action_is_not_recreated_and_apply_receipt_prevents_false_cancellation():
    now = datetime(2026, 9, 28, tzinfo=ZoneInfo("America/Chicago"))
    record = {"id": "email", "type": "task", "title": "Email Alice", "meta": {
        "est": "15m", "due": "2026-09-30T17:00:00-05:00"}}
    old = {"uuid": "old", "status": "pending", "tags": ["managed", "composer"],
           "scheduled": "2026-09-28", "starttime": "10:00", "endtime": "10:15",
           "est": "15m", "todo": "- Email Alice @15m [omn:email]"}
    p = load_live("2026-09-28", now=now, omn_records=[record], task_records=[old])
    c = solve(p, timeout_ms=3000, optimize=False)
    assert c["status"] == "ok"
    previous = {"problem": p.to_dict(), "candidate": c}
    after = load_live("2026-09-28", now=now, omn_records=[record], task_records=[], previous=previous)
    assert after.items == [] and after.metadata["cancelled_ids"] == ["email"]
    # The same intentional deletion remains excluded in the next revision.
    after_previous = {"problem": after.to_dict(), "candidate": c}
    after = load_live("2026-09-28", now=now, omn_records=[record], task_records=[], previous=after_previous)
    assert after.items == []
    # Successful publication records replacement UUIDs, not old engine-deleted UUIDs.
    replacement = {**old, "uuid": "new"}
    previous["task_receipt"] = [replacement]
    after = load_live("2026-09-28", now=now, omn_records=[record], task_records=[replacement], previous=previous)
    assert [i.id for i in after.items] == ["email"]
