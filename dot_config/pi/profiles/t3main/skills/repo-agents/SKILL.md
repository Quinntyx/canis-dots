---
name: repo-agents
description: "Use when creating or improving agent-facing guidance for a repository - AGENTS.md
  conventions, internal decision docs, custom lint rules that encode taste, and verification
  ladders - so coding agents build in that repo right by default. Use t3code's setup as the
  reference model."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A repository where agents (pi/T3 hijos or other harnesses) repeatedly work, its language and test
  runner, and observed agent failure modes when known.
- Access to the repo and permission to add or change tracked files (docs, lint configs, scripts).
- Optionall a reference: the t3code checkout at `~/docs/src/t3code/main` is the canonical worked
  example of every layer below.

## Output Contract

- An `AGENTS.md` that states environment safety, scope discipline, a verification ladder, and taste
  rules with reasons - opinionated defaults, not prose catalogs.
- A minimal docs tree (at least `docs/internals/`) holding only constraints the source cannot show.
- Repetitive agent mistakes converted into lint rules with prescriptive error messages, each with a
  passing/failing test when the repo's lint tool supports plugins.
- A named parity command (`check`-for-changed) documented as the pre-handoff definition of done.

# Entrypoint

## Stage 1: Survey and observe

1. Inspect the repo: package/build tooling, test runner, existing lint configuration, existing
   `AGENTS.md`/`CLAUDE.md`/`README` agent notes, and CI.
2. Collect observed agent failure points from session records when available: wrong diagnoses,
   invented machinery, disallowed processes (pattern-killing, poll-waiting tests), missed surfaces,
   low-value comments. Each repeated failure is a candidate guardrail.
3. Compare against the t3code reference (`~/docs/src/t3code/main/AGENTS.md`, `docs/internals/`,
   `oxlint-plugin-t3code/`): which of its layers would have prevented each observed failure here?

## Stage 2: Write AGENTS.md opinions

1. Cover, in this order: what makes the product special and must not regress; a glossary so agents
   use shared vocabulary; the ways this repo's environment can be hurt (process handling, live
   databases, stateful dirs, origin baking) as hard don'ts; the "hit every surface" checklist
   specific to this codebase; the verification ladder (which commands, in which order, in what
   scope, and which full-suite runs belong to CI only); test-writing rules tied to the failures you
   observed; PR/evidence conventions; a Taste section for style-level defaults (dependencies,
   types, comments, state management).
2. Prefer defaults and reasons over checklists of everything: each rule needs a "because" a senior
   maintainer could defend. Agent preferences override anything here, stated in the document.
3. Point into docs/ for anything longer than a screenful; do not inline full tutorials.

## Stage 3: Docs tree

1. Create `docs/internals/` only when a constraint crosses components or hides in the source:
   architecture overview, testing rules summary, domain-specific trap pages (one page per class of
   expensive-to-discover platform quirk).
2. Apply t3code's documentation philosophy verbatim: no field catalogs, no narrated control flow,
   no appended change logs; rewrite or delete stale text when decisions change; a short nearby
   code comment beats an internal doc for local reasons. Keep `docs/user/` (when the repo has end
   users) task-shaped and in the product's voice.

## Stage 4: Lint rules for decision points

1. For each recurring agent mistake, decide the enforcement vehicle: lint rule (mechanically
   detectable), test helper/fixture (structurally detectable), or AGENTS.md line (judgement call).
   Prefer lint when an error message can state the legitimate alternative.
2. Write the rule in the repo's existing lint system. For an oxlint-based repo, follow the shape of
   `/home/henry/docs/src/t3code/main/oxlint-plugin-t3code/rules/*`: one file per rule, prescriptive
   message naming the correct pattern, paired `*.test.ts` with passing and failing fixtures.
3. Keep per-file budgets (like t3code's `react-effect-budget`) external to the rule: shipped as JSON
   the rule reads, each new exception added via a reasoned disable comment, never by inflating the
   budget silently.
4. Test the rule against at least one case typed after a real observed failure; link that failure
   in the rule's comment.

## Stage 5: Verification ladder and CI parity

1. Define the fast loop: targeted tests + focused typecheck + scoped lint, then one
   `check:changed`-style command that mirrors CI's fast checks on changed files only.
2. Name the "never run unasked" full-suite commands explicitly so agents defer them to CI.
3. Document visual-proof versus test-proof routing: logic failures to failing-first tests, layout
  -only defects to before/after captures, and where integrated device verification (if any) fits.
4. Hand this stage's commands as one block agents can copy-paste; keep it stable across months.

## Stage 6: Keep the guidance alive

1. When a merge or review reveals an agent-hit pitfall the docs missed, update AGENTS.md or the
   relevant internals page in the same PR rather than delaying to a housekeeping pass.
2. Prune: every layer above must stay shorter than what the source can answer. Periodically delete
   rules whose lint now enforces them (prose-to-lint migration, not duplication).

# Reference model

- The t3code checkout at `~/docs/src/t3code/main` demonstrates every stage above implemented in
  full: AGENTS.md with enforced opinions, a 30-page internals tree, ~30 behavioral lint rules with
  tests, external effect budgets, `vp`-based verification ladder with hard CI boundaries. Read its
  current files before authoring a new repo's set; they are the calibration anchor.
