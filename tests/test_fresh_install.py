"""Fresh-install ordering and refusal regressions; never run a real installer."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fresh_deploy', ROOT / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class FreshWrapper(unittest.TestCase):
    def inventory(self):
        return {'_meta': {'hostvars': {host: {'dots_components': ['shell']} for host in ['araveia', 'syssec-canis']}}}

    def context(self, events):
        stack = contextlib.ExitStack()
        def run(argv, **kwargs):
            events.append(argv)
            return subprocess.CompletedProcess(argv, 0, json.dumps(self.inventory()) if argv[0] == 'ansible-inventory' else '')
        stack.enter_context(mock.patch.object(deploy.socket, 'gethostname', return_value='araveia'))
        stack.enter_context(mock.patch.object(deploy.shutil, 'which', return_value='/not-used'))
        stack.enter_context(mock.patch.object(deploy.subprocess, 'run', side_effect=run))
        return stack

    def test_fresh_rejects_remote_fleet_config_only_and_partial_requests_before_key_writes(self):
        for argv in [['--fresh', '--host', 'syssec-canis'], ['--fresh', '--all'],
                     ['--fresh', '--config-only'], ['--fresh', '--components', 'shell']]:
            events = []
            with self.subTest(argv=argv), self.context(events), mock.patch.object(deploy, 'password') as password:
                with self.assertRaises(ValueError):
                    deploy.main(argv)
                password.assert_not_called()
                self.assertEqual(len(events), 1)  # inventory only, no playbook

    def test_fresh_plan_does_not_create_keys_or_run_bootstrap(self):
        events = []
        with self.context(events), mock.patch.object(deploy, 'password') as password, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deploy.main(['--fresh', '--plan']), 0)
            password.assert_not_called()
            self.assertEqual(len(events), 1)

    def test_existing_vault_is_authenticated_before_recovery_then_secrets_enrolled_after(self):
        events = []
        def prepare(*args, **kwargs):
            events.append(('secrets', args[5], kwargs.get('allow_missing_required', False)))
            return []
        with self.context(events), mock.patch.object(deploy, 'password', return_value=b'fixture'), \
             mock.patch.object(deploy, 'private_directory'), mock.patch.object(deploy, 'prepare_secrets', side_effect=prepare), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deploy.main(['--fresh', '--no-become-prompt']), 0)
        order = [e[0] if isinstance(e, tuple) else (e[1] if e[0] == 'ansible-playbook' else e[0]) for e in events]
        self.assertEqual(order, ['ansible-inventory', 'secrets', 'playbooks/fresh.yml', 'secrets', 'playbooks/site.yml'])
        self.assertEqual(events[1], ('secrets', True, True))
        self.assertEqual(events[3], ('secrets', False, False))

    def test_explicit_fresh_uses_local_araveia_even_before_hostname_recovery(self):
        events = []
        with self.context(events), mock.patch.object(deploy.socket, 'gethostname', return_value='EndeavourOS'), \
             mock.patch.object(deploy, 'password', return_value=b'fixture'), \
             mock.patch.object(deploy, 'private_directory'), mock.patch.object(deploy, 'prepare_secrets', return_value=[]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deploy.main(['--fresh', '--no-become-prompt']), 0)
        plays = [event for event in events if event[0] == 'ansible-playbook']
        self.assertEqual(len(plays), 2)
        for play in plays:
            self.assertEqual(play[play.index('--limit') + 1], 'araveia')
            self.assertEqual(play[play.index('--connection') + 1], 'local')

    def test_fresh_check_does_not_assume_restored_credentials_exist(self):
        events = []
        with self.context(events), mock.patch.object(deploy, 'password', return_value=b'fixture'), \
             mock.patch.object(deploy, 'prepare_secrets', return_value=[]) as prepare, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deploy.main(['--fresh', '--check']), 0)
        plays = [event for event in events if event[0] == 'ansible-playbook']
        self.assertEqual(len(plays), 1)
        self.assertEqual(plays[0][1], 'playbooks/fresh.yml')
        prepare.assert_called_once()

    def test_wrong_key_prevents_even_fresh_mount_or_package_phase(self):
        events = []
        with self.context(events), mock.patch.object(deploy, 'password', return_value=b'wrong'), \
             mock.patch.object(deploy, 'private_directory'), \
             mock.patch.object(deploy, 'prepare_secrets', side_effect=ValueError('authentication failed')):
            with self.assertRaisesRegex(ValueError, 'authentication failed'):
                deploy.main(['--fresh', '--no-become-prompt'])
        self.assertEqual(len(events), 1)


class FreshBootstrapContract(unittest.TestCase):
    def test_fresh_upgrade_is_full_and_dns_reload_does_not_restart_connections(self):
        import yaml
        play = yaml.safe_load((ROOT / 'playbooks/fresh.yml').read_text())[0]
        commands = [task['ansible.builtin.command'].get('argv', []) for task in play['tasks']
                    if 'ansible.builtin.command' in task]
        pacman = [argv for argv in commands if argv and argv[0] == '/usr/bin/pacman']
        self.assertEqual(len(pacman), 1)
        self.assertIn('-Syu', pacman[0])
        self.assertIn('networkmanager', pacman[0])
        self.assertIn(['/usr/bin/nmcli', 'general', 'reload', 'conf'], commands)
        self.assertIn(['/usr/bin/nmcli', 'general', 'reload', 'dns-full'], commands)
        self.assertFalse(any('NetworkManager' in str(task.get('ansible.builtin.systemd_service', {}))
                             for task in play['tasks']))


class PreservedStorage(unittest.TestCase):
    def test_forgejo_ini_has_top_level_keys_and_must_still_be_locked(self):
        module_spec = importlib.util.spec_from_file_location('storage', ROOT / 'plugins/modules/dots_storage.py')
        storage = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(storage)
        with tempfile.TemporaryDirectory() as work:
            disk = Path(work)
            config = disk / 'host/forgejo/forgejo/gitea/conf/app.ini'
            config.parent.mkdir(parents=True)
            config.write_text('APP_NAME = Forgejo\nRUN_USER = git\n[security]\nINSTALL_LOCK = true\n')
            storage.verify_data(disk, disk.stat().st_uid, True)
            config.write_text('APP_NAME = Forgejo\n[security]\nINSTALL_LOCK = false\n')
            with self.assertRaisesRegex(ValueError, 'INSTALL_LOCK'):
                storage.verify_data(disk, disk.stat().st_uid, True)
            with self.assertRaisesRegex(ValueError, 'ownership'):
                storage.verify_data(disk, disk.stat().st_uid + 1, True)


if __name__ == '__main__':
    unittest.main()
