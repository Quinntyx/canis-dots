# Orchestration research

Reviewed 2026-10-05. These sources inform delivery policy, not Pi runtime APIs.

## Findings

- [Claude Code agent teams][1] use a shared dependency-aware task list and locked
  task claiming. Independent ownership prevents file overwrites; unblocked work
  can be claimed after a completion. The docs warn that coordination overhead,
  token cost, and diminishing returns make indiscriminate team growth slower.
  Transfer: give the parent one task ledger, explicit ownership, and an immediately
  replenished ready frontier; scale useful work, not the number of conversations.
- [Codex subagents][2] separate specialized parallel work from the primary thread
  and return distilled findings. The docs advise more caution with write-heavy
  concurrency because conflicting edits increase coordination overhead.
  Transfer: bounded assignments, compact evidence, and a single integration owner.
- [Codex worktrees][3] provide separate file checkouts for parallel work while
  sharing git metadata. The docs describe lightweight managed worktrees and safe
  handoff to the foreground checkout; isolated background completion is not the
  same thing as integration into the user's working prototype.
  Transfer: isolate conflicting effects when authorized, allocate only when useful,
  and verify integration. Worktrees do not justify concurrent shared-resource use.
- [LangGraph workflows][4] distinguish predetermined parallel sections from dynamic
  orchestrator-worker dispatch. Its Send API creates workers with individual state
  and aggregates their outputs into shared orchestrator state; evaluator-optimizer
  loops supply refinement when there is a concrete acceptance criterion.
  Transfer: completion-driven routing and bounded review/fix gates, not rigid
  project-wide scaffold/build/review batches or unbounded refinement.
- [Ray backpressure][5] distinguishes pending-work bounds from actual concurrency
  controlled by resource requirements. Unbounded producer queues can exhaust
  memory; waiting for completions allows controlled replenishment. The docs also
  caution against using pending-task bounds as the concurrency scheduler itself.
  Transfer: C is runtime admission capacity; ready headroom and task/resource
  budgets are separate controls. A larger roster does not authorize more windows.
- [Anthropic's multi-agent research system][6] emphasizes bounded delegation,
  distinct objectives, tool guidance, persistent artifacts, and effort scaled to
  task complexity. It reports substantial token overhead and specifically notes
  that tightly dependent coding work is less parallelizable than broad research.
  It also identifies synchronous batch waits as an information-flow bottleneck.
  Transfer: publish the smallest runnable slice early, isolate independent work,
  consume completions incrementally, and avoid duplication or dependency waits.

## Policy choices

- Approximately 3C dependency-cleared active-plus-queued jobs is the local Pi
  headroom heuristic, not an empirically optimal ratio established by these sources.
  C remains the admitted active ceiling. Do not manufacture tasks to meet 3C.
- Keep the demo critical path continuously supplied and integrate early. Saturate
  full C only when independent useful work exists; extra breadth can delay the
  integration and repair needed to make a prototype actually work.
- Positive soft reservations for review, repair, and checkpoints protect feedback
  latency; work stealing lends their unused capacity back to implementations.
  For small C, combine roles rather than declaring incompatible fixed quotas.
- Question only blockers, choose reversible defaults, establish minimum contracts,
  and use a scope cut order. Mandatory long grills, all-stream barriers, fixed
  profile requirements, PRs, and mock-first frontend prohibitions are avoidable
  startup/integration delays, not prerequisites for a credible prototype.
- Acceptance evidence, durable accounting, inherited admission limits, finite
  repair/delegation budgets, and retained failures still apply under time pressure.
  Speed means less unnecessary coordination, not erased safety or false success.

## Sources

[1]: https://code.claude.com/docs/en/agent-teams
[2]: https://developers.openai.com/codex/subagents/
[3]: https://developers.openai.com/codex/app/worktrees/
[4]: https://docs.langchain.com/oss/python/langgraph/workflows-agents
[5]: https://docs.ray.io/en/latest/ray-core/patterns/limit-pending-tasks.html
[6]: https://www.anthropic.com/engineering/multi-agent-research-system
