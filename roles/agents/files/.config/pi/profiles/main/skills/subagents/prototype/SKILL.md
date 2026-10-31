---
name: prototype
description: "Use when building a runnable prototype, proof of concept, or first usable
  version, including exploratory subsystem implementation."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A prototype objective, existing or new repository, target branch and permitted effects. New
  projects are created by the `../../git/init-project/SKILL.md` flow, not by this procedure.
- Known stack, external-service constraints, required behavior and actual deadline when supplied.
- A usable baseline and checks appropriate to the behavior being built.
- AgentPool capacity and worktree authority when delegating independent implementation.

## Output Contract

- A runnable end-to-end prototype of the requested core behavior with relevant verification.
- Explicit status of external integrations, agreed mocks, optional work and remaining blockers.
- Accepted integrated changes, or preserved partial work and a concrete resume point.
- Publication and workspace cleanup within the user's authority and after delivery validation.

# Entrypoint

## Stage 1: Select the runnable core

1. Infer the core user path and acceptance criteria from the request and repository context.
   Ask only for load-bearing unknowns. Use the supplied deadline when present; otherwise prioritize
   runnable behavior and dependency order.
2. Separate required core behavior from optional expansion. Establish acceptable mocks from the
   request or explicit agreement, and keep their status visible in the delivered result.
3. For planning-only requests, go to Stage 5: Deliver with the plan. For authorized implementation,
   go to Stage 2: Prepare.

## Stage 2: Prepare

1. For a new project, or an existing one without hosting, worktrees or test CI, run the
   `../../git/init-project/SKILL.md` procedure instead of bringing up git hosting, the `dev`
   worktree, the test workflow or the cwd move here. Resume this procedure at step 2 in the
   initialized container once that flow reports a green baseline, or report its blocker and go to
   Stage 5: Deliver.
2. Inspect the real framework, entrypoints, test discovery, remote and target baseline. Establish
   the local run command and the smallest relevant behavioral check.
3. Use one builder for a tightly coupled core. Choose parallel builders for genuinely independent
   subsystems when their useful work exceeds coordination cost. Honor explicit assignment counts
   and available concurrency from `PI_SUBAGENTS_MAX_CONCURRENT`.
4. Before substantial Forgejo implementation fan-out, verify working test CI, branch triggers,
   runner availability and discovery of added tests. Obtain required green baseline checks at the
   exact SHA. With a usable baseline go to Stage 3: Build; otherwise go to Stage 5: Deliver with
   the preserved blocker. A small local build uses its relevant local checks and goes to Stage 3.

## Stage 3: Build

1. Implement the thin end-to-end core directly or through the selected useful subsystem roster.
   Give each delegated writer an owned worktree and the overall request, subsystem objective,
   ready environment, permitted effects and acceptance criteria. Builders discover their design.
2. Use an explicitly named persistent kernel, `AgentPool` and `Task` when delegating. Inspect the
   installed API first. Set each Task's `cwd` and `agentDir`. Read `../model-selection/SKILL.md`
   for scoped builders, frontier engineers or acceptance reviewers as needed. Resolve the task's
   floor and explicit choices through that policy; give leaves zero delegation fuel.
3. Queue useful assignments once with `stage.submit` or `stage.submit_all`. For selected large
   high-parallelism work, up to 2C useful initial assignments is a headroom policy, not a minimum.
   Enforce real shared-resource leases in coordinator admission; stage slots are soft priorities.
4. Collect with `await pool.pop()` and account for each handle once. Retain confined failures and
   their workspaces, block their dependencies, and continue independent ready work. Inspect
   `AgentPoolFailureError.result` and its exact cause before applying a declared recovery policy.
   Unexpected failures and waiting interruptions retain the owned pool for inspection.
5. Require runnable subsystem behavior and relevant tests. In substantial workflows, use scoped
   intermediate review for consequential defects with a five-cycle repair cap and immediate exit
   on acceptance. Continue repairs in the original retained session using a new handle.
6. With accepted core components, go to Stage 4: Integrate. For a blocked required component or
   exhausted authorized repairs, go to Stage 5: Deliver with preserved partial state.

## Stage 4: Integrate

1. Integrate accepted dependencies in their actual order. For independent peer branches, prefer
   balanced mechanical pairs in owned merge worktrees, carrying any lone node forward unchanged.
   Explicit user-selected equal-depth power-of-two policies take precedence.
2. Start with ordinary `git merge`. Delegate repair for observed textual conflict or semantic test
   failure. Validate repaired tips before release and keep unrelated ready work moving.
3. Exercise the complete user path, entrypoints, hot paths and required integrations. Validate the
   actual resulting revision and applicable CI, including newly added tests. Whole-prototype
   review uses a five-cycle repair cap in substantial workflows and exits at first acceptance.
4. If the core passes, reconcile any authorized target movement and deliver the accepted candidate
   with exact-tip checks, then go to Stage 5: Deliver. If it fails and repair remains authorized,
   return to Stage 3: Build; otherwise go to Stage 5 with the blocker.

## Stage 5: Deliver

1. Report the runnable result or planning outcome first, with the run command and relevant checks.
   State required behavior still blocked, optional cuts and actual external-service/mock status.
2. Retain active work, owned worktrees, pool/handle identities, sessions, accepted SHAs and next
   actions while integration or follow-up remains. A saved notebook output is not submission state;
   inspect the live kernel before resuming. A wait timeout leaves the pool available.
3. Once work and continuation needs end, close the owned pool. Perform authorized workspace cleanup
   after accepted delivery, preserving dirty, unmerged and unrelated user work.
