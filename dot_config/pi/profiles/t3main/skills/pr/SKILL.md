---
name: pr
description: "Use when opening or drafting a pull request, revising a PR title or description,
  responding to PR review feedback, or splitting work into PRs."
disable-model-invocation: true
metadata:
  type: guideline
---

# Pull Request Writing

## Gather the change

- Read the full diff and relevant commit history, not just commit messages or a file summary.
- Identify the actual failure, trigger, consequence, and cause before drafting a bug-fix PR.
- Ask for missing operational context when it materially changes the explanation.
- Use the repository's exact identifiers, instruction names, errors, and system vocabulary.
  Search with `rg`; do not invent substitute terminology.
- Account for every material behavior change, including defaults, flags, and control flow.
- Classify the change as a bug fix, new feature, or a mixture before choosing the opening.

## Bug-fix descriptions

- Begin the body with a substantive paragraph starting literally with `Currently, `.
- Explain the current erroneous behavior, when it occurs, and its consequence. Include the
  mechanism when established; distinguish observed failures from inferred causes.
- Follow it with a substantive paragraph starting literally with `This PR fixes`.
- Explain what changes and how those changes address the erroneous behavior.
- Keep these opening paragraphs in order, before any headings or bullet lists.
- For multiple bugs, explain additional failures and fixes in separate paragraphs or sections.
- For mixed bug-fix and feature PRs, use the bug-fix opening and describe the feature separately.

## New-feature descriptions

- A `Currently, ` paragraph is not required for a new feature without a corrected defect.
- Begin the body with a substantive paragraph starting literally with `This PR`.
- Explain the new capability and its purpose, then the material behavior changes.
- The feature exception removes only the `Currently, ` paragraph, not the `This PR` wording.
- Do not manufacture erroneous prior behavior merely to reuse the bug-fix structure.

## Formatting and scope

- Write change descriptions as complete sentences with explicit subjects, including bullet points.
- When a statement describes what the PR does, use `This PR` followed by the verb.
  Do not substitute a subjectless verb fragment in paragraphs, bullets, or follow-up comments.
- Markdown headings and bullet points are welcome when they improve readability.
- Use bullets for parallel changes and headings to distinguish substantive concerns.
- Do not force prose-only descriptions or impose a fixed paragraph count.
- Keep descriptions concise without omitting the failure mechanism or meaningful behavior changes.
- Explain limitations, unresolved behavior, and assumptions when they genuinely apply.
- Do not force a limitations section onto a complete fix or invent future work to fill a template.
- Separate prevention of a failure from correction of its underlying behavior when they differ.
- Hedge or remove unverified claims; do not assert semantic equivalence or absence of behavior
  changes without support.
- Exclude PR-process commentary about why changes share a PR, how agents worked, or why the
  patch avoided unrelated files, helpers, tests, or other work.

## Prohibited validation clutter

- Never include a Validation, Testing, Verification, or equivalent results section in a PR body.
- Do not include test commands, test counts, passing-test claims, CI status, successful lint or
  diff checks, or verification-only evidence bullets anywhere in the description.
- Do not say that the change passes tests, has been validated, or is PR-ready.
- Perform the necessary checks before publication; PR readiness already implies those checks.
  Keep their status out of the PR description rather than moving it under another heading.
- Remove validation prompts or checklists inherited from repository PR templates.
- A factual description of a failure or a qualification of a real limitation is still appropriate;
  it must explain behavior, not advertise successful checks.
- Apply the same exclusions to unsolicited follow-up comments. If a reviewer explicitly requests
  evidence, answer that request separately without adding boilerplate to the PR description.

## Titles

- Use a plain, concise descriptive sentence naming the concrete symptom or new capability.
- Include version or scope context only when it helps identify the change.
- Do not use conventional-commit prefixes or turn the title into a full explanation.

## Follow-up comments

- When review feedback leads to new commits on an open PR, leave a self-contained timeline comment
  explaining the defect and change, with commit references and relevant remaining limitations.
- Use the same bug-fix or feature structure, vocabulary, certainty, and formatting rules as bodies.
- Do not assume access to another conversation or refer to surrounding discussion.
- Use the authenticated hosting CLI. If Forgejo comment posting cannot resolve the repository,
  use `POST /repos/{owner}/{repo}/issues/{number}/comments`; edit through
  `PATCH /repos/{owner}/{repo}/issues/comments/{id}` with the normal credential mechanism.
- Never disclose credentials or place them in the description or comment.

## Review before publication

- Confirm bug-fix descriptions start with `Currently, ` followed by `This PR fixes`.
- Confirm feature-only descriptions begin with `This PR` without requiring `Currently, `.
- Confirm feature-only descriptions do not invent a defect.
- Confirm statements about what the PR does use `This PR`, not subjectless verb fragments.
- Confirm the full diff is represented using concrete, repository-specific terminology.
- Confirm meaningful limitations are stated and unsupported claims are hedged or removed.
- Confirm useful headings and bullets remain, with no validation section or status claims.
- Confirm the body contains no PR-process commentary and the title names the concrete change.
- Confirm the intended PR and target repository before creating or editing remote content.
- Additional description review guidance is in `references/PR_EXAMPLES.md`.
