---
name: init-project
description: "Use when asked to initialize a new project or bootstrap a new repository on Forgejo."
metadata:
  type: procedure
---

# Contract

## Input Contract

- An explicit request to create a project, its repository name, and its language or framework.
- Public or private visibility, plus any required package name, project kind, and toolchain version.
  Ask only for missing choices that materially affect the resulting scaffold or exposure.
- Authenticated Forgejo access as `quinntyx` on `https://git.quinntyx.dev` and GitHub CLI access
  as `Quinntyx`. Require Git, `fj`, `gh`, and the selected language's initialization and test tools.
- A working Forgejo Actions runner compatible with the selected toolchain and workflow actions.
- Permission to create both hosted repositories, configure a server-side push mirror, initialize
  files, add test CI, commit and push `main`, publish `dev`, and move this Pi session.
- This skill's creation or revision does not itself authorize creating a project. Execute the
  procedure only for a project-initialization request.

## Output Contract

- Canonical repository: `https://git.quinntyx.dev/quinntyx/<project_name>`.
- GitHub mirror: `https://github.com/Quinntyx/<project_name>`, with identical visibility.
- Forgejo server-side push mirror to `ssh://github.com/Quinntyx/<project_name>.git`, with
  `interval` set to `8h0m0s` and `sync_on_commit` set to true.
- An ordinary primary clone at `~/docs/src/<project_name>/main`, checked out on `main`, with
  only `origin` pointing to `https://git.quinntyx.dev/quinntyx/<project_name>.git`.
- A language-appropriate scaffold, at least one passing test, and a working Forgejo Actions
  test workflow committed together on `main` with the exact commit message `initial commit`.
- A sibling Git worktree at `~/docs/src/<project_name>/dev`, checked out on `dev`, created
  from the initialized and CI-configured `main` commit. Both branches are published and track
  their matching `origin` branches. Both hosted repositories use `main` as their default branch.
- The current Pi instance's cwd becomes `~/docs/src/<project_name>`, not either checkout.
  Use a real session move; a shell subprocess's `cd` does not satisfy this requirement.
- Report repository URLs, checkout paths, initial commit, tests, CI, mirror synchronization,
  branch tracking, and verified Pi cwd. Report incomplete steps rather than claiming success.

# Entrypoint

## Stage 1: Resolve and preflight

1. Bind `project`, `package`, `language`, `visibility`, and any framework or project-kind choices
   to concrete values. Ask for missing language or visibility; never silently publish a project.
   Infer a conventional scaffold only when it does not materially change the requested project.
2. Validate `project` as one safe path segment. Reject empty values, `.` or `..`, path separators,
   traversal, control characters, leading hyphens, and names ending in `.git`. Validate `package`
   separately using the language's naming rules; do not use the directory name `main` as its name.
3. Bind `container="$HOME/docs/src/$project"`, `primary="$container/main"`, and
   `development="$container/dev"`. Quote every path and identifier in shell commands.
   Never execute unresolved angle-bracket placeholders from this document.
4. Check `command -v` for Git, hosting CLIs, and language tools. Verify Forgejo and GitHub
   identities. If a prerequisite is missing, stop and provide the needed user-run setup command;
   otherwise continue Stage 1. Do not install software or use sudo.
5. Use API base `https://git.quinntyx.dev/api/v1`. Read the Forgejo token from
   `~/.local/share/forgejo-cli/keys.json`, at `hosts["git.quinntyx.dev"].token`, into memory.
   Send it in the HTTP `Authorization: token ...` header using a programmatic HTTP client.
   Never print credentials or place them in command arguments, files, commits, or workflows.
6. Query `GET /repos/quinntyx/<project_name>` and
   `gh repo view "Quinntyx/$project" --json nameWithOwner,isPrivate,defaultBranchRef`.
   Require definite not-found responses for both. Authentication, authorization, DNS, TLS,
   timeout, and server errors are not absence. If either repository exists or lookup fails,
   stop and report it; otherwise continue Stage 1. Do not adopt or migrate an existing repository.
7. Require `container` to be absent, including dangling symlinks. If it exists, stop and report
   the collision; otherwise continue Stage 1. Do not overwrite or remove existing content.
8. Confirm Actions is available and identify an actual eligible runner label and environment
   through the forge's runner UI/API or its known runner configuration. Check compatibility
   with Git, action runtimes, toolchain installation, and dependencies. If no suitable runner
   exists, stop and report the prerequisite; otherwise continue Stage 1. Do not assume that
   a GitHub-hosted label exists on this Forgejo instance.
9. Determine whether this Pi runtime exposes a supported dispatcher for the `/move` extension
   command. Record its availability for Stage 8. Do not substitute `session_move`: that tool is
   diagnostic only. If dispatch is unavailable, retain a user-command handoff for Stage 8.
10. Run operations expected to exceed 10–15 seconds in detached, dedicated tmux job windows.
    Preserve the originating pane and native exit status; use bounded monitoring and retain output.
    Do not split the user's active pane, redirect progress to files, or silently abandon a job.
    The `tmux-jobs` skill offers optional depth for its job helper; these execution rules
    stand alone.
11. Proceed to Stage 2: Create repositories and mirror.

## Stage 2: Create repositories and mirror

1. Create the empty Forgejo repository with `POST /user/repos`. Set `name` to `project`,
   `private` to the selected visibility Boolean, `auto_init` to false, and `default_branch`
   to `main`. Do not request a server-generated README, license, or ignore file.
   If creation fails, stop and report it; otherwise continue Stage 2.
2. Create the empty GitHub repository with `gh repo create "Quinntyx/$project" --private`
   or `--public`, matching the forge visibility. Do not pass `--clone`, `--source`, `--push`,
   `--add-readme`, a license, or an ignore template. If creation fails, retain and report the
   empty forge repository; otherwise continue Stage 2. Do not delete it as rollback.
3. Re-read both repositories and verify their owners and identical visibility. Require both
   to remain empty. If either differs, stop and report it; otherwise continue Stage 2.
4. Read `GET /repos/quinntyx/<project_name>/push_mirrors` before creating a mirror. Require
   no conflicting mirror and no duplicate destination. Reuse an exact matching mirror only
   during an explicitly authorized recovery of this run; otherwise stop on unexpected state.
5. Create the mirror with `POST /repos/quinntyx/<project_name>/push_mirrors`. Set
   `remote_address` to `ssh://github.com/Quinntyx/<project_name>.git`, `interval` to
   `8h0m0s`, and `sync_on_commit` to true. Use the forge server's existing GitHub account key.
   If creation fails, stop and report partial state; otherwise continue Stage 2.
6. Enable repository Actions using `PATCH /repos/quinntyx/<project_name>` with
   `enable_actions` true, then re-read the repository to verify it. If the installed API
   differs, inspect its OpenAPI schema or use the repository Actions settings UI; never silently
   omit activation. If activation fails, stop; otherwise proceed to Stage 3: Clone and initialize.

## Stage 3: Clone and initialize

1. Run `mkdir -p "$container"`, then
   `fj repo clone "quinntyx/$project" "$primary" -H https://git.quinntyx.dev -S false`.
   If cloning fails, stop and report the partial directory; otherwise continue Stage 3.
2. Verify the clone is empty, has an ordinary `.git` directory, and has no commits or other
   remotes. Require canonical Forgejo `origin`; stop on an unexpected URL rewrite or GitHub
   transport on this initialization machine. Do not rewrite global Git configuration.
3. Set the unborn branch explicitly with
   `git -C "$primary" symbolic-ref HEAD refs/heads/main`.
   Do this only after proving HEAD is unborn. Do not switch an existing populated checkout.
4. Execute the selected initializer from Language initialization, with the working directory
   explicitly set to `primary`. Preserve the clone's `.git`; disable initializer Git creation
   where supported. Require the scaffold to live directly in `primary`, not a nested project.
5. Add the language's normal ignore rules and appropriate reproducibility files. Keep build
   outputs, dependency directories, local virtual environments, secrets, and editor state out
   of Git. Keep intended manifests, test sources, and appropriate lockfiles in Git.
6. Add at least one real test of scaffold behavior using the chosen stack's standard runner.
   Do not treat a runner that discovered zero tests or a placeholder success script as a suite.
7. Proceed to Stage 4: Configure and validate CI.

## Stage 4: Configure and validate CI

1. Create `.forgejo/workflows/test.yml` inside `primary`. Configure `push` on `main` and
   `dev`, plus `pull_request` on `main` and `dev`. Use ordinary `pull_request`, not
   `pull_request_target`. Do not create a GitHub Actions workflow for the mirror.
2. Use the verified runner label in `runs-on`. Check out the triggering commit with an explicit
   absolute action URL and a reviewed immutable action commit. Disable persisted checkout
   credentials. Match action runtime requirements to the actual runner; do not guess SHAs.
3. Provision the chosen toolchain version and install dependencies reproducibly before tests.
   Pin external setup actions to reviewed commits. Use a locked/frozen dependency install where
   the ecosystem supports it. Run the same test command locally and in CI from the repository root.
4. Match the test command and test discovery to Language initialization. Configure the workflow
   to fail on test errors. Do not mask exit codes or add deployment, releases, registry publishing,
   production credentials, or infrastructure beyond the requested test CI.
5. Validate workflow YAML with a parser that preserves the `on` key. Review its event filters,
   runner label, checkout behavior, setup, dependency install, and test steps.
6. Run the dependency installation and test command locally. If tests or validation fail, fix
   only this new scaffold and repeat Stage 4; otherwise proceed to Stage 5: Commit and publish main.

## Stage 5: Commit and publish main

1. Review `git -C "$primary" status --short` and all files intended for the initial commit.
   Confirm the scaffold, tests, ignore rules, reproducibility files, and workflow are included
   and no secrets, generated outputs, or unrequested files will be committed.
2. Stage only those reviewed files. Inspect the staged diff and run
   `git -C "$primary" diff --cached --check`.
3. Run `git -C "$primary" commit -m "initial commit"`, followed by
   `git -C "$primary" push -u origin main`. If either fails, stop and report the retained
   local state; otherwise continue Stage 5. Never bypass failed checks or force-push.
4. Record `initial_sha` with `git -C "$primary" rev-parse HEAD`. Require exactly one commit,
   a clean working tree, the exact commit subject, and upstream `origin/main`.
5. Ensure Forgejo's default branch is `main` using
   `PATCH /repos/quinntyx/<project_name>` with `default_branch` set to `main` if necessary.
6. Inspect the Forgejo Actions run for `initial_sha`, not merely the latest run. Poll within a
   bounded time budget and verify the test job completes successfully. If it fails, is absent,
   or remains queued, stop and report CI as incomplete; otherwise proceed to Stage 6:
   Create and publish dev. Any subsequent repair must be reported honestly as an additional commit.

## Stage 6: Create and publish dev

1. Require `main` and `origin/main` to equal `initial_sha` and include the scaffold and workflow.
   Require the `dev` path and branch to be absent. If state conflicts, stop and report it;
   otherwise continue Stage 6. Do not attach or reset an unrelated pre-existing branch.
2. Run `git -C "$primary" worktree add -b dev "$development" main` only now, after the
   initialized, CI-configured `main` has been committed, pushed, and tested.
3. Run `git -C "$development" push -u origin dev`. If creation or publication fails, retain
   the worktree and report the failure; otherwise continue Stage 6.
4. Require `git -C "$development" rev-parse HEAD` to equal `initial_sha`, a clean worktree,
   and upstream `origin/dev`. Verify `main` and `dev` remain checked out in their own paths.
5. Verify the Forgejo Actions test run for the `dev` push succeeds using the same bounded
   monitoring as Stage 5. If it fails or remains incomplete, stop and report that state;
   otherwise proceed to Stage 7: Verify hosting and mirror.

## Stage 7: Verify hosting and mirror

1. Trigger `POST /repos/quinntyx/<project_name>/push_mirrors-sync`. This queues work;
   HTTP success alone does not prove synchronization.
2. Poll `GET /repos/quinntyx/<project_name>/push_mirrors` within a bounded time budget.
   Require the expected destination, interval, sync-on-commit flag, a completed synchronization
   timestamp, and empty `last_error`. If synchronization fails or times out, stop and report
   the error; otherwise continue Stage 7. Do not silently repair server credentials or host keys.
3. Compare both `main` and `dev` remote SHAs against `initial_sha` on both hosts using
   `git ls-remote --heads` or authenticated host APIs. GitHub lookups are verification only;
   never add a GitHub local remote or push directly to GitHub. If refs differ, stop and report
   the mirror as incomplete; otherwise continue Stage 7.
4. Set GitHub's default branch after mirrored `main` exists:
   `gh repo edit "Quinntyx/$project" --default-branch main`. Re-read both hosts and require
   default branch `main` and identical visibility. If verification fails, stop and report it;
   otherwise continue Stage 7.
5. Check `git -C "$primary" worktree list --porcelain`, remote configuration, both checkout
   branches, upstreams, and clean status. Require one local remote, `origin`, on the forge.
   If any invariant fails, stop and report it; otherwise proceed to Stage 8: Move Pi and report.

## Stage 8: Move Pi and report

1. Finish all repository operations before switching the session. Resolve the container's
   absolute path, preserving the requested `~/docs/src/<project_name>` location.
2. Invoke `/move <absolute-container-path>` through a supported current-instance command
   dispatcher when available. Preserve session history; do not use `--launch`, `--shutdown`,
   `--diverge`, or `--force`. Do not start another Pi instance or move repository directories.
   If the move succeeds, continue at step 4; otherwise continue at step 3.
3. If no dispatcher exists or the switch is canceled, report the cwd step as pending and give
   the exact `/move` command for the user to run in this Pi instance. Do not send slash commands
   through a message socket that only injects conversation text, manipulate the session JSONL,
   inject terminal keystrokes, or claim that shell `cd` changed Pi. Stop this run after reporting
   all completed outcomes and the pending move; after the user runs it, resume at step 4.
4. Verify the active session cwd equals the container's canonical absolute path using runtime
   context or a fresh tool execution's working directory. If it differs, return to step 3;
   otherwise continue at step 5. Never infer success solely from a copied session file.
5. Report the two URLs, `main` and `dev` paths and upstreams, initial commit, local and hosted
   test results, mirror timestamp and errors, and active cwd. This completes the procedure.

# Language initialization

- These are operational mappings, not interchangeable defaults. Use the explicitly selected
  framework's initializer and test runner when it overrides the language's base tooling.
- Rust: run `cargo init --vcs none --name "$package" --bin "$primary"` for a binary or
  substitute `--lib` for a library. Add a Rust unit test; run `cargo test --locked`. Pin the
  toolchain. Generate and retain `Cargo.lock` before locked dependency resolution and validation.
- Go: resolve the module import path, then run `go mod init "$module"` in `primary`.
  Add Go source and a `_test.go` test; run `go test ./...`. Retain `go.mod` and `go.sum`
  when dependencies require it; match CI Go to the module's version.
- JavaScript: initialize the selected package manager in `primary`. For npm, run `npm init -y`,
  set the intended package name, add a real `test` script using the selected test runner, and
  generate the lockfile. Use `npm ci` then `npm test` in CI. For Node's built-in runner,
  configure the script as `node --test` and add discoverable tests.
- TypeScript: initialize the selected package manager, then install TypeScript and the chosen
  TypeScript-compatible test runner as development dependencies. Create compiler configuration,
  typed source, and a real test script. Run the locked dependency install, typecheck, and tests
  locally and in CI; do not assume Node can execute the chosen TypeScript syntax unaided.
- Python: use the requested packaging tool. With uv, run
  `uv init --vcs none --name "$package" "$primary"`, add pytest as a development dependency,
  and generate `uv.lock`. Run
  `uv sync --locked` and `uv run --locked pytest`. With another tool, declare the same testing
  dependencies and use its reproducible install. Keep virtual environments untracked.
- Java or Kotlin: use the selected Gradle or Maven project generator in the clone root,
  with explicit package/project identity and a compatible JDK. Commit the wrapper and a real
  test. Run `./gradlew test` or `./mvnw test` locally and in CI; enable zero-test failure.
- C#: use `dotnet new` with the requested project template, explicit name, and output path.
  Create a compatible test project, reference the production project, and add both to the
  solution. Restore and run `dotnet test` on the solution locally and in CI.
- C or C++: use the selected build-system generator rather than inventing a language initializer.
  For CMake, create root build configuration, source, and a registered CTest test. Run
  `cmake -S . -B build`, `cmake --build build`, and
  `ctest --test-dir build --output-on-failure --no-tests=error` locally and in CI.
- Other languages or frameworks: retrieve the official initialization, dependency, and test
  commands before writing the scaffold. If the stack remains ambiguous, stop and ask; otherwise
  execute its established initializer and a genuine test suite through Stages 3 and 4.

# Recovery constraints

- Stop at the first failed stage. Report exactly which hosted repositories, mirror, commit,
  branches, worktrees, CI runs, and session state already exist. Preserve all partial state.
- A retry requires explicit permission to resume this run. Verify repository ownership,
  visibility, emptiness or expected commits, mirror destination, origin identity, and paths
  before reusing anything. Resume only the incomplete stage; never replay creation blindly.
- No force-push, reset, automatic stash, branch deletion, worktree removal, repository deletion,
  visibility changes, or global Git configuration changes. Use `trash` only for authorized cleanup.
- Essential behavior is specified here. The `git` and `github-mirror` skills provide optional
  depth for distinct Git and server-repair concerns; loading them is not required for this
  procedure.
