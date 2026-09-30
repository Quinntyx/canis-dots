"""``schedule_composer.py`` entry point: ``plan`` and ``apply`` subcommands.

Normal use::

    schedule_composer.py plan --week 2026-09-28 --candidates 3 --out plan.json
    schedule_composer.py apply --plan plan.json --candidate 0 --yes

``--spec FILE`` selects the deterministic JSON seam used by tests/debugging.
The historic positional-spec invocation is still accepted for compatibility.
"""

from __future__ import annotations

import argparse
import json
import sys

from .apply import Taskwarrior, apply_candidate
from .common import ComposerConfig
from .decode import decode_candidate
from .model import solve_candidates
from .sources import load_live, load_spec


def build_config(args) -> ComposerConfig:
    config = ComposerConfig()
    for name in ("step", "min_block", "max_block", "day_cap", "wake_hour",
                 "work_start_hour", "work_end_hour", "max_blocks", "candidates"):
        value = getattr(args, name, None)
        if value is not None:
            setattr(config, name, int(value))
    timeout = getattr(args, "timeout_ms", None)
    if timeout is not None:
        config.solver_timeout_ms = int(timeout)
    seed = getattr(args, "seed", None)
    if seed is not None:
        config.seed = int(seed)
    return config


def _load_week(args, config):
    if getattr(args, "spec", None):
        return load_spec(args.spec, config)
    return load_live(args.week, config)


def command_plan(args) -> int:
    config = build_config(args)
    week = _load_week(args, config)
    candidates = solve_candidates(week, config)
    output_candidates = []
    for candidate in candidates:
        if candidate.get("status") == "ok":
            decoded = decode_candidate(week, candidate["blocks"])
            record = {
                "candidate_index": candidate["candidate_index"],
                "status": candidate["status"],
                "optimization_exact": candidate["optimization_exact"],
                "ladder_profile": candidate["ladder_profile"],
                "bucket_order": candidate["bucket_order"],
                "soft": candidate["soft"],
                "fingerprint": decoded["fingerprint"],
                "records": decoded["records"],
                "blocks": decoded["blocks"],
                "unsat_core": [],
                "diagnostics": candidate["diagnostics"],
            }
        else:
            record = {
                "candidate_index": candidate.get("candidate_index", 0),
                "status": candidate.get("status"),
                "optimization_exact": False,
                "ladder_profile": candidate.get("ladder_profile"),
                "bucket_order": candidate.get("bucket_order"),
                "soft": candidate.get("soft", {}),
                "fingerprint": None,
                "records": [],
                "blocks": [],
                "unsat_core": candidate.get("unsat_core", []),
                "note": candidate.get("note"),
                "diagnostics": candidate.get("diagnostics", []),
            }
        output_candidates.append(record)

    output = {
        "week_start": week.week_start.isoformat(),
        "source": week.source,
        "config": {
            "step_minutes": config.step,
            "minimum_block_minutes": config.min_block,
            "maximum_block_minutes": config.max_block,
            "blocks_per_day_cap": config.day_cap,
            "wake_hour": config.wake_hour,
            "work_start_hour": config.work_start_hour,
            "work_end_hour": config.work_end_hour,
            "max_blocks": config.max_blocks,
            "candidates": config.candidates,
            "solver_timeout_ms": config.solver_timeout_ms,
        },
        "week": week.to_dict(),
        "has_blocking_diagnostics": week.has_blocking,
        "diagnostics": [item.to_dict() for item in week.diagnostics],
        "candidates": output_candidates,
    }
    text = json.dumps(output, indent=2, sort_keys=False)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text + "\n")
    print(text)
    return 0


def command_apply(args) -> int:
    with open(args.plan) as handle:
        plan = json.load(handle)
    if not getattr(args, "week", None):
        args.week = plan.get("week_start")
    if not getattr(args, "spec", None) and plan.get("source") == "spec":
        args.spec = ((plan.get("week") or {}).get("metadata") or {}).get("spec_path")
    candidates = plan.get("candidates", [])
    if not candidates:
        print(json.dumps({"error": "plan contains no candidates"}, indent=2))
        return 1
    if args.candidate < 0 or args.candidate >= len(candidates):
        print(json.dumps({"error": f"candidate index {args.candidate} out of range"},
                         indent=2))
        return 1
    candidate = candidates[args.candidate]

    config = ComposerConfig()
    stored = plan.get("config", {})
    mapping = {
        "step": "step_minutes",
        "min_block": "minimum_block_minutes",
        "max_block": "maximum_block_minutes",
        "day_cap": "blocks_per_day_cap",
        "wake_hour": "wake_hour",
        "work_start_hour": "work_start_hour",
        "work_end_hour": "work_end_hour",
        "max_blocks": "max_blocks",
    }
    for attr, key in mapping.items():
        if key in stored:
            setattr(config, attr, int(stored[key]))
    for name in ("step", "min_block", "max_block", "day_cap", "wake_hour",
                 "work_start_hour", "work_end_hour", "max_blocks"):
        value = getattr(args, name, None)
        if value is not None:
            setattr(config, name, int(value))

    week = _load_week(args, config)
    planned_week = plan.get("week") or {}
    current_week = week.to_dict()
    snapshot_fields = ("requirements", "fixed_intervals", "legacy_managed_tasks")
    changed = [name for name in snapshot_fields
               if planned_week.get(name, []) != current_week.get(name, [])]
    if changed:
        print(json.dumps({
            "error": "refusing to apply a stale plan; rerun plan first",
            "changed": changed,
        }, indent=2))
        return 1
    report = apply_candidate(
        week,
        candidate,
        taskwarrior=Taskwarrior(),
        dry_run=not args.yes,
        confirmed=args.yes,
    )
    print(json.dumps(report.to_dict(), indent=2))
    if report.refused or report.error:
        return 1
    return 0


def _add_common(parser):
    parser.add_argument("--spec", help="deterministic JSON spec input (testing seam)")
    parser.add_argument("--week", help="Monday (or any day) of the target week")
    parser.add_argument("--step", type=int, default=None, help="grid minutes")
    parser.add_argument("--min-block", type=int, default=None)
    parser.add_argument("--max-block", type=int, default=None)
    parser.add_argument("--day-cap", type=int, default=None)
    parser.add_argument("--wake-hour", type=int, default=None)
    parser.add_argument("--work-start-hour", type=int, default=None)
    parser.add_argument("--work-end-hour", type=int, default=None)
    parser.add_argument("--max-blocks", type=int, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    plan = subparsers.add_parser("plan", help="propose candidate schedules")
    _add_common(plan)
    plan.add_argument("--candidates", type=int, default=3)
    plan.add_argument("--out", help="write the plan JSON here")
    plan.add_argument("--timeout-ms", type=int, default=15_000)
    plan.add_argument("--seed", type=int, default=11)
    plan.set_defaults(func=command_plan)

    apply_parser = subparsers.add_parser("apply", help="apply a selected candidate")
    _add_common(apply_parser)
    apply_parser.add_argument("--plan", required=False,
                              help="plan JSON from `plan`")
    apply_parser.add_argument("--candidate", type=int, default=0,
                              help="candidate index to apply")
    apply_parser.add_argument("--yes", action="store_true",
                              help="confirm the write; without it, dry-run")
    apply_parser.set_defaults(func=command_apply)
    return parser


def _legacy_plan(argv) -> int:
    """Accept the historic ``schedule_composer.py SPEC.json`` invocation."""
    legacy = argparse.ArgumentParser(prog="schedule_composer.py")
    legacy.add_argument("spec")
    legacy.add_argument("--out")
    legacy.add_argument("--candidates-per-profile", type=int, default=3)
    legacy.add_argument("--seed", type=int, default=11)
    legacy.add_argument("--timeout-ms", type=int, default=15_000)
    args = legacy.parse_args(argv)
    args.command = "plan"
    args.candidates = args.candidates_per_profile
    args.spec = args.spec
    args.week = None
    for name in ("step", "min_block", "max_block", "day_cap", "wake_hour",
                 "work_start_hour", "work_end_hour", "max_blocks"):
        setattr(args, name, None)
    return command_plan(args)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    known = {"plan", "apply"}
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        return _legacy_plan(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    if args.command == "apply" and not getattr(args, "plan", None):
        print("error: apply requires --plan", file=sys.stderr)
        return 1
    if (args.command != "apply" and getattr(args, "spec", None) is None
            and getattr(args, "week", None) is None):
        print("error: one of --week or --spec is required", file=sys.stderr)
        return 1
    return args.func(args)
