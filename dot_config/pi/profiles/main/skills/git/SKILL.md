---
name: git
description: "Use when locating or cloning repositories, choosing git.quinntyx.dev or GitHub,
  forking repositories, creating or using Git worktrees, or publishing worktree branches."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A repository name, owner/repository identifier, URL, local path, or current repository context.
- An operation: locate, clone, fork, list worktrees, or create worktrees for assigned work.
- For new worktrees, a branch name and any explicit base; infer names from assigned tasks only when
  the intended split is clear. Ask when the repository, task split, or base is ambiguous.
- Git plus the selected host's authenticated CLI: `fj` for Forgejo and `gh` for GitHub.
- Permission to clone or create worktrees includes publishing newly created branches to `origin`.
  Honor an explicit local-only request instead; do not publish commits or change visibility
  otherwise.

## Output Contract

- Repositories live under `~/docs/src`, in a container with an ordinary primary clone at `main`.
- Additional worktrees are registered against that primary clone and live inside the same container.
- Prefer `git.quinntyx.dev`; use GitHub only when requested or the forge repository is absent.
- New worktree branches exist on `origin` and track `origin/<branch>`, unless explicitly local-only.
- Report the selected host, absolute checkout paths, branch/base, tracking, and any incomplete
  steps.
- Execute using direct `fj`, `gh`, and `git` commands. No fish function, alias, separate skill,
  helper script, or shell-global override is required to understand or execute this procedure.

# Entrypoint

## Stage 1: Select the operation

1. Bind shell variables to actual resolved values before using the commands below; quote every path
   and identifier. Do not execute unresolved placeholders. Set `src="$HOME/docs/src"`.
2. Do not turn a location-only request into a clone, or a worktree request into a forge migration.
3. Check `command -v git` and the CLI needed for the selected host. If missing, stop and report the
   prerequisite; do not install software or silently substitute unauthenticated cloning.
4. Run network operations that may exceed 10–15 seconds in a visible tmux pane. Use a distinct
   `tmux wait-for` completion channel, capture output after completion, and address panes by ID.
   Preserve the command's exit status; do not redirect progress to a file.
5. Select the requested operation:
   - Clone: proceed to Stage 2.
   - Fork: proceed to Stage 3.
   - Locate, list worktrees, or use/create worktrees: proceed to Stage 4.

## Stage 2: Resolve and clone

1. Resolve the repository identifier:
   - Bare names belong to the user's account: `quinntyx` on the forge, `Quinntyx` on GitHub.
   - Owner/repository identifiers retain the specified foreign owner. Treat `quinntyx` and
     `Quinntyx`
     as the user's own account and normalize its spelling for each host.
   - Explicit host URLs or an explicit host instruction select that host without fallback.
   - Strip a trailing `.git` from the repository name. Reject empty names, traversal, extra path
     components, and unsafe destination segments. Do not guess a foreign owner for a bare name.
   With an explicit host, continue at step 4; otherwise continue at step 2.
2. For an unqualified host, query the forge first:
   `fj repo view "$owner/$repo" -H https://git.quinntyx.dev`.
   - Repository exists: select the forge and continue at step 5.
   - Repository is definitively absent: continue at step 3.
   - Authentication, authorization, DNS, TLS, timeout, or server failure: stop and report it.
     An inaccessible or private repository is not proof that it is absent.
3. Query GitHub with `gh repo view "$owner/$repo" --json nameWithOwner,url,defaultBranchRef` after
   normalizing the user's own owner to `Quinntyx`.
   - Repository exists: select GitHub and continue at step 5.
   - Repository is absent or lookup fails: stop with the lookup results; ask for owner/host if
     needed.
4. For an explicit host, verify it using that host's lookup command above before continuing.
   - Success: continue at step 5.
   - Failure: stop; do not override the explicit host choice.
5. Set `container="$src/$repo"` for the user's repositories. For foreign owners, set
   `container="$src/${owner}_$repo"`. Set `primary="$container/main"`.
   - Container does not exist: continue at step 6.
   - Container exists: inspect `main` and its origin. If it is the requested repository, reuse it
     and proceed to Stage 6; for a fork return to Stage 3 step 4 instead. Otherwise stop and report
     the collision. Never overwrite it.
6. Run `mkdir -p "$container"`, then use the selected host's CLI:
   - Forge: `fj repo clone "$owner/$repo" "$primary" -H https://git.quinntyx.dev -S false`.
   - GitHub: `gh repo clone "https://github.com/$owner/$repo" "$primary" --no-upstream`.
   Clone failure: stop, report any partial destination, and do not retry into it automatically.
   Clone success: proceed to Stage 6; for a fork return to Stage 3 step 4 instead.

## Stage 3: Fork

1. Resolve the specified foreign repository and host using Stage 2's lookup rules, without cloning.
   Require an explicit fork request; ordinary cloning must not create a hosted repository.
   Save the original repository's clone URL as `upstream_url` before selecting the user's fork.
2. For GitHub, run `gh repo fork "$owner/$repo" --clone=false`.
   For Forgejo, run `fj repo fork "$owner/$repo" -H https://git.quinntyx.dev`.
   If either command fails, stop and report it rather than cloning an unverified fork.
3. Verify the fork under the user's own account on the selected host, then clone that fork through
   Stage 2 with an explicit host. Its container is `"$src/$repo"`, not the foreign-owner container.
4. Inspect existing remotes. If absent, add the original foreign repository with
   `git -C "$primary" remote add upstream "$upstream_url"`.
   Keep `origin` pointing to the user's fork. Never overwrite a conflicting remote without approval.
5. Proceed to Stage 6. An upstream remote is for genuine foreign forks, not the user's GitHub
   mirror.

## Stage 4: Locate the anchor

1. For a named repository, inspect only its expected containers under `~/docs/src` first:
   `"$src/$repo/main"` or `"$src/${owner}_$repo/main"`. Verify origin identity before selecting one.
   Resolve collisions or multiple candidates with the user; do not recursively scan `~/docs/src`.
2. From an existing checkout, use `git -C "$checkout" rev-parse --show-toplevel` and
   `git -C "$checkout" worktree list --porcelain`. The first `worktree` entry is the primary clone;
   do not assume the current checkout is the anchor. Set `primary` to that absolute path.
3. From a container directory, use its `main` child only after verifying it is a Git checkout.
   Set `container` to the primary clone's parent. Require the canonical `main` anchor and sibling
   layout for newly created worktrees.
   - Canonical anchor exists: continue at step 4.
   - Missing or noncanonical anchor: stop and ask before cloning, moving, or converting anything.
4. Inspect `git -C "$primary" remote -v`, `git -C "$primary" status --short --branch`, and
   `git -C "$primary" worktree list --porcelain`. Preserve existing dirty work and branch checkouts.
   - Locate or list only: report the paths or worktree list, then proceed to Stage 6.
   - Create/use worktrees: proceed to Stage 5.

## Stage 5: Create and publish worktrees

1. Choose one branch/worktree name per task. Set `name` and `target="$container/$name"`.
   Keep the name a single safe path segment; reject traversal and separators. Validate with
   `git check-ref-format --branch "$name"`. Do not invent a task split without enough context.
2. Set `base` from an explicit instruction, otherwise derive it from the name:
   - With a hyphen, everything before the LAST hyphen is the base branch.
   - Without a hyphen, the base is `main`.
   The primary directory's name `main` is not a guarantee that a branch named `main` exists.
3. Inspect the target path and local branch with
   `git -C "$primary" show-ref --verify --quiet "refs/heads/$name"`.
   - Target or local branch exists: stop creating it. Report the matching registered worktree or
     existing branch; never force checkout, reset, remove, or recreate it. Reuse a matching worktree
     only when it belongs to the requested task; then continue at step 9. Otherwise stop.
   - Neither exists: continue at step 4.
4. Refresh origin before deciding whether the remote branch exists:
   `git -C "$primary" fetch origin`. If it fails, stop; do not treat failure as branch absence.
   Query `git -C "$primary" ls-remote --heads --exit-code origin "refs/heads/$name"`.
   - Exact branch exists: continue at step 5.
   - Exit status 2, meaning no matching ref: continue at step 6.
   - Other failure: stop and report it.
5. Attach to the existing remote branch, fetching its remote-tracking ref explicitly for clones
   with restricted fetch specifications:
   `git -C "$primary" fetch origin "refs/heads/$name:refs/remotes/origin/$name"`.
   Then run `git -C "$primary" branch --track "$name" "origin/$name"` and
   `git -C "$primary" worktree add "$target" "$name"`.
   - Both succeed: continue at step 9; no new remote branch or push is necessary.
   - Failure: stop and report any local branch left behind; do not delete or force it.
6. Resolve the new branch base, checking the exact local branch before its origin counterpart:
   `git -C "$primary" show-ref --verify --quiet "refs/heads/$base"`, then
   `git -C "$primary" show-ref --verify --quiet "refs/remotes/origin/$base"`.
   Set `base_ref` to `$base` or `origin/$base`, respectively.
   - Base found: continue at step 7.
   - Base missing: stop and ask for the intended base. Do not silently use HEAD or the default
     branch.
   Preserve local-first precedence; report if the selected local base differs from origin.
7. Run `git -C "$primary" worktree add -b "$name" "$target" "$base_ref"`.
   - Success: continue at step 8.
   - Failure: stop and report partial state; do not force or delete branches or files.
8. Run `git -C "$target" push -u origin "$name"` immediately after creation.
   This creates the remote branch and sets tracking; a separate hosting-CLI branch operation is
   unnecessary. For an explicit local-only request, skip the push and continue at step 9.
   - Push succeeds: continue at step 9.
   - Push fails: retain the local worktree, report that publication/tracking is incomplete, and
     stop.
     Retry the push only after addressing the cause; never create another worktree as a workaround.
9. If more requested worktrees remain, repeat Stage 5 with distinct names and paths. Otherwise
   proceed to Stage 6. Publish all branches before dispatching work, unless explicitly local-only.
   Do not share one checkout across agents or publish intermediate implementation commits.

## Stage 6: Verify and report

1. Verify the requested result using `git -C "$primary" worktree list --porcelain` and
   `git -C "$primary" remote -v`.
2. For clone/fork, set `target="$primary"`. For each created or reused checkout, verify its path,
   checked-out branch, and tracking:
   `git -C "$target" status --short --branch` and
   `git -C "$target" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'`.
3. For a newly published branch, verify `refs/heads/$name` with `git ls-remote` against origin.
   Require `origin/$name` as upstream. Report missing tracking honestly for local-only work.
4. State which checkout subsequent work will use. Shell `cd` in one tool call does not persist
   reliably; use an explicit tool working directory, `git -C`, or `cd` within each command.
5. Finish with host, absolute paths, branch/base, and publication/tracking status. A locate-only
   request has no creation or publication requirements.

# Invariants

- `~/docs/src/<repo>/main` is a normal clone with `.git`, not a bare clone or a branchless
  container.
  Its directory remains named `main` even when the actual default branch has another name.
- Worktrees share objects, refs, remotes, and configuration with the primary clone. Never clone a
  second independent repository to create a worktree, nest worktrees inside `main`, or default to
  temporary folders, Pi's package cache, or profile-managed git directories for development repos.
- Forge-owned repositories use a single local `origin` on `git.quinntyx.dev`. GitHub push mirrors
  are server-side; never add a local `github` or mirror `upstream` remote or push to both hosts.
  GitHub-only and explicitly GitHub-selected repositories legitimately have a GitHub origin.
- Respect existing Git URL rewrites on firewall-restricted machines. Do not rewrite global Git
  configuration or mistake a rewritten GitHub transport for permission to change canonical hosting.
- Do not migrate repositories, create mirrors, change visibility, or convert existing layouts
  merely to clone or create worktrees. Those are separate operations requiring explicit requests.
- Do not auto-stash, auto-commit, reset, force-push, delete branches, or remove worktrees. Preserve
  pre-existing dirty files. For approved filesystem cleanup use `trash`, never `rm`.
