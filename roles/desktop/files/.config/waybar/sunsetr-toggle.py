#!/usr/bin/python3
"""Waybar controls for Sunsetr: pause/resume and a separate super-night toggle.

Two independent buttons share this script:

  * Main button (existing): stops/starts Sunsetr entirely. "Paused" means the
    filter is off but returns by itself at 04:30 (or on click).
  * Super-night button: applies the `super` preset (static 3600K @ 60%, the
    pre-chill settings) until 04:30 local morning, then reverts to the default
    scheduling (Night: 3800K @ 80%, Day: 6500K @ 100%).

Keep MORNING and sunsetr-resume.timer's OnCalendar in sync. Both states live
outside configuration and survive logout/reboot; the service ExecCondition
prevents an early restart while the persistent timer catches a missed morning.
"""

from datetime import datetime, time, timedelta
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from time import sleep, monotonic as timeout_now


def timeout_deadline(seconds):
    return timeout_now() + seconds

MORNING = time(4, 30)
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "waybar-sunsetr"
PAUSED_FILE = STATE_DIR / "paused-until"
SUPER_FILE = STATE_DIR / "super-until"
LOCK = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "waybar-sunsetr.lock"


def deadline(path):
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def next_morning(now=None):
    now = now or datetime.now()
    morning = datetime.combine(now.date(), MORNING)
    if morning <= now:
        morning += timedelta(days=1)
    return int(morning.timestamp())


def save(path, until):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(f"{until}\n")
    temporary.replace(path)


def systemctl(*args):
    result = subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True, timeout=15
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "systemctl failed")
    return result.stdout


def is_active():
    return subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", "sunsetr.service"],
        timeout=5,
    ).returncode == 0


def ensure_service():
    """Start the service if it is not running (clears any main-button pause)."""
    PAUSED_FILE.unlink(missing_ok=True)
    if not is_active():
        systemctl("start", "sunsetr.service")


def preset_active_is(name):
    active = subprocess.run(["sunsetr", "preset", "active"],
                            capture_output=True, text=True, timeout=10)
    return active.stdout.strip() == name


def apply_preset(name, require_daemon_apply=True, attempts=10):
    """Switch the active preset, then wait until the change is confirmed."""
    last_error = None
    for attempt in range(attempts):
        result = subprocess.run(["sunsetr", "preset", name],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            if not require_daemon_apply:
                return
            deadline_ = timeout_deadline(4.0)
            while timeout_now() < deadline_:
                sleep(0.25)
                if preset_active_is(name):
                    return
            last_error = "preset change not confirmed by daemon"
        else:
            message = (result.stderr.strip() or result.stdout.strip()
                       or "preset failed").splitlines()
            last_error = message
            if is_active():
                # Service reload signal may race a restart; retry.
                sleep(0.4)
            else:
                # Activating outside a running service launches a foreground
                # sunsetr that holds the singleton; kill it and read state.
                subprocess.run(["pkill", "-f", "sunsetr preset"], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                sleep(1.0)
                if preset_active_is(name):
                    return
                last_error = "preset apply timed out (service not running)"
        sleep(0.3)
    raise RuntimeError("; ".join(last_error) or f"preset {name} failed")


def super_deadline():
    return deadline(SUPER_FILE)


def super_off_wrapper():
    """Deactivate super night and restore the default scheduling."""
    active = subprocess.run(["sunsetr", "preset", "active"],
                            capture_output=True, text=True, timeout=10)
    if active.stdout.strip() == "super":
        apply_preset("default")
    SUPER_FILE.unlink(missing_ok=True)


def expire_supers_locked():
    """Auto-expire super night once its deadline (04:30) has passed."""
    until = super_deadline()
    if until and until <= int(datetime.now().timestamp()):
        try:
            super_off_wrapper()
        finally:
            SUPER_FILE.unlink(missing_ok=True)


def status():
    tool, text, cls = "sunsetr-toggle.py", None, "off"
    until = deadline(PAUSED_FILE)
    if until:
        morning = datetime.fromtimestamp(until).strftime("%a %H:%M")
        return {"text": "\uf185", "class": "paused", "tooltip":
                f"Sunsetr paused until {morning}\nClick to resume now"}
    active = is_active()
    return {"text": "\uf186" if active else "\uf185",
            "class": "active" if active else "off", "tooltip":
            "Sunsetr enabled\nClick to pause until 04:30" if active else
            "Sunsetr stopped\nClick to resume"}


def super_status():
    expire_supers_locked()
    active = super_deadline() > int(datetime.now().timestamp())
    if active:
        morning = datetime.fromtimestamp(super_deadline()).strftime("%a %H:%M")
        return {"text": "\uf0e7", "class": "super-on", "tooltip":
                f"Super night until {morning}\nClick to return to normal scheduling"}
    hint = "Sunsetr is off" if not is_active() else "Night: 3800K · 80% (scheduling)"
    return {"text": "\uf10c", "class": "super-off", "tooltip":
            f"Normal scheduling — {hint}\nClick for super night until 04:30"}


def super_on():
    ensure_service()
    systemctl("enable", "--now", "sunsetr-resume.timer")
    previous = super_deadline()
    until = next_morning()
    try:
        apply_preset("super")
    except Exception:
        if previous:
            save(SUPER_FILE, previous)
        raise
    save(SUPER_FILE, until)


def super_toggle_locked():
    if super_deadline() > int(datetime.now().timestamp()):
        super_off_wrapper()
    else:
        super_on()


def pause():
    # Require the wake-up timer before stopping the filter.
    systemctl("enable", "--now", "sunsetr-resume.timer")
    previous = deadline(PAUSED_FILE)
    until = next_morning()
    save(PAUSED_FILE, until)
    try:
        systemctl("stop", "sunsetr.service")
    except Exception:
        if previous:
            save(PAUSED_FILE, previous)
        else:
            PAUSED_FILE.unlink(missing_ok=True)
        raise


def resume():
    previous = deadline(PAUSED_FILE)
    PAUSED_FILE.unlink(missing_ok=True)
    try:
        systemctl("start", "sunsetr.service")
    except Exception:
        if previous:
            save(PAUSED_FILE, previous)
        raise


def resume_if_due():
    expire_supers_locked()
    until = deadline(PAUSED_FILE)
    if until and until <= int(datetime.now().timestamp()):
        resume()


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "can-start":
        # Do not acquire LOCK here: systemctl start invokes this synchronously
        # while the caller already holds the lock.
        return 0 if deadline(PAUSED_FILE) <= int(datetime.now().timestamp()) else 1
    if action == "status":
        print(json.dumps(status()), flush=True)
        return 0
    if action == "super-status":
        print(json.dumps(super_status()), flush=True)
        return 0
    if action not in {"toggle", "pause", "resume", "resume-if-due",
                      "super-toggle", "super-on", "super-off"}:
        raise ValueError(f"Unknown action: {action}")
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        expire_supers_locked()
        until = deadline(PAUSED_FILE)
        if action == "resume-if-due":
            if until and until <= int(datetime.now().timestamp()):
                resume()
        elif action == "super-toggle":
            super_toggle_locked()
        elif action == "super-on":
            super_on()
        elif action == "super-off":
            super_off_wrapper()
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
        if len(sys.argv) > 1 and sys.argv[1] in {"toggle", "pause", "resume",
                                                 "super-toggle", "super-on",
                                                 "super-off"}:
            subprocess.run(["notify-send", "Sunsetr", str(exc)], check=False)
        sys.exit(1)
