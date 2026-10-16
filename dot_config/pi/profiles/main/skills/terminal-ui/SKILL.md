---
name: terminal-ui
description: "Use when implementing terminal or TUI interfaces, fixing terminal rendering,
  scrolling, streaming or animation behavior, or testing those interactions in a real terminal,
  including Pi TUIs."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A terminal application, requested implementation or symptom, checkout and permitted side effects.
- The actual entrypoint, build and configuration, resolved from task and repository instructions.
- Expected visible behavior and reproduction input; derive missing checks from the request.
- A terminal-capable environment and permission to launch an isolated application instance.
- Target geometry, themes, terminal protocols and trace sources selected for the current task.

## Output Contract

- A focused implementation or diagnosis, with the original interaction exercised in the application.
- A private, task-owned evidence directory outside the repository and installed skill tree.
- A run manifest binding source/build identity, argv, environment, PTY geometry and event trace.
- Completion tuple: manifest/source identity; timed raw output; event index with screens/metadata;
  exit/restoration provenance; separate `checksums.json` and successful digest verification.
- Boundary assertions, cursor/viewport state and check results tied to that tuple.
- A report separating deterministic tests, observed terminal behavior and unverified boundaries.
- Source delivery and cleanup within task authority; publication follows its chosen policy.

# Entrypoint

## Stage 1: Bind the target and evidence

1. Open `references/capture.md` with the read tool and read it fully before allocating any run.
   Resolve it relative to this skill's root, not the checkout. Then read project instructions,
   checkout status, build commands and the rendering/input owner. Resolve the implicated process,
   including launch wrappers and loaded modules.
2. Record the repository HEAD, complete dirty patch and hashes of relevant untracked source. Record
   dependency lock hashes, runtime versions and the build command. Bind the built executable or
   loaded source paths to these inputs; capture a digest of the actual runnable artifact.
3. Allocate one private evidence directory per run using `references/capture.md`. Record its owner,
   run token, absolute checkout, application state directory and authorized external effects.
   Keep application state in a task-owned location using the application's documented controls.
4. Resolve installed `bash`, `tmux`, `script`, `scriptreplay` and a programmatic controller. Inspect
   their local help/manpages and the project's existing terminal tests. The reference uses tmux
   and util-linux syntax. Available capture tools continue to Stage 2: Define the trace. Missing
   tools continue to Stage 6: Deliver with the missing dependency and a verified user-run install
   command appropriate to the machine; installation remains a separate authorized action.

## Stage 2: Define the trace

1. Convert the request into observable assertions and a minimal ordered event trace. Specify initial
   state, input bytes or logical events, stream chunks, readiness, expected screens and exit.
   Bind random seeds and clock controls supported by the application. Set a bounded readiness wait.
2. Record columns and rows, terminal/emulator and multiplexer versions, `TERM`, `COLORTERM`, locale,
   color depth, theme identity/digest, screen mode, negotiated protocols and application options.
   Record capability replies or their absence when the behavior depends on terminal negotiation.
3. Select representative content from the failing input or a small authorized, sanitized real trace.
   Record provenance and the sanitization mapping. Retain chunk boundaries, event order, pauses and
   state transitions that affect the bug. Store only the selected trace in the private workspace.
4. Select the smallest decisive boundary set and one nearby unaffected path. Use the coverage rules
   below to choose geometry, Unicode, scroll, stream and animation states. State each expected
   invariant, comparison method and tolerance before changing the implementation. For each selected
   geometry, include completion and subsequent redraw as well as active streaming. Specify expected
   cells and blank remainder across the affected rows so stale delimiters, suffixes and wrapped
   residue fail acceptance even when streaming width and cursor position pass.
5. For a repair, continue to Stage 3: Observe and localize with the failing build. For new terminal
   functionality, continue to Stage 4: Implement with the expected journey and baseline behavior.

## Stage 3: Observe and localize

1. Launch the actual application through its documented integrated entrypoint in the owned PTY.
   Use `references/capture.md` for startup, raw recording, event injection and boundary capture.
   Run long build/controller commands in detached owned job windows with retained output and status.
   An installed tmux-jobs helper can supervise them; the capture procedure itself is standalone.
2. Execute the chosen trace. At each decisive transition retain the event index, observed geometry,
   cursor and viewport state, a screen capture and the corresponding timed ANSI output interval.
   Wait for a state/readiness signal with a deadline; record elapsed waits and timeout failures.
3. Compare the observation with the expected invariant. Follow input decoding, state update, layout,
   invalidation, render scheduling and terminal writes until the first supported divergence.
   Distinguish application scrolling, terminal scrollback, output and terminal interpretation.
4. Use a focused experiment to discriminate the causal hypothesis. Record contrary evidence and
   terminal limitations. Authorized implementation with a supported cause continues to Stage 4:
   Implement. A review-only request or unavailable execution continues to Stage 6: Deliver.

## Stage 4: Implement

1. Read the installed framework's relevant API and local source before selecting exact interfaces.
   Modify the component that owns the incorrect transition; preserve established input, theme,
   lifecycle and terminal cleanup contracts. Pi-specific depth is in `references/pi-tui.md`.
2. Add proportionate deterministic checks using the project's existing test path. Control time and
   inject events at the owning layer. Assert state, display-cell widths, focus, cursor, viewport and
   emitted operations as relevant. Verify the check is discovered and fails on the faulty behavior.
3. For animation, sample both sides of start, loop seam, state handoff, completion and cancellation.
   Derive clock points from the current duration/frame logic, including delayed or coalesced ticks.
   Compare successive cell/style states with a declared continuity rule and allowed deltas. Retain
   the expected and observed values; choose cadence and algorithm from this application.
4. Rebuild the runnable target. Record the resulting source and build identities again, including
   changed dirty files and lockfiles. Continue to Stage 5: Verify the integrated run.

## Stage 5: Verify the integrated run

1. Launch a fresh instance from the exact repaired build with a fresh evidence directory. Verify
   loaded paths/build identity in the running application; reproduce Stage 2's entrypoint and trace.
2. Capture the real PTY output and terminal state at the selected boundaries. Repeat the decisive
   path and nearby unaffected path. Exercise the selected resize, theme and lifecycle transitions
   while the affected component is active. Capture completion and redraw before application exit
   at each selected geometry; compare full affected rows, including blank cells, with Stage 2's
   expectations. Separately retain exit status and final cursor, screen and input restoration.
3. Run the deterministic regression and applicable project checks. Reconcile their results with the
   actual terminal capture. A framework simulator proves its modeled behavior; a passing simulator
   and an unobserved application run remain separate findings.
4. Inspect boundary screens and raw operations/timing, including transient erase/redraw intervals.
   For emulator-specific appearance, inspect the real target emulator and retain its screenshot or
   recording plus version/geometry. tmux cell captures establish tmux's interpretation, not glyph
   appearance or support for every protocol in another emulator.
5. Verify that source and runnable digests still match the launched identities. Complete and seal
   the run using `references/capture.md`; reopen every component of the Output Contract's completion
   tuple and verify event/frame links and checksums. Screens alone cannot establish completion.
   Changed identities return to Stage 4: Implement for a fresh build and exact-revision run.
   Otherwise, a failed invariant returns to Stage 3: Observe and localize with the new evidence.
   Otherwise, a complete tuple and passing selected checks continue to Stage 6: Deliver as verified;
   missing tuple evidence continues to Stage 6: Deliver as incomplete, naming the missing artifacts.

## Stage 6: Deliver

1. Report implemented behavior or findings, causal evidence and the evidence directory. Copy actual
   HEAD, dirty-source and runnable digests from the verified manifest; state any unobserved identity
   rather than replacing a recorded revision with a placeholder. Report the completion tuple's
   paths and verification result, actual trace, geometry/theme coverage and checks run.
2. Separate observed fixes, test-only coverage, unavailable terminal boundaries and remaining work.
   A blocked run reports the precise prerequisite and retains the trace for resumption.
3. Retain evidence and completed job output for the handoff. Finish the owned PTY after graceful
   application exit as described in the capture reference. Record any active process and resume
   identity when completion is blocked; cleanup targets only the verified task-owned resources.

# Boundary selection

- Geometry: use the reported size and the nearest relevant wrap/overflow threshold on each side.
  Include live shrink and expansion while the affected state is active; verify SIGWINCH reached it.
- Unicode: use affected wide glyphs, combining sequences and grapheme clusters at the relevant cell
  edge. Assert visible column widths and cursor placement with the framework's width model, then
  observe the target emulator where its width interpretation or glyph rendering is implicated.
- Cursor/focus: verify the intended focused input, hardware cursor location/visibility and focus
  handoffs. Include paste and negotiated keyboard/mouse sequences when they drive the defect.
- Scrolling: test the relevant top/bottom boundary, scroll-away anchor, return-to-end behavior and
  content/viewport relationship during redraw and resize. Capture normal and alternate screens when
  the affected application supports both paths; record terminal scrollback separately.
- Streaming: preserve chunk timing and partial Unicode/ANSI/parser boundaries when relevant. Check
  pending, partial, completed, cancelled and failed states, plus redraw after stream termination.
- Animation: retain deterministic boundary checks plus timed integrated output through multiple
  cycles and state handoffs. Measure suspected stalls/flicker from the actual trace. Select an
  explicit acceptable transition delta rather than equating identical frames with correctness.
- Themes: exercise the reported palette and a contrasting supported appearance where cache or color
  invalidation is implicated. Record terminal default-color replies separately from selected theme.
