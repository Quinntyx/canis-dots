"""Fresh-account software/agent/session decisions, proven with real Ansible and mocks.

Every package manager, build tool, sudo and Pi executable here is a recording
mock in a disposable directory. Become is disabled (with a nonexistent become
executable as a tripwire), so nothing installs, authenticates, or starts. These
runs prove task decisions and argv, not live package installation.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = shutil.which('ansible-playbook')
GIT_ENVIRONMENT = {'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'url.http://127.0.0.1:3000/.insteadOf',
                   'GIT_CONFIG_VALUE_0': 'https://git.quinntyx.dev/'}

MOCK = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
state = Path(os.environ['DOTS_MOCK_STATE'])
installed = set((state / 'installed').read_text().split()) if (state / 'installed').exists() else set()
keys = ['GIT_CONFIG_COUNT', 'GIT_CONFIG_KEY_0', 'PI_CODING_AGENT_DIR', 'RUSTUP_AUTO_INSTALL', 'NPM_CONFIG_PREFIX', 'HOME']
record = {'cmd': name, 'args': args, 'leader': os.getsid(0) == os.getpid(),
          'env': {k: os.environ[k] for k in keys if k in os.environ}}
with open(os.environ['DOTS_MOCK_LOG'], 'a') as log:
    log.write(json.dumps(record) + '\n')
def done(code=0, out=''):
    if out:
        print(out)
    sys.exit(code)
if name == 'pacman':
    if args == ['-Qq']:
        done(0, '\n'.join(sorted(installed)))
    if args[:1] == ['-Q']:
        done(0 if args[1] in installed else 1)
    if args[:1] == ['-T']:
        # Deptest semantics: a virtual dependency is satisfied by any installed provider.
        provides = {'jack': {'jack2', 'pipewire-jack'}}
        missing = [a for a in args[1:] if a != '--' and a not in installed
                   and not provides.get(a, set()) & installed]
        done(127 if missing else 0, '\n'.join(missing))
    done()
if name == 'rustup':
    active = state / 'rust-active'
    if args == ['show', 'active-toolchain']:
        if active.exists():
            done(0, active.read_text().strip())
        print('error: no active toolchain', file=sys.stderr)
        done(1)
    if args == ['which', 'cargo']:
        done(0 if (state / 'rust-installed').exists() else 1)
    done()
if name == 'uv':
    if args[:2] == ['python', 'find']:
        done(1)
    if args[:1] == ['venv']:
        Path(args[-1]).mkdir(parents=True, exist_ok=True)
        (Path(args[-1]) / 'pyvenv.cfg').write_text('fixture\n')
    if args[:2] == ['pip', 'list']:
        done(0, '[]')
    done()
if name == 'makepkg' and args == ['--packagelist']:
    base = os.getcwd()
    done(0, f'{base}/fixture-bin-1-1-x86_64.pkg.tar.zst\n{base}/fixture-bin-debug-1-1-x86_64.pkg.tar.zst')
if name == 'pi':
    failing = (state / 'pi-fail').read_text().split() if (state / 'pi-fail').exists() else []
    done(1 if Path(os.environ['PI_CODING_AGENT_DIR']).name in failing else 0)
done()
'''


def load_filter():
    spec = importlib.util.spec_from_file_location('dots_filter', ROOT / 'plugins/filter/dots.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(PLAYBOOK, 'Install project-local ansible-core to run fresh-host decision tests')
class FreshHostDecisions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dots-fresh-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.home = self.base / 'home'
        self.bindir = self.base / 'bin'
        self.state = self.base / 'state'
        self.log = self.base / 'calls.jsonl'
        for directory in (self.home, self.bindir, self.state):
            directory.mkdir()
        mock = self.base / 'mock.py'
        mock.write_text(MOCK)
        mock.chmod(0o755)
        for name in ('pacman', 'rustup', 'npm', 'cargo', 'cargo-binstall', 'uv', 'makepkg', 'yay', 'sudo'):
            (self.bindir / name).symlink_to(mock)
        (self.bindir / 'setsid').symlink_to(shutil.which('setsid'))

    def play(self, tasks, variables):
        playbook = self.base / 'play.yml'
        playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                             'gather_facts': False, 'tasks': tasks}]))
        variables = dict({'dots_git_environment': GIT_ENVIRONMENT}, **variables, dots_home=str(self.home),
                         dots_user='fixture', dots_sandbox=False, ansible_become=False,
                         ansible_become_exe='/nonexistent-become-tripwire',
                         ansible_python_interpreter=sys.executable)
        environment = dict(os.environ, DOTS_MOCK_STATE=str(self.state), DOTS_MOCK_LOG=str(self.log),
                           ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg'))
        self.log.write_text('')
        extra = self.base / 'extra-vars.json'
        extra.write_text(json.dumps(variables))
        result = subprocess.run([PLAYBOOK, '-i', 'localhost,', str(playbook), '--extra-vars', '@' + str(extra)],
                                cwd=ROOT, env=environment, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=180)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return result, calls

    def assert_untrusted(self, calls, command):
        """Each untrusted call follows `sudo -K` and leads its own session."""
        seen = 0
        for index, call in enumerate(calls):
            if call['cmd'] == command:
                seen += 1
                self.assertEqual(calls[index - 1]['cmd'], 'sudo', call)
                self.assertEqual(calls[index - 1]['args'], ['-K'], call)
                self.assertTrue(call['leader'], call)
        self.assertTrue(seen, command)

    # --- software role ---------------------------------------------------

    def software(self, installed):
        (self.state / 'installed').write_text('\n'.join(installed))
        role = str(ROOT / 'roles/software')
        tasks = [{'ansible.builtin.include_role': {'name': role, 'tasks_from': name}}
                 for name in ('packages', 'tools')]
        return self.play(tasks, {'software_bindir': str(self.bindir)})

    def test_prerequisites_precede_curated_batch_and_jack2_is_never_removed(self):
        result, calls = self.software(['base', 'coreutils', 'jack2'])
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        installs = [c['args'] for c in calls if c['cmd'] == 'pacman' and c['args'][:1] == ['-S']]
        self.assertEqual(len(installs), 2, installs)
        prerequisites, curated = installs
        variables = yaml.safe_load((ROOT / 'roles/software/vars/main.yml').read_text())
        self.assertEqual(prerequisites[:4], ['-S', '--needed', '--noconfirm', '--'])
        self.assertEqual(sorted(prerequisites[4:]), sorted(variables['software_official_prerequisites']))
        self.assertTrue({'acl', 'sudo', 'util-linux', 'rustup', 'cargo-binstall'} <= set(prerequisites))
        self.assertFalse(set(prerequisites[4:]) & set(curated[4:]))
        self.assertNotIn('pipewire-jack', curated)
        self.assertIn('niri', curated)
        self.assertIn('pipewire-jack not installed: conflicts with installed jack2', result.stdout)
        for call in calls:
            if call['cmd'] == 'pacman':
                self.assertFalse({'-R', '-Rns', '-Sy', '-Syu', '-Su', '--ask'} & set(call['args']), call)
        # Every account installer gets the parent's loopback Git rewrite.
        for call in calls:
            if call['cmd'] in ('npm', 'cargo-binstall'):
                self.assertEqual(call['env']['GIT_CONFIG_COUNT'], '1')
                self.assertEqual(call['env']['NPM_CONFIG_PREFIX'], str(self.home / '.npm-global'))

    def test_missing_rust_toolchain_and_untrusted_installers_on_fresh_account(self):
        result, calls = self.software(['jack2'])
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        rustup = [c for c in calls if c['cmd'] == 'rustup']
        self.assertIn(['default', 'stable'], [c['args'] for c in rustup])
        for call in rustup:
            if call['args'][:1] in (['show'], ['which']):
                self.assertEqual(call['env']['RUSTUP_AUTO_INSTALL'], '0')
        binstall = [c['args'] for c in calls if c['cmd'] == 'cargo-binstall']
        self.assertEqual(sorted(a[-1] for a in binstall), ['flamegraph', 'mdbook-katex'])
        for arguments in binstall:
            self.assertIn('--disable-strategies', arguments)
            self.assertEqual(arguments[arguments.index('--disable-strategies') + 1], 'quick-install')
        self.assert_untrusted(calls, 'npm')
        self.assert_untrusted(calls, 'cargo-binstall')
        npm = [c['args'][-1] for c in calls if c['cmd'] == 'npm']
        self.assertIn('@anthropic-ai/claude-code', npm)

    def test_restored_selection_without_installed_toolchain_is_installed_not_replaced(self):
        (self.state / 'rust-active').write_text('stable-x86_64-unknown-linux-gnu (default)\n')
        result, calls = self.software([])
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        changes = [c['args'] for c in calls if c['cmd'] == 'rustup' and c['args'][:1] in (['default'], ['toolchain'])]
        self.assertEqual(changes, [['toolchain', 'install', 'stable-x86_64-unknown-linux-gnu']])

    def test_installed_toolchain_and_packages_cause_no_changes(self):
        variables = yaml.safe_load((ROOT / 'roles/software/vars/main.yml').read_text())
        lists = ROOT / 'docs/backups/private_araveia/packages/pacman.txt'
        curated = [line.split('#', 1)[0].strip() for line in lists.read_text().splitlines()]
        (self.state / 'rust-active').write_text('stable-x86_64-unknown-linux-gnu (default)\n')
        (self.state / 'rust-installed').write_text('')
        result, calls = self.software([p for p in curated if p] + variables['software_official_prerequisites'])
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        self.assertFalse([c for c in calls if c['cmd'] == 'pacman' and c['args'][:1] == ['-S']])
        self.assertFalse([c for c in calls if c['cmd'] == 'rustup' and c['args'][:1] in (['default'], ['toolchain'])])

    # --- shared AUR recipe tasks ------------------------------------------

    def test_aur_recipe_uses_pacman_deptest_and_skips_debug_artifacts(self):
        recipe = self.base / 'aur' / 'fixture-bin.git'
        recipe.mkdir(parents=True)
        (recipe / '.SRCINFO').write_text('pkgbase = fixture-bin\n\tdepends = jack\n\tdepends = glibc>=2.40\n'
                                         'pkgname = fixture-bin\n')
        git = ['git', '-C', str(recipe), '-c', 'user.name=fixture', '-c', 'user.email=fixture@invalid']
        subprocess.run(['git', 'init', '-q', str(recipe)], check=True)
        subprocess.run(git + ['add', '.SRCINFO'], check=True)
        subprocess.run(git + ['commit', '-q', '-m', 'fixture'], check=True)
        revision = subprocess.run(git + ['rev-parse', 'HEAD'], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
        (self.state / 'installed').write_text('pipewire-jack\nglibc\nbase-devel\n')
        playbook_git = dict(GIT_ENVIRONMENT, GIT_CONFIG_COUNT='2', GIT_CONFIG_KEY_1='url.file://' + str(self.base / 'aur') + '/.insteadOf',
                            GIT_CONFIG_VALUE_1='https://aur.archlinux.org/')
        tasks = [{'ansible.builtin.include_tasks': str(ROOT / 'roles/software/tasks/aur.yml'),
                  'vars': {'dots_aur_name': 'fixture-bin'}}]
        result, calls = self.play(tasks, {'software_bindir': str(self.bindir), 'dots_aur_revisions': {'fixture-bin': revision},
                                          'dots_git_environment': playbook_git})
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        pacman = [c['args'] for c in calls if c['cmd'] == 'pacman']
        self.assertIn(['-T', '--', 'base-devel', 'git'], pacman)
        self.assertIn(['-S', '--needed', '--noconfirm', '--', 'git'], pacman)
        # jack is already provided by pipewire-jack, so no default jack2 is pulled in.
        self.assertIn(['-T', '--', 'jack', 'glibc'], pacman)
        self.assertFalse([a for a in pacman if a[:1] == ['-S'] and 'jack' in a])
        upgrade = [a for a in pacman if a[:1] == ['-U']]
        self.assertEqual(len(upgrade), 1)
        self.assertTrue(upgrade[0][-1].endswith('/fixture-bin-1-1-x86_64.pkg.tar.zst'))
        self.assertFalse([a for a in upgrade[0] if '-debug-' in a])
        self.assert_untrusted(calls, 'makepkg')

    # --- agents role ------------------------------------------------------

    def agents(self, host):
        dots_files = load_filter().entries(['agents'], host)
        for entry in dots_files:
            if entry['dest'].endswith('/settings.json') and 'pi' in entry['dest']:
                path = self.home / entry['dest']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({'fixture': entry['dest']}))
        pi = self.home / '.npm-global/bin/pi'
        pi.parent.mkdir(parents=True, exist_ok=True)
        if not pi.exists():
            pi.symlink_to(self.base / 'mock.py')
        tasks = [{'ansible.builtin.include_role': {'name': str(ROOT / 'roles/agents')}}]
        variables = {'dots_files': dots_files, 'dots_bindir': str(self.bindir), 'dots_install_agent_tools': True,
                     'dots_manage_externals': False, 'dots_controller_root': str(ROOT),
                     'dots_npm_tools': [{'name': '@earendil-works/pi-coding-agent', 'version': '1.4.0'}]}
        return self.play(tasks, variables)

    def expected_dirs(self, host):
        dirs = {str(Path(e['dest']).parent) for e in load_filter().entries(['agents'], host)
                if e['dest'] == '.pi/agent/settings.json'
                or (e['dest'].startswith('.config/pi/profiles/') and e['dest'].count('/') == 4
                    and e['dest'].endswith('/settings.json'))}
        return {str(self.home / d) for d in dirs}

    def test_every_declared_profile_reconciles_extensions_without_self_update(self):
        result, calls = self.agents('araveia')
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        pi = [c for c in calls if c['cmd'] == 'pi']
        self.assertTrue(all(c['args'] == ['update', '--extensions'] for c in pi), pi)
        reconciled = {c['env']['PI_CODING_AGENT_DIR'] for c in pi}
        self.assertEqual(reconciled, self.expected_dirs('araveia'))
        for name in ('subagents', 'coordinator-subagents', 'design-subagents', 'omn-assistant', 'main', 't3main'):
            self.assertIn(str(self.home / '.config/pi/profiles' / name), reconciled)
        self.assertIn(str(self.home / '.pi/agent'), reconciled)
        self.assertTrue(all(c['env']['GIT_CONFIG_COUNT'] == '1' for c in pi))
        self.assert_untrusted(calls, 'pi')
        self.assert_untrusted(calls, 'npm')
        self.assertEqual([c['args'][-1] for c in calls if c['cmd'] == 'npm'], ['@earendil-works/pi-coding-agent@1.4.0'])
        receipts = sorted((self.home / '.local/state/ansible-dots').iterdir())
        self.assertEqual(len(receipts), len(reconciled))
        self.assertTrue(all(r.read_text().startswith('pi update --extensions ') for r in receipts))
        repeat, calls = self.agents('araveia')
        self.assertEqual(repeat.returncode, 0, repeat.stdout[-8000:])
        self.assertFalse([c for c in calls if c['cmd'] == 'pi'])

    def test_lab_profiles_exclude_main_only_declarations(self):
        result, calls = self.agents('syssec-canis')
        self.assertEqual(result.returncode, 0, result.stdout[-8000:])
        reconciled = {c['env']['PI_CODING_AGENT_DIR'] for c in calls if c['cmd'] == 'pi'}
        self.assertEqual(reconciled, self.expected_dirs('syssec-canis'))
        self.assertNotIn(str(self.home / '.config/pi/profiles/omn-assistant'), reconciled)

    def test_failed_reconciliation_writes_no_receipt_and_legacy_receipts_do_not_count(self):
        state = self.home / '.local/state/ansible-dots'
        state.mkdir(parents=True)
        settings = self.home / '.config/pi/profiles/main/settings.json'
        settings.parent.mkdir(parents=True)
        settings.write_text('{}')
        import hashlib
        # The baseline wrote a bare checksum after a self-update-only `pi update`.
        (state / 'pi-main.sha256').write_text(hashlib.sha256(b'{}').hexdigest() + '\n')
        (self.state / 'pi-fail').write_text('subagents\n')
        result, calls = self.agents('araveia')
        self.assertNotEqual(result.returncode, 0)
        reconciled = [c['env']['PI_CODING_AGENT_DIR'] for c in calls if c['cmd'] == 'pi']
        self.assertIn(str(self.home / '.config/pi/profiles/main'), reconciled)
        self.assertIn(str(self.home / '.config/pi/profiles/subagents'), reconciled)
        self.assertFalse((state / 'pi-extensions-.config_pi_profiles_subagents.sha256').exists())
        self.assertTrue((state / 'pi-extensions-.config_pi_profiles_main.sha256').exists())
        (self.state / 'pi-fail').write_text('')
        retry, calls = self.agents('araveia')
        self.assertEqual(retry.returncode, 0, retry.stdout[-8000:])
        retried = [c['env']['PI_CODING_AGENT_DIR'] for c in calls if c['cmd'] == 'pi']
        self.assertIn(str(self.home / '.config/pi/profiles/subagents'), retried)
        self.assertNotIn(str(self.home / '.config/pi/profiles/main'), retried)


class FreshSourcePolicy(unittest.TestCase):
    def test_desktop_and_software_groups_match_managed_configuration(self):
        groups = yaml.safe_load((ROOT / 'policy/packages.yml').read_text())
        desktop = set(groups['desktop'])
        self.assertTrue({'niri', 'xwayland-satellite', 'fuzzel', 'swaylock', 'awww', 'nautilus', 'waybar', 'mako',
                         'kitty', 'xdg-desktop-portal-gnome', 'xdg-desktop-portal-wlr', 'syncthing',
                         'pipewire', 'pipewire-pulse', 'wireplumber'} <= desktop)
        self.assertFalse({p for p in desktop if p.startswith(('hypr', 'fcitx'))} | {'wofi', 'alacritty', 'polkit-kde-agent',
                         'xdg-desktop-portal-hyprland'} & desktop)
        variables = yaml.safe_load((ROOT / 'roles/software/vars/main.yml').read_text())
        curated = {line.split('#', 1)[0].strip()
                   for line in (ROOT / 'docs/backups/private_araveia/packages/pacman.txt').read_text().splitlines()}
        self.assertLessEqual(set(groups['software']), curated | set(variables['software_official_prerequisites']))
        self.assertTrue({'cloudflared', 'firewalld', 'mosh', 'avahi', 'cups', 'bluez', 'power-profiles-daemon',
                         'acl', 'util-linux'} <= set(groups['system']))
        self.assertTrue({'sudo', 'util-linux'} <= set(groups['agents']))
        # Selective forgejo binds the tailnet address; its source preflight needs Git.
        self.assertTrue({'git', 'tailscale', 'acl'} <= set(groups['forgejo']))
        # A JACK provider here would race the software role's held conflict.
        self.assertFalse({'jack2', 'pipewire-jack', 'ffmpeg', 'mpv'} & {p for g in groups.values() for p in g})

    def test_desktop_session_tasks_start_without_restarting_or_replacing_display_manager(self):
        text = (ROOT / 'roles/desktop/tasks/main.yml').read_text()
        tasks = yaml.safe_load(text)
        session = next(t for t in tasks if 'block' in t)
        self.assertIn('not ansible_check_mode', session['when'])
        modules = [t for t in session['block'] if 'ansible.builtin.systemd_service' in t]
        self.assertEqual({t['ansible.builtin.systemd_service']['state'] for t in modules}, {'started'})
        self.assertFalse([t for t in modules if 'enabled' in t['ansible.builtin.systemd_service']])
        self.assertIn('syncthing.service', text)
        manager = next(t for t in tasks if 'display-manager' in json.dumps(t) and 'ansible.builtin.stat' in t)
        self.assertEqual(manager['ansible.builtin.stat']['path'], '/etc/systemd/system/display-manager.service')
        for forbidden in ('state: restarted', 'state: stopped', 'state: reloaded', 'niri.service', 'enable-linger'):
            self.assertNotIn(forbidden, text)

    def test_untrusted_build_policy_disables_cached_credentials_and_debug_splits(self):
        builds = (ROOT / 'roles/software/tasks/builds.yml').read_text()
        self.assertIn('Defaults:{{ dots_user }} timestamp_timeout=0', builds)
        self.assertIn('OPTIONS+=(!debug)', builds)
        for path in ('roles/software/tasks/builds.yml', 'roles/software/tasks/tools.yml'):
            for task in yaml.safe_load((ROOT / path).read_text()):
                for inner in task.get('block', [task]):
                    for nested in inner.get('block', [inner]):
                        argv = json.dumps(nested.get('ansible.builtin.command', {}).get('argv', ''))
                        if any(tool in argv for tool in ("/makepkg'", "/yay'", "/npm'", "/cargo-binstall'")):
                            self.assertIn('software_untrusted_argv', argv, nested['name'])


if __name__ == '__main__':
    unittest.main()
