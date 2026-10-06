"""Grid plan/show/apply. Native JSON is the lossless deterministic input seam."""
import argparse
import hashlib
import json
from pathlib import Path

from .adapter import digest, load_live
from .decode import decode
from .engine import solve
from .schema import Problem, ceil_slot
from .verify import verify


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    inputs = plan.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--spec", help="native grid-week/v1 JSON input")
    inputs.add_argument("--week", help="read omn and Taskwarrior without modifying them")
    plan.add_argument("--previous", help="earlier grid plan whose prefix must be preserved")
    plan.add_argument("--from-minute", type=int, help="spec reschedule boundary in week-relative minutes; rounded UP")
    plan.add_argument("--work-start-hour", type=int, default=8)
    plan.add_argument("--work-end-hour", type=int, default=24)
    plan.add_argument("--timeout-ms", type=int, default=10000)
    plan.add_argument("--no-optimize", action="store_true")
    plan.add_argument("--out")
    plan.add_argument("--quiet", action="store_true")
    show = commands.add_parser("show")
    show.add_argument("--plan", required=True)
    publish = commands.add_parser("apply")
    publish.add_argument("--plan", required=True)
    publish.add_argument("--yes", action="store_true", help="explicitly authorize Taskwarrior writes")
    publish.add_argument("--replace-legacy", action="store_true", help="adopt pending composer blocks in this week's suffix")
    publish.add_argument("--replace-carried", action="store_true", help="explicitly retire covered pending owned blocks from earlier in this week; never completed/fixed history")
    publish.add_argument("--replace-travel", action="store_true", help="explicitly replace exact source-migrated future legacy trips with colored travel; never fixed attendance/history")
    return root


def load_json(path):
    return json.loads(Path(path).read_text())


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            previous = load_json(args.previous) if args.previous else None
            if previous:
                old_problem = Problem.from_dict(previous["problem"], history_only=True)
                if previous["candidate"].get("status") != "ok" or verify(old_problem, previous["candidate"]):
                    raise ValueError("previous plan has no valid grid certificate")
            if args.spec:
                spec_data = load_json(args.spec)
                problem = Problem.from_dict(spec_data)
                problem.source = "spec"  # a saved live snapshot is still a dry-run input
                problem.metadata["spec_path"] = str(Path(args.spec).resolve())
                problem.metadata["spec_digest"] = hashlib.sha256(json.dumps(spec_data, sort_keys=True).encode()).hexdigest()
                if args.from_minute is not None:
                    if args.from_minute < 0 or args.from_minute > 10080:
                        raise ValueError("from-minute must be in 0..10080")
                    problem.prefix = ceil_slot(args.from_minute)
                if previous:
                    if previous["problem"]["week_start"] != problem.week_start.isoformat():
                        raise ValueError("previous plan belongs to another week")
                    if args.from_minute is None:
                        raise ValueError("spec rescheduling needs --from-minute")
                    problem.previous = previous["candidate"]["grid"]
                    # Historical color identities are stable even when source
                    # requirements disappear; retain them as unavailable keys.
                    from .schema import Color
                    current_keys = {c.key for c in problem.colors}
                    old_palette = {c["key"]: c for c in previous["problem"]["colors"]}
                    for key in set(problem.previous[:problem.prefix]) - current_keys - {"free"}:
                        problem.colors.append(Color(key, "unavailable", location=old_palette[key].get("location", "")))
            else:
                if args.from_minute is not None:
                    raise ValueError("live plans use the system clock, not --from-minute")
                problem = load_live(args.week, work_start=args.work_start_hour,
                                    work_end=args.work_end_hour, previous=previous)
            if previous:
                problem.metadata["sealed_history"] = {
                    "problem": previous["problem"], "candidate": previous["candidate"],
                    "records": previous.get("records", []), "through_cell": problem.prefix}
            candidate = solve(problem, timeout_ms=args.timeout_ms, optimize=not args.no_optimize)
            output = {"schema": "grid-plan/v1", "problem": problem.to_dict(),
                      "candidate": candidate,
                      "records": decode(problem, candidate) if candidate["status"] == "ok" else []}
            text = json.dumps(output, indent=2) + "\n"
            if args.out:
                Path(args.out).write_text(text)
            if not args.quiet:
                print(text, end="")
            return 0 if candidate["status"] == "ok" else 2
        plan = load_json(args.plan)
        if plan.get("schema") != "grid-plan/v1":
            raise ValueError("not a grid plan; interval-v1 plans require the explicit legacy entrypoint")
        problem = Problem.from_dict(plan["problem"])
        candidate = plan["candidate"]
        if args.command == "show":
            print(f"{problem.week_start} | {candidate['status']} | 15-minute grid")
            if candidate["status"] != "ok":
                print(candidate.get("note") or "no certified coloring")
                for issue in candidate.get("capacity_errors", []):
                    name = issue.get("title") or issue.get("color") or "remaining week"
                    day = f" (day {issue['day']})" if "day" in issue else ""
                    print(f"  {name}{day}: needs {issue['required_cells'] * 15}m; available {issue['available_cells'] * 15}m")
                if candidate.get("preparation_error"):
                    print("  " + candidate["preparation_error"])
                return 2
            errors = verify(problem, candidate)
            if errors or plan["records"] != decode(problem, candidate):
                raise ValueError("invalid grid plan certificate")
            for record in plan["records"]:
                print(f"{record['scheduled']} {record['starttime']}-{record['endtime']}  {record['description']} [{record['location']}]")
                for line in record.get("todo", "").splitlines():
                    print("  " + line)
            print(f"{candidate['stats']['seconds']:.3f}s; {candidate['stats']['layout_cuts']} layout cuts; optimization {'exact' if candidate['optimization_exact'] else 'approximate'}")
            return 0
        # Source refresh compares facts, not moving time floors. Time is checked
        # separately immediately before writes. No old model is invoked.
        if problem.source == "live":
            from scheduler.sources import read_omn_export, read_task_export
            current_digest = digest(read_omn_export(), read_task_export())
            if current_digest != problem.metadata.get("source_digest"):
                raise ValueError("source state changed; replan before applying")
        elif problem.metadata.get("spec_path"):
            current_spec = load_json(problem.metadata["spec_path"])
            fresh_digest = hashlib.sha256(json.dumps(current_spec, sort_keys=True).encode()).hexdigest()
            if fresh_digest != problem.metadata.get("spec_digest"):
                raise ValueError("spec changed; replan before applying")
        if problem.source != "live" and args.yes:
            raise ValueError("spec plans are dry-run only; publish a fresh --week plan")
        from .apply import apply
        report = apply(problem, candidate, plan["records"], confirmed=args.yes,
                       replace_legacy=args.replace_legacy, replace_carried=args.replace_carried,
                       replace_travel=args.replace_travel)
        if report.get("applied"):
            try:
                from scheduler.sources import read_task_export

                from .adapter import task_snapshot
                plan["task_receipt"] = task_snapshot(read_task_export(), problem.week_start)
                receipt = Path(args.plan).with_suffix(".receipt.tmp")
                receipt.write_text(json.dumps(plan, indent=2) + "\n")
                receipt.replace(args.plan)
            except (OSError, RuntimeError) as exc:
                report["receipt_error"] = f"schedule applied, but history receipt could not be saved: {exc}"
        print(json.dumps(report, indent=2))
        return 1 if report.get("refused") or report.get("error") or report.get("receipt_error") else 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
