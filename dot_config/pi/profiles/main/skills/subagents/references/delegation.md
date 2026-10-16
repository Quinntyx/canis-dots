# Lightweight delegation

1. Identify the actual independent assignments and requested count. A single useful question maps
   to one task; a finite set maps to that many tasks, queued within available concurrency.
2. Use one AgentPool and the minimum useful stages. Select one agent when a single specialist can
   deliver the result. Let immutable input sharing replace unnecessary workspace preparation.
3. Give each worker the requested outcome, relevant context, actual cwd/profile, allowed effects,
   acceptance criteria and a concise artifact/report destination. Preserve explicit model choices;
   otherwise inherit the selected profile's configuration.
4. Give concurrent writers owned worktrees and real shared-resource leases. A read-only task needs
   only the environment and inputs necessary to answer it.
5. Collect the outcome once, verify the relevant claim or changed behavior, and provide targeted
   feedback when necessary. Choose additional review only for a consequential uncertainty.
6. For start-only work retain the open pool, handles and named kernel as the handoff. For completed
   work retain only while follow-up is useful, then explicitly close the owned pool.

# Escalation criterion

- Select coordinated workflow stages when the requested result depends on accepted predecessors,
  streaming intake, cross-subsystem integration or repeated evaluation against clear criteria.
- Scale the task graph to useful work and the user's actual count. Concurrency is an admission
  ceiling, independent of roster size. A small task can finish without filling available capacity.
