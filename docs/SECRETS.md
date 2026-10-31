# Secrets and encrypted preimages

## Normal existing-machine deployment

`./scripts/deploy` imports existing, explicitly allowlisted private files into
`.vault/encrypted_files/<host>/<home-relative-destination>.vault` in memory, using
Ansible Vault. It never imports a whole live tree or prints secret values. The
policy is `policy/secrets.yml`; ordinary roles contain only configuration.

The controller creates `~/.config/ansible/vault-pass` with a random key if this is
the first real deployment. The file is controller-owned, mode `0600`; its private
parent is `0700`. Existing unsafe permissions, empty keys and symlinks are errors.
The store and private payload parents are `0700`, ciphertext files `0600`.
Override locations with `DOTS_VAULT_ROOT` and `DOTS_VAULT_PASSWORD_FILE` if needed.
The key is **not sent to managed nodes**, stored in Git, printed, or put in argv.

`--plan` creates nothing. `--check` does not create a persistent key/enroll files;
it can inspect existing local allowlisted secrets without copying them to public
source. A controller without the correct key cannot decrypt existing secrets or
backups and must stop rather than overwrite them.

Every selected host's enrolled secret and existing encrypted backup is
authenticated before any host deployment begins. Required missing service
credentials fail before mutation. Optional missing application credentials are
not fabricated. Secrets are installed with restrictive modes, `no_log: true`,
`diff: false`, and Ansible's normal encrypted transport/private temporary module
execution. Never enable verbose/debug callbacks that dump module internals.

## Backup, transfer and explicit import

**Back up the Vault key separately from `.vault/`.** Losing the key loses the
ability to restore the encrypted files. Git ignores both the store and common
credential filenames. Git ignoring is not encryption and is not a backup.
The main controller needs the store/key to deploy credentials to a replacement
main node; an existing local machine can enroll its own permitted files on its
first deployment. Normal SSH/Tailscale/provider authentication is preserved, not
cloned between hosts.

For an approved private file already available to the controller:

```sh
./scripts/vault-import --host araveia \
  --dest .local/share/cliproxyapi/secrets.json \
  --source /private/location/secrets.json
```

This encrypts only an exact allowlisted destination and does **not** deploy it.
It never prints the file. Use a protected source location and do not put secret
values in command-line arguments. The default import replaces a previously
authenticated payload only; deploy the affected component separately afterward.
Changing the proxy secret triggers its service restart on deployment.

Provider `auth.json`, token caches, browser profiles, SSH keys, runner database,
mail OAuth/keyring state, Tailscale node identity, Forgejo database and Cloudflare
enrollment remain runtime-owned. Optional runner enrollment configuration may be
encrypted explicitly by policy; the runner is not started without it. Do not turn
a source resolver's unmanaged result into permission to adopt these trees.

## Encrypted configuration rollback

Before installation, `dots_backup` takes **only declared destination preimages**
on the target and sends them through Ansible to controller memory. It records
regular-file bytes/modes, link targets, and absent destinations in an encrypted
`.vault/backups/<host>/<UTC timestamp>.vault` artifact. It never writes a plaintext
backup archive, follows a destination ancestor symlink, or adopts unlisted keys,
messages or databases. Root-owned system overrides use `<host>-system`, with
separate scope. Repeated identical preimages reuse the prior artifact.

To restore a deliberately chosen artifact to the same enrolled host:

```sh
./scripts/rollback --host araveia --confirm-host araveia \
  --backup .vault/backups/araveia/TIMESTAMP.vault --check
./scripts/rollback --host araveia --confirm-host araveia \
  --backup .vault/backups/araveia/TIMESTAMP.vault
```

Use `--system` only with an `araveia-system` artifact to restore the explicitly
managed root-owned files; sudo is requested. Host/scope identity must match.
Wrong-key/mismatched-host restoration fails without changes. A new encrypted
preimage is taken before restoration. Neither keys nor decrypted archive contents
are printed or placed in a plaintext controller JSON file.

This is **configuration rollback**, not disk imaging or package downgrade:
restoration restores recorded files/links/modes, leaves newly created files in
place when the old state was absent, never deletes unknown data, and does not
undo package installation, the explicit fresh-install full OS upgrade, account
groups, service enablement, or builds. `--fresh` also takes root configuration
preimages for fstab/hostname/resolver/tunnel changes before writing them. Recovery
of create-only private identities, mounted personal data, and manager-applied
firewalld runtime/permanent rules is **not** undone by restoring a file artifact. Reload
only the affected service after inspecting the restored configuration. Compare
artifact timestamps carefully: the earliest pre-migration artifact, not the
latest already-configured snapshot, is usually the intended migration rollback.
