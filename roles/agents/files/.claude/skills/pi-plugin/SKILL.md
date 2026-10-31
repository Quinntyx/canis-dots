---
name: pi-plugin
description: "Use when creating or changing a Pi plugin, extension, or resource package,
  including source-package tests and authorized managed Git-reference installation."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested behavior, package identity, acceptance criteria, source ownership, and selected profiles.
- Actual installed Pi version/APIs and any existing repository or installed package declaration.
- Assigned source, publication, hosting, configuration, and installation effects. A source-only
  change does not publish, install, create hosted repositories, or move/start a thread implicitly.

## Output Contract

- Validated implementation in the owning source package, never patched into an installed cache.
- Relevant discovered tests, package-content checks, and actual entrypoint/startup evidence or a
  precise missing boundary. Verification follows the shared ladder, not every possible runtime.
- For authorized delivery: accepted published SHA, selected Git ref, targeted managed declaration
  and package update, installed-revision evidence, and distinct activation status.
- A concise receipt or coordinator handoff preserving pending effects and unrelated work.

# Entrypoint

## Stage 1: Bind source, runtime, and delivery

1. Resolve behavior, acceptance checks, package name, existing/new source, target profiles, and effect
   ownership. An ordinary existing-package fix skips new-project hosting/bootstrap machinery.
2. Bind the active profile from actual system context and `PI_CODING_AGENT_DIR`; keep explicit install
   destinations separate. Resolve each selected settings file's actual owner with
   `../edit-config/SKILL.md`. Read its declaration/filters without editing package caches.
3. Read the installed Pi README, `docs/extensions.md`, `docs/packages.md`, and `docs/skills.md`, following
   applicable API links in `references/api-and-sources.md`. Inspect actual installed declarations
   before promising registrations, cache locations, update behavior, or profile resolution.
4. Select verification scope using `../runtime-verification/SKILL.md`. Planning-only returns the
   lifecycle and prerequisites at Stage 7: Report without writes, installs, tests, or publication.
   Ready execution goes to Stage 2: Establish source; unresolved identity/authority goes to Stage 7.

## Stage 2: Establish source and workspace

1. Read `../git/SKILL.md`. Honor a verified supplied checkout and its branch/edits. Locate/clone an
   absent owning repository through the Git procedure/T3 project tools, not a shell-created worker
   checkout. Installed files supply identity, not an implementation destination.
2. A new package uses `../git/init-project/SKILL.md` for source bootstrap and only the assigned hosted
   delivery/registration. Personal anchors default to `~/docs/src/<name>/main`; no sibling `dev`
   worktree is mandatory. Use Package authoring below for the scaffold and real tests.
3. T3 owns managed thread/delegate worktree allocation against the bound project and committed
   baseline. Use `delegate_task(isolation:'worktree')` for appropriate same-repo writers; a brief's
   path/base does not rebind a task. Verify binding before delegation. Do not pre-create worktrees.
4. Existing branches and narrower source/coordinator scope are valid. Do not require a branch push
   merely to begin editing, or redirect an assigned source branch without a reason.
5. Ready source goes to Stage 3: Develop. A repository/project binding mismatch goes to Stage 7 with
   a source handoff; it does not authorize a new top-level thread.

## Stage 3: Develop and verify source

1. Follow repository agent guidance and relevant internal docs. Implement the owning package's actual
   registration, command/tool/event/UI boundary using installed types and existing patterns.
2. Add a durable regression where appropriate; cover relevant state/error/cancel/cleanup transitions.
   Run discovered changed-file tests/type checks and inspect `npm pack --dry-run --json` or the actual
   package-content equivalent. Reconcile manifest resources, imports, assets, and generated outputs.
3. Use `references/runtime-validation.md` for task-relevant isolated startup/entrypoint checks. Select
   the affected supported modes and real acceptance flow; do not test every mode without a trigger.
   TUI changes use the terminal skill's selected tier, not automatic forensic capture.
4. Re-run focused acceptance after fixes. Passing source checks go to Stage 4: Publish source when
   assigned; source-only/no-push/coordinator work goes to Stage 7 with validated files and checks.
   An unavailable runtime is an explicit limit, not a fabricated pass or permission to install tools.

## Stage 4: Publish source and select ref

1. Review owned diff, tests, manifest/lockfile, and CI; run the repository's required checks and
   `git diff --check`. Follow Git preservation/publication rules and `references/hosting.md` when
   hosted delivery is assigned. Stage/commit/push only owned work to the assigned branch.
2. Verify the accepted SHA and required exact-revision CI. For assigned personal mirror delivery,
   confirm completed server sync, empty error, and matching refs through the mirror procedure.
   Pending required publication/checks go to Stage 7; do not install an unpublished pretend result.
3. Resolve the existing/requested install ref. A new development delivery can use published `dev`;
   release delivery needs its actual accepted release ref. Branches advance on update; commits pin
   code, and tags require an immutability policy. Record the resolved `delivery_sha`.
4. Personal source declarations use `git:git.quinntyx.dev/quinntyx/<name>@<ref>`. Preserve genuine
   foreign origins and verified transport rewrites. Require the selected ref to serve the accepted
   source SHA. Assigned installation goes to Stage 5; otherwise go to Stage 7.

## Stage 5: Stage and apply managed installation

1. Read `../edit-config/SKILL.md`; it owns source classification, scoped commit/push, targeted apply,
   and unrelated-drift preservation. Do not adopt a generated/package-managed file as configuration.
2. Reconcile only the selected package declaration in each assigned profile's authoritative settings
   source. Preserve resource filters, other entries, and the separate excluded orchestration skill.
   Match repository identity without its ref to avoid equivalent duplicate package declarations.
3. Retire loose duplicates only within explicit migration scope after preserving their source and
   proving the intended registration remains. Credentials/caches/sessions stay outside tracked state.
4. Validate JSON and rendered settings plus relevant isolated loading of the accepted published ref.
   Coordinator-owned config goes to Stage 7; assigned complete config follows targeted publication
   and exact-file application through edit-config, then goes to Stage 6: Verify installation.

## Stage 6: Update and verify installation

1. From a neutral cwd update only the selected package in the selected profile using the inspected
   installed CLI, for example `PI_CODING_AGENT_DIR="$agent_dir" pi update "$source" --no-approve`.
   This reconciles manager-owned caches; never hand-edit or shell-pull an installed package tree.
2. Inspect profile-scoped `pi list`, actual installed HEAD/origin/ref, and resource discovery. Require
   the accepted `delivery_sha`; successful command exit alone does not establish which copy loaded.
   Verify targeted managed settings have no task-owned drift.
3. Exercise the relevant installed startup/acceptance boundary in isolated representative storage.
   Record discovery/startup/behavior separately from live-session activation. Use a supported active
   reload/restart only when available and in scope; otherwise report that a fresh session is needed.
4. T3 binding is not changed by shell `cd`. This procedure does not start a new thread.
   For requested project/thread allocation follow init-project's T3 ownership route, then report.

## Stage 7: Report

1. Lead with implemented/installed behavior and actual coverage. Name source paths/branch/SHA,
   selected profiles/ref, installed SHA, targeted application, and activation status when performed.
2. Include hosted/CI/mirror evidence only for assigned effects; distinguish proposed, source-ready,
   pushed, installed, and active. Preserve partial state and name the concrete next action.
3. Coordinator handoff lists owned files, meaningful checks, and pending publication/config/update.
   Planning-only states intended lifecycle and unresolved prerequisites without claiming execution.

# Package authoring

- A plugin is a source package even with one extension. Use `package.json`, conventional
  `extensions/`, `skills/`, `prompts/`, and `themes/`, or explicit `pi` manifest resource paths.
  Paths are package-root relative; exclude development-only resources from shipped discovery.
- TypeScript extensions default-export a factory accepting the installed `ExtensionAPI` from
  `@earendil-works/pi-coding-agent`. Register during factory load; use runtime events for initialized
  session state and optional UI. Do not guess signatures from old examples.
- Runtime imports belong in `dependencies`. Used host-provided `@earendil-works/pi-ai`,
  `@earendil-works/pi-agent-core`, `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, and
  `typebox` belong in `peerDependencies` with `"*"` ranges; local tooling belongs in devDependencies.
  Keep host packages external to production bundles and inspect compiled imports.
- Declare real build/test scripts and lock dependencies. Include generated entrypoints/assets in
  the distribution. Pi installs Git/npm dependencies; source-checkout setup remains separate and
  follows host authorization for software installation.
- Dependency resources need a shipped dependency graph and explicit paths where required. Verify
  actual settings-filter semantics: omitted means all allowed, `[]` means none, `!pattern` excludes,
  and `+path`/`-path` select exact resources in the inspected installed implementation.
- Keep tests/docs in source; private credentials, logs, runtime harnesses, and receipts stay in
  task-owned storage outside distributed package resources.
