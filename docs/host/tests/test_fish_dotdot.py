#!/usr/bin/env python3
"""Run with: python docs/host/tests/test_fish_dotdot.py (needs fish and starship)."""
import fcntl
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time
import unittest

SOURCE = Path(__file__).resolve().parents[3]
FISH = SOURCE / "dot_config/private_fish"


class FishSession:
    """An isolated real reader; snapshots observe, but do not request, repaint."""

    def __init__(self, root):
        self.cwd = root / "nested/a/b/c/d/e"
        self.cwd.mkdir(parents=True)
        self.snapshot = root / "snapshot"
        home = root / "home"
        config = home / ".config/fish"
        (config / "functions").mkdir(parents=True)
        shutil.copyfile(FISH / "config.fish", config / "config.fish")
        for name in ("__dotdot_preview.fish", "fish_prompt.fish", "fish_user_key_bindings.fish", "reload.fish"):
            shutil.copyfile(FISH / "functions" / name, config / "functions" / name)
        shutil.copyfile(SOURCE / "dot_config/starship.toml", home / ".config/starship.toml")
        self.ack, ack_writer = os.pipe()
        os.set_inheritable(ack_writer, True)
        self.env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
                        XDG_DATA_HOME=str(home / ".local/share"), XDG_CACHE_HOME=str(home / ".cache"),
                        STARSHIP_CONFIG=str(home / ".config/starship.toml"), TERM="xterm-256color",
                        DOTDOT_SNAPSHOT=str(self.snapshot), DOTDOT_ACK_FD=str(ack_writer))
        init = r'''
function __dotdot_snapshot
    set -l buffer (commandline --current-buffer | string collect)
    printf '%s\0' "$buffer" "$PWD" "$__dotdot_previewing" > "$DOTDOT_SNAPSHOT"
    printf 'DOTDOT_SNAPSHOT_DONE\n' >&$DOTDOT_ACK_FD
end
for mode in default insert
    bind -M $mode ctrl-o __dotdot_snapshot
    bind -M $mode ctrl-b 'commandline --replace ""; commandline -f repaint'
    bind -M $mode ctrl-x 'commandline --replace "exit 0"; commandline -f execute'
end
printf 'DOTDOT_INIT_DONE\n' >&$DOTDOT_ACK_FD
'''
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.close(self.ack)
            os.chdir(self.cwd)
            os.execvpe("fish", ["fish", "--private", "--interactive", "--init-command", init], self.env)
        os.close(ack_writer)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        self.raw = bytearray()
        self.until(b"DOTDOT_INIT_DONE")
        self.inspect()  # reader/prompt startup barrier, not just init-command completion

    def until(self, marker):
        output = bytearray()
        deadline = time.monotonic() + 20
        while marker not in output:
            remaining = deadline - time.monotonic()
            ready = select.select([self.fd, self.ack], [], [], max(0, remaining))[0]
            if remaining <= 0 or not ready:
                raise AssertionError(f"Fish reader timeout: {bytes(self.raw[-2000:])!r}")
            for fd in ready:
                chunk = os.read(fd, 65536)
                if not chunk:
                    raise AssertionError("Fish reader exited")
                if fd == self.ack:
                    output.extend(chunk)
                else:
                    self.raw.extend(chunk)

    def inspect(self, keys=""):
        if keys:
            os.write(self.fd, keys.encode())
        # Fish coalesces repaint requests while input remains queued. Let the
        # real reader finish its output before observing state, without repainting it.
        deadline = time.monotonic() + 20
        while select.select([self.fd], [], [], 0.1)[0]:
            self.raw.extend(os.read(self.fd, 65536))
            if time.monotonic() > deadline:
                raise AssertionError("Fish output did not settle")
        os.write(self.fd, b"\x0f")
        self.until(b"DOTDOT_SNAPSHOT_DONE")
        # The acknowledgement is the callback's last command, not its return.
        # In particular, do not inject SIGINT while that callback is still active.
        while select.select([self.fd], [], [], 0.1)[0]:
            self.raw.extend(os.read(self.fd, 65536))
            if time.monotonic() > deadline:
                raise AssertionError("Fish output did not settle after snapshot")
        buffer, cwd, preview, _ = self.snapshot.read_text().split("\0")
        return buffer, Path(cwd), preview

    def clear(self):
        return self.inspect("\x02")  # deterministic fixture reset; Ctrl-C is tested separately

    def close(self):
        os.write(self.fd, b"\x18")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                os.close(self.fd)
                os.close(self.ack)
                if os.waitstatus_to_exitcode(status) != 0:
                    raise AssertionError(f"Fish exit status: {status}")
                return
            if select.select([self.fd], [], [], 0.1)[0]:
                try:
                    self.raw.extend(os.read(self.fd, 65536))
                except OSError:
                    pass
        os.kill(self.pid, signal.SIGTERM)
        os.waitpid(self.pid, 0)
        os.close(self.fd)
        os.close(self.ack)
        raise AssertionError("Fish did not exit cleanly")


@unittest.skipUnless(shutil.which("fish") and shutil.which("starship"), "needs fish and starship")
class DotdotTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="fish-dotdot-test-"))
        self.addCleanup(subprocess.run, ["trash", str(self.root)], check=True)
        self.shell = FishSession(self.root)
        self.addCleanup(self.shell.close)

    def target(self, levels, cwd=None):
        return os.path.normpath(str(cwd or self.shell.cwd) + "/.." * levels)

    def test_any_number_of_dots_previews_then_expands(self):
        for count in (2, 3, 4, 5, 12, 64):
            with self.subTest(dots=count):
                self.shell.clear()
                buffer, cwd, preview = self.shell.inspect("." * count)
                self.assertEqual(buffer, "." * count)
                self.assertEqual(cwd, self.shell.cwd)  # rendering never changes directory
                self.assertEqual(preview, self.target(count - 1))
                buffer, cwd, preview = self.shell.inspect(" ")
                self.assertEqual(buffer, "cd " + "../" * (count - 1) + " ")
                self.assertEqual(preview, self.target(count - 1))

    def test_only_command_tokens_expand_and_only_navigation_previews(self):
        for text in (". ", "echo ... ", "cd somewhere ", "'...' ", '"..." ', ".hidden ",
                     "...x ", "...; echo nope", "...\nfalse", "cd ../; echo nope"):
            with self.subTest(text=text):
                self.shell.clear()
                # Only multiline input needs paste protection against execution.
                keys = "\x1b[200~" + text + "\x1b[201~" if "\n" in text else text
                buffer, cwd, preview = self.shell.inspect(keys)
                expected = "cd ../../; echo nope" if text == "...; echo nope" else text
                self.assertEqual(buffer, expected)
                self.assertEqual(cwd, self.shell.cwd)
                self.assertEqual(preview, "")
        self.shell.clear()
        self.shell.inspect("...")
        self.assertEqual(self.shell.inspect("x")[2], "")

    def test_deletion_clear_and_cancel_restore_the_real_directory(self):
        self.assertEqual(self.shell.inspect("....")[2], self.target(3))
        self.assertEqual(self.shell.inspect("\x7f")[2], self.target(2))
        self.assertEqual(self.shell.inspect("\x7f")[2], self.target(1))
        self.assertEqual(self.shell.inspect("\x7f")[2], "")
        for clear in ("\x15", "\x17", "\x03", "\x1b\x7f"):
            self.shell.clear()
            self.shell.inspect("...")
            buffer, cwd, preview = self.shell.inspect(clear)
            self.assertEqual((buffer, cwd, preview), ("", self.shell.cwd, ""))

    def test_reload_preserves_prompt_preview_and_paste(self):
        for _ in range(2):
            self.shell.clear()
            self.shell.inspect("reload\r")
            self.assertEqual(self.shell.inspect("...")[2], self.target(2))
            self.assertEqual(self.shell.inspect("\x1b[200~x\x1b[201~")[2], "")
        self.assertNotIn(b"Unknown command", self.shell.raw)

    def test_paste_and_undo_do_not_leave_a_stale_preview(self):
        self.assertEqual(self.shell.inspect("...")[2], self.target(2))
        self.assertEqual(self.shell.inspect("\x1b[200~x\x1b[201~")[2], "")
        self.shell.clear()
        self.assertEqual(self.shell.inspect("\x1b[200~....\x1b[201~")[2], self.target(3))
        self.assertEqual(self.shell.inspect("\x15")[2], "")
        self.assertEqual(self.shell.inspect("\x1a")[2], self.target(3))  # undo the deletion
        self.assertEqual(self.shell.inspect("\x1b/")[2], "")  # redo it

    def test_enter_navigates_to_the_preview(self):
        for dots, levels in (("..", 1), ("...", 2), ("....", 3)):
            with self.subTest(dots=dots):
                self.shell.clear()
                self.shell.inspect("builtin cd -- " + str(self.shell.cwd) + "\r")
                preview = self.shell.inspect(dots)[2]
                buffer, cwd, after = self.shell.inspect("\r")
                self.assertEqual(str(cwd), preview)
                self.assertEqual(str(cwd), self.target(levels))
                self.assertEqual((buffer, after), ("", ""))

    def test_logical_symlink_parents_and_spaces(self):
        link = self.root / "logical space"
        link.symlink_to(self.shell.cwd, target_is_directory=True)
        self.shell.inspect("builtin cd -- '" + str(link) + "'\r")
        buffer, cwd, preview = self.shell.inspect("..")
        self.assertEqual(cwd, link)
        self.assertEqual(preview, str(self.root))
        self.assertEqual(self.shell.inspect("\r")[1], self.root)

    def test_native_starship_style_status_pipeline_and_transience_are_preserved(self):
        script = r'''
starship init fish | source
functions --copy fish_prompt __native_prompt
source $argv[1]
# No reader buffer here; the other tests cover the real preview boundary.
function __dotdot_preview
    return 1
end
set -g COLUMNS 100
set -g CMD_DURATION 0
set -e cmd_duration
for pipeline in 'true' 'false' 'false | true' 'true | false'
    eval $pipeline
    __native_prompt > $argv[2]/native
    eval $pipeline
    fish_prompt > $argv[2]/custom
    cmp $argv[2]/native $argv[2]/custom; or exit 1
end
__native_prompt --final-rendering > $argv[2]/native
fish_prompt --final-rendering > $argv[2]/custom
cmp $argv[2]/native $argv[2]/custom; or exit 1
function starship_transient_prompt_func
    printf '%s\n' $argv
end
false | true
__native_prompt --final-rendering > $argv[2]/native
false | true
fish_prompt --final-rendering > $argv[2]/custom
cmp $argv[2]/native $argv[2]/custom
'''
        result = subprocess.run(["fish", "--no-config", "-c", script,
                                 str(FISH / "functions/fish_prompt.fish"), str(self.root)],
                                env=self.shell.env, cwd=self.shell.cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
