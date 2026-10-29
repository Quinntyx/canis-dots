---
name: agent-repo-guidance
description: "Use when authoring or repairing a repository's AGENTS.md or CLAUDE.md, agent-facing
  internal guidance, changed-file verification ladder, or guardrails for repeated agent mistakes;
  also when explicitly scaffolding these foundations. Not for ordinary implementation or planning."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Existing repository and observed agent failure, or requested new-repository guidance foundation.
- Actual build/test/lint tooling, relevant agent/contribution documents, and authorized write scope.
- Target harness/runtime constraints and evidence of expensive-to-discover repository traps.

## Output Contract

- Focused agent operating guidance grounded in the real repository, with checked pointers and checks.
- Internal docs only for nonlocal decisions/traps that source and existing documents cannot explain.
- Mechanical enforcement only for a demonstrated, objectively detectable mistake worth maintaining.
- An actual available pre-handoff verification path, not promised lint infrastructure or commands.
- Clear source-only/delivery ownership and verification limitations; no automatic hosting or CI setup.

# Entrypoint

## Stage 1: Establish the repository and failure

1. Read applicable agent guidance completely, then relevant architecture/testing/domain docs and
   actual scripts/configuration. Preserve the repository's vocabulary and existing source of truth.
2. Identify the requested gap. For repeated failures, retain a concrete example and its cost; for a
   new repo, select only high-consequence facts known from its real stack and initial implementation.
3. Distinguish product requirements, architecture, execution state, and agent operating rules using
   `../project-plan/SKILL.md` when planning documents also change. Do not copy a product specification
   or task checklist into AGENTS.md merely to make it always loaded.
4. Rank candidate rules by recurrence, consequence, and detectability. With evidence go to Stage 2:
   Choose the owner; with a missing consequential decision, ask only that question or report it.

## Stage 2: Choose the owner

1. Use AGENTS.md for durable local operating knowledge: safety boundaries, conventions with reasons,
   required docs by task, implicated-surface checklists, and a concise real verification ladder.
2. Put cross-component architectural decisions or platform traps in an existing internal-docs tree,
   with a conditional pointer in AGENTS.md. Create a new docs directory only when such material exists.
3. Use a nearby comment for local rationale, a test/fixture for behavior, or a lint rule for a stable
   syntactically/structurally detectable constraint. Judgment remains guidance, not a heuristic linter
   that produces false certainty. Do not invent a custom lint plugin for a new repo by default.
4. Existing tool configuration is its own source of truth. Point to discoverable scripts/types rather
   than copying field catalogs or command output. With owners selected, go to Stage 3: Write.

## Stage 3: Write focused guidance

1. Update in place. Cover only applicable concerns: safe runtime/state directories and processes,
   unusual domain vocabulary, relevant platform/entrypoint/reverse-state surfaces, required evidence,
   and a few defensible taste constraints. Explain the nonobvious reason once.
2. Give each required doc a subject and condition for reading it. Keep AGENTS.md short enough to be
   read completely; disclose long detail without hiding an essential operation behind a vague link.
3. Name real changed-file commands and their scope. Reuse an existing command; add an orchestration
   script only if it genuinely composes useful existing checks. Do not claim global type checks or
   dependency-wide tests are file-scoped when the tool runs the entire project.
4. Define a small mandatory check floor, objective escalation triggers, and which expensive suites
   belong to CI. The shared `../runtime-verification/SKILL.md` ladder guides cost, while the repo's
   actual surface/evidence needs determine its local floor. Avoid copying a whole generic ladder.
5. State missing checks as proposed/blocked until implemented. Use the actual harness's worktree,
   browser, and process controls; do not transplant T3 commands or permissions into a different repo.
6. If mechanical enforcement is warranted, go to Stage 4: Enforce. Otherwise go to Stage 5: Verify.

## Stage 4: Enforce a demonstrated rule

1. Use the existing linter/test framework. Add the smallest enforcement vehicle with a diagnostic
   that names the valid alternative. Retain the observed failure as a test fixture or brief rationale.
2. Prove a real violating case fails and legitimate nearby cases pass. Test suppression/exception
   handling where supported; avoid broad syntax bans or unreasoned budget increases.
3. Keep one authoritative rule owner. A short AGENTS.md pointer to enforcement is useful; a second
   diverging copy of its complete implementation policy is not. Go to Stage 5: Verify.

## Stage 5: Verify and deliver

1. Read the document set together for contradictions, stale routes, invalid commands, and authority
   expansion. Check all newly referenced local files and run the actual documented focused checks.
2. Walk one representative task and one relevant negative/edge task through the guidance. Distinguish
   static walk-throughs from live agent evaluation; do not claim measured behavior from prose checks.
3. Report changes, rule rationale, checks actually run, and pending delivery. Commit/publish only
   when assigned. Future observed failures update the relevant owner, not an accumulating changelog.

# Design basis

- T3 Code's AGENTS.md and task-shaped repository skills demonstrate local safety, scoped verification,
  conditional internal-doc pointers, truthful evidence, and source-backed conventions. Their commands
  and product-specific restrictions are not templates to copy verbatim into unrelated repositories.
- `../create-skill/references/authoring-patterns.md` records the Anthropic/Matt Pocock/T3 research
  behind progressive disclosure, trigger quality, examples, and behavioral rather than textual tests.
