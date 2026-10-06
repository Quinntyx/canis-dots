"""Subtract structured co-participant busy windows in regular Python."""
from scheduler.common import hhmm_to_minutes

from .schema import CELLS, ROWS, ceil_slot

DAYS = {name: day for day, name in enumerate(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'))}


def participant_windows(meta, records):
    requested = meta.get('people', meta.get('with', meta.get('participants', [])))
    if isinstance(requested, str):
        requested = [requested]
    if not requested:
        return None
    persons = [r for r in records if r.get('type') == 'person']
    busy = []
    for name in requested:
        matches = [r for r in persons if str(name).casefold() in {
            str(r.get('id')).casefold(), str(r.get('title')).casefold(),
            str((r.get('meta') or {}).get('name', '')).casefold()}]
        if len(matches) != 1:
            raise ValueError(f'unresolved co-scheduling participant: {name}')
        data = matches[0].get('meta') or {}
        if data.get('timezone', 'America/Chicago') != 'America/Chicago':
            raise ValueError(f'participant timezone requires conversion: {name}')
        margin = 15 if data.get('times_approximate') else 0
        for entry in data.get('busy', []):
            start, end = hhmm_to_minutes(entry['start']), hhmm_to_minutes(entry['end'])
            if not 0 <= start < end <= 1440:
                raise ValueError(f'invalid participant busy interval: {name}')
            for raw in entry['days']:
                day = DAYS.get(str(raw).lower()[:3]) if not isinstance(raw, int) else raw
                if day is None or not 0 <= day < 7:
                    raise ValueError(f'invalid participant weekday: {raw}')
                busy.append((day * ROWS + max(0, (start - margin) // 15),
                             day * ROWS + min(ROWS, ceil_slot(end + margin))))
    free = [(0, CELLS)]
    for a, b in sorted(busy):
        next_free = []
        for x, y in free:
            if b <= x or y <= a:
                next_free.append((x, y))
            else:
                if x < a:
                    next_free.append((x, a))
                if b < y:
                    next_free.append((b, y))
        free = next_free
    return free
