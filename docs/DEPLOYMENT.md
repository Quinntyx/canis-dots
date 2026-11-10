# Deployment

## Model

This repository is ordinary Ansible Core source. The existing EndeavourOS
restore procedure runs **first** after a reinstall. Normal Ansible then converges
configuration, packages, user services and the main node's integrations. It does
not format/mount disks, recreate identities or restore databases.

Run as the intended normal target account. `dots_home`, `dots_user` and `dots_uid`
come from that account's gathered facts, not a hard-coded home. Privileged tasks
use `become: true`; account-local tools remain unprivileged. Only araveia and
syssec-canis are enrolled, regardless of T3 connections or tailnet discovery.

## Commands

```sh
./scripts/deploy                     # this enrolled machine, local connection
./scripts/deploy --host syssec-canis  # remote, ordinary SSH
./scripts/deploy --all               # both hosts, serial: 1
./scripts/deploy --check --diff       # read-only preview, not install proof
```

Arguments after the wrapper's optional host selector are standard
`ansible-playbook` arguments. It prompts for sudo and encrypted Vault files.
For direct invocation, set `ANSIBLE_CONFIG` to this checkout's ansible.cfg if
running from another directory; the wrapper changes into the checkout for you.
For a deliberately noninteractive local invocation, `DOTS_UNATTENDED=1` suppresses
only the sudo prompt; provide standard Ansible become/Vault credentials yourself.
Forgejo uses `ansible-playbook` directly, not this convenience variable.

```sh
ansible-playbook playbooks/site.yml --limit araveia -c local --ask-become-pass
# Add --ask-vault-pass or standard ANSIBLE_VAULT_PASSWORD_FILE when needed.
```

`--tags shell`, `--tags tmux` etc. use Ansible's ordinary tag behavior, not custom
dependency selection. Common prerequisites still run. Prefer the complete play
for an initial post-restore deployment. A failed target stops the serial play;
fix it and rerun. Unchanged files/installed packages remain untouched; failed
builds and incomplete Pi extension reconciliations are retried.

## Source ownership

`roles/<component>/tasks/config.yml` names ordinary `copy`, `template` and `file`
operations through small shared task includes in `roles/common/tasks/`. Static
file sources are destination-shaped under `files/<host-scope>/<mode>/`. For
example `.config/fish/config.fish` is the shell role's
`files/common/0644/.config/fish/config.fish`.

The tree copy checks destination directories and files without following links,
does not delete unrelated files, and keeps executable/private file modes explicit.
Templates retain literal embedded syntaxes with standard Jinja header delimiters.
Runtime-owned credentials and personal repositories are not recursively adopted.
Upstream skills are obtained by their owner/acquisition instructions, not modified
to contain local policy. Native handlers restart only declared affected services. Vault file deliveries
name affected roles with `services`, rather than restarting every service.

Araveia-only roles are system, desktop, mail, CLIProxyAPI, Forgejo, website source
and curated software. The lab receives shell/Git/SSH/tmux/editor/agent setup plus
the shared `t3code` desktop-client role, not the main node's full desktop stack.
Both enrolled hosts declare the client's FUSE/Electron prerequisites and receive
its AppImage, launcher and icon. `--tags t3code` selects this shared client with
ordinary common prerequisites. Its bootstrap is disabled in check mode, sandbox,
and when packages or external acquisition are disabled. The lab's personal SSH
config is preserved and receives an isolated config.d include.
Main role data checks refuse an unmounted/wrong docs filesystem, empty Forgejo
installation, or a different Tailscale address before application writes.

The entire t3assistant/coursework profile is **araveia-only**, including its
settings, skills, shared auth/model links, application config, MCP connection
and service/timer definitions. Normal lab deployment never acquires its profile
packages or creates its profile directory. Existing unknown lab files are not
pruned. Unit files also carry `ConditionHost=araveia` as a runtime guard.

Its restored `.local/state/t3assistant/config.private.json` overrides the public
config defaults with private output/log suppression. Ansible preserves araveia's
existing enabled `t3assistant-coursework.timer`: after checking the coordinator
checkout, rendered config and restored OAuth file, it enables/starts that timer
without restarting an active job. The email timer remains opt-in and no provider
registration or coordinator checkout is manufactured. Source development does
not run these tasks against the active machine.

The private config and runtime state belong in the existing backup, not Git.
The exact backup/restore integration, refresh command and limits are documented
in [Recovery](RECOVERY.md#compatibility-with-freshly-applied-chezmoi-main).

## Forgejo Actions: one-time setup

The workflow in `.forgejo/workflows/ansible.yml` uses the existing runner with an
`ubuntu-latest` label capable of starting Docker jobs. Its job containers install
controller/test dependencies; this does not install tools on the runner host.
The runner must be able to resolve and SSH to both inventory hostnames, including
araveia itself, through the existing network. Do not expose target SSH publicly
or disable host-key verification to make a job succeed. Verify name resolution
from an actual job container, not only from the runner host. If short names are
not resolvable there, set each host's ordinary inventory `ansible_host` to its
verified reachable address/FQDN and use matching entries in `ANSIBLE_KNOWN_HOSTS`.

Add these **repository Actions secrets** in Forgejo:

| Secret | Value |
| --- | --- |
| `ANSIBLE_VAULT_PASSWORD` | Password for the encrypted files committed here |
| `ANSIBLE_SSH_PRIVATE_KEY` | Deployment key whose public half is authorized on both normal accounts |
| `ANSIBLE_KNOWN_HOSTS` | Verified SSH host-key lines for araveia and syssec-canis |
| `ANSIBLE_SSH_USER` | Normal login account used on both machines |
| `ANSIBLE_BECOME_PASSWORD` | Its sudo password on both machines |

The initial workflow assumes the same login name and sudo password on both
machines. If they differ, use ordinary inventory host variables with Vault-
encrypted per-host passwords instead of this shared CI variable override.
Never put the actual values into the workflow. Set up/verify SSH authorization
through your existing trusted administration channel; Ansible cannot bootstrap
its own missing remote access. For key-only noninteractive sudo, deliberately
configure the chosen policy separately instead of silently granting NOPASSWD.

PRs and `main` pushes run source/disposable checks. Only a successful `main`
check permits deployment; `workflow_dispatch` is also restricted to main.
Deployments are serialized without cancelling one halfway through a host. The
normal play serializes the two hosts. The runner/Forgejo version must support
job-level `concurrency`; verify that on the existing installation before enabling
automatic deployment. An offline lab machine makes deployment
fail rather than silently claiming the fleet was updated. Inspect the job and
rerun after restoring access; there is no unattended retry daemon or auto-merge.

Secrets exist only in the deployment step. Native Vault reads a temporary private
password file; SSH uses a temporary private key and verified known_hosts. A trap
removes the temporary directory using Ansible's file module. Commands never
contain password values. Job containers are disposable. Forgejo's encryption is
not an offline backup: retain the Vault password outside Forgejo so reinstalling
its host does not create a recovery dependency cycle.

Same-repository workflow authors are trusted with deployment secrets under the
owner's chosen two-user/owner-merge trust model. Branch checks are an operational
approval convention, not a claim that branch writers cannot access repository
secrets by changing workflows. Workflow files and secrets are not enabled or
executed by source validation. Keep this PR open until the owner merges it.

### Forgejo and runner activation

Forgejo's change handler force-recreates only the `forgejo` container, so mounted
configuration/template changes activate even if Compose YAML is unchanged. It
does not recreate the Actions runner that may be executing this deployment.
The website role starts an already-enrolled runner with `--no-recreate`. Runner
image/definition changes therefore require a separately scheduled, explicit
runner recreation when no job is running; merging this repository does not
silently replace its own running executor.

For this reinstall, keep the separate restore procedure's chezmoi step: run the
repaired live restore against **pre-merge main**, then deploy the current PR #3
checkout, and merge only after verification; see [Recovery](RECOVERY.md). Do not
point chezmoi at the PR first. This source's deny-all `.chezmoiignore` prevents a
later legacy apply from putting the Ansible tree into your home.

## Rollback and verification

Revert the unwanted source commit, review/merge the revert, and redeploy. This
restores desired configuration only. It does not downgrade packages, reconstruct
deleted files, restore a database/schema, revoke credentials, reverse groups or
restore a whole machine. Use the existing separate backups for those operations.

`./scripts/check static` checks syntax/source ownership and whitespace.
`deployment` runs real Ansible in disposable homes including standard Vault;
`software` records package/build/Pi decisions with executable substitutes;
`tmux` checks the persistence protocol. `all` runs them together. No real
installation, sudo/SSH, provider sign-in, service activation or visual capture is
claimed by these tests. Only explicit real-host deployment can exercise those
remaining boundaries.
