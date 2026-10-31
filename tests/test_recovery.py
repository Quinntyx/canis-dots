"""Fresh-install recovery from the legacy private snapshot, in disposable trees only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PLAY = shutil.which('ansible-playbook')
spec = importlib.util.spec_from_file_location('dots_recover', ROOT / 'plugins/modules/dots_recover.py')
recover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recover)
SECRET = 'recovery-private-sentinel'
COUNTS = {'changed', 'created_dirs', 'created_files', 'created_links', 'matched', 'skipped_sockets', 'missing_optional', 'entries'}


def tree(path):
    return sorted(str(item.relative_to(path)) for item in path.rglob('*'))


class Recovery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='dots-recover-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.snapshot = self.base / 'snapshot'
        for part in ['home', 'root']:
            (self.snapshot / part).mkdir(parents=True, mode=0o700)
        self.snapshot.chmod(0o700)
        self.home = self.base / 'home'
        self.home.mkdir(mode=0o700)
        self.system = self.base / 'system'
        self.system.mkdir(mode=0o755)

    def put(self, relative, data=SECRET, mode=0o600, scope='home'):
        path = self.snapshot / scope / relative
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(data)
        path.chmod(mode)
        return path

    def run_home(self, entries, operation='restore', check=False, **extra):
        return recover.recover(str(self.snapshot), str(self.home), 'home', entries, operation, check, **extra)

    def assertRejected(self, entries, pattern='', scope='home', home=None):
        before = tree(home or self.home)
        with self.assertRaisesRegex(recover.RecoveryError, pattern) as caught:
            recover.recover(str(self.snapshot), str(home or self.home), scope, entries, 'restore', False)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(tree(home or self.home), before)
        return caught.exception

    def test_home_tree_restores_private_modes_skips_sockets_and_reports_counts_only(self):
        self.put('.ssh/id_ed25519')
        self.put('.ssh/id_ed25519.pub', mode=0o644)
        self.put('.ssh/hook', mode=0o755)
        self.put('.gnupg/private-keys-v1.d/key.key')
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        listener.bind(str(self.snapshot / 'home/.gnupg/S.gpg-agent'))
        self.put('.config/pi/agent/auth.json')
        entries = [dict(path='.ssh', kind='tree', required=True), dict(path='.gnupg', kind='tree', required=True),
                   dict(path='.config/pi/agent/auth.json', kind='file', required=True),
                   dict(path='.codex/auth.json', kind='file', required=False)]
        result = self.run_home(entries)
        self.assertEqual(set(result), COUNTS)
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual((result['created_files'], result['skipped_sockets'], result['missing_optional']), (5, 1, 1))
        self.assertTrue(result['changed'])
        self.assertEqual((self.home / '.ssh/id_ed25519').read_text(), SECRET)
        self.assertEqual((self.home / '.ssh/id_ed25519.pub').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.home / '.ssh/hook').stat().st_mode & 0o777, 0o700)
        for directory in ['.ssh', '.gnupg/private-keys-v1.d', '.config', '.config/pi/agent']:
            self.assertEqual((self.home / directory).stat().st_mode & 0o777, 0o700, directory)
        self.assertFalse((self.home / '.gnupg/S.gpg-agent').exists())
        self.assertEqual([name for name in tree(self.home) if '.dots-recover' in name], [])
        repeat = self.run_home(entries)
        self.assertFalse(repeat['changed'])
        self.assertEqual(repeat['created_files'] + repeat['created_dirs'], 0)

    def test_check_mode_and_validate_never_write(self):
        self.put('.git-credentials')
        entries = [dict(path='.git-credentials', kind='file', required=True)]
        self.assertTrue(self.run_home(entries, check=True)['changed'])
        validated = self.run_home(entries, operation='validate')
        self.assertFalse(validated['changed'])
        self.assertEqual(validated['created_files'], 1)
        self.assertEqual(tree(self.home), [])

    def test_whole_inventory_is_validated_before_first_write(self):
        self.put('.git-credentials')
        (self.snapshot / 'home/.config/mail-router').mkdir(parents=True, mode=0o700)
        os.mkfifo(self.snapshot / 'home/.config/mail-router/pipe', 0o600)
        self.assertRejected([dict(path='.git-credentials', kind='file', required=True),
                             dict(path='.config/mail-router', kind='tree', required=False)], 'special file')
        self.assertRejected([dict(path='.git-credentials', kind='file', required=True),
                             dict(path='.claude.json', kind='file', required=True)], 'required')

    def test_existing_destination_is_never_overwritten_and_conflicts_are_redacted(self):
        self.put('.ssh/private-name-sentinel')
        existing = self.home / '.ssh/private-name-sentinel'
        existing.parent.mkdir(mode=0o700)
        existing.write_text('current-live-bytes')
        existing.chmod(0o600)
        error = self.assertRejected([dict(path='.ssh', kind='tree', required=True)], 'conflict')
        self.assertNotIn('private-name-sentinel', str(error))
        self.assertNotIn('current-live-bytes', str(error))
        self.assertEqual(existing.read_text(), 'current-live-bytes')
        existing.write_text(SECRET)
        existing.chmod(0o644)
        self.assertRejected([dict(path='.ssh', kind='tree', required=True)], 'conflict')
        existing.chmod(0o600)
        result = self.run_home([dict(path='.ssh', kind='tree', required=True)])
        self.assertEqual((result['matched'], result['changed']), (1, False))
        link = self.home / '.claude.json'
        link.symlink_to(self.base / 'elsewhere')
        self.put('.claude.json')
        self.assertRejected([dict(path='.claude.json', kind='file', required=True)], 'conflict')
        self.assertFalse((self.base / 'elsewhere').exists())

    def test_existing_directories_are_not_adopted_or_reset(self):
        self.put('.ssh/id_ed25519')
        (self.home / '.ssh').mkdir(mode=0o755)
        self.run_home([dict(path='.ssh', kind='tree', required=True)])
        self.assertEqual((self.home / '.ssh').stat().st_mode & 0o777, 0o755)
        (self.home / '.gnupg').mkdir(mode=0o777)
        (self.home / '.gnupg').chmod(0o777)
        self.put('.gnupg/pubring.kbx')
        self.assertRejected([dict(path='.gnupg', kind='tree', required=True)], 'unsafe destination')

    def test_symlinked_source_and_destination_ancestry_are_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir(mode=0o700)
        self.put('.config/gh/hosts.yml')
        (self.home / '.config').symlink_to(outside, target_is_directory=True)
        self.assertRejected([dict(path='.config/gh/hosts.yml', kind='file', required=True)], 'symlink')
        self.assertEqual(list(outside.iterdir()), [])
        (self.home / '.config').unlink()
        real = self.base / 'real-source'
        real.mkdir(mode=0o700)
        (real / 'keys.json').write_text(SECRET)
        (self.snapshot / 'home/.local/share').mkdir(parents=True)
        (self.snapshot / 'home/.local/share/forgejo-cli').symlink_to(real, target_is_directory=True)
        self.assertRejected([dict(path='.local/share/forgejo-cli/keys.json', kind='file', required=True)], 'symlink')
        os.symlink(real / 'keys.json', self.snapshot / 'home/.git-credentials')
        self.assertRejected([dict(path='.git-credentials', kind='file', required=True)], 'not a regular file')
        linked = self.base / 'linked-home'
        linked.symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(recover.RecoveryError, 'symlink'):
            recover.recover(str(self.snapshot), str(linked), 'home', [], 'validate', False)

    def test_tree_links_only_recreate_lexical_internal_relative_targets(self):
        self.put('.local/share/cliproxyapi/auths/one.json')
        (self.snapshot / 'home/.local/share/cliproxyapi/current').symlink_to('auths/one.json')
        result = self.run_home([dict(path='.local/share/cliproxyapi', kind='tree', required=True)])
        self.assertEqual(result['created_links'], 1)
        self.assertEqual(os.readlink(self.home / '.local/share/cliproxyapi/current'), 'auths/one.json')
        for target in ['../../escape', '/etc/passwd', 'auths/../../outside']:
            self.put('.local/state/oama/token')
            link = self.snapshot / 'home/.local/state/oama/link'
            link.unlink(missing_ok=True)
            link.symlink_to(target)
            self.assertRejected([dict(path='.local/state/oama', kind='tree', required=True)], 'link')

    def test_inventory_shape_traversal_duplicates_and_overlap_are_rejected(self):
        self.put('.local/share/cliproxyapi/secrets.json')
        self.put('.local/share/cliproxyapi/auth.json')
        bad = [[dict(path='../escape', kind='file', required=True)],
               [dict(path='/etc/passwd', kind='file', required=True)],
               [dict(path='a/./b', kind='file', required=True)],
               [dict(path='.ssh/', kind='tree', required=True)],
               [dict(path='.ssh', kind='device', required=True)],
               [dict(path='.ssh', kind='tree', required='yes')],
               [dict(path='.ssh', kind='tree', required=True, mode='0644')],
               [dict(path='.x', kind='file', required=True, mode='0777')],
               [dict(path='.x', kind='file', required=True, surprise=1)],
               [dict(path='.x', kind='file', required=True)] * 2,
               [dict(path='.local/share/cliproxyapi', kind='tree', required=True),
                dict(path='.local/share/cliproxyapi/secrets.json', kind='file', required=True)]]
        for entries in bad:
            self.assertRejected(entries, 'inventory')
        result = self.run_home([dict(path='.local/share/cliproxyapi', kind='tree', required=True, exclude=['secrets.json']),
                                dict(path='.local/share/cliproxyapi/secrets.json', kind='file', required=True)])
        self.assertEqual(result['created_files'], 2)

    def test_snapshot_must_be_private_and_owner_controlled(self):
        self.put('.git-credentials')
        entries = [dict(path='.git-credentials', kind='file', required=True)]
        self.snapshot.chmod(0o755)
        self.assertRejected(entries, 'snapshot')
        self.snapshot.chmod(0o700)
        (self.snapshot / 'home/.git-credentials').chmod(0o622)
        self.assertRejected(entries, 'snapshot')
        (self.snapshot / 'home/.git-credentials').chmod(0o600)
        self.put('etc/cloudflared/token', scope='root')
        system = [dict(path='etc/cloudflared/token', kind='file', required=True)]
        with mock.patch.object(recover.os, 'geteuid', return_value=os.geteuid() + 4242):
            self.assertRejected(system, 'snapshot', scope='system', home=self.system)

    def test_home_ownership_is_inferred_or_asserted_and_preexisting_trees_are_not_chowned(self):
        self.put('.config/mail-router/key')
        (self.home / '.config').mkdir(mode=0o700)
        info = self.home.stat()
        with self.assertRaisesRegex(recover.RecoveryError, 'owner'):
            self.run_home([], owner=info.st_uid + 4242)
        with self.assertRaisesRegex(recover.RecoveryError, 'scope'):
            recover.recover(str(self.snapshot), str(self.system), 'system', [], 'validate', False, owner=info.st_uid)
        calls = []
        real_chown = os.chown

        def record(path, uid, gid, **kwargs):
            calls.append((path, uid, gid))
            return real_chown(path, uid, gid, **kwargs)

        with mock.patch.object(recover.os, 'fchown', side_effect=lambda fd, uid, gid: calls.append((fd, uid, gid))), \
                mock.patch.object(recover.os, 'chown', side_effect=record):
            result = self.run_home([dict(path='.config/mail-router', kind='tree', required=False)])
        self.assertEqual((result['created_dirs'], result['created_files']), (1, 1))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call[1:] == (info.st_uid, info.st_gid) for call in calls))

    def test_system_scope_uses_root_subtree_explicit_public_host_key_mode_and_existing_parents(self):
        self.put('var/lib/tailscale/tailscaled.state', scope='root')
        self.put('etc/ssh/ssh_host_ed25519_key', scope='root')
        self.put('etc/ssh/ssh_host_ed25519_key.pub', 'public-key', mode=0o644, scope='root')
        self.put('etc/cloudflared/token', scope='root')
        (self.system / 'etc/ssh').mkdir(parents=True, mode=0o755)
        (self.system / 'etc/ssh').chmod(0o755)
        policy = json.loads((ROOT / 'policy/recovery.yml').read_text())['araveia']['system']
        result = recover.recover(str(self.snapshot), str(self.system), 'system', policy, 'restore', False)
        self.assertEqual((result['created_files'], result['missing_optional']), (4, 4))
        self.assertEqual((self.system / 'etc/ssh/ssh_host_ed25519_key.pub').stat().st_mode & 0o777, 0o644)
        self.assertEqual((self.system / 'etc/ssh/ssh_host_ed25519_key').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.system / 'etc/ssh').stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.system / 'var/lib/tailscale').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.system / 'etc/cloudflared/token').read_text(), SECRET)

    def test_policy_is_exact_json_and_excludes_replayed_system_state(self):
        policy = json.loads((ROOT / 'policy/recovery.yml').read_text())
        self.assertEqual(set(policy), set(json.loads((ROOT / 'inventory/hosts.yml').read_text())['all']['children']['workstations']['hosts']))
        araveia = policy['araveia']
        recover.validate_inventory(araveia['home'])
        recover.validate_inventory(araveia['system'])
        system = {entry['path']: entry for entry in araveia['system']}
        keys = {'etc/ssh/ssh_host_%s_key%s' % (kind, suffix) for kind in ['ed25519', 'rsa', 'ecdsa'] for suffix in ['', '.pub']}
        self.assertEqual(set(system), keys | {'var/lib/tailscale/tailscaled.state', 'etc/cloudflared/token'})
        self.assertTrue(system['var/lib/tailscale/tailscaled.state']['required'] and system['etc/cloudflared/token']['required'])
        self.assertTrue(all(not system[key]['required'] and system[key].get('mode', '0600') == ('0644' if key.endswith('.pub') else '0600') for key in keys))
        home = {entry['path']: entry for entry in araveia['home']}
        secrets = {entry['dest'] for entry in json.loads((ROOT / 'policy/secrets.yml').read_text())['araveia']}
        self.assertEqual({path for path in secrets if not path.startswith('docs/')} - set(home), set())
        self.assertTrue(home['.local/share/cliproxyapi/secrets.json']['required'])
        self.assertEqual(home['.local/share/cliproxyapi']['exclude'], ['secrets.json'])
        self.assertTrue(home['.ssh']['required'] and home['.gnupg']['required'] and home['.config/pi/agent/auth.json']['required'])
        for forbidden in ['.config/pi', '.pi', '.claude', '.config/pi/shared', '.codex', 'src', 'downs', '.config/opencode']:
            self.assertNotIn(forbidden, home)
        self.assertFalse([path for path in home if path.startswith('docs/')])
        self.assertEqual(policy['syssec-canis'], {'home': [], 'system': []})


@unittest.skipUnless(PLAY, 'Requires project-local ansible-core')
class RecoveryAnsible(unittest.TestCase):
    def test_real_ansible_restore_check_mode_and_no_payload_in_output(self):
        with tempfile.TemporaryDirectory(prefix='dots-recover-play-') as temp:
            base = Path(temp)
            snapshot = base / 'snapshot'
            (snapshot / 'home/.config/gh').mkdir(parents=True, mode=0o700)
            for path in [snapshot, snapshot / 'home', snapshot / 'home/.config', snapshot / 'home/.config/gh']:
                path.chmod(0o700)
            (snapshot / 'home/.config/gh/hosts.yml').write_text(SECRET)
            home = base / 'home'
            home.mkdir(mode=0o700)
            playbook = base / 'recover.yml'
            playbook.write_text(json.dumps([{'hosts': 'localhost', 'gather_facts': False, 'tasks': [
                {'name': 'Recover', 'no_log': True, 'register': 'recovered',
                 'dots_recover': {'snapshot': str(snapshot), 'home': str(home), 'scope': 'home', 'operation': 'restore',
                                  'entries': [{'path': '.config/gh/hosts.yml', 'kind': 'file', 'required': True},
                                              {'path': '.codex/auth.json', 'kind': 'file', 'required': False}]}},
                {'ansible.builtin.assert': {'that': ['recovered.created_files == expected', 'recovered.missing_optional == 1']}}]}]))
            env = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg'))

            def play(expected, check=False):
                command = [PLAY, str(playbook), '-i', 'localhost,', '--connection', 'local',
                           '-e', json.dumps(dict(expected=expected, ansible_python_interpreter=sys.executable))]
                result = subprocess.run(command + (['--check'] if check else []), cwd=ROOT, env=env, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout[-6000:])
                self.assertNotIn(SECRET, result.stdout)
                return result

            play(1, check=True)
            self.assertEqual(list(home.iterdir()), [])
            play(1)
            self.assertEqual((home / '.config/gh/hosts.yml').read_text(), SECRET)
            self.assertRegex(play(0).stdout, r'changed=0\s+unreachable=0\s+failed=0')
            (home / '.config/gh/hosts.yml').write_text('changed-live')
            command = [PLAY, str(playbook), '-i', 'localhost,', '--connection', 'local',
                       '-e', json.dumps(dict(expected=0, ansible_python_interpreter=sys.executable))]
            failed = subprocess.run(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual((home / '.config/gh/hosts.yml').read_text(), 'changed-live')
            self.assertNotIn(SECRET, failed.stdout)


if __name__ == '__main__':
    unittest.main()
