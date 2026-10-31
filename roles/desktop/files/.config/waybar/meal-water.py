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
- Peer sync (see the Tailscale section in the code): every machine running
  this config on the tailnet serves its state and pulls all online peers,
  merging newest-wins -- no canonical server, no fixed peer list. An offline
  peer never blocks anything; its clicks converge on the next successful
  pull. Other tailnet devices are skipped (they don't answer the port).
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
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
SYNC_MARKER_PATH = STATE_PATH.with_suffix(".sync")

# --- Tailscale peer sync -----------------------------------------------------
# Fully symmetric P2P: every machine running this config on the tailnet serves
# its state over HTTP (see `serve`, run as a systemd --user service) and pulls
# every other machine's state, merging newest-wins per counter. No machine is
# canonical; peers are discovered dynamically from `tailscale status` each
# cycle (online nodes only; nodes without this config fail the port probe and
# are skipped). Nodes going offline or coming online never matter: an
# unreachable peer is skipped silently and its clicks converge on the next
# successful cycle.
SYNC_PORT = 43017
SYNC_EVERY = timedelta(minutes=2)
SYNC_TIMEOUT = 3  # seconds, per peer fetch


def tailnet_peers() -> list[str]:
    """MagicDNS hostnames of online tailnet peers, excluding this machine.

    Returns [] when tailscale is unavailable -- everything degrades to
    standalone operation without touching local state.
    """
    try:
        proc = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        status = json.loads(proc.stdout)
    except Exception:
        return []
    self_name = (status.get("Self") or {}).get("HostName", "")
    peers = []
    for peer in (status.get("Peer") or {}).values():
        if not peer.get("Online"):
            continue  # offline nodes are skipped instantly
        name = peer.get("HostName", "")
        if name and name != self_name:
            peers.append(name)
    return peers


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


# --- sync: merge + pull + serve ----------------------------------------------

def _adopt_peer_block(local_ts: str | None, peer_ts: str | None) -> bool:
    """True when the peer's event block should replace the local one.

    Only blocks from today (in local time) are adopted, so a machine that was
    offline since yesterday can't resurrect old events and shift the
    breakfast/lunch/dinner numbering.
    """
    if peer_ts is None:
        return False
    try:
        pt = datetime.fromisoformat(peer_ts).astimezone()
    except ValueError:
        return False
    if pt.date() != date.today():
        return False  # stale day -- keep local (fresh-day rollover wins)
    if local_ts is None:
        return True
    lt = datetime.fromisoformat(local_ts).astimezone()
    return pt > lt


def _merge_meals(local_meals: list, peer_meals: list) -> list:
    """Union of logged meals by (meal, time), collapsing near-duplicate
    entries of the same meal within 120 s (both machines logged it)."""
    seen: list[dict] = []
    for entry in sorted(local_meals + peer_meals, key=lambda e: e["time"]):
        try:
            t = datetime.fromisoformat(entry["time"]).astimezone()
        except (ValueError, KeyError):
            continue
        if any(
            e["meal"] == entry.get("meal")
            and abs((datetime.fromisoformat(e["time"]).astimezone() - t).total_seconds()) < 120
            for e in seen
        ):
            continue
        seen.append({"meal": entry.get("meal", "meal"), "time": entry["time"]})
    return seen


def merge_states(local: dict, peer: dict) -> dict:
    merged = dict(local)
    if _adopt_peer_block(local.get("last_eat"), peer.get("last_eat")):
        merged["last_eat"] = peer["last_eat"]
        merged["meals"] = _merge_meals(local.get("meals", []), peer.get("meals", []))
    if _adopt_peer_block(local.get("last_water"), peer.get("last_water")):
        merged["last_water"] = peer["last_water"]
        merged["glasses"] = int(peer.get("glasses", 0))
    return merged


def _load_sync_marker() -> dict:
    try:
        return json.loads(SYNC_MARKER_PATH.read_text())
    except Exception:
        return {}


def _save_sync_marker(marker: dict) -> None:
    try:
        SYNC_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        SYNC_MARKER_PATH.write_text(json.dumps(marker))
    except Exception:
        pass


def _fetch_state(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=SYNC_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None  # peer down / not on tailscale / not running the service


def maybe_sync(force: bool = False) -> bool:
    """Pull every online tailnet peer's state and merge newest-wins into the
    local state file. Returns True if the local state file changed."""
    marker = _load_sync_marker()
    last = marker.get("last_attempt")
    if (
        not force
        and last is not None
        and now() - datetime.fromisoformat(last) < SYNC_EVERY
    ):
        return False
    marker["last_attempt"] = now().isoformat(timespec="seconds")
    _save_sync_marker(marker)

    urls = [f"http://{name}:{SYNC_PORT}/state" for name in tailnet_peers()]
    if not urls:
        return False

    local = load_state()
    merged = local
    any_success = False
    with ThreadPoolExecutor(max_workers=8) as pool:
        for data in pool.map(_fetch_state, urls):
            if not isinstance(data, dict) or not isinstance(data.get("state"), dict):
                continue
            any_success = True
            try:
                merged = merge_states(merged, data["state"])
            except Exception:
                continue
    if not any_success:
        return False

    marker["last_success"] = now().isoformat(timespec="seconds")
    _save_sync_marker(marker)
    if merged != local:
        save_state(merged)
        return True
    return False


class _StateHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path != "/state":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"host": socket.gethostname(), "state": load_state()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # keep the journal quiet
        pass


def serve() -> None:
    """Serve local state for the peer to pull; also pull the peer
    periodically so this side converges even without waybar running."""

    def pull_loop() -> None:
        while True:
            try:
                maybe_sync()
            except Exception:
                pass
            threading.Event().wait(SYNC_EVERY.total_seconds())

    threading.Thread(target=pull_loop, daemon=True).start()
    HTTPServer(("0.0.0.0", SYNC_PORT), _StateHandler).serve_forever()


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
    maybe_sync(force=True)  # ping-pong: converge the peer promptly after a click
    emit_status("eat")


def log_water() -> None:
    state = load_state()
    state["last_water"] = now().isoformat(timespec="seconds")
    state["glasses"] = int(state.get("glasses", 0)) + 1
    save_state(state)
    maybe_sync(force=True)
    emit_status("water")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eat-status"
    if cmd == "serve":
        serve()
    elif cmd == "eat-status":
        maybe_sync()  # throttled; the peer may have clicked since last look
        emit_status("eat")
    elif cmd == "water-status":
        maybe_sync()
        emit_status("water")
    elif cmd == "eat":
        log_eat()
    elif cmd == "water":
        log_water()
    else:
        sys.exit(f"unknown subcommand: {cmd}")


if __name__ == "__main__":
    main()
