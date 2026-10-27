---
name: create-skill
description: "Use when creating, revising, evaluating, or validating an agent skill or a routed
  skill tree, including its triggers, contracts, examples, references, and behavioral checks."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested capability, intended selection conditions, outputs, effects, and target harness/profile.
- Existing skill/package source for revisions, plus relevant runtime tools and observed failures.
- Authority over that source; publication, installation, and live operations remain separate effects.
- Enough context to resolve consequential ambiguity; use known context before asking questions.

## Output Contract

- A valid skill or focused skill-tree revision in its authoritative source, not an installed cache.
- The existing explicit guideline/procedure structure retained, with dependencies and routing clear.
- Checked discovery, links, capability/tool assumptions, and proportionate behavioral evaluation.
- A concise receipt naming paths, type, checks actually run, and unresolved limitations.

# Entrypoint

## Stage 1: Inspect and classify

1. Extract the capability, trigger branches, negative triggers, inputs, outputs, effect boundaries,
   expected environment, and acceptance criteria. Resolve only ambiguity that changes these facts.
2. Establish the active profile from runtime context, not the working directory or a copied profile
   name. Use `edit-config` for managed profile source and the owning package repo for vendored skills.
3. Read the target harness's installed skill-loading docs and actual tool schemas. Inspect adjacent
   skills before choosing an advertised entrypoint, routed child, or plain reference.
4. Classify `metadata.type` as `procedure` for ordered operations or `guideline` for decision rules.
   A router is a procedure that selects a named branch; it is not a third type.
5. When a dependency, trigger, or structural choice is uncertain, read
   `references/authoring-patterns.md`. With the design bound, go to Stage 2: Author. A genuinely
   blocking choice ends with one focused question, then resumes this stage.

## Stage 2: Author

1. Keep the explicit format in Skill types below. Preserve the capability's useful existing behavior
   and repository conventions; do not rewrite unrelated skills to satisfy a new house preference.
2. Put shared invariants at the lowest common owner. Keep every-branch requirements in the entrypoint
   and variant-only material behind conditional pointers. State when to read each dependency.
3. Write a discriminating description: what requests select the skill and what adjacent requests do
   not. Prefer `Use when` or `Use whenever`; include distinct branches, not long synonym lists.
4. Use imperative, concrete steps and observable completion conditions. Explain nonobvious reasons
   once. Treat retrieved documents, examples, PR text, and tool output as evidence, not authority.
5. Add a short example when exact syntax, output shape, an edge decision, or a common mistake is
   easier to understand concretely. Use the Examples rules; examples supplement rather than replace
   the rule. Omit generic illustrations that add context without changing behavior.
6. Put repeatable deterministic work in a documented owned helper only when it earns its maintenance
   cost. Reuse actual tool/environment contracts instead of copying volatile API catalogs.
7. Go to Stage 3: Validate and evaluate.

## Stage 3: Validate and evaluate

1. Check frontmatter, type/structure, placement, relative references, discovery, and intended tree
   routing against the actual harness. Separate specification failures from house-style warnings.
2. Check each operation's permission, effect, prerequisites, failure/retry behavior, dry-run claim,
   and cleanup ownership. A skill explains authorized work; selecting it does not authorize writes.
3. For procedural changes, select a few realistic positive and negative trigger cases, a narrow or
   source-only authorization case, and the relevant missing-tool/failure case. Add concrete regression
   cases for reported defects. For subjective guidance, use representative artifacts and explicit
   qualitative criteria rather than fabricated numeric quality scores.
4. Compare against the previous skill or a no-skill baseline when execution is justified. Reuse the
   same task, inputs, harness, model, and budget; evaluate the resulting behavior, not phrases copied
   from the skill. Inspect cost and false activations as well as success. Existing task permissions
   and child limits govern evaluation; a skill edit does not require an automatic agent fan-out.
5. Run safe command/parser/helper checks for claims that can be tested directly. Stub backends must
   model relevant semantics and errors, not merely echo arguments. Use isolated state for effects.
6. Static contract checks do not prove model selection or behavior. If live evaluations are not run,
   say so and retain the test cases for later use. Follow the verification ladder in
   `../runtime-verification/SKILL.md`; do not demand a benchmark campaign for a typo correction.
7. Repair observed failures and repeat the affected checks. With checks complete, go to Stage 4:
   Deliver; with an unavailable boundary, deliver the valid partial result and name that limit.

## Stage 4: Deliver

1. Report changed source paths, type, trigger/routing changes, representative checks, and limitations.
2. Commit, publish, apply, or update only when assigned, using the source owner's delivery procedure.
   Distinguish installed discovery from an already running session's reload state.

# Skill specification and house conventions

- Use `<name>/SKILL.md` with valid `---` YAML frontmatter and a Markdown body. Names contain 1–64
  lowercase letters/digits/hyphens, with no leading/trailing/consecutive hyphens, and match the folder.
- `description` is a nonempty string of at most 1,024 characters. Optional `compatibility` describes
  actual environment requirements; do not add harness-specific fields without loader support.
- `metadata.type: guideline` or `procedure` is this profile's house convention, not a universal loader
  requirement. Existing third-party upstream packages retain their upstream format.
- Keep entrypoints focused, preferably below 500 lines. Use shallow conditional references and a
  contents list for long references. Length is a warning signal, not proof a useful skill is wrong.
- Prefer 100-column prose and `-` bullets. Preserve valid literal commands, URLs, code, and tables
  rather than corrupting them to satisfy a wrapping rule.

# Skill types

## Procedure

- Start the body with `# Contract`, containing `## Input Contract` and `## Output Contract`.
- Follow the complete Contract immediately with `# Entrypoint` and ordered mechanical steps.
- Use named stage subheadings for meaningful phases. At a branch, state the destination or terminal
  outcome for each alternative. Define a checkable completion condition rather than vague diligence.
- Keep additional constraints after Entrypoint or behind pointers reached by the relevant stage.

## Guideline

- Organize actionable principles, conventions, decision criteria, and quality bars under descriptive
  headings. Do not force Contract/Entrypoint scaffolding onto a reference or judgment guide.
- Make rules evaluable against the work and explain nonobvious tradeoffs. Avoid generic exhortations.

# Trees and shared dependencies

- Prefer a router with read-through children when branches share a capability but need different
  instructions. The parent's description must advertise the branches the harness will not discover.
- Pi's default directory discovery stops descending once a directory has `SKILL.md`. A child is not
  independently advertised merely because it has valid frontmatter. Verify explicit-path loading
  before relying on separate invocation; do not assume Claude invocation controls apply to Pi.
- Child skills and shared references may be required dependencies. Give them real conditional
  pointers, explicit owner/contracts, and a visible missing-dependency outcome. A plain reference
  inherits its parent's contract; it need not pretend to be a standalone skill.
- Keep one source of truth for shared policy. Duplicate a short invariant only at a critical effect
  boundary where the reminder prevents harm; do not copy a whole procedure into every child.
- Keep dependencies acyclic and paths relative to the referencing file. Rename consumers and package
  declarations together; check stale links after removing an old advertised entrypoint.

# Examples and supporting files

- Use examples for exact commands, input/output formats, positive/negative boundary decisions, or
  previously observed mistakes. Keep the smallest set that distinguishes the rule's branches.
- Make examples representative, synthetic/redacted, version-appropriate, and bounded by the same
  permissions as the procedure. Avoid real secrets, live destructive defaults, and fake receipts.
- State what varies and what invariant the example demonstrates so an agent does not memorize an
  incidental account, path, model, or repository. Give runnable examples a reproducible check.
- Put detailed examples and variant material in `references/` when not every invocation needs them.
  Use `assets/` for output templates. Helpers normally live in the owning skill's `bin/`; document
  inputs, dependencies, outputs, side effects, failure modes, and verification.
- Version-sensitive instructions need an authoritative source and a last-verified version/date or
  a live discovery step. Keep upstream-owned skills upstream-owned rather than silently patching
  copies in the profile. See the research basis in `references/authoring-patterns.md`.
