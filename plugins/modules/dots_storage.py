#!/usr/bin/python
"""Validate the approved preserved data volume; never format or adopt data."""
from pathlib import Path
import configparser
import json
import os
from ansible.module_utils.basic import AnsibleModule


def safe_ancestry(path):
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise ValueError('Preserved storage must not have symlinked ancestry')


def verify_data(path, uid, require_forge):
    safe_ancestry(path)
    if not path.is_dir() or path.stat().st_uid != uid:
        raise ValueError('Preserved docs disk ownership does not match the target account UID; do not recursively chown it')
    if require_forge:
        config = path / 'host/forgejo/forgejo/gitea/conf/app.ini'
        safe_ancestry(config)
        if not config.is_file() or config.stat().st_uid != uid:
            raise ValueError('Existing Forgejo app.ini with the target account ownership is required; refusing a blank forge')
        try:
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            # Forgejo permits top-level APP_NAME/RUN_USER before any INI section.
            parser.read_string('[DEFAULT]\n' + config.read_text())
            locked = parser.getboolean('security', 'INSTALL_LOCK', fallback=False)
        except Exception:
            raise ValueError('Unable to validate the existing Forgejo installation lock') from None
        if not locked:
            raise ValueError('Existing Forgejo INSTALL_LOCK=true is required; refusing the setup wizard')


def mounted_uuid(module, path):
    rc, out, _ = module.run_command(['/usr/bin/findmnt', '--json', '--mountpoint', str(path), '--output', 'TARGET,UUID,FSTYPE'])
    if rc == 1:
        return None
    if rc:
        raise ValueError('Unable to inspect the preserved docs mount')
    try:
        mounts = json.loads(out)['filesystems']
        if len(mounts) != 1 or mounts[0]['target'] != str(path):
            raise ValueError
        return mounts[0]
    except (ValueError, KeyError, TypeError):
        raise ValueError('Unexpected preserved storage mount metadata') from None


def main():
    module = AnsibleModule(argument_spec=dict(path=dict(type='path', required=True), uuid=dict(type='str', required=True),
                           uid=dict(type='int', required=True), require_forge=dict(type='bool', default=True),
                           operation=dict(choices=['validate', 'mount'], default='validate'),
                           fstype=dict(type='str', default='ext4')), supports_check_mode=True)
    try:
        path = Path(module.params['path'])
        uuid = module.params['uuid']
        if not path.is_absolute() or path == Path('/') or not uuid or any(c not in '0123456789abcdefABCDEF-' for c in uuid):
            raise ValueError('Invalid preserved storage declaration')
        safe_ancestry(path)
        current = mounted_uuid(module, path)
        changed = False
        if current is None:
            if module.params['operation'] != 'mount':
                raise ValueError('The preserved docs disk is not mounted; use scripts/deploy --fresh after reinstalling without formatting that disk')
            rc, _, _ = module.run_command(['/usr/bin/blkid', '-U', uuid])
            if rc:
                raise ValueError('The explicitly declared preserved docs UUID is unavailable; no replacement disk will be created or formatted')
            rc, elsewhere, _ = module.run_command(['/usr/bin/findmnt', '-rn', '-S', 'UUID=' + uuid, '-o', 'TARGET'])
            if rc not in [0, 1] or elsewhere.strip():
                raise ValueError('The preserved docs disk is already mounted elsewhere; resolve the mount explicitly')
            if path.exists() and (not path.is_dir() or any(path.iterdir())):
                raise ValueError('Refusing to hide existing files beneath a new docs mount')
            if module.check_mode:
                module.exit_json(changed=True, pending_mount=True)
            if not path.exists():
                path.mkdir(mode=0o700)
                os.chown(path, module.params['uid'], -1)
            rc, _, _ = module.run_command(['/usr/bin/mount', '-t', module.params['fstype'], '-U', uuid, str(path)])
            if rc:
                raise ValueError('Mounting the approved preserved docs disk failed')
            changed = True
            current = mounted_uuid(module, path)
        if not current or current.get('uuid') != uuid or current.get('fstype') != module.params['fstype']:
            raise ValueError('The docs mount does not match the approved filesystem UUID and type')
        verify_data(path, module.params['uid'], module.params['require_forge'])
        module.exit_json(changed=changed, pending_mount=False)
    except (ValueError, OSError) as error:
        module.fail_json(msg=str(error) if isinstance(error, ValueError) else 'Preserved storage validation failed')


if __name__ == '__main__':
    main()
