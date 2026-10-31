# Curated araveia software

The parent playbook's **software** component includes `roles/software` **only on
araveia**, and **last**, after restoring account configuration and starting Forgejo.
Local omn PKGBUILDs fetch from the Forgejo hosted on this machine. Membership and
host selection belong to the parent; importing the role alone is not a host guard.
This is not a replay of every package once installed on the old machine.

After installing `ansible-core>=2.19`, run the parent's normal apply command with
become authentication (`--ask-become-pass`). No external Ansible collections,
preinstalled yay, manual npm/cargo dependencies, or downloaded shell installers
are required. The parent supplies `dots_user` and the gathered account's real
`dots_home`; the role checks that home against passwd. It does not hardcode a
username or `/home` layout. The EndeavourOS installer still owns the base system,
kernel, firmware, NVIDIA drivers and networking. Existing pacman repositories
must be usable; the role never does a partial `pacman -Sy` refresh or full upgrade.

## Installation contract

`roles/software/vars/main.yml` directly parses the curated files (one package per
line, comments allowed), rather than copying a stale second list:

| Source | Installation |
| --- | --- |
| `docs/backups/private_araveia/packages/pacman.txt` | Native `pacman -Qq`, then `pacman -S --needed --noconfirm` for missing names only. `chezmoi` is deliberately excluded. |
| `docs/backups/private_araveia/packages/aur.txt` | Missing names only, one at a time through EndeavourOS's yay. If missing, yay is built as the account from `https://aur.archlinux.org/yay.git` in an isolated workspace. |
| `docs/backups/private_araveia/packages/local.txt` | Existing `~/docs/` recipe paths are used without pulling/resetting their repositories. For missing packages whose recipe is absent, `roles/software/vars/local-sources.yml` acquires the exact declared owning repo/ref into a package-source cache. Installed packages are skipped. `makepkg --printsrcinfo` verifies recipe identities; failures are not hidden. |

Explicit additional official prerequisites include ACL support for Ansible's
unprivileged become, sudo, CA certificates, base-devel, Git, Python, Node/npm,
Rustup, cargo-binstall, uv and GTK development libraries. Pacman resolves their
transitive dependencies. Unavailable/renamed packages and conflicts fail visibly;
there is no silent dropping of packages or forced replacement of unrelated apps.
Neither official nor AUR installation performs a blanket upgrade or removal.

Builds run as `dots_user`, never root. Generated source, build and package output
live in a temporary workspace, not personal repositories. No personal checkout is
pulled, reset, cleaned or switched. PKGBUILDs are executable trusted source: review
those declarations before deployment, including the local T3 release checksums.
AUR availability and upstream package builds can still fail independently.

When builds are needed, a unique, root-owned bridge and a `visudo -cf`-validated
sudoers fragment permit **only** bounded pacman operations. The bridge rejects
removal, database refresh, sysupgrade, arbitrary configs/roots/hooks, unknown
flags and archives outside this run's build workspace. There is no grant for
arbitrary pacman, makepkg, a shell, or a user-writable helper. `block`/`always`
revokes the grant before removing policy and build files on success or failure.
No privilege is retained for subsequent sessions. A killed controller/power loss
cannot execute Ansible's cleanup: inspect `90-dots-software-*` fragments before
rerunning; their `/run/dots-software-policy-*` executables disappear on reboot.

## Account-owned tools

All of these run with `HOME`, executable paths, npm prefix and Rust/uv homes
resolved from `dots_home`, not the controller's account:

- npm CLIs: Pi (`@earendil-works/pi-coding-agent`), `pi-profiles`, Claude Code
  (`@anthropic-ai/claude-code`, replacing the backup's remote shell installer),
  and Codex (`@openai/codex`, whose state is preserved by the backup).
  Only absent manifests are installed in `~/.npm-global`. Existing versions are
  not upgraded, and the role does not rewrite `.npmrc`.
- Rust: initialize stable only if no toolchain is selected; retain an existing
  selection. Install missing `mdbook-katex` and `flamegraph` using cargo-binstall.
- If preserved source exists, install `layer-shell-rs` from
  `~/docs/src/layer-shell` and `astala-downloader` from
  `~/docs/src/astala-downloader/main`. The role reports absent optional sources;
  it neither invents upstreams nor claims those tools were installed.
- uv provides Python 3.14 and `~/.cache/pi-ptc/python-env` with matplotlib, NumPy,
  pandas and Pillow. Existing environments are not cleared; missing packages
  alone are installed. This replaces running every restored Pi profile's setup
  script, which would erase the same environment repeatedly.

Pi profile declarations and restored checkouts belong to the parent file-restore
component and Pi's own package manager. This role installs the CLI, **not** a
blanket `pi update --extensions` across all caches/profiles. Existing versions,
refs and dirty state remain untouched. This role does not reconcile extension caches/dependencies itself. The parent's
agents role runs Pi's supported `pi update` in explicitly selected profile
environments when the profile settings checksum lacks a successful receipt. There is no cache
mutation disguised as software restoration.

## Explicitly unmanaged / not completed by this role

- **Cider and ChatGPT desktop**: the historical restore script adds vendor repos
  (ChatGPT by executing a downloaded installer). Those are not official/AUR
  curated-list entries. This role does not execute that installer or configure
  unverified vendor repos/keys. Install via a separately reviewed vendor-supported
  declaration if desired; neither app is claimed installed here.
- **Gantry, DecentSampler and other manually distributed apps/assets**: preserved
  backup data is not proof of an installed, working binary. No guessed AppImage
  download or remote `curl | sh` replacement is used.
- **CLIProxyAPI**: the parent service/restore component owns its supported local
  updater, configuration and activation; this role does not invoke an unknown
  updater or start services.
- Sign-ins, OAuth refresh, Android SDK license acceptance, restored application
  state and runtime activation are not package-installation results.
- Navidrome, Sunshine, OpenClaw, Nix/Incus and other abandoned stacks are not
  restored. No live configuration, service enablement, firewall or account-group
  mutation belongs to this software role.

## Safety and verification

`dots_sandbox: true` (default **false**) disables **all** installation paths,
queries, downloads, temporary privilege and account tool/cache setup. The parent
runtime fixtures must set it explicitly. `--check` is also a non-mutating plan
boundary: it skips real software tasks rather than pretending missing package
executables can be exercised on a fresh host.

Focused checks (in an isolated dependency environment):

```sh
uv run --no-project --with 'ansible-core>=2.19,<2.20' \
  python roles/software/tests/test_software.py
```

The tests parse every role task file, validate curated-list resolution, syntax
check the role, execute sandbox and check-mode runs with zero changes, and probe
the bridge's supported and rejected requests without invoking pacman or sudo.
They do not prove a real AUR build, upstream downloads, privilege escalation,
package conflicts or desktop activation. Those require an authorized disposable
EndeavourOS installation, not live package changes during source implementation.
