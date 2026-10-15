---
name: visual-design
description: "Use when designing, implementing, comparing, or reviewing UI, visual identity,
  responsive layouts, shaders, or autonomous screenshot-based design variants."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A product goal or existing UI, repository path, requested deliverable, and editing authority.
- Existing visual assets, design constraints, and target platform inferred from the project.
- A distinct output directory for screenshots, design notes, and the comparison report.
- Existing browser or application capture tools, or permission to run a local preview.
- Autonomous work is the default within an authorized design request. Interactive markup requires
  an explicit request for a user-driven review session.

## Output Contract

- A purposeful, runnable design or an evidence-backed review within the requested product scope.
- Captured pages and interaction states, with exact viewport, revision, theme, and route metadata.
- A Markdown report with inline relative image links, observed differences, and remaining limits.
- For variants, a reasoned recommendation and concrete features worth combining from each version.
- Preserved shader settings, motion identity, and approved visual constraints unless change is part
  of the request. Autonomous completion describes validation, separately from human approval.

# Entrypoint

## Stage 1: Resolve mode and ownership

1. Read the brief, repository instructions, current UI, and existing assets. Infer missing ordinary
   details from evidence; ask only about ambiguity that changes authority or the product's purpose.
2. Identify the primary user task, target routes, viewports, and existing workflow integrations.
   Keep the requested scope and use the actual product's terminology and content.
3. If interactive annotation or a designer review session was explicitly requested, proceed to
   Stage 2: Interactive handoff. Otherwise proceed to Stage 3: Autonomous design.

## Stage 2: Interactive handoff

1. Preserve the brief and current artifacts. Offer the optional `ui-mock` skill for the existing
   Pi UI Forge workflow; it governs that separate interactive session and its approval lifecycle.
2. If the interactive tools and session authority are available, use that workflow and finish with
   its actual outcome. Otherwise report the missing capability and finish with the preserved brief.

## Stage 3: Autonomous design

1. Record a short design intent: audience, primary task, layout hierarchy, type scale, spacing,
   palette roles, and one purposeful visual emphasis. Derive choices from the product and brief.
2. Inventory identity-bearing source: shader files, uniforms, compositing, color management,
   textures, motion assets, and current settings. Record paths and values before editing.
3. Reuse the existing identity-bearing implementation. Keep shader appearance and voice or status
   animations intact while improving composition. Evaluate visual changes against captured output.
4. Match the implementation effort to the requested deliverable. Use existing framework and assets;
   build real navigation, selection, forms, focus, and state transitions for the primary task.
   Represent unavailable services with explicit local state and disclose the boundary in the report.
5. Use a dedicated worktree per concurrent writer or variant. Record ownership, base revision, and
   runnable command for each. Carry out serial work directly when concurrency was not requested.
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
   for fonts, assets, layout, and shader initialization. Record capture settings and revision.
4. Exercise the primary workflow, keyboard navigation, selected states, scrolling, theme switching,
   and relevant empty, loading, and failure states. Capture states that reveal layout or behavior.
5. Inspect actual images. Check edge clipping, backgrounds, nested scroll behavior, interaction
   feedback, shader identity, legibility, and console errors against the brief and baseline.
6. For fidelity work, align viewport, scale, theme, data, and animation phase before comparison.
   Produce side-by-side images and a pixel-difference image using an available image library.
   Record changed regions and alignment limits; distinguish rendering noise from layout changes.
7. If observed defects remain within the authorized scope, fix them and repeat Stage 4. Otherwise
   proceed to Stage 5: Compare and report with any remaining defects explicitly identified.

## Stage 5: Compare and report

1. Run the smallest relevant build and interaction checks. Keep original captures and associate
   final screenshots with their exact source revision, route, theme, and viewport.
2. Write `visual-report.md` in the output directory. Embed selected page images with relative
   Markdown links; link remaining full-resolution captures without loading every image into context.
3. For each design, describe observed workflow choices, fidelity, interaction completeness,
   accessibility, and visual tradeoffs. Tie judgments to rendered evidence and exercised behavior.
4. For multiple variants, recommend one with reasons and identify useful elements from the others.
   For one design, summarize baseline changes and remaining limits. Use observed findings rather
   than numeric self-ratings as the quality evidence.
5. Report changed paths, runnable preview command, checks, report location, and blocked validation.
   Release only owned preview resources when their useful lifetime ends.
