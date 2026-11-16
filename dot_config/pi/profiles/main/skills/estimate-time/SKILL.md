---
name: estimate-time
description: "Use when you need to judge how long agent work will take: sizing or sequencing a
  plan, deciding whether to delegate, predicting how long you, a named model or a subagent will
  run, or because a duration is about to go into a plan or reply. It yields a working figure for
  your own reasoning from measured per-model times and a reference-class method; agent work runs
  in minutes and hours, not days or weeks. Not for choosing or launching delegates (use
  subagents), human effort estimates, cost or token estimates, or measuring a run that already
  happened."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The task text, and whatever it points at (brief files, repository, target area).
- The executing model and effort setting. When estimating for yourself, use your own model. When
  unknown, estimate for the model that would normally take the task and keep that assumption
  with the figure.
- The unit wanted: one turn, or the whole task through to settled. Default to the whole task for
  a fresh work request and to one turn for a follow-up message or a delegated brief.

## Output Contract

- A working figure for your own reasoning: a centre for active time, a likely range (roughly the
  middle half of outcomes), and the two or three assumptions that drive it: kind of work, size,
  slowest commands, delegation.
- The unit the figure is in and what it excludes.
- For a parent budgeting delegation: a figure per child plus the wall-clock for the batch.
- The figure is an input to the decision that prompted it: plan sizing, delegation, how long to
  wait, or a duration the user asked for. A reply carries it only when that reply calls for a
  duration, as a sentence in the reply's own style.

# Entrypoint

## Stage 1: Fix the unit

Agent work is measured in minutes and hours. Of 256 measured tasks, half finished in under 30
minutes of active time and nine in ten in under 3 hours; the largest, a 33,000-line migration
with 27 delegates, took 27 hours. Reason about durations and plan timelines for agent work in
those units, and reserve days for clock time spent waiting on people, CI or quota.

Active time is wall-clock while the agent or any of its delegates is working. It excludes waiting
for CI, for the user and for quota resets. Choose one unit:

- **Turn**: one message until the agent's reply. A delegated brief is one turn.
- **Whole task**: first prompt until the work is settled (answer accepted, or PR merged). It
  includes the follow-up prompts that normally occur. Tasks ending in a merged PR are whole tasks.

Go to Stage 2.

## Stage 2: Size the work from the task and the workspace

Read `references/calibration.md` first; its rows define the kinds of work and sizes used below.
Then spend at most about ten quick tool calls on the task itself. Read any brief the task names,
find the files or component it touches, and find the repository's check command (its gate) and
how long it runs. Base every number on the task text and the current workspace, sizing the work
as it stands before the task starts. Then decide:

1. **Kind of work** — which calibration row the turn will follow. The questions that separate
   rows: will files change, will a build or test gate run, will other agents be delegated, is it
   a question the current context already answers.
2. **Size** — expected files touched, changed lines, and items to process (pairs to judge, files
   to review, sections to write).
3. **Verification** — which slow commands will run and how many times.
4. **Delegation** — whether the lead will launch children, whether they run in parallel, and each
   child's own kind of work.

Go to Stage 3.

## Stage 3: Anchor on the reference class

Pick the most specific calibration cell for the unit, the kind of work and the executing model,
in this order: a delegated-brief cell for delegated work; a common-single-turn cell for a turn
sent by a person, when one fits; otherwise the shape-by-model cell; the all-model shape row only
for a model with no column. Where the calibration gives an effort-specific figure, use it instead
of the pooled cell. Take the cell's median as the starting estimate.

Then position by the size found in Stage 2: small for its kind goes toward p25, large toward p75.
A cell printed as a median only takes its range from the note under its table. Leave the range
only for a concrete, named reason (a cold build, an unusually broad change, many delegates).

Measured agents take fewer steps than the material suggests: a reviewer samples and targets
rather than reading every changed line, and a small change costs the fixed overhead of reading,
checking and reporting whatever its size. Let the table set the figure, and let file and line
counts only position the estimate within the range.

For a whole task, use the whole-task tables in this order: lead model, whether it will launch
child agents, then diff size. Those medians already include the usual follow-up prompts. Budget
review rounds, repeated gate runs and repair cycles only when the request or the lead model's
habit calls for them.

Go to Stage 4.

## Stage 4: Check the slow parts

Check the anchored figure against the parts that can move it:

```
slow_commands = Σ (duration × runs) for commands over about 30 s
delegate_wait = longest child in each parallel batch, summed across sequential batches
```

Most commands finish in under a second, so only the named slow ones add command time. Compare
`slow_commands + delegate_wait` with the anchor row's usual slow-command time. When yours is
larger, add the excess to the anchor; otherwise keep the anchor. The outcome distribution is
right-skewed, so make the range wider above the estimate than below it.

For a model with no row of its own, build the figure bottom-up instead:
`turn = steps × seconds_per_step(model) + slow_commands + delegate_wait`, taking the steps from
the Opus column for that kind of work and scaling by the model's steps-versus-Opus factor.

The procedure ends here with the working figure: a centre, its range, the unit and the drivers.
Keep the range attached to the centre. Identical tasks rerun on the same model land within ±20%
of their own median only about half the time, so the centre is where outcomes cluster and the
range is what to plan around. Carry the figure into the decision that prompted it.

# Estimating for another model

A parent estimating a child uses the child's own row, not the parent's. Models differ in how many
steps they take as well as how fast each step is, and the per-model cells already reflect both.

For a parallel batch the wall-clock is the slowest child plus the parent's own launch and
integration turns, not the sum. Sequential review-and-repair rounds add one child duration plus
one parent turn per round.
