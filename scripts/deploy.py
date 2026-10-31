#!/usr/bin/env python3
"""Deploy explicit inventory membership. Nothing is inferred from T3 connections."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def select_components(requested, eligible):
    graph = json.loads((ROOT / 'policy/components.json').read_text())
    ordered, visiting = [], set()
    def add(name):
        if name not in graph or name not in eligible:
            raise ValueError(f'Component {name!r} is unknown or ineligible on this host')
        if name in visiting:
            raise ValueError('Dependency cycle')
        if name in ordered:
            return
        visiting.add(name)
        for dependency in graph[name]:
            add(dependency)
        visiting.remove(name)
        ordered.append(name)
    for name in requested or eligible:
        add(name)
    return ordered


def private_directory(path):
    if any(parent.is_symlink() for parent in [path, *path.parents]):
        raise ValueError(f'Refusing symlinked private directory: {path}')
    missing = []
    parent = path
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    path.chmod(0o700)


def password(path, create):
    if any(parent.is_symlink() for parent in [path, *path.parents]):
        raise ValueError('Vault password must not have symlinked ancestry')
    if not path.exists():
        if not create:
            return None
        private_directory(path.parent)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(secrets.token_urlsafe(48).encode() + b'\n')
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('Vault password must be owned by you and mode 0600 or stricter')
    value = path.read_bytes().strip()
    if not value:
        raise ValueError('Empty Vault password')
    return value


def atomic_private(path, data):
    private_directory(path.parent)
    if path.is_symlink():
        raise ValueError('Refusing symlinked Vault payload')
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    # On failure retain the encrypted staging file for diagnosis; never plaintext.
    with os.fdopen(fd, 'wb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
    os.replace(name, path)


def prepare_secrets(host, components, vault_root, key, source_home, check):
    from ansible.parsing.vault import VaultLib, VaultSecret
    vault = VaultLib([('default', VaultSecret(key))])
    policy = json.loads((ROOT / 'policy/secrets.yml').read_text()).get(host, [])
    # Authenticate every existing host backup, including root-owned system preimages,
    # before packages, services, or ordinary files can change.
    for backup_host in [host, host + '-system']:
        directory = vault_root / 'backups' / backup_host
        if any(parent.is_symlink() for parent in [directory, *directory.parents]):
            raise ValueError('Refusing symlinked Vault backup ancestry')
        for existing in directory.glob('*.vault'):
            if existing.is_symlink():
                raise ValueError('Refusing symlinked Vault backup')
            try:
                vault.decrypt(existing.read_bytes())
            except Exception:
                raise ValueError('Backup Vault authentication failed; no deployment was started') from None
    result = []
    # Authenticate ALL enrolled payloads first, before writing/enrolling anything.
    enrolled = []
    for entry in policy:
        if entry['component'] not in components:
            continue
        payload = vault_root / 'encrypted_files' / host / (entry['dest'] + '.vault')
        if any(parent.is_symlink() for parent in [payload, *payload.parents]):
            raise ValueError('Refusing symlinked secret payload ancestry')
        if payload.exists():
            try:
                vault.decrypt(payload.read_bytes())
            except Exception:
                raise ValueError('Vault authentication failed; no deployment was started') from None
            enrolled.append((entry, payload, None))
            continue
        source = source_home / entry['dest'] if source_home else None
        if source and source.is_file() and not source.is_symlink():
            enrolled.append((entry, payload, source))
        elif entry.get('required'):
            raise ValueError(f'Missing enrolled secret for {host}: {entry["dest"]}. Run on its existing machine first or use scripts/vault-import.')
    for entry, payload, source in enrolled:
        if source:
            if check:
                # Check mode may use the existing local file in place, without enrolling.
                result.append(dict(entry, source=str(source), encrypted=False))
                continue
            atomic_private(payload, vault.encrypt(source.read_bytes()))
        result.append(dict(entry, source=str(payload), encrypted=True))
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    target = p.add_mutually_exclusive_group()
    target.add_argument('--host', help='Inventory host; default is the local hostname')
    target.add_argument('--all', action='store_true', help='Explicitly deploy every enrolled host')
    p.add_argument('--components', help='Comma-separated components; dependencies are included')
    p.add_argument('--check', action='store_true')
    p.add_argument('--diff', action='store_true')
    p.add_argument('--plan', action='store_true', help='Print non-secret selection only; make no changes')
    p.add_argument('--user', help='SSH login for remote execution (or use SSH config)')
    p.add_argument('--ask-become-pass', action='store_true')
    p.add_argument('--no-become-prompt', action='store_true', help='For passwordless sudo / CI')
    p.add_argument('--config-only', action='store_true', help='Skip package provisioning and service activation')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    os.chdir(ROOT)
    os.environ['ANSIBLE_CONFIG'] = str(ROOT / 'ansible.cfg')
    if not shutil.which('ansible-playbook'):
        raise ValueError('Install ansible-core (or ansible) first: sudo pacman -S ansible-core')
    completed = subprocess.run(['ansible-inventory', '--list'], check=True, stdout=subprocess.PIPE, text=True)
    inventory = json.loads(completed.stdout)
    known = inventory['_meta']['hostvars']
    local = socket.gethostname().split('.')[0]
    hosts = sorted(known) if args.all else [args.host or local]
    selections = []
    for host in hosts:
        if host not in known:
            raise ValueError(f'{host!r} is not enrolled. Add explicit inventory membership first; no inferred fleet deployment.')
        components = select_components(args.components.split(',') if args.components else None, known[host]['dots_components'])
        selections.append((host, components))
    if args.plan:
        print(json.dumps([{'host': h, 'connection': 'local' if h == local else 'ssh', 'components': c} for h,c in selections], indent=2))
        return 0
    vault_root = Path(os.environ.get('DOTS_VAULT_ROOT', ROOT / '.vault')).expanduser().absolute()
    key_path = Path(os.environ.get('DOTS_VAULT_PASSWORD_FILE', '~/.config/ansible/vault-pass')).expanduser().absolute()
    key = password(key_path, create=not args.check)
    if not args.check:
        private_directory(vault_root)
    with tempfile.TemporaryDirectory(prefix='dots-deploy-') as work:
        if key is None:
            key = secrets.token_urlsafe(48).encode()
            key_path = Path(work) / 'vault-pass'
            key_path.write_bytes(key)
            key_path.chmod(0o600)
        plans = []
        # Complete every host's secret authentication before invoking ANY host.
        for host, components in selections:
            secret_files = prepare_secrets(host, components, vault_root, key, Path.home() if host == local else None, args.check)
            plans.append((host, components, secret_files))
        for host, components, secret_files in plans:
            extra = {'dots_requested_components': components, 'dots_secret_files': secret_files,
                     'dots_vault_root': str(vault_root), 'dots_controller_root': str(ROOT),
                     'dots_manage_packages': not args.config_only, 'dots_manage_services': not args.config_only,
                     'dots_install_agent_tools': not args.config_only, 'dots_manage_externals': not args.config_only}
            variables = Path(work) / f'{host}.json'
            variables.write_text(json.dumps(extra))
            variables.chmod(0o600)
            command = ['ansible-playbook', 'playbooks/site.yml', '--limit', host,
                       '--vault-password-file', str(key_path), '--extra-vars', '@' + str(variables)]
            if host == local:
                command += ['--connection', 'local']
                # Use the interpreter in which this wrapper imports ansible.
                command += ['--extra-vars', json.dumps({'ansible_python_interpreter': sys.executable})]
            if args.user:
                command += ['--user', args.user]
            if args.ask_become_pass or (not args.no_become_prompt and not args.config_only and not args.check):
                command += ['--ask-become-pass']
            if args.check:
                command += ['--check']
            if args.diff:
                command += ['--diff']
            result = subprocess.run(command)
            if result.returncode:
                return result.returncode
    print('Deployment finished. Back up the Vault key separately from .vault/; see docs/SECRETS.md.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f'deploy: {error}', file=sys.stderr)
        sys.exit(2)
