"""Bundle ONLY declared non-secret source files, never a live directory tree."""
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
from pathlib import Path, PurePosixPath
import hashlib
import io
import os
import tarfile


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _supports_check_mode = True

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        root = Path(self._task.args['root'])
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            for item in self._task.args['entries']:
                if item['kind'] != 'file':
                    continue
                dest = PurePosixPath(item['dest'])
                if dest.is_absolute() or '..' in dest.parts:
                    raise AnsibleActionFail('Unsafe declared file destination')
                source = root / 'roles' / item['component'] / 'files' / item['source']
                if source.is_symlink() or not source.is_file():
                    raise AnsibleActionFail('Source must be an ordinary declared file')
                content = source.read_bytes()
                info = tarfile.TarInfo(str(dest))
                info.size = len(content)
                info.mode = int(item['mode'], 8)
                info.mtime = 0
                archive.addfile(info, io.BytesIO(content))
        payload = buffer.getvalue()
        digest = hashlib.sha256(payload).hexdigest()
        directory = root / '.artifacts' / 'bundles'
        if directory.is_symlink():
            raise AnsibleActionFail('Refusing symlinked bundle cache')
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = directory / (digest + '.tar')
        if not destination.exists():
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
        elif destination.is_symlink() or hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise AnsibleActionFail('Bundle cache integrity failure')
        return dict(result, changed=False, path=str(destination))
