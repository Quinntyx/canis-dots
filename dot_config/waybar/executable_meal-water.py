#!/usr/bin/env python3
"""Waybar eat/drink countdown buttons.

Subcommands:
    eat-status   -> JSON status for the `custom/eat` module
    water-status -> JSON status for the `custom/drink` module
    eat          -> log a finished meal (1st click of the day = breakfast,
                    2nd = lunch, 3rd = dinner, later ones = snack)
    water        -> log a finished glass of water

Behavior:
- EAT interval: 5h between meals (4-6h meal-spacing band, VA/Cleveland Clinic).
- WATER interval: 90 min between glasses (~200-250 ml; NASEM AI 2.7-3.7 L/day
  total fluid, drunk as ~1 glass every 90-120 min while awake).
- State rolls over at midnight: both counters start the day "overdue" (red)
  and the first eat click of the day is breakfast. No sleep window: a new day
  simply starts red, and a severely overdue timer resets to a good state on
  the next click. Red styling only -- no notifications.
"""

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

EAT_INTERVAL = timedelta(hours=5)
DRINK_INTERVAL = timedelta(minutes=90)
MEALS = ("breakfast", "lunch", "dinner")

ICON_EAT = "\uf2e7"    # fa-utensils
ICON_DRINK = "\uf043"  # fa-tint (droplet)

STATE_PATH = (
    Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    / "waybar-meal-water.json"
)


def now() -> datetime:
    return datetime.now().astimezone()


def load_state() -> dict:
    """Load state, rolling over to a fresh day when the date has changed.

    A new day starts with no meal logged and no glass logged, so both
    counters render red ("now") until the first clicks of the day.
    """
    today = date.today().isoformat()
    try:
        state = json.loads(STATE_PATH.read_text())
    except Exception:
        state = {}
    if state.get("day") != today:
        state = {
            "day": today,
            "meals": [],
            "last_eat": None,
            "last_water": None,
            "glasses": 0,
        }
    return state


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_PATH.parent, prefix=STATE_PATH.name)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def remaining(last: str | None, interval: timedelta) -> timedelta | None:
    """Time left until the deadline, negative when overdue."""
    if last is None:
        return None
    return (datetime.fromisoformat(last) + interval) - now()


def fmt_hours(delta: timedelta | None) -> str:
    """3h12m / -2h41m / now"""
    if delta is None:
        return "now"
    total = int(abs(delta).total_seconds() + 59) // 60  # ceil to minute
    h, m = divmod(total, 60)
    sign = "-" if delta.total_seconds() < 0 else ""
    return f"{sign}{h}h{m:02d}m"


def fmt_minutes(delta: timedelta | None) -> str:
    """47m / -35m / now"""
    if delta is None:
        return "now"
    total = int(abs(delta).total_seconds() + 59) // 60
    sign = "-" if delta.total_seconds() < 0 else ""
    return f"{sign}{total}m"


def last_meal_name(state: dict) -> str:
    meals = state["meals"]
    if not meals:
        return "none"
    return meals[-1]["meal"]


def emit_status(counter: str) -> None:
    state = load_state()
    today = date.today().isoformat()

    if counter == "eat":
        meals_today = len(state["meals"])
        if meals_today >= len(MEALS):  # breakfast, lunch, dinner all logged
            # After dinner there is no next meal today: show a done indicator
            # until tomorrow, when the day rolls over and breakfast re-arms it.
            text = f"{ICON_EAT} done"
            tooltip = (
                f"All meals done for today\n"
                f"Last: {last_meal_name(state)}"
                f" at {datetime.fromisoformat(state['last_eat']):%H:%M}\n"
                f"Next: tomorrow's breakfast"
            )
            critical = False
        else:
            rem = remaining(state["last_eat"], EAT_INTERVAL)
            if rem is None:
                text = f"{ICON_EAT} now"
                tooltip = "Time to eat (breakfast)"
            else:
                text = f"{ICON_EAT} {fmt_hours(rem)}"
                deadline = now() + rem
                overdue = rem.total_seconds() < 0
                overdue_note = f"\nOverdue by {fmt_hours(rem)[1:]}" if overdue else ""
                tooltip = (
                    f"Next meal by {deadline:%H:%M}{overdue_note}\n"
                    f"Last: {last_meal_name(state)}"
                    f" at {datetime.fromisoformat(state['last_eat']):%H:%M}\n"
                    f"Guideline: meals every 5 h while awake"
                )
            critical = rem is None or rem.total_seconds() <= 0
    else:  # water
        rem = remaining(state["last_water"], DRINK_INTERVAL)
        if rem is None:
            text = f"{ICON_DRINK} now"
            tooltip = "Time for a glass of water\n(starts the day cycle)"
        else:
            text = f"{ICON_DRINK} {fmt_minutes(rem)}"
            deadline = now() + rem
            overdue = rem.total_seconds() < 0
            overdue_note = f"\nOverdue by {fmt_minutes(rem)[1:]}" if overdue else ""
            tooltip = (
                f"Next glass by {deadline:%H:%M}{overdue_note}\n"
                f"Glasses today: {state['glasses']}\n"
                f"Guideline: ~1 glass (200-250 ml) every 90 min"
            )
        critical = rem is None or rem.total_seconds() <= 0

    print(
        json.dumps(
            {
                "text": text,
                "tooltip": tooltip,
                "class": "critical" if critical else "",
            }
        )
    )


def log_eat() -> None:
    state = load_state()
    meals = state["meals"]
    n = len(meals) + 1
    name = MEALS[n - 1] if n <= len(MEALS) else "snack"
    meals.append({"meal": name, "time": now().isoformat(timespec="seconds")})
    state["last_eat"] = now().isoformat(timespec="seconds")
    save_state(state)
    emit_status("eat")


def log_water() -> None:
    state = load_state()
    state["last_water"] = now().isoformat(timespec="seconds")
    state["glasses"] = int(state.get("glasses", 0)) + 1
    save_state(state)
    emit_status("water")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eat-status"
    if cmd == "eat-status":
        emit_status("eat")
    elif cmd == "water-status":
        emit_status("water")
    elif cmd == "eat":
        log_eat()
    elif cmd == "water":
        log_water()
    else:
        sys.exit(f"unknown subcommand: {cmd}")


if __name__ == "__main__":
    main()
