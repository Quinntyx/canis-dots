# Independent subsystem implementation

1. Inspect the repository, target branch and existing tests. Identify the behavior that must work
   and the acceptance checks that can demonstrate it. Establish a usable shared baseline once.
2. For substantial Forgejo implementation workflows, establish test CI before builder fan-out.
   Inspect `git remote -v`, workflow discovery, repository Actions enablement, runner availability,
   branch triggers and test discovery. Preserve working automation when extending it. Obtain green
   required jobs at the baseline SHA, or retain the blocker before launching dependent builders.
3. Decompose the request into useful subsystems. Give each builder the overall request, its
   objective, baseline, owned branch/worktree, allowed effects and relevant acceptance checks.
   Let the builder discover interfaces and cross-file changes within its owned workspace.
4. Use the actual requested assignment count. For an explicitly selected high-parallelism build,
   queue up to 2C genuinely useful initial build items once when scope supports them. Otherwise
   queue the natural smaller roster. Treat later reviews and repairs as conditional work, with
   live admission still bounded by C. Preserve explicit total-launch limits across all roles.
5. Admit ready builders through AgentPool. Coordinate mutable services, ports, caches and GPUs
   through actual resource ownership. Reuse existing compiler caches when available and useful.
6. Require each builder to implement its subsystem, add relevant regression tests, verify their
   discovery and provide changed-behavior evidence. When CI is part of acceptance, capture its
   required job results for the candidate's exact current tip.
7. As a candidate settles, perform scoped intermediate acceptance. Accept its required behavior
   with green applicable checks; return concrete critical defects to the retained builder session.
   Five review/repair cycles is the default cap for this selected substantial implementation mode.
8. Retain each accepted candidate's tip, workspace, feature scope and evidence. Release integration
   when its actual prerequisites are accepted, while unrelated ready work continues.

# Candidate invariants

- Acceptance names the current commit, covered scope, relevant tests and unresolved blockers.
- A failed candidate retains its workspace, diagnostics and dependent-task block. Repair changes
  invalidate acceptance of the previous tip and require checks for the new one.
- Ready environment setup belongs to the coordinator. Workers receive task inputs and relevant
  checks; they spend implementation effort on their assigned outcome.
- Explicit alternatives have distinct hypotheses and selection criteria. Use subsystem decomposition
  for the normal path so that independent builders contribute complementary behavior.
