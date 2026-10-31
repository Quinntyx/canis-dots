---
name: full-send
description: "Use when the user says 'full send' — finish the task end-to-end without
  check-ins: prove the change, review, file and babysit the PR, and merge when the
  gate passes."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A user request explicitly containing "full send", plus the current work state (branch, diff, PR).
- Repository access with push rights, CI and review visibility, and merge authority on the
  repository.
- Read `../full-stop/SKILL.md` for its Shared permission scope, preparation stages 2–6, Proof,
  Readiness gate, and Asking the user. This skill adds merging to that preparation.

## Output Contract

- Work complete through a merged PR, or a blocked state with the PR left safe (open and unmerged)
  and one focused question.
- A final report naming the PR link, merge commit or open-PR state, the proof for each change, and
  every decision made for the user.
- No PR watch left active after handing off.

# Entrypoint

## Stage 1: Grant and boundary

The user triggered this because they are not watching the thread; your updates go unread until
long after you stop. Own the work end-to-end. If the trigger was not an explicit "full send", do
not assume full autonomy — ask instead.

For this task, the request adopts full-stop's Shared permission scope and additionally grants
merging the PR once its Readiness gate passes. The remaining scope boundaries still apply.

## Stage 2: Prepare the PR

Execute full-stop's stages 2–6 with its Proof, Readiness gate, and Asking the user rules. That is
the shared finish → prove → review → file → babysit procedure. Return here with its readiness
result; this invocation's grant and merge/report ending were selected in stage 1.

Proceed to stage 3 only when the Readiness gate passes on the latest head. A waiting-for-approval
or blocked result is not permission to merge; follow Asking the user when you cannot resolve it.
If someone else already merged the PR, report the observed result instead.

## Stage 3: Merge

Recheck the live head and Readiness gate before merging. In T3 Code, call `unwatch_pull_request`
before the merge. Use the method the repository uses; check allowed methods and recent merged PRs.
If the host uses a merge queue or auto-merge, stay until it reports the PR as merged. Merge through
branch protection as configured; never use `--admin` or other bypasses.

## Stage 4: Report

Confirm the host reports the PR as merged, then report the PR link, merge commit, your proof, and
each decision you made for the user. For a blocked handoff, leave the PR safe and use full-stop's
Asking the user rules, including removing any PR watch before asking.
