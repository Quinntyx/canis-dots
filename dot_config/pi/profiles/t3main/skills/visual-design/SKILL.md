---
name: visual-design
description: "Use when designing, implementing, comparing, or reviewing UI, visual identity,
  responsive layouts, or autonomous screenshot-based design variants."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A product goal or existing UI, repository path, requested deliverable, and editing authority.
- Existing visual assets, design constraints, and target platform inferred from the project.
- A task-local output directory when screenshots, design files, or a comparison report are needed.
- Existing browser or application capture tools, or permission to run a local preview.
- Autonomous work is the default within an authorized design request. Interactive markup requires
  an explicit request for a user-driven review session.

## Output Contract

- A purposeful, runnable design or an evidence-backed review within the requested product scope.
- Rendered evidence for runnable work, with viewport, revision, theme, and route metadata. Reviews
  of supplied artifacts use that evidence and identify its limits.
- A comparison report or design artifacts when part of the deliverable; advice returns the
  requested critique or design direction directly.
- For variants, a reasoned recommendation and concrete features worth combining from each version.
- Preserved product identity and established visual constraints within the requested change scope.
  Autonomous completion describes validation, separately from human approval.

# Entrypoint

## Stage 1: Resolve mode and ownership

1. Read the brief, repository instructions, current UI, and existing assets. Infer missing ordinary
   details from evidence; ask only about ambiguity that changes authority or the product's purpose.
2. Identify the primary user task, target routes, viewports, and existing workflow integrations.
   Keep the requested scope and use the actual product's terminology and content.
3. If interactive annotation or a designer review session was explicitly requested, proceed to
   Stage 2: Interactive handoff. For design advice or a review of supplied artifacts, proceed to
   Stage 5 using that evidence. For authorized runnable work, proceed to Stage 3: Autonomous design.

## Stage 2: Interactive handoff

1. Preserve the brief and current artifacts. For an explicitly requested interactive design
   review, select a `design` role child (`../subagents/model-selection/SKILL.md` sets its tier)
   and exchange mock iterations through its wake turns: each iteration is a new `delegate_task`
   carrying the current artifacts' paths, the latest feedback and the approval state. Use the T3
   preview tools to render and inspect mock states yourself between rounds.
2. If the requested interactivity cannot be delegated (live annotation while you wait), report the
   missing capability and finish with the preserved brief. Otherwise finish with the review
   outcome: approved version, iteration history and remaining decisions.

## Stage 3: Autonomous design

1. Record a short design intent: audience, primary task, layout hierarchy, type scale, spacing,
   palette roles, and one purposeful visual emphasis. Derive choices from the product and brief.
2. Inventory existing design tokens, assets, rendering and interaction behavior that carry the
   product's identity. Record relevant paths and settings before editing.
3. Reuse identity-bearing implementation within the brief's change scope. Evaluate intentional
   visual changes against the existing design and captured output.
4. Match the implementation effort to the requested deliverable. Use existing framework and assets;
   build real navigation, selection, forms, focus, and state transitions for the primary task.
   Represent unavailable services with explicit local state and disclose the boundary in the report.
5. Work directly for one design. If variants or concurrent contributors are part of the task,
   give each writer an owned worktree and record its base revision and runnable command.
6. Implement hierarchy, density, keyboard access, semantic controls, visible focus, contrast,
   reduced motion, and responsive layouts. Label actions consistently with their resulting state.
7. Proceed to Stage 4: Render and exercise.

## Stage 4: Render and exercise

1. Discover already exposed browser tools with `tool_search`. Inspect their schemas before use.
   Use an existing local capture facility when available; otherwise inspect project preview and
   capture commands. Start only owned preview processes and keep existing user sessions intact.
2. If a runnable capture path exists, continue Stage 4. Otherwise record the exact missing command
   or tool and proceed to Stage 5 with visual validation marked incomplete.
3. Run the app and capture the requested page set at fixed viewport sizes and device scale. Wait
   for fonts, assets, layout, and renderer initialization. Record capture settings and revision.
4. Exercise the primary workflow, keyboard navigation, selected states, scrolling, theme switching,
   and relevant empty, loading, and failure states. Capture states that reveal layout or behavior.
5. Inspect actual images. Check edge clipping, backgrounds, nested scroll behavior, interaction
   feedback, visual identity, legibility, and console errors against the brief and baseline.
6. For fidelity work, align viewport, scale, theme, data, and animation phase before comparison.
   Produce side-by-side images and a pixel-difference image using an available image library.
   Record changed regions and alignment limits; distinguish rendering noise from layout changes.
7. If observed defects remain within the authorized scope, fix them and repeat Stage 4. Otherwise
   proceed to Stage 5: Compare and report with any remaining defects explicitly identified.

## Stage 5: Compare and report

1. Verify the requested deliverable with the relevant checks. For runnable changes, run build and
   interaction checks. Associate captures with their revision, route, theme, and viewport; artifact
   reviews and design advice use the supplied evidence and describe any unrendered proposals.
2. For runnable work or a requested comparison, write `visual-report.md` in the output directory
   with relative image links and remaining capture links. For advice or a supplied-artifact review,
   return the requested critique directly. Both paths continue at step 3.
3. For each design, describe observed workflow choices, fidelity, interaction completeness,
   accessibility, and visual tradeoffs. Tie judgments to rendered evidence and exercised behavior.
4. For multiple variants, recommend one with reasons and identify useful elements from the others.
   For one design, summarize baseline changes and remaining limits. Use observed findings rather
   than numeric self-ratings as the quality evidence.
5. Report changed paths, runnable preview command, checks, report location, and blocked validation.
   Release only owned preview resources when their useful lifetime ends.
