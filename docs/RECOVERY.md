# Fresh-install runtime recovery

## What this is, and what it is not

A replacement araveia install needs runtime identities that Ansible cannot
manufacture: SSH/GnuPG keys, provider logins, the Tailscale node key and the
Cloudflare tunnel token. `dots_recover` copies an **enumerated** set of them,
once, from the **existing legacy private snapshot** onto the fresh install.

- **Input: the legacy plaintext snapshot.** It was written by the retired
  `backup.sh` (baseline recorded in
  `docs/backups/private_araveia/backup.sh.legacy.txt`) and already exists on
  the preserved docs disk, e.g. `/preserved/docs/backups/araveia`. This
  repository does **not** add a new plaintext snapshot exporter, and nothing
  here refreshes that snapshot.
- **New backups are different.** Ongoing secrets and configuration preimages are
  Ansible Vault ciphertext under `.vault/` ([secrets](SECRETS.md)). Recovery
  neither reads nor writes `.vault/`.
- **Not lossless personal-data recovery.** The legacy snapshot also holds app
  data, sessions, browser profiles, game saves, `~/src`, downloads and more.
  This tool restores none of that. Anything outside the policy stays in the
  snapshot for a deliberate, separate decision.

## Snapshot layout

```
<snapshot>/home/<home-relative path>   source for scope "home"
<snapshot>/root/<root-relative path>   source for scope "system"
<snapshot>/reference/                  never read
```

The legacy script copied exact policy paths with `rsync -aR`, so files keep their
original owners: user-owned under `home/`, root-owned under `root/`. The snapshot
root and its `home/`/`root/` directories are `0700`. Forgejo's database and
repositories, `docs/host/forgejo/.env` and the runner enrollment
`docs/host/forgejo/runner-data/runner-config.yml` are **not** in the snapshot.
They stay on the preserved docs disk and are used in place, so the policy has no
`docs/` entries.

## Module interface

```yaml
- name: Recover home runtime credentials from the legacy snapshot
  become: true
  no_log: true
  dots_recover:
    snapshot: /preserved/docs/backups/araveia   # absolute, normalized
    home: /home/LOGIN                           # destination root
    scope: home                                 # home | system
    operation: restore                          # validate | restore
    entries: "{{ (lookup('file', 'policy/recovery.yml') | from_json)[inventory_hostname].home }}"
    # owner: LOGIN            optional; home scope only, must equal the home owner
    # group: LOGIN            optional; home scope only, defaults to the home group
    # snapshot_owner: LOGIN   optional; extra account trusted to own snapshot paths
```

| Parameter | Meaning |
| --- | --- |
| `snapshot` | Snapshot root. Every ancestor must be a real directory (no symlinks) owned by root, the module's effective user or the trusted snapshot owner. It must be either not group/other-writable or sticky. The root and its `home`/`root` subdirectory must have no group/other permissions. |
| `home` | Destination root: the account home for `home`, `/` for `system`. Tests pass a disposable directory; the parent passes the real `/` only outside the sandbox. |
| `scope` | `home` reads `<snapshot>/home`; `system` reads `<snapshot>/root`. |
| `operation` | `validate` checks everything and returns would-be counts, never writes, and reports `changed: false`. `restore` writes unless Ansible `--check`. |
| `entries` | List of `{path, kind, required, mode?, exclude?}`. |
| `owner`, `group` | Home scope only (an error in system scope). These are a user name or a numeric ID. If omitted they are inferred from the trusted, non-symlink destination home. An explicit `owner` that differs from the home's owner fails. |
| `snapshot_owner` | A user name or UID. For home scope it defaults to the destination owner. For system scope it is unset, so only root/effective-user snapshot ownership passes. Pass the login if the legacy `root/` directory or snapshot root is user-owned. |

Entry fields:

- `path`: a normalized relative path, with no `.`, `..`, empty components or
  leading `/`. Duplicates and overlapping entries are rejected.
- `kind`: `file` must be a regular source file. `tree` must be a real source
  directory and is copied recursively.
- `required`: a missing required source fails the whole run. A missing optional
  source is counted in `missing_optional`.
- `mode` (`file` only): `"0600"`, `"0644"` or `"0700"`, as a quoted string.
  This is used for public SSH host keys. Without it, files are `0600`, or
  `0700` when the source has any execute bit.
- `exclude` (`tree` only): exact relative paths inside the tree. A file entry
  inside a tree is allowed only when it is excluded from that tree. This is how
  `.local/share/cliproxyapi/secrets.json` is a separate required entry.

Results contain only counts: `changed`, `entries`, `created_dirs`,
`created_files`, `created_links`, `matched`, `skipped_sockets` and
`missing_optional`. No paths, names or payloads are returned. Failures name the
public policy entry and a generic reason, such as `Recovery conflict: existing
destination differs at policy entry .ssh`. They never include tree-internal
names, bytes or OS error strings.

## Guarantees

- **Validate all, then write.** The module reads and checks the whole inventory
  before its first write: source and destination, ownership, permissions,
  special files, links, required presence and conflicts. Any failure leaves the
  destination untouched.
- **Create-only.** An existing destination file or link must already match
  exactly (bytes or link target, mode and owner). If it does not, the run fails.
  Nothing is overwritten, renamed over or deleted. Each file is written to a
  private temporary file opened with `O_EXCL|O_NOFOLLOW`, then fchowned,
  fchmodded and fsynced. It is published with `link(2)`, which cannot replace a
  name. The temporary file is then removed.
- **No symlink following.** Both trees are walked with `O_NOFOLLOW` directory
  descriptors. A symlinked source or destination ancestor fails, and so does a
  symlinked source file for a `file` entry. A tree symlink is recreated only if
  it is relative and lexically stays inside its tree. Absolute or escaping links
  fail the run.
- **Special files.** Sockets (for example GnuPG's `S.gpg-agent*`) are skipped and
  counted, never opened. FIFOs and device nodes fail the run. Files are opened
  with `O_NONBLOCK`, so a FIFO swapped in during validation can never hang.
- **Snapshot trust.** Every source directory, file and link must be owned by a
  trusted account (root, the effective user or the snapshot owner). Directories
  and files must not be group/other-writable.
- **No adoption.** Existing directories are never chmodded, chowned or adopted
  recursively. An existing directory on the path must be a real directory owned
  by root or the target account, and not group/other-writable. Only enumerated
  missing directories are created (`0700`), along with files beneath them.
- **Ownership under `become: true`.** Home-scope creations are chowned to the
  target account, never left root-owned. System-scope creations belong to the
  module's effective user, which is root in real use.
- **Bounded.** The total source size is limited to 512 MiB.

## Policy (`policy/recovery.yml`)

The policy is JSON (valid YAML), keyed by inventory host. `syssec-canis` has empty
lists. For araveia:

- **home**:
  - Critical (required): `.ssh` and `.gnupg` trees, `.config/pi/agent/auth.json`,
    the `.local/share/cliproxyapi` login pool and its separate required
    `secrets.json`.
  - Optional:
    - `.config/pi/agent/antigravity-accounts.json`, the shared Pi auth that
      profile `auth.json` links target.
    - Every non-`docs/` destination in `policy/secrets.yml`.
    - `.local/state/oama` and `.config/mail-router`.
    - `.config/gh/hosts.yml`, `.local/share/forgejo-cli/keys.json`,
      `.git-credentials`, `.codex/auth.json`, `.claude.json` and
      `.config/opencode/antigravity-accounts.json`.
- **system**:
  - Required: `var/lib/tailscale/tailscaled.state` and `etc/cloudflared/token`.
  - Optional: `etc/ssh/ssh_host_{ed25519,rsa,ecdsa}_key` (`0600`) and their
    `.pub` files (`0644`).

The policy deliberately excludes the following:

- Root's `cloudflared.service` unit, any other `/etc` file, fstab, firewall
  zones, NVIDIA/GPU profiles, keyd, cups and NetworkManager. Their owners are in
  `policy/system.yml` and [deployment](DEPLOYMENT.md).
- Whole `.config/pi`, `.pi` or `.claude` trees, Pi `shared/` extensions,
  plugin/npm/Git caches, sessions and per-profile `mcp-auth.json` files.
- Personal data and repositories.

Recovered `policy/secrets.yml` destinations are ordinary existing private files.
The first normal deployment enrolls them into Vault as described in
[secrets](SECRETS.md).

## Ordering and conflicts (for the bootstrap integration)

Run `operation: validate` first, then `restore`. Restore after accounts and
packages exist, and **before** the relevant services first start:

- tailscaled must not have created its own `tailscaled.state`.
- sshd's first start generates host keys.
- cloudflared needs its token.

A service that already created its own state causes a conflict that fails the
whole run. Resolve it by deliberate manual inspection, not by forcing an
overwrite.

A missing `/etc/cloudflared` is created as root `0700` with a `0600` token. Adjust
the policy if the enrolled unit runs as a non-root user. Reuse the Tailscale node
key only after the old install is gone, so that two nodes never share one
identity.

Re-running is idempotent. Identical existing files count as `matched`. If a run
fails mid-write (an I/O error after validation), only new files remain, and a
re-run continues from there. Nothing is recorded for configuration rollback: to
undo recovery, remove the created files manually. Every created path lies
inside the enumerated policy entries.

## Open blocker: stale OAuth state

OAuth refresh tokens rotate. The legacy script itself warned that an old
snapshot can restore dead tokens: CLIProxyAPI pooled logins, Pi, oama,
gcal-sync, and likely Codex/OpenCode/Antigravity. Recovery copies whatever the
snapshot holds and does not test, refresh or re-mint credentials. The legacy
restore notes already recorded gcal-sync as expired. **No refresh procedure is
defined here.** How to detect and re-authenticate stale providers on the new
install is still to be decided with the owner, and must not be improvised from
this tool.

## Verification

`tests/test_recovery.py` exercises the module in disposable trees. It covers:

- Unit cases for modes, sockets, conflicts, symlinked ancestry, link escapes,
  inventory shape, snapshot permissions, ownership and validate-before-write.
- The policy's exact system set.
- A real `ansible-playbook` run (check mode, restore, idempotent repeat and
  conflict) with `no_log` that asserts the payload never appears in output.

It never touches the active home, `/`, the real snapshot or services. Running as
root, real chown to another account, and the live legacy snapshot were not
exercised.
