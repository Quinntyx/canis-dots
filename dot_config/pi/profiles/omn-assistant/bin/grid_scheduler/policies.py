"""Structured source policies compiled to cell bounds, never guessed from notes."""
from scheduler.common import hhmm_to_minutes, parse_est_minutes

from .schema import STEP, ceil_slot


def support_overrides(records, week_start):
    """Dated, user-authored meal/break exceptions; never alter defaults."""
    from datetime import date

    result = {}
    names = {"cook", "breakfast", "lunch", "break", "dinner"}
    for record in records:
        meta = record.get("meta") or {}
        if meta.get("active") is False:
            continue
        dates = meta.get("support_overrides", {})
        if not isinstance(dates, dict):
            raise TypeError("support_overrides must map ISO dates to support rules")
        for stamp, rules in dates.items():
            day = (date.fromisoformat(stamp) - week_start).days
            if not 0 <= day < 7:
                continue
            if not isinstance(rules, dict):
                raise TypeError("dated support overrides must be objects")
            for name, value in rules.items():
                if name not in names or not isinstance(value, dict):
                    raise ValueError(f"invalid support override: {stamp}/{name}")
                if set(value) - {"waived", "skipped", "hours", "duration", "independent_start"}:
                    raise ValueError(f"unsupported support fields: {stamp}/{name}")
                for flag in ("waived", "skipped", "independent_start"):
                    if flag in value and not isinstance(value[flag], bool):
                        raise TypeError(f"{flag} must be boolean")
                if "duration" in value:
                    minutes = parse_est_minutes(value["duration"])
                    if minutes is None or minutes <= 0 or minutes % 15:
                        raise ValueError("support duration must be positive whole quarter-hours")
                if "hours" in value:
                    parts = str(value["hours"]).split("-")
                    if len(parts) != 2:
                        raise ValueError("support hours must be HH:MM-HH:MM")
                    a, b = (hhmm_to_minutes(v) for v in parts)
                    if not 0 <= a < b <= 1440:
                        raise ValueError("support hours must be an increasing same-day interval")
                key = (day, name)
                if key in result and result[key] != value:
                    raise ValueError(f"conflicting support overrides: {stamp}/{name}")
                result[key] = dict(value)
    return result


def opening_windows(meta, week_start):
    """Explicit researched venue hours: day/date -> [[HH:MM, HH:MM], ...]."""
    values = meta.get("open_hours")
    if values is None:
        return None
    if not isinstance(values, dict):
        raise TypeError("open_hours must be a day/date mapping")
    windows = []
    for key, ranges in values.items():
        from datetime import date
        day = (date.fromisoformat(key) - week_start).days if "-" in str(key) else int(key)
        if not 0 <= day < 7:
            continue
        for start, end in ranges:
            a, b = hhmm_to_minutes(start), hhmm_to_minutes(end)
            if not 0 <= a < b <= 1440:
                raise ValueError("venue hours must be increasing same-day intervals")
            windows.append((day * 96 + ceil_slot(a), day * 96 + b // STEP))
    return sorted(windows)


def intersect_windows(windows, allowed):
    if allowed is None:
        return windows
    return sorted({(max(a, c), min(b, d)) for a, b in windows for c, d in allowed
                   if max(a, c) < min(b, d)})


def daily_bounds(meta, rid, week_start, tasks):
    """Per-semantic-activity day quantities; explicit completion credit only."""
    keys = ("daily_est", "daily_min_est", "daily_max_est")
    if not any(k in meta for k in keys):
        return {}
    from .adapter import completed_credit, task_date
    values = {k: meta.get(k, {}) for k in keys}
    if any(not isinstance(v, dict) for v in values.values()):
        raise TypeError("daily estimates must map weekday 0..6 to durations")
    days = {int(d) for v in values.values() for d in v}
    result = {}
    for day in sorted(days):
        if not 0 <= day < 7:
            raise ValueError("daily estimate weekday must be 0..6")
        def get(key, fallback, day=day):
            value = values[key].get(str(day), values[key].get(day, fallback))
            minutes = parse_est_minutes(value)
            if minutes is None:
                raise ValueError(f"invalid {key}/{day}: {value}")
            return minutes
        exact = values["daily_est"].get(str(day), values["daily_est"].get(day))
        lower = get("daily_min_est", exact)
        upper = get("daily_max_est", exact)
        credit = completed_credit([t for t in tasks if task_date(t) is not None
            and (task_date(t) - week_start).days == day], week_start).get(rid, 0)
        lo = ceil_slot(max(0, lower - credit))
        hi = max(0, upper - credit) // STEP if "daily_max_est" in meta else ceil_slot(max(0, upper - credit))
        if hi < lo:
            raise ValueError(f"empty daily estimate range for {rid}/{day}")
        result[day] = (lo, hi)
    return result
