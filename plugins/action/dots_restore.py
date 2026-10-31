"""Authenticate encrypted preimages in controller memory, then restore explicit paths."""
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
import json
from pathlib import Path


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _supports_check_mode = True

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        args = self._task.args
        source = Path(args['backup'])
        if any(parent.is_symlink() for parent in [source, *source.parents]):
            raise AnsibleActionFail('Refusing symlinked backup ancestry')
        try:
            payload = json.loads(self._loader._vault.decrypt(source.read_bytes()))
        except Exception:
            raise AnsibleActionFail('Backup authentication failed') from None
        expected = args['host'] + ('-system' if args.get('system') else '')
        if payload.get('version') != 1 or payload.get('host') != expected:
            raise AnsibleActionFail('Backup scope/host mismatch')
        if args.get('system') and args['home'] != '/':
            raise AnsibleActionFail('System rollback must explicitly target the system root')
        result = self._execute_module(module_name='dots_restore_files', module_args={'home': args['home'], 'entries': payload['files']}, task_vars=task_vars)
        result['_ansible_no_log'] = True
        return result
