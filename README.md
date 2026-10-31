# Dots, deployed with Ansible

This repository is the desired state for **araveia** (the primary workstation,
Ansible controller, and service node) and **syssec-canis** (the scoped lab setup).
It replaces Chezmoi; do not run both managers against these destinations.

## Deploy

On each existing EndeavourOS/Arch machine you intend to configure:

```sh
sudo pacman -Syu --needed ansible-core
cd /path/to/this/checkout
./scripts/deploy
```

That is the normal local deployment command, **including on araveia**. It selects
only the machine's enrolled inventory hostname, gathers its actual login/home/UID,
asks for its sudo password, installs the declared dependencies, enrolls existing
allowlisted secrets into local Vault storage, creates encrypted preimages, installs
configuration, and converges the selected services. No collections, manual yay,
manual npm tools, or plaintext secret files in Git are required.

### Fresh EndeavourOS reinstall of araveia

**Preserve the separate `docs` disk; do not format it.** Install EndeavourOS with
an existing normal sudo-capable account using the same UID (currently `1000`).
The data volume must retain UUID `40eda021-8152-4dab-8be2-f19307298da2`, the existing
Forgejo data/installation lock, and private `backups/araveia/{home,root}` snapshot.
Keep an offline copy of this checkout (or fetch the PR branch from the public
[GitHub mirror](https://github.com/Quinntyx/canis-dots), branch `t3/164ce4df`
until PR #3 is merged, then `main`) so restoring
this forge does not require the forge to already be running.

Then, with internet access and Ansible installed, as the **normal account**:

```sh
cd /path/to/this/checkout
./scripts/deploy --fresh
```

This mounts only the approved existing filesystem (never formats), checks its
ownership and nonblank Forgejo installation, validates and restores allowlisted
private runtime identities, refreshes and **fully upgrades** the fresh Arch OS
with bootstrap packages (avoiding an unsupported partial upgrade), restores DNS/tunnel
integration and the enrolled hostname, then runs normal deployment. It uses
loopback for this node's self-hosted Git fetches. It does not blindly restore old
`/etc` or adopt personal repositories. `--fresh --check` checks recovery only;
it does not pretend an unmounted disk or newly installed service is available.

Fetch the checkout over HTTPS and run recovery **before** creating new SSH files
or starting sshd: conflicting account files/host keys fail safely rather than
being overwritten. No unrelated firewall dump or LAN trusted subnet is restored.

Before wiping, preserve any `.vault/` together with its **separate** password
file, push personal/worktree branches, and retain current credentials. The
existing snapshot is not a live backup and OAuth tokens may have expired; no
automation can recreate lost keys, personal data or provider sign-ins. Completed
recovery records a private receipt so retrying `--fresh` does not replay stale
rotating tokens. Resume later convergence with `./scripts/deploy`.
See [recovery procedure and exact exclusions](docs/RECOVERY.md).

Normal deployment of existing machines still requires their enrolled data and
network identity; araveia's required proxy secret is imported automatically
without displaying it. See [the exact boundary](docs/DEPLOYMENT.md#existing-machine-boundary).

Araveia can also be the controller for remote deployment, using normal SSH
configuration/trust and the account already configured on the target:

```sh
./scripts/deploy --host syssec-canis               # SSH from araveia
./scripts/deploy --host syssec-canis --user LOGIN  # if SSH has no User configured
./scripts/deploy --all                           # explicitly authorize BOTH hosts
```

No connections are discovered from T3. No phone, shared device, or unconfirmed
machine is enrolled. Host/component eligibility is enforced by the playbook as
well as the wrapper: asking for a server component cannot turn the lab into a
server. **Do not add `--all` for a local-only change.**

## Inspect or narrow an authorized deployment

```sh
./scripts/deploy --plan                    # selection only, no key/config writes
./scripts/deploy --check --diff            # live reads; no target changes
./scripts/deploy --components tmux         # includes its shell dependency
./scripts/deploy --config-only             # files only; no installs, external fetches, or service activation
./scripts/dots-source --host araveia .config/fish/config.fish
```

`--check` can fail on missing prerequisites and cannot prove first-boot builds or
service activation. Configuration-only mode assumes prerequisites already exist.
Component selection is **not exact-file selection**. The deployment does not prune
unknown files or reconcile unrelated managers' outputs.

## What is managed

- Shared shell, Git, tmux persistence, editors, and profile-aware agent setup.
- Main-only desktop, mail, CLIProxyAPI, Forgejo/website integration, system
  overrides, and [curated used software](docs/SOFTWARE.md).
- Public files/templates have explicit destinations/modes; upstream/runtime
  ownership is marked rather than silently adopted.
- [Secret provisioning and encrypted rollback](docs/SECRETS.md).
- [Migration coverage and intentional exclusions](docs/migration/README.md).

For ownership, host/network differences, services, and extending inventory, read
[deployment architecture](docs/DEPLOYMENT.md). For source-only development and
non-destructive verification, read [AGENTS.md](AGENTS.md).

**Source readiness is not a deployment:** this migration was built and tested in
disposable homes. It does not apply itself, deploy the website, rewrite the
currently active profile, or migrate live data merely by being merged.
