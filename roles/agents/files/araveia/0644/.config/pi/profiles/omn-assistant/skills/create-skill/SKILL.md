---
name: create-skill
description: "Use whenever a user asks to create, define, revise, or validate an agent skill."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A request to create, revise, or validate an agent skill.
- Enough information to determine the behavior that should trigger the skill and the behavior the
  skill should govern.
- The currently active Pi profile, supplied by the system prompt when Pi is the target harness.
- An explicit destination only when the user wants the skill outside the active Pi profile.
- Existing skill files when the request is a revision or validation rather than a new skill.
- Missing details may be inferred only when they do not materially change the skill's scope,
  contract, side effects, or artifact locations.

## Output Contract

- Produce a self-contained Agent Skills package whose required file is `<skill-name>/SKILL.md`.
- Place a Pi skill in the active profile's `skills` directory unless the user explicitly selects a
  different destination.
- Match the skill directory name to the frontmatter `name`.
- Add scripts, references, or assets only when they are necessary to execute or understand the
  skill.
- Report the final path, the selected skill type, and the validation result.
- Do not modify unrelated skills, profile files, or project files.

# Entrypoint

## Stage 1: Inspect and Classify

1. Read the request and identify the intended trigger, governed behavior, required inputs, expected
   outputs, side effects, artifact paths, environment constraints, and validation requirements.
2. Inspect the system prompt for the active Pi profile and use its `skills` directory as the default
   destination.
3. Classify the skill as `guideline` when it primarily states what to keep in mind while performing
   work, or as `procedure` when it defines how to complete work through ordered operations.
4. Determine whether the skill must branch, invoke tools, create artifacts, or include supporting
   files.
5. If the required information is complete, proceed to Stage 3: Author. Otherwise, proceed to
   Stage 2: Clarify.

## Stage 2: Clarify

1. Ask only for information whose absence would materially alter scope, safety, side effects,
   contracts, destination, or control flow.
2. Resolve each blocking ambiguity before writing files.
3. Once the required information is complete, proceed to Stage 3: Author.

## Stage 3: Author

1. Derive a concise, specification-compliant skill name and create the matching skill directory.
2. Write `SKILL.md` as raw Markdown with valid YAML frontmatter and a Markdown body.
3. Set `metadata.type` to exactly `guideline` or `procedure` according to the classification.
4. Write the description exclusively as a trigger statement beginning with `Use when` or
   `Use whenever`.
5. Structure the body according to the selected type and apply every rule in this skill.
6. Keep the skill self-contained and add supporting files only when progressive disclosure or
   executable automation materially improves the result.
7. Proceed to Stage 4: Validate.

## Stage 4: Validate

1. Validate frontmatter, naming, directory placement, Markdown structure, contracts, independence,
   list syntax, line length, and supporting-file references.
2. Confirm that no examples, sample scenarios, or domain-specific illustrations appear anywhere in
   the package.
3. Confirm that every line is at most 100 characters.
4. Confirm that the description communicates selection criteria rather than summarizing content.
5. Confirm that a procedure can be followed mechanically from its Entrypoint and contracts.
6. Confirm that a guideline skill communicates its constraints densely and unambiguously.
7. If any check fails, return to Stage 3: Author and correct every failure. Otherwise, proceed to
   Stage 5: Report.

## Stage 5: Report

1. Report the created or revised path.
2. Report whether the skill is tagged `guideline` or `procedure`.
3. Report whether validation passed and identify any unresolved limitation.

# Agent Skills Specification

- Treat every skill as raw Markdown stored in a directory containing `SKILL.md`.
- Begin `SKILL.md` with YAML frontmatter delimited by `---` lines.
- Include these required frontmatter fields:
  - `name`: a string from 1 through 64 characters.
  - `description`: a non-empty string from 1 through 1024 characters.
- Make `name` contain only lowercase ASCII letters, digits, and hyphens.
- Do not begin or end `name` with a hyphen or use consecutive hyphens.
- Make the `name` value exactly match the parent directory name.
- Tag every skill with a `metadata` map containing `type: guideline` or `type: procedure`.
- Keep every metadata key and value a string when adding metadata beyond the required type tag.
- Include `license` only when a license applies to the skill package.
- Include `compatibility` only for material environment requirements and keep it within 500
  characters.
- Include `allowed-tools` only when the target harness supports its experimental semantics.
- Keep `SKILL.md` below 500 lines and preferably below 5,000 tokens.
- Use paths relative to the skill root when referring to bundled files.
- Keep references shallow and load supporting material only when it is needed.

# Description Rules

- Write the frontmatter description as a quoted string beginning with `Use when` or `Use whenever`.
- State the conditions, requests, concepts, file types, systems, or operations that should trigger
  the skill.
- Optimize the description for skill selection because it is loaded before the body.
- Do not use the description as a literal summary of what the skill explains or contains.
- Keep the trigger broad enough to catch intended requests and narrow enough to avoid unrelated
  activation.
- Include discriminating keywords without turning the description into implementation guidance.

# Skill Types

## Guideline Skills

- Use `metadata.type: guideline`.
- Treat the body as constraints, principles, conventions, quality bars, and decision criteria that
  govern work.
- Organize the body under any number of descriptive headers and subheaders appropriate to the
  subject.
- Prefer dense technical statements that tell the agent what to preserve, avoid, verify, or choose.
- Do not force an Entrypoint or Contract structure onto a guideline skill unless the governed task
  independently requires those sections.
- Ensure each rule is actionable and specific enough to evaluate against the resulting work.

## Procedure Skills

- Use `metadata.type: procedure`.
- Make `# Contract` the first Markdown header after frontmatter.
- Place `## Input Contract` and `## Output Contract` under `# Contract`.
- State what information, files, state, permissions, or environment the procedure requires under
  `## Input Contract`.
- State what artifacts, state changes, messages, and destinations the procedure must produce under
  `## Output Contract`.
- Place `# Entrypoint` immediately after the complete Contract section.
- Use a numbered list under Entrypoint for concrete, ordered, mechanical operations.
- Include exact commands, paths, tool actions, checks, and transition conditions when they are
  needed for reliable execution.
- Divide branching behavior or phases into named stage subheaders under Entrypoint.
- At every branch, explicitly state which named stage follows when the condition is true and which
  named stage follows otherwise.
- Keep the main path direct enough that an agent can execute it without reconstructing intent.
- Add any number of guideline sections after Entrypoint when the procedure also needs behavioral
  constraints.

# Standalone Design

- Make every skill independently understandable and executable for its basic purpose.
- Do not require another skill to supply definitions, contracts, core rules, or mandatory steps.
- A skill may point to another skill only for optional depth on a distinct concern.
- Ensure that failure to load a referenced skill does not block the current skill's basic behavior.
- Duplicate essential rules rather than hiding necessary behavior behind cross-skill references.
- Keep scripts self-contained or document every dependency, input, output, side effect, and failure
  mode within the same skill package.

# Content and Formatting

- Do not include examples, sample inputs, sample outputs, demonstrations, illustrative scenarios, or
  domain-specific analogies.
- Replace examples with detailed, dense technical explanations of invariants, decisions,
  operations, edge conditions, and validation criteria.
- Use Markdown headers and subheaders to separate categories, phases, contracts, and concerns.
- Express enumerations of rules, facts, constraints, or items as unordered lists using `-` markers.
- Never use `*` as an unordered-list marker.
- Express ordered operations as numbered lists.
- Use alphabetical sub-bullets only when an ordered step requires subordinate ordering.
- Do not exceed two levels of nesting in ordered lists.
- Allow deeper unordered nesting only when it improves comprehension, with four or five levels as a
  soft maximum.
- Wrap every line at 100 characters, including frontmatter, prose, lists, and fenced content.
- Prefer concise headers, parallel bullet construction, explicit modal verbs, and testable wording.
- Remove generic introductions, repetition, motivational prose, and commentary that does not change
  agent behavior.

# Supporting Files

- Put executable automation in `scripts/` when repeated mechanical work warrants a script.
- Put detailed material in `references/` only when keeping it in `SKILL.md` would impair focused
  loading.
- Put static templates or other non-instructional resources in `assets/`.
- Reference supporting files with paths relative to the skill root.
- Keep each reference focused and avoid chains in which one reference requires another reference to
  explain basic content.
- Apply the no-examples rule, standalone requirement, Markdown structure, and 100-character wrapping
  rule to every textual supporting file.

# Validation Checklist

- The directory contains `SKILL.md` and its name matches the frontmatter `name`.
- The frontmatter satisfies all Agent Skills field constraints.
- The description is a selection trigger beginning with `Use when` or `Use whenever`.
- The `metadata.type` tag matches the body's actual structure and purpose.
- A guideline skill uses descriptive sections and actionable technical guidance.
- A procedure starts with Contract, follows it directly with Entrypoint, and provides mechanical
  ordered steps.
- Every branch names its destination stage explicitly.
- The package is self-contained for its basic behavior.
- Lists use the required marker and nesting conventions.
- No example or illustrative content remains.
- Every line is 100 characters or fewer.
- Every referenced file exists at the stated relative path.
- The final package is located in the active Pi profile unless the user selected another location.
