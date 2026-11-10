# araveia reinstall: restore first, deploy the PR, merge last

## The actual sequence

Keep PR #3 **unmerged** until the restored machine has successfully deployed its
checkout. The existing restore procedure is still the chezmoi-era procedure; it
is not an Ansible bootstrap and does not require `ansible-core`.

1. Before wiping the OS, refresh and verify the existing private snapshot using
   its normal owner-operated backup procedure. Updated scripts do **not** add
   missing files to an older snapshot. In particular, verify the APK signing key,
   keyring, t3assistant database/token, private-config link and proxy hosting files.
   No backup has been run by this change.
2. Install EndeavourOS as required by the existing restore script: hostname
   `araveia`, user `zlare`, NVIDIA driver. Preserve the docs disk; mount its
   existing filesystem at `~/docs`. Do not format it.
3. Run the existing live procedure from the preserved disk:
   `sudo ~/docs/backups/araveia/restore.sh`. It restores system/data identities,
   home files, tools and services and **still runs chezmoi apply from pre-merge
   main**. Inspect its final failure summary and complete its manual follow-up.
   Nothing in that script invokes Ansible or requires this PR to be merged.
4. Install `ansible-core` yourself. Obtain **the current PR #3 branch**, not main,
   in a separate checkout and run `./scripts/deploy` there as your normal user.
   It selects the local enrolled hostname and prompts for sudo/Vault as needed.
   Do not switch the chezmoi source checkout to the PR before step 3: the PR has
   a deny-all `.chezmoiignore` and is deliberately not a chezmoi configuration.
5. Verify the machine and only then merge PR #3 and retire chezmoi. Retain the
   verified snapshot and restore scripts. Do not keep using chezmoi as the
   configuration manager after the migration. Merged main changes may deploy
   through Forgejo Actions once its existing runner/secrets/SSH access work.

For an existing PR checkout, fetch the PR's current head first: its branch was
rebased onto main. The exact reviewed checkout/commit is preferable to a stale
local branch. See [Deployment](DEPLOYMENT.md) for inventory, Vault and SSH
prerequisites; `./scripts/deploy --host syssec-canis` runs from araveia only after
that explicitly enrolled target and its ordinary SSH/sudo access are ready.

## Which scripts actually own recovery

The owning source while chezmoi main is active is
`docs/backups/private_araveia/executable_{backup,restore}.sh` on **main**. Commit
`1eb2734242bfe6b537169b2a115f56e15d83050c` repaired that source and was pushed to
both Forgejo `origin` and `github`. The authorized, backup-only chezmoi apply
updated `~/docs/backups/araveia/{backup,restore}.sh` and their package lists.
A subsequent pre-merge chezmoi apply therefore retains these repairs.

In this Ansible branch, the inert `.legacy.txt` files under
[`backups/private_araveia/`](backups/private_araveia/) are exact snapshots of
those repaired main scripts, **not executable Ansible roles**. The tracked
[`araveia-t3assistant.patch`](backups/araveia-t3assistant.patch) records the full
repair from pre-repair main `c6e9752` to `1eb2734`; despite its historical name,
it includes all of the backup additions and update-proxy restore step. Tests
reverse it, verify the old baseline hashes, reapply it and check the current
references. It contains no Ansible handoff. Do not apply it again to the already
repaired live scripts or use these reference files as a second recovery system.

The old claim that the live restore had removed chezmoi and invoked Ansible was
incorrect. That integration is not the procedure used for this reinstall.

## Newly protected private state

The main-source backup's explicit `home_paths` now includes:

- `~/.local/share/t3code-fork`, including the **irreplaceable**
  `android.keystore` and `android-signing.json`, and `hosting/`'s compose file
  and `nginx.conf`. The cache directory is excluded.
- `~/Applications/t3code-fork`, preserving the self-updating AppImage and its
  executable mode. No local `t3code-fork-bin` package is installed by restore.
- `~/.config/t3assistant` and `~/.local/state/t3assistant`, excluding cache.
  `state.sqlite3` participates in the existing SQLite online-backup loop.
  `config.private.json` is a symlink to
  `~/docs/omn/artifacts/t3assistant-config.private.json`; the **target remains
  on the separately preserved docs disk**. Copying the link is not a second
  backup of its target. Check both before wiping.
- `~/.local/share/keyrings`, `~/.config/scrabblebot`,
  `~/.config/claude-ambassator` and `~/.claude-ambassator`. The ambassador
  directory excludes the same `cache`, `shell-snapshots`, `session-env` and
  `downloads` directories as `.claude`.
- `~/.local/share/Steam/config/libraryfolders.vdf`. Re-check Steam's second
  library at `~/docs/SteamLibrary` after restore; the library itself stays on
  the preserved docs disk.

**Deliberately excluded:** Schooner's test config/data/state, including
`~/.config/schooner`, `~/.local/share/schooner`, `~/.local/state/schooner-*`;
`~/.local/state/argo-server`; and `~/.t3/scratch`. Schooner will be redeployed
through T3 Code later. There is no Schooner container reconstruction step and
no `incus` addition.

The shared package lists now include `audacity`, `gnome-keyring` and `perf`;
both the existing restore and Ansible consume them. Snapshot data, signing keys,
private configs, keyrings and provider tokens remain outside Git. Expired tokens
still need normal provider renewal; Ansible never invents credentials.

## T3 Code update proxy and desktop client

The existing live restore now runs `docker compose up -d` in
`~/.local/share/t3code-fork/hosting` **after its Forgejo step**. This recreates
`t3code-update-proxy` from the backed-up definition, without adding a second
Ansible owner for that compose stack. Inspect the restore's failure summary and
check the proxy's normal operation; restoring definitions does not prove DNS,
remote networking or a healthy release endpoint.

The desktop AppImage is shared by **both** enrolled workstations. Ansible
preserves an existing restored/self-updated binary, including a newer version;
only a missing copy triggers its verified bootstrap download. The bootstrap
needs the existing tailnet package endpoint. No pacman copy is removed
implicitly. The araveia-only coursework/Pi integration is separate from this
shared desktop client.

## Compatibility with freshly applied chezmoi main

The PR is rebased through repaired main `1eb2734`. Main's intervening Pi provider
changes, Mistral image input, changelog bookkeeping and coursework questionnaire
package are carried into native role sources. The main-only SSH include supplies
`User henry` for `syssec-canis` without replacing the restored personal SSH
config. Forgejo's additional `runner-2`/`runner-3` definitions are retained with
actual target UID/GID and Docker group, not hard-coded host account numbers.
Existing runner registrations/data remain runtime state; configuration changes
do not recreate an executor underneath its running job.

For coursework, Ansible prefers the regular private archive on the docs disk,
accepts/recreates **only the declared** state-path symlink to it, and retains an
existing legacy regular file without overwriting it. With no archive, that
regular file remains the fallback; with neither, public defaults are rendered.
Unexpected links or symlinked source ancestors are refused before reading
private contents. Rendered config remains mode `0600`, and private reads/rendering
suppress logs and diffs. The profile/config/MCP/timers remain **araveia-only**.

## Scope of proof

Checks exercise ordinary Ansible in disposable homes, both-host configuration,
restored private-file/link compatibility and isolated data-copy/proxy-command
fixtures. They do not run the backup or privileged restore entrypoint, install
real packages, deploy over SSH, activate services, launch the AppImage, sign in
to providers or prove a complete reinstall. This change's only active-home write
was the explicitly authorized backup-only chezmoi apply.

Ansible is desired-state configuration, not disk recovery or a personal-data
backup. Its deployment checks require araveia's declared docs filesystem,
restored Forgejo data/configuration and enrolled Tailscale identity. It fails
rather than initialize a blank forge or invent identities. Preserve existing
firewall/tunnel enrollment, provider tokens, private data and runner registration.
A Git revert/redeploy does not roll back packages, databases or a whole machine.
The removed custom recovery implementation remains historical at `f81385a`;
it is not part of the current deployment path.
