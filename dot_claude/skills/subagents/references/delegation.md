# Lightweight delegation

1. Identify the actual independent assignments and requested count. A single useful question maps
   to one child; a finite set maps to that many `delegate_task` launches within available
   parallelism.
2. Use the minimum useful children. Select one child when a single specialist can deliver the
   result. Let immutable input sharing (`isolation: 'shared'`) replace unnecessary workspace
   preparation.
3. Give each child the requested outcome, relevant context and skill-entrypoint paths, actual
   workspace authority, allowed effects, acceptance criteria and a concise artifact/report
   destination. Resolve each new assignment's eligible model and role through
   `../model-selection/SKILL.md`, then carry that resolved choice in its `target` and brief.
4. Give concurrent writers `isolation: 'worktree'` children (T3 prepares the checkout and branch;
   the child can publish its own PR) and real shared-resource leases. A read-only child needs only
   the environment and inputs necessary to answer it.
5. Collect the outcome from its completion wake, verify the relevant claim or changed behavior, and
   provide targeted feedback when necessary. Choose additional review only for a consequential
   uncertainty; each re-check is a new `delegate_task`.
6. For start-only work, report the retained `taskId`s and worktree identities as the handoff and
   stay idle until the wakes arrive. Do not stop work that still has a planned consumer; let it
   finish or cancel it explicitly with `task_cancel`.

# Escalation criterion

- Select coordinated multi-child stages when the requested result depends on accepted predecessors,
  cross-subsystem integration or repeated evaluation against clear criteria.
- Scale the task graph to useful work and the user's actual count. Parallelism is an admission
  ceiling, independent of roster size. A small task can finish without filling available capacity.
