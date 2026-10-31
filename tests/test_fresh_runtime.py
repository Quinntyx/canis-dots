"""Bounded real-Ansible probes for fresh storage, firewall and source decisions.

Fakes record firewall decisions; Git itself resolves the real insteadOf rule.
No sudo, package install, mount, network service or active home is used.
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
from unittest import mock
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAY = shutil.which('ansible-playbook')


@unittest.skipUnless(PLAY, 'Requires project-local ansible-core')
class FreshRuntime(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-fresh-runtime-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'
        self.home.mkdir()
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible.cfg'),
                        ANSIBLE_COLLECTIONS_PATH=str(self.base / 'empty-collections'))

    def play(self, tasks, extra=None, host='localhost', check=False):
        path = self.base / 'play.yml'
        path.write_text(json.dumps([dict(hosts=host, gather_facts=False,
            environment={'PATH': str(self.bin) + ':' + os.environ['PATH']}, tasks=tasks)]))
        variables = dict(dots_controller_root=str(ROOT), dots_home=str(self.home), dots_uid=os.getuid(),
                         ansible_python_interpreter=sys.executable, ansible_become=False,
                         ansible_become_exe='/nonexistent-no-sudo')
        variables.update(extra or {})
        argv = [PLAY, '-i', host + ',', '-c', 'local', str(path), '-e', json.dumps(variables)]
        if check:
            argv += ['--check']
        return subprocess.run(argv, cwd=ROOT, env=self.env, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=90)

    def test_nonmounted_storage_refuses_before_any_target_file_change(self):
        marker = self.home / 'sentinel'
        marker.write_text('untouched')
        result = self.play([{'dots_storage': dict(path=str(self.home / 'docs'),
                                 uuid='40eda021-8152-4dab-8be2-f19307298da2', uid=os.getuid())},
                            {'ansible.builtin.copy': dict(content='must-not-run', dest=str(marker))}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not mounted', result.stdout)
        self.assertEqual(marker.read_text(), 'untouched')
        self.assertEqual([p.name for p in self.home.iterdir()], ['sentinel'])

    def test_loopback_rewrite_applies_to_the_actual_source_preflight(self):
        recorder = self.bin / 'git-recorder'
        log = self.base / 'resolved'
        recorder.write_text('#!/bin/sh\nset -eu\n/usr/bin/git ls-remote --get-url "$3" >> ' + str(log) + '\n')
        recorder.chmod(0o700)
        result = self.play([{'ansible.builtin.include_tasks': str(ROOT / 'roles/forgejo/tasks/source-preflight.yml')}],
                           dict(dots_git_binary=str(recorder), dots_selected=['forgejo'], dots_manage_externals=True,
                                dots_git_environment=yaml.safe_load((ROOT / 'inventory/group_vars/all.yml').read_text())['dots_git_environment']), 'araveia')
        self.assertEqual(result.returncode, 0, result.stdout[-6000:])
        resolved = log.read_text().splitlines()
        self.assertEqual(len(resolved), 4)
        self.assertTrue(all(url.startswith('http://127.0.0.1:3000/quinntyx/') for url in resolved), resolved)
        self.assertFalse((self.home / '.gitconfig').exists())

    def test_firewall_rules_converge_both_stores_without_deleting_or_reloading(self):
        state, calls = self.base / 'state.json', self.base / 'calls.jsonl'
        state.write_text('[]')
        firewall = self.bin / 'firewall-cmd'
        firewall.write_text('#!' + sys.executable + '\n' + '''import json,sys
from pathlib import Path
state=Path(''' + repr(str(state)) + '''); calls=Path(''' + repr(str(calls)) + ''')
a=sys.argv[1:]
with calls.open('a') as out: out.write(json.dumps(a)+'\\n')
store='permanent' if '--permanent' in a else 'runtime'
zone=next((x.split('=',1)[1] for x in a if x.startswith('--zone=')), '')
values=json.loads(state.read_text())
for arg in a:
    if arg.startswith('--query-'):
        k=store+':'+zone+':'+arg[len('--query-'):]
        sys.exit(0 if k in values else 1)
    if arg.startswith(('--add-','--change-')):
        key=arg.split('-',3)[-1] if arg.startswith('--change-') else arg[len('--add-'):]
        k=store+':'+zone+':'+key
        if k not in values: values.append(k)
        state.write_text(json.dumps(values)); sys.exit(0)
sys.exit(7)
''')
        firewall.chmod(0o700)
        rule = dict(zone='tailscale', kind='interface', value='tailscale0')
        tasks = [{'ansible.builtin.include_tasks': str(ROOT / 'roles/system/tasks/firewall-rule.yml')}]
        first = self.play(tasks, dict(dots_firewall_rule=rule))
        self.assertEqual(first.returncode, 0, first.stdout[-6000:])
        second = self.play(tasks, dict(dots_firewall_rule=rule))
        self.assertEqual(second.returncode, 0, second.stdout[-6000:])
        self.assertRegex(second.stdout, r'changed=0\s+unreachable=0\s+failed=0')
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        changes = [a for a in commands if any(x.startswith('--change-') for x in a)]
        self.assertEqual(len(changes), 2)
        self.assertTrue(all('--change-interface=tailscale0' in a for a in changes))
        self.assertFalse(any('--reload' in a or any(x.startswith('--remove-') for x in a) for a in commands))

    def test_full_firewall_handles_permanent_only_new_zone_and_no_zone_exit_two(self):
        state, calls = self.base / 'zone-state.json', self.base / 'zone-calls.jsonl'
        initial = dict(permanent=['public'], runtime=['public'], rules=[], iface='no zone')
        state.write_text(json.dumps(initial))
        firewall = self.bin / 'firewall-cmd'
        firewall.write_text('#!' + sys.executable + '\n' + '''import json,sys
from pathlib import Path
p=Path(''' + repr(str(state)) + '''); log=Path(''' + repr(str(calls)) + ''')
a=sys.argv[1:]; s=json.loads(p.read_text())
with log.open('a') as out: out.write(json.dumps(a)+'\\n')
store='permanent' if '--permanent' in a else 'runtime'
if '--get-zones' in a: print(' '.join(s[store])); sys.exit(0)
if '--check-config' in a: sys.exit(0)
if '--reload' in a:
    s['runtime']=s['permanent'][:]; p.write_text(json.dumps(s)); sys.exit(0)
if '--get-zone-of-interface=tailscale0' in a or '--get-zone-of-interface' in a:
    print(s['iface']); sys.exit(2 if s['iface']=='no zone' else 0)
for arg in a:
    if arg.startswith('--new-zone='):
        assert store=='permanent'
        s[store].append(arg.split('=',1)[1]); p.write_text(json.dumps(s)); sys.exit(0)
zone=next((x.split('=',1)[1] for x in a if x.startswith('--zone=')), '')
if zone not in s[store]: print('INVALID_ZONE'); sys.exit(112)
for arg in a:
    if arg.startswith('--query-'):
        key=store+':'+zone+':'+arg[len('--query-'):]
        sys.exit(0 if key in s['rules'] else 1)
    if arg.startswith(('--add-','--change-')):
        value=arg.split('-',3)[-1] if arg.startswith('--change-') else arg[len('--add-'):]
        key=store+':'+zone+':'+value
        if key not in s['rules']: s['rules'].append(key)
        if arg=='--change-interface=tailscale0': s['iface']=zone
        p.write_text(json.dumps(s)); sys.exit(0)
sys.exit(8)
''')
        firewall.chmod(0o700)
        tasks = yaml.safe_load((ROOT / 'roles/system/tasks/firewall.yml').read_text())
        # Only activation is substituted: every CLI/assert/include task is real.
        tasks[0] = {'ansible.builtin.debug': {'msg': 'firewalld service activation is not exercised'}}
        for task in tasks:
            if task.get('ansible.builtin.include_tasks') == 'firewall-rule.yml':
                task['ansible.builtin.include_tasks'] = str(ROOT / 'roles/system/tasks/firewall-rule.yml')
        import copy
        old_rc = copy.deepcopy(tasks)
        next(t for t in old_rc if t.get('register') == 'dots_tailnet_zone')['failed_when'] = 'dots_tailnet_zone.rc not in [0, 1]'
        self.assertNotEqual(self.play(old_rc, {'dots_fresh_install': True}).returncode, 0)
        state.write_text(json.dumps(initial))
        old_zone = [t for t in tasks if t.get('ansible.builtin.command', {}).get('argv') != ['firewall-cmd', '--reload']]
        failed = self.play(old_zone, {'dots_fresh_install': True})
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('INVALID_ZONE', failed.stdout)
        state.write_text(json.dumps(initial))
        calls.write_text('')
        first = self.play(tasks, {'dots_fresh_install': True})
        self.assertEqual(first.returncode, 0, first.stdout[-6000:])
        second = self.play(tasks, {'dots_fresh_install': True})
        self.assertEqual(second.returncode, 0, second.stdout[-6000:])
        self.assertRegex(second.stdout, r'changed=0\s+unreachable=0\s+failed=0')
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        self.assertEqual(commands.count(['--reload']), 1)
        self.assertEqual(json.loads(state.read_text())['iface'], 'tailscale')

    def test_mount_logic_checks_exact_uuid_and_never_formats_or_hides_files(self):
        spec = importlib.util.spec_from_file_location('storage', ROOT / 'plugins/modules/dots_storage.py')
        storage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(storage)
        class Exit(Exception):
            pass
        results, commands = [], []
        docs = self.home / 'docs'
        class Module:
            check_mode = True
            params = dict(path=str(docs), uuid='40eda021-8152-4dab-8be2-f19307298da2', uid=os.getuid(),
                          operation='mount', fstype='ext4', require_forge=True)
            def run_command(self, argv):
                commands.append(argv)
                if argv[0].endswith('blkid'):
                    return 0, '/dev/test-only', ''
                return 1, '', ''
            def exit_json(self, **kwargs):
                results.append(kwargs)
                raise Exit
            def fail_json(self, **kwargs):
                results.append(kwargs)
                raise Exit
        with mock.patch.object(storage, 'AnsibleModule', return_value=Module()), self.assertRaises(Exit):
            storage.main()
        self.assertEqual(results[-1], dict(changed=True, pending_mount=True))
        self.assertFalse(docs.exists())
        self.assertFalse(any('mount' == Path(c[0]).name or 'mkfs' in c[0] for c in commands))
        docs.mkdir()
        (docs / 'do-not-hide').write_text('sentinel')
        Module.check_mode = False
        with mock.patch.object(storage, 'AnsibleModule', return_value=Module()), self.assertRaises(Exit):
            storage.main()
        self.assertIn('hide existing files', results[-1]['msg'])
        self.assertEqual((docs / 'do-not-hide').read_text(), 'sentinel')


if __name__ == '__main__':
    unittest.main()
