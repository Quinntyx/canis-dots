# PR Description Review

## Behavior and causality

- Separate the observed failure, its trigger, its consequence, and the proposed cause.
- Describe a confirmed cause directly; qualify an inferred cause or omit it.
- Distinguish a pre-existing issue from a regression introduced by the compared change.
- Match the explanation to the scope of the implementation rather than claiming a pipeline-wide
  correction from a local change.
- Explain reliance on another subsystem when the fix leaves underlying erroneous behavior intact.
- Name actual code identifiers and errors instead of replacing them with vague labels.

## Coverage and limitations

- Compare the description against every behavior-changing hunk in the full diff.
- Distinguish a changed default, a changed failure path, and a new capability when they coexist.
- Separate independent fixes so readers can connect each failure to its corresponding change.
- State meaningful remaining limitations and assumptions without manufacturing a caveat.
- Keep scope statements about behavior; omit commentary about how the patch was organized.

## Structure and formatting

- A bug-fix body starts with `Currently, ` and explains the existing erroneous behavior.
- The next substantive paragraph starts with `This PR fixes` and explains the correction.
- Put headings and parallel-change bullets after those opening paragraphs when useful.
- Feature-only PRs start with `This PR` and describe the new capability and its purpose.
- Only the `Currently, ` block is optional for features; the `This PR` wording remains required.
- Mixed PRs retain the bug-fix opening and separate the feature discussion.
- Do not replace a readable heading or list with prose merely to match a rigid paragraph count.

## Publication prose

- Write change descriptions as complete sentences with explicit subjects, including bullet points.
- Statements about what the PR does use `This PR` followed by the verb, not subjectless fragments.
- Apply that sentence structure in paragraphs, bullets, and follow-up comments.
- Omit all validation, testing, verification, and PR-readiness sections and status claims.
- Omit successful-check counts, commands, CI summaries, and evidence-only bullets under any heading.
- Keep necessary checks in the engineering workflow, not in the PR description.
- Preserve facts that explain a failure or qualify a real behavioral limitation.
- Do not copy repository template validation prompts into the finished description.
- Follow-up comments must be self-contained and use the same structure and exclusions.
