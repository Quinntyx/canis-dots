#!/usr/bin/env python3
"""Exercise the real pinned plugin and helper past the former 60s deadline."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
if not (source / "private_dot_local/bin/executable_tmux-persist").is_file():
    source = Path(subprocess.check_output(["chezmoi", "source-path"], text=True).strip())
real_home = Path.home()
root = Path(tempfile.mkdtemp(prefix="tmux-persist-long-restore-"))
socket = str(root / "test.sock")
env = os.environ.copy()
for key in ("TMUX", "TMUX_PANE", "XDG_STATE_HOME"):
    env.pop(key, None)
env["HOME"] = str(root)
helper = root / ".local/bin/tmux-persist"
plugin = root / ".local/share/tmux/plugins/tmux-resurrect"
helper.parent.mkdir(parents=True, exist_ok=True)
helper.write_text((source / "private_dot_local/bin/executable_tmux-persist").read_text())
helper.chmod(0o755)
plugin.parent.mkdir(parents=True, exist_ok=True)
plugin.symlink_to(real_home / ".local/share/tmux/plugins/tmux-resurrect", target_is_directory=True)
savedir = root / ".local/state/tmux/resurrect"
savedir.mkdir(parents=True)
saved = savedir / "fixture.txt"
row = ["pane", "restored-probe", "1", "1", ":*", "0", "probe", ":" + str(root), "1", "shell", ":"]
saved.write_text("\t".join(row) + "\nstate\trestored-probe\trestored-probe\n")
(savedir / "last").symlink_to(saved.name)


def tmux(*args):
    return subprocess.run(["tmux", "-S", socket, *args], env=env, text=True, capture_output=True, timeout=10, check=True).stdout.strip()


def option(name):
    result = subprocess.run(["tmux", "-S", socket, "show-option", "-g", "-v", name], env=env, text=True, capture_output=True, timeout=10)
    return result.stdout.strip()


def spinner_pids():
    matches = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            command = (proc / "cmdline").read_bytes().split(b"\0")
            if str(plugin / "scripts/tmux_spinner.sh").encode() in command:
                matches.append(int(proc.name))
        except OSError:
            pass
    return matches


child = None
try:
    tmux("-f", "/dev/null", "new-session", "-d", "-s", "bootstrap", "sleep 180")
    tmux("set-option", "-g", "default-shell", "/bin/sh")
    tmux("set-option", "-g", "@resurrect-hook-pre-restore-all", "sleep 65")
    started = time.monotonic()
    tmux("source-file", str(source / "dot_config/tmux/persistence.conf"))
    while time.monotonic() - started < 85:
        state = option("@tmux-persist-state")
        if state == "ready":
            break
        if state == "restore-failed":
            raise RuntimeError(option("@tmux-persist-error"))
        if not state and time.monotonic() - started > 5:
            raise RuntimeError("Startup did not initialize: " + tmux("show-messages"))
        time.sleep(0.5)
    elapsed = time.monotonic() - started
    assert option("@tmux-persist-state") == "ready", "long restore did not complete"
    assert elapsed > 60, elapsed
    assert "restored-probe" in tmux("list-sessions", "-F", "#{session_name}").splitlines()
    assert option("@tmux-persist-ready") == tmux("display-message", "-p", "#{pid}")
    time.sleep(0.3)
    assert not spinner_pids(), spinner_pids()
    print(json.dumps({"long_restore_seconds": round(elapsed, 2), "state": "ready", "all_expected_panes": True, "spinners": []}), flush=True)

    # Cancellation must not leave the same forever-spinner defect behind.
    tmux("set-option", "-g", "@resurrect-hook-pre-restore-all", "sleep 30")
    child_env = env.copy()
    child_env["TMUX"] = socket + ",0,0"
    child = subprocess.Popen([str(helper), "restore"], env=child_env)
    deadline = time.monotonic() + 10
    while not spinner_pids() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert spinner_pids(), "cancellation test never reached spinner"
    child.send_signal(signal.SIGTERM)
    assert child.wait(timeout=6) == 1
    time.sleep(0.3)
    assert not spinner_pids(), spinner_pids()
    assert option("@tmux-persist-state") == "restore-failed"
    ready = subprocess.run(["tmux", "-S", socket, "show-option", "-g", "-v", "@tmux-persist-ready"], capture_output=True)
    assert ready.returncode != 0, "cancelled restore incorrectly allowed autosaving"
    assert (savedir / "last").resolve() == saved
    print(json.dumps({"cancelled_restore": "failed visibly", "spinners": [], "last_snapshot_preserved": True, "autosave": "blocked"}), flush=True)

    # A retry should repair readiness and allow a real filtered snapshot save.
    tmux("set-option", "-g", "-u", "@resurrect-hook-pre-restore-all")
    subprocess.run([str(helper), "restore"], env=child_env, check=True, timeout=15)
    subprocess.run([str(helper), "save"], env=child_env, check=True, timeout=15)
    snapshot = savedir / "last"
    assert snapshot.is_file() and snapshot.resolve() != saved
    assert any(line.startswith("pane\trestored-probe\t") for line in snapshot.read_text().splitlines())
    assert option("@tmux-persist-state") == "ready"
    assert not spinner_pids(), spinner_pids()
    print(json.dumps({"retry_restore": "ready", "real_filtered_save": "passed", "spinners": []}), flush=True)
finally:
    if child is not None and child.poll() is None:
        child.terminate()
        child.wait(timeout=6)
    subprocess.run(["tmux", "-S", socket, "kill-server"], capture_output=True)
    subprocess.run(["trash", str(root)], check=True)
