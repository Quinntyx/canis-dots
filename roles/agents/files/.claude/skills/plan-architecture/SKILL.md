---
name: plan-architecture
description: "Interactive architecture planning: resolve consequential ambiguity, inspect repository impact and produce a durable plan and ROADMAP.md."
argument-hint: "[plan request]"
disable-model-invocation: true
metadata:
  type: procedure
---

# Contract

## Input Contract

- Planning request: $ARGUMENTS, existing repository/docs and allowed planning artifacts.
- No implementation, publication or deployment authority unless separately assigned.

## Output Contract

- A coherent architecture/behavior contract and durable ROADMAP.md grounded in the current system.
- Decisions, alternatives, risks, verification and milestones traceable to the user's answers.

# Entrypoint

1. Read `../project-plan/SKILL.md`, repository guidance and relevant architecture/testing docs.
   Inspect real source before claiming how the current system works. Preserve existing document
   roles and conventions; agent operating guidance belongs to `agent-repo-guidance` instead.
2. Group consequential open questions and ask through the available native interaction surface or
   concise chat. Keep a dated Q&A record with decisions/rationale. Proceed on established facts;
   do not invent authority or turn every implementation detail into a blocking question.
3. Define goals/non-goals, actors, inputs/outputs, behavior flow, invariants, failure handling,
   interfaces, state/data ownership, compatibility and security. Compare meaningful alternatives,
   record the selected design and its reasoning, and identify the actual repo impact.
4. If source inspection benefits from delegation, follow `../subagents/SKILL.md` with bounded
   questions and evidence locators. Native foreground Agent or T3 routing replaces the obsolete
   scout type; do not prescribe a fake agent, another provider or automatic parallel roster.
5. Inspect existing tests and specify changed behavior's verification at the correct objective tier.
   Split ROADMAP.md into dependency-ordered, independently checkable milestones with scope,
   acceptance evidence and remaining risks. Keep architecture and roadmap consistent.
6. Review flow/invariants/interfaces/milestones for contradictions and missing prerequisites. Save
   only authorized planning artifacts. Report decisions, paths and unresolved questions; execute
   implementation only if the user assigned that effect separately.
