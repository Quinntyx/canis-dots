"""The public path is ordinary Ansible, exercised only in disposable homes."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlainAnsibleTests(unittest.TestCase):
    def test_concurrent_coursework_profile_keeps_remote_private_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            role = {'role': 'agents', 'tasks_from': 'coursework'}
            first = self.run_role(home, role=role)
            self.assertEqual(first.returncode, 0, first.stdout)
            target = home / '.config/t3assistant/config.json'
            self.assertEqual(json.loads(target.read_text())['token_file'],
                             str(home / '.local/state/t3assistant/oauth-token.json'))
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            override = home / '.local/state/t3assistant/config.private.json'
            override.parent.mkdir(parents=True)
            payload = '{"fixture_secret": "never-log-this-coursework-override"}\n'
            override.write_text(payload)
            override.chmod(0o600)
            result = self.run_role(home, role=role)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(target.read_text(), payload)
            self.assertNotIn('never-log-this-coursework-override', result.stdout)
            self.assertEqual(override.read_text(), payload)
            self.assertIn('changed=0', self.run_role(home, role=role).stdout)
            target.rename(base / 'previous-config')
            outside = base / 'outside'
            outside.write_text('unmanaged')
            target.symlink_to(outside)
            self.assertNotEqual(self.run_role(home, role=role).returncode, 0)
            self.assertEqual(outside.read_text(), 'unmanaged')

    def test_coursework_accepts_the_declared_chezmoi_private_link_and_prefers_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            archive = home / 'docs/omn/artifacts/t3assistant-config.private.json'
            archive.parent.mkdir(parents=True)
            payload = '{"fixture_secret":"restored-docs-private-config"}\n'
            archive.write_text(payload)
            archive.chmod(0o600)
            legacy = home / '.local/state/t3assistant/config.private.json'
            legacy.parent.mkdir(parents=True)
            legacy.symlink_to(archive)
            role = {'role': 'agents', 'tasks_from': 'coursework'}
            result = self.run_role(home, role=role)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual((home / '.config/t3assistant/config.json').read_text(), payload)
            self.assertTrue(legacy.is_symlink())
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('restored-docs-private-config', result.stdout)
            self.assertIn('changed=0', self.run_role(home, role=role).stdout)
            legacy.unlink()
            legacy.write_text('{"fixture":"preserve-legacy-but-prefer-docs"}')
            result = self.run_role(home, role=role)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(legacy.read_text(), '{"fixture":"preserve-legacy-but-prefer-docs"}')
            self.assertEqual((home / '.config/t3assistant/config.json').read_text(), payload)

    def test_coursework_recreates_only_the_declared_link_and_refuses_unexpected_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            archive = home / 'docs/omn/artifacts/t3assistant-config.private.json'
            archive.parent.mkdir(parents=True)
            archive.write_text('{"fixture":"archive-only"}')
            archive.chmod(0o600)
            legacy = home / '.local/state/t3assistant/config.private.json'
            role = {'role': 'agents', 'tasks_from': 'coursework'}
            dry_run = self.run_role(home, role=role, check=True)
            self.assertEqual(dry_run.returncode, 0, dry_run.stdout)
            self.assertFalse(legacy.is_symlink())
            result = self.run_role(home, role=role)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(legacy.is_symlink())
            self.assertEqual(legacy.readlink(), archive)
            legacy.unlink()
            outside = base / 'outside'
            outside.write_text('never-read-this-unexpected-target')
            legacy.symlink_to(outside)
            rejected = self.run_role(home, role=role)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertNotIn('never-read-this-unexpected-target', rejected.stdout)
            self.assertEqual(outside.read_text(), 'never-read-this-unexpected-target')

    def test_coursework_refuses_a_symlinked_archive_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            outside = base / 'outside'
            outside.mkdir()
            (home / 'docs').symlink_to(outside, target_is_directory=True)
            result = self.run_role(home, role={'role': 'agents', 'tasks_from': 'coursework'})
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(outside.iterdir()), [])

    def test_main_ssh_keeps_restored_config_and_uses_henry_for_the_lab(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            (home / '.ssh').mkdir(parents=True)
            config = home / '.ssh/config'
            original = 'Host personal\n  HostName example.invalid\nHost syssec-canis\n  User old-user\n'
            config.write_text(original)
            result = self.run_role(home, role='ssh')
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(original, config.read_text())
            query = subprocess.run(['ssh', '-G', '-F', str(config), 'syssec-canis'],
                                   capture_output=True, text=True, check=True)
            self.assertIn('user henry\n', query.stdout)
            self.assertEqual((home / '.ssh/config.d/50-main.conf').stat().st_mode & 0o777, 0o600)
            self.assertIn('changed=0', self.run_role(home, role='ssh').stdout)

    def test_coursework_unit_changes_do_not_mark_desktop_restart_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            home.mkdir()
            role = {'role': 'desktop', 'tasks_from': 'config'}
            first = self.run_role(home, role=role)
            self.assertEqual(first.returncode, 0, first.stdout)
            coursework = home / '.config/systemd/user/t3assistant-coursework.timer'
            coursework.write_text('stale coursework unit\n')
            result = self.run_role(home, role=role,
                                   assertions=['not dots_configuration_changed'])
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotEqual(coursework.read_text(), 'stale coursework unit\n')
            desktop = home / '.config/systemd/user/meal-water-sync.service'
            desktop.write_text('stale desktop unit\n')
            result = self.run_role(home, role=role,
                                   assertions=['dots_configuration_changed'])
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotEqual(desktop.read_text(), 'stale desktop unit\n')

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
            'roles': [role] if isinstance(role, str) else [],
            'tasks': [{'ansible.builtin.import_role': {'name': role['role'],
                       'tasks_from': role['tasks_from']}}] if isinstance(role, dict) else [],
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
