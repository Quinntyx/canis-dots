---
name: terminal-ui
description: "Use when implementing terminal or TUI interfaces, repairing terminal rendering,
  scrolling, streaming, animation, or input behavior, or testing these interactions in a real
  terminal, including Pi TUIs."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Application/checkout, requested behavior or symptom, expected interaction, and permitted effects.
- Actual build/entrypoint/configuration and relevant repository instructions.
- Terminal-capable runtime and authority to launch an isolated instance; otherwise name that limit.

## Output Contract

- Focused implementation or diagnosis with relevant deterministic checks and real interaction.
- Evidence proportional to the selected verification tier, bound to the actual runnable source.
- A short receipt distinguishing modeled tests, observed terminal state, and unverified emulator
  appearance/protocol boundaries. Publication and cleanup stay within task ownership.

# Entrypoint

## Stage 1: Bind scope and tier

1. Read project guidance, current changes, rendering/input owners, actual entrypoint, build, and
   wrappers. Preserve user processes, state directories, terminal panes, and unrelated edits.
2. Select the objective ladder in `../runtime-verification/SKILL.md`. A bounded layout/input fix
   starts with its focused checks; state/lifecycle/resize interactions select boundary regression;
   unexplained timing/flicker, repeated repairs, or identity uncertainty selects forensic capture.
3. Record source revision plus relevant dirty changes, runnable path/build, terminal geometry, and
   minimal expected interaction. Keep credentials/runtime state out of evidence.
4. Select an existing permitted terminal test/capture route. Missing software is a user prerequisite,
   not permission to install another automation stack. Available runtime goes to Stage 2: Reproduce;
   unavailable execution goes to Stage 5: Deliver with the exact blocked boundary.

## Stage 2: Reproduce and localize

1. Use an isolated owned instance through the real application entrypoint, not only a framework
   simulator. Define observable expected cells/cursor/viewport behavior and bounded readiness.
2. Exercise the reported input at its geometry. Retain the decisive screen/cell capture or
   interaction result, command/sequence, actual loaded build, and relevant errors.
3. At Tier 2 include implicated wrap/resize/Unicode/scroll/lifecycle boundaries and one nearby
   unaffected path. Keep stream chunk order or timing only where it changes the observed behavior.
4. At Tier 3 read `references/capture.md` completely before allocating the forensic run. It owns the
   replayable trace, timed raw output, source/runnable manifest, indexed screens/events, restoration
   provenance, and checked digests. Those artifacts are not required for Tier 1/2 completion.
5. Follow input decoding, state, layout, invalidation, scheduling, and terminal writes to the first
   supported divergence. Use a focused experiment rather than inferring a cause from a screenshot.
6. An authorized repair with a supported cause goes to Stage 3: Implement. Review-only or blocked
   execution goes to Stage 5: Deliver with evidence and uncertainty.

## Stage 3: Implement

1. Read the installed framework's relevant docs/types/source. For Pi-specific changes read
   `references/pi-tui.md` and its applicable installed API references before choosing interfaces.
2. Fix the owning transition while preserving input, theme, lifecycle, and terminal cleanup behavior.
   Add a focused discovered regression check; prove failure on the faulty behavior when feasible.
3. Control clocks/events in deterministic tests for animation or streaming. A modeled backend must
   implement relevant semantics; recording emitted arguments alone does not validate them.
4. Rebuild and record the changed runnable identity, then go to Stage 4: Verify.

## Stage 4: Verify

1. Launch the repaired build and repeat the original interaction. Confirm it actually loaded the
   changed source/build. Observe completion and a subsequent redraw when stale cells are implicated.
2. Run the selected boundary checks and repository-required checks. For shrink/wrap bugs compare
   affected full rows, including expected blank remainder, not just cursor position or final width.
3. Match the claim to the evidence. tmux cells establish tmux's interpretation, not another emulator's
   font/glyph/protocol behavior. Inspect the actual target emulator when that boundary is the claim.
4. At Tier 3 complete/seal the capture reference's evidence tuple and verify its links/digests.
   At Tier 1/2 retain the concise source/build, sequence, geometry, decisive observations, checks,
   and exit/restoration result; do not escalate solely because a checksum manifest is absent.
5. Passing relevant checks goes to Stage 5: Deliver. An observed failure returns to Stage 2 for
   diagnosis; two unsuccessful repairs of the same symptom escalate under the shared ladder.

## Stage 5: Deliver

1. Lead with observed behavior or findings, causal evidence, selected coverage, checks, and remaining
   limits. Link richer artifacts only when produced; never report a missing boundary as verified.
2. Gracefully stop only the owned instance when its useful lifetime ends. Retain diagnostic output
   and any blocked run's resume identity. Verify terminal cursor/screen/input restoration relevant
   to the affected application; do not kill user panes or broad process-name matches.

# Boundary selection

- Geometry: the reported size and nearest relevant wrap/overflow thresholds; live shrink/expansion
  only where implicated. Verify the application received the resize.
- Unicode: affected wide/combining/grapheme sequences near the relevant edge; distinguish framework
  width assertions from observed emulator rendering.
- Cursor/focus: active input, location/visibility, handoff, and affected paste/keyboard/mouse protocol.
- Scroll: top/bottom, scroll-away anchor, return-to-end, redraw, and relevant normal/alternate modes.
- Stream: implicated chunk/parser boundaries, completion/cancellation/failure, and subsequent redraw.
- Animation: deterministic start/seam/handoff/completion/cancel boundaries plus real timed observation
  where continuity, flicker, or latency is claimed. Select an explicit acceptable transition rule.
- Theme: affected palette plus a contrasting supported appearance when cache/color invalidation is
  implicated; terminal default-color replies and selected application theme are different inputs.
