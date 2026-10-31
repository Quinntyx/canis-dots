---
name: edit-config
description: "Use when creating, changing, or removing persistent configuration, dotfiles,
  rcfiles, application settings, or Pi profile files, including Ansible-managed source changes."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested configuration change, exact destination paths, inventory host/profile, and allowed effects.
- Access to the verified Ansible controller checkout and the target's actual owning manager.
- Source, commit, push, and deployment ownership: this agent, a coordinator, or a source-only handoff.
- Explicit approval for secret provisioning or new host-specific values and their destination scope.

## Output Contract

- Validated changes in authoritative source, never an incidental edit to a managed live destination.
- Assigned commits/pushes on the task branch before any separately authorized targeted deployment.
- Source-only, no-push, no-deploy, and coordinator boundaries preserved with pending effects named.
- Only owned hosts/components changed; unrelated source edits and live drift remain untouched.
- A receipt distinguishing source, publication, deployment, and actual runtime/activation evidence.

# Entrypoint

## Stage 1: Establish ownership and scope

1. Read the target's relevant source, neighboring instructions, and repository operating docs. Record
   exact task paths, baseline changes, selected inventory host, active profile, and permitted effects.
   Resolve Pi's profile from runtime context/environment, not cwd or a copied profile name.
2. Locate the controller checkout from an explicitly supplied verified source or the deployment
   marker `~/.config/ansible/dots-source.json`. It records `source_root` and `inventory_hostname`.
   For local deployment, `source_root` identifies the controller checkout; for remote deployment it
   identifies a path on the controller, not necessarily a checkout on the target. Verify repository
   identity and host selection before using it. A missing/inaccessible marker is not permission to
   guess a source path or edit live files; an authorized source-only checkout needs no deployment.
3. From that checkout use `scripts/dots-source` for the exact destination, following its documented
   host-selection interface. Check the resolved source and host eligibility in
   `roles/<component>/manifest.yml` (`source`, `dest`, `mode`) and inventory variables. The resolver
   reports unmanaged targets rather than manufacturing source paths; inspect symlinks, upstream
   resource declarations, and Other managers before concluding the file is user-editable.
4. An owned Ansible target goes to Stage 2: Edit source. A package/plugin/generated/upstream target
   goes to Stage 1A. Genuinely unmanaged personal configuration goes to Stage 1B. Ambiguous ownership
   or an unavailable controller ends at Stage 5: Report with the missing evidence.

## Stage 1A: Follow the owning manager

1. Locate the editable declaration, supported override, or verified user-owned upstream repository.
   Inspect installed files for identity only. Read `../git/SKILL.md` before source setup/publication.
2. Change only that authorized source and update only the affected package through its manager when
   assigned. Upstream-owned skills stay upstream-owned: change their acquisition declaration or
   owning source, not a downloaded copy. Do not adopt package caches as personal configuration.
3. Verify the installed revision/effective configuration when installation is assigned. Otherwise
   stop at validated source. Go to Stage 5 with pending manager updates or activation named.

## Stage 1B: Decide adoption

1. Consider adoption only for authorized durable personal configuration needed on selected hosts.
   Generated outputs, package downloads, caches, sessions, databases, OAuth stores, and identities
   remain outside normal manifests. A resolver's unmanaged result alone does not establish ownership.
2. For approved adoption, inspect current live content without importing secrets/runtime state. Add
   ordinary files/templates and a narrow manifest entry with explicit destination/mode in the owning
   role, plus the intended inventory eligibility; then go to Stage 2. Do not import whole live trees.
3. Otherwise make only an explicitly authorized direct edit to genuinely unmanaged content, validate
   it, and go to Stage 5 explaining why it stays unmanaged. Unclear ownership stays blocked.

## Stage 2: Edit source

1. Edit only the resolved source in the assigned checkout. The repository uses root `ansible.cfg`,
   `inventory/hosts.yml`, `inventory/group_vars`, `inventory/host_vars`, `playbooks/site.yml`, and
   `roles/<component>/{files,templates}` with `manifest.yml` destination/mode entries. Preserve explicit
   permissions, executable bits, links, templates, and unrelated edits. Source filenames no longer
   encode destination semantics through legacy manager prefixes.
2. Reconcile relevant live drift deliberately; do not overwrite source just because a tool rewrote
   live settings. Use inventory/group/host variables for genuine host/network differences and keep
   server-only roles gated. Component selection narrows eligible hosts; it cannot grant eligibility.
3. Keep plaintext secrets out of Git, argv, logs, diffs, and artifacts. Approved provisioned secrets
   use Ansible Vault in `encrypted_files/<host>/...` under `policy/secrets.yml`; passwords stay outside
   the repository and on the controller. Secret tasks need protected parents, explicit restrictive
   modes, `no_log: true`, and `diff: false`. Runtime/auth state stays local unless separately approved.
   Mixed config/secrets that cannot be split need a decision before import. An already committed
   secret requires revocation/history-cleanup scope; encryption now does not erase old plaintext.
4. Run application syntax checks, repository changed-file checks, and `git diff --check`; inspect
   the complete owned diff. Validate relevant host variants and manifest ownership without exposing
   unrelated data. Use the repository's documented Ansible syntax/check-mode path when available;
   check mode is supplementary evidence, not proof of runtime behavior or permission to deploy.
5. For assigned commits/pushes go to Stage 3: Publish. Source-only/coordinator/no-commit work goes
   to Stage 5 with validated paths and remaining effects. Failed checks return here or end with a
   precise blocker; do not install host software to fill a missing prerequisite silently.

## Stage 3: Publish

1. Follow `../git/SKILL.md`. Verify the assigned branch/upstream, stage exact owned paths, inspect the
   staged diff, and commit only those paths. Preserve unrelated staged changes and active worktrees.
   Use the task branch; configuration work does not require switching or merging to `main`.
2. Push only when assigned, verify the accepted remote SHA, and leave unrelated dirt untouched.
   A commit-only/cherry-pick handoff ends at Stage 5. A failed/uncertain push is reconciled by reading
   the remote before retrying; deployment remains pending.
3. A verified push plus deployment authority goes to Stage 4. A source-only/no-deploy instruction
   ends at Stage 5 even after publication. Publishing source does not itself authorize application.

## Stage 4: Deploy owned scope

1. Read `scripts/deploy` usage and the selected inventory/role tasks and handlers. The wrapper uses
   `inventory/hosts.yml` and `playbooks/site.yml`; its default is the local inventory host. Prefer
   explicit `--host HOST` with `--components csv` for the task. `--all` requires fleet-wide authority;
   omitting component selection requires whole-host scope. Do not substitute broad raw playbook runs.
2. Enumerate every affected destination and side effect of those components, including shared
   templates, external downloads, services, and handlers. Component scope is not exact-file scope:
   if it would apply unrelated changes, stop for a narrower supported plan rather than claim an
   exact-file deployment. Preserve concurrent edits and unrelated live drift.
3. Preview only the authorized host/components:

   ```sh
   scripts/deploy --host "$host" --components "$components" --check --diff
   ```

   Prevent secret diffs before running it; check mode can skip unsupported tasks and may still invoke
   reads/commands. Do not run even a preview against live inventory when the assignment prohibits it.
   Review the plan before the authorized same-scope deployment without `--check`; `--diff` remains
   subject to secret policy.
4. Validate actual rendered content, modes/links, and relevant application behavior. Repeat the
   same-scope check for unexplained task-owned drift; an idempotence claim needs a real second run
   when authorized, not inference from check mode. Verify the deployment marker separately from
   application activation. Do not reconcile other hosts/components merely for global cleanliness.
5. Source removal or omission from a manifest is not automatic live deletion. Removal needs explicit
   target ownership and authorized manager cleanup/recoverable deletion. Failed owned checks return
   to Stage 2; passing checks go to Stage 5. Keep service/reload effects distinct from file writes.

## Stage 5: Report

1. Name changed source/destination paths, controller/host/components, branch/commit/push result where
   assigned, exact deployed scope, checks run, and any pending reload or fresh-session action.
2. Distinguish source-ready, published, deployed, and active. State missing access/tool evidence and
   coordinator effects explicitly. Unrelated drift matters only when it blocks the assigned scope.

# Other managers

- Package/plugin managers and Pi's Git/npm manager own installed files and fetched skill caches.
  Change supported overrides or owning source, then use the exact package's supported update path.
- Generators own their outputs: change the template/schema/settings or documented override.
- Resolve symlink/wrapper ownership before editing. An unmanaged resolver result is not a bypass.
- Manifests are allowlists, not recursive directory adoption or pruning. Runtime state is omitted;
  `policy/secrets.yml` controls permitted encrypted-secret destinations, not secret-history cleanup.
