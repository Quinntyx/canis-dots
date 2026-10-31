"""Real Ansible integration in private disposable homes; never a live deployment."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = shutil.which('ansible-playbook')


@unittest.skipUnless(PLAYBOOK, 'Install project-local ansible-core to run boundary tests')
class DisposableDeployment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='dots-integration-')
        cls.base = Path(cls.temp.name)
        cls.key = cls.base / 'key'
        cls.key.write_text('test-only-nonproduction-key\n')
        cls.key.chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_play(self, host, home, components=None, check=False, key=None):
        variables = dict(dots_home=str(home), dots_sandbox=True,
                         dots_manage_packages=False, dots_manage_services=False,
                         dots_manage_externals=False, dots_install_agent_tools=False,
                         dots_controller_root=str(ROOT), dots_vault_root=str(self.base / 'vault'), dots_docker_group_gid=777,
                         ansible_python_interpreter=sys.executable)
        if components is not None:
            variables['dots_requested_components'] = components
        command = [PLAYBOOK, 'playbooks/site.yml', '--limit', host, '--connection', 'local',
                   '--vault-password-file', str(key or self.key), '--extra-vars', json.dumps(variables)]
        if check:
            command.append('--check')
        return subprocess.run(command, cwd=ROOT, env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT/'ansible.cfg')),
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)

    def require_ok(self, run):
        self.assertEqual(run.returncode, 0, run.stdout[-14000:])

    def test_main_and_lab_first_run_repeat_check_and_unowned_preservation(self):
        for host in ['araveia', 'syssec-canis']:
            with self.subTest(host=host):
                home = self.base / host
                home.mkdir()
                (home / '.ssh').mkdir(mode=0o700)
                unowned = home / '.ssh/id_ed25519'
                unowned.write_text('unowned-test-identity-never-adopt\n')
                config = home / '.ssh/config'
                config.write_text('Host personal-sentinel\n    HostName 192.0.2.1\n')
                self.require_ok(self.run_play(host, home))
                self.assertEqual(unowned.read_text(), 'unowned-test-identity-never-adopt\n')
                self.assertTrue((home / '.config/ansible/dots-source.json').is_file())
                if host == 'syssec-canis':
                    self.assertIn('personal-sentinel', config.read_text())
                    self.assertIn('Include config.d/50-lab.conf', config.read_text())
                    self.assertTrue((home / '.ssh/config.d/50-lab.conf').is_file())
                    for absent in ['.mbsyncrc', '.config/hypr/hyprland.conf', '.config/systemd/user/forgejo.service',
                                   '.config/systemd/user/mail-sync.service', '.config/cliproxyapi/config.yaml']:
                        self.assertFalse((home / absent).exists(), absent)
                fish = (home / '.config/fish/config.fish').read_text()
                self.assertNotIn('/home/zlare', fish)
                repeat = self.run_play(host, home)
                self.require_ok(repeat)
                self.assertRegex(repeat.stdout, r'changed=0\s+unreachable=0\s+failed=0')
                before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file() and not p.is_symlink()}
                self.require_ok(self.run_play(host, home, check=True))
                after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file() and not p.is_symlink()}
                self.assertEqual(before, after)
                encrypted = list((self.base / 'vault/backups' / host).glob('*.vault'))
                self.assertTrue(encrypted)
                self.assertTrue(all(p.read_bytes().startswith(b'$ANSIBLE_VAULT;') for p in encrypted))
                wrong = self.base / ('wrong-' + host)
                wrong.write_text('deliberately-incorrect-key\n')
                wrong.chmod(0o600)
                rejected = self.run_play(host, home, key=wrong)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertEqual(before, {str(p.relative_to(home)): p.read_bytes() for p in home.rglob('*') if p.is_file() and not p.is_symlink()})

    def test_lab_cannot_request_main_services_even_directly(self):
        home = self.base / 'forbidden-lab'
        home.mkdir()
        result = self.run_play('syssec-canis', home, ['mail'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(home.iterdir()), [])

    def test_symlinked_destination_ancestor_is_rejected_before_write(self):
        home = self.base / 'unsafe-home'
        outside = self.base / 'outside'
        home.mkdir()
        outside.mkdir()
        (home / '.config').symlink_to(outside, target_is_directory=True)
        result = self.run_play('syssec-canis', home, ['shell'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
