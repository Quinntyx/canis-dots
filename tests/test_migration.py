"""Offline ownership/selection checks; runtime tests use disposable homes only."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MigrationContract(unittest.TestCase):
    def test_every_baseline_entry_has_a_disposition(self):
        records = json.loads((ROOT / 'policy/migration.json').read_text())
        self.assertEqual(len(records), len({r['legacy_source'] for r in records}))
        self.assertGreater(len(records), 1300)
        for record in records:
            self.assertIn(record['disposition'], ['managed', 'reference', 'retired', 'upstream'])
            if record['disposition'] == 'managed':
                self.assertTrue((ROOT / record['source']).is_file(), record)

    def test_ledger_covers_exact_original_git_blobs_not_postmigration_edits(self):
        baseline = json.loads((ROOT / 'policy/baseline.yml').read_text())
        tree = subprocess.check_output(['git', 'ls-tree', '-rz', baseline['revision']], cwd=ROOT)
        objects = []
        for line in tree.split(b'\0'):
            if line:
                metadata, name = line.split(b'\t', 1)
                objects.append((metadata.split()[2], name.decode()))
        result = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT, check=True,
                                input=b'\n'.join(blob for blob, _ in objects) + b'\n', stdout=subprocess.PIPE).stdout
        hashes, offset = {}, 0
        for blob, name in objects:
            end = result.index(b'\n', offset)
            size = int(result[offset:end].split()[2])
            offset = end + 1
            hashes[name] = hashlib.sha256(result[offset:offset + size]).hexdigest()
            offset += size + 1
        records = json.loads((ROOT / 'policy/migration.json').read_text())
        self.assertEqual(baseline['tracked_files'], len(objects))
        self.assertEqual({r['legacy_source']: r['sha256'] for r in records}, hashes)

    def test_manifests_have_unique_safe_destinations(self):
        destinations = set()
        for path in (ROOT / 'roles').glob('*/manifest.yml'):
            entries = json.loads(path.read_text())
            for entry in entries:
                dest = entry['dest']
                self.assertFalse(dest.startswith('/'), dest)
                self.assertNotIn('..', Path(dest).parts, dest)
                self.assertNotIn(dest, destinations, dest)
                destinations.add(dest)
                self.assertNotIn(entry['mode'], ['0777', '0666'])
                if entry['kind'] == 'file':
                    self.assertTrue((path.parent / 'files' / entry['source']).is_file())
        self.assertGreater(len(destinations), 1300)

    def test_no_active_legacy_manager(self):
        self.assertFalse((ROOT / '.chezmoiignore').exists())
        self.assertFalse((ROOT / '.chezmoiexternal.toml').exists())
        self.assertFalse((ROOT / 'run_onchange_after_tmux-persistence.sh.tmpl').exists())

    def test_host_scope_and_dependency_closure(self):
        spec = importlib.util.spec_from_file_location('deploy', ROOT / 'scripts/deploy.py')
        deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deploy)
        self.assertIn('shell', deploy.select_components(['tmux'], ['shell', 'tmux']))
        with self.assertRaises(ValueError):
            deploy.select_components(['mail'], ['shell', 'agents'])
        with self.assertRaises(ValueError):
            deploy.select_components(['typo'], ['shell'])


if __name__ == '__main__':
    unittest.main()
