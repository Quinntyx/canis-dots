#!/usr/bin/env python3
"""Run with: python docs/host/tests/test_tmux_persistence.py (in chezmoi source)."""
import contextlib
from pathlib import Path
import signal
import subprocess
import tempfile
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[3]
HELPER = SOURCE / "private_dot_local/bin/executable_tmux-persist"
if not HELPER.is_file():
    SOURCE = Path(subprocess.check_output(["chezmoi", "source-path"], text=True).strip())
    HELPER = SOURCE / "private_dot_local/bin/executable_tmux-persist"


def pane(index):
    return "\t".join(("pane", "work", "1", "1", ":*", str(index), "", ":/tmp", "1", "shell", ":")) + "\n"


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.module = types.ModuleType("tmux_persist_test")
        exec(compile(HELPER.read_text(), str(HELPER), "exec"), self.module.__dict__)
        self.root = Path(tempfile.mkdtemp(prefix="tmux-persist-test-"))
        self.addCleanup(subprocess.run, ["trash", str(self.root)], check=True)
        self.module.PLUGIN = self.root / "plugin"
        (self.module.PLUGIN / "scripts").mkdir(parents=True)
        for action in ("restore", "save"):
            (self.module.PLUGIN / "scripts" / f"{action}.sh").write_text("exit 0\n")

    def test_main_socket_only_including_custom_tmpdir(self):
        for tmpdir in ("", "/tmp", str(self.root / "sockets")):
            directory = Path(tmpdir or "/tmp") / f"tmux-{self.module.os.getuid()}"
            with self.subTest(tmpdir=tmpdir), mock.patch.dict(self.module.os.environ, {"TMUX_TMPDIR": tmpdir}):
                with mock.patch.object(self.module, "SOCKET", str(directory / "default")):
                    self.assertTrue(self.module.is_main_server())
                for socket in (directory / "pycells-git-test", self.root / "default"):
                    with mock.patch.object(self.module, "SOCKET", str(socket)):
                        self.assertFalse(self.module.is_main_server())

    def test_timer_context_resolves_default_socket_without_tmux_environment(self):
        with mock.patch.dict(self.module.os.environ, {"TMUX_TMPDIR": "/tmp"}), mock.patch.object(self.module, "SOCKET", ""), mock.patch.object(self.module, "tmux", return_value=f"/tmp/tmux-{self.module.os.getuid()}/default") as tmux:
            self.assertTrue(self.module.is_main_server())
            tmux.assert_called_once_with("display-message", "-p", "#{socket_path}", check=False)
        with mock.patch.object(self.module, "SOCKET", ""), mock.patch.object(self.module, "tmux", return_value=""):
            self.assertFalse(self.module.is_main_server())

    def test_private_server_operations_are_noops_before_touching_state(self):
        for action in ("startup", "save", "restore", "filter", "resume"):
            with self.subTest(action=action), mock.patch.object(self.module.sys, "argv", [str(HELPER), action]), mock.patch.object(self.module.signal, "signal"), mock.patch.object(self.module, "is_main_server", return_value=False), mock.patch.object(self.module, "lock") as lock, mock.patch.object(self.module, "tmux") as tmux, mock.patch.object(self.module, "filter_file") as filter_file, mock.patch.object(self.module, "resume") as resume:
                self.assertEqual(self.module.main(), 0)
                lock.assert_not_called()
                tmux.assert_not_called()
                filter_file.assert_not_called()
                resume.assert_not_called()

    def test_main_server_probe_exit_status(self):
        for allowed in (True, False):
            with self.subTest(allowed=allowed), mock.patch.object(self.module.sys, "argv", [str(HELPER), "is-main-server"]), mock.patch.object(self.module.signal, "signal"), mock.patch.object(self.module, "is_main_server", return_value=allowed):
                self.assertEqual(self.module.main(), 0 if allowed else 1)

    def test_main_server_dispatch_still_runs(self):
        with mock.patch.object(self.module.sys, "argv", [str(HELPER), "startup"]), mock.patch.object(self.module.signal, "signal"), mock.patch.object(self.module, "is_main_server", return_value=True), mock.patch.object(self.module, "startup") as startup:
            self.assertEqual(self.module.main(), 0)
            startup.assert_called_once_with()

    def test_no_fixed_deadline_for_restore_or_save(self):
        for action in ("restore", "save"):
            with self.subTest(action=action), mock.patch.object(self.module.subprocess, "Popen") as popen, mock.patch.object(self.module, "cleanup_resurrect") as cleanup:
                process = popen.return_value
                process.wait.return_value = 0
                self.module.resurrect(action)
                self.assertTrue(popen.call_args.kwargs["start_new_session"])
                process.wait.assert_called_once_with()
                cleanup.assert_called_once_with(process)

    def test_nonzero_exit_is_cleaned_and_reported(self):
        with mock.patch.object(self.module.subprocess, "Popen") as popen, mock.patch.object(self.module, "cleanup_resurrect") as cleanup:
            popen.return_value.wait.return_value = 7
            with self.assertRaisesRegex(RuntimeError, "restore failed \\(7\\)"):
                self.module.resurrect("restore")
            cleanup.assert_called_once_with(popen.return_value)

    def test_cancellation_also_cleans_children(self):
        with mock.patch.object(self.module.subprocess, "Popen") as popen, mock.patch.object(self.module, "cleanup_resurrect") as cleanup:
            popen.return_value.wait.side_effect = InterruptedError("cancelled")
            with self.assertRaises(InterruptedError):
                self.module.resurrect("restore")
            cleanup.assert_called_once_with(popen.return_value)

    def test_real_background_children_are_reaped_on_success_and_failure(self):
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code):
                child_file = self.root / f"child-{exit_code}"
                script = self.module.PLUGIN / "scripts/restore.sh"
                script.write_text(f'sleep 30 &\nprintf "%s" "$!" > "{child_file}"\nexit {exit_code}\n')
                if exit_code:
                    with self.assertRaises(RuntimeError):
                        self.module.resurrect("restore")
                else:
                    self.module.resurrect("restore")
                pid = int(child_file.read_text())
                info = self.module.process_info(pid)
                if info is not None:
                    # A briefly unreaped zombie is dead, not a running spinner.
                    stat = Path(f"/proc/{pid}/stat").read_text()
                    self.assertEqual(stat[stat.rfind(")") + 2:].split()[0], "Z")

    def test_failed_restore_clears_readiness_and_reports_failure(self):
        with mock.patch.object(self.module, "tmux") as tmux, mock.patch.object(self.module, "restore_snapshot", side_effect=RuntimeError("incomplete")):
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                self.module.restore_locked("123")
            tmux.assert_any_call("set-option", "-g", "-u", "@tmux-persist-ready", check=False)
            tmux.assert_any_call("set-option", "-g", "@tmux-persist-state", "restore-failed", check=False)
            self.assertNotIn(mock.call("set-option", "-g", "@tmux-persist-ready", "123"), tmux.call_args_list)

    def test_successful_restore_enables_saves_only_after_completion(self):
        with mock.patch.object(self.module, "tmux") as tmux, mock.patch.object(self.module, "restore_snapshot") as restore, mock.patch.object(self.module, "server_pid", return_value="123"):
            self.module.restore_locked("123")
            restore.assert_called_once_with()
            self.assertEqual(tmux.call_args_list[-2:], [
                mock.call("set-option", "-g", "@tmux-persist-ready", "123"),
                mock.call("set-option", "-g", "@tmux-persist-state", "ready"),
            ])

    def test_incomplete_layout_is_not_accepted(self):
        saved = self.root / "last"
        saved.write_text(pane(0) + pane(1))
        with mock.patch.object(self.module, "snapshot", return_value=saved), mock.patch.object(self.module, "resurrect"), mock.patch.object(self.module, "tmux", return_value="work\t1\t0"):
            with self.assertRaisesRegex(RuntimeError, "1 of 2 saved panes missing"):
                self.module.restore_snapshot()
            self.assertEqual(saved.read_text(), pane(0) + pane(1))

    def test_complete_layout_is_accepted(self):
        saved = self.root / "last"
        saved.write_text(pane(0) + pane(1))
        with mock.patch.object(self.module, "snapshot", return_value=saved), mock.patch.object(self.module, "resurrect") as restore, mock.patch.object(self.module, "tmux", return_value="work\t1\t0\nwork\t1\t1"):
            self.module.restore_snapshot()
            restore.assert_called_once_with("restore")

    def test_save_before_readiness_is_not_a_silent_success(self):
        with mock.patch.object(self.module, "tmux", return_value="work"), mock.patch.object(self.module, "lock", return_value=contextlib.nullcontext()), mock.patch.object(self.module, "server_pid", return_value="123"), mock.patch.object(self.module, "ready", return_value=False), mock.patch.object(self.module, "resurrect") as save:
            with self.assertRaisesRegex(RuntimeError, "Autosave paused"):
                self.module.save()
            save.assert_not_called()

    def test_source_reload_does_not_repeat_a_completed_restore(self):
        with mock.patch.object(self.module, "tmux", return_value="work"), mock.patch.object(self.module, "lock", return_value=contextlib.nullcontext()), mock.patch.object(self.module, "server_pid", return_value="123"), mock.patch.object(self.module, "ready", return_value=True), mock.patch.object(self.module, "restore_locked") as restore:
            self.module.startup()
            restore.assert_not_called()

    def test_termination_raises_for_finally_cleanup(self):
        with self.assertRaisesRegex(InterruptedError, "SIGTERM"):
            self.module.interrupted(signal.SIGTERM, None)

    def test_systemd_does_not_impose_another_save_or_restore_wait_deadline(self):
        service = (SOURCE / "dot_config/systemd/user/tmux-resurrect-save.service").read_text()
        self.assertIn("TimeoutStartSec=infinity", service)

    def test_timer_spaces_runs_from_completion_not_start(self):
        timer = (SOURCE / "dot_config/systemd/user/tmux-resurrect-save.timer").read_text()
        self.assertIn("OnUnitInactiveSec=1min", timer)
        self.assertNotIn("OnUnitActiveSec=", timer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
