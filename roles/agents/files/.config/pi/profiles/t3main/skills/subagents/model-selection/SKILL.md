---
name: model-selection
description: "Use when selecting subagent models, assigning child roles, balancing cost and
  capability, escalating failed work, or composing heterogeneous implementations or reviews."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The assignment, acceptance criteria, consequences of error and known scope or uncertainty.
- Explicit model, inference variant, effort, budget, execution and diversity requirements.
- The `orchestrator_capabilities` listing for this thread and current availability observations.
- Existing candidate assignments and review outcomes when comparing or escalating work.

## Output Contract

- A role, minimum capability tier, selected model and inference variant, and effort per assignment.
- A diversity plan containing eligible peer models, or an honest statement of limited diversity.
- A resolved `target` (model plus options) ready for `delegate_task`, with the model choice and
  reason retained in the task record.
- A precise unavailable-model or capability blocker when the assignment cannot be staffed.

# Entrypoint

## Stage 1: Classify the assignment

1. Establish the requested result and its acceptance test. Classify the work by the role in Role
   defaults — the T3 `delegate_task` `role` values (`implementation`, `research`, `review`,
   `design`, `test`, `general`) name the routing; this policy selects model and effort on top.
2. Distinguish producing candidates, collecting evidence and deciding final acceptance.
3. Set the minimum capability tier before considering preferred models or diversity. Complexity,
   uncertainty, and consequences govern this floor independently of task size. Select verification
   cost separately through `../../runtime-verification/SKILL.md`; a strong model or high effort
   neither removes required checks nor mandates forensic artifacts.
4. Preserve explicit model, variant and effort choices. A choice below the needed floor requires an
   explicit scope adjustment or capable acceptance path; surface the mismatch before assigning
   consequential authority. An explicitly requested identity is used exactly as requested, or the
   mismatch is reported.
5. Simple delegation may inherit this thread's model when it meets the floor. Otherwise continue
   to Stage 2: Resolve eligible models.

## Stage 2: Resolve eligible models

1. Read `orchestrator_capabilities`: providers, models each offers, supported options (such as
   effort) and runtime modes. That listing is the live catalog for this thread. Call it once per
   thread; call again only after an error or a user-named provider change.
2. Group equivalent catalog entries by underlying model and inference variant. Match explicit
   identities exactly against the listing; prefer the Current model roster's tier mapping when an
   identity is recognized, and treat unrecognized families conservatively.
3. Choose the provider for the chosen model and variant. When this thread's own provider offers the
   chosen model and no user setting requires otherwise, prefer it: a child under the same
   provider/model with no extra settings may also run through the native child mechanism instead
   of `delegate_task`. A named provider must appear in the listing to be used.
4. If no provider offers the needed identity, and no peer at the required tier offers a qualified
   substitute, go to Stage 5: Record with the unavailable-identity blocker. Do not silently
   downgrade or change provider unasked.
5. Qualify the selected model against the tier floor, required tools and inputs, context, output
   and budget. With every prerequisite met, go to Stage 3: Compose the roster. Otherwise inspect
   the unmet prerequisite once; if genuinely unmet, go to Stage 5: Record with the concrete
   blocker.

## Stage 3: Compose the roster

1. Select one eligible model per requested child. For ordinary assignments, use the role default
   and continue at step 3. For competing implementations, exploratory alternatives or requested
   independent perspectives, continue at step 2 with the useful child count.
2. Form the peer set from a single tier meeting the floor. Choose the lowest suitable tier with
   enough eligible peers; a higher tier is appropriate only within the task's budget. Prefer
   distinct underlying models and, when qualified, different model families. Balance useful
   assignments across those models. Different providers for the same model supply execution
   diversity rather than independent model perspectives.
3. Capability takes precedence over diversity. With only one qualified model, retain the tier and
   vary approaches or independent children; report reduced model diversity. An explicit demand for
   distinct models remains blocked until enough qualified peers exist or scope is revised.
   Separate exploratory evidence at a lower tier from the consequential decision at its own floor.
4. Use the role's effort default unless explicitly overridden. Resolve supported effort levels
   through the `orchestrator_capabilities` option listing; pass them in `target.options` (for
   example `{effort:'max'}`), which override inherited values. High is the normal deliberate-work
   setting.
5. Assign comparisons the same brief, baseline, evidence access and acceptance criteria. Keep
   independent writers in separate `isolation: 'worktree'` children. A judge receives the resulting
   artifacts and actual tests; its floor follows the decision's stakes rather than the candidates'
   tier.
6. Record the resolved choices, then go to Stage 4: Observe and escalate.

## Stage 4: Observe and escalate

1. Launch only the roster authorized by the surrounding task. Model selection itself returns a
   plan; the owning workflow supplies launches, workspace authority and acceptance.
2. Validate initial outputs with the real acceptance criteria. A focused child's unsupported
   diagnosis is a hypothesis for independent verification. Record review failures by task id.
3. After two unsuccessful repair reviews of a focused builder on the same requirement, promote
   that task to frontier engineering with its retained branch/worktree and observed failures. A
   changed model or variant launches a fresh child whose brief states the prior lineage. Broader
   review-loop caps remain owned by the surrounding workflow. Frontier-level scope raises the
   floor at once.
4. For an unavailable selected model/provider, report the actual failure and prepare alternatives
   without launching a substitute unasked. User-authorized selection changes return to Stage 2.
   Authorized repairs retain explicit model choices and return to Stage 3; accepted work or
   exhausted authority goes to Stage 5: Record.

## Stage 5: Record

1. Return the role, floor and selection outcome. A resolved choice includes its model, variant,
   tier, effort and reason, plus the `target` needed for launch. A blocked choice uses an empty
   eligible model set; record its intended model and unmet prerequisite as diagnostic context.
2. Record peer models and diversity limits, explicit overrides, promotions and unresolved access
   requirements in the owning task record.
3. Continue the surrounding workflow with resolved choices, or report the concrete blocking
   decision.

# Model identity

- The unit of selection is the underlying model and any behaviorally distinct inference variant.
  The same model and variant have the same capabilities, tier and role defaults on every provider.
- Preserve explicitly labeled fast or free variants as distinct execution choices. A base-model
  selection and an explicitly requested variant are different choices.
- Base-model identity determines independent model perspectives. Repeated entries, sessions or
  different providers for one underlying model remain one model for heterogeneous-model
  comparisons.

# Capability tiers

- Focused: bounded implementation with a clear local acceptance test; reproducible case diagnosis;
  evidence extraction; initial visual exploration; and intermediate, non-final critique. Limited
  scope and independently checkable results make throughput valuable.
- Frontier: substantial or uncertain engineering, architecture, cross-subsystem integration,
  subtle correctness/security review, skill authoring and final acceptance of consequential work.
  Independent verification remains necessary at this tier.
- These are task-routing floors calibrated to observed workflows, not benchmark ranks. Equivalent
  entries for a model and variant share a tier. Reasoning-effort options change execution
  characteristics, not the model's tier.

# Current model roster

- Maintained personal routing preference, reviewed 2026-10-27; not an independently measured
  benchmark ranking or a guarantee of capability on every task. Revise from observed acceptance
  outcomes, not model names alone. The live truth for availability is
  `orchestrator_capabilities`; a mapped identity absent from the listing is treated as
  unavailable, and an unmapped family is qualified conservatively before use at a tier.
- Focused tier: GLM 5.3 Flash, DeepSeek V4.1 Flash, MiMo V2.6 Flash when listed.
- Frontier tier: GPT 6.1 Sol and equivalent frontier engineering models when listed.
- When this thread inherits a capable default (a focused-tier model such as DeepSeek V4.1 Flash),
  simple delegation inherits it. Promotion to the frontier tier needs the frontier
  roster or an explicit user choice.

# Role defaults

- Scoped builder (`implementation`): focused-tier model, high effort, for small self-contained
  changes with independently checkable acceptance. Promote repeated unsuccessful repairs through
  Stage 4.
- Case diagnostician and procedure tester: focused-tier model, high effort. Root-cause claims
  receive the verification demanded by the surrounding workflow.
- Exploratory candidate: two focused-tier peers, high effort, for initial alternatives with
  concrete comparison criteria.
- Evidence and browser worker (`research`): focused-tier model, high effort, for bounded retrieval,
  extraction or browser operations. Ambiguous causal synthesis raises the floor to frontier.
- Frontier engineer (`implementation` at frontier tier): frontier model, high effort, for
  substantial implementation, integration, architecture and authored procedures. Use the maximum
  supported effort only for genuinely difficult reasoning or explicit request.
- Acceptance reviewer (`review`): frontier model, high effort; another qualified frontier model
  supplies an additional perspective. Focused critique remains useful evidence before this
  decision.

# Maintenance

- Update model identities, variants, tiers, effort and role defaults in this file together. Other
  subagent skills name roles or requirements and link here instead of repeating model names.
- A newly listed identity becomes a candidate after its capabilities are established; catalog
  appearance alone supplies neither. Keep capability qualification specific to the model and
  variant.
