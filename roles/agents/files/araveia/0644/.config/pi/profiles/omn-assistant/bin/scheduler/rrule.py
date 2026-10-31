"""RFC 5545 WEEKLY recurrence expansion.

omn stores ``meta.rrule`` (with ``meta.start`` as DTSTART and a
``meta.cancelled`` date list). The composer only needs the weekly cases used in
practice, so this module expands ``FREQ=WEEKLY`` rules faithfully — BYDAY,
INTERVAL, COUNT, UNTIL, WKST, EXDATE — and raises for anything else so the
caller can emit a diagnostic instead of guessing.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .common import TZ, WEEKDAY_CODES


class UnsupportedRecurrence(ValueError):
    """The rule is not a WEEKLY rrule this expander understands."""


def parse_rrule(text: str) -> dict:
    """Split ``FREQ=...;BYDAY=...`` into a case-insensitive dict of lists."""
    parts: dict[str, list[str]] = {}
    for chunk in str(text).split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        parts.setdefault(key.strip().upper(), []).extend(
            item for item in value.split(",") if item
        )
    return parts


def _weekday_index(code: str) -> int:
    code = code.strip().upper()[:2]
    if code not in WEEKDAY_CODES:
        raise UnsupportedRecurrence(f"unknown BYDAY value {code!r}")
    return WEEKDAY_CODES.index(code)


def _parse_until(value: str) -> date:
    text = value.strip()
    try:
        if "T" in text:
            dt = datetime.strptime(
                text, "%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(TZ).date()
        return datetime.strptime(text[:8], "%Y%m%d").date()  # noqa: DTZ007
    except ValueError as exc:  # pragma: no cover - defensive
        raise UnsupportedRecurrence(f"bad UNTIL value {value!r}") from exc


def _parse_exdate(value: str) -> date:
    try:
        return datetime.strptime(  # noqa: DTZ007 - date-only, naive is intended
            value.strip()[:8], "%Y%m%d").date()
    except ValueError as exc:  # pragma: no cover - defensive
        raise UnsupportedRecurrence(f"bad EXDATE value {value!r}") from exc


def expand_weekly(
    rrule_text: str,
    dtstart: datetime,
    window_start: date,
    window_end: date,
) -> list[date]:
    """Occurrence dates of a WEEKLY rule inside ``[window_start, window_end]``."""
    parts = parse_rrule(rrule_text)
    freq = (parts.get("FREQ") or ["WEEKLY"])[0].upper()
    if freq != "WEEKLY":
        raise UnsupportedRecurrence(f"only FREQ=WEEKLY is supported, got {freq!r}")

    interval = 1
    if parts.get("INTERVAL"):
        try:
            interval = max(1, int(parts["INTERVAL"][0]))
        except ValueError as exc:
            raise UnsupportedRecurrence("bad INTERVAL") from exc

    if parts.get("BYDAY"):
        bydays = sorted({_weekday_index(code) for code in parts["BYDAY"]})
    else:
        bydays = [dtstart.weekday()]

    until = _parse_until(parts["UNTIL"][0]) if parts.get("UNTIL") else None
    count = int(parts["COUNT"][0]) if parts.get("COUNT") else None
    exdates = {_parse_exdate(value) for value in parts.get("EXDATE", [])}

    wkst = _weekday_index(parts["WKST"][0]) if parts.get("WKST") else 0
    first_monday = dtstart.date() - timedelta(days=(dtstart.weekday() - wkst) % 7)
    dtstart_date = dtstart.date()

    occurrences: list[date] = []
    emitted = 0
    week_index = 0
    # 520 weeks (~10 years) is a hard safety bound; real rules carry UNTIL or
    # COUNT, and expansion is only ever asked about a one-week window.
    while week_index <= 520 and first_monday + timedelta(days=7 * week_index) <= window_end:
        week_monday = first_monday + timedelta(days=7 * week_index)
        if week_index % interval == 0:
            candidates = sorted(
                week_monday + timedelta(days=(weekday - wkst) % 7)
                for weekday in bydays
            )
            for candidate in candidates:
                if candidate < dtstart_date:
                    continue
                if until is not None and candidate > until:
                    return occurrences
                if count is not None and emitted >= count:
                    return occurrences
                emitted += 1
                if candidate not in exdates and window_start <= candidate <= window_end:
                    occurrences.append(candidate)
        week_index += 1
    return occurrences
