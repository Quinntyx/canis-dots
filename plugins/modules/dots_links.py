#!/usr/bin/python
"""Create declared layout links, preserving machine auth and package-manager outputs."""
from ansible.module_utils.basic import AnsibleModule
import os
from pathlib import Path


def main():
    module = AnsibleModule(argument_spec={'home': {'type': 'path', 'required': True}, 'entries': {'type': 'list', 'elements': 'dict', 'required': True}}, supports_check_mode=True)
    home = Path(module.params['home'])
    changed = False
    try:
        for item in module.params['entries']:
            relative = Path(item['dest'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe link destination')
            path = home / relative
            for parent in relative.parents:
                if str(parent) != '.' and (home / parent).is_symlink():
                    raise ValueError('Refusing symlinked link ancestor')
            target = item['target'].replace('{{ dots_home }}', str(home))
            if item.get('preserve_existing') and (path.exists() or path.is_symlink()):
                continue
            if item.get('optional_target') and not (path.parent / target).exists():
                continue
            if path.is_symlink() and os.readlink(path) == target:
                continue
            if path.exists() and not path.is_symlink():
                raise ValueError('Refusing to replace a non-link owned by another runtime: ' + str(relative))
            changed = True
            if not module.check_mode:
                # Only the declared link itself, never its target, is replaced.
                staging = path.with_name(path.name + '.ansible-link-' + str(os.getpid()))
                staging.symlink_to(target)
                os.replace(staging, path)
    except (ValueError, OSError) as error:
        module.fail_json(msg=str(error))
    module.exit_json(changed=changed)


if __name__ == '__main__':
    main()
