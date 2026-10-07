---
name: hack-plan
description: "Use when the user asks to plan or swarm-build a prototype under a
  deadline, prioritize a demo, cut scope, or maximize useful parallel delivery
  for a hackathon, demo day, or game jam."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A bounded prototype objective, intended demo, and permitted effects. A deadline,
  human responsibilities, stack, and deployment target may already be specified.
- Distinguish planning from permission to implement. An expression of interest is
  not permission to write code, change git state, deploy, or modify configuration.
- For implementation: an approved checkout, baseline identity, integration branch,
  acceptance checks, resource ownership, and permission for necessary git effects.
- For agent execution: a notebook-backed PTC kernel, tmux, `pi_subagents`, and a
  selected agent directory loading pi-sock and pi-activity. Extra coordinator,
  research, and design profiles are optional, not prerequisites.
- C is `PI_SUBAGENTS_MAX_CONCURRENT`, default 8 when unset. Read, never change, it;
  reject invalid or non-positive values. Respect inherited immutable root limits.
- Existing plans, user files, credentials, and uncommitted work remain protected.

## Output Contract

- A concise plan identifying the demo slice, scope cuts, assumptions, task graph,
  ownership, milestones, acceptance checks, and fallback; no compulsory ceremony.
- When authorized, maintain an uncommitted repository-root `PLAN.md`. Use another
  agreed path if that file belongs to the user; never overwrite it or commit it.
  Record material decisions there; use existing decision records when available.
- For implementation: the earliest feasible runnable vertical slice, followed by
  incrementally integrated improvements and evidence from the actual demo path.
- A durable notebook recording runtime identity, constants, orchestration,
  outcomes, inspection, and separate deliberate teardown; no orphaned workers.
- Report delivered behavior, demo instructions, passed/failed/not-run checks,
  remaining blockers, acknowledged stubs, and published integration identity.

# Entrypoint

## Stage 1: Frame the run

1. Identify planning-only versus authorized implementation and record permitted
   effects. Read relevant existing project metadata before choosing a stack;
   this procedure supports greenfield projects and bounded prototype changes.
2. Extract the demo's single success condition, clock, environment, constraints,
   existing credentials' availability, and human-owned work from the request.
   Ask at most one short questionnaire round for blocking unknowns. Do not repeat
   supplied answers or make a detailed grill a prerequisite for starting.
3. Choose reversible defaults for non-blocking decisions and record assumptions.
   Never auto-default permission, destructive effects, secrets, or a user approval
   gate. Honor explicit autonomy; do not introduce unnecessary confirmation steps.
4. Time-box planning to a small fraction of the available clock. Without a stated
   clock, use milestone checkpoints rather than inventing a deadline. Declare a
   finite execution budget before launching agents and reserve final demo time.
5. Identify the riskiest dependency and the shortest route to a runnable end-to-end
   slice. Go to Stage 2: Cut the scope; do not expand into general architecture work.

## Stage 2: Cut the scope

1. Separate must-demo, optional improvement, and stretch work. Write observable
   acceptance checks for the must-demo slice and an explicit feature cut order.
2. Specify intentional stubs, hardcoded data, and deferred integrations. Label
   them honestly in handoff and demo notes; do not fabricate validation or bypass
   access controls. Prefer a working bounded prototype over unfinished breadth.
3. Plan milestones for runnable scaffold, functioning vertical slice, and stable
   demo. Each must state what actually works and how to verify it. These are
   integration checkpoints, not barriers requiring every workstream to finish.
4. Define a freeze checkpoint and a fallback demo path. Reserve time for smoke
   checks, repair, and handoff. Cut optional work before borrowing that reserve.
5. For planning-only requests, go to Stage 6: Inspect and replan without agent
   setup, scaffolding, worktrees, commits, or deployments. Otherwise go to
   Stage 3: Establish boundaries.

## Stage 3: Establish boundaries

1. Record the approved checkout, revision, relevant uncommitted path/digest
   manifest, target branch, and human edits. Do not assume `main` is the target;
   use an authorized existing `dev` or explicit user destination. Never switch
   branches in place or incorporate unrelated work without permission.
2. Define the minimum shared interfaces needed for the first slice, with one
   contract owner. Reuse existing paths and types; a new `shared/` directory,
   global version constant, and separate decision file are not mandatory.
   Clear interface-dependent tasks only after the relevant contract is accepted.
3. Decompose into bounded deliverables with identity, satisfied prerequisites,
   owned files, shared-resource ownership, baseline, acceptance checks, timeout,
   stop condition, and complete/blocked report requirements. Prefer narrow tasks
   that quickly unlock integration over coarse phase-long assignments.
4. Assign owners or serialization gates for generated output, caches, ports,
   fixtures, services, dependency installs, and repo-wide checks. File globs alone
   do not establish isolation. Readers inspect accepted immutable snapshots;
   checks that mutate resources require ownership even in read-only audits.
5. Share a checkout only with explicit authorization and disjoint file/resource
   ownership. Otherwise obtain authorized isolation or serialize/repartition.
   Allocate worktrees lazily from the approved baseline only when ready work
   needs them; bound allocations and retain failed workspaces for inspection.
   Worktrees do not isolate shared caches, ports, or external services.
6. One parent owns integration and task routing. Protect its integration target;
   gate repo-wide commands against concurrent conflicting writes. Reconcile
   contract changes only with affected owners at a safe completion boundary;
   never broadcast rebases to active writers or mutate their baselines mid-turn.
7. For GUI work, start the functional frontend alongside other independent work.
   A design/mock track is optional and must not gate all frontend progress unless
   the user explicitly requires mock approval. Gate only the affected decisions.
8. If safe ownership and approved effects are established, go to Stage 4: Author
   the workflow. Otherwise record blockers and go to Stage 6: Inspect and replan.

## Stage 4: Author the workflow

1. Provision a notebook in the project's `.pi/workflows/` unless another location
   is selected. Import `pi_subagents as subagents`; record `subagents.__file__`,
   loaded source/revision or distribution identity, and this skill's path.
2. Inspect `inspect.signature(subagents.Task)`, `subagents.AgentStage.submit`, and
   `subagents.AgentStage.submit_all`. Require `Task.agentDir`, not `profile`;
   submit accepts `parent`, `session_handle`, and `session_name`, while submit_all
   accepts `parent`. Check `AgentPoolFailureError`, `PiSockSessionEnded`,
   `SchemaValidationError`, and `agent_dir_defaults` are public exports. Verify
   success-only dormancy and failure-session retention from source or scoped
   evidence; signatures alone cannot establish lifecycle compatibility.
3. If incompatible, report the actual mismatch and go to Stage 6: Inspect and
   replan. Do not install software, change profiles, swap sources, or translate
   removed arguments to make the preflight pass. An authorized runtime update
   requires a fresh compatible kernel; never reset a kernel with live pools.
4. Save constants, visible workflow, and teardown in separate recorded cells with
   `write_cell`. Constants include prompts, schemas, paths, C, task graph, model
   requests, budgets, ownership, timeouts, and round caps. The workflow exposes
   every Task, stage, submission, completion consumer, dependency and round gate.
5. Use `AgentPool()` to inherit C or select a smaller positive limit at most C.
   For C=1 use one delivery stage. For C=2 use build and flow stages; flow handles
   review, repair, and checkpoints. For C=3 use build, quality, and checkpoint;
   quality handles review and repair. For larger C give review, repair, and
   checkpoint one positive slot each and build the remainder. Slot sums must
   not exceed C. These are soft reservations; idle capacity is work-stolen,
   allowing builds to use full C. Submit no task just to occupy a reservation.
6. Plan approximately 3C useful dependency-cleared tasks in the active-plus-queued
   frontier when independent work exists. Keep blocked work in the parent ledger,
   not running agents. This is queue headroom, not 3C simultaneous agents, a
   minimum quota, delegation fuel, or permission to expand the project.
7. Prioritize the demo critical path, work unlocking many dependents, repair,
   review, and integration over optional breadth. Bound the submitted backlog so
   stale low-priority work does not delay new critical work; reorder unsubmitted
   ready work in the parent rather than inventing a runtime priority argument.
8. Declare a finite task/continuation budget and review/fix cap, normally two
   repair rounds or fewer when the clock demands it. Unexpected failures propagate.
   Any recoverable-completion policy must name eligible units, exact cause types,
   containment conditions, and exactly-once accounting before execution.
9. Save a separate teardown cell containing synchronous `pool.close()`. Do not
   close in a workflow cell, context manager, error handler, or `finally` block.
   Guard replay with submission identities, accepted evidence, baseline and inputs;
   reuse an open pool without duplicating work or caching blocked reports as done.
10. Unless the user requested autonomy/no prompts, call `request_cell_review` on
    the saved workflow before execution. On approval or authorized autonomy, go
    to Stage 5: Run the delivery loop. On rejection return to Stage 4: Author the
    workflow. New permissions or materially expanded cost require fresh approval.

## Stage 5: Run the delivery loop

1. Execute saved constants with `run_cell`, verify them, then execute the saved
   workflow. Use one completion consumer per pool and ordered kernel execution.
   Never launch the workflow from scratch, use `asyncio.run`, or blindly replay
   an active notebook. Submit only tasks whose dependencies/resources are clear.
2. Set explicit `Task.cwd`, schema, timeout, and integer `metadata["rounds"]`.
   Public Task fields are prompt, name, model, thinking, schema, cwd, agentDir,
   timeout, and metadata. Omitted model/thinking inherit the chosen agent directory;
   do not select a model manually unless the user requested one.
3. Consume `await pool.pop(timeout=...)` in completion order. Record each outcome
   exactly once, inspect the deliverable and acceptance evidence, and immediately
   refill unaffected useful ready work. Do not wait for whole batches, submission
   order, arbitrary sleeps, or all workstreams before integrating the first slice.
4. Release dependencies only after semantic acceptance and required checks pass.
   A valid response schema, settled session, or blocked/incomplete report is not
   acceptance. Route scoped review and smoke checks immediately on accepted
   prerequisites; validate the actual snapshot, not an evolving writer checkout.
5. Prefer targeted review and fast deterministic checks on the demo path. Keep
   correctness, interface, and safety gates; avoid mandatory PR creation, separate
   arbitration agents, exhaustive reviews, or five-round polish loops. Heavy
   checks run at a stable integration checkpoint when required by acceptance.
6. Route necessary fixes with `stage.submit(task, parent=result,
   session_handle=result.handle)` when the retained session can continue. Carry
   and increment rounds explicitly; preserve timeout, schema, ownership and fuel.
   Send concise prose describing feedback, not raw JSON or entire result dumps.
   Never run simultaneous continuations on the same session.
7. Integrate accepted contributions incrementally through the integration owner.
   Verify source checkout, baseline, changed-path/artifact identity, check evidence,
   and target identity. Gate demo validation on accepted integration; isolated
   tests and unmerged branches do not establish a working prototype.
8. At risk of missing the checkpoint, cut optional scope, use acknowledged stubs,
   or simplify the interface. Stop requeuing at the round cap or deadline. A
   blocked decision stops only its dependents; unaffected useful work continues.
9. When the demo slice works, preserve it while improving it. At freeze, stop
   optional dispatch and allow necessary checks/repairs to drain. Do not create
   new work to keep C occupied. Record any cancellation's actual outcome.
10. `pop()` returning None means quiescence, not success or pool closure. On
    quiescence, failure, timeout, or interruption go to Stage 6: Inspect and replan
    with pools and diagnostics intact.

## Stage 6: Inspect and replan

1. For planning-only runs, inspect the plan against the demo, clock, cuts,
   ownership and acceptance checks, then go to Stage 7: Deliver and teardown.
   Otherwise inspect `pool.snapshot()`, `pool.handles(...)`, results, open gates,
   integration identity, and every passed/failed/not-run check with its evidence.
2. Account for failed, cancelled, incomplete, and unsubmitted work separately.
   Retain failed sessions and workspaces; never treat cleanup as validation or
   delete unmerged work to claim completion. Timeout/interrupt alone does not
   cancel tasks; inspect before any continuation or new submission.
3. If bounded continuation is necessary, permitted, and within remaining budget,
   return to Stage 5: Run the delivery loop. If scope/permissions materially
   change, return to Stage 4: Author the workflow. Otherwise go to Stage 7:
   Deliver and teardown with explicit blockers or partial-delivery status.

## Stage 7: Deliver and teardown

1. For planning-only runs, report the plan/artifact path and unresolved decisions,
   then stop without agent or git effects. Otherwise validate the integrated demo
   command/path and record its actual behavior, limitations, and fallback.
2. Unless the user chose another end state, merge contributing branches into the
   intended integration branch, validate, and push before claiming delivery. Do
   not create PRs unless requested. Preserve unrelated and unmerged work.
3. Once inspection is complete and retained sessions are no longer needed, execute
   the dedicated teardown cell calling `pool.close()` without await and inspect
   its PoolSummary. `subagents.finish()` is deliberate cleanup of all live pools,
   not routine per-workflow teardown. Successful validated dormancy is automatic.
4. After workers stop, clean only authorized, owned temporary fan-out branches
   and worktrees whose contributions are published. Preserve canonical main/dev,
   integration branches, failed workspaces and user files; use trash, never rm.
5. Report the runnable result and published identity, demo instructions, remaining
   gaps/stubs, validation evidence, notebook/plan paths, and cleanup status. If
   delivery is blocked, report that rather than presenting a branch roster as done.

# Admission and delegation

- C bounds admitted active work across pools in this process. Root live-window,
  admission-count and deadline limits also constrain kernels and descendants.
  Starting statuses may include admission waits; do not infer capacity violations
  from their count. A queued roster or user-requested job count never raises C.
- Treat requested task count separately from requested simultaneous concurrency.
  Explain limits when the requested concurrency exceeds admitted capacity; execute
  useful approved work within them, never change settings or launch around guards.
- Read `PI_SUBAGENTS_MAX_DEPTH` and inherited depth/root identity without changes;
  maximum depth 1 is flat, root depth 0. Parse depths as nonnegative integers.
  Root `PI_SUBAGENTS_ROOT_MAX_CONCURRENT` defaults to C, root admission count
  `PI_SUBAGENTS_ROOT_MAX_TASKS` to 512, and shared admission/wait deadline
  `PI_SUBAGENTS_ROOT_TIMEOUT` to 1800 seconds. Parse limits as positive integers;
  malformed values block dispatch. These are not fresh allowances per workflow.
- Parent-waiting windows occupy capacity; leave headroom before authorized
  nesting. Saturated nested admission fails fast, not forever. Retained failed
  windows remain charged until explicit close confirms their termination.
- Default every assignment to a leaf: explicit no-spawning instruction,
  `delegation_jobs_remaining=0` and `delegation_levels_remaining=0` in the prompt
  and metadata. The parent routes research, design, review and integration too.
- Allow recursion only when explicitly authorized for a narrower verifiable unit.
  Root B is finite approved job/continuation fuel; L cannot exceed unused depth.
  Reserve 1+B_child for each child from remaining B; all reservations must fit.
  Set L_child at most L-1 and unused inherited depth. No child invents fuel from C.
- Put each child's explicit authorization, B/L allocation, scope, deadline, rounds,
  acceptance checks, stop condition, owner and monotone allocation rules in its
  prompt. Mirror budgets in metadata; metadata alone does not teach the contract.
- Count every scheduled child task, retry and continuation against fuel without
  refunds. Preserve spent fuel/rounds and one ledger owner across cells; uncertain
  recovery blocks further delegation. Child deadlines cannot exceed the parent's.
- Missing authorization, invalid B/L, zero fuel/levels, or exhausted runtime limits
  means finish locally or report blocked. Never bypass with manual Pi launches,
  fresh roots, changed depth/limits, new kernels, or replacement sources.
- Fuel/authorization are orchestration policy, not a runtime security capability.
  Local PTC snapshots are not root-wide descendant telemetry.

# Failure and continuation

- Failures raise; do not use removed `result.ok` or unwrap helpers. `pool.pop()`
  raises `AgentPoolFailureError`; `.result` identifies the unit and `__cause__`
  preserves its error. Underlying causes include `PiSockSessionEnded` and
  schema-repair exhaustion. A cancelled result has no successful schema body.
- Catch only an individual pop failure matching the predeclared recoverable
  policy's exact cause types, eligible unit, and containment conditions. Account
  once, retain diagnostics, block dependents and refill safe unrelated work.
  Do not automatically retry or blanket-catch unexpected/shared-resource failures.
- A pop timeout stops the wait, not the pool, and is not a completion. Retain pools
  on interruption/failure for inspection; explicit close invalidates handles.
- Active `handle.send` steers, not creates an independent result. A terminal send
  schedules a new handle; track its completion exactly once. It does not increment
  rounds, so use explicit stage submission for bounded repair cycles.
- Only successful validated tasks may become dormant. Retained live/dormant
  sessions can continue through the public API; dead non-dormant sessions do not
  automatically respawn. Never manually unload failure windows or hot-reload live
  pools. A task timeout covers a turn, not queue wait or the entire workflow.

# Research basis

- See [orchestration research](references/orchestration-research.md) for source
  evidence and tradeoffs. This procedure contains its essential runtime and
  scheduling rules; no other skill is required to execute its basic workflow.
