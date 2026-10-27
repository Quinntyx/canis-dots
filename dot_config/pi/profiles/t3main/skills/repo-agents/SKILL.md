---
name: repo-agents
description: "Use when helping agents work a repository right by default - authoring or improving
  agent-facing repo guidance (AGENTS.md, internal decision docs, taste-encoding lint rules,
  verification ladders) - or when scaffolding a new repository with that agent-native foundation
  from the start."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Either: an existing repository where agents keep working and its observed failure modes, or a new
  repository to scaffold (language, test runner, build tooling, and intended domains).
- Access to the repo and authority over tracked files (docs, lint configs, scripts, CI definitions).
- The agent harness reality the guidance targets (harnesses that read AGENTS.md/CLAUDE.md-style
  files, run shell commands, and browse the repo's own tool surface).

## Output Contract

- An `AGENTS.md` that states environment safety, scope discipline, a verification ladder, and taste
  rules with reasons - opinionated defaults, not prose catalogs.
- A minimal docs tree (at least `docs/internals/`) holding only constraints the source cannot show.
- A lint-rule layer that converts each recurring agent mistake into a mechanical check with a
  prescriptive error message, each rule carrying its own test when the lint tool supports plugins.
- One named `check:changed`-style parity command documented as the pre-handoff definition of done.

# Entrypoint

## Stage 1: Choose the route

1. Improving an existing repo: survey first (Stage 2). Scaffolding a new repo: create the
   foundation alongside the initial code (Stage 6), then Stage 3 onward applies with lighter
   observation since failure history does not exist yet → calibrate from the domain's known
   pitfalls instead.
2. Both routes share Stage 3 through Stage 7.

## Stage 2: Survey and observe (existing repos)

1. Inspect the repo: package/build tooling, test runner, existing lint configuration, existing
   agent notes (`AGENTS.md`, `CLAUDE.md`, contributing guides), CI definitions.
2. Collect observed agent failure points from session records when available: wrong diagnoses,
   invented machinery, disallowed processes (pattern-matching kills, poll-waiting tests), missed
   surfaces, low-value comments. Each repeated failure is a guardrail candidate.
3. Rank candidates by recurrence times cost: a mistake that costs an hour of debugging every time
   outranks a style nit that a review comment fixes.

## Stage 3: Write AGENTS.md opinions

1. Cover, in this order: what the product must never regress (a short "what makes this special"
   section); a glossary so agents use shared vocabulary; the environment ways to hurt
   yourself (process handling, live databases, stateful directories, baked-in origins or
   environment URLs) as hard don'ts; a "hit every surface" checklist specific to this codebase
   (entry points, platforms, contracts, reverse states, deployment modes - whichever exist); the
   verification ladder (which commands, in which order, in what scope, and which full-suite runs
   belong to CI only); test-writing rules tied to observed failures; PR and evidence conventions;
   a Taste section for style-level defaults (dependencies, types, comments, state management).
2. Every rule needs a "because" a senior maintainer could defend. State that the developer's
   explicit preferences override anything in the document.
3. Point into docs/ for anything longer than a screenful; do not inline tutorials. Keep the final
   document shorter than a model's temptation to skim: dense rules, no narration.

## Stage 4: Docs tree

1. Create `docs/internals/` only when a constraint crosses components or hides in the source:
   architecture overview, testing rules summary, one trap page per class of expensive-to-discover
   platform quirk.
2. Documentation philosophy: no field catalogs, no narrated control flow, no appended change logs;
   rewrite or remove stale text when decisions change; a short nearby code comment beats an
   internal doc for local reasons. User-facing docs (when the repo has end users) stay task-shaped
   and in the shipped product's voice.

## Stage 5: Lint rules for decision points

1. For each recurring mistake, choose the enforcement vehicle: lint rule (mechanically
   detectable), test helper/fixture (structurally detectable), or AGENTS.md line (judgement call).
   Prefer lint when an error message can state the legitimate alternative.
2. Author in the repo's lint system. Standard shape for a pluggable linter: one file per rule, a
   prescriptive message naming the correct pattern, and a paired test with passing and failing
   fixtures.
3. Keep per-file budgets external: ship the allowances as a versioned JSON the rule reads; each new
   exception lands via a reasoned disable comment, never by silently inflating the budget.
4. Test each rule against at least one case typed after a real observed failure; record that
   failure in the rule's comment so the rationale survives maintainers.

## Stage 6: Scaffold the agent-native foundation (new repos)

1. Create alongside initial code: root `AGENTS.md` per Stage 3 (with env-safety and verification
   sections filled from actual commands, not aspiration); `docs/internals/overview.md` sketching
   the architecture and its non-negotiable boundaries; a lint config wired for custom rules.
2. Ship a `check:changed`-style script early: format + targeted lint + typecheck + tests-scoped-
   to-changed-files, mirroring what CI will run fast. Define the "never run unasked" full-suite
   commands from day one.
3. Seed the lint plugin with the domain's deadliest pitfalls even without failure history: the
   waiting/polling test rules, comment minimalism, dependency-additions-need-a-reason - the ones
   every agent-provided codebase drifts toward. Balance: fewer than ten first-day rules.
4. Provision evidence norms in the PR template or contributing guide: failing-test-first for
   logic, captures for visual, per-surface notes for frontend scope.

## Stage 7: Keep the guidance alive

1. When a merge or review reveals an agent-hit pitfall the docs missed, update AGENTS.md or the
   relevant internals page in the same PR rather than a housekeeping pass.
2. Prune: every layer stays shorter than what the source can answer. Periodically migrate prose
   rules into lint (prose-to-lint, not duplication) and delete the superseded prose.
3. Re-observe agent behavior after each guidance change; guidance that never changes is guidance
   nobody is using (or nobody is reading).
