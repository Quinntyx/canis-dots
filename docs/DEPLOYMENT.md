# Deployment and ownership

## Existing-machine boundary

The default entrypoint is `scripts/deploy`; only Ansible Core 2.19+ needs to be
installed manually on the existing Arch-family machines. Python is included with
Ansible. The wrapper does not install software until invoked for a deployment.
It can run locally on either enrolled machine, or from araveia over ordinary SSH.
SSH connectivity, host-key trust, the target login, sudo authority, usable pacman
repositories, and existing network/data/auth state are inputs, not guessed values.
Use `--user` or a personal SSH `User` declaration when target logins differ.

This is a configuration/software migration, **not a bare-metal backup image**.
It does not partition/format disks, recover arbitrary personal data, rewrite
kernel/GPU configuration, import a whole `/etc` snapshot, fabricate Tailscale
keys, or perform provider sign-ins. `scripts/deploy --fresh` is the explicit
**local araveia reinstall** route: it mounts the existing UUID, requires matching
account/data ownership and a locked existing Forgejo install, validates the
private legacy snapshot, restores only `policy/recovery.yml`, and adds that
single UUID mount to fstab. It declares resolver and token-file tunnel
integration rather than replaying system dumps. System preimages are encrypted
before those named configuration changes. The existing data remains in place.

The system role uses firewalld's manager CLI for additive named `tailscale` zone
rules (SSH, mosh, proxy 8317), interface association, and public SSH; it preserves
unrelated zones/rules and does not replay old development-server/public-port
rules. A missing zone is activated with one validated reload only during explicit
fresh recovery (permanent SSH access is added first); existing nodes lacking the
zone fail for inspection instead of dropping unrelated runtime-only rules. An unexpected custom interface zone fails
for inspection. `policy/system.yml` records the exact owners. See
[recovery](RECOVERY.md) for data/identity inputs and retry boundaries.

Normal deployment checks the enrolled main-node Tailscale address for both
Forgejo and the proxy **before any application mutation**. Explicit fresh recovery
installs bootstrap prerequisites and restores the existing node identity first.
It intentionally fails early on the wrong identity instead of exposing a proxy on
a guessed public interface. Main-only IP bindings live in inventory, not lab
files. Package prerequisites are selected only from eligible components.

## Source layout

- `ansible.cfg`: inventory/plugins; host-key verification on; no retry files or
  target syslog containing module parameters.
- `inventory/hosts.yml`: explicit membership. `main_server` contains only araveia;
  `lab` contains only syssec-canis. No T3 connection catalog feeds inventory.
- `inventory/group_vars/all.yml`: defaults; actual user/home/UID come from facts.
  `inventory/host_vars/*.yml`: eligibility and genuine host/network differences.
- `policy/components.json`: dependency closure. Both wrapper and filter enforce
  that every requested component and dependency is eligible on that host.
- `roles/<component>/manifest.yml`: JSON (valid YAML) allowlists with `source`,
  `dest`, `kind`, `mode`, optional `hosts`, `owner`, and layout-link metadata.
  Most entries default to user ownership; upstream mirrors and runtime outputs
  are explicitly distinguished. `files/` and `templates/` use actual names,
  **not** legacy private/executable/dot filename encodings.
- `roles/*/tasks`: package/acquisition/service lifecycles, not recursive adoption.
- `policy/packages.yml`: official prerequisites; `roles/software/vars` and the
  curated historical package lists describe additional actively used software.
- `policy/externals.yml`: exact-ref, checksum-pinned upstream entrypoints.
- `policy/secrets.yml`: exact allowed private file destinations by host/component.
- `.vault/`: ignored local encrypted secrets and per-host preimage archives.
- `.artifacts/`, `.venv/`: ignored development outputs, never target configuration.

`policy/migration.json` accounts for every original tracked file and its original
SHA-256. Historical dispositions are evidence, not an alternate live manager.

## Ownership resolution

Use `scripts/dots-source --host HOST --home /actual/target/home DESTINATION`.
Home-relative destinations need no `--home`. It prints the controller source,
component, eligibility, and whether the item is user-editable. It never prints
file contents. Unknown destinations remain unmanaged; upstream assets point to
acquisition policy; secrets point to the Vault import route; system destinations
point to their role/manager rather than inviting direct `/etc` edits.

The deployed private marker `~/.config/ansible/dots-source.json` records
`source_root`, `inventory_hostname`, and last selected components. For a remote
deployment, `source_root` is a **controller path**, not necessarily a target path.
Verify that checkout's repository identity. A missing marker never authorizes
editing generated/package-managed configuration directly.

Symlinked destination ancestors are rejected, rather than following them into an
unowned tree. Layout links to shared Pi authentication/cache locations are
created only when absent; existing runtime files/directories are preserved and
not read into ordinary configuration backups. Provider credentials, sessions,
model caches, npm/Git package caches and identities are not user source.

## Lifecycle order and activation

The playbook resolves ownership and authenticates encrypted inputs/preimages
before installs or file writes. It installs selected prerequisites, prepares the
real account/user manager, and writes only declared files/templates/links. A
non-secret allowlist bundle makes the large static-resource set efficient without
copying whole live directories. Private parents and explicit file modes are
applied; no recursive ownership reset or pruning occurs.

System integration and Forgejo start before self-hosted source acquisition.
Forgejo's existing repositories/databases are **never copied, reinitialized, or
pruned**. The supported user unit runs Compose. The Docker group GID is gathered,
not hardcoded. The Docker daemon requires the data mount at boot, and the user
unit requires the mount and existing `app.ini`. Per-process Git URL rewrites use
loopback on araveia, with source reachability checked after Forgejo health; no
persistent personal Git rewrite or public tunnel is needed to fetch its sources.
An explicit account socket ACL allows the already-running user
manager to use Docker without forcing logout; Docker membership is root-equivalent.
The website remains its own repository and its own Actions deployment pipeline:
Ansible checks out source without forcing dirty work, and starts a runner only
when an existing private enrollment is available. It does not publish site
content or mint runner credentials. Theme sources keep their literal Go-template
syntax and are installed in Forgejo's actual `gitea/` custom path.

Tmux uses pinned tmux-resurrect, its existing main-server-only persistence helper
and timer, with unbounded completion-aware restore/save behavior preserved.
Existing tmux reloads only after configuration changes; no tmux server is created
merely to deploy files. Mail restores programs/config/hooks and starts selected
user units, but never copies messages, notmuch indexes, or OAuth stores into Git.

The proxy is built from its owning clean Git checkout, with an exact successful
build receipt. A failed upgrade is retried even if the checkout already advanced.
Changed binary or secret/configuration triggers service restart. Its secrets
remain outside public YAML and arrive through Vault. Desktop files apply without
forcibly restarting the compositor, display manager, browser, or audio session.

Agent CLIs use account-owned npm prefixes. Pi profile resources are acquired
through **Pi's supported package manager** under explicit profile environments;
no caches are edited as source, and the active `ppi` selection is not switched.
A successful settings-checksum receipt avoids rolling package updates on every
unchanged deployment. Manually clear only the affected receipt after reviewing a
recovery need; normal package updates belong to the manager's specific update
route. Existing provider authentication remains local. Upstream mirrored skills
keep their original baseline hashes/ownership; change acquisition/source
ownership, not downloaded copies.

Curated application software runs last, after self-hosted Git is healthy. Missing
local PKGBUILDs are acquired at declared refs into a package-source cache if the
original personal checkout is unavailable; existing personal repos are never
pulled/reset/cleaned. See [software](SOFTWARE.md) for the bounded package-build
privilege contract and intentionally unsupported vendor installers.

## Selection and adding a host

Defaults deploy the local short hostname only, never the whole inventory. Unknown
hosts fail closed. `--all` is a distinct explicit fleet-wide action. Omitting
`--components` selects that host's full allowed set; dependencies are added but
cannot grant server eligibility. The playbook repeats the membership checks, so
raw role requests are not an eligibility bypass.

Before enrolling another machine, verify its actual hostname/OS/login/network,
add explicit `inventory/hosts.yml` membership and host variables, choose its
components, and add only approved secret policy. Never treat a shared T3 device
or observed tailnet peer as consent to configure it. Test its configuration in a
disposable home before any authorized real run.

`--config-only` disables packages, external acquisition and service activation;
it is useful for an already-provisioned account, not a substitute for bootstrap.
`--plan` only resolves inventory selection and makes no key/configuration writes.
`--check --diff` reads live state but skips actual builds/installers and suppresses
secret diffs. Missing fresh-host prerequisites can make check mode fail; check
mode does not prove package installation, network availability, or activation.
