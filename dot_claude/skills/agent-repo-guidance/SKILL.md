---
name: agent-repo-guidance
description: "Use when creating or repairing AGENTS.md/CLAUDE.md, repository agent guidance,
  verification ladders or recurring-mistake guardrails. Adds repository-specific policy to native
  /init; not for ordinary implementation or product planning."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Existing repository, requested guidance foundation or observed agent failure.
- Actual agent/contribution docs, architecture/testing notes and project commands.
- Authority over the target source and any requested mechanical enforcement.

## Output Contract

- Focused guidance grounded in this repository, with working pointers and real verification steps.
- One authoritative owner per rule; tests/lint only for demonstrated, objectively detectable cases.
- Honest coverage and delivery status; no automatic CI, hosting or generic lint infrastructure.

# Entrypoint

## Stage 1: Resolve the owner and native starting point

1. Read existing AGENTS.md/CLAUDE.md and relevant internal docs completely. Inspect the actual stack,
   scripts and failure example. Preserve established vocabulary and unrelated user work.
2. Resolve managed-source ownership with `../edit-config/SKILL.md` when applicable. For an explicitly
   requested new CLAUDE.md, use native `/init` through `Skill` when exposed and its destination and
   writing effects match the assignment. It owns the initial codebase survey/draft, not a second
   independent generation pass. Existing guidance repairs update in place.
3. Without a compatible native `/init`, draft from the inspected repository and name that boundary.
   Read-only/draft-only work produces findings or an unpublished draft, not a generated repo file.
4. Separate product plans from operating rules with `../project-plan/SKILL.md` when needed, then
   continue to Stage 2.

## Stage 2: Curate the repository-specific delta

1. Keep durable operating knowledge in the existing AGENTS.md/CLAUDE.md authority: unusual domain
   vocabulary, safety/state boundaries, docs to read by task, consequential taste rules and actual
   changed-file checks. Explain nonobvious reasons; omit facts easily rediscovered from source.
2. Put cross-component architecture/traps in existing internal docs with conditional pointers;
   keep local rationale in comments and behavior in tests. A requested scaffold need not invent a
   docs tree. Keep one owner instead of copying the same policy into several files.
3. Use the project's real command names, fixtures and surface checklists. Select the evidence cost
   from `../runtime-verification/SKILL.md`; repository requirements remain a floor. Name expensive
   CI checks separately rather than presenting whole-project tests as file-scoped commands.
4. For a repeated, mechanically detectable mistake, use the existing test/lint framework and prove
   a violating case fails while legitimate neighboring cases pass. Judgment stays guidance.
   Missing checks are proposals until implemented; a native draft does not authorize enforcement.
5. Review any native draft against these constraints, then continue to Stage 3.

## Stage 3: Verify and hand off

1. Read the resulting document set together for contradictions, stale paths, copied tool catalogs
   and unintended authority. Check new links and run the actual focused commands it recommends.
2. Walk a representative task plus a relevant negative/effect-boundary case through the guidance.
   Distinguish a static walk-through from live agent evaluation.
3. Report changed paths, rationale, checks and pending effects. Use the source owner's publication
   procedure only when assigned. Future failures update their existing rule owner, not a changelog.
