"""Real Ansible against a loopback-only fake AppImage, never executed or installed."""
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = shutil.which('ansible-playbook')


@unittest.skipUnless(PLAYBOOK, 'Project-local ansible-core required')
class AppImageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dots-appimage-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.home = self.base / 'home with spaces'
        self.home.mkdir()
        self.destination = self.home / 'Applications/t3code-fork/T3-Code.AppImage'
        self.payload = b'fake fixture AppImage; never execute\n'
        feed = self.base / 'feed'
        feed.mkdir()
        (feed / 'T3-Code-fixture-x86_64.AppImage').write_bytes(self.payload)
        requests = self.requests = []

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                super().do_GET()

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(feed)))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)
        self.bootstrap = {'url': f'http://127.0.0.1:{self.server.server_port}/T3-Code-fixture-x86_64.AppImage',
                          'checksum': 'sha512:' + hashlib.sha512(self.payload).hexdigest()}

    def stop_server(self):
        if self.worker.is_alive():
            self.server.shutdown()
            self.server.server_close()
            self.worker.join(timeout=5)

    def play(self, host='araveia', check=False, launcher=False, entrypoint=False, **variables):
        tasks_from = 'main' if entrypoint else 'appimage'
        role = ROOT / 'roles/software'
        if launcher:
            role, tasks_from = ROOT / 'roles/desktop', 't3code'
        play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                 'tasks': [{'ansible.builtin.include_role': {'name': str(role), 'tasks_from': tasks_from}}]}]
        playbook = self.base / 'play.yml'
        playbook.write_text(yaml.safe_dump(play))
        extra = {'dots_controller_root': str(ROOT), 'dots_home': str(self.home),
                 'dots_user': 'fixture', 'dots_uid': os.getuid(), 'dots_sandbox': True,
                 'inventory_hostname': host, 'ansible_facts': {'architecture': 'x86_64'},
                 'ansible_become': False, 'ansible_become_exe': '/nonexistent-become-tripwire',
                 'ansible_python_interpreter': sys.executable, 'software_t3code_bootstrap': self.bootstrap}
        extra.update(variables)
        extra_file = self.base / 'vars.json'
        extra_file.write_text(json.dumps(extra))
        return subprocess.run([PLAYBOOK, '-i', 'localhost,', str(playbook), '-e', '@' + str(extra_file)] +
                              (['--check'] if check else []), cwd=ROOT,
                              env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg'), ANSIBLE_NOCOWS='1'),
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)

    def test_missing_bootstrap_then_offline_repeat_preserves_self_updated_bytes(self):
        first = self.play()
        self.assertEqual(first.returncode, 0, first.stdout[-5000:])
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o755)
        self.assertEqual(len(self.requests), 1)
        updated = b'a newer version installed by the built-in updater\n'
        self.destination.write_bytes(updated)
        self.stop_server()
        repeat = self.play()
        self.assertEqual(repeat.returncode, 0, repeat.stdout[-5000:])
        self.assertEqual(self.destination.read_bytes(), updated)
        self.assertIn('changed=0', repeat.stdout)

    def test_bad_checksum_leaves_no_partial_install_and_retry_succeeds(self):
        bad = dict(self.bootstrap, checksum='sha512:' + '0' * 128)
        result = self.play(software_t3code_bootstrap=bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())
        retry = self.play()
        self.assertEqual(retry.returncode, 0, retry.stdout[-5000:])
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_destination_and_ancestor_links_are_refused_without_network_or_victim_change(self):
        victim = self.base / 'victim'
        victim.write_bytes(b'preserve me')
        self.destination.parent.mkdir(parents=True)
        self.destination.symlink_to(victim)
        result = self.play()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(victim.read_bytes(), b'preserve me')
        self.assertFalse(self.requests)
        # Use a separate disposable home to exercise an ancestor link.
        self.home = self.base / 'other-home'
        self.home.mkdir()
        (self.home / 'Applications').symlink_to(self.destination.parent, target_is_directory=True)
        result = self.play()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.requests)
        self.assertEqual(victim.read_bytes(), b'preserve me')

    def test_lab_check_mode_and_normal_sandbox_entrypoint_do_not_acquire(self):
        for variables in ({'host': 'syssec-canis'}, {'check': True}, {'entrypoint': True}):
            with self.subTest(variables=variables):
                result = self.play(**variables)
                self.assertEqual(result.returncode, 0, result.stdout[-5000:])
                self.assertFalse((self.home / 'Applications').exists())
                self.assertFalse(self.requests)

    def test_launcher_uses_portable_quoted_appimage_and_refuses_destination_links(self):
        result = self.play(launcher=True)
        self.assertEqual(result.returncode, 0, result.stdout[-5000:])
        launcher = self.home / '.local/share/applications/com.t3tools.T3Code.desktop'
        text = launcher.read_text()
        self.assertIn(f'Exec="{self.destination}" %U', text)
        self.assertIn('MimeType=x-scheme-handler/t3code;', text)
        self.assertNotIn('/opt/', text)
        self.assertNotIn('NoDisplay=true', text)
        repeat = self.play(launcher=True)
        self.assertEqual(repeat.returncode, 0, repeat.stdout[-5000:])
        self.assertIn('changed=0', repeat.stdout)
        other_home = self.base / 'lab'
        other_home.mkdir()
        lab = self.play(host='syssec-canis', launcher=True, dots_home=str(other_home))
        self.assertEqual(lab.returncode, 0, lab.stdout[-5000:])
        self.assertFalse((other_home / '.local').exists())
        special_home = self.base / 'home $cash'
        special_home.mkdir()
        escaped = self.play(launcher=True, dots_home=str(special_home))
        self.assertEqual(escaped.returncode, 0, escaped.stdout[-5000:])
        special_text = (special_home / launcher.relative_to(self.home)).read_text()
        # Desktop string unescaping happens before Exec argument unquoting.
        self.assertIn(str(special_home).replace('$', r'\\$'), special_text)
        linked_home = self.base / 'linked'
        parent = linked_home / '.local/share/applications'
        parent.mkdir(parents=True)
        victim = self.base / 'launcher-victim'
        victim.write_text('preserve me')
        (parent / launcher.name).symlink_to(victim)
        refused = self.play(launcher=True, dots_home=str(linked_home))
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(victim.read_text(), 'preserve me')

    def test_declarations_replace_package_bootstrap_and_keep_fuse_runtime(self):
        local = yaml.safe_load((ROOT / 'roles/software/vars/local-sources.yml').read_text())
        self.assertNotIn('t3code-fork-bin', [p for spec in local['software_local_sources'] for p in spec['packages']])
        policy = yaml.safe_load((ROOT / 'policy/packages.yml').read_text())
        self.assertIn('fuse2', policy['software'])
        values = yaml.safe_load((ROOT / 'roles/software/vars/main.yml').read_text())
        self.assertTrue({'gtk3', 'nss', 'alsa-lib', 'libxkbcommon'} <= set(values['software_t3code_runtime_packages']))
        preflight = (ROOT / 'roles/forgejo/tasks/source-preflight.yml').read_text()
        self.assertNotIn('quinntyx/t3code.git', preflight)
        task = (ROOT / 'roles/software/tasks/install.yml').read_text()
        self.assertIn('appimage.yml', task)
        self.assertTrue((ROOT / 'roles/desktop/files/araveia/0644/.local/share/icons/hicolor/scalable/apps/t3code-fork.svg').is_file())


if __name__ == '__main__':
    unittest.main()
