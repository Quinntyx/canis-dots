"""Source and isolated data-copy checks; never run a backup/restore entrypoint.

DOTS_BACKUP_SOURCE may point at the owning chezmoi main source while repairing
it. Normal CI reconstructs the same scripts from the archived baseline + patch.
"""
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReinstallAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='dots-reinstall-audit-')
        cls.base = Path(cls.tmp.name)
        source = os.environ.get('DOTS_BACKUP_SOURCE')
        if source:
            folder = Path(source) / 'docs/backups/private_araveia'
            cls.backup = (folder / 'executable_backup.sh').read_text()
            cls.restore = (folder / 'executable_restore.sh').read_text()
            cls.packages = folder / 'packages'
        else:
            for name in ('backup.sh', 'restore.sh'):
                shutil.copy2(ROOT / 'docs/backups/private_araveia' / (name + '.legacy.txt'), cls.base / name)
            patch = str(ROOT / 'docs/backups/araveia-t3assistant.patch')
            subprocess.run(['git', 'apply', '--reverse', '--unidiff-zero', patch],
                           cwd=cls.base, check=True, capture_output=True)
            subprocess.run(['git', 'apply', '--unidiff-zero', patch],
                           cwd=cls.base, check=True, capture_output=True)
            cls.backup = (cls.base / 'backup.sh').read_text()
            cls.restore = (cls.base / 'restore.sh').read_text()
            cls.packages = ROOT / 'docs/backups/private_araveia/packages'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_irreplaceable_state_and_appimage_are_declared(self):
        paths = re.search(r'home_paths=\((.*?)\n\)', self.backup, re.S).group(1)
        for path in ('.local/share/t3code-fork', 'Applications/t3code-fork', '.config/t3assistant',
                     '.local/state/t3assistant', '.local/share/keyrings', '.config/claude-ambassator',
                     '.claude-ambassator', '.config/scrabblebot', '.local/share/Steam/config/libraryfolders.vdf'):
            self.assertIn(path, paths)
        for path in ('schooner', 'argo-server', '.t3/scratch'):
            self.assertNotIn(path, paths)
        databases = re.search(r'live_dbs=\((.*?)\)', self.backup, re.S).group(1)
        self.assertIn('.local/state/t3assistant/state.sqlite3', databases)
        for suffix in ('cache/', 'shell-snapshots/', 'session-env/', 'downloads/'):
            self.assertIn("--exclude='.claude-ambassator/" + suffix + "'", self.backup)

    def test_packages_match_the_reinstall_decision(self):
        packages = {line.split('#')[0].strip() for line in (self.packages / 'pacman.txt').read_text().splitlines()}
        self.assertTrue({'audacity', 'gnome-keyring', 'perf'} <= packages)
        self.assertNotIn('incus', packages)
        self.assertNotIn('t3code-fork-bin', (self.packages / 'local.txt').read_text())

    def test_restore_keeps_chezmoi_then_recreates_the_release_proxy(self):
        self.assertIn('as_user chezmoi apply --force', self.restore)
        self.assertNotIn('ansible-playbook', self.restore)
        self.assertNotIn('scripts/deploy', self.restore)
        self.assertLess(self.restore.index('step "Forgejo" forgejo'),
                        self.restore.index('step "T3 Code update proxy" t3code_update_proxy'))
        function = re.search(r't3code_update_proxy\(\) \{.*?\n\}', self.restore, re.S).group(0)
        self.assertIn('$home/.local/share/t3code-fork/hosting', function)
        self.assertIn('docker compose up -d', function)
        # Only the extracted function, with Docker replaced by a recorder.
        home = self.base / 'proxy-home'
        hosting = home / '.local/share/t3code-fork/hosting'
        hosting.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(['bash', '-c', 'set -e; home=$1; docker() { printf "%s|%s" "$PWD" "$*"; };\n' +
                                 function + '\nt3code_update_proxy', 'fixture', str(home)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(hosting) + '|compose up -d')

    def test_followup_explains_steam_and_deliberate_exclusions(self):
        notes = self.restore.split('==> manual follow-up', 1)[1]
        for text in ('SteamLibrary', 'Schooner', 'argo-server', '.t3/scratch'):
            self.assertIn(text, notes)
        self.assertNotIn('schooner-ci', notes)

    @unittest.skipUnless(shutil.which('rsync'), 'isolated restore needs rsync')
    def test_isolated_home_copy_preserves_keys_hosting_links_and_sqlite(self):
        snapshot = self.base / 'snapshot'
        home = self.base / 'restored'
        home.mkdir()
        original = snapshot / 'home'
        for rel in ('.local/share/t3code-fork/android.keystore', '.local/share/t3code-fork/android-signing.json',
                    '.local/share/t3code-fork/hosting/docker-compose.yml', '.local/share/t3code-fork/hosting/nginx.conf',
                    'Applications/t3code-fork/T3-Code.AppImage', '.local/share/keyrings/login.keyring',
                    '.config/claude-ambassator/settings.json', '.config/scrabblebot/config.json',
                    '.local/share/Steam/config/libraryfolders.vdf'):
            file = original / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'private-fixture\n')
            file.chmod(0o755 if file.suffix == '.AppImage' else 0o600)
        state = original / '.local/state/t3assistant'
        state.mkdir(parents=True)
        private = home / 'docs/omn/artifacts/t3assistant-config.private.json'
        private.parent.mkdir(parents=True)
        private.write_text('{"fixture":true}')
        private.chmod(0o600)
        (state / 'config.private.json').symlink_to(private)
        with sqlite3.connect(state / 'state.sqlite3') as database:
            database.execute('CREATE TABLE sentinel (value TEXT)')
            database.execute("INSERT INTO sentinel VALUES ('saved')")
        function = re.search(r'home_data\(\) \{.*?\n\}', self.restore, re.S).group(0)
        subprocess.run(['bash', '-c', 'set -e; user=$(id -un); home=$1; here=$2;\n' + function + '\nhome_data',
                        'fixture', str(home), str(snapshot)], check=True)
        for file in original.rglob('*'):
            restored = home / file.relative_to(original)
            if file.is_symlink():
                self.assertTrue(restored.is_symlink())
                self.assertEqual(restored.readlink(), private)
            elif file.is_file():
                self.assertEqual(restored.read_bytes(), file.read_bytes())
                self.assertEqual(restored.stat().st_mode & 0o777, file.stat().st_mode & 0o777)
        with sqlite3.connect(home / '.local/state/t3assistant/state.sqlite3') as database:
            self.assertEqual(database.execute('SELECT value FROM sentinel').fetchone()[0], 'saved')


if __name__ == '__main__':
    unittest.main()
