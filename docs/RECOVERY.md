# Reinstall and recovery boundary

1. Install EndeavourOS and Ansible Core yourself.
2. Use the existing trusted backup/restore procedure to restore the preserved
   docs disk, personal data and credentials, system/network identities and remote
   access. Keep an offline Vault password copy. Do not format the docs disk.
3. Obtain this checkout from Git; run `./scripts/deploy` on the restored machine.
4. After the existing Forgejo/runner and SSH access work again, normal merged
   configuration changes can deploy through Forgejo Actions.

The historical restore/backup references under `docs/backups/private_araveia/`
are preserved documentation, not a newly executable Ansible recovery subsystem.
At the owner's request, the separate scripts at
`/home/zlare/docs/backups/araveia/{backup,restore}.sh` were updated for the
integration below. The applied source patch is tracked as
[`araveia-t3assistant.patch`](backups/araveia-t3assistant.patch); a regression
applies it to the untouched historical references with `git apply --unidiff-zero`.
This is an exact-baseline, zero-context change record, not a general updater. Do not execute the archived
reference as a deployment tool. The real restore now runs native Ansible after
restoring data/identities/tools and starting Forgejo, before legacy helper/service
steps. Its old chezmoi apply was removed. An existing checkout must have the
expected origin, a clean main branch and a fast-forward update; no reset occurs.
Merge the native migration before using that restore; it explicitly refuses a
checkout without `scripts/deploy`.

The defensive `.chezmoiignore` containing `*` still makes an accidentally invoked
legacy chezmoi apply manage no files. That is not configuration deployment or
proof of whole-machine recovery. Retain verified restore scripts and backups.
No backup or full restore was run as part of this source change.

Normal deployment checks araveia's declared docs filesystem UUID, installed
Forgejo data/configuration and enrolled Tailscale address. It fails instead of
initializing a blank forge or guessing a new identity. The existing firewall
zone, tunnel enrollment, provider tokens, user data and runner registration must
already be restored. Missing or expired credentials still require their owner's
normal recovery/sign-in procedure; Ansible cannot invent them.

## t3assistant on araveia

- Ansible tracks the public app/MCP configuration templates and the complete
  araveia-only Pi profile, including the latest coursework references. The
  coordinator source remains the existing checkout on the preserved docs disk:
  `~/docs/src/universal-data-management/main`. It is not adopted into this repo.
- `backup.sh` now includes `.config/t3assistant` and
  `.local/state/t3assistant`: private overrides, OAuth token, baseline/evidence
  and scheduler state. The new `state.sqlite3` entry uses the script's existing
  SQLite online-backup loop rather than relying on a raw live-database copy.
  Existing Pi authentication and private Fish configuration were already covered.
- `restore.sh`'s existing home-data step restores these owner-private files and
  modes. Its native Ansible handoff installs the profile/config and restores the
  existing coursework timer on araveia only; the email timer remains disabled
  unless separately opted in. Ansible never commits or invents OAuth credentials.

**Refresh the private snapshot before wiping the OS:** adding paths to a script
never retroactively adds files to an old backup. Run the existing backup as its
owner procedure specifies, and inspect its result:

```sh
sudo /home/zlare/docs/backups/araveia/backup.sh
```

Private snapshot contents are not Git source. Expired tokens still require normal
provider renewal. Only the isolated home-data fixture was exercised here, not a
full restore, live backup, OAuth sign-in or service activation. The archived
procedure's other disk/system operations have not been re-audited by this update.

Removed by the simplification: `--fresh`, the recovery module/policy, root disk
bootstrap, secret enrollment, automatic preimage archives and custom rollback.
Their last complete state is available at checkpoint commit **f81385a**, not
mixed into normal desired-state deployment.

A configuration Git revert is not backup recovery. Packages, databases, personal
files, network identities, root snapshots and provider accounts have independent
recovery procedures. Never test them by applying this source to the active host
without explicit deployment authorization.
