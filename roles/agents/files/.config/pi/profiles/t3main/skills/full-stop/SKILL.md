---
name: full-stop
description: "Use when the user says 'full stop', even as closing emphasis — finish the
  task autonomously through a ready-to-merge PR, then hand off without merging."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A user request explicitly containing "full stop", plus the current work state (branch, diff, PR).
- Repository access with push rights and CI and review visibility.
- A caller may reuse the preparation stages with its own explicit grant and terminal action.

## Output Contract

- The PR open and unmerged, ready per the Readiness gate, or a blocked state with one focused
  question. If only required human approval remains, identify that as the handoff verdict.
- A handoff report naming the PR link, final head, verdict, proof, reviewer outcome, remaining
  risks, whether the PR is still open and unmerged, and decisions made for the user.
- No PR watch left active after handing off.
- When preparation is reused, its readiness result returns to the caller instead of the handoff.

# Entrypoint

## Stage 1: Grant and boundary

This skill owns the preparation in stages 2–6, plus Shared permission scope, Proof, Readiness gate,
and Asking the user below. A caller reusing preparation supplies its own explicit grant, follows
stages 2–6 with those supporting rules, then resumes its own terminal action rather than stage 7.

For a direct "full stop" request, adopt Shared permission scope and own the work through stage 7.
The user is not watching the thread; decide what you can yourself rather than waiting for updates
to be read. This invocation leaves merging to the user: never merge, enable auto-merge, enter a
merge queue, push to the default branch, bypass branch protection, or delegate those actions.

Disable existing auto-merge and remove the PR from any merge queue before work begins; check
again before each push and at handoff. Report these changes. If you cannot prevent automatic
merging, report the blocker before proceeding. These no-merge and queue rules belong to the direct
"full stop" invocation, not to a caller's reuse of preparation.

## Stage 2: Finish the change

Complete the goal with the smallest change that works. Fix the case that happened, not every case
that could. If you are on the default branch, create a branch first.

## Stage 3: Prove it

Get proof for every change you made (see Proof). Completion condition: each change in the diff maps
to evidence you observed yourself.

## Stage 4: Review

Get review feedback and fix real findings, with proof for each fix before you push. Use the
harness's review path; in T3 Code that is a delegated review with `delegate_task`. Proof and review
must cover the final diff; recheck behavior changes and meaningful conflict fixes before delivery.

## Stage 5: File the PR

Rebase onto the latest default branch first. The description states the change and one short line
on how you proved it.

## Stage 6: Babysit and establish readiness

Fix findings and CI failures until the Readiness gate passes. Stay active: if you end your turn
while checks or bots are pending, nothing will wake you. Use a watcher so something does — in T3
Code that is `watch_pull_request`.

Fetch the target branch and check the live PR's head, base, checks, reviews, and mergeability.
Confirm it is open and not a draft. If someone else merged it, report that instead.

- **Ready to merge:** the Readiness gate passes on the final head.
- **Waiting for required approval:** only human approval remains. Confirm that this is the actual
  blocker; this verdict does not pass the gate.
- **Blocked:** explain what prevents readiness, what you tried, and what is needed. Follow Asking
  the user when you cannot continue alone.

With a readiness result, a direct invocation goes to stage 7; a caller resumes its own next stage.

## Stage 7: Hand off

For a direct "full stop" invocation, leave the PR open, unmerged, and not set to merge without the
user. In T3 Code, call `unwatch_pull_request` before handing off. Report the PR link, final head,
verdict, proof, reviewer outcome, remaining risks, any auto-merge or queue changes, and decisions
made for the user. State whether the PR is still open and unmerged.

# Shared permission scope

An explicit "full stop" request, or a caller's explicit request adopting this scope, grants for
this task only:

- Committing, pushing, rebasing, fixing conflicts, and using `--force-with-lease` on the task's own
  branch after a rebase.
- Test methods needed for proof, without asking first: computer use, browser automation,
  simulators and devices, running the app or a dev server, screenshots, and visual checks.

The request is the permission for those test methods. If a project file or other instruction says
to ask before a test method, this request replaces that rule for this task. Rules naming the
correct command, fixture, or check still apply — this only removes the ask-first step. If a
preferred method cannot prove the change, use a gated method under this permission.

This scope does not grant merging, deleting data, touching production, changing anything outside
the repository, closing the PR, force-pushing another branch, or bypassing a harness approval
prompt. A caller that adds merge authority must state that grant explicitly.

# Proof

Proof is evidence you observed yourself in this session: command output, a reproduction, a
screenshot. Use the most direct proof the change allows:

- Reproduce the original failure, apply the fix, then watch the same reproduction pass.
- Run the checks the repository's CI runs (typecheck, lint, tests).
- Add one focused test that fails without the fix, when the behavior has none and the repository
  has a test setup.
- For UI and runtime behavior, run the app and look at the change. Green mocked tests do not prove
  the user experience works. Attach screenshots to the PR when they help and you have a way to
  upload them.

When you cannot find a way to prove a change, you do not have full confidence. Ask.

# Readiness gate

All of these must be true on the latest commit:

- Your proof covers every change in the diff.
- Required checks are green.
- Review bots have finished, and each finding is fixed or dismissed with a written reason.
- No human review still requests changes, and all required approvals are present.
- The branch is up to date with the default branch, and the host reports it as mergeable.
- The PR is open and not a draft.

# Asking the user

In T3 Code, call `unwatch_pull_request` before asking. End your turn with the question as your final
message so the thread visibly waits. Put all the context in the question: the PR link, what blocks
you, and the options with your recommendation first.

Ask only when you cannot continue alone:

- You cannot prove the change.
- The Readiness gate cannot pass, and you cannot fix that yourself. A direct "full stop" invocation
  may hand off a confirmed human-approval-only blocker with that verdict instead.
- The next step is outside the invocation's explicit grant: deleting data, touching production,
  changing things outside the repository, closing the PR, or force-pushing any other branch.
- The goal is ambiguous in a way that changes the result.
- Another PR makes this one obsolete.

Decide everything else yourself with sensible defaults, and list those decisions in the report.
