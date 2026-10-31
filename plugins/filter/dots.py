"""Selection and source metadata, shared by direct playbook and wrapper flows."""
import json
from pathlib import Path, PurePosixPath
from ansible.errors import AnsibleFilterError

ROOT = Path(__file__).resolve().parents[2]


def selected(requested, eligible):
    graph = json.loads((ROOT / 'policy/components.json').read_text())
    result, visiting = [], set()
    def visit(name):
        if name not in graph or name not in eligible:
            raise AnsibleFilterError(f'Unknown or ineligible component: {name}')
        if name in visiting:
            raise AnsibleFilterError('Component dependency cycle')
        if name not in result:
            visiting.add(name)
            for parent in graph[name]:
                visit(parent)
            visiting.remove(name)
            result.append(name)
    for name in requested or eligible:
        visit(name)
    return result


def entries(components, host):
    result = []
    for component in components:
        manifest = ROOT / 'roles' / component / 'manifest.yml'
        if not manifest.exists():
            continue
        for item in json.loads(manifest.read_text()):
            if item.get('hosts') and host not in item['hosts']:
                continue
            dest = PurePosixPath(item['dest'])
            if dest.is_absolute() or '..' in dest.parts:
                raise AnsibleFilterError('Unsafe destination')
            result.append(dict(item, component=component))
    return result


def directories(items):
    result = set()
    for item in items:
        for parent in PurePosixPath(item['dest']).parents:
            if str(parent) != '.':
                result.add(str(parent))
    return sorted(result, key=lambda value: (value.count('/'), value))


class FilterModule:
    def filters(self):
        return {'dots_select': selected, 'dots_entries': entries, 'dots_directories': directories}
