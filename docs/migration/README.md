# Migration coverage

`policy/migration.json` is the complete baseline ledger: every tracked source path
at the pre-migration revision recorded in `policy/baseline.yml` has an original
Git-blob SHA-256 (before guidance edits) and one explicit
`managed`, `reference`, `retired`, or `upstream` disposition. For managed files it
records the Ansible source, actual destination, kind, mode and component. The
allowlists, not a recursive traversal of a live home, define deployment.

## Preserved and translated

- Chezmoi `dot_`, `private_`, `executable_` and `symlink_` semantics become real
  destination names, explicit modes and declared links. Original hashes remain
  evidence even where intentional Jinja/source-guidance edits change bytes.
- Host/home-dependent Go templates become inventory/fact-driven Jinja with a
  separate delimiter where embedded shell/Go templates would otherwise collide.
  Literal Forgejo application templates are not rendered by Ansible.
- The lab retains its narrow component subset and an included SSH fragment;
  existing personal SSH config/keys are preserved. Main-only mail, desktop,
  services, workstation PKGBUILDs and network bindings cannot leak through a
  component-selection request.
- The tmux hook becomes explicit dependency acquisition/timer/reload tasks;
  helper behavior and its regression tests are retained. No private tmux server
  is created during migration verification.
- User-owned agent instructions and configuration-editing skills now resolve
  manifests/controller identity and separate publication from deployment.
  Upstream skills remain upstream-owned and package outputs stay runtime-owned.
- The backup thread's curated, actually used package declarations are consumed
  directly, rather than replaying an installed-package dump. See SOFTWARE.md one
  directory up for actively supported apps and manual/vendor distribution gaps.

## Intentionally outside desired file state

- Personal docs/media, mail and notmuch databases, Forgejo repositories/database,
  runner state, browser/provider/SSH/OAuth identities, package caches, sessions,
  task/application databases, virtual environments, and generated downloads.
- Machine-specific disks/UUIDs, installer boot/GPU configuration, root network
  enrollment and working firewall state. The system role owns only named
  supported overrides/integration; it does not replay the backup's whole `/etc`.
- Retired Sunshine, Navidrome, OpenClaw, Nix/Incus and abandoned service stacks.
  The migration does not enable or reinstall them. Existing unowned leftovers
  are not silently deleted; removal needs separate ownership and deletion scope.
- The old absolute developer workspace path `/home/henry/src/dots` is retired.
  Actual target homes come from facts; no such directory is created or deleted.
- Inactive Forgejo template backup copies are history, not competing desired
  state. Website content is a separate owning repository and CI pipeline.

`legacy/` retains old ignore/remove/external/hook policy as non-executing audit
text. The former backup/restore shell scripts under `docs/backups/` are likewise
`.legacy.txt`: they are **not runnable alternatives** to the new encrypted
preimage/import/rollback flow. Removing the old manager's remove list does not
authorize deletion of any current live path.

## Evidence and limits

Run `scripts/check` for syntax, ownership, guidance, software safety, tmux helper,
and real disposable-home Ansible boundary tests. The tests cover both hosts,
repeat convergence, check-mode nonmutation, wrong-key refusal, lab/server
isolation, symlink refusal, secret rotation, encrypted rollback, and retry after
a failed proxy build. They never apply to the active home or start live services.
`scripts/check-packages` is a separate read-only query against the controller's
existing pacman databases; it never refreshes them or installs packages.

Source readiness does not prove a full live package/AUR build, sudo crossing,
remote SSH, signed-in provider, running service health, graphical session, or
website publication. Those require a separately authorized deployment on the
actual target. No configuration was applied merely to claim this migration was
verified.
