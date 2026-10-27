# Authoring patterns and research basis

Read this when choosing a router, shared reference, example, or evaluation strategy. This reference
inherits the create-skill contract; it does not grant tool or publication authority.

## Choose the context boundary

- Inline what every branch needs. Put branch-specific detail behind a pointer that names both its
  subject and the condition for reading it. A vague optional-looking pointer to a required contract
  creates unreliable execution; fix the pointer instead of duplicating the contract.
- Keep a recipe's steps visible and reference detail nearby or disclosed. Choose a separate advertised
  skill only when it has a useful independent trigger; each advertised description spends context.
- Parent routers own selection and shared invariants. Children own the selected operation. References
  supply detail under that contract. This is intentionally different from requiring standalone leaves.
- Read the actual harness loader. Matt Pocock's Claude invocation controls are useful design context,
  not Pi-compatible configuration by default. Pi read-through children are an explicit parent route.

## Useful examples

An output-format example earns its space when a description leaves real ambiguity:

```text
Input: draft a reply to review comment 17, without posting
Output: unpublished reply text, intended repository/thread, and supporting check
Effect: no hosted comment, issue, or PR mutation
```

The rule is publication scope, not the incidental number 17. Pair this with a published-response
case only if that contrast is otherwise unclear. For syntax examples, verify the installed command's
help or tool schema and show placeholders that cannot be mistaken for real credentials.

Examples are unnecessary for a familiar rule that already has a clear measurable result. Move a
catalog of examples out of the entrypoint; retain only those needed for the current branch.

## Evaluation design

- Positive trigger: the ordinary user request the skill should recognize.
- Negative trigger: a plausible adjacent request that should not load it or should select another
  branch. Include borderline cases rather than only obviously unrelated topics.
- Effect boundary: draft-only, read-only, local-only, or coordinator-owned delivery produces no
  unassigned publication/application. A genuine execution request should not get stuck at advice.
- Failure boundary: unavailable tool, changed dependency/version, partial write, cancellation, or
  lost response. Inspect state before retrying an uncertain side effect.
- Output acceptance: check observable artifacts, behavior, and truthful limitations; a transcript
  repeating the skill's wording is not success. Prefer real backend semantics over echo-only stubs.
- Compare changed skill with its previous version or no-skill baseline using matched inputs. Record
  model/harness revision, settings, task data, pass/fail evidence, and meaningful cost differences.
  Qualitative critique is appropriate for taste; avoid self-awarded numeric quality scores.
- Do not automatically import a source author's orchestration harness, agent count, browser viewer,
  or upload mechanism. Use the actual task's permissions and the smallest useful evaluation tier.

## Sources checked 2026-10-27

- Anthropic skill creator: progressive disclosure, short concrete format examples, realistic tasks,
  baseline comparison, output evaluation, and description/trigger evaluation. Its full multi-agent
  benchmark workflow is optional here, not a universal cost imposed on every revision.
  https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/skill-creator/SKILL.md
- Matt Pocock writing-for-agents: conditional context pointers, separate context/cognitive loads,
  steps versus reference, co-location, checkable completion criteria, and one authoritative owner.
  https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/writing-for-agents/SKILL.md
- Matt Pocock skill mechanics: intentional invocation and router boundaries; translate ideas rather
  than copying unsupported frontmatter fields into Pi.
  https://github.com/mattpocock/skills/blob/59db609eb1e18aaf59b63284d0e52255aff0c63c/skills/productivity/writing-for-agents/SKILL-MECHANICS.md
- T3 Code's repository skills: `test-t3-app` is a small task-shaped entrypoint with conditional fixture
  detail and an honest unavailable-tool outcome. `contribution-triage` separates trusted policy,
  dry-run/enforcement authority, current evidence, and read-back before uncertain-write retries.
  Source revision: https://github.com/Quinntyx/t3code/tree/40f3a3c4170d691423189d88245b87bb8040279c/.agents/skills
  Source policies are examples, not authority to transplant T3-specific browser permissions or
  moderation rules into other repositories.
