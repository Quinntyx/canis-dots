# Dependency-aware integration

1. Record each node's prerequisites, accepted input SHAs, combined scope, owner and required checks.
   Release a node only when its actual prerequisites pass. Independent tasks remain runnable.
2. Choose the integration shape from dependencies. For independent peers, form balanced mechanical
   pairs and merge those results at successive levels. Retain a lone node unchanged at a level;
   an arbitrary useful roster is valid. Use an explicit equal-depth power-of-two tree when the
   user selects that policy. For genuinely dependent changes, follow their dependency order.
3. Claim each pair once in the coordinator ledger. Create an owned integration worktree/branch
   from an accepted parent, then run ordinary `git merge` with the other accepted parent tip.
   Preserve the contributor set and both input SHAs as integration provenance.
4. On a textual conflict, admit an integration repair task with both parents, combined objective
   and observed conflict. On a clean merge, run the relevant tests and exact-tip required CI.
   Green checks release the result directly; observed semantic failure admits a repair task.
5. Give repair workers the observed failure and freedom to resolve it. Route repaired candidates
   through scoped acceptance with the selected five-cycle repair cap. Preserve exhausted or
   blocked nodes and their descendants as pending scope rather than treating them as delivered.
6. Integrate independent pairs concurrently within C and resource leases. Keep accepted child tips
   stable and retain their workspaces through final delivery. A faster pair advances only through
   its selected graph, keeping early code from repeatedly traversing unrelated review passes.
7. With a complete integrated candidate, run whole-request review, the runnable behavior path and
   required tests. The default final review/repair cap is five cycles; first approval ends it.
8. Fetch the authorized target before delivery. Reconcile target movement and validate the changed
   candidate again. Update only the authorized target, use ordinary non-force publication and
   confirm its exact-tip required checks. Verify all accepted contributors are reachable from it.
9. Report verified integrated behavior and open blockers. Preserve unmerged or failed work until
   recovery is settled. Perform authorized cleanup after delivery and owned worker completion.

# Integration evidence

- CI records identify repository, commit, required jobs and their terminal conclusions. Pending,
  absent, cancelled or skipped required jobs remain unresolved acceptance.
- Mechanical merge success establishes textual compatibility. Tests and behavioral checks establish
  semantic compatibility. Feature review and whole-request review have separate scopes.
- A dependency failure blocks its descendants, not independent components. A shared baseline or
  resource failure pauses affected admission until the coordinator restores a trustworthy state.
