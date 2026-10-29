---
name: full-stop
description: "Use when the user says 'full stop', even as closing emphasis — run the
  task autonomously like 'full send', but leave the PR ready for the user to merge.
  Never merge."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A user request explicitly containing "full stop", plus the current work state (branch, diff, PR).
- The same repository access and authority as `full-send`, minus merge permission.
- Read `../full-send/SKILL.md` first; this skill inherits its workflow, proof, review, and
  babysitting steps.

## Output Contract

- The PR open and unmerged, ready per full-send's merge gate, or a blocked state with one focused
  question.
- A handoff report naming the PR link, final head, verdict, proof, reviewer outcome, remaining
  risks, and whether the PR is still open and unmerged.
- No PR watch left active after handing off.

# Entrypoint

## Stage 1: Grant and boundary

An explicit "full stop" request authorizes full-send's workflow — including its testing
permission for the methods proof needs (computer use, browser automation, simulators and
devices, dev servers, screenshots, visual checks) even when a project file says to ask
first. Its merge permission does not apply. The overrides below take precedence.

## Stage 2: No merging

You may commit, push, rebase, fix conflicts, and use `--force-with-lease` on this task's
branch. Never merge, enable auto-merge, enter a merge queue, push to the default branch,
bypass branch protection, or delegate those actions.

Disable existing auto-merge and remove the PR from any merge queue before work begins;
check again before each push. Report these changes. If you cannot prevent automatic
merging, report the blocker before proceeding.

## Stage 3: Work and prove

Follow full-send's stages 2–6: finish the change, prove every change, get review, file
the PR, and babysit it. Proof and review must cover the final diff; recheck behavior
changes and meaningful conflict fixes before handoff.

## Stage 4: Stop at the gate

Use full-send's merge gate as the readiness check, replacing its merge and report steps
with a handoff. Fetch the target branch and check the live PR's head, base, checks,
reviews, and mergeability. Confirm it is open, not a draft, and not set to merge without
the user. If someone else merged it, report that instead.

- **Ready to merge:** the merge gate passes. Leave the PR open and unmerged.
- **Waiting for required approval:** only human approval remains. Confirm that this is
  the actual blocker.
- **Blocked:** explain what prevents readiness, what you tried, and what is needed.
  Follow full-send's rules for asking the user.

## Stage 5: Hand off

In T3 Code, call `unwatch_pull_request` before the handoff or a question. Report the PR
link, final head, verdict, proof, reviewer outcome, and remaining risks. State whether
the PR is still open and unmerged.
