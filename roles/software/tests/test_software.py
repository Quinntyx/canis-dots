#!/usr/bin/env python
"""Source/sandbox checks only: never invoke real package installers or sudo."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROLE = Path(__file__).resolve().parents[1]
REPO = ROLE.parents[1]


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dots-software-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        source = (ROLE / "templates/pacman-bridge.py.j2").read_text().replace(
            "{{ software_build.path | to_json }}", json.dumps(str(self.root)))
        namespace = {"__name__": "bridge_test"}
        exec(compile(source, "pacman-bridge", "exec"), namespace)
        self.validate = namespace["validate"]
        self.archive = self.root / "demo-1-1-x86_64.pkg.tar.zst"
        self.archive.write_bytes(b"fixture, not a real package")

    def test_supported_queries_and_installs(self):
        for arguments in (["-Qq"], ["-Qmq"], ["-Qi"], ["-Q", "--foreign"],
                          ["-T", "gtk4>=4.12"], ["-Sg", "base-devel"],
                          ["--dots-validate"]):
            with self.subTest(arguments=arguments):
                self.assertTrue(self.validate(arguments))
        for arguments in (["-S", "--needed", "--noconfirm", "git"],
                          ["--config", "/etc/pacman.conf", "-S", "--asdeps", "gtk4"],
                          ["-D", "--asdeps", "gtk4"],
                          ["-S", "--asdeps", "extra/gtk4"],
                          ["-U", "--noconfirm", "--", str(self.archive)]):
            with self.subTest(arguments=arguments):
                self.assertFalse(self.validate(arguments))

    def test_denies_unbounded_privilege_and_upgrade_paths(self):
        requests = [
            ["-R", "git"], ["-Rnu", "git"], ["-Syu"], ["-Sy", "git"],
            ["-S", "--sysupgrade", "git"], ["-S", "--refresh", "git"],
            ["-S", "--root", "/tmp", "git"],
            ["-S", "--hookdir", "/tmp", "git"],
            ["-S", "--config", "/tmp/attacker.conf", "git"],
            ["-S", "--config=/tmp/attacker.conf", "git"],
            ["-S", "--dbpath", "/tmp", "git"],
            ["-S", "--overwrite", "*", "git"],
            ["-S", "--", "--sysupgrade"], ["-S", "../bad"],
            ["-S", "git;touch /tmp/bad"], ["-S"],
            ["-D", "--print", "git"], ["-D", "-i", "git"],
            ["-S", "-u", "git"], ["-U", "--print", str(self.archive)],
            ["-Q", "-S", "git"], ["-U", "/etc/passwd"],
            ["--dots-validate", "-S", "git"],
        ]
        outside = self.root.parent / "outside.pkg.tar.zst"
        link = self.root / "escape.pkg.tar.zst"
        link.symlink_to("/etc/passwd")
        requests.extend((["-U", str(outside)], ["-U", str(link)]))
        for arguments in requests:
            with self.subTest(arguments=arguments):
                with self.assertRaises((ValueError, OSError)):
                    self.validate(arguments)


class RoleTests(unittest.TestCase):
    def test_task_surfaces_are_builtin_only_and_cleanup_is_unconditional(self):
        task_keywords = {"name", "become", "become_user", "environment", "when", "loop",
                         "loop_control", "register", "changed_when", "failed_when", "block", "always", "check_mode"}

        def inspect(tasks):
            for task in tasks:
                for key in task:
                    self.assertTrue(key in task_keywords or key.startswith("ansible.builtin."), key)
                for key in ("block", "always"):
                    if key in task:
                        inspect(task[key])

        for path in (ROLE / "tasks").glob("*.yml"):
            inspect(yaml.safe_load(path.read_text()))
            self.assertNotIn("/home/zlare", path.read_text())
        builds = yaml.safe_load((ROLE / "tasks/builds.yml").read_text())[-1]
        self.assertEqual(builds["always"][0]["ansible.builtin.file"]["state"], "absent")
        self.assertEqual(builds["always"][0]["ansible.builtin.file"]["path"], "{{ software_sudoers.path }}")
        self.assertIn("--noremovemake", (ROLE / "tasks/builds.yml").read_text())

    def test_sudo_policy_and_wrapper_syntax_without_installing_them(self):
        validator = shutil.which("visudo")
        if validator is None:
            self.skipTest("visudo unavailable; deployment still uses copy.validate")
        with tempfile.TemporaryDirectory(prefix="dots-policy-test-") as temporary:
            policy = Path(temporary) / "sudoers"
            policy.write_text("fixture ALL=(root) NOPASSWD: /run/dots-software-policy-fixture/pacman *\n")
            result = subprocess.run([validator, "-cf", str(policy)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            wrapper = Path(temporary) / "sudo"
            source = (ROLE / "templates/sudo.sh.j2").read_text().replace(
                "{{ (software_policy.path + '/pacman') | quote }}", "/run/dots-software-policy-fixture/pacman")
            wrapper.write_text(source)
            result = subprocess.run(["/bin/sh", "-n", str(wrapper)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_curated_provenance_and_no_abandoned_packages(self):
        paths = REPO / "docs/backups/private_araveia/packages"
        expected = {}
        for name in ("pacman", "aur", "local"):
            expected[name] = [line.split("#", 1)[0].strip() for line in (paths / f"{name}.txt").read_text().splitlines()]
            expected[name] = [value for value in expected[name] if value and value != "chezmoi"]
        self.assertIn("niri", expected["pacman"])
        self.assertIn("zen-browser-bin", expected["aur"])
        self.assertEqual(len(expected["local"]), 2)
        for package in ("chezmoi", "navidrome", "sunshine", "openclaw", "nix", "incus"):
            self.assertNotIn(package, expected["pacman"] + expected["aur"])

    def run_ansible(self, check=False, syntax=False, sandbox=True, repetitions=1):
        with tempfile.TemporaryDirectory(prefix="dots-role-fixture-") as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            marker = home / "untouched"
            marker.write_text("retain me\n")
            playbook = Path(temporary) / "site.yml"
            playbook.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"dots_sandbox": sandbox, "dots_home": str(home), "dots_user": "fixture"},
                "roles": [{"role": str(ROLE)}],
                "post_tasks": [{"name": "Assert package source resolution", "vars": {"role_path": str(ROLE)},
                                "ansible.builtin.assert": {"that": [
                    "'chezmoi' not in software_official_packages",
                    "'acl' in software_official_packages",
                    "'niri' in software_official_packages",
                    "'sunsetr-bin' in software_aur_packages",
                    "software_local_directories | length == 2",
                    "software_official_curated | length > 150",
                ]}}],
                # Static imports make --syntax-check inspect the real task surfaces,
                # even though production deliberately includes them dynamically.
                "tasks": [{"ansible.builtin.import_role": {"name": str(ROLE), "tasks_from": name}}
                          for name in ("install", "builds", "tools")] if syntax else [],
            }]))
            command = [shutil.which("ansible-playbook"), "-i", "localhost,", str(playbook)]
            if syntax:
                command.append("--syntax-check")
            if check:
                command.append("--check")
            for _ in range(repetitions):
                result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if not syntax:
                    self.assertRegex(result.stdout, r"changed=0\s+unreachable=0\s+failed=0")
                    self.assertNotIn("Install missing official packages", result.stdout)
                self.assertEqual(marker.read_text(), "retain me\n")
                self.assertEqual(list(home.iterdir()), [marker])

    def test_role_syntax(self):
        self.run_ansible(syntax=True)

    def test_sandbox_first_run_and_repeat(self):
        self.run_ansible(repetitions=2)

    def test_real_mode_check_is_also_side_effect_free(self):
        self.run_ansible(check=True, sandbox=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
