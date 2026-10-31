"""The public path is ordinary Ansible, exercised only in disposable homes."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlainAnsibleTests(unittest.TestCase):
    def test_no_custom_runtime_framework(self):
        self.assertFalse((ROOT / 'plugins').exists())
        for name in ['fresh.yml', 'rollback.yml']:
            self.assertFalse((ROOT / 'playbooks' / name).exists())
        self.assertFalse((ROOT / 'scripts/deploy.py').exists())
        self.assertFalse((ROOT / 'policy/migration.json').exists())
        self.assertEqual(list((ROOT / 'roles').glob('*/manifest.yml')), [])

    def test_deploy_is_a_thin_explicit_target_wrapper(self):
        text = (ROOT / 'scripts/deploy').read_text()
        self.assertIn('ansible-playbook', text)
        self.assertNotIn('deploy.py', text)
        self.assertNotIn('--fresh', text)
        self.assertLess(len(text.splitlines()), 70)

    def run_role(self, home, host='araveia', role='shell', check=False, variables=None, vault_password=None, assertions=()):
        work = Path(home).parent
        inventory = work / 'inventory.json'
        inventory.write_text(json.dumps({'all': {'hosts': {host: {'ansible_connection': 'local'}}}}))
        playbooks = work / 'playbooks'
        playbooks.mkdir(exist_ok=True)
        play = playbooks / 'play.yml'
        play.write_text(json.dumps([{'hosts': 'all', 'gather_facts': False,
            'vars': {'dots_home': str(home), 'dots_sandbox': True,
                     'dots_manage_services': False, 'dots_manage_packages': False,
                     'dots_manage_externals': False, 'dots_install_agent_tools': False,
                     'dots_controller_root': str(ROOT), 'dots_configuration_changed': False,
                     **(variables or {})},
            'roles': [role],
            'post_tasks': [{'ansible.builtin.assert': {'that': list(assertions)}}] if assertions else []}]))
        command = ['ansible-playbook', '-i', str(inventory), str(play)]
        if check:
            command.append('--check')
        if vault_password:
            command.extend(['--vault-password-file', str(vault_password)])
        return subprocess.run(command, cwd=ROOT, env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg')),
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def test_shell_converges_without_pruning_personal_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            home.mkdir()
            (home / 'personal-note').write_text('keep me')
            result = self.run_role(home)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue((home / '.config/fish/config.fish').is_file())
            self.assertEqual((home / 'personal-note').read_text(), 'keep me')
            result = self.run_role(home)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn('changed=0', result.stdout)
            self.assertEqual(self.run_role(home, check=True).returncode, 0)

    def test_symlinked_configuration_parent_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            outside = Path(tmp) / 'outside'
            home.mkdir()
            outside.mkdir()
            (home / '.config').symlink_to(outside, target_is_directory=True)
            result = self.run_role(home)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_configuration_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            outside = base / 'outside'
            outside.write_text('unmanaged')
            (home / '.config/fish').mkdir(parents=True)
            target = home / '.config/fish/config.fish'
            target.symlink_to(outside)
            result = self.run_role(home)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertTrue(target.is_symlink())
            self.assertEqual(outside.read_text(), 'unmanaged')

    def test_symlinked_template_destination_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            outside = base / 'outside'
            outside.write_text('unmanaged')
            target = home / '.npmrc'
            target.symlink_to(outside)
            result = self.run_role(home)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertTrue(target.is_symlink())
            self.assertEqual(outside.read_text(), 'unmanaged')

    def test_encrypted_file_is_delivered_privately_without_plaintext_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            password = base / 'password'
            password.write_text('fixture-password-only\n')
            password.chmod(0o600)
            plaintext = base / 'plaintext'
            plaintext.write_text('secret-value-that-must-never-be-logged')
            (base / 'secrets').mkdir()
            encrypted = base / 'secrets/payload.vault'
            subprocess.run(['ansible-vault', 'encrypt', '--vault-password-file', str(password),
                            '--output', str(encrypted), str(plaintext)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            variables = {'vault_files': [{'src': encrypted.name, 'dest': '.private/token', 'services': ['cliproxyapi']}]}
            result = self.run_role(home, role='common', variables=variables, vault_password=password,
                                   assertions=["dots_changed_secret_roles == ['cliproxyapi']"])
            self.assertEqual(result.returncode, 0, result.stdout)
            target = home / '.private/token'
            self.assertEqual(target.read_text(), plaintext.read_text())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(plaintext.read_text(), result.stdout)
            repeat = self.run_role(home, role='common', variables=variables, vault_password=password,
                                   assertions=['dots_changed_secret_roles == []'])
            self.assertEqual(repeat.returncode, 0, repeat.stdout)
            self.assertIn('changed=0', repeat.stdout)
            bad_password = base / 'wrong-password'
            bad_password.write_text('wrong-password\n')
            target.rename(base / 'first-delivered-token')
            result = self.run_role(home, role='common', variables=variables, vault_password=bad_password)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            self.assertNotIn(plaintext.read_text(), result.stdout)

    def test_secret_delivery_refuses_a_symlinked_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            outside = base / 'outside'
            home.mkdir()
            outside.mkdir()
            (home / '.private').symlink_to(outside, target_is_directory=True)
            result = self.run_role(home, role='common', variables={
                'vault_files': [{'src': 'does-not-need-to-exist.vault', 'dest': '.private/token'}]})
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(outside.iterdir()), [])

    def test_secret_delivery_refuses_a_symlinked_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            (home / '.private').mkdir(parents=True)
            outside = base / 'outside'
            outside.write_text('unmanaged')
            (home / '.private/token').symlink_to(outside)
            result = self.run_role(home, role='common', variables={
                'vault_files': [{'src': 'does-not-need-to-exist.vault', 'dest': '.private/token'}]})
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((home / '.private/token').is_symlink())
            self.assertEqual(outside.read_text(), 'unmanaged')

    def test_lab_ssh_does_not_replace_personal_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            (home / '.ssh').mkdir(parents=True)
            path = home / '.ssh/config'
            path.write_text('Host personal\n  HostName example.invalid\n')
            result = self.run_role(home, 'syssec-canis', 'ssh')
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn('Host personal', path.read_text())
            self.assertTrue((home / '.ssh/config.d/50-lab.conf').exists())


if __name__ == '__main__':
    unittest.main()
