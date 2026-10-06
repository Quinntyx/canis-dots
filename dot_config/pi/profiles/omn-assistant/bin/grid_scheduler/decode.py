"""Contiguous color runs -> time blocks -> imperative todo records."""
from collections import Counter
from datetime import timedelta
from itertools import pairwise

from .schema import ROWS, STEP, Problem, eligible
from .verify import verify


def clock(minutes: int) -> str:
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


def decode(problem: Problem, candidate: dict) -> list[dict]:
    errors = verify(problem, candidate)
    if errors:
        raise ValueError("invalid candidate: " + "; ".join(errors))
    owners = {int(cell): rid for cell, rid in candidate["owners"].items()}
    items = {i.id: i for i in problem.items}
    colors = {c.key: c for c in problem.colors}
    records = []
    for run in candidate["runs"]:
        color = colors[run["color"]]
        start, end = run["start"], run["end"]
        if color.kind == "travel":
            # A travel block shorter than an hour needs no leave-early prep:
            # its time stays reserved on the grid but is not its own item.
            if end - start < 4:
                continue
            from .travel import record
            records.append(record(problem, candidate["grid"], start, end, owners))
            continue
        spans = [(start, end)]
        if color.kind == "work":
            included = {owners[c] for c in range(start, end)}
            # Preserve long semantic runs. If a todo cannot truthfully belong
            # to the entire run, emit owner pieces instead. Never slice an
            # indivisible item at somebody else's deadline boundary.
            if any(not set(range(start, end)) <= eligible(items[rid].windows) for rid in included):
                boundaries = [start] + [c for c in range(start + 1, end) if owners[c] != owners[c - 1]] + [end]
                spans = list(pairwise(boundaries))
        for a, b in spans:
            day = problem.week_start + timedelta(days=a // ROWS)
            record = {"description": color.topic or color.key,
                      "scheduled": day.isoformat(), "starttime": clock(a % ROWS * STEP),
                      "endtime": clock(b % ROWS * STEP), "location": color.location,
                      "transport": color.transport, "est": f"{(b - a) * STEP}m",
                      "tags": ["managed", "composer", "grid", "grid-" + problem.week_start.isoformat()]}
            if color.kind == "support":
                record["tags"].append("schedule")
            else:
                counts = Counter(owners[c] for c in range(a, b))
                ordered_ids = sorted(counts, key=lambda rid: min(c for c in range(a, b) if owners[c] == rid))
                record["description"] = (items[ordered_ids[0]].title if len(counts) == 1
                                          else "Work on " + (color.topic or "scheduled tasks"))
                boundaries = [a] + [c for c in range(a + 1, b) if owners[c] != owners[c - 1]] + [b]
                record["todo"] = "\n".join(
                    f"- {items[owners[x]].title} @{(y - x) * STEP}m [omn:{items[owners[x]].reference or owners[x]}]"
                    for x, y in pairwise(boundaries))
                dues = [items[rid].due for rid in counts if items[rid].due]
                if dues:
                    record["due"] = min(dues)
                travel = [items[rid].travel for rid in ordered_ids if items[rid].travel]
                if travel:
                    record["travel"] = travel[0]
                # Between-class gaps with a direct transfer keep the user on
                # campus: work painted there happens at the standing
                # between-class spot, never "at home".
                if record.get("location") in ("", "At home"):
                    from .travel import transfers
                    for t in transfers(problem):
                        lo, hi, slots = t["after_edge"], t["before_edge"], t["slots"]
                        if lo <= a and b <= hi - slots and all(
                                candidate["grid"][i] == "travel" for i in range(hi - slots, hi)):
                            record["location"] = "SU Starbucks"
                            break
            records.append(record)
    # Naming is a regular-code layout decision; it cannot affect feasibility.
    by_item = {}
    for record in records:
        todo = record.get("todo", "")
        refs = [i.id for i in problem.items if f"[omn:{i.reference or i.id}]" in todo]
        if len(refs) == 1:
            by_item.setdefault(refs[0], []).append(record)
    verbs = {"work", "read", "write", "review", "study", "finish", "start", "complete", "register", "email", "send", "reply", "practice", "prepare", "submit", "check", "attend", "go", "buy", "call", "cancel"}
    for rid, related in by_item.items():
        for n, record in enumerate(related):
            title = items[rid].title
            if len(related) > 1:
                verb = "Start" if n == 0 else "Finish" if n == len(related) - 1 else "Continue"
                record["description"] = verb + " " + title
            elif title.split()[0].lower().strip(":") not in verbs:
                record["description"] = "Work on " + title
    if problem.metadata.get("fixed_attendance"):
        from .facts import attendance_records
        records.extend(attendance_records(problem))
    return sorted(records, key=lambda r: (r["scheduled"], r["starttime"], r["description"]))
