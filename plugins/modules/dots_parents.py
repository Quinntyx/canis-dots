#!/usr/bin/python
"""Create declared parent directories without recursively adopting existing trees."""
from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import os
import stat


def main():
    module = AnsibleModule(argument_spec={'home': {'type': 'path', 'required': True}, 'directories': {'type': 'list', 'elements': 'str', 'required': True}, 'private': {'type': 'list', 'elements': 'str', 'default': []}}, supports_check_mode=True)
    root = Path(module.params['home'])
    changed = False
    for relative in module.params['directories']:
        item = Path(relative)
        if item.is_absolute() or '..' in item.parts:
            module.fail_json(msg='Unsafe directory destination')
        path = root / item
        for part in [item] + list(item.parents):
            if (root / part).is_symlink():
                module.fail_json(msg='Refusing symlinked destination directory')
        mode = 0o700 if relative in module.params['private'] else 0o755
        if not path.exists():
            changed = True
            if not module.check_mode:
                path.mkdir(parents=True, mode=mode)
        elif not path.is_dir():
            module.fail_json(msg='Directory destination is not a directory')
        elif relative in module.params['private'] and stat.S_IMODE(path.stat().st_mode) != mode:
            changed = True
            if not module.check_mode:
                os.chmod(path, mode)
    module.exit_json(changed=changed)


if __name__ == '__main__':
    main()
