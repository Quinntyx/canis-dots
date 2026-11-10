"""Public playbook template/layout flow, disposable homes, no live effects.

Bulk static transfer is covered by digest parity and the real shell fixtures;
this bounded fixture renders every role's templates and links on both hosts.
"""
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class FullConfiguration(unittest.TestCase):
    def test_both_enrolled_hosts_render_templates_without_live_side_effects(self):
        with tempfile.TemporaryDirectory(prefix='dots-native-config-') as tmp:
            base = Path(tmp)
            for host in ['araveia', 'syssec-canis']:
                home = base / host
                home.mkdir()
                # Preseed public static bytes with a local filesystem copy. The
                # production static-copy task is independently exercised by the
                # shell/symlink tests, avoiding thousands of module startups here.
                roles = ['shell', 'git', 'ssh', 'tmux', 'editor', 'agents', 't3code']
                if host == 'araveia':
                    roles += ['forgejo', 'desktop', 'mail', 'cliproxyapi']
                for role in roles:
                    for scope in ['common', 'araveia' if host == 'araveia' else 'lab']:
                        source = ROOT / 'roles' / role / 'files' / scope
                        if source.exists():
                            for mode in source.iterdir():
                                if mode.is_dir():
                                    shutil.copytree(mode, home, dirs_exist_ok=True)
            inventory = base / 'connections.json'
            inventory.write_text(json.dumps({'all': {'hosts': {
                host: {'ansible_connection': 'local'} for host in ['araveia', 'syssec-canis']}}}))
            variables = base / 'variables.json'
            variables.write_text(json.dumps({
                'dots_home': str(base) + '/{{ inventory_hostname }}',
                # Reproduce the CI container's actor even on a non-root host.
                'ansible_facts': {'user_id': 'root', 'user_uid': 0, 'user_gid': 0, 'user_dir': '/root'},
                # Synthetic target identity only: installs/acquisitions/services
                # are disabled and no real account is created or modified.
                'dots_user': 'dots-fixture',
                'dots_uid': 12345,
                'dots_sandbox': True,
                'dots_manage_packages': False,
                'dots_manage_services': False,
                'dots_manage_externals': False,
                'dots_install_agent_tools': False,
                'dots_docker_group_gid': '12345',
            }))
            command = ['ansible-playbook', '-i', 'inventory/hosts.yml', '-i', str(inventory),
                       'playbooks/site.yml', '--skip-tags', 'static_files',
                       '--extra-vars', '@' + str(variables)]
            result = subprocess.run(command, cwd=ROOT,
                env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg'), ANSIBLE_NOCOWS='1'),
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode:
                # Only public, artificial fixture data can appear here.
                self.fail(result.stdout[-18000:])
            for host in ['araveia', 'syssec-canis']:
                home = base / host
                self.assertTrue((home / '.config/fish/functions/hx-copilot.fish').is_file())
                self.assertTrue((home / '.npmrc').is_file())
                self.assertTrue((home / '.claude-ambassator/settings.json').is_file())
                launcher = home / '.local/share/applications/com.t3tools.T3Code.desktop'
                self.assertIn(str(home / 'Applications/t3code-fork/T3-Code.AppImage'), launcher.read_text())
                self.assertTrue((home / '.local/share/icons/hicolor/scalable/apps/t3code-fork.svg').is_file())
                self.assertFalse((home / 'Applications').exists(), 'Sandbox must not acquire an AppImage')
                if host == 'araveia':
                    self.assertTrue((home / '.config/pi/profiles/t3assistant/settings.json').is_file())
                    self.assertTrue((home / '.config/pi/profiles/t3assistant/auth.json').is_symlink())
                else:
                    self.assertFalse((home / '.config/pi/profiles/t3assistant').exists())
            forgejo = base / 'araveia/docs/host/forgejo/docker-compose.yml'
            self.assertTrue(forgejo.is_file())
            services = yaml.safe_load(forgejo.read_text())['services']
            for runner in ('runner', 'runner-2', 'runner-3'):
                self.assertEqual(services[runner]['user'], '12345:0')
                self.assertEqual(services[runner]['group_add'], ['12345'])
                self.assertEqual(services[runner]['profiles'], ['runner'])
            self.assertFalse((base / 'syssec-canis/docs/host/forgejo/docker-compose.yml').exists())
            self.assertTrue((base / 'araveia/.config/pi/profiles/t3assistant/mcp.json').is_file())
            self.assertFalse((base / 'syssec-canis/.config/pi/profiles/t3assistant/mcp.json').exists())
            self.assertTrue((base / 'araveia/.config/t3assistant/config.json').is_file())
            self.assertFalse((base / 'syssec-canis/.config/t3assistant').exists())
            self.assertTrue((base / 'araveia/.config/systemd/user/t3assistant-coursework.timer').is_file())
            self.assertFalse((base / 'syssec-canis/.config/systemd/user/t3assistant-coursework.timer').exists())
            self.assertTrue((base / 'araveia/.config/niri/config.kdl').is_file())
            self.assertFalse((base / 'syssec-canis/.config/niri/config.kdl').exists())


if __name__ == '__main__':
    unittest.main()
