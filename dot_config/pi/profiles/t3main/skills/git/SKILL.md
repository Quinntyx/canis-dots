---
name: git
description: "Use when locating, cloning, forking, initializing, or mirroring repositories,
  selecting branches or worktrees, committing or pushing, or drafting, publishing, updating,
  or responding to repository issues and pull requests."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Repository identity or supplied checkout, requested operation, and authorized effects.
- Git and appropriate authenticated hosting access: Forgejo or GitHub as selected by the task.
- Current T3 project/thread binding and existing checkout ownership when worktrees are involved.

## Output Contract

- Verified repository, checkout, branch/base, tracking, and requested result.
- Personal source defaults to a canonical Forgejo origin and `~/docs/src/<repo>/main` anchor.
  A supplied matching checkout and the repository's actual default branch take precedence.
- T3 owns managed thread/delegate worktree allocation; Git owns history and authorized publication.
- A concise receipt with exact revisions and any pending operation. Unrelated work stays intact.

# Entrypoint

## Stage 1: Route and bind authority

1. Resolve operation, repository/host, existing checkout, branch/base, and effect ownership from the
   request. Bind quoted command variables to actual values; preserve explicit local-only limits.
2. Read the selected child relative to this skill, execute its procedure, and return its outcome:
   - New project initialization: `init-project/SKILL.md`.
   - Server-side GitHub mirroring, repair, or migration: `github-mirror/SKILL.md`.
   - PR drafting, publication, revision, splitting, or review responses: `pr/SKILL.md`.
   - Issue research, duplicate checks, drafting, publication, revision, or responses: `issues/SKILL.md`.
   Children are read-through routes, not independently advertised commands under Pi discovery.
3. For chezmoi configuration, keep its existing `main` checkout and use `../edit-config/SKILL.md`.
   Follow assigned source/publication/application ownership and return that receipt. Basic repository
   operations continue to Stage 2: Resolve source.

## Stage 2: Resolve source

1. A supplied checkout is checked for actual origin, branch, worktree layout, and existing changes.
   Honor a verified matching checkout rather than relocating it to fit a naming preference.
2. Otherwise normalize a safe owner/repo. Bare personal names prefer `quinntyx` on Forgejo, then
   `Quinntyx` on GitHub after a definite not-found. Honor explicit foreign owners and hosts.
   Access/network failures are not evidence of absence; end at Stage 6: Report when unresolved.
3. Inspect only expected source paths. Personal anchors default to `~/docs/src/<repo>/main`;
   direct foreign clones use `~/docs/src/<owner>_<repo>/main`. The directory name does not prove
   the checked-out branch is `main`. Preserve the actual default and established branch association.
4. Locate-only work goes to Stage 6: Report. An absent requested clone/fork goes to Stage 3:
   Establish source. Existing matching source goes to Stage 4: Select workspace and branch.

## Stage 3: Establish source

1. Verify the destination is absent or already the selected repository; preserve collisions.
   An explicit fork request may create its fork on the selected contribution host. A clone request
   alone does not authorize a fork, migration, mirror, visibility change, push, or PR.
2. Use T3 `t3_project_clone` for a new source anchor, passing the verified remote and destination.
   Do not manufacture a child checkout in the shell or in a delegate brief. Missing T3 capability
   ends with the precise blocker rather than a hidden alternate allocation route.
3. Verify origin, actual default branch, tracking, and retained content. Genuine foreign forks keep
   their original upstream; personal Forgejo repos use one canonical writable origin and server-side
   mirrors. Preserve conflicting remote definitions for an explicit decision.
4. Project registration is a separate local setup concern: use `t3_project_create` only when project
   setup is assigned. It neither binds the current thread to that project nor starts a new thread.
   Continue to Stage 4: Select workspace and branch.

## Stage 4: Select workspace and branch

1. Inspect status, exact branch/upstream, and `git worktree list --porcelain`. Check
   `t3_worktree_status` before any managed allocation; distinguish this thread's bound repository
   from another repository reached by an absolute path.
2. Retain an authorized existing task checkout. Locate/clone/commit/push work does not itself require
   creating or switching branches. Do not force a remote's default `dev` checkout onto `main`.
3. For personal feature branches, prefer `feat-<description>` based on existing `dev` unless task or
   repository policy selects otherwise. Missing policy/base is a focused decision, not permission
   to invent `main`/`dev`, change ancestry, or move another active checkout's branch.
4. For an own-thread move within its bound project, use `t3_worktree_handoff` on a new branch after
   checking eligibility, as the final call with a continuation prompt. It ends the live session;
   do not confuse it with source setup or a cwd change in a subprocess.
5. Concurrent same-repo writers use `delegate_task` with `isolation:'worktree'`; T3 allocates their
   prepared checkouts from the coordinator's committed baseline. Read `../subagents/SKILL.md` for
   delegation. A different bound project cannot be selected merely by putting its path in the brief.
6. Only a user-requested new top-level thread uses `t3_thread_launch`, with the correct project and
   explicit workspace strategy. Do not create a thread simply to bootstrap a repository.
7. If T3 cannot allocate the required workspace, report that boundary; do not fall back to shell
   worktrees or synthetic Pi session moves. With a ready workspace go to Stage 5: Execute.

## Stage 5: Execute

1. Perform only the assigned Git operation. Before a commit, inspect the complete owned diff, run
   applicable changed-file checks, and stage exact paths. Keep unrelated staged changes out.
2. Commit only when assigned under Publication policy. A coordinator/source-only handoff preserves
   validated changes without publication. A no-commit/no-push instruction overrides personal defaults.
3. Before an authorized ordinary push, verify the exact remote, destination branch, local ancestry,
   and tracking. Fetch/reconcile target movement without discarding concurrent work. Never force,
   rewrite, prune, or merge into `main` without its own explicit scope.
4. A failed/uncertain remote write is reconciled by reading the remote before retrying. Keep retained
   source, branch, and original error; do not replace the checkout to hide failure.
5. Continue to Stage 6: Report.

## Stage 6: Report

1. Verify actual checkout, branch/base, upstream, and task-owned status. For publication compare the
   exact remote head to the accepted local SHA; an installed update or PR is a separate outcome.
2. State host, absolute checkout, branch/ref, requested result, performed checks, and pending effects.
   Missing tracking is expected for local-only work. Do not demand unrelated global cleanliness.

# Publication policy

- A clone or worktree request authorizes local preparation only, not branch publication. Push only
  under an explicit delivery request or an applicable established repository convention.
- In an existing personal `dev` checkout, requested implementation normally includes owned commits
  and ordinary pushes unless local-only, no-push, or coordinator ownership narrows the task.
- Requested chezmoi configuration normally includes owned commits/pushes on `main` and targeted apply;
  `edit-config` owns the precise lifecycle and handoff exceptions.
- Source implementation is distinct from PR/issue/comment publication, merging, hosting migration,
  visibility changes, deployment, and installing into live profiles. Honor each task's actual scope.
- Preserve histories, unrelated changes, worktrees, and active user processes. Approved filesystem
  removals use recoverable `trash`; keep Git configuration changes repo-local.
- Use canonical origins with configured transport rewrites intact. Long jobs use owned retained
  execution with bounded waits and actual output/exit status; never kill by a broad name pattern.
