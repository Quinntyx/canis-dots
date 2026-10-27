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
5. Route observed actionable defects to repairs: land small fixes yourself; launch a new repair
   `delegate_task` for a child's retained branch only when the repair is substantial. Track the new
   child and revision, revalidate changed evidence, and re-review the actual repaired tip. Every
   new review or re-check is a new `delegate_task`, never a `t3_thread_send` to the prior child.
6. Apply the parent verification ladder and actual launch budget. A focused review finishes when
   its acceptance questions are settled; no fixed five-round or extra final-review ritual. After
   two unsuccessful repairs of the same symptom, renew diagnosis and escalate the implicated
   boundary. Preserve unresolved candidates honestly when authority/budget is exhausted.
7. Keep review comments appropriate to repository readers: actionable finding, evidence and
   requested correction or acceptance. Put private execution details in the coordinator ledger.

# Acceptance boundaries

- A valid schema, persuasive explanation or clean diff is evidence to inspect, not proof of
  behavior.
- Separate baseline/infrastructure failure from the candidate's defect; both keep affected gates
  unresolved until their actual checks can run.
- Review consumes the authorized assignment/launch budget. Where the budget cannot cover another
  role, perform the relevant coordinator check or report the remaining verification limit.
