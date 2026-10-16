---
name: pi-plugin
description: "Use when asked to create, build, develop, or deliver a Pi plugin,
  extension, or resource package, or change an existing Pi plugin's implementation."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested Pi behavior, acceptance criteria, package identity, and selected installation profiles.
- Active profile and installed Pi version; existing repository or installed package identity.
- Git, Node.js, npm, chezmoi, authenticated Forgejo and GitHub access, and eligible CI capacity.
- New-project visibility and material dependency choices, resolved with the user when unspecified.
- A new-plugin delivery request includes personal hosting, mirroring, source commits and pushes,
  and managed Git-reference installation. Explicit local-only limits or coordinator ownership
  select a source handoff instead of those delivery effects.
- Runtime credentials and service access only for the requested behavior and selected test modes.

## Output Contract

- Implementation, documentation, reproducible dependencies, and real tests in a source repository.
- New personal projects use `~/docs/src/<name>/main` as an ordinary clone, a sibling `dev`
  worktree, canonical `git.quinntyx.dev/quinntyx` hosting, and a server-side GitHub push mirror.
- Authorized delivery includes a pushed source revision, exact-revision CI, verified mirror,
  canonical Git-ref declarations in the selected profiles, and installed revision evidence.
- Discovery and actual startup evidence from isolated representative runtimes, plus the requested
  behavior exercised through its real entrypoint. UI behavior includes an interactive terminal run.
- A concise receipt distinguishes source, hosting, configuration, installation, and runtime results.
  Coordinator-owned delivery ends with validated source changes and an actionable handoff.

# Entrypoint

## Stage 1: Bind the delivery

1. Bind behavior, npm package identity, one-segment repository name, visibility, acceptance checks,
   and publication scope. Bind profile names and absolute agent directories from task context.
   Resolve material uncertainty with the user, then resume Stage 1: Bind the delivery.
2. Inspect `command -v pi`, the installed package version, its README, and `docs/extensions.md`,
   `docs/packages.md`, and `docs/skills.md`. Read linked API documents needed by the implementation.
   Use `references/api-and-sources.md` to locate installed-version documentation and source.
3. Read selected profiles' settings and package entries, then their chezmoi source equivalents.
   Identify project overrides, resource filters, parent/worker profile relationships, and runtime
   dependencies relevant to this plugin. Preserve the task's selected profiles as the target set.
4. Record acceptance checks, source/config ownership, external services, and delivery destinations.
   Use PTC for structured inspection and evidence processing when available. Run long operations
   in dedicated detached tmux jobs with retained native output, exit status, and bounded monitoring.
5. A ready request proceeds to Stage 2: Establish source. An unresolved prerequisite proceeds to
   Stage 10: Report with its concrete decision or required access.

## Stage 2: Establish source

1. Existing-plugin work continues at step 2. New-plugin work continues here.
   With hosting assigned here, execute the creation steps in `references/hosting.md`.
   With hosting owned elsewhere, select a coordinator-prepared empty ordinary source clone.
   Bind `name`, `primary`, `development`, and `target`; verify the clone on unborn `main`.
   Success proceeds to Stage 3: Bootstrap. An absent prepared clone or incomplete creation
   proceeds to Stage 10: Report with the required source or hosting action.
2. For an existing plugin, identify its canonical repository from the selected package source,
   package metadata, origin, and project documentation. Inspect installed files for identity only;
   implementation and tests belong in the verified development checkout.
3. Resolve the expected personal anchor at `~/docs/src/<name>/main`. Verify origin and inspect
   `git -C "$primary" status --short --branch` and
   `git -C "$primary" worktree list --porcelain`. A matching supplied checkout takes precedence.
   Clone an absent, verified personal repository using `references/hosting.md`'s clone command.
   A missing source identity or conflicting path proceeds to Stage 10: Report for a source decision.
4. Bind `target` to the authorized existing task worktree. Existing `dev` accepts requested task
   commits and ordinary pushes. For feature work on `main`, obtain a `dev` destination decision
   unless work on `main` was explicit. Preserve explicit branch/base choices and existing edits.
5. For a requested sibling worktree, bind a one-segment `branch`, validate it with
   `git check-ref-format --branch "$branch"`, and bind `target="$container/$branch"`.
   Fetch origin and verify branch/base refs. For a remote-only branch, fetch its tracking ref with
   `git -C "$primary" fetch origin "refs/heads/$branch:refs/remotes/origin/$branch"`, then run
   `git -C "$primary" branch --track "$branch" "origin/$branch"`.
   Attach an existing local branch with `git -C "$primary" worktree add "$target" "$branch"`.
   Create an authorized absent branch with
   `git -C "$primary" worktree add -b "$branch" "$target" "$base_ref"`.
   New feature names use `feat-<description>`, base `dev`; folder name equals branch name.
   Missing required bases proceed to Stage 10: Report for a branch decision; ready paths continue.
6. Bind `branch` from `git -C "$target" symbolic-ref --short HEAD`; verify base and identity.
   With branch publication assigned here, publish an unpublished branch using
   `git -C "$target" push -u origin "$branch"`.
   Set a missing upstream to the verified `origin/$branch`; resolve conflicting tracking explicitly.
   Preserve genuine foreign upstreams and configured transport rewrites. Success proceeds to
   Stage 4: Develop; uncertainty proceeds to Stage 10: Report. Hosting migrations and merges into
   `main` retain their own explicit scope.

## Stage 3: Bootstrap

1. In the new `primary` clone, build a minimal functioning package boundary for the requested
   behavior using Package authoring below. Include a real behavioral test, declared scripts,
   reproducibility files, documentation, and appropriate ignores.
2. Create `.forgejo/workflows/test.yml` for every branch push and ordinary `pull_request` events
   targeting `main` and `dev`. Use the verified runner, reproducible install, and test command.
   Pin reviewed action URLs to immutable commits and disable persisted checkout credentials.
3. Validate workflow YAML with a parser preserving the `on` key. Install dependencies and run the
   discovered tests and type checks. Passing checks continue at step 4; failures return to
   Stage 3: Bootstrap for repairs.
4. With bootstrap publication assigned here, stage owned scaffold paths and inspect the diff.
   Run `git -C "$primary" diff --cached --check`, commit with subject `initial commit`, and run
   `git -C "$primary" push -u origin main`. Verify the exact SHA's successful Forgejo test run.
   With coordinator-owned or local-only publication, bind `target="$primary"` and proceed to
   Stage 4: Develop, retaining the implementation for a handoff at Stage 5: Publish source.
5. Run `git -C "$primary" worktree add -b dev "$development" main`, then
   `git -C "$development" push -u origin dev`. Verify equal initial SHAs, upstreams, clean paths,
   and passing CI on `dev`. Bind `target="$development"`, `branch=dev`, then go to Stage 4: Develop.
   Publication or CI failures proceed to Stage 10: Report with retained bootstrap state.

## Stage 4: Develop

1. Implement the remaining requested behavior, package resources, and documentation in `target`.
   Follow Package authoring below and the inspected installed TypeScript declarations.
2. Add regression tests through the actual registration, event, command, tool, or UI boundary.
   Cover relevant state transitions, cancellation, errors, cleanup, and supported runtime modes.
   Keep deterministic logic tests alongside integration checks; use observable acceptance criteria.
3. Run the declared reproducible dependency install, type checking, and discovered test suite.
   Use the same commands in CI. Inspect `npm pack --dry-run --json` from `target` and reconcile
   declared resources, imported modules, assets, and generated outputs against the package files.
4. Execute `references/runtime-validation.md` using the source checkout in isolated storage.
   Resolve task-relevant registration conflicts and load errors. Passing behavior and startup
   checks proceed to Stage 5: Publish source; failures return to Stage 4: Develop.

## Stage 5: Publish source

1. Bind `branch` from `git -C "$target" symbolic-ref --short HEAD`. Review the complete task diff,
   tests, manifest, lockfile, resource paths, and CI. Run `git -C "$target" diff --check`.
   For assigned personal publication, run the preservation check in `references/hosting.md`.
   Stage only owned task paths and inspect the staged diff.
2. With source publication assigned here, commit the changed source and push the selected branch
   to canonical origin. A clean, already published accepted revision needs no extra commit.
   With coordinator-owned or local-only publication, proceed to Stage 10: Report with the source
   handoff. A failed push also proceeds to Stage 10: Report; successful publication continues here.
3. Bind `delivery_sha` from `git -C "$target" rev-parse HEAD`. Verify the upstream remote ref,
   clean task paths, and successful hosted tests for that exact SHA, including newly added tests.
4. Verify server-side mirroring with the synchronization steps in `references/hosting.md`.
   Record completed synchronization, empty error, and matching branch/tag refs. A verified result
   proceeds to Stage 6: Select the installed ref; incomplete CI or mirroring proceeds to
   Stage 10: Report.

## Stage 6: Select the installed ref

1. Resolve the delivery ref from the request and existing package policy. A new plugin developed
   on `dev` defaults to published `dev` unless release delivery was selected. Bind `ref` to the
   published branch, immutable tag, or commit and record its resolved `delivery_sha`.
   An explicit development delivery uses its published development ref; release delivery uses
   the authorized published release ref. A `main` install resolves to code actually on `main`.
2. Bind `source="git:git.quinntyx.dev/quinntyx/$name@$ref"` for personal canonical delivery.
   Existing foreign contribution repositories retain their actual canonical host and owner.
   Read `docs/packages.md` and the installed Git package implementation for ref reconciliation.
   A branch can advance on targeted update. A commit pins code; tags require immutability policy.
   Verify the resolved SHA for every chosen ref.
3. Verify the remote ref resolves to the accepted source SHA. Read any transport rewrites and
   verify the effective transport serves that SHA while retaining canonical source declarations.
   Exact agreement proceeds to Stage 7: Stage managed installation; a mismatch returns to
   Stage 5: Publish source with the required branch/release publication decision.

## Stage 7: Stage managed installation

1. For each selected profile, bind `agent_dir` and `settings="$agent_dir/settings.json"`.
   Run `chezmoi source-path -- "$settings"` and inspect the resolved source file and neighbors.
   For durable unmanaged profile configuration, deliberately adopt the current live file into
   source state, with correct chezmoi attributes and secret/runtime exclusions, then resume here.
2. Edit only that managed source file's package declaration. Add or reconcile the canonical
   `source`, preserving existing resource filters, unrelated entries, and other profile settings.
   Git identity is repository URL without ref, so reconcile the existing entry rather than
   introducing duplicate equivalent sources. Keep caches and credentials as runtime state.
3. Retire a superseded loose extension declaration or file only within authorized migration scope.
   Preserve its code in the source project and prove one intended registration remains. Package
   implementation now lives in the repository; the profile contains delivery configuration.
4. Validate the source JSON and targeted chezmoi rendering. Build an isolated representative
   configuration from the desired rendered settings and run `references/runtime-validation.md`
   against the published canonical Git ref. Passing checks continue at step 5; failures return
   to Stage 4: Develop for code or Stage 7: Stage managed installation for configuration.
5. Review `git -C ~/.local/share/chezmoi diff --check` and the complete owned source diff.
   Coordinator-owned configuration proceeds to Stage 10: Report with the validated source files.
   Self-owned authorized configuration proceeds to Stage 8: Apply managed installation.

## Stage 8: Apply managed installation

1. Verify the chezmoi checkout is on `main`; another branch proceeds to Stage 10: Report.
   On `main`, stage only owned changes, inspect the staged diff, commit, and push the configured
   upstream. Confirm the push and task paths are
   clean. A failed push proceeds to Stage 10: Report with apply pending; success continues here.
2. Run `chezmoi apply -- "$settings"` for each selected profile's changed settings target, and
   apply any other explicitly changed migration targets by path. Source commit and push precede
   application. Preserve unrelated source edits and live drift through this targeted application.
3. From a neutral working directory, reconcile only the selected package in each intended profile:
   `PI_CODING_AGENT_DIR="$agent_dir" pi update "$source" --no-approve`.
   The source declaration already comes from managed configuration; this updates runtime caches.
4. Run targeted `chezmoi diff -- "$settings"` and `chezmoi status -- "$settings"` for all owned
   targets. Empty output proceeds to Stage 9: Verify delivery; remaining drift returns to
   Stage 7: Stage managed installation for deliberate reconciliation and another pushed change.

## Stage 9: Verify delivery

1. Run `PI_CODING_AGENT_DIR="$agent_dir" pi list` in the neutral directory for each selected
   profile. Locate the installed path and inspect its Git HEAD, origin, and configured ref.
   Require `delivery_sha`; capture evidence separately from the development worktree.
2. Repeat `references/runtime-validation.md` with the final selected profile settings and installed
   revision represented in isolated runtime storage. Exercise the actual acceptance flow and
   verify discovery, startup handlers, shutdown, and relevant integrations in every selected mode.
3. For an affected currently running Pi instance, arrange supported `/reload` or a deliberate
   restart in that instance; a fresh isolated run is distinct evidence from active-session reload.
   Record any pending active-instance action. Passing checks continue at step 4; failures
   return to Stage 4: Develop or Stage 7: Stage managed installation according to the cause.
4. For new-project delivery, use a supported current-instance dispatcher for
   `/move <absolute-container-path>` and verify the active Pi cwd. When unavailable, give the
   exact user command and pending result at Stage 10: Report. Shell `cd` is process-local.
   A verified move or existing-project delivery proceeds directly to Stage 10: Report.

## Stage 10: Report

1. Record canonical and mirror URLs, source paths, branch/base, source SHA, installed ref, exact
   CI result, mirror completion/error, profiles, configuration diff, apply result, and cwd result.
2. Attach local tests, discovery paths, runtime entrypoint evidence, observed behavior, and retained
   isolated test artifacts. Identify partial state, first failed stage, and a concrete resume step.
3. For coordinator handoff, list changed files, dependencies, checks, and pending publication,
   managed configuration, apply, or runtime actions. Finish with coordinator effects pending.

# Package authoring

- A plugin is a source package even with one extension. Use `package.json`, conventional
  `extensions/`, `skills/`, `prompts/`, and `themes/` directories, or explicit `pi` manifest paths.
  Manifest paths are package-root relative; declare every intended shipped resource explicitly
  when conventional discovery would include development-only files.
- TypeScript extensions default-export a factory accepting `ExtensionAPI` from
  `@earendil-works/pi-coding-agent`. Use installed API types for registrations and handlers.
  Register commands, tools, and event handlers during factory loading; use runtime events for
  operations requiring initialized session state. Select optional UI behavior by runtime context.
- Runtime imports belong in `dependencies`. Host-provided `@earendil-works/pi-ai`,
  `@earendil-works/pi-agent-core`, `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, and
  `typebox` belong in `peerDependencies` with `"*"` ranges when used, with local test tooling in
  `devDependencies`. Keep host packages external to production bundles and inspect compiled imports.
- Declare build and testing scripts and lock the dependency graph. Include generated entrypoints
  and required assets in the distributed package. Pi installs dependencies for Git/npm packages;
  local-checkout dependency installation remains the author's responsibility.
- Package resources from another dependency need that dependency in the delivered graph and its
  resource paths declared through `node_modules`. Respect per-package module roots and declared
  imports. Settings filters narrow declared resources: omitted means all allowed, `[]` means none,
  `!pattern` excludes glob matches, and `+path`/`-path` select exact allowed paths.
- Keep project tests and task documentation in the source checkout. Keep private runtime harnesses,
  credentials, logs, and receipts in isolated task artifacts outside shipped package resources.
