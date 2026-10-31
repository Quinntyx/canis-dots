# Software provisioning

Normal Ansible installs the declared, actually used software after the existing
restore procedure. It does not import `pacman -Q` output as desired state, reset
personal repositories, upgrade the whole OS or install packages during source
checks.

## Official packages

`policy/packages.yml` is a small YAML variable file grouping role prerequisites.
The software role also reads the curated commented package lists preserved under
`docs/backups/private_araveia/packages/`. It excludes the retired chezmoi manager.
All installations use the distro's `pacman` through `ansible.builtin.command`:
query installed names, then `pacman -S --needed` only for missing names. No sync-
database refresh, system-wide upgrade, forced removal or package replacement is
hidden in the play. Maintain a coherent Arch installation through its normal OS
update procedure before deploying; this is not an upgrade manager.

ACL/sudo/util-linux/build prerequisites are installed before unprivileged become
or tool setup. The curated PipeWire JACK provider is held when jack2 is already
installed rather than forcing a conflicting replacement. The play reports the
hold and its interactive resolution. Missing official build dependencies are
queried with pacman's dependency test, preserving existing virtual providers.

## AUR and owned PKGBUILDs

Native tasks in `roles/software/tasks/{builder,build-package,builds,aur}.yml`
clone a declared recipe, evaluate its metadata, install missing official
dependencies, build unprivileged, and install only completed current artifacts
through root pacman. No custom Ansible plugin, request protocol, root bridge or
sudoers grant exists. PKGBUILDs execute under **dots-builder**, a system account
with a locked password, nologin shell, private home and no sudo group; `setpriv
--no-new-privs` prevents acquiring new privilege. They do not receive the login
account's home, authentication stores or cached sudo ticket. Package installation
itself is privileged and trusts the chosen package's install scripts, as normal
pacman operation does. The account is a privilege separation boundary, not a
network/filesystem sandbox or an approval of arbitrary unreviewed recipes.

Desktop/mail prerequisites have explicit reviewed AUR revisions in inventory.
Bulk AUR software uses the curated list in its declared order and current AUR
recipe HEAD; already installed packages are not rebuilt or upgraded. Dependencies
that are themselves AUR packages must be explicitly listed before dependents;
unknown dependencies fail rather than adding a recursive acquisition engine.
Debug split artifacts and old package versions left in a build cache are not
installed. The next run retries any package whose build/install did not finish.

`roles/software/vars/local-sources.yml` names the owning repositories and exact
refs for omn-git and t3code-fork-bin. They are acquired into the build account's
managed cache, never by resetting an existing personal development checkout.
The restored Forgejo must be healthy first; private source access must be
explicitly supplied through its normal owner rather than copied from user auth
stores. Trusted signed custom-repository applications remain part of the existing
restore procedure, not silently replaced with a downloaded binary or alternate
package source. The source preflight and isolated package builder use the same
araveia-local Forgejo URL rewrite, including Git invoked from inside makepkg.
The declared bootstrap repositories must allow anonymous read access on that
restored forge; unavailable/private sources fail the preflight rather than
borrowing personal credentials.

## Account-local tools

Packaged npm, rustup, cargo-binstall and uv install account-local CLIs under the
actual account's prefix. npm includes Pi, pi-profiles, Claude Code and Codex.
Rustup preserves an existing selected toolchain and installs it if missing;
otherwise it initializes stable. Cargo binary acquisition disables third-party
quick-install and telemetry. Existing installed CLI versions are not forced to
upgrade. Installer scripts run without a controlling TTY or cached sudo ticket.

uv provides Python 3.14 and the existing PTC scientific environment without
clearing an existing venv. Optional layer-shell-rs and astala-downloader use
preserved local source only, with absence reported instead of inventing a new
upstream. Provider credentials/sign-ins are runtime state, not CLI installation.

The agents role installs explicit Pi versions from inventory if missing and uses
`pi update --extensions` for every host-eligible configured profile. The profile
list is a small normal role variable; files are managed by native role tasks.
Pi owns its Git/npm resource caches. A successful reconciliation records the
settings checksum; failure records no success and retries. It does not self-
update Pi, change the selected active profile, patch installed resources, or
inject local policy into upstream-owned skill files.

## Session and services

The main desktop is niri with its declared Wayland applications and portals,
PipeWire/WirePlumber and Syncthing. It is not replaced by a Hyprland/Fcitx stack.
Session starts do not forcibly restart a running compositor or replace an
existing display manager. First graphical login remains the owner's action.
Native configuration handlers restart declared user services on changed inputs;
binary build failure does not publish a successful receipt or service restart.
Website publication stays in the website repository's separate Actions pipeline.
The website and CLIProxyAPI paths under `~/docs` are personal source checkouts:
Ansible clones them only if missing and never updates, switches branches or
resets an existing checkout. You update those sources through normal Git work.
The proxy builds from that checkout's current HEAD, recording only successful
builds; the isolated package recipe caches are instead manager-owned and may be
reset to retry a recipe changed by a failed VCS build.

## Evidence

`PATH="$PWD/.venv/bin:$PATH" ./scripts/check software` executes real Ansible
control flow against disposable homes and recording substitutes for installers,
package builders, Pi and privilege commands. It tests missing/already-installed
packages, provider conflicts, dependency decisions, artifact selection, toolchains
and failed-resource retry. It is **not** evidence of a live AUR build, successful
provider login, sudo/SSH operation or working graphical session. `check-packages`
is an optional read-only availability query against existing Arch sync databases;
it installs/refreshes nothing.
