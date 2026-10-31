#!/usr/bin/python
"""Read-only target snapshot. Plaintext exists in memory/SSH only, never a backup file."""
from ansible.module_utils.basic import AnsibleModule
import base64
import os
from pathlib import Path
import stat


def snapshot(home, entries):
    root = Path(home)
    if not root.is_absolute() or not root.is_dir():
        raise ValueError('Home must be an existing absolute directory')
    result = []
    total = 0
    for entry in entries:
        relative = Path(entry['dest'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe snapshot path')
        path = root / relative
        if entry.get('preserve_existing') and (path.exists() or path.is_symlink()):
            continue
        for parent in relative.parents:
            if str(parent) != '.' and (root / parent).is_symlink():
                raise ValueError('Refusing symlinked destination ancestor: ' + str(parent))
        item = {'dest': str(relative), 'kind': 'absent'}
        if path.is_symlink():
            item.update(kind='link', target=os.readlink(path))
        elif path.is_file():
            info = path.stat()
            total += info.st_size
            if total > 100 * 1024 * 1024:
                raise ValueError('Baseline exceeds 100 MiB; enroll a separately reviewed data backup')
            item.update(kind='file', mode=format(stat.S_IMODE(info.st_mode), '04o'), data=base64.b64encode(path.read_bytes()).decode())
        elif path.exists():
            raise ValueError('Managed file destination is not a file: ' + str(relative))
        result.append(item)
    return result


def main():
    module = AnsibleModule(argument_spec={'home': {'type': 'path', 'required': True}, 'entries': {'type': 'list', 'elements': 'dict', 'required': True}}, supports_check_mode=True)
    try:
        data = snapshot(module.params['home'], module.params['entries'])
    except (ValueError, OSError) as error:
        module.fail_json(msg=str(error))
    module.exit_json(changed=False, snapshot=data)


if __name__ == '__main__':
    main()
