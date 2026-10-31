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
- Nothing in the task may require permissions beyond those granted here (see Stage 1).

## Output Contract

- Work complete through a merged PR, or a blocked state with the PR left safe (open and unmerged)
  and one focused question.
- A final report naming the PR link, merge commit or open-PR state, the proof for each change, and
  every decision made for the user.
- No PR watch left active after handing off.

# Entrypoint

## Stage 1: Grant and boundary

The user triggered this because they are not watching the thread; your updates go unread
until long after you stop. Own the work end-to-end. If the trigger was not an explicit
"full send", do not assume full autonomy — ask instead.

The request grants, for this task only:

- Merging the PR once the merge gate passes.
- `--force-with-lease` on the PR's own branch after a rebase.
- Test methods needed for proof, without asking first: computer use, browser automation,
  simulators and devices, running the app or a dev server, screenshots, and visual checks.

A "full send" request is the permission for those methods. If a project file or other
instruction says to ask before a test method, this request replaces that rule for this
task. Rules naming the correct command, fixture, or check still apply — this only removes
the ask-first step. If a preferred method cannot prove the change, use a gated method
under this permission.

It does not add permission to delete data, touch production, change anything outside the
repository, close the PR, force-push another branch, or bypass a harness approval prompt.

## Stage 2: Finish the change

Complete the goal with the smallest change that works. Fix the case that happened, not
every case that could. If you are on the default branch, use the Git procedure to select
the task branch. Parallel work follows `../subagents/SKILL.md`: in T3 use managed allocation,
not native `/batch`'s automatic worktree/PR recipe. Full send is delivery authority, not a
second orchestration engine or permission to bypass workspace ownership.

## Stage 3: Prove it

Get proof for every change you made (see Proof). Completion condition: each change in the
diff maps to evidence you observed yourself.

## Stage 4: Review

Get one independent review and fix real findings, with proof for each fix before pushing.
Use native `/code-review` through `Skill` when exposed and compatible with the child/model
routing in `../subagents/SKILL.md`; otherwise use one T3 delegated review through that
procedure. Retain actual reviewer evidence. Choose one path rather than automatically
running both; review findings alone do not publish PR comments or apply `--fix` effects.

## Stage 5: File the PR

Rebase onto the latest default branch first. The description states the change and one
short line on how you proved it.

## Stage 6: Babysit

Fix findings and CI failures until the merge gate passes. Stay active: if you end your
turn while checks or bots are pending, nothing will wake you. Use a watcher so something
does — in T3 Code that is `watch_pull_request`; call `unwatch_pull_request` before you
stop before the merge.

## Stage 7: Merge

Merge only when the merge gate passes. Use the method the repository uses; check allowed
methods and recent merged PRs. If the host uses a merge queue or auto-merge, stay until
it reports the PR as merged. Merge through branch protection as configured; never use
`--admin` or other bypasses.

## Stage 8: Report

Final message: PR link, merge commit, your proof, and each decision you made for the user.

# Proof

Use `../runtime-verification/SKILL.md` to select the evidence tier and native `/verify`
recipe when applicable. That skill owns verification cost and method; this one owns the
delivery/merge gate. Full-send's explicit testing grant supplies the permitted capture
methods, while repository checks remain a floor. Reuse the resulting reproduction,
commands and actual captures as proof instead of running a second generic proof workflow.

Observe the evidence yourself on the final change, not just a workflow's completion
message. Attach useful captures to the PR when possible. An unavailable decisive check
leaves the gate blocked and goes to Asking the user.

# Merge gate

Full confidence means all of these are true on the latest commit:

- Your proof covers every change in the diff.
- Required checks are green.
- Review bots have finished, and each finding is fixed or dismissed with a written reason.
- No human review still requests changes.
- The branch is up to date with the default branch, and the host reports it as mergeable.

# Asking the user

End your turn with the question as your final message so the thread visibly waits. Put
all the context in the question: the PR link, what blocks you, and the options with your
recommendation first.

Ask only when you cannot continue alone:

- You cannot prove the change.
- The merge gate cannot pass, and you cannot fix that yourself.
- The next step is outside the Stage 1 grant: deleting data, touching production,
  changing things outside the repository, closing the PR, or force-pushing any other
  branch.
- The goal is ambiguous in a way that changes the result.
- Another PR makes this one obsolete.

Decide everything else yourself with sensible defaults, and list those decisions in the
report.
