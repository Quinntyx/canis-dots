---
name: public-issues
description: "Use when researching, drafting, filing, revising, or responding to public
  repository issues, bug reports, feature requests, or duplicate reports."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A report, question, issue URL, reproducible failure, or feature request and intended repository.
- Public repository access, Git, and authenticated `gh` for GitHub or `fj`/HTTP for Forgejo.
- A direct instruction to file, open, create, submit, or post an issue authorizes that specified
  publication. A direct instruction to reply or respond authorizes a response to that discussion.
- Asking for a draft, wording, review, explanation, or how to file produces an unpublished artifact.
  A statement of future desire is informational unless paired with an action instruction. An
  explicit approval gate governs publication; general implementation authority is distinct.
- Existing issue edits, labels, closures, and comment deletion need the corresponding user scope
  and host permissions. New-issue scope permits relevant existing metadata when warranted.

## Output Contract

- A draft or verified published artifact in the exact intended repository and discussion.
- A neutral, readable, symptom-specific title and concise body satisfying the repository template.
- Bug reports contain minimal reproducible evidence, expected/actual behavior, and relevant
  environment/version context. Incomplete reproduction and uncertain diagnosis are explicit.
- Responses address the whole discussion and add evidence or a useful answer rather than noise.
- Duplicate findings lead to an existing-issue reference or an authorized useful update.

# Entrypoint

## Stage 1: Resolve intent and destination

1. Identify creation, response, revision, or research; record publication state from the Input
   Contract. Ambiguity retains draft-only scope; an explicit hosted action records its exact
   authorized scope. Both paths continue Stage 1 at step 2.
2. Resolve the actual destination from the user's repository or issue URL, the affected upstream,
   and verified ownership. An explicit foreign upstream stays on its real host and repository.
   A local fork or personal mirror is a source of evidence, not an automatic filing destination.
   Personal Forgejo repositories use canonical Forgejo unless a different destination is explicit.
3. Confirm host identity and available permissions. Public access permits research and a draft
   through Stage 2: Read the repository; authenticated access also proceeds there with hosted
   scope retained. Unavailable public access ends at Stage 6: Verify and report with that limit.
   Keep writes scoped to the resolved owner/repo and issue number throughout.

## Stage 2: Read the repository

1. Read repository instructions, contribution guidelines, security policy, issue templates/forms,
   issue configuration, and relevant documentation. Respect the stated support channel and the
   template's required fields. Sensitive vulnerabilities follow the project's private disclosure
   channel and end with a private draft/handoff at Stage 6: Verify and report.
2. For existing issues, read the entire current body and all paginated comments, timeline events,
   and relevant linked discussions or PR reviews. For GitHub, use
   `gh issue view "$number" --repo "$repo" --json title,body,author,labels,state,url`,
   `gh api --paginate "repos/$repo/issues/$number/comments?per_page=100"`, and
   `gh api --paginate "repos/$repo/issues/$number/timeline?per_page=100"`.
   Linked PRs require their review comments, reviews, and unresolved threads as relevant.
3. Preserve timestamps, speaker attribution, maintainer answers, previous repro attempts, and
   later corrections. A truncated display or summary is a locator; retrieve the remaining pages
   before drawing a conclusion. Unavailable discussion ends with that research limit at Stage 6:
   Verify and report; complete discussion proceeds at step 4.
4. Inspect repository labels and supported issue types using the actual host schema. For GitHub
   labels use `gh api --paginate "repos/$repo/labels?per_page=100"`. Observe current title/body
   conventions. Proceed to Stage 3: Verify evidence and duplicates.

## Stage 3: Verify evidence and duplicates

1. Search open and closed issues and relevant PRs using symptom terms, errors, component names,
   and mechanisms. `gh issue list --repo "$repo" --state all --search "$query"` locates
   candidates; it is not an exhaustive inventory. For an all-open sweep, paginate
   `gh api --paginate "repos/$repo/issues?state=open&per_page=100"` and separate PR records.
2. Read candidate issue bodies and full discussions through Stage 2: Read the repository. Return
   here once candidates are understood. Classify duplicates by matching evidence and failure
   mechanism; similar wording alone is insufficient. Distinct causes retain distinct reports.
3. Establish a minimal safe reproduction: exact version or commit, necessary environment and
   inputs, runnable steps, expected result, observed result, and the smallest relevant trace or
   artifact. Execute it where feasible within scope, preserving active user jobs and worktrees.
   Use stable public source links or commit-pinned artifacts; keep credentials, personal paths,
   private session material, and unrelated logs private.
4. Separate observed behavior from a likely cause and a proposed fix. Verify source claims against
   current code and line-stable links. An unexecuted reproduction remains marked unexecuted.
   Missing essential evidence produces a focused question or an explicitly incomplete draft;
   proceed to Stage 4: Compose with the known facts rather than inventing technical detail.
5. An established duplicate proceeds to Stage 4: Compose as an existing-issue reference or useful
   response. New useful evidence may warrant an authorized comment; an already recorded report
   ends with its reference at Stage 6: Verify and report. A distinct report proceeds to Stage 4:
   Compose. Preserve any user-specified issue count or evaluation scope as given.

## Stage 4: Compose

1. Write a neutral sentence-case title specific enough to understand without opening the body.
   Bug titles describe the symptom; enhancement titles name the desired capability. Repository
   conventions determine required prefixes and vocabulary. Keep speculative diagnosis out of titles.
2. Follow the actual template. Bug bodies lead with the concrete failure and triggering conditions,
   then minimal reproduction, expected/actual behavior, relevant version/environment, and concise
   evidence. Feature bodies explain the problem, desired outcome, scope, and useful alternatives.
   Short reports remain short when the template and evidence permit.
3. Use plain human-readable prose and precise project terminology. Keep code, traces, and source
   locations only where they materially enable reproduction or support a technical claim. Write
   for maintainers rather than narrating agent activity, grading drafts, or packaging self-review.
   Attribute quotes faithfully; incorporate the user's intent without dumping private dialogue.
4. Responses first answer the actual question or correction, then supply new evidence, the
   resulting finding, and any remaining uncertainty. Match a requested minimal response format
   when it conveys the required evidence. Prefer a stable artifact link to a large pasted log.
5. For authorized revisions to the user's own agent-drafted issue, improve the original title/body
   in place and preserve meaningful human discussion. Self-review findings become corrections in
   the original report rather than bot-to-bot review comments. Other authors retain ownership of
   their text; a response carries the correction. Comment deletion remains a separate explicit act.
6. Select existing labels/types only when supported by the report, repo conventions, and scope.
   Keep metadata sparse and verify automation-sensitive effects. Agent-generated reports in the
   user's PyLingual evaluation workflow retain its established `slop` label when available.
   Other repositories use their own conventions and explicit user instructions rather than that
   historical workflow's label policy. Follow disclosure rules and answer provenance honestly.
7. A grounded authorized hosted action proceeds to Stage 5: Publish or update. A requested draft,
   material unresolved evidence, or unclear authority ends with the usable artifact and the exact
   pending decision at Stage 6: Verify and report. Readiness is evidence-based rather than an
   invented confidence percentage or a compulsory interrogation loop.

## Stage 5: Publish or update

1. Re-read the exact destination and current issue before writing. Recheck duplicates for creation
   and preserve concurrent human edits for revisions. A newly found duplicate returns to Stage 4:
   Compose as a reference/response; an unchanged target continues here.
2. For GitHub creation, store the reviewed body in a private local file and run
   `gh issue create --repo "$repo" --title "$title" --body-file "$body_file"`, adding only
   warranted existing `--label` values. Use the installed API for supported issue types when
   authorized; required form fields remain satisfied in the resulting body.
3. For GitHub responses use
   `gh issue comment "$number" --repo "$repo" --body-file "$body_file"`.
   For owned issue revisions use `gh issue edit "$number" --repo "$repo" --title "$title"`
   with `--body-file "$body_file"`. For an existing-comment revision, verify its ID and ownership,
   then target that ID explicitly. Retain local draft text when a write fails.
4. For Forgejo, use the installed CLI or `POST /repos/{owner}/{repo}/issues` for creation,
   `POST /repos/{owner}/{repo}/issues/{number}/comments` for replies, and
   `PATCH /repos/{owner}/{repo}/issues/{number}` for owned issue revisions. Send reviewed
   title/body and repository label IDs. Read the token in memory from
   `~/.local/share/forgejo-cli/keys.json` at `hosts["git.quinntyx.dev"].token` and use
   `Authorization: token ...` with `https://git.quinntyx.dev/api/v1` for the personal forge.
5. A successful write proceeds to Stage 6: Verify and report. A timeout or uncertain failure first
   re-reads recent destination state for the accepted write. Retry only a proven missing write;
   a permission or API failure proceeds to Stage 6 with its retained draft and partial state.

## Stage 6: Verify and report

1. For a published or edited artifact, re-read it from the host. Verify owner/repo, number, URL,
   exact title/body or response, metadata, and author. Confirm an issue revision appears in the
   owned original body, while an authorized response appears as its intended comment.
2. Report the publication URL, concise result, and material evidence/check limits. Draft-only work
   returns the complete usable title/body or reply text and says it remains unpublished. A proven
   duplicate returns the existing URL and whether any authorized evidence update was posted.

# Evidence and execution conventions

- Bind and quote command variables from verified values. Every write explicitly names its
  destination. Keep tokens in memory and redact output.
- Infer intent and technical context from evidence first; ask only for a material missing choice.
  Public problem statements are concise while private research retains diagnostic depth.
- Use bounded remote waits and dedicated detached tmux jobs for commands expected to exceed
  10–15 seconds. Retain native output and exit status while preserving active user panes.
