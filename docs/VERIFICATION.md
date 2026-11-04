# Native Ansible rebuild verification

Checkpoint **f81385a**, tagged `checkpoint/ansible-before-native`, preserves the
implementation before simplification. The
current source replaces the custom plugins, manifests, recovery/enrollment and
rollback framework with built-in Ansible roles, files, templates, handlers and
optional Vault data. `.forgejo/workflows/ansible.yml` supplies the ordinary
same-repository check-then-main-deploy workflow.

## Observed proof

`PATH="$PWD/.venv/bin:$PATH" ANSIBLE_NOCOWS=1 ./scripts/check all` passed after
the native rebuild's implementation and review fixes: **89 tests passed** (52 Python and
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
  update that separate restore procedure. Its later t3assistant integration is
  covered separately below.

### t3assistant follow-up

`PATH="$PWD/.venv/bin:$PATH" ANSIBLE_NOCOWS=1 ./scripts/check static` and
`PATH="$PWD/.venv/bin:$PATH" ANSIBLE_NOCOWS=1 ./scripts/check all` passed after
this follow-up: **92 tests passed** (55 Python and 37 Node), plus syntax checks.
The owner's new configuration is restricted completely to araveia, including
profile acquisition and auth/model links. Its public coursework references were
synchronized from the verified owned source; private values remain target-local.
New regression coverage proves the main/lab boundary, the preserved timer's
restored-file prerequisites and timer selection using recording systemctl,
plus application of the tracked patch to the existing backup/restore references.
The existing home-data function restored artificial private JSON with mode 0600
using real rsync in a disposable directory. The separate on-disk scripts were
edited and syntax-checked, not executed. The focused Opus 5.5 review found no
host/timer blockers and identified a fresh-restore npm-prefix ordering gap;
that gap was fixed with an explicit user-owned prefix. The follow-up regression
also proves early detection of the owner-installed Ansible prerequisite and
exercises npm-prefix propagation without invoking sudo or npm. The dead hostname
repair branch was removed and dirty/non-main checkout refusals now explain why.
No live snapshot, SQLite backup, OAuth renewal or systemd activation was performed.

The final independent Opus 5.5 source review found no blockers on `79e1f8f`.
Its two minor findings were addressed afterwards: coursework unit definitions
are installed separately without marking unrelated desktop-service restart
inputs, and the dependency comment correctly includes the CI controller. A
focused real-Ansible regression failed before the service-input fix and passed
afterwards; changing a real desktop unit still marks its restart inputs. No
live service restart was exercised. Earlier quota interruptions did not provide
review approval; this completed review is the source-review evidence.

### Self-updating T3 Code AppImage follow-up

The complete `scripts/check all` set passed: **98 tests** (61 Python and 37
Node), plus playbook syntax checks. The six AppImage regressions first failed
before implementation. Real Ansible against a loopback-only fake feed proves
missing-file bootstrap, checksum rejection with no partial install, retry,
executable mode, preserving newer updater bytes during an offline repeat,
refusing destination/ancestor links, and no acquisition in check mode or
through the normal sandbox entrypoint. Desktop tests cover quoted homes,
idempotence and unsafe launcher destinations. The original lab exclusion was
incorrect and is superseded by the shared-workstation correction below. A final
red-to-green quoting case covers desktop string-unescaping before Exec parsing;
the entire six-test AppImage set was rerun successfully afterwards.

The actual backup script's AppImage path is represented in the tracked patch.
Real rsync restored an artificial AppImage with its bytes and executable mode
intact; the full backup/restore scripts were not run. The production asset pin
and SHA-512 come from the fork's published stable metadata, not the fake feed.
No real AppImage download, FUSE mount, desktop launch, in-app update, release-feed
service change or pacman fallback removal was performed in this task.

### Shared-workstation client and main-only coursework boundary

T3 Code now has its own shared role rather than inheriting araveia-only desktop
or curated-software gates. The focused six-test AppImage set proves bootstrap
and newer-byte preservation during offline redeploy on **both** enrolled hosts,
and installs each account's launcher and icon with real Ansible. It also checks
that the public playbook includes the client unconditionally and both hosts
declare its runtime package group. Check-mode and normal sandbox non-acquisition
are tested on both hosts. The two-host public-playbook fixture expects the client
launcher/icon on both, while retaining its existing assertions that Pi Coursework
(`t3assistant`), its configuration/MCP and timers are absent on syssec-canis.
This correction changes neither coursework activation nor inventory membership.
`PATH="$PWD/.venv/bin:$PATH" ANSIBLE_NOCOWS=1 ./scripts/check all` passed after
the correction: **98 tests** (61 Python and 37 Node), plus playbook syntax
checking. Real-host installation, SSH, FUSE/GUI launch and live activation
remain unexercised.

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
