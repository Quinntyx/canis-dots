"""Travel coloring vocabulary and independent, ordinary-code certificates."""
from .schema import CELLS, TRAVEL, ceil_slot


def rules(meta, location, *, is_class=False):
    from scheduler.common import parse_est_minutes, transit_minutes
    raw = meta.get("travel_time", {})
    if not isinstance(raw, dict) or set(raw) - {"before", "after", "origin", "mode"}:
        raise ValueError("travel_time must contain before/after/origin/mode")
    origin = str(raw.get("origin", "At home"))
    online = any(word in str(location).lower() for word in ("online", "teams", "zoom", "virtual", "remote"))
    default = 0 if online or not location else transit_minutes(origin, location)
    if is_class and not online:
        default = max(default, 30)
    amounts = []
    for side in ("before", "after"):
        value = raw.get(side, meta.get("buffer_" + side, f"{default}m"))
        minutes = parse_est_minutes(value)
        if minutes is None or minutes < 0:
            raise ValueError(f"invalid travel_time.{side}: {value!r}")
        amounts.append(ceil_slot(minutes))
    mode = raw.get("mode", "car" if meta.get("transport_required") else "no-car")
    if mode not in {"car", "no-car"}:
        raise ValueError("travel_time.mode must be car or no-car")
    return (*amounts, origin, mode)


def transfers(problem):
    """Parsed direct-transfer plan between consecutive same-day outings.

    Walking home between two campus commitments wastes up to an hour per
    gap. For each eligible pair the solver either routes directly (venue to
    venue, travel painted immediately before the later event) or takes the
    classic home detour when a home-anchored support block needs the gap.
    """
    return list(problem.metadata.get("travel_transfers", []))


def anchors(problem):
    """Exact fixed overlays can be hidden by adjacent rounding envelopes.

    A continuous same-color reservation is one visit, including over midnight.
    Only true outer edges impose travel; identity is not an SMT variable.
    Edges owned by a direct transfer are excluded: the transfer constraint
    paints either the direct span or both classic spans itself.
    """
    palette = {c.key: c for c in problem.colors}
    owned = set()
    for t in transfers(problem):
        owned.add((t["after_edge"], "after"))
        owned.add((t["before_edge"], "before"))
    for r in problem.reservations:
        color = palette[r.color]
        before_continues = any(s is not r and s.color == r.color and
                               s.start_minute < r.start_minute <= s.end_minute
                               for s in problem.reservations)
        after_continues = any(s is not r and s.color == r.color and
                              s.start_minute <= r.end_minute < s.end_minute
                              for s in problem.reservations)
        start, end = max(0, r.start_minute // 15), min(CELLS, ceil_slot(r.end_minute))
        if color.travel_before and r.start_minute >= 0 and start >= problem.prefix and not before_continues \
                and (start, "before") not in owned:
            yield start, "before", color.travel_before
        if (color.travel_after and r.end_minute <= CELLS * 15
                and end + color.travel_after > problem.prefix and not after_continues) \
                and (end, "after") not in owned:
            yield end, "after", color.travel_after


def certificate_errors(problem, grid):
    palette = {c.key: c for c in problem.colors}
    transfer_edges = set()
    for t in transfers(problem):
        transfer_edges.add((t["after_edge"], "after"))
        transfer_edges.add((t["before_edge"], "before"))
    edges = list(anchors(problem))
    for i, key in enumerate(grid):
        if key == TRAVEL or key not in palette:
            continue
        color = palette[key]
        inherited = i == 0 and any(r.color == key and r.start_minute < 0 < r.end_minute for r in problem.reservations)
        continuing = i + 1 == CELLS and any(r.color == key and r.end_minute > CELLS * 15 for r in problem.reservations)
        if i >= problem.prefix and not inherited and (i == 0 or grid[i - 1] != key) and color.travel_before \
                and (i, "before") not in transfer_edges:
            edges.append((i, "before", color.travel_before))
        if (i + 1 + color.travel_after > problem.prefix and not continuing
                and (i + 1 == CELLS or grid[i + 1] != key) and color.travel_after) \
                and (i + 1, "after") not in transfer_edges:
            edges.append((i + 1, "after", color.travel_after))
    errors = []
    supported = set()
    for t in transfers(problem):
        lo, hi, slots = t["after_edge"], t["before_edge"], t["slots"]
        tcells = range(hi - slots, hi)
        outside = range(lo, hi - slots)
        direct = all(grid[i] == TRAVEL for i in tcells) and all(
            grid[i] != TRAVEL for i in outside if 0 <= i < CELLS)
        if direct:
            # The direct hop IS the transfer's travel; credit it as supported.
            supported.update(tcells)
            for i in outside:
                if 0 <= i < CELLS and any(grid[i] == c.key for c in problem.colors
                                          if c.kind == "support"):
                    errors.append(f"direct-transfer gap polluted at {i}")
        else:
            from_color, to_color = palette[t["from_color"]], palette[t["to_color"]]
            for i in range(lo, lo + from_color.travel_after):
                if 0 <= i < CELLS and grid[i] != TRAVEL:
                    errors.append(f"transfer classic route violated at {i}")
            for i in range(hi - to_color.travel_before, hi):
                if 0 <= i < CELLS and grid[i] != TRAVEL:
                    errors.append(f"transfer classic route violated at {i}")
            # A clean classic route's slivers are the transfer's own travel.
            supported.update(range(lo, lo + from_color.travel_after))
            supported.update(range(hi - to_color.travel_before, hi))
    for edge, side, count in edges:
        cells = range(edge - count, edge) if side == "before" else range(edge, edge + count)
        if any(not 0 <= i < CELLS or grid[i] != TRAVEL for i in cells):
            errors.append(f"required travel violated: {side}/{edge}/{count}")
        seed = edge - 1 if side == "before" else edge
        if 0 <= seed < CELLS and grid[seed] == TRAVEL:
            lo, hi = seed, seed + 1
            while lo and grid[lo - 1] == TRAVEL:
                lo -= 1
            while hi < CELLS and grid[hi] == TRAVEL:
                hi += 1
            supported.update(range(lo, hi))
    if any(grid[i] == TRAVEL and i not in supported for i in range(problem.prefix, CELLS)):
        errors.append("unjustified travel run")
    return errors


def migrated_bindings(records, tasks, week_start):
    """Recognize only exact pending legacy trips explicitly replaced by a visit.

    This is migration evidence, not permission to mutate fixed registrations.
    """
    from scheduler import sources

    from .adapter import task_date
    from .facts import identity
    by_id = {r["id"]: r for r in records}
    result = {}
    for source in records:
        meta = source.get("meta") or {}
        link = meta.get("travel_replaced_by")
        if not link:
            continue
        if not isinstance(link, dict) or link.get("side") not in {"before", "after"}:
            raise ValueError("travel_replaced_by needs event and before/after side")
        event = by_id.get(link.get("event"), {})
        em = event.get("meta") or {}
        if (meta.get("active") is not False or event.get("type") != "event"
                or sources.is_inactive(event)[0] or em.get("rrule") or em.get("cancelled")):
            continue
        side = link["side"]
        a, b = sources._aware(meta["start"]), sources._aware(meta["end"])
        week_begin = sources.datetime.combine(week_start, sources.datetime.min.time(), sources.TZ)
        if b <= week_begin or a >= week_begin + sources.timedelta(days=7):
            continue
        edge = sources._aware(em["start"] if side == "before" else em["end"])
        count = rules(em, em.get("location"))[0 if side == "before" else 1]
        expected = (edge - sources.timedelta(minutes=count * 15), edge) if side == "before" else (
            edge, edge + sources.timedelta(minutes=count * 15))
        if (a, b) != expected:
            raise ValueError(f"{source['id']}: legacy trip does not match declared travel")
        for task in tasks:
            day = task_date(task)
            if (task.get("status") != "pending" or "fixed" not in task.get("tags", [])
                    or "managed" not in task.get("tags", []) or day is None):
                continue
            if not 0 <= (day - week_start).days < 7:
                continue
            from scheduler.common import hhmm_to_minutes
            start = sources.datetime.combine(day, sources.datetime.min.time(), sources.TZ) + sources.timedelta(
                minutes=hhmm_to_minutes(task.get("starttime", "00:00")))
            finish = sources.datetime.combine(day, sources.datetime.min.time(), sources.TZ) + sources.timedelta(
                minutes=hhmm_to_minutes(task.get("endtime", "00:00")))
            if finish <= start:
                finish += sources.timedelta(days=1)
            if (start, finish) == (a, b) and (source["id"] in sources._todo_refs(task)
                    or (not sources._todo_refs(task) and identity(task.get("description")) == identity(source.get("title")))):
                result[task["uuid"]] = {"source": source["id"], "event": event["id"], "side": side,
                    "span": [(a.date() - week_start).days * 1440 + a.hour * 60 + a.minute,
                             (b.date() - week_start).days * 1440 + b.hour * 60 + b.minute]}
    return result


def record(problem, grid, start, end, owners):
    """A travel run belongs to its destination; return falls back to origin."""
    from datetime import timedelta

    from .decode import clock
    from .schema import ROWS, STEP
    for t in transfers(problem):
        lo, hi, slots = t["after_edge"], t["before_edge"], t["slots"]
        if lo <= start and end <= hi and all(grid[i] == TRAVEL for i in range(hi - slots, hi)):
            verb = "Drive" if t["mode"] == "car" else "Walk"
            result = {"description": f"{verb} to {t['to_label']}",
                      "scheduled": (problem.week_start + timedelta(days=start // ROWS)).isoformat(),
                      "starttime": clock(start % ROWS * STEP), "endtime": clock(end % ROWS * STEP),
                      "location": f"{t['from_location']} → {t['to_location']}", "transport": t["mode"],
                      "travel": f"From {t['from_location']} to {t['to_location']}",
                      "est": f"{(end - start) * STEP}m",
                      "tags": ["managed", "composer", "grid", "grid-" + problem.week_start.isoformat(), "travel", "schedule"]}
            if t.get("to_source"):
                result["todo"] = f"- Attend {t['to_label']} [omn:{t['to_source']}]"
            return result
    palette = {c.key: c for c in problem.colors}
    whole_start, whole_end = start, end
    while whole_start and grid[whole_start - 1] == "travel":
        whole_start -= 1
    while whole_end < CELLS and grid[whole_end] == "travel":
        whole_end += 1
    previous = next((i for i in range(whole_start - 1, -1, -1)
                     if grid[i] in palette and palette[grid[i]].kind in {"work", "support", "fixed"}), None)
    following = next((i for i in range(whole_end, CELLS)
                      if grid[i] in palette and palette[grid[i]].kind in {"work", "support", "fixed"}), None)
    before = palette[grid[previous]] if previous is not None else None
    after = palette[grid[following]] if following is not None else None
    # Only the immediately adjacent visit can justify a route/mode. Searching
    # across free cells is for destination naming, never for SMT requirements.
    required_before = before if previous == whole_start - 1 and before.travel_after else None
    required_after = after if following == whole_end and after.travel_before else None
    choices = [(c, n) for c, n in ((required_after, required_after.travel_before if required_after else 0),
                                  (required_before, required_before.travel_after if required_before else 0)) if c]
    owner = max(choices, key=lambda pair: pair[1])[0] if choices else None
    if owner is None:
        raise ValueError("travel run has no adjacent destination/return requirement")
    origin = before.location if before and previous == whole_start - 1 else owner.travel_origin
    destination = (after.location if after and following == whole_end
                   else owner.travel_origin if required_before
                   else after.location if after else owner.travel_origin)
    mode = owner.transport
    verb = "Drive" if mode == "car" else "Walk"
    at_home = destination.casefold() in {"home", "at home"}
    label = "home" if at_home else destination
    refs = []
    for point in (following, previous):
        if point is None:
            continue
        reservation = next((r for r in problem.reservations
                            if r.color == grid[point] and r.start_minute // STEP <= point < ceil_slot(r.end_minute)), None)
        if reservation:
            fixed = next((f for f in problem.metadata.get("fixed_attendance", [])
                          if f["reservation"] == reservation.id), None)
            if fixed:
                refs.append(fixed["source"])
                if point == following and not at_home:
                    label = reservation.label
    target_item = next((i for i in problem.items if following is not None and i.id == owners.get(following)), None)
    route = f"From {origin} to {destination}"
    if target_item:
        route += f"; before {target_item.title}"
    result = {"description": f"{verb} {label}" if at_home else f"{verb} to {label}",
              "scheduled": (problem.week_start + timedelta(days=start // ROWS)).isoformat(),
              "starttime": clock(start % ROWS * STEP), "endtime": clock(end % ROWS * STEP),
              "location": f"{origin} → {destination}", "transport": mode,
              "travel": route, "est": f"{(end - start) * STEP}m",
              "tags": ["managed", "composer", "grid", "grid-" + problem.week_start.isoformat(), "travel", "schedule"]}
    if refs:
        result["todo"] = "\n".join(f"- {result['description']} [omn:{ref}]" for ref in dict.fromkeys(refs))
    return result
