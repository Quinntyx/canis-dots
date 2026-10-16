---
name: subagents
description: "Use when delegating work, launching or continuing subagents, using agent pools,
  coordinating parallel research, prototyping or evaluation workflows, integrating parallel work,
  or requesting an interactive design-subagent review."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The requested outcome, known context, acceptance criteria and permitted effects.
- Explicit agent counts, concurrency, model choices and real deadlines when supplied.
- A persistent Python kernel and installed `pi_subagents` for delegated execution.
- A working environment, repository and shared-resource access appropriate to the task.

## Output Contract

- Verified requested results or an accurate partial outcome with blockers and resume identities.
- A task ledger, evidence artifacts and isolated workspaces proportional to the actual work.
- Exact-revision integration evidence when delivering code; source-backed synthesis for research.
- Hosted actions, target updates and cleanup only within the user's authorized scope.

# Entrypoint

## Stage 1: Select the smallest useful shape

1. Infer the outcome and effects from the request. Resolve only uncertainties that change authority,
   correctness or delivery. Use supplied deadlines as constraints; otherwise plan by dependencies.
   For an explicit interactive designer session, read `design-subagent/SKILL.md`, execute its
   Entrypoint, and return that outcome. Other delegated work continues at step 2.
2. For a delegated prototype or first usable version, read `prototype/SKILL.md` and execute its
   Entrypoint; return here only for coordination detail needed by that procedure.
   For evaluation, benchmark passes/failures/crashes, regression diagnosis or issue triage, read
   `eval-triage/SKILL.md` and execute its Entrypoint, covering runner and agent errors alike.
   Otherwise continue with lightweight delegation for one assignment, research for evidence,
   independent implementation for separable subsystems, or dependent integration for accepted
   predecessors. One assignment or a small independent roster uses lightweight delegation and
   its relevant checks. An explicit workflow or substantial dependent scope selects only the
   coordination stages it needs.
3. Preserve requested assignment counts. Distinguish total launches, total assignments and live
   concurrency C. Read `PI_SUBAGENTS_MAX_CONCURRENT` as the runtime ceiling; use available headroom
   and user limits. A total-launch cap includes follow-ups and reviews according to its wording.
4. Decompose useful work by outcome or subsystem. Keep dependent work blocked until its actual
   inputs are accepted. Give builders room to discover their design in owned worktrees.
5. Record the selected shape and its reason in a brief plan, then go to Stage 2: Prepare.

## Stage 2: Prepare

1. Inspect the named kernel and installed `AgentPool`, `Task`, submission, completion and failure
   interfaces. Use `references/runtime.md` for the compact binding to the current API. Keep
   inherited admission identity and reservations runtime-owned. If public construction or admission
   is unavailable, preserve its original error and go to Stage 5: Retain or finish with delegated
   execution blocked. Otherwise continue preparation at step 2.
2. Establish the environment and baseline once in the coordinator. Check the actual execution
   path, test discovery and needed services. Give workers ready inputs and scoped objectives.
3. Let read-only workers share immutable inputs. Give concurrent writers separate worktrees.
   Assign one owner to integration, publication and each scarce shared resource.
4. Inherit the selected profile's model unless the user names a model or authorizes role routing.
   Resolve explicit model/provider/effort choices against the live catalog. Preserve unavailable
   choices as blockers or obtain an authorized substitute. Treat quota changes as current context.
5. For authorized role routing, use a strong reasoning model for implementation, integration and
   consequential review; use a throughput model for bounded diagnosis or evidence extraction.
   Choose actual models from the live catalog and task context. Research inherits the selected
   profile unless the request supplies a different choice.
6. Give leaves zero delegation fuel. Keep any authorized nested orchestration finite and within
   inherited global limits. Use parent-owned scheduling for the ordinary path.
7. Record task identities, dependencies, revision/input identities, owners and acceptance checks.
   For a finite roster, queue the useful assignments once. For a stream, bound admitted backlog.
8. Separate setup, submission/collection and teardown cells. Use saved-cell review when required
   by the execution tools; autonomous execution follows the user's existing authorization.
   Go to Stage 3: Execute.

## Stage 3: Execute

1. Create only the necessary AgentPool stages. Use `stage.submit` or `stage.submit_all` and retain
   their handles. Stage slots express scheduling priority; coordinator admission enforces leases
   and hard stage-specific limits. Share the available C across all live work.
2. Route according to the selected shape, then continue at step 3:
   - Lightweight delegation: one completion per useful assignment; see `references/delegation.md`.
   - Research: independent evidence questions and coordinator synthesis; see
     `references/research.md`.
   - Streaming evaluation: read `eval-triage/SKILL.md` and execute its Entrypoint for bounded
     intake, diagnosis, error isolation and serialized publication before continuing this stage.
   - Independent implementation: owned subsystem worktrees, relevant tests and scoped acceptance;
     see `references/independent-implementation.md`.
   - Dependent integration: release accepted prerequisites, mechanically merge and validate the
     resulting revision; see `references/dependent-integration.md`.
   - Review: distinguish feature acceptance from integrated behavior; see `references/review.md`.
3. Consume completions as they arrive through one accounting path, normally `await pool.pop()`.
   Record each handle once, including failed and cancelled outcomes. Release only dependencies
   whose real acceptance checks pass; replenish independent ready work immediately.
4. Bound feedback loops by explicit counters and a useful acceptance criterion. Selected substantial
   implementation workflows retain five scoped review/repair cycles and five final cycles as caps;
   approval ends each loop immediately. Lightweight work uses only its relevant check.
5. Keep case-local expected failures inspectable and continue unaffected work under a declared
   recovery policy. Propagate shared-state uncertainty and unexpected scheduler/runtime failures.
   A waiting timeout or cell interrupt is an inspection point with the pool still owned.
6. When requested results are ready, go to Stage 4: Verify. For start-only work, interruption or a
   blocked dependency, go to Stage 5: Retain or finish with the current state.

## Stage 4: Verify

1. Verify the requested outcome, not just worker self-reports. Check cited evidence for research,
   reproduce claimed diagnoses, and exercise changed behavior for implementation.
2. For integrated code, validate the exact resulting commit and required CI jobs. On Forgejo,
   establish working test CI before substantial implementation fan-out. Treat pending or missing
   jobs as unresolved evidence. Include newly added tests in discovery.
3. Compare delivered scope with the actual request. If acceptance passes, go to Stage 5: Retain or
   finish. Otherwise return actionable observed failures to Stage 3: Execute while repair remains
   authorized and within its cap; at exhaustion go to Stage 5 with an explicit blocker.

## Stage 5: Retain or finish

1. Persist accepted, failed, pending and blocked tasks; pool and handle identities; session paths;
   workspaces; revision identities; counters; leases; publication receipts; and next actions.
   Use `references/resumable-state.md` for interruption and uncertain-side-effect recovery.
2. For active work or expected follow-up, retain the named kernel, open pool, handles and sessions.
   Report the verified outcome, current blocker and concrete resume point.
3. For completed owned work with no continuation needed, close that pool explicitly. Perform
   authorized workspace cleanup only after final delivery validation, preserving recoverable work.
4. Report outcomes first, then relevant checks and open limits. Keep internal orchestration detail
   in the durable ledger unless it is necessary to resume or understand a blocker.

# Focused entrypoints

- `design-subagent/SKILL.md` selects the explicitly requested interactive designer session.

- `prototype/SKILL.md` selects a runnable prototype path with optional independent subsystem
  work.
- `eval-triage/SKILL.md` selects streaming regression diagnosis and bounded issue publication.
- Read the matching child before executing either selected route. Both also run independently.
- Every child carries its own contract; this skill supplies general coordination when needed.
