---
name: model-selection
description: "Use when selecting subagent models, assigning workflow roles, balancing cost and
  capability, escalating failed work, or composing heterogeneous implementations or reviews."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The assignment, acceptance criteria, consequences of error and known scope or uncertainty.
- Explicit model, inference variant, effort, budget, execution and diversity requirements.
- The selected agent profile, live model catalog and current availability or quota observations.
- Existing candidate assignments and review outcomes when comparing or escalating work.

## Output Contract

- A role, minimum capability tier, selected model and inference variant, and effort per assignment.
- A diversity plan containing eligible peer models, or an honest statement of limited diversity.
- A runtime-resolved model setting ready for Task construction, with its selected provider and
  the model choice and reason retained in the task ledger.
- A precise unavailable-model or capability blocker when the assignment cannot be staffed.

# Entrypoint

## Stage 1: Classify the assignment

1. Establish the requested result and its acceptance test. Classify the work by the role in Role
   defaults. Distinguish producing candidates, collecting evidence and deciding final acceptance.
2. Set the minimum tier from Capability tiers before considering preferred models or diversity.
   Complexity, uncertainty and consequences govern this floor independently of task size.
3. Preserve explicit model, inference variant and effort choices. A choice below the needed floor
   requires an explicit scope adjustment or capable acceptance path; surface the mismatch before
   assigning consequential authority. An explicitly requested identity remains exact.
4. Use the role defaults for workflow assignments or an explicit model-selection request. Simple
   delegation may inherit its selected profile's model when that identity meets the floor.
   Continue to Stage 2: Resolve eligible models.

## Stage 2: Resolve eligible models

1. Read Current model roster, Model identity and Provider resolution in this file. They are the
   single maintained source for model choices, variants, defaults, tiers and provider preference.
2. Query the installed pi_subagents catalog with list_models(refresh=True), model_slugs,
   best_model_match or resolve_models. Group equivalent entries by model and inference variant.
   Match explicit identities exactly and inspect configured access and actual availability.
3. For a Codex-family model, form its execution set exclusively from the actual project's admitted
   `cliproxyapi` entries under Codex execution requirement. A nonempty set continues at step 6.
   An empty set goes to Stage 5: Record with a project-access or quota blocker. Other models
   continue at step 4.
4. For other models, apply Provider resolution to the available entries. If GLM 5.3 Flash or
   DeepSeek V4.1 Flash is available only through Inco, go to Stage 2A: Resolve Inco-only access.
   Otherwise choose the first available ranked provider for that model and variant, then step 5.
   An empty execution set goes to Stage 5: Record with the unavailable identity.
5. Bind the exact model and variant to the selected entry, then continue at step 6.
6. Qualify the selected model against the tier floor, required tools and inputs, context, output
   and budget. With every prerequisite met, go to Stage 3: Compose the roster. Otherwise refresh
   availability once and inspect the unmet prerequisite. If restored, go to Stage 3: Compose the
   roster; otherwise go to Stage 5: Record with the concrete blocker.

## Stage 2A: Resolve Inco-only access

1. Bind the requested model, available Inco variant and projected run size or cost. Inco's fast
   inference is expensive; normal default and bulk assignments use the Sol substitution below.
2. If the user explicitly selected GLM 5.3 Flash or DeepSeek V4.1 Flash, continue at step 3.
   Otherwise continue at step 4.
3. Check for existing approval of the actual Inco variant and its cost. With that approval, bind
   the approved entry and go to Stage 2: Resolve eligible models at step 6. Otherwise warn that
   only Inco is available, identify the exact variant and its cost implications, and ask whether
   to continue. When only fast is available, state that explicitly. Go to Stage 5: Record with
   pending confirmation and an empty eligible execution set until the user answers.
4. Substitute GPT 6.1 Sol for this default assignment. Record the cost-motivated model promotion
   and recompose any peer set at a single suitable tier. Go to Stage 2: Resolve eligible models
   at step 3 with Sol selected, retaining the task requirements and budget.

## Stage 3: Compose the roster

1. Select one eligible model per requested assignment. For ordinary assignments, use the role
   default and continue at step 4. For competing implementations, exploratory alternatives or
   requested independent perspectives, continue at step 2 with the useful assignment count.
2. Form the peer set from a single tier meeting the floor. Choose the lowest suitable tier with
   enough eligible peers; a higher tier is appropriate only within the task's budget. Prefer
   distinct underlying models and, when qualified, different model families. Balance useful
   assignments across those models. Execution variants alone supply execution diversity rather
   than independent model perspectives.
3. Capability takes precedence over diversity. With only one qualified model, retain the tier and
   vary approaches or independent sessions; report reduced model diversity. An explicit demand
   for distinct models remains blocked until enough qualified peers exist or scope is revised.
   Separate exploratory evidence at a lower tier from the consequential decision at its own floor.
4. Use the role's effort default unless explicitly overridden. Resolve supported effort levels
   through the runtime; high is the normal deliberate-work setting. Maximum effort follows a
   genuinely difficult frontier assignment or explicit request.
5. Assign comparisons the same brief, baseline, evidence access and acceptance criteria. Keep
   independent writers in separate workspaces. A judge receives the resulting artifacts and
   actual tests; its floor follows the decision's stakes rather than the candidates' tier.
6. Record the resolved choices, then go to Stage 4: Observe and escalate.

## Stage 4: Observe and escalate

1. Launch only the roster authorized by the surrounding task. Model selection itself returns a
   plan; the owning workflow supplies AgentPool admission, resource ownership and acceptance.
2. Validate initial outputs with the real acceptance criteria. A focused worker's unsupported
   diagnosis is a hypothesis for independent verification. Record review failures by task.
3. After two unsuccessful repair reviews of a focused builder on the same requirement, promote
   that task to frontier engineering with its retained artifacts and observed failures. A changed
   model or inference variant uses a fresh session with explicit lineage. Broader review-loop caps
   remain owned by the surrounding workflow. Frontier-level scope raises the floor at once.
4. For unavailable models, recompute eligibility in Stage 2 using the actual failure. For
   authorized repairs return to Stage 3 with the revised floor. For accepted work or exhausted
   repair authority, go to Stage 5: Record.

## Stage 5: Record

1. Return the role, floor and selection outcome. A resolved choice includes its model, variant,
   tier, effort and reason, plus the runtime setting needed for launch. A blocked choice uses an
   empty eligible model set. Record its intended model and unmet prerequisite as diagnostic context.
2. Record peer models and diversity limits, explicit overrides, promotions and unresolved access
   requirements in the owning task ledger. A Codex project-quota blocker follows the Codex
   execution requirement while retaining the same project identity and capability floor.
3. Continue the surrounding workflow with resolved choices, or report the concrete blocking
   decision. Keep completed work and retained sessions available for their existing owner.

# Model identity

- The unit of selection is the underlying model and any behaviorally distinct inference variant.
  The same model and variant have the same capabilities, tier and role defaults on every provider.
- Preserve explicitly labeled fast variants as distinct execution choices. GLM-5.3-Flash:fast and
  DeepSeek-V4.1-Flash:fast retain their variant labels and require qualification for the assigned
  tier. A base-model selection and an explicitly requested fast variant are different choices.
- Base-model identity determines independent model perspectives. Repeated entries, sessions or
  execution variants of one underlying model remain one model for heterogeneous-model comparisons.

# Capability tiers

- Focused: bounded implementation with a clear local acceptance test; reproducible case diagnosis;
  evidence extraction; initial visual exploration; and intermediate, non-final critique. Limited
  scope and independently checkable results make throughput valuable.
- Frontier: substantial or uncertain engineering, architecture, cross-subsystem integration,
  subtle correctness/security review, skill authoring and final acceptance of consequential work.
  Independent verification remains necessary at this tier.
- These are task-routing floors calibrated to observed workflows, not benchmark ranks. Equivalent
  entries for a model and variant share a tier. Reasoning effort changes execution characteristics,
  not the model's tier. A distinct inference variant needs its own capability qualification.

# Current model roster

## Focused tier

- GLM 5.3 Flash: scoped implementation, bulk diagnosis and procedure testing.
- DeepSeek V4.1 Flash: exploratory peer candidates and bounded evidence or browser work.
- MiMo V2.6 Flash: an additional focused critique perspective when another viewpoint is useful and
  the model supports the required inputs.
- The named Inco fast variants of GLM 5.3 Flash and DeepSeek V4.1 Flash are distinct focused-tier
  execution choices, subject to Stage 2A's default Sol substitution and explicit cost approval.

## Frontier tier

- GPT 6.1 Sol: substantial engineering, architecture, authored procedures and consequential review.
- GPT 6 Astra has prior final code and visual review use. It is a frontier peer when available under
  the Codex execution requirement. At the last catalog check only Sol qualified for execution;
  refresh availability before claiming a second frontier model.

# Provider resolution

- Choose the model and inference variant for the assignment before resolving its provider. Provider
  choice retains that model's capability tier and role; provider names supply no model diversity.
- For non-Codex models, prefer OpenCode Go, then Bitdeer, then OpenRouter, then Inco among entries
  that are configured, accessible and available for the chosen model and variant.
- Current relevant catalog registrations are listed below. Refresh configured access and runtime
  availability when selecting; registration alone establishes neither credentials nor usable quota.
- OpenCode Go (`opencode-go`): GLM 5.3 Flash, DeepSeek V4.1 Flash and MiMo V2.6 Flash.
- Bitdeer (`bitdeer`): GLM 5.3 Flash.
- OpenRouter (`openrouter`): GLM 5.3 Flash, DeepSeek V4.1 Flash and MiMo V2.6 Flash.
- Inco (`inco`): GLM-5.3-Flash:fast and DeepSeek-V4.1-Flash:fast, distinct expensive fast variants.
- CLIProxyAPI (`cliproxyapi`): GPT 6.1 Sol, subject to the project's quota admission below.
- Inco-only GLM or DeepSeek access goes through Stage 2A. This separates ordinary model defaults
  from an expensive variant choice that needs explicit user confirmation for a named-model request.

# Codex execution requirement

- The complete eligible execution set for any Codex-family model is the actual project's admitted
  `cliproxyapi` entries, bound to its real directory and quota identity. This set replaces the
  non-Codex provider ranking. Direct `openai-codex` entries are obsolete in this setup.
- A nonempty admitted set permits execution. An empty set leaves the assignment blocked, including
  a Sol substitution from Stage 2A. Resolve the blocker through configured quota renewal or an
  approved project allocation change inside CLIProxyAPI, retaining the project identity and tier.
- Preserve this admission prerequisite throughout scheduling, continuation and escalation.

# Role defaults

- Scoped builder: GLM 5.3 Flash, high effort, for small self-contained changes with independently
  checkable acceptance. Promote repeated unsuccessful repairs through Stage 4.
- Case diagnostician and procedure tester: GLM 5.3 Flash, high effort. Root-cause claims receive
  the verification demanded by the surrounding workflow.
- Exploratory candidate: GLM 5.3 Flash and DeepSeek V4.1 Flash peers, high effort, for initial
  alternatives with concrete comparison criteria. Complex production candidates use the frontier
  floor and its eligible peer set instead.
- Evidence and browser worker: DeepSeek V4.1 Flash, high effort, for bounded retrieval, extraction
  or browser operations. Ambiguous causal synthesis and consequential conclusions raise the floor
  to frontier engineering rather than merely increasing output length.
- Frontier engineer: GPT 6.1 Sol, high effort, for substantial implementation, integration,
  architecture and authored procedures. Use xhigh for unusually difficult reasoning when supported
  and consistent with the task's budget or explicit request.
- Acceptance reviewer: GPT 6.1 Sol, high effort; use another qualified frontier model for an
  additional perspective. This role covers final correctness, root-cause validation and
  consequential
  visual acceptance. Focused critique remains useful evidence before this decision.

# Maintenance

- Update model identities, inference variants, tiers, effort and role defaults in this file
  together.
  Other subagent skills name roles or requirements and link here instead of repeating model names.
- A newly registered identity becomes a candidate after its capabilities and availability are
  established; release numbering alone supplies neither. Keep capability qualification specific
  to the model and variant.
- Model roles describe useful assignments already needed by the task, independently of whether
  the workflow needs additional agents or review stages.
