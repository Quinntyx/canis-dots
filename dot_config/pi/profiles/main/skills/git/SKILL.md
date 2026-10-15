---
name: git
description: "Use when locating, cloning, forking, initializing, or mirroring repositories,
  using branches or worktrees, committing, pushing, or drafting, filing, updating, or responding
  to pull requests and public issues."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A repository identifier, URL, checkout, or current repository context and requested operation.
- Git and authenticated host access: `fj` for `git.quinntyx.dev`, `gh` for GitHub.
- Authorization appropriate to the requested side effects, as defined in Publication policy.

## Output Contract

- A verified repository destination, checkout, branch/base, tracking, and requested result.
- Personal repositories prefer Forgejo and use `~/docs/src/<repo>/main` as an ordinary clone.
- Concurrent writers use separate sibling worktrees whose directory names equal their branches.
- A concise report of completed outcomes and any incomplete publication or verification.

# Entrypoint

## Stage 1: Route the request

1. Resolve the repository, operation, host instruction, and publication scope from the request.
   Bind command variables to actual values and quote paths and identifiers before execution.
2. Match specialized requests to the child below, read that file relative to this skill's
   directory, execute its complete procedure, and return its outcome. This is mandatory dispatch:
   children are read-through procedures rather than separately advertised commands. Basic Git
   requests continue Stage 1 at step 3 without loading a child.
   - New project initialization: `init-project/SKILL.md`.
   - Server-side GitHub mirrors, mirror repairs, or Forgejo migration: `github-mirror/SKILL.md`.
   - Drafting, publishing, revising, or responding to pull requests: `pr/SKILL.md`.
   - Creating, drafting, updating, or responding to public issues: `public-issues/SKILL.md`.
3. For `~/.local/share/chezmoi`, retain the existing `main` checkout and source-state layout.
   Verify `main`; an unexpected branch ends with a report, preserving the checkout. Edit source
   state, validate, then commit and push before applying when those
   actions are assigned to this agent. An explicit coordinator handoff ends at validated source
   changes. Report the completed lifecycle stages and finish here. For code repositories continue
   to Stage 2: Resolve the repository.

## Stage 2: Resolve the repository

1. For a supplied existing checkout, verify its origin identity and primary worktree, bind
   `checkout`, `target`, `primary`, and `container`, then proceed to Stage 4: Select the branch.
   Otherwise continue Stage 2 at step 2.
2. Normalize owner/repo before lookup. Bare names select `quinntyx` on Forgejo and `Quinntyx`
   on GitHub; an explicit foreign owner remains intact. Strip a trailing `.git` and validate safe
   segments. Check Git and the host CLI. Missing prerequisites end at Stage 6: Verify and report;
   available tools continue Stage 2 at step 3. Use configured transport rewrites as found.
3. Honor an explicit host/URL and verify it on that host. Otherwise query Forgejo first with
   `fj repo view "$owner/$repo" -H https://git.quinntyx.dev`. A definite absence permits a GitHub
   lookup with `gh repo view "$owner/$repo" --json nameWithOwner,url,defaultBranchRef`, after
   normalizing the user's owner for GitHub. Successful lookup continues Stage 2 at step 4.
   An access, network, or final lookup failure ends at Stage 6: Verify and report.
4. Set `container="$HOME/docs/src/$repo"` for personal repositories or forks. Direct foreign
   clones use `container="$HOME/docs/src/${owner}_$repo"`. Set `primary="$container/main"`.
   Inspect only the expected container and supplied checkout; retain all existing content.
5. Locate-only work verifies the expected checkout, binds `target="$primary"`, and proceeds to
   Stage 6: Verify and report. Clone/fork work proceeds to Stage 3: Clone or fork. Existing
   repository work proceeds to Stage 4: Select the branch. A missing or conflicting anchor ends
   at Stage 6: Verify and report with the required destination decision, preserving existing files.

## Stage 3: Clone or fork

1. Verify the destination is absent or an existing clone of exactly the selected repository.
   Reuse a matching clone at Stage 4: Select the branch. Report collisions before proceeding.
2. An explicit fork request creates a fork on the selected contribution host. Use
   `gh repo fork "$owner/$repo" --clone=false` for GitHub, or
   `fj repo fork "$owner/$repo" -H https://git.quinntyx.dev` for Forgejo. Save the foreign
   repository URL, verify the personal fork, and select it as `origin`. An ordinary clone request
   retains the selected repository. Both paths continue at step 3.
3. Create the container, then clone with the selected CLI:
   `fj repo clone "$owner/$repo" "$primary" -H https://git.quinntyx.dev -S false` or
   `gh repo clone "https://github.com/$owner/$repo" "$primary" --no-upstream`.
   A successful clone continues at step 4. A failure ends with the retained partial path and error.
4. For a genuine foreign fork, add its original repository as `upstream` when absent. Preserve and
   report a conflicting remote for resolution. For personal Forgejo repositories with GitHub
   mirrors, retain a single Forgejo `origin`; server-side mirrors handle GitHub publication.
5. Verify the ordinary clone's `.git`, identity, and branch. Proceed to Stage 4: Select the branch.
   Hosting migration, mirror creation, and visibility changes remain separate requested operations.

## Stage 4: Select the branch

1. Verify an ordinary primary clone at `main` and sibling layout before creating worktrees.
   A missing/noncanonical anchor ends at Stage 6: Verify and report for a destination decision;
   a valid anchor continues Stage 4 here. Set `target` to the supplied task checkout or `primary`.
   Inspect `git -C "$primary" remote -v`, `git -C "$primary" status --short --branch`, and
   `git -C "$primary" worktree list --porcelain`. Preserve existing edits and branch associations.
2. Locate/list-only requests proceed to Stage 6: Verify and report. Other requests continue
   Stage 4 here. Check the actual task checkout's branch; use the primary when none was supplied.
   For feature edits on `main`, ask whether to use `dev` and wait, unless work on `main` was
   explicitly requested. An accepted `dev` destination proceeds to Stage 5: Attach the worktree;
   an authorized current checkout proceeds to Stage 6: Verify and report.
3. Newly named feature branches use `feat-<dash-delimited-description>` and default to base `dev`.
   Their future PR target also defaults to `dev`; each override is independent. Preserve names
   and bases supplied explicitly. Missing required branches require a destination decision before
   resuming Stage 4. Report missing `main` or `dev` rather than manufacturing repository policy.
4. For non-feature branch creation, preserve the established naming convention: the portion before
   the last hyphen is the base; a name without a hyphen uses `main`. Existing branches retain their
   commits and ancestry. An explicit base takes precedence over naming conventions.
5. A requested destination branch proceeds to Stage 5: Attach the worktree. Work staying in its
   authorized checkout proceeds to Stage 6: Verify and report. Branch changes use a new sibling
   worktree or the destination's existing correctly named worktree.

## Stage 5: Attach the worktree

1. Bind `name`, `base`, and `target="$container/$name"`. Require a single safe path segment and
   a successful `git check-ref-format --branch "$name"`. Keep each writer in its own worktree.
2. Inspect registered worktrees and the target path. A correctly named worktree on the matching
   branch is reused at step 7. An absent target continues at step 3. A collision ends with a report
   for the user to resolve; existing checkouts retain their branch and folder association.
3. Run `git -C "$primary" fetch origin` and query the exact branch with
   `git -C "$primary" ls-remote --heads --exit-code origin "refs/heads/$name"`.
   Success selects the existing branch path at step 4. Exit 2 selects step 4 for an existing local
   branch or step 5 for a new branch. Other failures end with a report of incomplete lookup.
4. For a remote branch, fetch its tracking ref explicitly when needed by a restricted refspec:
   `git -C "$primary" fetch origin "refs/heads/$name:refs/remotes/origin/$name"`.
   Create an absent local branch with `git -C "$primary" branch --track "$name" "origin/$name"`.
   Preserve existing local commits; set a missing upstream to `origin/$name` only when it exists.
   Resolve a conflicting upstream with the user. Attach using
   `git -C "$primary" worktree add "$target" "$name"`, then continue at step 6.
5. Resolve the requested base from its local branch first, otherwise `origin/$base`; report local
   divergence. Creating absent `main` or `dev` requires an explicit creation request. A verified
   base permits `git -C "$primary" worktree add -b "$name" "$target" "$base_ref"`, then step 6.
   An absent base ends with a request for the intended base.
6. A local-only request continues at step 7. Otherwise publish a newly created or local-only branch
   with `git -C "$target" push -u origin "$name"`. An already published branch continues at step 7.
   A failed publication retains the worktree and ends with its incomplete tracking status.
7. Verify branch, path, and upstream. Repeat Stage 5 for remaining worktrees; otherwise proceed to
   Stage 6: Verify and report. Publish requested worktree branches before concurrent work begins.

## Stage 6: Verify and report

1. For incomplete work, report retained state and the precise unresolved prerequisite, then
   finish. Completed work continues Stage 6 at step 2.
2. Verify the selected checkout using `git -C "$target" status --short --branch`, remotes, and
   `git -C "$primary" worktree list --porcelain`. For clones set `target="$primary"`.
3. For published branches, verify the exact remote head and upstream `origin/$name`. Report absent
   tracking honestly for local-only work. Check expected `main` and `dev` locally and on origin.
4. State the host, absolute checkout, branch/base, tracking, and requested result. Use explicit tool
   working directories or `git -C` for subsequent operations; shell `cd` is process-local.

# Publication policy

- A clone or worktree request authorizes the requested branch publication, subject to local-only
  instructions. Task commits and pushes on other feature branches require task authorization.
- Existing `dev` permits requested task commits and ordinary pushes without another permission
  prompt. Explicit no-commit, no-push, or local-only instructions govern the current task.
- Merging into `main` requires explicit authorization. Work on an explicitly selected `main` keeps
  its requested scope; implementation alone is distinct from opening a pull request.
- Requested chezmoi configuration changes normally authorize source-state commits and ordinary
  pushes on `main`, followed by apply. A coordinator-owned lifecycle leaves source changes ready.
- Foreign upstream contributions use the upstream's actual host, fork workflow, contribution rules,
  and target branches. An explicit foreign repo or issue URL outranks personal-host defaults.
- Respect configured transport rewrites on restricted machines while preserving canonical hosting.
  Ordinary development pushes use the canonical writable origin, with server-side mirrors syncing
  personal Forgejo repositories to GitHub.
- Preserve unrelated edits, remote histories, and active worktrees. Destructive cleanup requires its
  own scope; approved filesystem removal uses `trash`. Keep Git configuration changes repo-local.
- Use bounded waits for remote operations. Jobs expected to exceed 10–15 seconds use dedicated
  detached tmux windows with retained native output and exit status, preserving active user panes.
