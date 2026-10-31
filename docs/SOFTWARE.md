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
unprivileged become, sudo, util-linux (`setsid`), CA certificates, base-devel, Git,
Python, Node/npm, Rustup, cargo-binstall, uv and GTK development libraries. They
are installed in **their own transaction first**, so a curated-list conflict
cannot strand them before account become/build tasks; the curated batch follows.
`policy/packages.yml` also lists them for the earlier component install, and its
desktop/software groups contain only what the managed niri configuration and this
role use, not opinionated extra applications.

Unavailable/renamed packages and conflicts fail visibly; there is no silent
dropping of packages or forced replacement of unrelated apps. The one declared
exception is `software_conflict_guards`: if `jack2` is already installed,
`pipewire-jack` is **held and reported**, never swapped in by removing jack2
(pacman's `--noconfirm` would refuse that removal and abort the whole batch).
No policy group contains a JACK consumer, so a fresh install does not pull in
jack2 as the default provider before this role runs. Neither official nor AUR
installation performs a blanket upgrade or removal. AUR dependencies are
checked with `pacman -T`, which honors existing providers, and are installed with
plain pacman: ansible-core's `package` module would need community.general.

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
No privilege is retained for subsequent sessions.

Untrusted package code (makepkg, including `--printsrcinfo`/`--packagelist`, yay,
npm, cargo, uv builds and Pi package installs) runs as
`setsid --wait sh -c 'sudo -K && exec ...'`: a new session with no controlling TTY,
after discarding the account's cached sudo credentials. While the build grant is
present, its fragment also sets `Defaults:<user> timestamp_timeout=0`. Ansible's
become password therefore cannot be reused by build scripts; only the bridge's
NOPASSWD rule works. The makepkg override sets `OPTIONS+=(!debug)`, so uncurated
`-debug` split packages are neither built nor installed; the shared AUR tasks drop
a `-debug` packagelist entry for the same reason. Clearing cached credentials also
ends an interactive terminal's sudo ticket for that account. A killed controller/power loss
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
- Rust: queries run with `RUSTUP_AUTO_INSTALL=0`. Initialize stable only if no
  toolchain is selected. If a (restored) selection names a toolchain that is not
  installed, install that toolchain instead of replacing the selection. Install
  missing `mdbook-katex` and `flamegraph` with cargo-binstall's upstream metadata
  or source build only: `--disable-strategies quick-install --disable-telemetry`,
  so no third-party prebuilt mirror is substituted.
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
agents role runs `pi update --extensions` (packages only; bare `pi update` updates
Pi itself) in **every** host-eligible declared agent directory: each
`.config/pi/profiles/<name>/settings.json` in the selected manifest entries,
including subagent profiles, plus `~/.pi/agent`. A receipt records the command and
settings checksum only after success. Receipts from the former bare `pi update`
never match, and a failed directory gets no receipt, so it is retried on the next run.
Self-hosted Git commands (Pi packages, local recipe acquisition, builds) receive the
parent's `dots_git_environment` loopback rewrite. There is no cache mutation
disguised as software restoration.

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
- **Desktop session**: the desktop role starts Syncthing and the PipeWire sockets
  that packages already enabled in the lingering user manager, but never restarts,
  enables over a user's disable/mask, or switches display managers. An installed
  display manager is preserved and reported; without one, start niri from a TTY
  with `niri-session`. Portals are D-Bus activated. No Hyprland or fcitx stack is
  installed because the baseline configures neither. The legacy restore's
  `~/Documents`/`~/Downloads`/`~/Pictures` aliases moved user files, and are not
  in the baseline configuration, so they stay unmanaged.
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
python -m unittest tests/test_fresh_software.py   # project .venv on PATH
```

`tests/test_fresh_software.py` runs the real task files against **recording
mocks** for pacman, rustup, npm, cargo, uv, makepkg, yay, sudo and Pi, with become
disabled and a nonexistent become executable as a tripwire. It proves transaction
order, held conflicts, toolchain repair, untrusted-command wrapping, Git environment
propagation, AUR deptest/debug filtering and per-profile Pi receipts. It is **not**
a live installation, sudo or session test.

The tests parse every role task file, validate curated-list resolution, syntax
check the role, execute sandbox and check-mode runs with zero changes, and probe
the bridge's supported and rejected requests without invoking pacman or sudo.
They do not prove a real AUR build, upstream downloads, privilege escalation,
package conflicts or desktop activation. Those require an authorized disposable
EndeavourOS installation, not live package changes during source implementation.
