#!/usr/bin/python
"""Create-only recovery of enumerated runtime credentials from the legacy private snapshot.

The whole inventory is validated before the first write. Nothing existing is
overwritten, adopted, chmodded or chowned; no symlink is followed in the source
or destination. Results are counts only; payloads and tree-internal names never
appear in results or errors. Playbooks still wrap the task in no_log.
"""
from ansible.module_utils.basic import AnsibleModule
import errno
import grp
import os
import posixpath
import pwd
import secrets
import stat

KEYS = {'path', 'kind', 'required', 'mode', 'exclude'}
MODES = {'0600': 0o600, '0644': 0o644, '0700': 0o700}
LIMIT = 512 * 1024 * 1024
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
READ = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
CREATE = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC


class RecoveryError(Exception):
    pass


def relative(value):
    if not isinstance(value, str) or not value or '\0' in value:
        raise RecoveryError('Invalid recovery inventory path')
    parts = tuple(value.split('/'))
    if any(part in ('', '.', '..') for part in parts):
        raise RecoveryError('Invalid recovery inventory path')
    return parts


def validate_inventory(entries):
    """Normalize the inventory; reject unknown keys, traversal, duplicates and overlap."""
    if not isinstance(entries, list):
        raise RecoveryError('Invalid recovery inventory')
    result = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - KEYS or not {'path', 'kind', 'required'} <= set(entry):
            raise RecoveryError('Invalid recovery inventory entry')
        if entry['kind'] not in ('file', 'tree') or not isinstance(entry['required'], bool):
            raise RecoveryError('Invalid recovery inventory kind or required flag')
        mode = None
        if 'mode' in entry:
            if entry['kind'] != 'file' or not isinstance(entry['mode'], str) or entry['mode'] not in MODES:
                raise RecoveryError('Invalid recovery inventory mode')
            mode = MODES[entry['mode']]
        exclude = []
        if 'exclude' in entry:
            if entry['kind'] != 'tree' or not isinstance(entry['exclude'], list):
                raise RecoveryError('Invalid recovery inventory exclusion')
            exclude = [relative(item) for item in entry['exclude']]
            if len(set(exclude)) != len(exclude):
                raise RecoveryError('Invalid recovery inventory exclusion')
        result.append(dict(label=entry['path'], parts=relative(entry['path']), kind=entry['kind'],
                           required=entry['required'], mode=mode, exclude=exclude))
    for outer in result:
        for inner in result:
            if outer is inner:
                continue
            if outer['parts'] == inner['parts']:
                raise RecoveryError('Invalid recovery inventory: duplicate entry ' + outer['label'])
            depth = len(outer['parts'])
            if inner['parts'][:depth] == outer['parts']:
                suffix = inner['parts'][depth:]
                if outer['kind'] != 'tree' or not any(suffix[:len(item)] == item for item in outer['exclude']):
                    raise RecoveryError('Invalid recovery inventory: overlapping entries ' + outer['label'])
    return result


def account(value, lookup, label):
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    try:
        return lookup(value)
    except (KeyError, TypeError):
        raise RecoveryError('Unknown recovery ' + label) from None


def writable(info):
    return info.st_mode & 0o022


class Recovery:
    def __init__(self, scope, check):
        self.scope = scope
        self.check = check
        self.fds = []
        self.label = None
        self.budget = LIMIT
        self.counts = dict(created_dirs=0, created_files=0, created_links=0, matched=0, skipped_sockets=0, missing_optional=0)

    def where(self):
        return ' at policy entry ' + self.label if self.label else ''

    def fail(self, message):
        raise RecoveryError(message + self.where())

    def keep(self, fd):
        self.fds.append(fd)
        return fd

    def child(self, parent, name, missing_ok=False):
        """Open an existing child directory without following a symlink."""
        try:
            return self.keep(os.open(name, DIRECTORY, dir_fd=parent))
        except OSError as error:
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                if missing_ok:
                    return None
                raise error from None
            if stat.S_ISLNK(info.st_mode):
                self.fail('Refusing recovery path through a symlink')
            if not stat.S_ISDIR(info.st_mode):
                self.fail('Recovery path ancestor is not a directory')
            raise

    def absolute(self, path, what):
        if not isinstance(path, str) or not path.startswith('/') or posixpath.normpath(path) != path or '\0' in path:
            raise RecoveryError('Recovery ' + what + ' must be a normalized absolute path')
        fd = self.keep(os.open('/', DIRECTORY))
        chain = [os.fstat(fd)]
        for name in [part for part in path.split('/') if part]:
            fd = self.child(fd, name)
            chain.append(os.fstat(fd))
        return fd, chain

    def read(self, parent, name, info, trusted):
        if info.st_uid not in trusted or writable(info):
            self.fail('Unsafe recovery snapshot permissions')
        fd = os.open(name, READ, dir_fd=parent)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                self.fail('Recovery source changed during validation')
            self.budget -= opened.st_size
            if self.budget < 0:
                self.fail('Recovery inventory exceeds the size limit')
            chunks = []
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    return b''.join(chunks)
                chunks.append(chunk)
        finally:
            os.close(fd)

    def walk(self, fd, inside, entry, trusted, nodes):
        for name in sorted(os.listdir(fd)):
            parts = inside + (name,)
            if any(parts[:len(item)] == item for item in entry['exclude']):
                continue
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            path = entry['parts'] + parts
            if stat.S_ISSOCK(info.st_mode):
                self.counts['skipped_sockets'] += 1
            elif stat.S_ISDIR(info.st_mode):
                if info.st_uid not in trusted or writable(info):
                    self.fail('Unsafe recovery snapshot permissions')
                nodes.append(('dir', path, None, 0o700))
                self.walk(self.child(fd, name), parts, entry, trusted, nodes)
            elif stat.S_ISREG(info.st_mode):
                data = self.read(fd, name, info, trusted)
                nodes.append(('file', path, data, 0o700 if info.st_mode & 0o111 else 0o600))
            elif stat.S_ISLNK(info.st_mode):
                if info.st_uid not in trusted:
                    self.fail('Unsafe recovery snapshot permissions')
                target = os.readlink(name, dir_fd=fd)
                resolved = posixpath.normpath(posixpath.join(*inside, target) if inside else target)
                if not target or target.startswith('/') or resolved == '..' or resolved.startswith('../'):
                    self.fail('Recovery tree link is not a relative internal link')
                nodes.append(('link', path, target, None))
            else:
                self.fail('Recovery source contains a special file')

    def source(self, root, entry, trusted):
        """Return planned nodes for one entry, or None for an absent optional source."""
        fd = root
        for name in entry['parts'][:-1]:
            fd = self.child(fd, name, missing_ok=True)
            if fd is None:
                return None
            info = os.fstat(fd)
            if info.st_uid not in trusted or writable(info):
                self.fail('Unsafe recovery snapshot permissions')
        try:
            info = os.stat(entry['parts'][-1], dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if entry['kind'] == 'file':
            if not stat.S_ISREG(info.st_mode):
                self.fail('Recovery source is not a regular file')
            data = self.read(fd, entry['parts'][-1], info, trusted)
            mode = entry['mode'] if entry['mode'] is not None else (0o700 if info.st_mode & 0o111 else 0o600)
            return [('file', entry['parts'], data, mode)]
        if not stat.S_ISDIR(info.st_mode):
            self.fail('Recovery source tree is not a directory')
        if info.st_uid not in trusted or writable(info):
            self.fail('Unsafe recovery snapshot permissions')
        nodes = [('dir', entry['parts'], None, 0o700)]
        self.walk(self.child(fd, entry['parts'][-1]), (), entry, trusted, nodes)
        return nodes

    def directory(self, parts):
        if parts not in self.open_dirs:
            self.open_dirs[parts] = self.child(self.directory(parts[:-1]), parts[-1])
        return self.open_dirs[parts]

    def existing(self, parts):
        if self.state.get(parts[:-1]) == 'create':
            return None
        try:
            return os.stat(parts[-1], dir_fd=self.directory(parts[:-1]), follow_symlinks=False)
        except FileNotFoundError:
            return None

    def same_bytes(self, parts, data):
        fd = os.open(parts[-1], READ, dir_fd=self.directory(parts[:-1]))
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return False
            current = b''
            while len(current) <= len(data):
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                current += chunk
            return current == data
        finally:
            os.close(fd)

    def plan(self, kind, parts, payload, mode):
        """Decide create or match for one destination node; anything else is a conflict."""
        if kind == 'dir' and parts in self.state:
            return
        info = self.existing(parts)
        if info is None:
            self.actions.append((kind, parts, payload, mode))
            self.counts['created_' + kind + 's'] += 1
            if kind == 'dir':
                self.state[parts] = 'create'
            return
        if kind == 'dir':
            if stat.S_ISLNK(info.st_mode):
                self.fail('Refusing recovery destination ancestry through a symlink')
            if not stat.S_ISDIR(info.st_mode):
                self.fail('Recovery conflict: existing destination differs')
            if info.st_uid not in (0, self.uid) or writable(info):
                self.fail('Refusing unsafe destination directory')
            self.state[parts] = 'exists'
            return
        if info.st_uid != self.uid:
            self.fail('Recovery conflict: existing destination differs')
        if kind == 'file' and stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == mode and self.same_bytes(parts, payload):
            self.counts['matched'] += 1
        elif kind == 'link' and stat.S_ISLNK(info.st_mode) and os.readlink(parts[-1], dir_fd=self.directory(parts[:-1])) == payload:
            self.counts['matched'] += 1
        else:
            self.fail('Recovery conflict: existing destination differs')

    def create(self, kind, parts, payload, mode):
        parent = self.directory(parts[:-1])
        name = parts[-1]
        if kind == 'dir':
            os.mkdir(name, 0o700, dir_fd=parent)
            fd = self.directory(parts)
            os.fchown(fd, self.uid, self.gid)
            os.fchmod(fd, 0o700)
            return
        staging = '.dots-recover-' + secrets.token_hex(8)
        try:
            if kind == 'link':
                os.symlink(payload, staging, dir_fd=parent)
                os.chown(staging, self.uid, self.gid, dir_fd=parent, follow_symlinks=False)
            else:
                fd = os.open(staging, CREATE, 0o600, dir_fd=parent)
                try:
                    os.fchown(fd, self.uid, self.gid)
                    view = memoryview(payload)
                    while view:
                        view = view[os.write(fd, view):]
                    os.fchmod(fd, mode)
                    os.fsync(fd)
                finally:
                    os.close(fd)
            # link(2) never replaces an existing name, unlike rename(2).
            try:
                os.link(staging, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            except FileExistsError:
                self.fail('Recovery conflict: destination appeared during recovery')
        finally:
            try:
                os.unlink(staging, dir_fd=parent)
            except FileNotFoundError:
                pass
        os.fsync(parent)

    def run(self, snapshot, home, entries, operation, owner, group, snapshot_owner):
        inventory = validate_inventory(entries)
        if self.scope == 'system' and (owner is not None or group is not None):
            raise RecoveryError('Recovery owner/group apply only to home scope')
        destination, destination_chain = self.absolute(home, 'destination')
        root_info = destination_chain[-1]
        if self.scope == 'home':
            self.uid = root_info.st_uid if owner is None else account(owner, lambda name: pwd.getpwnam(name).pw_uid, 'owner')
            self.gid = root_info.st_gid if group is None else account(group, lambda name: grp.getgrnam(name).gr_gid, 'group')
            if self.uid != root_info.st_uid:
                raise RecoveryError('Recovery owner does not match the destination home owner')
        else:
            self.uid, self.gid = os.geteuid(), os.getegid()
        trusted = {0, os.geteuid()}
        extra = account(snapshot_owner, lambda name: pwd.getpwnam(name).pw_uid, 'snapshot owner')
        trusted.add(extra if extra is not None else self.uid)
        snapshot_fd, chain = self.absolute(snapshot, 'snapshot')
        for info in chain[:-1]:
            if info.st_uid not in trusted or (writable(info) and not info.st_mode & stat.S_ISVTX):
                raise RecoveryError('Unsafe recovery snapshot ancestry')
        source_root = self.child(snapshot_fd, 'home' if self.scope == 'home' else 'root')
        for info in (chain[-1], os.fstat(source_root)):
            if info.st_uid not in trusted or info.st_mode & 0o077:
                raise RecoveryError('Recovery snapshot is not private and owner-controlled')
        for info in destination_chain[:-1]:
            if info.st_uid not in trusted | {self.uid} or (writable(info) and not info.st_mode & stat.S_ISVTX):
                raise RecoveryError('Unsafe recovery destination ancestry')
        if root_info.st_uid not in ({self.uid} if self.scope == 'home' else {0, self.uid}) or writable(root_info):
            raise RecoveryError('Unsafe recovery destination root')
        self.open_dirs = {(): destination}
        self.state = {(): 'exists'}
        self.actions = []
        for entry in inventory:
            self.label = entry['label']
            nodes = self.source(source_root, entry, trusted)
            if nodes is None:
                if entry['required']:
                    self.fail('Missing required recovery source')
                self.counts['missing_optional'] += 1
                continue
            for depth in range(1, len(entry['parts'])):
                self.plan('dir', entry['parts'][:depth], None, 0o700)
            for node in nodes:
                self.plan(*node)
        self.label = None
        created = bool(self.actions)
        if operation == 'restore' and not self.check:
            for kind, parts, payload, mode in self.actions:
                self.label = next(entry['label'] for entry in inventory if parts[:len(entry['parts'])] == entry['parts'] or entry['parts'][:len(parts)] == parts)
                self.create(kind, parts, payload, mode)
        return dict(changed=created and operation == 'restore', entries=len(inventory), **self.counts)

    def close(self):
        for fd in self.fds:
            try:
                os.close(fd)
            except OSError:
                pass


def recover(snapshot, home, scope, entries, operation, check, owner=None, group=None, snapshot_owner=None):
    if scope not in ('home', 'system') or operation not in ('validate', 'restore'):
        raise RecoveryError('Invalid recovery scope or operation')
    job = Recovery(scope, check)
    try:
        return job.run(snapshot, home, entries, operation, owner, group, snapshot_owner)
    except OSError as error:
        # Never str(error): it embeds file names that may be tree-internal.
        raise RecoveryError('Recovery I/O failure (' + errno.errorcode.get(error.errno, 'unknown') + ')' + job.where()) from None
    finally:
        job.close()


def main():
    module = AnsibleModule(argument_spec={
        'snapshot': {'type': 'str', 'required': True},
        'home': {'type': 'str', 'required': True},
        'scope': {'type': 'str', 'required': True, 'choices': ['home', 'system']},
        'entries': {'type': 'list', 'elements': 'dict', 'required': True},
        'operation': {'type': 'str', 'required': True, 'choices': ['validate', 'restore']},
        'owner': {'type': 'raw'}, 'group': {'type': 'raw'}, 'snapshot_owner': {'type': 'raw'},
    }, supports_check_mode=True)
    params = module.params
    try:
        result = recover(params['snapshot'], params['home'], params['scope'], params['entries'], params['operation'],
                         module.check_mode, params['owner'], params['group'], params['snapshot_owner'])
    except RecoveryError as error:
        module.fail_json(msg=str(error))
    except Exception as error:
        module.fail_json(msg='Recovery failed: ' + type(error).__name__)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
