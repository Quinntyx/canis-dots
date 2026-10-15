---
name: pr
description: "Use when drafting, opening, revising, or splitting pull requests, or responding
  to PR review feedback with commits, descriptions, or comments."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A requested PR action, repository or PR URL, source branch/diff, and relevant task context.
- Git and authenticated `gh` for GitHub or `fj`/Forgejo API access for Forgejo.
- A direct request to open/create a PR authorizes that PR publication. A request to draft or write
  PR text produces an unpublished draft; opening a draft PR is an explicit hosted operation.
- A direct request to reply authorizes that response. Implementing a change alone authorizes
  neither PR creation nor review-comment publication. Merge scope is a separate decision.

## Output Contract

- A concise, problem-first title/body grounded in the complete diff, verification, and limitations.
- An explicit destination repository, source/head, base, draft state, and publication result.
- Authorized review follow-ups update the PR timeline with the finding, change, commit references,
  relevant checks, and remaining limitations, understandable without the private Pi conversation.

# Entrypoint

## Stage 1: Resolve destination and authority

1. Resolve and record the requested artifact and publication state. Draft-only and ambiguous
   scope retain an unpublished artifact for Stage 5: Verify and report. An explicit hosted
   instruction records its exact scope for Stage 4: Publish or revise. Continue Stage 1 at step 2.
2. Inspect remotes, checked-out branch, worktrees, repository owner, and the specified PR URL.
   An explicit destination governs. Personal Forgejo repositories use Forgejo for PRs; GitHub
   mirror URLs remain mirrors. Foreign upstream contributions target the genuine upstream's host
   and repository, using the personal fork as head when required. Verify the PR base repository
   independently of the local `origin` to prevent accidentally targeting a fork or mirror.
3. For personal feature work, use `feat-<dash-delimited-description>` branches based on `dev` and
   target PRs explicitly to `dev`. Branch-base and PR-target overrides are independent. A required
   missing `dev` ends with a target decision. Foreign repositories follow their actual contributor
   workflow and branches. Explicit user targets take precedence after repository verification.
4. Read contribution instructions, PR templates, existing PR state, and every review thread and
   timeline page. For GitHub use paginated issue comments, pull review comments, reviews, and
   GraphQL review threads as needed; a short summary is a locator rather than the full discussion.
   Proceed to Stage 2: Inspect the change.

## Stage 2: Inspect the change

1. Inspect the full base-to-head diff, not only commit subjects. Use
   `git diff "$base...$head"`, the relevant commits, and repository terms from scoped `rg`.
   Account for all behavior changes, flags, defaults, signature changes, and control flow.
2. Establish the real failure mode or motivation from task evidence, discussion, and observed
   behavior. Infer only what the evidence supports. A material missing user-intent detail requires
   one focused question before resuming Stage 2; otherwise continue here.
3. Run the smallest relevant checks for the change and inspect the actual results. Separate
   observed behavior, inferred mechanism, assumptions, and unverified claims. Preserve existing
   unrelated edits and runtime jobs.
4. For requested review fixes, use the authorized checkout or a separate sibling worktree named
   after its branch. Existing `dev` permits task commits and ordinary pushes. Other task branches
   need authorization for commits/pushes. Retain chezmoi's existing `main` source-state checkout
   and its assigned configuration lifecycle. Merges into `main` require explicit authorization.
5. Once evidence and checks are sufficient, proceed to Stage 3: Write the artifact. Check failures
   remain explicit findings; they are repaired within scope or reported as unresolved.

## Stage 3: Write the artifact

1. Follow the repository template and exact vocabulary. Write a plain sentence-case title naming
   the concrete symptom or result. Use type prefixes only where repository convention requires.
2. Lead the body with what breaks, when, and why it matters. Follow with the mechanism and scope,
   then verification and meaningful limitations or assumptions. Keep it short, usually two to four
   paragraphs; parallel changes may use bullets. Preserve required template sections.
3. State partial behavior and unverified claims accurately. Claims of semantic equivalence or
   unchanged behavior require evidence. Keep explanations about the change rather than private
   workflow, PR packaging justification, or agent execution details.
4. For review responses, answer the actual concern directly. State the finding, resulting change
   with commit references, verification, and open limitation in a short self-contained response.
   Attribute quoted observations correctly and distinguish evidence from speculation.
5. An authorized hosted operation proceeds to Stage 4: Publish or revise. Draft-only or unresolved
   publication scope proceeds to Stage 5: Verify and report with the unpublished artifact.

## Stage 4: Publish or revise

1. Re-read the current PR and comments to preserve concurrent human edits and avoid duplicates.
   Verify exact repository, base, head, and requested draft/ready state before writing.
2. For GitHub creation, bind the reviewed text to local files and use `gh pr create --repo "$repo"`
   with explicit `--base "$base"`, `--head "$head"`, `--title "$title"`, and
   `--body-file "$body_file"`. Include `--draft` only for a requested hosted draft PR.
   Forgejo creation uses the installed CLI or `POST /repos/{owner}/{repo}/pulls` with explicit
   head/base and reviewed title/body. Verify the installed host's draft mechanism before using it.
3. For revisions, edit the existing title/body rather than creating another PR. For a direct
   review reply, publish the reviewed response to the correct thread or timeline. Authorized
   follow-up fixes on an open PR include a concise timeline response when review-response scope
   includes publication; draft-only scope returns the response text instead.
4. Use `gh pr comment "$number" --repo "$repo" --body-file "$body_file"` for GitHub timeline
   comments. For Forgejo resolution failures, use
   `POST /repos/{owner}/{repo}/issues/{number}/comments`; edit an owned comment with
   `PATCH /repos/{owner}/{repo}/issues/comments/{id}`. Read the forge token in memory from
   `~/.local/share/forgejo-cli/keys.json`, at `hosts["git.quinntyx.dev"].token`, and send an
   `Authorization: token ...` header to `https://git.quinntyx.dev/api/v1`.
5. A successful write proceeds to Stage 5: Verify and report. A failed or timed-out write first
   re-reads the destination for an accepted write, then reports its actual state at Stage 5.
   Retry only a proven missing write, preserving unrelated edits and existing discussion.

## Stage 5: Verify and report

1. For published artifacts, re-read the exact PR or comment and verify destination, base/head,
   title/body, draft state, and relevant commit/check links. Report incomplete checks honestly.
2. Return the URL and concise outcome for publication, or the complete usable text for a draft.
   Include the verified tests and material unresolved limit. Local working-tree bookkeeping belongs
   in the private task report, while the public artifact serves repository readers.
