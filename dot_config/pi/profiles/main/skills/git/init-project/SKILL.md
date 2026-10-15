---
name: init-project
description: "Use when asked to initialize a new project or bootstrap a personal repository
  with Forgejo hosting, a GitHub mirror, language initialization, tests, and worktrees."
metadata:
  type: procedure
---

# Contract

## Input Contract

- An explicit project-creation request, repository name, language/framework, and visibility.
- Authenticated `fj` access as `quinntyx` on `git.quinntyx.dev`, `gh` as `Quinntyx`, Git, and
  the selected stack's initializer and test tools. Resolve material missing choices with the user.
- Creation scope includes two hosted repositories, a server-side mirror, scaffold and test CI,
  initial commit/push on `main`, published `dev` worktree, and a current-session cwd move.
- Existing Forgejo runner capacity suitable for the selected toolchain and action runtime.

## Output Contract

- Canonical Forgejo repository and same-visibility GitHub mirror under the user's accounts.
- Server-side push mirror to `ssh://github.com/Quinntyx/<project>.git`, interval `8h0m0s`, with
  `sync_on_commit` true and verified matching remote heads.
- Ordinary clone at `~/docs/src/<project>/main`, a sibling `dev` worktree, and one local Forgejo
  `origin`. Both branches track origin and initially share the scaffold-and-CI commit.
- A real passing test suite and Forgejo Actions test workflow. Initial commit subject is exactly
  `initial commit`; both hosts default to `main`.
- Current Pi cwd becomes `~/docs/src/<project>` through supported `/move` dispatch, or the report
  gives the precise user command and marks that step pending.

# Entrypoint

## Stage 1: Resolve and preflight

1. Bind the requested project, package/module identity, stack, project kind, and visibility. Ask
   for material missing choices, then resume Stage 1. Validate the repository as one safe path
   segment and the package/module name against its stack's rules.
2. Bind `container="$HOME/docs/src/$project"`, `primary="$container/main"`, and
   `development="$container/dev"`. Require an absent container, including dangling symlinks.
   Existing content ends with a collision report; an authorized recovery proceeds at Stage 8.
3. Check `command -v` for Git, host CLIs, and stack tools. Verify host identities and runner access.
   Missing prerequisites end with a user-run setup command; otherwise continue Stage 1.
4. Read the Forgejo token in memory from `~/.local/share/forgejo-cli/keys.json`, at
   `hosts["git.quinntyx.dev"].token`. Use API base `https://git.quinntyx.dev/api/v1` and an
   `Authorization: token ...` HTTP header. Keep credentials in memory and redacted from output.
5. Query `GET /repos/quinntyx/{project}` and
   `gh repo view "Quinntyx/$project" --json nameWithOwner,isPrivate,defaultBranchRef`.
   Two definite not-found responses permit step 6. An existing repo requires a recovery decision
   at Stage 8; an access or network failure ends with a prerequisite report.
6. Verify an actual eligible Forgejo Actions runner label, action runtime, and toolchain support.
   Establish whether this Pi instance exposes a supported `/move` dispatcher. Retain a user-command
   handoff when dispatch is unavailable. Proceed to Stage 2: Create hosting.

## Stage 2: Create hosting

1. Create the empty forge repository using `POST /user/repos` with `name`, chosen `private`
   Boolean, `auto_init: false`, and `default_branch: main`.
2. Create the empty GitHub repository with `gh repo create "Quinntyx/$project"` and the selected
   `--public` or `--private` flag. Re-read both repositories and verify ownership, visibility,
   and emptiness. Each successful write continues here; a failed write ends at Stage 8: Recovery.
3. Read `GET /repos/quinntyx/{project}/push_mirrors` and require an unambiguous destination.
   Create the server-side mirror with `POST /repos/quinntyx/{project}/push_mirrors`, using
   `remote_address: ssh://github.com/Quinntyx/{project}.git`, `interval: 8h0m0s`, and
   `sync_on_commit: true`. Use the forge server's established GitHub credentials.
4. Enable Actions with `PATCH /repos/quinntyx/{project}` and `enable_actions: true`, then verify.
   Consult the installed OpenAPI schema or repository settings UI if its API differs. Success
   proceeds to Stage 3: Initialize the clone; an incomplete write proceeds to Stage 8: Recovery.

## Stage 3: Initialize the clone

1. Create the container and run
   `fj repo clone "quinntyx/$project" "$primary" -H https://git.quinntyx.dev -S false`.
   Verify an ordinary `.git`, an empty clone with unborn HEAD, and only canonical Forgejo `origin`.
   Success continues here; a collision, populated clone, or failed clone proceeds to Stage 8.
2. Set the proven unborn HEAD with `git -C "$primary" symbolic-ref HEAD refs/heads/main`.
3. Retrieve the selected stack's official initializer and testing instructions. Execute its
   initializer in `primary`, explicitly supplying package/module identity and disabling nested Git
   initialization where supported. The scaffold lives directly in `main`, retaining the clone Git.
4. Add stack-appropriate ignore rules, reproducibility files, a pinned toolchain where appropriate,
   and at least one real behavioral test. Keep credentials, environments, dependencies, and build
   outputs outside tracked content. Proceed to Stage 4: Configure and run tests.

## Stage 4: Configure and run tests

1. Create `.forgejo/workflows/test.yml` for pushes and ordinary `pull_request` events on `main`
   and `dev`. Select the verified runner label and the same test command used locally.
2. Use explicit absolute action URLs pinned to reviewed immutable commits. Match action runtimes
   to the runner and disable persisted checkout credentials. Provision the selected toolchain,
   install dependencies reproducibly, and run actual discovered tests with failure propagation.
3. Validate YAML using a parser that preserves `on` as a key. Check runner label, event filters,
   dependency lock handling, and action compatibility. Keep workflow scope to requested testing.
4. Run the stack's real dependency installation and test commands locally. Require discovered
   tests and successful results. Failures return to Stage 3 for scaffold repairs or Stage 4 for
   workflow repairs; successful tests proceed to Stage 5: Publish main.

## Stage 5: Publish main

1. Review all intended source, tests, workflow, ignores, and lockfiles. Stage only the scaffold
   content; inspect the staged diff and run `git -C "$primary" diff --cached --check`.
2. Run `git -C "$primary" commit -m "initial commit"`, then
   `git -C "$primary" push -u origin main`. Success continues here; failure proceeds to Stage 8.
3. Record `initial_sha`, exactly one commit, the exact subject, clean status, and `origin/main`.
   Set the forge default branch to `main` if needed using `PATCH /repos/quinntyx/{project}`.
4. Inspect the Forgejo Actions test run for this exact SHA with a bounded wait. Success proceeds
   to Stage 6: Publish dev. Failed, absent, or queued tests proceed to Stage 8: Recovery, with CI
   accurately marked incomplete. A repair after publication is an additional reported commit.

## Stage 6: Publish dev

1. Verify initialized `main` and `origin/main` match `initial_sha`; require absent `dev` path and
   branch. Unexpected state proceeds to Stage 8: Recovery; otherwise continue here.
2. Run `git -C "$primary" worktree add -b dev "$development" main`, then
   `git -C "$development" push -u origin dev`. Verify the same SHA, clean status, `origin/dev`,
   and stable branch-to-folder associations. A failure proceeds to Stage 8; success continues here.
3. Verify the exact `dev` push's Forgejo test run. A successful run proceeds to Stage 7: Verify and
   move; failed or incomplete CI proceeds to Stage 8: Recovery.

## Stage 7: Verify and move

1. Request `POST /repos/quinntyx/{project}/push_mirrors-sync`. Poll mirror state within a bounded
   wait for completed synchronization and empty `last_error`. Queue acceptance alone is pending.
2. Compare both remote branch SHAs on both hosts to the initialized commit. Set GitHub's default
   branch with `gh repo edit "Quinntyx/$project" --default-branch main`; re-read both hosts and
   verify default branches, visibility, mirror options, remotes, paths, and tracking.
3. Verified hosting proceeds at step 4. A mismatch or timeout proceeds to Stage 8: Recovery.
4. Dispatch `/move <absolute-container-path>` through a supported current-instance command API.
   A successful dispatch continues at step 5. An unavailable or canceled dispatch ends with the
   exact command for the user and a pending cwd result. This is a session move preserving history;
   `session_move` provides diagnostics, and shell `cd` changes only its subprocess.
5. Verify active Pi cwd from fresh runtime context. A matching container completes the procedure;
   otherwise report the pending `/move` handoff. Report URLs, paths, commit, tracking, local tests,
   hosted CI, mirror timestamp/errors, and cwd result concisely.

## Stage 8: Recovery

1. Record the first failed stage and retained repositories, mirror, commits, worktrees, CI, and
   session state. Preserve partial state and finish with the incomplete outcome.
2. An explicit resume request starts here: re-read ownership, visibility, commits, origin, paths,
   mirror destination, and CI. A matching retained state resumes its named incomplete stage;
   conflicting state ends with the exact decision required from the user.

# Execution conventions

- Use concrete, quoted identifiers in commands and resolved paths in HTTP routes and JSON fields.
- Keep long operations in dedicated detached tmux windows, with retained native output and exit
  status, bounded monitoring, and active user panes preserved.
- Match stack tooling to the selected framework: standard initializer, declared test dependencies,
  reproducible install, real test discovery, and a common local/CI test command.
- Required external tools and runner provisioning are user prerequisites. Existing repositories,
  histories, active worktrees, global settings, and server credentials remain intact on failure.
