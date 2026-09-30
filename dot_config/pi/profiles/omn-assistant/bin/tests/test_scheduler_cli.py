"""CLI tests for the plan/apply surface and legacy compatibility."""

from __future__ import annotations

import json

from scheduler import cli

WEEK = "2026-09-28"
SPEC = {
    "week_start": WEEK,
    "requirements": [
        {"omn_id": "a", "title": "A", "est": 2.0, "due": "2026-10-04T23:59:00",
         "topic": "m", "location": "home"},
    ],
}


def write_spec(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(SPEC))
    return path


def test_plan_spec_emits_candidates(tmp_path, capsys):
    out = tmp_path / "plan.json"
    rc = cli.main(["plan", "--spec", str(write_spec(tmp_path)), "--week", WEEK,
                   "--candidates", "2", "--out", str(out)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["week_start"] == WEEK
    assert payload["has_blocking_diagnostics"] is False
    assert [c["status"] for c in payload["candidates"]] == ["ok", "ok"]
    assert len({c["fingerprint"] for c in payload["candidates"]}) == 2
    assert json.loads(out.read_text())["candidates"][0]["records"]


def test_plan_requires_week_or_spec(capsys):
    rc = cli.main(["plan"])
    assert rc == 1
    assert "required" in capsys.readouterr().err


def test_legacy_positional_spec(tmp_path, capsys):
    out = tmp_path / "legacy.json"
    rc = cli.main([str(write_spec(tmp_path)), "--out", str(out),
                   "--candidates-per-profile", "1"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["week_start"] == WEEK
    assert len(payload["candidates"]) == 1


def test_apply_requires_plan(tmp_path, capsys):
    rc = cli.main(["apply", "--spec", str(write_spec(tmp_path))])
    assert rc == 1
    assert "--plan" in capsys.readouterr().err


def test_show_renders_candidates_without_llm(tmp_path, capsys):
    spec = write_spec(tmp_path)
    plan = tmp_path / "plan.json"
    assert cli.main(["plan", "--spec", str(spec), "--week", WEEK,
                     "--candidates", "1", "--out", str(plan), "--quiet"]) == 0
    assert capsys.readouterr().out == ""
    rc = cli.main(["show", "--plan", str(plan)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Candidate 0" in out and "Eat lunch" in out
    assert "- A" in out


def test_apply_rejects_stale_plan_without_touching_taskwarrior(tmp_path, capsys):
    spec = write_spec(tmp_path)
    plan = tmp_path / "plan.json"
    assert cli.main(["plan", "--spec", str(spec), "--candidates", "1",
                     "--out", str(plan)]) == 0
    capsys.readouterr()
    changed = dict(SPEC)
    changed["requirements"] = [dict(SPEC["requirements"][0], title="Changed")]
    spec.write_text(json.dumps(changed))
    rc = cli.main(["apply", "--plan", str(plan), "--candidate", "0"])
    assert rc == 1
    assert "stale plan" in capsys.readouterr().out


def test_apply_rejects_bad_candidate_index(tmp_path, capsys):
    spec = write_spec(tmp_path)
    plan = tmp_path / "plan.json"
    assert cli.main(["plan", "--spec", str(spec), "--week", WEEK,
                     "--candidates", "1", "--out", str(plan)]) == 0
    capsys.readouterr()
    rc = cli.main(["apply", "--spec", str(spec), "--plan", str(plan),
                   "--candidate", "7"])
    assert rc == 1
    assert "out of range" in capsys.readouterr().out
