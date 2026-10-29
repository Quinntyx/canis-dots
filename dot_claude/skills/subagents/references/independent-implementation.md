# Independent subsystem implementation

1. Inspect the repository, target branch and existing tests. Identify the behavior that must work
   and the acceptance checks that can demonstrate it. Establish a usable shared baseline once.
2. Inspect existing test/CI discovery and required checks once at the baseline. Verify required
   jobs when acceptance depends on them. Missing optional hosted CI is a limitation, not permission
   to provision workflows/runners or block unrelated local checks. Preserve working automation.
3. Decompose the request into useful subsystems. Give each builder the overall request, its
   objective, baseline, allowed effects and relevant acceptance checks. Launch builders with
   `isolation: 'worktree'` — each gets its own prepared checkout and branch from the baseline
   commit and discovers interfaces and cross-file changes within its owned workspace. Uncommitted
   coordinator edits are invisible to them: obtain an accepted committed baseline before dependent
   launches. Do not stash unrelated work or assume a brief transfers uncommitted implementation.
4. Use the actual requested child count. For an explicitly selected high-parallelism build, up to
   2C genuinely useful initial build items is a headroom policy, not a minimum. Otherwise launch
   the natural smaller roster. Treat later reviews and repairs as conditional work and preserve
   explicit total-launch limits across all roles.
5. Coordinate mutable services, ports, caches and GPUs through explicit ownership recorded in the
   brief: a child that owns a dev server or a cache says so, and siblings reference its artifacts
   rather than re-binding the same resource. Reuse existing compiler caches when available and
   useful.
6. Require each builder to implement its subsystem, add relevant regression tests, verify their
   discovery and provide changed-behavior evidence. When CI is part of acceptance, capture its
   required job results for the candidate's exact current tip.
7. As a candidate settles (its completed `summary` plus its branch/worktree), perform scoped
   intermediate acceptance. Accept its required behavior with green applicable checks; land small
   fixes yourself, and launch a new repair `delegate_task` for the child's branch only when the
   repair is substantial, after cancelling any replaced live run. Every new review/re-check is a
   new task, not a message to the old child. Apply the shared verification ladder: no fixed review
   rounds; two failed repairs of the same symptom require renewed diagnosis/escalation.
8. Retain each accepted candidate's branch tip, worktree path, feature scope and evidence. Release
   integration when its actual prerequisites are accepted, while unrelated ready work continues.

# Candidate invariants

- Acceptance names the current commit, covered scope, relevant tests and unresolved blockers.
- A failed candidate retains its worktree, diagnostics and dependent-task block. Repair changes
  invalidate acceptance of the previous tip and require checks for the new one.
- Ready environment setup belongs to the coordinator. Children receive task inputs and relevant
  checks; they spend implementation effort on their assigned outcome.
- Explicit alternatives have distinct hypotheses and selection criteria. Use subsystem
  decomposition for the normal path so that independent builders contribute complementary behavior.
