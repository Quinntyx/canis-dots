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

1. For T3 execution or model-catalog selection, read the cached once-per-thread capabilities
   listing. Use `references/runtime.md` for T3 tool bindings and `model-selection/SKILL.md` for
   choices. Eligible native children may inherit this thread's documented provider/settings and
   use the native lifecycle; do not manufacture T3 task identities for them.
2. Establish the environment and baseline once in this thread. Check the actual execution path,
   test discovery and needed services. Give children ready inputs and scoped objectives.
3. Use the Runtime rules to choose native versus T3 execution. For T3 same-repo concurrent writers,
   verify this thread's bound project, then use `isolation:'worktree'`: T3 allocates from the
   coordinator's committed baseline, not arbitrary paths or uncommitted edits. Read-only children
   can share. Explicitly prepared, distinct repositories may each have one exclusive writer using
   shared mode with exact source-path ownership; isolation on the wrong T3 project is not useful.
   Never create a child's checkout in the shell or its brief. A child PR still needs publication
   authority; worktree allocation alone does not grant it.
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

1. Launch through the route selected by Runtime rules. Native same-provider/no-extra-settings
   children must finish in this turn using that mechanism's normal join. For T3 delegation use
   `delegate_task`, a meaningful role/title, and retain `taskId`. Prefer `mode:'async'` for background
   work; `mode:'wait'` is only for a result needed in this turn, with a real wait boundary. Native
   children do not acquire T3 task ids or use T3 lifecycle tools.
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
   must stay Working on a Claude host, its supported `t3_background_wait` can retain Working;
   other hosts follow the returned `next` instead. A wait timeout does not authorize status polling
   or establish failure: the child remains live and its completion wake is still expected.
4. Account for each `taskId` once, including failed and cancelled outcomes, in a short task record.
   Release only dependencies whose real acceptance checks pass; launch independent ready work
   immediately.
5. Use the objective ladder in `../runtime-verification/SKILL.md` for acceptance cost. One scoped
   review is enough when needed; no route requires five scoped and five final rounds. Repair small
   findings yourself. New delegate reviews/re-checks are new tasks and count against user limits.
   Two failed repairs of the same symptom trigger renewed diagnosis/escalation, not identical loops.
6. Case-local expected failures stay inspectable and unaffected work continues under a declared
   recovery policy. Shared-credential or infrastructure uncertainty propagates rather than being
   retried into the same error.
7. When requested results are ready, go to Stage 4: Verify. For start-only work or a blocked
   dependency, go to Stage 5: Retain or finish with the current state.

## Stage 4: Verify

1. Verify the requested outcome, not just child self-reports. Check cited evidence for research,
   reproduce claimed diagnoses, and exercise changed behavior for implementation.
2. For integrated code, validate the exact resulting revision and repository-required checks/CI.
   Verify configured CI when the task depends on it; do not provision hosting/runners just to fan
   out ordinary work. Pending required jobs are unresolved, while absent optional CI is a stated
   limitation rather than permission to expand scope. Include new tests in actual discovery.
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
3. Before replacing still-live T3 work, cancel its run with `task_cancel(taskId, reason)`; cancel
   work no longer needed as well. A completed task retains its result. New reviews/re-checks use
   new delegates within the original limits. Never interrupt a child's thread with the top-level
   `t3_thread_interrupt` tool.
4. Report outcomes first, then relevant checks and open limits. Keep internal orchestration detail
   in the durable record unless it is necessary to resume or understand a blocker.

# Focused entrypoints

- `model-selection/SKILL.md` selects child models, capability tiers and heterogeneous rosters.

- Read the matching reference before executing a route. These references inherit this skill's
  authority, runtime, workspace, lifecycle, and acceptance contract; they are not standalone skills.
- `model-selection/SKILL.md` owns model routing, not execution permission or a separate lifecycle.
