---
name: prototype
description: >-
  Use when the user asks to prototype a project from scratch quickly, build a
  working proof of concept, prioritize a first usable version, or coordinate
  exploratory subsystem worktrees with CI-gated parallel implementation.
metadata:
  type: procedure

---

# Contract

## Input Contract

- A prototype objective, demo thesis, target repository/branch and allowed effects.
- Real user constraints, available stack/credentials and any actual demo deadline.
- Effective concurrency C, a usable subagent profile and an explicitly named persistent kernel.
- Permission for implementation, worktrees, CI bootstrap and publication when building.
- Five intermediate and five final review/repair cycles by default; user overrides take priority.

## Output Contract

- A runnable prototype matching the core demo, not merely many completed agent reports.
- A concise durable plan, exploratory subsystem worktrees, exact-tip CI evidence and merge tree.
- A published accepted target tip, or intact partial work and an explicit blocker/resume report.
- No cleanup of temporary worktrees/remote branches before the whole workflow succeeds.

# Entrypoint

## Stage 1: Decide what must work

1. Infer the demo's core behavior and constraints from the request. Ask one brief questionnaire
   only for load-bearing unknowns; skip it when autonomous execution was requested.
2. Identify must-demo, optional and stretch work, and explicitly acceptable mocks/fallbacks.
   Prefer a thin runnable path, but do not silently fake required behavior or external actions.
3. Record real deadlines only when the user supplied them. Do not grill for an invented clock,
   impose per-agent time quotas or spend the session designing every implementation detail.
4. For planning only, return the plan without creating CI, commits or worktrees. For a build,
   confirm permitted effects and go to Stage 2. Existing repositories are valid inputs.

## Stage 2: Bootstrap tests and CI

1. Inspect the actual framework, test discovery and remote. If the remote host is
   git.quinntyx.dev, set up or repair Forgejo Actions BEFORE fan-out; otherwise use existing CI.
2. Run the canonical project tests in CI and ensure newly added tests will be discovered. Cover
   pushes to every build/merge branch. Reuse .forgejo/workflows, or preserve .github/workflows
   fallback; introducing a .forgejo directory must not disable other required automation.
3. Confirm Actions enabled, compatible runner available and required workflows/jobs identifiable.
   Missing infrastructure/credentials blocks fan-out; do not call absent or skipped CI green.
   Do not install/deploy services or weaken test coverage without authority.
4. Commit/push an authorized CI bootstrap branch based on the target, wait for green required
   test jobs at its exact commit and use it as the baseline. Preserve the final target until
   accepted integration. Fix/report a red baseline before going to Stage 3.

## Stage 3: Exploratory Build cohort

1. Set effective C from requested concurrency and real pool capacity. Share C across Build,
   IntermediateReview and FinalReview; metadata tracks feature scope, depth, lineage and cycles.
2. Break work into coherent subsystems/features, not file slices. Each builder receives the
   overall request, its subsystem objective, acceptance criteria, worktree and CI duties. Let
   it discover and implement its design, interfaces and cross-file changes independently.
3. Prepare 3C useful initial Build items and queue them with build.submit_all. Do not try to
   predict or maintain '3C ready-or-running': subsequent reviews, repairs and merges grow the
   pool naturally while live admission stays C. If the project cannot support useful 3C work,
   say so before launch instead of manufacturing busywork or duplicating the entire prototype.
4. Give each builder a separate branch/worktree from the green baseline. Meaningfully different
   alternatives can be useful, but partition by subsystem to avoid accidental whole-app replicas.
   Do not provide file allowlists, predesigned interfaces or arbitrary assignment deadlines.
5. Tell builders to add relevant tests, verify discovery and ensure CI executes their new tests.
   Coordinate only actual shared ports/services/mutable caches; worktrees isolate source edits.
6. Author constants, scheduling and teardown as distinct notebook cells. Use explicit kernel
   names for operations; review the saved orchestration cell unless no-prompt execution was
   authorized. Preflight runtime Task/profile APIs and preserve submission identities on replay.
7. Consume completions immediately and go to Stage 4 for settled builders. No phase-wide wait
   barrier: reviews and independent builds can run simultaneously under the shared C cap.

## Stage 4: Loose intermediate review

1. Commit/push the candidate and require CI green for its exact tip. Tell the reviewer explicitly
   that it is an INTERMEDIATE reviewer, what feature was implemented and what its scope is.
2. Be relatively loose. Ignore out-of-scope bugs, nits, style and minor suggestions. Reject only
   critical logic errors, races, deadlocks, crashing exceptions, unmet required behavior and
   similarly consequential problems. Do not substitute a final whole-project review here.
3. CI is still mandatory. A textual merge success or reviewer approval never overrides red,
   missing, skipped, queued, cancelled or stale required jobs. Separate runner failures from
   code failures, but neither permits an approved node while its gate remains unresolved.
4. If approved and CI-green, collect the node in Stage 5 with depth zero. Otherwise feed scoped
   feedback to the original builder/session/worktree as a Build repair and repeat Stage 4.
5. Default cap: five intermediate review/repair cycles per candidate, including merge-repair
   candidates. At exhaustion preserve the branch/worktree and report a blocker; never hide it
   to claim a complete prototype. Independent work can continue.

## Stage 5: CI-gated balanced reduction

1. Track ready nodes by depth, not one flat array. Store branch/worktree, current commit, feature
   scope, contributors, review count and CI evidence. Atomically claim two same-depth nodes.
2. Create a separate merge worktree/branch from one parent and run ordinary git merge of the
   other. Do NOT start a merge agent for an ordinary mechanical merge.
3. Textual conflict queues a Build repair. After a successful merge, push the tip and wait for
   exact-tip CI; failing tests are semantic incompatibility and also queue a Build repair.
   Repair builders receive both parents, combined feature scope and observed errors, not an
   imposed solution. Their changes go through Stage 4's five-cycle loop and CI before release.
4. A mechanical merge with green CI advances without an extra intermediate reviewer. Its depth
   is d+1 for two parents at depth d. Put it only in that bucket; never immediately feed AB
   into a depth-zero pool to absorb C while other depth-zero builders remain outstanding.
5. Merge independent equal-depth pairs in parallel. When all build/review/CI/repair/merge work
   that can release further nodes is quiescent and no equal-depth pair remains, carry the
   lowest-depth orphan into the nearest higher-depth node and continue reducing. Use at most
   one orphan carry per level; non-power-of-two sizes can need carries at multiple levels.
6. Cross-depth carries use the identical mechanical merge, CI and repair/review gates. Keep
   every original and intermediate branch/worktree. When one validated root remains and all
   accepted contributors are accounted for, proceed to Stage 6.

## Stage 6: Strict final review and delivery

1. Tell the final reviewer it is FINAL review of the whole prototype. Review the core demo,
   cross-subsystem interactions, regressions, duplication and broader project standards.
   Run the runnable demo path and required tests; component reports do not prove integration.
2. Rejects return to Build on the combined worktree, then final review plus exact-tip CI.
   Default cap is five final review/repair cycles, separately counted from intermediate cycles.
3. If the demo cannot fit an actual user deadline, propose scope cuts or explicit fallback;
   do not relax CI or silently shorten the stated review limits to rush through known defects.
4. Fetch the target before integration. If it moved, reconcile and repeat validation/review
   for the changed candidate. Merge the accepted root into the authorized target and push it
   without force. Require target CI green and every contributing tip reachable from that tip.
5. If delivery succeeds, go to Stage 7. Otherwise preserve all work and report the blocker,
   runnable state and recovery identity; do not present unmerged branches as shipped behavior.

## Stage 7: Retain then clean

1. Large fan-out is intentional and permitted. N=3C builders plus N-1 distinct merge worktrees
   produces 2N-1 = 6C-1 worktrees/branches, before repair/review extras. Disk use is acceptable:
   do not lower concurrency, avoid worktrees or prematurely delete nodes because it looks large.
2. Use sccache for Rust and comparable cache approaches when other compilers show overhead.
   Address contention at the cache/resource layer rather than throttling the orchestration.
3. Keep local worktrees and their remote branches throughout the entire workflow, including
   already-merged children. They are recovery state, not disposable completion-by-completion.
4. Only after all workers stop, final review/target CI pass and all owned work is merged into
   the published target may the root close the pool and delete owned temporary remote branches
   and local worktrees/branches. Preserve dev/main, canonical trees, dirty/unmerged work and
   unrelated files. Use trash rather than rm for filesystem removal.
5. Blocked requested scope forbids successful completion and cleanup unless explicitly
   superseded by the user. Report the working demo, tests, cuts/fallbacks and blockers. Never
   claim completion from a self-report, empty agent reply, inactive window or successful schema.

# Coordination and anti-patterns

- Worktree ownership replaces exhaustive file ownership. Subsystem briefs state what to achieve,
  not which files to edit or which parent-designed interfaces/classes to reproduce.
- Submit 3C initial Build items once via submit_all; don't maintain a speculative ready frontier.
- Review a feature loosely before merging; review the final prototype strictly after reduction.
- Pure git merge plus green CI is the default. Dispatch repair agents on observed failure only.
- Do not form a rolling accumulator or repeatedly send early branches through unrelated agents.
- Preserve native Pi sessions through feedback and native compaction. Do not request handoffs
  merely for context pressure, manually respawn dormant handles or replay initial submissions.
- Use finite review/repair counters and explicit root ownership; no unauthorized recursive agents.
- Technical startup/transport guards are not invented delivery deadlines or per-builder quotas.
- Retain inspectable failures and durable notebook state; a timeout does not itself cancel work.

# Forgejo references

- Workflow directory, runner model and GitHub fallback:
  https://forgejo.org/docs/latest/user/actions/overview/
- Actions enablement and runner prerequisites:
  https://forgejo.org/docs/latest/user/actions/quick-start/
- Branch triggers and workflow syntax:
  https://forgejo.org/docs/latest/user/actions/reference/
