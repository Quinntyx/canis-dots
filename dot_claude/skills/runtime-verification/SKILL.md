---
name: runtime-verification
description: "Use when fixing bugs, reviewing runtime correctness, or verifying real user flows.
  Supplies local evidence tiers and execution permissions around Claude's native /verify workflow."
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

## Stage 1: Bind the target and evidence budget

1. Read the request, repository instructions and existing run/verify guidance. Resolve the actual
   checkout, build, process, configuration and affected user journey; preserve unrelated work.
2. Select a tier below from its objective triggers. Record the tier, decisive check and permitted
   effects briefly. Repository checks remain a floor; browser permission remains a separate gate.
3. For investigation, retain a failing input and trace the first divergence before proposing a
   repair. A review stays read-only; an authorized repair changes the smallest owning component
   and adds a focused regression check when useful. Use `../subagents/SKILL.md` if delegating.
4. Continue to Stage 2 with the target, acceptance condition and execution boundaries bound.

## Stage 2: Use the native verification recipe

1. For a changed runtime surface, load native `/verify` through `Skill` when that built-in is
   exposed in the current session. Supply the target/revision, selected tier, existing project
   checks and permitted capture route. Native `/verify` owns the end-to-end exercise method;
   this skill owns its local evidence budget and permissions. Reuse its evidence rather than
   running a second generic verification workflow.
2. Keep any native run/verify-skill bootstrap within assigned repository-writing authority.
   Read-only or source-only work uses existing instructions/checks without generating new project
   guidance. A docs/test-only diff needs its applicable checks, not a fabricated runtime journey.
3. If the native recipe is absent or cannot honor those boundaries, exercise the smallest existing
   project entrypoint directly and record the limitation. No replacement plugin or capture stack
   is implied. Use actual process/network/GPU execution for claims dependent on that boundary.
4. Check the loaded build/configuration, original acceptance condition and applicable repository
   checks. A failed check returns to diagnosis, with experiments bounded by the ladder below;
   a passing or explicitly blocked check goes to Stage 3.

## Stage 3: Report the observed result

1. Lead with the verified outcome or actionable finding, cause and decisive evidence. Distinguish
   observed behavior from inference and retain reproduction commands or captures when useful.
2. Separate source changes, installation, restart, visual inspection and deployment. Name blocked
   boundaries and untested behavior; a native workflow's completion message is not proof by itself.

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
