---
name: ui-mock
description: "Use when a UI mock needs an interactive design-subagent review before implementation."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A product brief, target pages, visual constraints, project path, and authority to run a designer.
- A resolved absolute `design-subagents` agent directory with Pi UI Forge available and Pi native
  automatic compaction enabled. Check profile and project overrides; do not change settings
  silently.
- A durable mock folder distinct from production implementation, with a known owner for its files.
- A compatible `pi_subagents` runtime available in a persistent Python kernel, and tmux available.
- Explicit user approval of the exact final mock before implementing that design in production.

## Output Contract

- One user-driven designer session, preserved through native compaction, with no competing writers.
- Mock source in `app/`, rendered pages in `shots/`, annotations in `ann/`, and `design-notes.md`.
- A truthful terminal outcome: approved, cancelled, or blocked; successful turn settlement alone
  never establishes approval. Preserve approval evidence produced by the installed UI Forge tools.
- For approval, the exact approved version, matching source and renders, and production replication
  within the user's implementation request. For cancellation or a blocker, a report without rollout.
- A closed pool only after terminal work is accounted for and no continuing designer is needed.

# Entrypoint

## Stage 1: Prepare

1. Resolve the brief, project, mock folder, and absolute designer agent directory. Inspect existing
   mock files and repository instructions; preserve unrelated work. For a requested resume, reuse
   the existing designer session and mock folder when available rather than duplicate the designer.
2. Verify the designer profile exposes `mock_build` and `mock_review`, and check native compaction
   configuration for that profile and project. If compaction is disabled or unavailable, report the
   mismatch and obtain authorization to correct it; do not replace the session as a workaround.
3. Inspect the actual imported SDK: require `AgentPool`, `Task.agentDir`, `stage`, `submit`,
   retained
   handle continuation, and success-only dormancy. Record runtime source/version. An older `profile`
   argument is not compatible. On incompatibility, stop with the required runtime change; otherwise
   continue to Stage 2. Do not upgrade software or alter profiles without authorization.

## Stage 2: Start or resume the designer

1. In a persistent kernel, create `AgentPool(concurrency=1, name="design")` and a design stage with
   `slots=1`. Keep the pool and submitted handle in kernel state so later cells can inspect or await
   the same session. Save the orchestration in a notebook for substantial work.
2. Submit one `Task` containing the brief with `name="designer"`, the resolved absolute `agentDir`,
   `cwd` set to the mock folder, and an explicit positive settle timeout appropriate for human
   review; allow at least four hours unless the user specifies otherwise. Check actual SDK fields
   before supplying additional options. Apply required admission metadata without granting children
   authority to spawn other agents. Do not launch variants or helpers into the same design loop.
3. Include the lifecycle contract in the submitted instructions: the designer must keep the same
   session through native compaction, use only genuine user feedback from `mock_review`, and never
   settle merely to reduce context. Product constraints remain in the brief; do not override the
   designer's design discipline or imply that implementation has been authorized.
4. For an existing handle, inspect its actual state and continue that session using the supported
   continuation API only when appropriate. A dormant successful handle retains its session identity;
   dormancy is neither approval nor permission to create a replacement designer.
5. Continue to Stage 3 once the designer is running. On a real startup or session failure, proceed
   to Stage 4 with a blocked outcome rather than claim a successful design.

## Stage 3: Run the interactive loop

1. Let the designer alternate propose, `mock_build`, blocking `mock_review`, and user-directed
   revision. A feedback tool waiting for markup is expected; do not interrupt it for context upkeep.
   The parent may perform unrelated work but must not edit the mock or compete for its review loop.
2. Await the same handle. Check the actual result and error, not merely a completed await or an idle
   window. A cell or settle-wait timeout does not establish a terminal design outcome: inspect the
   live session, retain the pool, and re-await the same handle when it is still waiting for
   feedback.
3. Let Pi compact the designer's existing session automatically when its configured threshold or
   supported overflow recovery triggers. Compaction preserves session identity and rebuilds model
   context; it is not a final response, checkpoint handoff, approval, or reason to close the pool.
4. If manual compaction is needed, use Pi's native `/compact` command in that designer session or a
   supported native compaction API targeting that exact session. Wait for active feedback/tool work
   to finish safely. Ordinary steering text is not a native compaction command. Preserve the latest
   user direction, pending feedback, unresolved decisions, artifact paths, and approval status in
   the compaction instructions; do not invent an SDK method or run compaction in the parent instead.
5. After compaction, the designer re-reads `design-notes.md`, the current source as needed, and only
   the latest relevant renders and annotations. Continue the same review loop with pending feedback.
   Keep the contract current without duplicating transcript history or repeatedly loading old
   images.
6. If a settled result arrives, proceed to Stage 4. If feedback is still pending, stay in Stage 3.
   A context percentage, review count, saved file, or successful stop is never a completion gate.

## Stage 4: Verify the outcome

1. Read the result, `design-notes.md`, current source, final renders, and the actual review outcome.
   Inspect `design-approval.json` when the installed tools produce it. Verify approval belongs to
   the exact current version and artifact digests when provided; do not manufacture approval files.
2. If genuine final approval is present and implementation is authorized, continue to Stage 5. If
   approved but implementation was not requested, report the approved artifacts and go to Stage 6.
3. If the user closed or cancelled the editor without approving the final version, record cancelled,
   retain the mock, report what remains, and go to Stage 6. Closing the editor does not approve it.
4. If an actual error, provider failure, or unrecoverable session loss blocks work, report blocked
   with the evidence and preserved artifact paths, and go to Stage 6. Do not classify every 400 or
   413 response as context overflow or assume Pi recovered; verify the actual error and retry
   result.
5. If an agent settled with approval pending, classify the design as incomplete, not approved. When
   its retained session can continue, resume that same designer with the remaining task and return
   to Stage 3. Otherwise report the blocker and seek explicit authorization for recovery; never
   silently substitute a new designer or promote a checkpoint summary to completion.

## Stage 5: Replicate the approved design

1. Use the exact approved `design-notes.md`, matching `app/` source, and final `shots/` renders as
   the implementation contract. Confirm the production destination and repository constraints.
2. Port components, layout, spacing, colors, and structure pixel-near. Replace dummy data with real
   sources while preserving the approved appearance and requested interactions.
3. Run relevant checks and compare the implemented pages with the approved renders. Report any
   remaining differences; do not claim approval for a materially changed design.
4. Continue to Stage 6 after reporting the implemented paths and mock source location.

## Stage 6: Teardown and report

1. Before closing, confirm approval, cancellation, or a reported blocker is accounted for and the
   designer is no longer needed. Never close a pool just because a wait timed out or context grew.
2. Call synchronous `pool.close()` only at this terminal boundary. Preserve the mock and session
   artifacts; remove only owned temporary resources and never close unrelated windows or editors.
3. Report the actual outcome, mock folder, approved version when applicable, production changes,
   validation, and remaining decisions. Explicitly say when no final approval was obtained.

# Context and completion invariants

- Native Pi compaction is the context lifecycle. Do not request a saved-file handoff, terminate the
  designer, reset its session, or replace it based on a context percentage or number of reviews.
- Durable files support re-anchoring and genuine recovery; saving them does not complete the task.
- A successful settled turn may automatically hibernate its tmux window. This is runtime cleanup,
  not evidence of design approval. Never cause that cleanup with a premature success response.
- Preserve approval as pending through compaction until the user approves that exact final version.
- A genuinely unusable session may require recovery, but report it and obtain explicit authorization
  before creating a replacement. Normal context pressure is not such a failure.
