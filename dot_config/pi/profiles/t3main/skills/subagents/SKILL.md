---
name: subagents
description: "Use when delegating work, launching parallel children, coordinating multi-angle
  research or parallel implementation, integrating parallel work, selecting child models, or
  delegating review. This profile delegates through the t3-code MCP server."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The requested outcome, known context, acceptance criteria and permitted effects.
- Explicit child counts, parallelism, model choices and real deadlines when supplied.
- A thread in a T3 Code environment with the `t3-code` MCP server attached for delegated execution.
- A working environment, repository and shared-resource access appropriate to the task.

## Output Contract

- Verified requested results or an accurate partial outcome with blockers and resume identities.
- A task record, evidence artifacts and isolated workspaces proportional to the actual work.
- Exact-revision integration evidence when delivering code; source-backed synthesis for research.
- Hosted actions, target updates and cleanup only within the user's authorized scope.

# Runtime rules

- Call `orchestrator_capabilities` once per thread before the first `delegate_task`; again only
  after an error or a user-named provider change. Settings go in `target.options`; values from
  `orchestrator_capabilities` (for example `{effort:'max'}`) override inherited ones; `[]` or `{}`
  clears. Provider or model unavailable: say so.
- Use the native child mechanism only when the child uses your provider, a model it offers and no
  settings beyond yours, and finishes in this turn. Everything else — another provider, user-asked
  settings, a separate checkout, or background work — is `delegate_task`. "Workflow" only when
  the user asks for one.
- The child never receives broader modes than this thread: a runtime mode above yours is rejected.
  Treat this thread's runtime mode as the parallelism/authority ceiling.
- Children are visible in the T3 UI and browsable as threads: name them well, keep briefs
  self-contained, and mention a child result as its `link` verbatim when reporting.

# Entrypoint

## Stage 1: Select the smallest useful shape

1. Infer the outcome and effects from the request. Resolve only uncertainties that change authority,
   correctness or delivery. Use supplied deadlines as constraints; otherwise plan by dependencies.
   For model selection without execution, read `model-selection/SKILL.md` and return its plan.
   Other delegated work continues at step 2.
2. Continue with lightweight delegation for one assignment, research for evidence, independent
   implementation for separable subsystems, or dependent integration for accepted predecessors.
   One assignment or a small independent roster uses lightweight delegation and its relevant
   checks. An explicit multi-child request or substantial dependent scope selects only the
   coordination stages it needs.
3. Preserve requested child counts. Distinguish total launches, total assignments and live
   parallelism C. Parent runtime mode, user limits and model rate limits are the ceiling; use
   available headroom. A total-launch cap includes follow-ups and reviews according to its wording.
4. Decompose useful work by outcome or subsystem. Keep dependent work blocked until its actual
   inputs are accepted. Give builders room to discover their design in owned workspaces.
5. Record the selected shape and its reason in a brief plan, then go to Stage 2: Prepare.

## Stage 2: Prepare

1. Read the provider, model, option and runtime-mode list from `orchestrator_capabilities`.
   Use `references/runtime.md` for the compact `delegate_task`/`task_status`/`task_cancel`/
   thread-tool binding. Resolve each assignment's model and options per `model-selection/SKILL.md`.
   Simple delegation may inherit this thread's settings when capable.
2. Establish the environment and baseline once in this thread. Check the actual execution path,
   test discovery and needed services. Give children ready inputs and scoped objectives.
3. Let read-only children share this checkout (`isolation: 'shared'`). Give concurrent writers
   `isolation: 'worktree'` — T3 creates a prepared checkout per child from this thread's commit;
   uncommitted edits stay out, and a worktree child can deliver its own PR.
4. Resolve eligible model identities and supported effort per `model-selection/SKILL.md`. Apply
   explicit user choices before cost or diversity preferences. Carry the resolved role, model
   choice and relevant skill-entrypoint paths in each child's brief.
5. Give leaves zero delegation fuel. The brief either forbids spawning or bounds it within these
   rules; nested orchestration stays finite and inside inherited limits.
6. Record child identities, dependencies, revision/input identities, owners and acceptance checks.
   Launch a finite roster once; route streaming work as bounded batches instead of a scheduler.
7. Large intermediate material (logs, scans, data) lives in files and paths; a brief names its
   inputs by path and asks for a compact report, not a paste.
8. Go to Stage 3: Execute.

## Stage 3: Execute

1. Launch the useful children with `delegate_task`, `role` from implementation, research, review,
   design, test or general, retaining each returned `taskId`. Background children default to
   `mode:'async'`; use `mode:'wait'` only when this turn cannot proceed without the result, and pass a real `timeoutMs`
   matching that wait boundary.
2. Route according to the selected shape, then continue at step 3:
   - Lightweight delegation: one completion per useful assignment; see `references/delegation.md`.
   - Research: independent evidence questions and coordinator synthesis; see `references/research.md`.
   - Independent implementation: owned worktree children, relevant tests and scoped acceptance;
     see `references/independent-implementation.md`.
   - Dependent integration: release accepted prerequisites, mechanically merge and validate the
     resulting revision; see `references/dependent-integration.md`.
   - Review: distinguish feature acceptance from integrated behavior; see `references/review.md`.
3. Consume completions as their wake turns arrive. Do not poll a running child with `task_status`,
   sleeps or watchers. For a start-only child this thread should otherwise go idle; when the turn
   must stay Working, `t3_background_wait(taskId)` keeps this thread in Working until the child
   completes (`waiting: false` clears it). Treat a wait timeout as an inspection point, not a
   cancellation — the child keeps running and its result still arrives.
4. Account for each `taskId` once, including failed and cancelled outcomes, in a short task record.
   Release only dependencies whose real acceptance checks pass; launch independent ready work
   immediately.
5. Bound feedback loops by explicit counters and a useful acceptance criterion. Selected substantial
   implementation workflows retain five scoped review/repair cycles and five final cycles as caps;
   approval ends each loop immediately. Lightweight work uses only its relevant check.
6. Case-local expected failures stay inspectable and unaffected work continues under a declared
   recovery policy. Shared-credential or infrastructure uncertainty propagates rather than being
   retried into the same error.
7. When requested results are ready, go to Stage 4: Verify. For start-only work or a blocked
   dependency, go to Stage 5: Retain or finish with the current state.

## Stage 4: Verify

1. Verify the requested outcome, not just child self-reports. Check cited evidence for research,
   reproduce claimed diagnoses, and exercise changed behavior for implementation.
2. For integrated code, validate the exact resulting commit and required CI jobs. On Forgejo,
   establish working test CI before substantial implementation fan-out. Treat pending or missing
   jobs as unresolved evidence. Include newly added tests in discovery.
3. Compare delivered scope with the actual request. If acceptance passes, go to Stage 5: Retain or
   finish. Otherwise return actionable observed failures to Stage 3: Execute while repair remains
   authorized and within its cap; at exhaustion go to Stage 5 with an explicit blocker.

## Stage 5: Retain or finish

1. Persist accepted, failed, pending and blocked children by `taskId`; worktree paths, branches and
   PR links; session/thread ids; revision identities; counters; publication receipts and next
   actions. Use `references/resumable-state.md` for interruption and uncertain-side-effect recovery.
2. For active work, report the verified outcome, current blocker and concrete resume point. A
   finished delegate keeps its result: `task_status` reads it; a still-running delegate keeps its
   wake.
3. Do not start a replacement delegate for work you replace or no longer need: stop it with
   `task_cancel(taskId, reason)`. Never use `t3_thread_interrupt` on a child's thread id.
4. Report outcomes first, then relevant checks and open limits. Keep internal orchestration detail
   in the durable record unless it is necessary to resume or understand a blocker.

# Focused entrypoints

- `model-selection/SKILL.md` selects child models, capability tiers and heterogeneous rosters.

- Read the matching reference before executing a selected route. Every reference also runs
  independently.
- Every reference carries its own contract; this skill supplies general coordination when needed.
