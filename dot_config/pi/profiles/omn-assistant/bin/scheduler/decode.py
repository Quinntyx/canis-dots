"""Decode a solved model into Taskwarrior-shaped candidate records.

The exact allocation minutes come straight from the solver. Every allocation
is emitted on the block's ``todo`` bullet, pinned with the existing ``@10m``
syntax, except that a single large open-ended primary requirement may be left
unpinned when doing so is unambiguous (it is then the only consumer of the
leftover time). The sum of pinned minutes never exceeds the block duration
because the model guarantees ``sum(alloc) <= duration``.
"""

from __future__ import annotations

from datetime import timedelta

from .common import (
    MINUTES_PER_DAY,
    format_est_minutes,
    minutes_to_hhmm,
)

# Pins below this are always emitted; at/above it the unique largest allocation
# may stay open-ended so the linter can attribute the block remainder to it.
UNPIN_THRESHOLD_MINUTES = 60

IMPERATIVE = {
    "attend", "eat", "complete", "start", "finish", "practice", "cancel",
    "attempt", "check", "renew", "work", "research", "write", "talk",
    "calculate", "set", "download", "sign", "lab", "discuss", "revisit",
    "register", "email", "contact", "buy", "go", "call", "schedule",
    "verify", "apply", "take", "review", "prepare", "read", "study",
    "submit", "plan", "draft", "fix", "build", "install", "reply",
}


def _glance_title(requirements, group) -> str:
    if len(requirements) == 1:
        title = requirements[0].title.strip()
    else:
        title = group[0].strip()
    if not title:
        title = "scheduled block"
    first = title.split()[0].lower().strip(":")
    if first in IMPERATIVE:
        return title[0].upper() + title[1:]
    return f"Work on {title}"


def _bullet(requirement, minutes: int, pinned: bool) -> str:
    pin = f" @{minutes}m" if pinned else ""
    return f"- {requirement.title.strip()}{pin} [omn:{requirement.id}]"


def _earliest_due(requirements):
    dues = [req.due_local for req in requirements if req.due_local]
    return min(dues) if dues else None


def _support_records(week, supports: list) -> list:
    """Decode placed support windows into Taskwarrior records.

    Support records are tagged ``+managed +schedule +composer`` so they show
    in the calendar and are replaced wholesale on re-apply, but they carry no
    ``todo`` and no ``due`` — they are time scaffolding, not requirements.
    """
    records = []
    for support in supports:
        if not support.get("placed", True):
            continue
        day = week.week_start + timedelta(days=int(support["day"]))
        start = int(support["start"])
        duration = int(support["duration"])
        record = {
            "description": support["description"],
            "scheduled": day.isoformat(),
            "starttime": minutes_to_hhmm(start % MINUTES_PER_DAY),
            "endtime": minutes_to_hhmm(start % MINUTES_PER_DAY + duration),
            "location": support.get("location") or "At home",
            "transport": "no-car",
            "est": format_est_minutes(duration),
            "tags": ["managed", "schedule", "composer"],
        }
        records.append(record)
    return records


def decode_candidate(week, blocks: list, supports: list | None = None) -> dict:
    """Turn model block dicts into candidate records + summaries."""
    records = []
    summaries = []
    for block in sorted(blocks, key=lambda item: (item["start"], item["group"])):
        allocations = {int(r): int(m) for r, m in block["allocations"].items()
                       if int(m) > 0}
        if not allocations:
            continue
        ordered = sorted(allocations.items(), key=lambda pair: (-pair[1], pair[0]))
        requirements = [week.requirements[r] for r, _ in ordered]
        primary_index, primary_minutes = ordered[0]

        duration = int(block["duration"])
        other_minutes = sum(minutes for index, minutes in ordered
                            if index != primary_index)
        open_ended = (
            primary_minutes >= UNPIN_THRESHOLD_MINUTES
            and sum(1 for _, minutes in ordered if minutes == primary_minutes) == 1
            and primary_minutes == duration - other_minutes
        )
        bullets = []
        for index, minutes in ordered:
            pinned = not (open_ended and index == primary_index)
            bullets.append(_bullet(week.requirements[index], minutes, pinned))

        start = int(block["start"])
        day = week.week_start + timedelta(days=start // MINUTES_PER_DAY)
        minute_of_day = start % MINUTES_PER_DAY
        group = (block["group"][0], block["group"][1])
        transport = block["group"][2] if len(block["group"]) > 2 else "no-car"
        due = _earliest_due(requirements)
        record = {
            "description": _glance_title(requirements, group),
            "scheduled": day.isoformat(),
            "starttime": minutes_to_hhmm(minute_of_day),
            "endtime": minutes_to_hhmm(minute_of_day + duration),
            "location": group[1],
            "transport": transport,
            "est": format_est_minutes(duration),
            "todo": "\n".join(bullets),
            "tags": ["managed", "composer"],
        }
        travel_values = [req.travel for req in requirements if req.travel]
        if travel_values:
            record["travel"] = travel_values[0]
        if due:
            record["due"] = due
        records.append(record)
        summaries.append({
            "group": list(group),
            "transport": transport,
            "day": day.isoformat(),
            "start_minute": start,
            "start": minutes_to_hhmm(minute_of_day),
            "end": minutes_to_hhmm(minute_of_day + duration),
            "duration_minutes": duration,
            "allocations": [
                {"omn_id": week.requirements[index].id, "minutes": minutes}
                for index, minutes in ordered
            ],
        })
    return {
        "records": records,
        "supports": [support for support in (supports or [])
                     if support.get("placed", True)],
        "support_records": _support_records(week, supports or []),
        "blocks": summaries,
        "fingerprint": fingerprint(blocks),
    }


def fingerprint(blocks: list, supports: list | None = None) -> str:
    parts = sorted(
        f"{'@'.join(str(part) for part in block['group'])}:"
        f"{block['start']}:{block['duration']}"
        for block in blocks
    )
    for support in supports or []:
        if support.get("placed", True):
            parts = sorted(parts + [
                f"support:{support['id']}:{support['start']}:{support['duration']}"])
    return "|".join(parts)
