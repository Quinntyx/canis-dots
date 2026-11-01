# Native Ansible rebuild verification

Checkpoint **f81385a**, tagged `checkpoint/ansible-before-native`, preserves the
implementation before simplification. The
current source replaces the custom plugins, manifests, recovery/enrollment and
rollback framework with built-in Ansible roles, files, templates, handlers and
optional Vault data. `.forgejo/workflows/ansible.yml` supplies the ordinary
same-repository check-then-main-deploy workflow.

## Observed proof

`PATH="$PWD/.venv/bin:$PATH" ANSIBLE_NOCOWS=1 ./scripts/check all` passed after
the final implementation and rebase fixes: **88 tests passed** (51 Python and
37 Node), plus playbook syntax checking. They include syntax/ownership checks,
agent tool checks, real Ansible fixtures, software decision fixtures and tmux
protocol tests.
`git diff --check` is also required before publication.

- Real Ansible in disposable homes proves shell deployment, idempotence, host
  filtering, Vault delivery/wrong-key failure, declared service selection and
  refusing unexpected destination symlinks for static files/templates/secrets.
- The two-host template/layout fixture exercises the public playbook for both
  enrolled hosts with all live effects disabled. It explicitly supplies a
  synthetic ordinary target identity while simulating the CI container's root
  actor facts. CI's inherited-root failure was reproduced locally before that
  fixture correction; the production playbook's root-account guard is unchanged.
  It preseeds public static bytes using a local filesystem copy and skips the bulk static-transfer block. It is
  template/layout coverage, **not** a complete live deployment or proof that every
  static file was transferred through Ansible. The separate shell fixture covers
  native static transfer; digest checks cover the reviewed static-source layout.
- Focused red-to-green regressions cover preserving personal Git branches and
  unpushed commits, retryable manager-owned build recipes/Git routing, trackable
  `.vault` files and wrapper prompting, and layout links whose runtime target is
  not installed yet without allowing an existing ordinary file to be replaced.
- The full render fixture caught a stale template source path that syntax-only
  checking had missed; the repaired template renders on both hosts.
- Rebase preservation covers the concurrently merged coursework profile: 23
  static files were copied byte-for-byte, two home-path templates translated and
  four service/timer definitions retained on the main node. A focused real
  Ansible fixture proves its public defaults, mode-0600 target-local private
  override, no secret logs, repeat convergence and destination-link refusal.
  The two-host flow confirms main-only MCP/application config and unit scoping.
- The CI run after the account-fixture correction passed through the source,
  deployment and software tests, then exposed missing `trash` during all tmux
  fixture cleanups. The same failure was reproduced with PATH restricted to the
  project virtualenv. Declaring the already-used `trash-cli` version as a pinned
  verification dependency made that identical restricted-PATH test pass, without
  weakening cleanup or installing host software.
- An isolated chezmoi `managed`/`apply` check observed zero managed files with the
  deny-all `.chezmoiignore`. This protects against the archived restore procedure
  accidentally applying this Ansible source as dotfiles. It does not validate or
  update that separate restore procedure.

The independent Opus review identified concrete issues that were fixed with
focused proof. Its final follow-up was interrupted by Claude quota; there is no
claim of independent approval of the finished revision.

## Deliberately unexercised boundaries

No active configuration, real host packages, sudo/SSH deployment, preserved disk,
network identity, live service/container activation, provider sign-in, runner
registration, website publication or visual behavior was changed or tested.
Software substitutes prove decisions, not successful real installations.

No repository deployment secrets were provisioned and no privileged Forgejo job
was run. PR source checks execute in the existing runner's test container; their
results are recorded on the PR. The main-branch deployment job, SSH reachability
from its runner, concurrency support and merge-triggered production deployment
remain unverified until the owner configures the documented credentials and
performs an authorized deployment. Source validation does not grant permission
to exercise those live effects.

The PR must remain open and unmerged. Configuration rollback is a Git
revert/redeploy, not database, package, identity or personal-data recovery. See
[Deployment](DEPLOYMENT.md), [Secrets](SECRETS.md), and [Recovery](RECOVERY.md).
