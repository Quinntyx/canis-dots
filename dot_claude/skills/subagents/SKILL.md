---
name: subagents
description: "Use when delegating, coordinating parallel work or selecting child models. Routes
  native Agent/review workflows versus T3-managed delegation, preserving model, workspace and effect
  boundaries rather than duplicating Claude's native child lifecycle."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested outcome, acceptance criteria and permitted effects.
- Supplied child counts, parallelism, models, settings and deadlines.
- Native Agent capability and/or T3 MCP access as required by the selected route.
- Verified repository/project binding and exclusive writer ownership where needed.

## Output Contract

- Verified results or a truthful partial outcome with retained resume identities.
- Separate native agent IDs and T3 taskIds, plus relevant revision/evidence records.
- No unassigned publication, installation, merge, new thread or workspace allocation.

# Runtime rules

- Native foreground `Agent` (`run_in_background:false` when exposed) owns in-turn children using
  this provider, an actually supported native model and no extra settings. Use its actual native
  result/join and cancellation controls; no T3 task identity or duplicate lifecycle is implied.
- Another provider, requested extra settings, a separate checkout, background work or an explicit
  `delegate_task` request uses T3 `delegate_task`. A missing managed route is a blocker, not a
  provider CLI, native worktree or shell-checkout fallback. Keep the parent's mode ceiling.
- For T3, call `orchestrator_capabilities` once before the first delegate; repeat only after an
  error or user-named provider change. Put supported settings in `target.options`. Report an
  unavailable named model/provider rather than substituting one.
- Use `Workflow` only when explicitly requested. A native skill does not grant extra authority.
- In T3, a batch uses managed delegates and the independent-implementation reference below.
  Native `/batch`'s automatic worktree/PR orchestration is not the execution route here: T3 owns
  allocation, while the user owns child limits and publication authority.

# Entrypoint

## Stage 1: Select the smallest useful shape

1. Bind outcome, effects and supplied limits. Distinguish total launches from live concurrency;
   reviews/retries count toward the user's cap. Decompose by acceptance outcome, not agent roles
   for their own sake. Give leaves no onward delegation unless explicitly bounded.
2. For model-selection-only work read `model-selection/SKILL.md` and return the plan. For execution,
   choose native Agent or T3 using Runtime rules. One assignment needs only lightweight delegation;
   dependent work remains blocked until its inputs are accepted.
3. Native `/code-review` may supply the review recipe when exposed and compatible with these routes
   and limits. Choose one review path, not native review plus an automatic duplicate T3 round.
   Comment publication and `--fix` remain effects distinct from read-only findings.
4. Continue to Stage 2 with a finite roster and clear acceptance criteria.

## Stage 2: Prepare

1. Check actual runtime, services, task inputs and baseline once. Read native tool schemas for the
   native route; use `references/runtime.md` and model-selection for T3 bindings/settings.
2. Give each child a self-contained brief, owned paths, permitted effects, relevant skill paths and
   a compact expected output. Keep large inputs/artifacts in files rather than pasted prompts.
3. T3 concurrent same-repo writers require the correct bound project and `isolation:'worktree'`;
   allocation starts at the coordinator's committed baseline. Read-only work can share. Explicitly
   prepared distinct repos can each have one exclusive writer with exact source-path ownership.
   A path in a brief does not bind a project, and allocation does not grant a PR or push.
4. Retain identities, limits and input/revision dependencies, then continue to Stage 3.

## Stage 3: Execute

1. Launch native children through Agent and complete their native join in this turn. Launch T3
   children through `delegate_task`, with a useful title/role and retained taskId. Use returned
   completion wakes/`next`; do not poll running delegates. A wait timeout leaves the child live.
2. For T3, read only the reference selected by the actual work shape; these references own its
   detailed mechanics rather than another generic native-Agent implementation:
   - One assignment: `references/delegation.md`.
   - Evidence research: `references/research.md`.
   - Independent/batch implementation: `references/independent-implementation.md`.
   - Dependent integration: `references/dependent-integration.md`.
   - Independent review: `references/review.md`.
3. Record each completion/failure once. Release accepted dependents; keep unrelated results usable.
   Infrastructure/credential failures remain explicit rather than becoming identical retry loops.
4. Continue to Stage 4 when results are ready, or Stage 5 for a start-only/blocked handoff.

## Stage 4: Verify

1. Check evidence, actual changed artifacts and the integrated revision; child summaries alone are
   not proof. Use `../runtime-verification/SKILL.md` and the repository's actual check floor.
2. Use one scoped independent review when needed/requested, not mandatory repeated rounds. Repair
   small findings directly. A new T3 review/re-check is a new `delegate_task`, within the launch cap.
3. Confirm scope and authorized effects. Accepted or budget-limited work goes to Stage 5; a useful
   bounded repair returns to Stage 3. Two failed repairs require renewed diagnosis, not repetition.

## Stage 5: Retain or finish

1. Retain result state, revisions, artifacts, branches/PRs and resume identities proportional to the
   work. Read `references/resumable-state.md` for uncertain side effects or dependent integration.
2. Cancel replaced/unneeded live T3 work with `task_cancel`, not top-level thread interruption.
   Completed task results remain readable; never poll an unfinished task for its final result.
3. Report verified outcomes, blockers and pending effects. Mention T3 children/threads using their
   returned links verbatim. Keep native Agent identities distinct from T3 taskIds.

# Focused entrypoints

`model-selection/SKILL.md` owns model choice, not execution permission. The conditional references
above inherit this skill's scope and runtime rules; they are not standalone advertised commands.
