"""Encrypt target preimages on the controller before configuration changes."""
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import tempfile


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _supports_check_mode = True

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        args = self._task.args
        host = args['host']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', host):
            raise AnsibleActionFail('Unsafe backup hostname')
        entries = args.get('entries', [])
        if args.get('backup_entries_from'):
            source = Path(args['backup_entries_from'])
            if any(parent.is_symlink() for parent in [source, *source.parents]):
                raise AnsibleActionFail('Refusing symlinked rollback source ancestry')
            try:
                restore = json.loads(self._loader._vault.decrypt(source.read_bytes()))
            except Exception:
                raise AnsibleActionFail('Rollback authentication failed before snapshot') from None
            if restore.get('host') != host or restore.get('version') != 1:
                raise AnsibleActionFail('Rollback scope/host mismatch before snapshot')
            entries = [{'dest': entry['dest']} for entry in restore['files']]
        for secret in args.get('secrets', []):
            if secret.get('encrypted', True):
                try:
                    self._loader._vault.decrypt(Path(secret['source']).read_bytes())
                except Exception:
                    raise AnsibleActionFail('Secret authentication failed before any target changes') from None
        snapshot = self._execute_module(module_name='dots_snapshot', module_args={'home': args['home'], 'entries': entries}, task_vars=task_vars)
        if snapshot.get('failed'):
            return dict(snapshot, _ansible_no_log=True)
        if self._play_context.check_mode:
            return dict(result, changed=False, _ansible_no_log=True)
        vault = self._loader._vault
        if not vault.secrets:
            raise AnsibleActionFail('Supply --vault-password-file; plaintext backups are forbidden')
        vault_root = Path(args['vault_root'])
        directory = vault_root / 'backups' / host
        if not vault_root.is_absolute() or any(parent.is_symlink() for parent in [directory, *directory.parents]):
            raise AnsibleActionFail('Refusing unsafe or symlinked backup directory ancestry')
        for private in [vault_root, vault_root / 'backups', directory]:
            private.mkdir(parents=True, exist_ok=True, mode=0o700)
            private.chmod(0o700)
        payload = json.dumps({'version': 1, 'host': host, 'home': args['home'], 'files': snapshot['snapshot']}, sort_keys=True).encode()
        previous = sorted(directory.glob('*.vault'))
        if previous:
            if any(path.is_symlink() for path in previous):
                raise AnsibleActionFail('Refusing symlinked existing backups')
            try:
                if vault.decrypt(previous[-1].read_bytes()) == payload:
                    return dict(result, changed=False, backup=str(previous[-1]), _ansible_no_log=True)
            except Exception:
                raise AnsibleActionFail('Existing backup authentication failed; refusing changes') from None
        encrypted = vault.encrypt(payload)
        fd, name = tempfile.mkstemp(prefix='.encrypted-', dir=directory)
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(encrypted)
        destination = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '.vault')
        os.replace(name, destination)
        return dict(result, changed=False, backup=str(destination), _ansible_no_log=True)
