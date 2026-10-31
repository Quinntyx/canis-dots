# Repository operating rules

This is Ansible **source**, not the active home. Read README.md and
 docs/DEPLOYMENT.md before changing inventory or roles; docs/SECRETS.md for secrets;
 docs/SOFTWARE.md for packages/builds; docs/migration/README.md for migration scope.

## Boundaries

- Source work never deploys to real machines, installs host software, starts live
  services, updates active Pi profiles, or publishes the website. A PR is not
  permission to apply it. Leave PRs unmerged unless explicitly authorized.
- Use ordinary Ansible Core modules, inventory, roles and handlers. Do not add
  custom modules/plugins, automatic secret enrollment, recovery orchestration or
  a manifest engine. Explain any genuinely necessary exception before adding it.
- Role files/templates and named YAML tasks are the desired-state source.
  Package/Git/Pi managers own their outputs. Unknown files, credentials, sessions,
  personal repositories and databases remain runtime/data state. Never recursively
  adopt, chown, prune or reset them; preserve upstream-owned resource bytes.
- The existing restore procedure owns reinstall/data recovery; Ansible runs after
  it. Do not add disk formatting/mount recovery, restore a whole /etc, clone
  identities, or use this repository as personal-data backup.
- Inventory membership is explicit. Neither T3 connections nor requested tags
  authorize enrolling a host. Main-only services must not reach syssec-canis.
- Secrets are restored runtime files or standard Ansible Vault files. Never commit
  plaintext credentials, private backups or keys. Suppress secret logs/diffs.
  Forgejo deployment secrets and privileged jobs follow docs/SECRETS.md.

## Change and verification

Preserve permissions, actual account/home portability, host scoping and literal
embedded template languages. Use native stat/assert checks for unexpected
symlinks before file installation. Services restart only for affected config,
secret or binary changes; failed builds must retry. Build/package code runs as
an unprivileged account, without reusable sudo credentials. Do not grant builds
arbitrary passwordless sudo to simplify installation.

Add a focused regression first for logic/security changes. Test target-file,
host selection and Vault behavior using real Ansible in explicitly disposable
homes (`dots_sandbox=true`); disable all installs, acquisitions and services.
Never edit active home, /etc or manager caches to make a test pass.

Project-local dependencies: `uv venv .venv && uv pip install --python
.venv/bin/python -r requirements-dev.txt`. Mandatory floor:
`PATH="$PWD/.venv/bin:$PATH" ./scripts/check static` (not file-scoped).
Escalate affected surfaces with `scripts/check deployment`, `scripts/check
software`, or `scripts/check tmux`; cross-cutting changes use `scripts/check all`.
Keep the virtualenv PATH prefix. `scripts/check-packages` is a read-only query,
not an install/refresh. Run `git diff --check` and inspect changed paths for
unassigned files/secrets before handoff.

Name actual checks. Explicitly mark real installs, sudo/SSH, service activation,
provider sign-ins and visual behavior unexercised when unauthorized. Configuration
rollback via Git/redeploy is not package, database or whole-machine recovery.
