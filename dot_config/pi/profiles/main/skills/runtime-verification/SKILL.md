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

- A reproduced failure and supported causal explanation, or an explicit reproduction limitation.
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
2. Give concurrent writers isolated worktrees and subsystem-level assignments when delegation
   materially helps. Keep the current repository's branch and publication policy in force.
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

# Design basis

- Claude Code's verification-first guidance grounds completion in an executable check:
  <https://code.claude.com/docs/en/best-practices>.
- Local session history repeatedly requests real hot-path checks, causal repairs, and lightweight
  smoke testing appropriate to exploratory work. Existing project checks remain authoritative.
