# Review routing

1. Identify the review target, current revision and requested decision. Give the reviewer the
   relevant user requirements, changed scope, ready environment and evidence needed to decide.
2. For intermediate feature review, explicitly label the role and feature. Evaluate required
   behavior, critical logic defects, races, deadlocks and crashing exceptions in that scope.
   Accept a correct scoped change with relevant green checks and leave broader polish for final
   review. Return concrete defects with reproduction evidence and affected requirements.
3. For final review, explicitly label the role and whole-request scope. Exercise entrypoints and
   hot paths, cross-subsystem interactions, error behavior and regressions on the integrated tip.
   Include applicable project standards and the core runnable user path in the decision.
4. Use independent verification for consequential or uncertain claims. A reviewer can be read-only
   in a candidate workspace when its inputs stay stable; repairs belong to the owning writer.
5. Send observed actionable defects to the retained implementation session. Track the new handle
   and revision, revalidate changed evidence, and re-review the actual repaired tip.
6. Use five review/repair cycles as the cap in selected substantial implementation workflows.
   Finish at first approval. At cap exhaustion preserve the candidate and report the blocker.
   Lightweight checks need only the feedback necessary for their actual acceptance decision.
7. Keep review comments appropriate to repository readers: actionable finding, evidence and
   requested correction or acceptance. Put private execution details in the coordinator ledger.

# Acceptance boundaries

- A valid schema, persuasive explanation or clean diff is evidence to inspect, not proof of
  behavior.
- Separate baseline/infrastructure failure from the candidate's defect; both keep affected gates
  unresolved until their actual checks can run.
- Review consumes the authorized assignment/launch budget. Where the budget cannot cover another
  role, perform the relevant coordinator check or report the remaining verification limit.
