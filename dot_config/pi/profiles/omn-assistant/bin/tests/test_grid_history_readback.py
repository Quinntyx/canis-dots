"""Legacy FREE-gap data is read-only history, never a new planning policy."""
from copy import deepcopy

import pytest
from test_grid_scheduler import FakeTasks, one

from grid_scheduler.apply import apply
from grid_scheduler.decode import decode
from grid_scheduler.engine import solve
from grid_scheduler.schema import Color, Problem, Reservation
from grid_scheduler.verify import verify


def old_data():
    p = one(extra_colors=[Color("other", "support", maximum=1)])
    candidate = solve(p, timeout_ms=3000)
    data = p.to_dict()
    data["gaps"] = [{"from": "other", "to": "work", "cells": 2}]
    return p, candidate, data


def test_old_free_gap_spec_is_rejected_but_historical_certificate_can_be_read():
    _, candidate, data = old_data()
    with pytest.raises(ValueError, match="FREE gaps are legacy"):
        Problem.from_dict(data)
    history = Problem.from_dict(data, history_only=True)
    assert verify(history, candidate) == []
    damaged = deepcopy(candidate)
    damaged["grid"][40] = "other"
    assert any("historical transition gap violated" in e for e in verify(history, damaged))


def test_old_reservation_free_buffers_are_history_only_too():
    p = one(extra_colors=[Color("class", "fixed")], reservations=[Reservation("class", "class", 600, 615)])
    c = solve(p, timeout_ms=3000)
    data = p.to_dict()
    data["reservations"][0]["buffer_before"] = 15
    with pytest.raises(ValueError, match="reservation FREE buffers are legacy"):
        Problem.from_dict(data)
    assert verify(Problem.from_dict(data, history_only=True), c) == []


def test_history_cannot_be_solved_or_published_even_with_injected_transport():
    p, candidate, data = old_data()
    history = Problem.from_dict(data, history_only=True)
    with pytest.raises(ValueError, match="historical certificates are read-only"):
        solve(history)
    transport = FakeTasks([])
    with pytest.raises(ValueError, match="historical certificates cannot be published"):
        apply(history, candidate, decode(p, candidate), confirmed=True, taskwarrior=transport, post_publish=False)
    assert transport.calls == []
