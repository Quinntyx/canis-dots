#!/usr/bin/python
"""Restore recorded regular-file/link preimages. Never delete newly created files."""
from ansible.module_utils.basic import AnsibleModule
import base64
import os
from pathlib import Path
import stat
import tempfile


def main():
    module = AnsibleModule(argument_spec={'home': {'type': 'path', 'required': True}, 'entries': {'type': 'list', 'elements': 'dict', 'required': True, 'no_log': True}}, supports_check_mode=True)
    root = Path(module.params['home'])
    changed = False
    retained = 0
    try:
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise ValueError('Restore root must be an existing absolute ordinary directory')
        # Validate EVERY destination before beginning restoration.
        for item in module.params['entries']:
            relative = Path(item['dest'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe restore path')
            for parent in relative.parents:
                if str(parent) != '.' and (root / parent).is_symlink():
                    raise ValueError('Refusing symlinked restore ancestor')
            target = root / relative
            if target.exists() and target.is_dir() and not target.is_symlink():
                raise ValueError('Refusing to replace an existing directory')
            if item['kind'] not in ['absent', 'file', 'link']:
                raise ValueError('Unsupported backup entry')
            if item['kind'] == 'file':
                item['_bytes'] = base64.b64decode(item['data'], validate=True)
                item['_mode'] = int(item['mode'], 8)
                if item['_mode'] < 0 or item['_mode'] > 0o777:
                    raise ValueError('Unsafe restored mode')
            elif item['kind'] == 'link' and not isinstance(item.get('target'), str):
                raise ValueError('Invalid restored link target')
        for item in module.params['entries']:
            target = root / item['dest']
            if item['kind'] == 'absent':
                retained += int(target.exists() or target.is_symlink())
                continue
            content = item.get('_bytes')
            mode = item.get('_mode', 0o600)
            if item['kind'] == 'file' and target.is_file() and not target.is_symlink() and target.read_bytes() == content and stat.S_IMODE(target.stat().st_mode) == mode:
                continue
            if item['kind'] == 'link' and target.is_symlink() and os.readlink(target) == item['target']:
                continue
            changed = True
            if module.check_mode:
                continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if item['kind'] == 'link':
                staging = target.with_name(target.name + '.restore-' + str(os.getpid()))
                staging.symlink_to(item['target'])
                os.replace(staging, target)
            else:
                fd, staging = tempfile.mkstemp(dir=target.parent, prefix='.restore-')
                with os.fdopen(fd, 'wb') as stream:
                    os.fchmod(stream.fileno(), mode)
                    stream.write(content)
                os.replace(staging, target)
    except (ValueError, OSError) as error:
        module.fail_json(msg=str(error))
    module.exit_json(changed=changed, newly_created_files_retained=retained)


if __name__ == '__main__':
    main()
