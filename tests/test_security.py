"""Real Ansible boundary regressions, wholly inside private disposable directories."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLAY = shutil.which('ansible-playbook')
spec = importlib.util.spec_from_file_location('deployment', ROOT / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


@unittest.skipUnless(PLAY, 'Requires project-local ansible-core')
class SecurityBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-security-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'
        self.home.mkdir()
        self.key = self.base / 'key'
        self.key.write_bytes(b'disposable-only-vault-key\n')
        self.key.chmod(0o600)
        from ansible.parsing.vault import VaultLib, VaultSecret
        self.vault = VaultLib([('default', VaultSecret(self.key.read_bytes().strip()))])
        self.env = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg'),
                        DOTS_VAULT_ROOT=str(self.base / 'vault'), DOTS_VAULT_PASSWORD_FILE=str(self.key))

    def run_play(self, playbook, extra, key=None, check=False):
        variables = dict(dots_home=str(self.home), dots_vault_root=str(self.base / 'vault'),
                         dots_sandbox=True, dots_manage_packages=False, dots_manage_externals=False,
                         dots_manage_services=False, dots_install_agent_tools=False,
                         dots_controller_root=str(ROOT), ansible_python_interpreter=sys.executable)
        variables.update(extra)
        command = [PLAY, str(playbook), '--limit', 'syssec-canis', '--connection', 'local',
                   '--vault-password-file', str(key or self.key), '-e', json.dumps(variables)]
        if check:
            command.append('--check')
        return subprocess.run(command, cwd=ROOT, env=self.env, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=120)

    def require_ok(self, run):
        self.assertEqual(run.returncode, 0, run.stdout[-10000:])

    def backup(self, entries, host='syssec-canis'):
        path = self.base / 'restore.vault'
        path.write_bytes(self.vault.encrypt(json.dumps(dict(version=1, host=host, files=entries)).encode()))
        return path

    def test_rollback_authentication_check_mode_and_preimage(self):
        target = self.home / 'owned'
        target.write_text('current-sentinel')
        artifact = self.backup([dict(dest='owned', kind='file', mode='0600', data=base64.b64encode(b'old-sentinel').decode()),
                                dict(dest='leave-new', kind='absent')])
        (self.home / 'leave-new').write_text('never-delete-me')
        extra = dict(dots_restore_backup=str(artifact))
        wrong = self.base / 'wrong'
        wrong.write_text('wrong-key')
        wrong.chmod(0o600)
        rejected = self.run_play(ROOT / 'playbooks/rollback.yml', extra, key=wrong)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(target.read_text(), 'current-sentinel')
        self.require_ok(self.run_play(ROOT / 'playbooks/rollback.yml', extra, check=True))
        self.assertEqual(target.read_text(), 'current-sentinel')
        self.require_ok(self.run_play(ROOT / 'playbooks/rollback.yml', extra))
        self.assertEqual(target.read_text(), 'old-sentinel')
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.home / 'leave-new').read_text(), 'never-delete-me')
        backups = list((self.base / 'vault/backups/syssec-canis').glob('*.vault'))
        self.assertEqual(len(backups), 1)
        snapshot = json.loads(self.vault.decrypt(backups[0].read_bytes()))
        self.assertEqual(base64.b64decode(snapshot['files'][0]['data']), b'current-sentinel')
        repeat = self.run_play(ROOT / 'playbooks/rollback.yml', extra)
        self.require_ok(repeat)
        self.assertRegex(repeat.stdout, r'changed=0\s+unreachable=0\s+failed=0')
        self.assertNotIn('current-sentinel', repeat.stdout)

    def test_rollback_validates_whole_archive_before_first_write(self):
        (self.home / 'owned').write_text('must-stay-current')
        artifact = self.backup([dict(dest='owned', kind='file', mode='0600', data=base64.b64encode(b'replacement').decode()),
                                dict(dest='bad', kind='file', mode='0600', data='%%%invalid-base64%%%')])
        rejected = self.run_play(ROOT / 'playbooks/rollback.yml', dict(dots_restore_backup=str(artifact)))
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual((self.home / 'owned').read_text(), 'must-stay-current')

    def test_import_is_encrypted_allowlisted_private_and_rejects_wrong_key(self):
        source = self.base / 'private-source'
        source.write_text('private-import-sentinel')
        command = [sys.executable, str(ROOT / 'scripts/vault-tools.py'), 'import', '--host', 'araveia',
                   '--dest', '.local/share/cliproxyapi/secrets.json', '--source', str(source)]
        result = subprocess.run(command, cwd=ROOT, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = self.base / 'vault/encrypted_files/araveia/.local/share/cliproxyapi/secrets.json.vault'
        self.assertTrue(payload.read_bytes().startswith(b'$ANSIBLE_VAULT;'))
        self.assertEqual(self.vault.decrypt(payload.read_bytes()), b'private-import-sentinel')
        self.assertEqual(payload.stat().st_mode & 0o777, 0o600)
        self.assertEqual(payload.parent.stat().st_mode & 0o777, 0o700)
        self.assertNotIn('private-import-sentinel', result.stdout + result.stderr)
        old = payload.read_bytes()
        self.key.write_text('wrong-key')
        result = subprocess.run(command, cwd=ROOT, env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload.read_bytes(), old)
        self.assertFalse((ROOT / '.vault').exists())

    def test_controller_wrong_key_and_symlinked_ancestry_fail_before_mutation(self):
        root = self.base / 'vault'
        (root / 'backups/syssec-canis').mkdir(parents=True)
        artifact = root / 'backups/syssec-canis/previous.vault'
        artifact.write_bytes(self.vault.encrypt(b'old-preimage'))
        with self.assertRaisesRegex(ValueError, 'authentication failed'):
            deploy.prepare_secrets('syssec-canis', ['shell'], root, b'wrong', None, False)
        outside = self.base / 'outside'
        outside.mkdir()
        link = self.base / 'indirect'
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            deploy.private_directory(link / 'nested')
        self.assertEqual(list(outside.iterdir()), [])

    def test_secret_rotation_changes_service_activation_input(self):
        source = self.base / 'test-secret.vault'
        source.write_bytes(self.vault.encrypt(b'first-private-sentinel'))
        observer = self.base / 'observe.yml'
        observer.write_text('- import_playbook: ' + str(ROOT / 'playbooks/site.yml') + '\n'
                            '- hosts: workstations\n  gather_facts: false\n  tasks:\n'
                            '    - ansible.builtin.assert:\n'
                            '        that: dots_configuration_changed == expect_changed\n')
        extra = dict(dots_requested_components=['shell'], dots_secret_files=[dict(component='shell',
                     dest='.config/test-private', source=str(source), encrypted=True)], expect_changed=True)
        self.require_ok(self.run_play(observer, extra))
        extra['expect_changed'] = False
        self.require_ok(self.run_play(observer, extra))
        source.write_bytes(self.vault.encrypt(b'rotated-private-sentinel'))
        extra['expect_changed'] = True
        result = self.run_play(observer, extra)
        self.require_ok(result)
        self.assertEqual((self.home / '.config/test-private').read_bytes(), b'rotated-private-sentinel')
        self.assertNotIn('rotated-private-sentinel', result.stdout)

    def test_declared_leaf_symlink_is_replaced_without_writing_its_target(self):
        manifest = json.loads((ROOT / 'roles/shell/manifest.yml').read_text())
        entry = next(item for item in manifest if item['kind'] == 'file')
        target = self.home / entry['dest']
        target.parent.mkdir(parents=True, exist_ok=True)
        outside = self.base / 'untouched-outside'
        outside.write_text('unowned-outside-sentinel')
        target.symlink_to(outside)
        self.require_ok(self.run_play(ROOT / 'playbooks/site.yml', dict(dots_requested_components=['shell'])))
        self.assertEqual(outside.read_text(), 'unowned-outside-sentinel')
        self.assertFalse(target.is_symlink())

    def test_failed_proxy_upgrade_retries_after_checkout_already_advanced(self):
        repository = self.base / 'repo'
        repository.mkdir()
        (repository / 'source.txt').write_text('disposable source')
        subprocess.run(['git', 'init', '-q', str(repository)], check=True)
        subprocess.run(['git', '-C', str(repository), 'add', 'source.txt'], check=True)
        subprocess.run(['git', '-C', str(repository), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                        'commit', '-qm', 'disposable revision'], check=True)
        revision = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
        binary = self.home / '.local/lib/cliproxyapi/cli-proxy-api'
        binary.parent.mkdir(parents=True)
        binary.write_text('old-binary-sentinel')
        go = self.base / 'fake-go'
        go.write_text('#!/bin/sh\nset -eu\nprintf x >> "' + str(self.base / 'attempts') + '"\n'
                      'test -f "' + str(self.base / 'allow-build') + '" || exit 9\n'
                      'printf "new-binary-sentinel" > "$4"\n')
        go.chmod(0o700)
        playbook = self.base / 'build.yml'
        playbook.write_text('- hosts: workstations\n  gather_facts: false\n  tasks:\n'
                            '    - ansible.builtin.include_tasks: ' + str(ROOT / 'roles/cliproxyapi/tasks/build.yml') + '\n')
        extra = dict(dots_cliproxyapi_repo=str(repository), dots_cliproxyapi_revision=revision, dots_go_binary=str(go))
        failed = self.run_play(playbook, extra)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(binary.read_text(), 'old-binary-sentinel')
        self.assertFalse((binary.parent / 'build-revision').exists())
        (self.base / 'allow-build').touch()
        self.require_ok(self.run_play(playbook, extra))
        self.assertEqual(binary.read_text(), 'new-binary-sentinel')
        self.assertEqual((binary.parent / 'build-revision').read_text().strip(), revision)
        repeat = self.run_play(playbook, extra)
        self.require_ok(repeat)
        self.assertRegex(repeat.stdout, r'changed=0\s+unreachable=0\s+failed=0')
        self.assertEqual((self.base / 'attempts').read_text(), 'xx')


if __name__ == '__main__':
    unittest.main()
