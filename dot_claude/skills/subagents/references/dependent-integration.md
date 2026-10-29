# Dependency-aware integration

This route inherits the parent subagents contract, T3 allocation rules, and verification ladder.

1. Record each node's accepted input SHAs, contributors, prerequisites, owner, and required checks.
   Release only ready nodes. Independent work stays runnable; failed prerequisites block descendants.
2. Choose the smallest useful integration graph. Dependency order governs dependent changes; ordinary
   merges suffice for small independent sets. Balanced or equal-depth trees are optional when useful
   or requested, not a required power-of-two coordination ritual.
3. Allocate integration writers through `delegate_task(isolation:'worktree')` after verifying the
   bound repository and committed coordinator baseline. T3 starts from that baseline, not an arbitrary
   accepted child tip. The integration brief carries immutable input SHAs; the worker verifies and
   merges those tips inside its allocated checkout. Never create/pre-seed a child checkout in the
   shell or claim that a path/base in the brief changes T3's allocation source.
4. Preserve both accepted parents and contributor reachability. On textual conflict, repair the
   combined objective within that owned workspace. After a clean merge, run the relevant behavior
   and required exact-tip checks; mechanical compatibility alone does not establish semantic success.
5. Apply scoped acceptance and the shared escalation ladder. Small fixes belong to the coordinator;
   substantial repair or a new review uses a fresh delegate within the user's launch budget. Cancel
   replaced live work first. Two failed repairs of the same symptom trigger renewed diagnosis, not
   an automatic five-pass loop.
6. Integrate ready independent nodes concurrently only within the actual parallelism and resource
   limits. Keep accepted inputs stable and retain their worktrees until delivery/recovery is settled.
7. Check the completed request on its integrated revision: affected entrypoints, cross-component
   behavior, repository-required tests, and any review justified by remaining consequential
   uncertainty. Do not replay identical feature reviews at every tree level without a new question.
8. Before authorized target delivery, fetch/reconcile target movement and revalidate the changed
   candidate. Publish normally only within scope; verify exact remote SHA, required checks, and
   reachability of every accepted contributor. Merge/publication authority is not supplied by this
   integration reference.
9. Report verified behavior and pending scope. Retain unmerged/failed candidates and diagnostics;
   clean only task-owned resources after completion under explicit cleanup authority.

# Evidence boundaries

- Required CI identifies repository, SHA, job, and actual terminal conclusion. Pending, absent,
  cancelled, or skipped required jobs remain unresolved; optional CI absence is a stated limit.
- Feature acceptance and integrated acceptance have different questions; neither is established by
  a persuasive summary, valid schema, clean merge, or elapsed time alone.
- A shared infrastructure/baseline failure pauses affected admission. Preserve unrelated work and
  restore trustworthy inputs rather than repeatedly launching workers into the same failure.
