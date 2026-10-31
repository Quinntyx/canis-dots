---
name: design-subagent
description: "Use when the user explicitly requests an interactive design-subagent session
  or designer-led UI review with live annotation and final approval through Pi UI Forge."
metadata:
  type: procedure
---

# Contract

## Input Contract

- An explicit request for interactive design review, a brief, project path, and designer authority.
- A resolved absolute `design-subagents` agent directory with existing `mock_build` and
  `mock_review` tools and native Pi automatic compaction enabled in profile and project settings.
- A compatible installed `pi_subagents` runtime, persistent Python kernel, and tmux.
- A durable mock folder with exclusive writer ownership, separate from production implementation.
- Production replication authority is separate from design review and requires approval of the
  exact final mock. Autonomous design belongs to the optional `visual-design` workflow.

## Output Contract

- One user-driven designer session retaining its identity through native compaction and dormancy.
- Mock source in `app/`, renders in `shots/`, annotations in `ann/`, and `design-notes.md`.
- Genuine tool-produced approval tied to the final version, or a cancelled or blocked outcome.
- Exact approved source and captures used for production replication when separately authorized.
- A terminal report that accounts for the designer before releasing its owned pool and resources.

# Entrypoint

## Stage 1: Prepare

1. Resolve the brief, mock folder, project instructions, and absolute designer agent directory.
   Inspect existing files and reuse the retained session for a requested resume. For a new session,
   read `../model-selection/SKILL.md` for exploratory candidate selection or a higher task floor.
   Preserve the existing model identity when resuming the retained designer.
2. Verify existing UI Forge tools and effective native compaction settings. Inspect the installed
   SDK for `AgentPool`, `Task.agentDir`, stages, submission, retained-handle continuation, and
   successful-turn dormancy. Record the imported source and version.
3. If these capabilities and launch authority are available, proceed to Stage 2: Start or resume.
   Otherwise proceed to Stage 6: Report with the exact missing capability and preserved files.

## Stage 2: Start or resume

1. In a persistent Python kernel, retain one `AgentPool(concurrency=1, name="design")`, a stage
   with `slots=1`, and the submitted handle. Use the actual installed SDK's signatures and admission
   policy. `../references/runtime.md` offers optional depth on the installed AgentPool API.
2. Submit one designer `Task` with the resolved `agentDir`, mock-folder `cwd`, brief, and a positive
   settle timeout compatible with the requested interactive lifetime. A wait bound measures when
   to inspect progress, independently of whether the human has finished reviewing.
3. Ask the designer to enter `mock_build` then blocking `mock_review` as the control plane for
   genuine user markup. Carry product constraints into the brief and retain native compaction as
   the context lifecycle. Keep design authority distinct from production editing authority.
4. For a resume, inspect the retained handle and continue the same session through its supported
   continuation API. Successful dormancy retains session identity and pending approval state.
5. If startup succeeds or the retained session is continuing, proceed to Stage 3: Review loop.
   Otherwise proceed to Stage 4: Verify outcome with the actual startup failure.

## Stage 3: Review loop

1. Let the single designer alternate building, blocking review, and user-directed revisions.
   Preserve exclusive ownership of its mock files and feedback loop while it awaits annotation.
2. Await the same handle and inspect actual state and errors. For a wait timeout with a usable
   session, remain in Stage 3 and re-await that handle. For a settled result or actual failure,
   proceed to Stage 4: Verify outcome.
3. Let Pi compact the existing designer session at its configured threshold or supported overflow
   recovery. Preserve latest direction, pending feedback, artifact paths, and approval state.
4. When native manual compaction is needed, target that exact designer session with `/compact` or
   an installed supported native API, after active tool work settles safely. Ordinary steering
   remains steering; compaction occurs only through Pi's native mechanism.
5. After compaction, re-anchor from `design-notes.md`, current source, and the latest relevant
   captures and annotations. Keep older full-resolution images available by path.

## Stage 4: Verify outcome

1. Inspect the actual review result, notes, source, renders, and tool-produced approval record.
   When `design-approval.json` exists, check its version and artifact digests against current files.
2. If genuine final approval matches the current version and implementation is authorized, proceed
   to Stage 5: Replicate. If it matches but implementation is outside scope, proceed to Stage 6
   with approved artifacts. Otherwise continue Stage 4 with approval still pending.
3. If the user cancelled or closed review without approving, proceed to Stage 6 with a cancelled
   outcome and retained mock. Otherwise continue Stage 4 and inspect the ability to resume.
4. If approval is pending and the retained session is usable, continue that session and return to
   Stage 3. Otherwise proceed to Stage 6 with a blocked outcome and the actual failure evidence.
5. Diagnose the actual provider error and retry result. Classify overflow only from evidence of
   overflow; preserve the same session during ordinary context pressure and supported recovery.

## Stage 5: Replicate

1. Use matching approved `app/`, `shots/`, and `design-notes.md` as the implementation contract.
   Record approval identity and source revision before production work.
2. Port layout, spacing, colors, components, shaders, and interactions pixel-near. Replace mock
   data with authorized real sources while preserving approved appearance and behavior.
3. Run relevant checks and capture the implemented states at matching viewport, scale, and theme.
   Compare side-by-side and pixel differences with an available image library; report deviations.
4. If a material design change needs human approval, return to Stage 3 with the changed version.
   Otherwise proceed to Stage 6: Report with implementation checks and remaining differences.

## Stage 6: Report

1. Account for actual approval, cancellation, or a reported blocker. A successful turn, saved
   checkpoint, or dormant window establishes execution state separately from design approval.
2. If the retained designer remains useful and can continue, preserve its pool and report pending
   review with its handle. Otherwise close the owned pool with synchronous `pool.close()` after
   terminal work is accounted for, retaining artifacts and unrelated user windows.
3. Report the actual outcome, mock folder, approved version when present, production changes,
   validation, and remaining decisions. Recovery of a genuinely unusable session requires explicit
   replacement authority; ordinary native compaction keeps the current session.
