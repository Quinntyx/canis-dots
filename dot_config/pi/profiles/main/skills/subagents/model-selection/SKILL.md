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
- Explicit model, provider, effort, budget and diversity requirements from the current request.
- The selected agent profile, live model catalog, provider access and current quota observations.
- Existing candidate assignments and review outcomes when comparing or escalating work.

## Output Contract

- A role, minimum capability tier, one exact provider/model slug and effort per assignment.
- A diversity plan containing eligible peers, or an honest statement of limited diversity.
- Model choices ready for Task construction, with selection reasons retained in the task ledger.
- A precise unavailable-model or capability blocker when the required assignment cannot be staffed.

# Entrypoint

## Stage 1: Classify the assignment

1. Establish the requested result and its acceptance test. Classify the work by the role in Role
   defaults. Distinguish producing candidates, collecting evidence and deciding final acceptance.
2. Set the minimum tier from Capability tiers before considering preferred models or diversity.
   Complexity, uncertainty and consequences govern this floor independently of task size.
3. Preserve explicit model, provider and effort choices. A choice below the needed floor requires
   an explicit scope adjustment or capable acceptance path; surface the mismatch before assigning
   consequential authority. An explicitly requested model remains exact rather than a fuzzy alias.
4. Select role routing for a workflow, an explicit model-selection request or authorized model
   choice. A simple delegation with no role-routing context inherits its selected profile when
   that model meets the floor. Continue to Stage 2: Resolve eligible models.

## Stage 2: Resolve eligible models

1. Read the Current model roster in this file. This is the single maintained source for concrete
   model identities, provider preferences, role defaults, tiers and effort defaults.
2. Query the installed pi_subagents catalog with list_models(refresh=True), model_slugs,
   best_model_match or resolve_models. Bind exact provider/model slugs for the selected agentDir.
   Catalog registration establishes identity and advertised modalities; configured provider access
   and actual runtime errors establish whether the route is usable.
3. Establish each identity's required provider scope first. Codex-family assignments require
   CLIProxyAPI project-quota admission with the actual project's directory and quota identity.
   The frontier roster's eligible routes are admitted cliproxyapi entries. When the project's
   admitted set is empty, go to Stage 5: Record with the project quota blocker. Other identities use
   their roster routes. Within that scope filter by tier floor, tools, modalities, context, output,
   access and current quota. The eligible set contains only routes satisfying every prerequisite.
4. Choose the role default within that eligible set. An alternate transport qualifies only within
   the required provider scope from step 3. A stronger model qualifies only if its route meets the
   same project/provider requirements and budget. An empty eligible set goes to Stage 5: Record
   with the unavailable route and required in-scope access or quota decision.
5. With eligible models, go to Stage 3: Compose the roster. Without one, refresh the catalog once
   and inspect the actual prerequisite. If still unavailable, go to Stage 5: Record with a blocker
   and the required configured-route, credential or quota decision.

## Stage 3: Compose the roster

1. Bind one exact route per requested assignment; keep alternate routes in selection reasoning.
   For ordinary assignments, bind the selected role default and continue at step 4. For competing
   implementations, exploratory design variants or requested independent model perspectives,
   continue at step 2 with the requested useful assignment count.
2. Form the peer set from a single tier meeting the floor. Choose the lowest suitable tier with
   enough eligible peers; a higher tier is appropriate only within the task's budget. Prefer
   distinct underlying models and, when qualified, different model families. Provider aliases
   of one model count as one identity. Balance useful assignments across eligible identities.
3. Capability takes precedence over diversity. With only one qualified identity, retain the tier
   and vary approaches or independent sessions; report reduced model diversity. An explicit demand
   for distinct models remains blocked until enough qualified peers exist or scope is revised.
   Separate exploratory evidence at a lower tier from the consequential decision at its own floor.
4. Use the role's effort default unless explicitly overridden. Resolve supported effort levels
   through the selected runtime/provider; high is the normal deliberate-work setting. Maximum
   effort follows a genuinely difficult frontier assignment or explicit request.
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
   that task to frontier engineering with its retained artifacts and observed failures. New model
   identity uses a fresh session with explicit lineage. Broader review-loop caps remain owned by
   the surrounding workflow. An earlier discovery of frontier-level scope raises the floor at once.
4. For unavailable routes, recompute eligibility in Stage 2 using the actual provider/quota error
   and the same required project/provider scope. An exhausted eligible set goes to Stage 5 with
   its blocker. For authorized repairs return to Stage 3 with the revised floor. For accepted work
   or exhausted repair authority, go to Stage 5: Record.

## Stage 5: Record

1. Return the role, floor and selection outcome. A resolved choice includes its eligible exact
   slug, tier, effort and reason. A blocked choice uses an empty eligible model set, with the intended
   identity and unmet prerequisite recorded separately as diagnostic context.
2. Record peer identities and diversity limits, explicit overrides, provider failures, promotions
   and unresolved access requirements in the owning task ledger. Resolve a project-quota blocker
   by awaiting its configured renewal or obtaining an approved project allocation change inside
   CLIProxyAPI. Keep the same project identity and capability requirement in the proposed next step.
3. Continue the surrounding workflow with resolved choices, or report the concrete blocking
   decision. Keep completed work and retained sessions available for their existing owner.

# Capability tiers

- Focused: bounded implementation with a clear local acceptance test; reproducible case diagnosis;
  evidence extraction; initial visual exploration; and intermediate, non-final critique. Limited
  scope and independently checkable results make throughput valuable.
- Frontier: substantial or uncertain engineering, architecture, cross-subsystem integration,
  subtle correctness/security review, skill authoring and final acceptance of consequential work.
  Independent verification remains necessary at this tier.
- These are task-routing floors calibrated to the user's observed workflows, not benchmark ranks.
  A model keeps its listed tier across providers. Reasoning effort and provider speed change its
  execution characteristics, not its capability tier. New identities need explicit placement here.

# Current model roster

## Focused tier

- GLM 5.3 Flash: opencode-go/glm-5.3-flash is the bulk diagnosis and procedure-testing route.
  bitdeer/zai-org/GLM-5.3-Flash is the preferred scoped-builder route. Other configured routes
  for the same identity are inco/glm-5.3-flash:fast and opencode/glm-5.3-flash.
- DeepSeek V4.1 Flash: opencode-go/deepseek-v4.1-flash is the exploratory peer route.
  inco/deepseek-v4.1-flash:fast is preferred for latency-sensitive browser/evidence work when
  usable. Actual tool latency, prefill cost and turn count determine measured speed.
- MiMo V2.6 Flash: opencode-go/mimo-v2.6-flash is an additional focused critique perspective.
  Use it when an extra independent viewpoint is useful and the live route supports the inputs.

## Frontier tier

- GPT 6.1 Sol: cliproxyapi/gpt-6.1-sol is the substantial-engineering and consequential-review
  route. CLIProxyAPI supplies project-scoped quota admission; retain the task's real project
  context throughout scheduling, continuation and any approved escalation.
- GPT 6 Astra has prior final code and visual review use. It becomes an eligible frontier peer
  only when cliproxyapi/gpt-6-astra is configured and usable in the live catalog. At this policy
  revision that proxy route is absent, so frontier work currently has one qualified identity.
  Retain Sol and report limited model diversity until another frontier peer is qualified here.

# Role defaults

- Scoped builder: focused GLM through the scoped-builder route, high effort. Small, self-contained
  changes use this role when their acceptance can be independently checked. Promote repeated
  unsuccessful repairs through Stage 4.
- Case diagnostician and procedure tester: focused GLM through the bulk route, high effort.
  Root-cause claims receive the verification demanded by the surrounding workflow.
- Exploratory candidate: focused GLM and DeepSeek peers, high effort, for initial alternative
  designs or implementations with concrete comparison criteria. Complex production candidates
  use the frontier floor and its peer set instead.
- Evidence and browser worker: focused DeepSeek through the latency route, high effort, for
  bounded retrieval, extraction or browser operations. Ambiguous causal synthesis and consequential
  conclusions raise the floor to frontier engineering rather than merely increasing output length.
- Frontier engineer: frontier Sol, high effort, for substantial implementation, integration,
  architecture and authored procedures. Use xhigh for unusually difficult reasoning when supported
  and consistent with the task's budget or explicit request.
- Acceptance reviewer: frontier Sol, high effort; use a configured, qualified frontier peer for
  an additional model perspective. Use this role for final correctness, root-cause validation and
  consequential visual acceptance. Focused critique remains useful evidence before this decision.

# Maintenance

- Update identities, provider preferences, tiers, effort and role defaults in this file together.
  Other subagent skills name roles or requirements and link here instead of repeating model IDs.
- Treat substitutions as task-calibrated choices. A newly registered name becomes a candidate only
  after its capabilities and usable route are established; release numbering alone supplies neither.
- Keep routing proportional: model roles describe useful assignments already needed by the task,
  independently of whether the workflow needs additional agents or review stages.
