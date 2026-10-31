"""Focused regressions from the independent Opus review; disposable state only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ReviewRegressions(unittest.TestCase):
    def test_vault_file_extension_is_trackable_and_prompts(self):
        ignored = subprocess.run(['git', 'check-ignore', '--no-index', 'secrets/cliproxyapi.vault'],
                                 cwd=ROOT, capture_output=True)
        self.assertEqual(ignored.returncode, 1, ignored.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'scripts').mkdir()
            (base / 'secrets').mkdir()
            (base / 'bin').mkdir()
            shutil.copy2(ROOT / 'scripts/deploy', base / 'scripts/deploy')
            (base / 'secrets/payload.vault').write_text('$ANSIBLE_VAULT;1.1;AES256\nfixture-only\n')
            mock = base / 'bin/ansible-playbook'
            mock.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            mock.chmod(0o755)
            env = dict(os.environ, PATH=str(base / 'bin') + ':' + os.environ['PATH'])
            env.pop('ANSIBLE_VAULT_PASSWORD_FILE', None)
            result = subprocess.run([str(base / 'scripts/deploy'), '--host', 'araveia'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--ask-vault-pass', result.stdout)

    def test_owned_build_cache_is_retryable_and_uses_verified_git_route(self):
        tasks = yaml.safe_load((ROOT / 'roles/software/tasks/build-package.yml').read_text())
        acquire = tasks[0]
        self.assertTrue(acquire['ansible.builtin.git']['force'])
        for task in tasks:
            if task.get('become_user') == '{{ software_builder_user }}':
                self.assertIn('dots_git_environment', str(task['environment']), task['name'])

    def test_legacy_chezmoi_apply_cannot_install_the_ansible_tree(self):
        self.assertEqual((ROOT / '.chezmoiignore').read_text().strip(), '*')

    def test_layout_links_allow_missing_runtime_targets_but_preserve_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            target = home / '.config/pi/profiles/main/git'
            play = base / 'play.yml'
            play.write_text(json.dumps([{'hosts': 'localhost', 'gather_facts': False,
                'vars': {'dots_home': str(home), 'dots_controller_root': str(ROOT),
                         'config_dest': '.config/pi/profiles/main/git', 'config_target': '../../git'},
                'tasks': [{'ansible.builtin.include_tasks': str(ROOT / 'roles/common/tasks/link.yml')}]}]))
            def run():
                return subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(play)],
                    cwd=ROOT, env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg')),
                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            result = run()
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(target.is_symlink())
            self.assertFalse(target.exists())  # The package manager creates its target later.
            target.rename(base / 'old-link')
            target.write_text('runtime-owned file')
            self.assertNotEqual(run().returncode, 0)
            self.assertEqual(target.read_text(), 'runtime-owned file')

    def test_personal_checkouts_keep_branch_and_unpushed_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / 'home'
            home.mkdir()
            remote = base / 'origin.git'
            seed = base / 'seed'
            def git(*args, cwd=None):
                return subprocess.check_output(['git', *args], cwd=cwd, text=True,
                    stderr=subprocess.STDOUT).strip()
            git('init', '--bare', str(remote))
            git('init', '-b', 'main', str(seed))
            git('config', 'user.name', 'Fixture', cwd=seed)
            git('config', 'user.email', 'fixture@example.invalid', cwd=seed)
            (seed / 'tracked').write_text('base\n')
            git('add', 'tracked', cwd=seed)
            git('commit', '-m', 'base', cwd=seed)
            git('remote', 'add', 'origin', str(remote), cwd=seed)
            git('push', 'origin', 'main', cwd=seed)
            git('symbolic-ref', 'HEAD', 'refs/heads/main', cwd=remote)
            destinations = [home / 'docs/src/CLIProxyAPI/main', home / 'docs/host/quinntyx-dev']
            expected = []
            for destination in destinations:
                destination.parent.mkdir(parents=True, exist_ok=True)
                git('clone', str(remote), str(destination))
                git('config', 'user.name', 'Fixture', cwd=destination)
                git('config', 'user.email', 'fixture@example.invalid', cwd=destination)
                (destination / 'tracked').write_text('local main commit\n')
                git('add', 'tracked', cwd=destination)
                git('commit', '-m', 'unpushed', cwd=destination)
                git('checkout', '-b', 'personal-feature', cwd=destination)
                expected.append(git('rev-parse', 'HEAD', cwd=destination))
            mock_go = base / 'go'
            mock_go.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n'
                'if [ "$1" = -o ]; then shift; printf fixture > "$1"; exit 0; fi\nshift\ndone\nexit 1\n')
            mock_go.chmod(0o755)
            tasks = [
                {'ansible.builtin.include_tasks': str(ROOT / 'roles/cliproxyapi/tasks/build.yml')},
                {'ansible.builtin.include_tasks': str(ROOT / 'roles/website/tasks/main.yml')},
            ]
            play = base / 'play.yml'
            play.write_text(json.dumps([{'hosts': 'localhost', 'gather_facts': False,
                'vars': {'dots_home': str(home), 'dots_sandbox': False, 'dots_manage_externals': True,
                    'dots_manage_services': False, 'dots_git_environment': {},
                    'dots_cliproxyapi_repo': str(remote), 'dots_cliproxyapi_revision': 'main',
                    'dots_website_repo': str(remote), 'dots_website_revision': 'main',
                    'dots_go_binary': str(mock_go)}, 'tasks': tasks}]))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(play)],
                cwd=ROOT, env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg')),
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(result.returncode, 0, result.stdout)
            for destination, revision in zip(destinations, expected):
                self.assertEqual(git('branch', '--show-current', cwd=destination), 'personal-feature')
                self.assertEqual(git('rev-parse', 'HEAD', cwd=destination), revision)
                self.assertEqual(git('rev-parse', 'main', cwd=destination), revision)


if __name__ == '__main__':
    unittest.main()
