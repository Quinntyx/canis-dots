#!/usr/bin/env python3
"""Allowlisted secret import and encrypted configuration rollback. Never prints plaintext."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deployment', ROOT / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['import', 'rollback'])
    parser.add_argument('--host', required=True)
    parser.add_argument('--dest', help='Exact home-relative destination from policy/secrets.yml')
    parser.add_argument('--source', type=Path, help='Existing secret file to encrypt')
    parser.add_argument('--backup', type=Path, help='Encrypted preimage produced by scripts/deploy')
    parser.add_argument('--system', action='store_true', help='Restore explicitly enrolled root-owned preimages')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--user')
    parser.add_argument('--confirm-host', help='Required for rollback: repeat the target inventory hostname')
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ['ANSIBLE_CONFIG'] = str(ROOT / 'ansible.cfg')
    inventory = json.loads(subprocess.check_output(['ansible-inventory', '--list'], text=True))['_meta']['hostvars']
    if args.host not in inventory:
        raise ValueError('Unknown inventory host')
    vault_root = Path(os.environ.get('DOTS_VAULT_ROOT', ROOT / '.vault')).expanduser().absolute()
    key_path = Path(os.environ.get('DOTS_VAULT_PASSWORD_FILE', '~/.config/ansible/vault-pass')).expanduser().absolute()
    key = deploy.password(key_path, create=args.operation == 'import')
    if not key:
        raise ValueError('Restore the separately backed up Vault key first')
    from ansible.parsing.vault import VaultLib, VaultSecret
    vault = VaultLib([('default', VaultSecret(key))])
    if args.operation == 'import':
        allowed = json.loads((ROOT / 'policy/secrets.yml').read_text()).get(args.host, [])
        if args.dest not in [entry['dest'] for entry in allowed]:
            raise ValueError('Destination is not in the host secret allowlist')
        if not args.source or args.source.is_symlink() or not args.source.is_file():
            raise ValueError('Provide a non-symlinked regular --source file')
        payload = vault_root / 'encrypted_files' / args.host / (args.dest + '.vault')
        if any(parent.is_symlink() for parent in [payload, *payload.parents]):
            raise ValueError('Refusing symlinked secret payload ancestry')
        if payload.exists():
            vault.decrypt(payload.read_bytes())
        if not args.check:
            deploy.private_directory(vault_root)
            deploy.atomic_private(payload, vault.encrypt(args.source.read_bytes()))
        print('Secret import validated' if args.check else 'Encrypted secret imported; no deployment was run')
        return 0
    if args.confirm_host != args.host:
        raise ValueError('Rollback requires --confirm-host matching --host')
    if not args.backup or args.backup.is_symlink() or not args.backup.is_file():
        raise ValueError('Provide an existing encrypted --backup file')
    try:
        payload = json.loads(vault.decrypt(args.backup.read_bytes()))
    except Exception:
        raise ValueError('Backup authentication failed; nothing was restored') from None
    expected = args.host + ('-system' if args.system else '')
    if payload.get('host') != expected or payload.get('version') != 1:
        raise ValueError('Backup identity does not match the explicitly selected host/scope')
    command = ['ansible-playbook', 'playbooks/rollback.yml', '--limit', args.host,
               '--vault-password-file', str(key_path), '--extra-vars', json.dumps({
                   'dots_restore_backup': str(args.backup.absolute()), 'dots_restore_system': args.system,
                   'dots_vault_root': str(vault_root)})]
    import socket
    if args.host == socket.gethostname().split('.')[0]:
        command += ['--connection', 'local', '--extra-vars', json.dumps({'ansible_python_interpreter': sys.executable})]
    if args.system and not args.check:
        command.append('--ask-become-pass')
    if args.user:
        command += ['--user', args.user]
    if args.check:
        command.append('--check')
    return subprocess.run(command).returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'vault-tools: {error}', file=sys.stderr)
        sys.exit(2)
