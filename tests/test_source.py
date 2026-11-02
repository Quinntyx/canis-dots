"""Bounded source checks; no active files, installs, services or network."""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SourceTests(unittest.TestCase):
    def test_inventory_enrollment_is_explicit(self):
        inventory = yaml.safe_load((ROOT / 'inventory/hosts.yml').read_text())
        hosts = inventory['all']['children']['workstations']['hosts']
        self.assertEqual(set(hosts), {'araveia', 'syssec-canis'})

    def test_role_sources_match_the_reviewed_conversion(self):
        # Compact test receipt, not a deployment manifest. Update intentionally
        # when changing owned static files; tasks still own all destinations.
        expected = json.loads((ROOT / 'tests/fixtures/config-digests.json').read_text())
        actual = {}
        for role in sorted((ROOT / 'roles').iterdir()):
            source = role / 'files'
            entries = []
            if source.exists():
                for path in sorted(source.rglob('*'), key=str):
                    if path.is_file():
                        entries.append(str(path.relative_to(source)) + '\0' +
                                       hashlib.sha256(path.read_bytes()).hexdigest())
            if entries:
                actual[role.name] = {'count': len(entries),
                    'sha256': hashlib.sha256('\n'.join(entries).encode()).hexdigest()}
        self.assertEqual(actual, expected)

    def test_yaml_sources_parse_and_no_custom_plugins_remain(self):
        for folder in ('roles', 'playbooks', 'inventory', 'policy', 'secrets', '.forgejo/workflows'):
            for path in (ROOT / folder).rglob('*.yml'):
                if '/files/' not in str(path) and not path.read_bytes().startswith(b'$ANSIBLE_VAULT;'):
                    yaml.safe_load(path.read_text())
        self.assertFalse((ROOT / 'plugins').exists())
        self.assertFalse(list((ROOT / 'roles').glob('*/manifest.yml')))

    def test_owned_guidance_points_to_current_native_source(self):
        for relative in ('roles/agents/files/common/0644/.claude/CLAUDE.md',
            'roles/agents/files/common/0644/.config/pi/profiles/main/APPEND_SYSTEM.md',
            'roles/agents/files/common/0644/.config/pi/profiles/t3main/APPEND_SYSTEM.md'):
            text = (ROOT / relative).read_text()
            self.assertIn('roles/<role>/tasks/config.yml', text)
            self.assertIn('Ansible Vault', text)
            for stale in ('scripts/dots-source', 'dots-source.json', 'policy/secrets.yml', 'encrypted_files/<host>'):
                self.assertNotIn(stale, text, relative)

    def test_coursework_profile_and_units_are_strictly_araveia_only(self):
        profile = Path('.config/pi/profiles/t3assistant')
        self.assertFalse((ROOT / 'roles/agents/files/common/0644' / profile).exists())
        self.assertTrue((ROOT / 'roles/agents/files/araveia/0644' / profile / 'settings.json').is_file())
        values = yaml.safe_load((ROOT / 'roles/agents/vars/main.yml').read_text())
        self.assertNotIn(str(profile), values['dots_pi_shared_dirs'])
        self.assertIn(str(profile), values['dots_pi_main_dirs'])
        for unit in (ROOT / 'roles/desktop/files/araveia/0644/.config/systemd/user').glob('t3assistant-*'):
            self.assertIn('ConditionHost=araveia', unit.read_text(), str(unit))
        services = yaml.safe_load((ROOT / 'inventory/group_vars/all.yml').read_text())['dots_service_units']
        self.assertEqual(services['coursework'], ['t3assistant-coursework.timer'])

    def test_existing_restore_patch_preserves_coursework_private_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in ('backup.sh', 'restore.sh'):
                shutil.copy2(ROOT / 'docs/backups/private_araveia' / (name + '.legacy.txt'), base / name)
            result = subprocess.run(['git', 'apply', '--unidiff-zero', str(ROOT / 'docs/backups/araveia-t3assistant.patch')],
                                    cwd=base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(['bash', '-n', str(base / 'backup.sh'), str(base / 'restore.sh')], check=True)
            backup = (base / 'backup.sh').read_text()
            paths = re.search(r'home_paths=\((.*?)\n\)', backup, re.S).group(1)
            self.assertIn('.config/t3assistant', paths)
            self.assertIn('.local/state/t3assistant', paths)
            self.assertIn('Applications/t3code-fork', paths)
            databases = re.search(r'live_dbs=\((.*?)\)', backup, re.S).group(1)
            self.assertIn('.local/state/t3assistant/state.sqlite3', databases)
            restore = (base / 'restore.sh').read_text()
            self.assertIn('this restore procedure is only for araveia', restore)
            self.assertLess(restore.index('command -v ansible-playbook'), restore.index('step "hostname'))
            self.assertNotIn('hostnamectl set-hostname', restore)
            as_user = re.search(r'as_user\(\) \{.*?\n\}', restore, re.S).group(0)
            self.assertIn('NPM_CONFIG_PREFIX="$home/.npm-global"', as_user)
            environment_test = ('user=fixture; uid=1000; home=$1; '
                                'sudo() { shift 3; "$@"; };\n' + as_user +
                                '\nas_user bash -c \'printf "%s" "$NPM_CONFIG_PREFIX"\'\n')
            environment = subprocess.run(['bash', '-c', environment_test, 'fixture', str(base / 'npm-home')],
                                         capture_output=True, text=True, check=True)
            self.assertEqual(environment.stdout, str(base / 'npm-home/.npm-global'))
            self.assertNotIn('as_user chezmoi', restore)
            self.assertIn('as_user "$source/scripts/deploy"', restore)
            self.assertLess(restore.index('step "Forgejo" forgejo'),
                            restore.index('step "Ansible configuration'))
            if shutil.which('rsync'):
                # Execute only the existing home-data function on artificial
                # files. Never source/run the privileged restore entrypoint.
                snapshot = base / 'snapshot'
                home = base / 'restored'
                home.mkdir()
                for rel in ('.config/t3assistant/config.json',
                            '.local/state/t3assistant/config.private.json',
                            '.local/state/t3assistant/oauth-token.json',
                            'Applications/t3code-fork/T3-Code.AppImage'):
                    file = snapshot / 'home' / rel
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text('{"fixture":true}\n')
                    file.chmod(0o755 if file.suffix == '.AppImage' else 0o600)
                function = re.search(r'home_data\(\) \{.*?\n\}', restore, re.S).group(0)
                command = 'set -e; user=$(id -un); home=$1; here=$2;\n' + function + '\nhome_data\n'
                subprocess.run(['bash', '-c', command, 'fixture', str(home), str(snapshot)], check=True)
                for original in (snapshot / 'home').rglob('*'):
                    if original.is_file():
                        restored = home / original.relative_to(snapshot / 'home')
                        self.assertEqual(restored.read_bytes(), original.read_bytes())
                        self.assertEqual(restored.stat().st_mode & 0o777, original.stat().st_mode & 0o777)

    def test_workflow_keeps_privilege_in_main_deployment_and_is_serial(self):
        workflow = yaml.safe_load((ROOT / '.forgejo/workflows/ansible.yml').read_text())
        self.assertEqual(workflow['on']['push']['branches'], ['main'])
        jobs = workflow['jobs']
        self.assertEqual(jobs['deploy']['needs'], 'check')
        self.assertIn("forgejo.ref == 'refs/heads/main'", jobs['deploy']['if'])
        self.assertIn("forgejo.event_name != 'pull_request'", jobs['deploy']['if'])
        self.assertFalse(jobs['deploy']['concurrency']['cancel-in-progress'])
        self.assertNotIn('secrets.', json.dumps(jobs['check']))
        deploy = jobs['deploy']['steps'][-1]
        self.assertEqual(set(deploy['env']), {'ANSIBLE_VAULT_PASSWORD', 'ANSIBLE_SSH_PRIVATE_KEY',
            'ANSIBLE_KNOWN_HOSTS', 'ANSIBLE_SSH_USER', 'ANSIBLE_BECOME_PASSWORD'})
        self.assertIn('StrictHostKeyChecking=yes', deploy['run'])
        self.assertNotIn('ssh-keyscan', deploy['run'].replace('not runtime ssh-keyscan output', ''))
        play = yaml.safe_load((ROOT / 'playbooks/site.yml').read_text())[0]
        self.assertEqual(play['serial'], 1)
        self.assertEqual(play['hosts'], 'workstations')


if __name__ == '__main__':
    unittest.main()
