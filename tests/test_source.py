"""Bounded source checks; no active files, installs, services or network."""
import hashlib
import json
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
