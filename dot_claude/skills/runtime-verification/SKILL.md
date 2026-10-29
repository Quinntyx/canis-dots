---
name: runtime-verification
description: "Use when fixing bugs, reviewing runtime correctness, investigating repeated failures,
  or verifying code changes against real user flows."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A symptom, requested change, review target, or expected user-visible behavior.
- Repository or runtime context and the user's permitted effects.
- Available logs, reproduction inputs, running instances, and project validation commands.

## Output Contract

- Observed runtime behavior and supported causal explanations for identified defects, or an
  explicit execution limitation. A clean review records its actual coverage and findings.
- For authorized implementation, a focused repair verified against the original user flow.
- For review, actionable findings with affected paths, conditions, impact, and evidence.
- A concise final account separating observed behavior, inference, and remaining uncertainty.

# Entrypoint

## Stage 1: Establish the actual target

1. Read the request, local project instructions, current checkout state, and relevant prior
   findings.
2. Resolve the actual running build, branch, process, configuration, and entrypoint implicated by
   the symptom. Preserve existing user work and unrelated running instances.
3. Translate the request into observable user journeys and identify the smallest decisive check.
   Select a tier from Verification ladder using its concrete triggers, not model confidence or
   requested effort. Record the tier and trigger briefly; repository-required checks remain a floor.
4. When execution is available, continue to Stage 2: Reproduce. Otherwise, continue to Stage 3:
   Trace with the unavailable runtime explicitly recorded.

## Stage 2: Reproduce the user journey

1. Exercise the reported entrypoint with the relevant input and environment. Capture its result,
   logs, exit state, and elapsed time; use screenshots or traces when those expose the symptom.
2. Follow startup, first use, steady use, cancellation, and reconnect paths only where the request
   or observed failure makes them relevant.
3. Compare the observed result with the intended behavior. Record the reproduction command or
   interaction sequence and preserve the failing input. Continue to Stage 3: Trace.

## Stage 3: Trace the causal path

1. Follow the actual input through state transitions, process boundaries, asynchronous work, and
   persistence until the first divergence from the intended behavior.
2. Form a causal hypothesis and use a focused experiment, trace, or relevant source evidence to
   distinguish it from plausible alternatives. Reuse existing instrumentation where possible.
3. Review the changed path's callers, lifecycle, errors, cancellation, and shared-resource ownership
   according to the actual failure surface. Keep implementation decisions proportional to evidence.
4. When implementation is authorized and the cause is supported, continue to Stage 4: Repair.
   Otherwise, continue to Stage 6: Deliver with findings and unresolved uncertainty.

## Stage 4: Repair the cause

1. Modify the smallest coherent component that owns the incorrect behavior. Preserve the user's
   requested architecture and observable semantics across all affected callers.
2. When delegation materially helps, use the subagents procedure and T3-managed allocation for
   concurrent same-repo writers. Verify the bound repository before selecting worktree isolation.
   Keep branch, publication, and source/coordinator ownership within the actual request.
3. Add a focused regression check when it captures a durable failure mode. Prefer an existing
   test path and a small smoke check for exploratory work. Continue to Stage 5: Verify.

## Stage 5: Verify the repaired runtime

1. Run the decisive check against the repaired build, then repeat the original user journey.
2. Confirm the running process actually loaded the changed build and the relevant configuration.
3. Run the project's applicable checks and inspect the diff for unintended behavioral changes.
4. Use real process, browser, kernel, network, or GPU execution for claims that depend on that
   boundary. Identify the narrower coverage of isolated tests when the real boundary is unavailable.
5. When the original symptom is resolved and applicable checks pass, continue to Stage 6: Deliver.
   Otherwise, return to Stage 3: Trace with the new evidence.

## Stage 6: Deliver the result

1. Lead with the verified outcome or highest-impact finding. Include the causal explanation and
   evidence needed to trust it, with exact affected paths where useful.
2. State performed checks and coverage limits. Distinguish an implemented change from a deployed,
   restarted, visually inspected, or remotely verified result.
3. Report blockers and remaining decisions. A focused repair gets a short outcome-led paragraph
   covering cause, decisive verification, and remaining uncertainty. Save detailed trajectories in
   the task workspace when they materially help.

# Verification ladder

This is the shared default for verification cost. Specialist skills add relevant surface checks;
artifact-heavy specialist references are escalation routes, not a mandatory minimum for every task.
Higher tiers retain the decisive checks from lower tiers and expand only implicated boundaries.

## Tier 1: Focused

- Default for a bounded, understood change with a local acceptance path and no Tier 2/3 trigger.
- Inspect the owned diff, run the repository's applicable changed-file checks, and exercise the
  smallest real affected entrypoint. For a durable logic repair, prove the regression fails before
  and passes after when feasible. State unavailable runtime boundaries honestly.
- UI claims need rendered evidence when appearance is material; source/build success alone does
  not prove appearance. A small task needs the relevant capture, not a comparison campaign.
- Keep a short command/result and revision receipt. No compulsory manifest, checksums, timed stream,
  extra reviewer, CI provisioning, or multiple repair rounds merely to satisfy a generic ceremony.

## Tier 2: Boundary regression

- Escalate for changed public/API contracts; state/persistence or migrations; shared asynchronous,
  process, network, or privilege boundaries; security-sensitive effects; configuration installation;
  multiple interacting surfaces/platforms; uncertain ownership; or a regression with unclear scope.
- Inventory affected callers/surfaces, test the relevant happy and failure/lifecycle paths, and
  verify the real crossing plus one nearby unaffected path. For an installed update, bind source,
  selected ref, installed revision, effective configuration, and activation separately.
- Use an independent reviewer only for a consequential claim not settled by the available checks,
  or when requested/repository-required. One scoped review is the default, not a fixed loop count.
- If scope is initially unknown, begin with a short Tier 2 discovery pass. Remain here while any
  trigger is unresolved; return to Tier 1 only after explicitly ruling those triggers out.

## Tier 3: Forensic

- Escalate for two unsuccessful repairs of the same symptom, unexplained nondeterminism, races,
  timing/flicker/performance claims, contradictory runtime identity, or explicit forensic/replayable
  evidence requirements. A high reasoning-effort setting alone does not select this tier.
- Retain replayable inputs and the implicated timing/event/state trace. Use richer source/build
  manifests, hashes, terminal raw streams, profiling, or independent reconstruction only where
  they distinguish a hypothesis or establish provenance needed for the claim.
- Bound each experiment by a hypothesis and acceptance criterion. Stop expanding evidence when
  the symptom, affected boundaries, and causal claim are established. Repeated failed repairs call
  for renewed diagnosis, not repeated identical tests or automatic reviewer relaunches.
- Missing tools/access produce a precise blocked boundary. Never fabricate evidence, install an
  alternate automation stack, or broaden authority to make the tier appear complete.

# Browser evidence and permission

- Use T3 preview tools only when the current request asks for browser work or names a page/tab.
  A frontend edit or an evidence requirement is not by itself permission to use those tools.
- Otherwise use an already available repository-approved local capture/runtime facility within
  task scope. Do not install or switch automation systems merely to obtain a screenshot.
- Supplied captures can support a review of those artifacts. Do not label them fresh verification
  of a new build. If no permitted capture route exists, report visual verification as blocked.
- Use permitted semantic/runtime evidence for interaction claims and actual images for appearance;
  distinguish captured, inspected, deployed, and active-session states.

# Design basis

- Claude Code's verification-first guidance grounds completion in an executable check:
  <https://code.claude.com/docs/en/best-practices>.
- Local session history repeatedly requests real hot-path checks, causal repairs, and lightweight
  smoke testing appropriate to exploratory work. Existing project checks remain authoritative.
