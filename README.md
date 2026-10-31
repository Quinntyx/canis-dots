# Dots, deployed with Ansible

This repository is the desired state for **araveia** (the primary workstation,
Ansible controller, and service node) and **syssec-canis** (the scoped lab setup).
It replaces Chezmoi; do not run both managers against these destinations.

## Deploy

On each existing EndeavourOS/Arch machine you intend to configure:

```sh
sudo pacman -S --needed ansible-core
cd /path/to/this/checkout
./scripts/deploy
```

That is the normal local deployment command, **including on araveia**. It selects
only the machine's enrolled inventory hostname, gathers its actual login/home/UID,
asks for its sudo password, installs the declared dependencies, enrolls existing
allowlisted secrets into local Vault storage, creates encrypted preimages, installs
configuration, and converges the selected services. No collections, manual yay,
manual npm tools, or plaintext secret files in Git are required.

These are existing, installed machines, not blank disks: preserve their OS,
network/Tailscale enrollment, data mounts, SSH trust, and application sign-ins.
Araveia's existing proxy secret is required; the command imports it automatically
without displaying it. A replacement machine needs the encrypted Vault store and
its separately backed-up password, plus its normal OS/data/auth restoration.
Ansible cannot manufacture account identities or recover missing credentials.
See [the exact boundary](docs/DEPLOYMENT.md#existing-machine-boundary).

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
