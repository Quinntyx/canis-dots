---
name: init-project
description: "Use when initializing a software project or bootstrapping a personal repository,
  including requested Forgejo hosting, GitHub mirroring, tests/CI, and T3 project registration."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Project/repository identity, stack, requested local or hosted deliverable, and relevant visibility.
- Actual stack tools and, for hosted delivery, authenticated Forgejo/GitHub access and CI capacity.
- Existing T3 project/thread context and any supplied source path; preserve partial prior work.
- Authority for each requested hosted effect. A local initialization or plan does not create two
  repositories, publish branches, relocate a thread, or start a new thread implicitly.

## Output Contract

- A working source scaffold, real discovered behavioral test, reproducibility files, and honest checks.
- A T3 project registered against the ordinary source anchor when registration is assigned.
- For hosted personal bootstrap: canonical Forgejo repository, same-visibility server-side GitHub
  mirror, accepted initial commit, published `main`/`dev` refs, and exact-revision CI/mirror receipts.
- No pre-created development worktree or Pi session relocation. T3 allocates thread/delegate
  worktrees later against the registered project and committed source baseline.

# Entrypoint

## Stage 1: Bind the project and effects

1. Resolve stack, safe one-segment name, package/module identity, source destination, local/hosted
   scope, visibility, and registration ownership. Personal anchors default to
   `~/docs/src/<project>/main`; retain an explicit or established source path.
2. Read relevant existing instructions and inspect exact destination/hosting state. A truly new
   source continues here. A matching partial setup goes to Stage 7: Resume or report. Conflicting
   content is preserved and ends there with the concrete reuse decision.
3. Use actual tool availability and official initializer/testing guidance. Missing installed software
   is a user prerequisite, not permission to install a toolchain. Resolve material missing choices
   before mutation, then continue Stage 1.
4. Hosted scope requires verified host accounts, visibility, runner labels/runtime, and mirror
   credentials suitable for private sources when applicable. Local-only work skips host checks.
   Establish safe secret handling through the configured clients, never credential arguments/logs.
5. With hosted scope go to Stage 2: Establish hosting. With local-only scope go to Stage 3:
   Initialize source. Planning-only returns the proposed lifecycle at Stage 7 without effects.

## Stage 2: Establish hosting

1. Read `../github-mirror/SKILL.md` for preservation, visibility, private-source authentication, and
   server-side mirror setup. This branch owns hosting; do not duplicate or bypass its safeguards.
2. Create/reuse the authorized empty Forgejo source and same-visibility GitHub mirror only after
   definite absence or verified compatible partial state. Canonical identity is
   `git.quinntyx.dev/quinntyx/<project>`; mirrors run server-side, not as a second local origin.
3. Establish push mirror destination `ssh://github.com/Quinntyx/<project>.git`, interval `8h0m0s`,
   and `sync_on_commit: true`. Verify actual host capabilities and existing server credentials.
   Enable Actions only within the hosted bootstrap scope.
4. Re-read hosting state after writes. An uncertain response is reconciled before retrying.
   Verified empty hosting goes to Stage 3: Initialize source; a blocker goes to Stage 7.

## Stage 3: Initialize source

1. For hosted source use `t3_project_clone` with the verified canonical URL and chosen empty anchor.
   For local-only source initialize Git at the selected empty source root on `main`. This is source
   bootstrap, not creation of a managed thread/delegate worktree. Preserve all path collisions.
2. Verify origin where applicable, empty/unborn state, and source root. Set an unborn hosted HEAD to
   `main` only after proving it is empty; never switch populated branches by assumption.
3. Run the official stack initializer in the source root, supplying actual package identity and
   avoiding nested Git. Add appropriate ignores/lockfiles/toolchain metadata and a real test through
   the requested behavior. Follow `../../agent-repo-guidance/SKILL.md` only for requested repository
   agent foundations; do not invent custom lint rules or an internal-docs tree automatically.
4. Go to Stage 4: Validate scaffold and CI.

## Stage 4: Validate scaffold and CI

1. Run actual discovered tests and the relevant format/lint/type checks. Record commands, results,
   and missing boundaries. A zero-test success is not a passing behavioral suite.
2. For hosted scope write `.forgejo/workflows/test.yml` with pushes on all working branches and
   ordinary pull requests targeting the actual integration branches. Feature-branch pushes need
   tests too; do not limit push events to `main`/`dev`.
3. Use the verified runner label, reproducible dependency installation, actual test command,
   immutable reviewed action URLs, and disabled persisted checkout credentials. Validate YAML with
   an `on`-preserving parser and check action/toolchain runtime compatibility.
4. Failed checks return to Stage 3 or this stage for scoped repair. Passing checks go to Stage 5:
   Commit and publish. A source-only/coordinator boundary instead goes to Stage 7 with a handoff.

## Stage 5: Commit and publish

1. Review/stage only owned scaffold paths, inspect the staged diff, and run `git diff --cached --check`.
   Commit the initial scaffold with `initial commit` when committing is assigned. Explicit no-commit
   scope goes to Stage 7 with source ready. Local-only work skips remote writes and goes to Stage 6.
2. For hosted bootstrap push `main` to canonical origin and verify the exact SHA's real CI result.
   Create the requested `dev` ref at that accepted SHA and publish it without allocating a worktree;
   an ordinary branch ref is not a T3 workspace. Respect explicit narrower branch policy.
3. Verify both remote heads and configured defaults. Use the mirror procedure to reconcile refs
   safely and confirm completed sync, empty error, and matching accepted SHAs on both hosts.
4. Missing/failed/pending CI or mirror completion stays explicitly pending at Stage 7. Verified
   hosted delivery goes to Stage 6: Register and hand off.

## Stage 6: Register and hand off

1. Query/reuse any existing T3 project for the verified source root. When registration is assigned,
   use `t3_project_create` with explicit `workspaceRoot` and truthful saved scripts from the scaffold.
   Do not invoke its no-workspace convenience bootstrap over an already initialized source tree.
2. Registration does not change this thread's project binding or cwd. Keep source work explicit with
   absolute tool paths or `git -C`; report a ready project rather than claiming the thread moved.
3. Same-project own-thread worktree moves belong to `t3_worktree_handoff`, after
   `t3_worktree_status`, as a final call with a continuation prompt. It cannot rebind an unrelated
   scratch thread to a new project. Do not attempt shell worktrees or Pi session-command substitutes.
4. Delegates in the bound project use `delegate_task(isolation:'worktree')`; T3 chooses their
   prepared checkout from the coordinator's committed baseline. New top-level project threads use
   `t3_thread_launch` with explicit workspace strategy only when the user requests a new thread.
   If this thread belongs elsewhere, report that boundary rather than silently launching one.
5. Go to Stage 7: Resume or report.

## Stage 7: Resume or report

1. Report source/project identity, actual branch refs, checks, and requested completed effects.
   Include CI/mirror/registration receipts only when performed; keep missing effects explicit.
2. For resumption inspect retained source, hosted state, refs, visibility, mirror, CI, and registered
   workspace before continuing the first incomplete stage. Never repeat an uncertain create blindly.
3. Preserve repositories, worktrees, running jobs, and user changes on failure. Deliver the precise
   next action; destructive cleanup or new scope requires its own authorization.

# Ownership

- Git/hosting procedures own source identity, history, branch refs, publication, and mirroring.
- T3 project setup owns registration and saved scripts against the canonical source root.
- T3 thread/delegate tools own managed worktree allocation and binding; a filesystem cwd change
  does not perform that binding. Initializing source does not allocate speculative worker worktrees.
- This agent owns scoped checks and receipts. A coordinator may retain publication/application
  ownership; initialization does not grant unrequested remote or session-management effects.
