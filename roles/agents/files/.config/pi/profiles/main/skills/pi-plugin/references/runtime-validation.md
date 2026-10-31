# Isolated discovery and runtime validation

Execute this procedure during Stages 4, 7, and 9 in SKILL.md. Keep task harnesses and captured
terminal evidence in private task artifacts, separate from shipped resources and active sessions.

## Stage A: Prepare representative storage

1. Create an isolated `run_dir`, neutral `cwd`, and `isolated_agent` under task artifacts. Record
   Pi version, target profile, source/ref/SHA, selected runtime modes, and acceptance criteria.
   Use a separate directory for each profile and revision; keep user panes and sessions intact.
2. Populate isolated settings from the intended profile's desired rendered settings before apply,
   or its final managed settings after apply. Carry relevant packages, filters, theme, and plugin
   options. Rebase relative resources to their original absolute locations or isolated copies.
   Preserve selected parent/worker relationships using isolated peer directories when exercised.
3. Supply needed models and credentials through existing environment-backed access or a private
   runtime copy with restrictive permissions. Disable unrelated external effects in the fixture.
   Record representative differences, dependency sources, and services actually exercised.
4. For checkout validation, replace the selected plugin's package entry in the isolated fixture
   with the local `target` package path. Install its declared dependencies in that checkout using
   the repository's reproducible command. Relevant peer plugins retain their intended sources.
5. For published validation, retain the canonical `source` entry unchanged and run from `cwd`:
   `PI_CODING_AGENT_DIR="$isolated_agent" pi update "$source" --no-approve`.
   Read `pi list` under the same environment, locate the installed path, and verify its origin and
   `git -C "$installed_path" rev-parse HEAD` equal the accepted `delivery_sha`.
6. Reconcile other required fixture packages with targeted updates. The neutral cwd and explicit
   `--no-approve` keep unrelated project configuration out of this test. A project-local plugin
   deliberately selects its trusted isolated project and documents that distinction.
7. Prepared fixtures continue to Stage B: Inspect discovery. Setup failures return to the calling
   stage in SKILL.md with the exact unavailable dependency or revision.

## Stage B: Inspect discovery

1. Read the installed `dist/core/resource-loader.d.ts`, `dist/core/settings-manager.d.ts`, and
   resource-loader implementation before authoring the private harness. Import its public exports
   from the installed `@earendil-works/pi-coding-agent` package using explicit module resolution.
2. Create `SettingsManager.create(cwd, isolated_agent)` and pass it with those same directories to
   `DefaultResourceLoader`. Call `await loader.reload()`. Inspect `loader.getExtensions()` for
   loaded `extensions`, `errors`, and `warnings`, recording each resolved path and registration.
3. Assert that the intended package entrypoints loaded exactly once and expose expected tools,
   commands, flags, shortcuts, or event handlers. Attribute paths to the checkout during source
   tests and to the verified installed cache during Git-ref tests.
4. Inspect `loader.getSkills()`, `loader.getPrompts()`, and `loader.getThemes()` for the resources
   actually declared by this package. Record diagnostics and verify settings filters select the
   intended set. Resolve task-related errors and registration/resource collisions.
5. For shipped npm resources, inspect `npm pack --dry-run --json` against `files`, ignore rules,
   manifest paths, imports, generated entrypoints, and assets. When npm distribution is in scope,
   create the actual tarball outside the checkout with `npm pack --pack-destination "$run_dir"`.
   Extract it into isolated storage, install runtime dependencies with host peers external, and
   repeat discovery and startup from that extracted package.
6. Discovery success continues to Stage C: Exercise startup and behavior. A discovery failure
   returns to Stage 4: Develop or Stage 7: Stage managed installation in SKILL.md by cause.

## Stage C: Exercise startup and behavior

1. Launch the installed Pi executable from the fixture's `cwd` with terminal stdin and stdout:
   `PI_CODING_AGENT_DIR="$isolated_agent" pi --no-approve --no-session --offline --verbose`.
   Use a dedicated tmux job or owned PTY and record its handle, terminal size, and output.
   Installation is complete before this offline runtime check; package discovery remains enabled.
2. Wait for actual readiness and inspect startup diagnostics. Exercise the plugin's real command,
   tool, event, or UI entrypoint and verify its observable acceptance criteria. Startup logging,
   a successful process spawn, and package enumeration alone are distinct from working behavior.
3. Test the declared runtime modes. Terminal UI behavior runs in the interactive PTY with the
   selected theme, geometry, input, and relevant transitions. Non-UI behavior also exercises its
   applicable print, JSON, RPC, or SDK integration and checks the same behavioral contract.
4. Use the real mode's session lifecycle so `session_start`, runtime bindings, and cleanup execute.
   `DefaultResourceLoader.reload()` loads factories but is not a session-start assertion.
   An SDK harness uses the installed `createAgentSession` and lifecycle bindings; inspect its
   implementation before asserting startup. A CLI invocation provides the basic startup check.
5. Add focused source tests for lifecycle behavior, cancellation, repeated invocation, errors,
   reload, and shutdown when relevant. Verify requested integrations against their actual APIs.
   Keep test inference or remote writes within task authority and record fixtures versus services.
6. Exit the test process through its supported shutdown path. Check exit status, extension errors,
   cleanup, and remaining owned workers. Retain evidence before reusing a tmux pane.
7. Record the exact package SHA, configuration identity, mode, entrypoint, observed result, and
   evidence paths. Passing checks return to the calling stage in SKILL.md. Runtime failures
   return to Stage 4: Develop for code or Stage 7: Stage managed installation for configuration.
