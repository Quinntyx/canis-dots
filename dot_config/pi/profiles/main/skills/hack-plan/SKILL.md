---
name: hack-plan
description: >-
  Use when the user wants to plan, decompose, or swarm-build a greenfield
  project under a deadline - hackathons, demo days, game jams, or requests to
  grill requirements, split a big ask into phased work, or fan implementation
  across subagent worktrees with a review loop.
metadata:
  type: procedure
---

# Contract

## Input Contract

- A project idea plus, when known, hours until demo, team size, demo format,
  and hard constraints; the grill resolves whatever is missing.
- A git repository initialized on a main branch, with a GitHub remote when
  PR-based review is wanted; local diff review is the offline fallback.
- tmux available and `PI_SUBAGENTS_MAX_CONCURRENT` set to a positive number
  (24 recommended); pi-subagents usable from a PTC kernel per its skill.
- Pi profiles present: `subagents` for build, review, integrate, and research;
  `coordinator-subagents` for arbitration with the questionnaire tool;
  `design-subagents` for the UI mock track.
- `PLAN.md`, `DECISIONS.md`, and `shared/` either absent or owned by this
  workflow.

## Output Contract

- `PLAN.md` at the repository root, never committed, containing the demo
  thesis, resolved decisions, scope tiers, phases, and workstreams.
- `shared/` contract stubs committed to main before any fan-out, with a
  contract version constant.
- `DECISIONS.md` committed to main recording every arbitration outcome.
- One git worktree per workstream, plus `ui-mock` when the project has a GUI.
- Either a completed swarm run with results merged to main, or an explicit
  handoff report with the pool closed and no orphaned tmux windows.

# Entrypoint

## Stage 1: Intake

1. Ask one questionnaire round with four questions, recommending an answer for
   each when inferable: hours until demo; team size and what humans build in
   parallel; demo format and what judges reward; hard constraints such as
   mandated stack, target environment, and credentials already held.
2. If the target is an existing repository with substantial code rather than a
   greenfield build, route to the plan-architecture prompt instead and stop.

## Stage 2: Grill

1. Model the idea as a decision tree over these axes: the single core demo
   moment, product scope, stack, data model, auth approach, external
   integrations, deploy target, largest technical risk, fake-able surface, and
   recovery plan if the live demo fails.
2. Run frontier rounds with the questionnaire tool: each round contains only
   questions whose prerequisite decisions have settled; every question offers
   a recommended option; freeform overrides stay enabled.
3. Cap the grill at 4 rounds and 16 questions. Exceed it only when a
   load-bearing decision is unresolved and no reasonable default exists; ask
   one final question and adopt defaults for the remainder.
4. Do not read code or scaffold anything during the grill; the target is
   greenfield and every question is an intent question.
5. After each round, append the resolved decisions verbatim to `PLAN.md`
   under `## Decisions` before running the next round.

## Stage 3: Scope triage

1. Tier every feature from the grill: must-demo, should, stretch.
2. Record an explicit fake-it list naming what gets hardcoded, stubbed, or
   scripted instead of built.
3. Compare must-demo effort against the Stage 1 clock. When it does not fit,
   propose cuts and confirm them with one questionnaire round before writing
   the tiers.
4. Write tiers and the fake-it list into `PLAN.md`.

## Stage 4: Phased plan

1. Write phases into `PLAN.md` mapped against the clock: scaffold, core loop,
   demo-critical polish, stretch buffer.
2. Give each phase workstreams; give each workstream a name, path-ownership
   globs, acceptance criteria, dependency edges, and a subagent-ready task
   description written in prose.
3. Ownership globs must not overlap between workstreams.
4. Each phase states what is demoable if the clock ran out at its end and
   names its integration checkpoint.

## Stage 5: Contracts

1. Before fan-out, author `shared/` on main from the primary session, which
   alone holds full grill context: typed interfaces, API schemas, protocol
   definitions, and importable stubs with a contract version constant.
2. Commit `shared/` to main. Worktrees import these stubs; implementers
   propose contract changes and never edit `shared/` themselves.
3. Record the initial contract version in `DECISIONS.md`.

## Stage 6: Fan-out setup

1. Create one worktree and branch per workstream from main, and a `ui-mock`
   worktree when Stage 4 flagged GUI work.
2. Verify the profiles and `PI_SUBAGENTS_MAX_CONCURRENT` exist; abort with
   setup instructions when anything is missing.
3. Branch: the user asked for planning only, or stopped the run - report
   `PLAN.md`, `shared/`, and the worktree layout, then stop. The user asked to
   build - proceed to Stage 7.

## Stage 7: Swarm run

Run from one `exec_cell` cell with pi-subagents; the parent cell is the only
coordinator because spawned agents cannot spawn agents. Create stages: build
sized to the workstream count, review 2, coordinate 1, integrate 1, research
2-3. Review model follows the repo's default subagents model; cross-provider
review only when the user asks.

1. Submit each workstream as a build task with cwd set to its worktree,
   agentDir set to the subagents profile, the prose task description from
   `PLAN.md`, ownership globs, and an explicit timeout.
2. On each settled build result, submit a review task with the subagents
   profile and parent linkage. The reviewer verifies the build's claims
   against the actual diff, enforces ownership globs, checks compatibility
   with main's current contract version, and settles with the verdict schema:
   `{"passed": boolean, "feedback": string[], "contract_change": object|null}`.
3. When the remote is reachable, review through gh: open or inspect the PR and
   leave inline review comments. When offline, review `git diff
   main...<stream>` locally. Both paths return the same verdict schema.
4. On a failed verdict with rounds under 5, resubmit to the same build session
   via its session handle with feedback restated as prose and rounds
   incremented. At the cap, report the workstream as blocked and leave it for
   the human.
5. On a non-null `contract_change`, submit it to the coordinate stage with
   agentDir set to the coordinator-subagents profile. Trivial additive changes
   are decided there, logged to `DECISIONS.md`, and committed as a shared/
   bump; everything else blocks on the user answering the coordinator's
   questionnaire in its own tmux window, with no auto-default and no timeout.
6. On a research request from the coordinator, fan research tasks out on the
   subagents profile, summarize findings into prose, and inject them back with
   the coordinator handle's send method, which starts a new turn on the
   settled session. Never paste raw JSON into any prompt.
7. On an approved contract version bump, send a rebase steering message to
   every affected in-flight build session: rebase onto main, resolve, continue.
8. After merges, submit an integrate task on the subagents profile that runs
   the demo path in the primary checkout; route failures back to the owning
   build session under the same rounds cap.
9. Gate every cycle on the rounds metadata, pop with explicit timeouts, check
   result.ok on every result, and end the cell with pool.close().

## Stage 8: UI track

1. When the project has a GUI, start the ui-mock design session in parallel
   with the swarm using the ui-mock skill on the design-subagents profile with
   cwd set to the ui-mock worktree. The swarm performs no frontend work.
2. After the user approves the mock, submit wiring jobs to build: each job
   gets its own worktree, consumes the approved mock plus the shared/ API
   contracts, and follows the same review and contract-change loop.

## Stage 9: Completion

1. Close the pool and report: merged state, workstreams blocked at the rounds
   cap, final contract version, decisions auto-defaulted by the coordinator,
   and remaining gap against the demo thesis.

# Durability rules

- Update `PLAN.md` after every grill round and `DECISIONS.md` at every
  arbitration outcome; never rely on conversation memory for user stipulations.
- Never commit `PLAN.md` or mention it in commit messages; `DECISIONS.md` and
  `shared/` are committed and visible.
- On resume with an existing `PLAN.md`, summarize its state and offer resume,
  revise, or replan before doing anything else.

# Orchestration constraints

- Keep all routing, rounds counting, and aggregation in the parent cell; the
  coordinate stage decides contract disputes but never coordinates agents.
- Subagent prompts are user-visible in tmux windows; compose them as complete
  prose a reader can understand, restating structured results in common
  language.
- A blocked coordinator questionnaire is an intentional stall: builds keep
  flowing while the decision waits, and nothing may auto-resolve it.
- When connectivity is uncertain, prefer local diff review over PR review
  rather than stalling the loop.
