#!/usr/bin/python3
"""Pause Sunsetr until the next 04:30 local morning, or resume it early.

Keep MORNING and sunsetr-resume.timer's OnCalendar in sync. Pause state lives
outside configuration and survives logout/reboot; the service condition prevents
an early restart, while the persistent timer catches a missed morning.
"""

from datetime import datetime, time, timedelta
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

MORNING = time(4, 30)
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "waybar-sunsetr/paused-until"
LOCK = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "waybar-sunsetr.lock"


def deadline():
    try:
        return int(STATE.read_text().strip())
    except FileNotFoundError:
        return 0


def next_morning(now=None):
    now = now or datetime.now()
    morning = datetime.combine(now.date(), MORNING)
    if morning <= now:
        morning += timedelta(days=1)
    return int(morning.timestamp())


def save(until):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(f"{until}\n")
    temporary.replace(STATE)


def systemctl(*args):
    result = subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True, timeout=10
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "systemctl failed")
    return result.stdout


def pause():
    # Require the wake-up timer before stopping the filter.
    systemctl("enable", "--now", "sunsetr-resume.timer")
    previous = deadline()
    until = next_morning()
    save(until)
    try:
        systemctl("stop", "sunsetr.service")
    except Exception:
        if previous:
            save(previous)
        else:
            STATE.unlink(missing_ok=True)
        raise


def resume():
    previous = deadline()
    STATE.unlink(missing_ok=True)
    try:
        systemctl("start", "sunsetr.service")
    except Exception:
        if previous:
            save(previous)
        raise


def is_active():
    return subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", "sunsetr.service"],
        timeout=5,
    ).returncode == 0


def status():
    until = deadline()
    if until:
        morning = datetime.fromtimestamp(until).strftime("%a %H:%M")
        result = {"text": "\uf185", "class": "paused", "tooltip":
                  f"Sunsetr paused until {morning}\nClick to resume now"}
    else:
        active = is_active()
        result = {"text": "\uf186" if active else "\uf185",
                  "class": "active" if active else "off", "tooltip":
                  "Sunsetr enabled\nClick to pause until 04:30" if active else
                  "Sunsetr stopped\nClick to resume"}
    print(json.dumps(result))


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "can-start":
        # Do not acquire LOCK here: systemctl start invokes this synchronously
        # while the caller already holds the lock.
        return 0 if deadline() <= int(datetime.now().timestamp()) else 1
    if action == "status":
        status()
        return 0
    if action not in {"toggle", "pause", "resume", "resume-if-due"}:
        raise ValueError(f"Unknown action: {action}")
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        until = deadline()
        if action == "resume-if-due":
            if until and until <= int(datetime.now().timestamp()):
                resume()
        elif action == "resume" or (action == "toggle" and
                                   (until or not is_active())):
            resume()
        else:
            pause()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Sunsetr button: {exc}", file=sys.stderr)
        if len(sys.argv) > 1 and sys.argv[1] in {"toggle", "pause", "resume"}:
            subprocess.run(["notify-send", "Sunsetr", str(exc)], check=False)
        sys.exit(1)
