# Assigned personal hosting and publication

This reference inherits pi-plugin's scope/ownership contract. It does not independently authorize
hosting, publication, mirroring, source allocation, or installation.

## Source and project setup

1. Read `../../git/SKILL.md` for verified source identity and T3-managed checkout allocation. Reuse a
   supplied matching source; never edit the installed cache or construct a worker checkout here.
2. For a new project read `../../git/init-project/SKILL.md`. It owns the requested bootstrap,
   same-visibility hosts, stack tests/CI, ordinary source anchor, branch refs, and optional T3 project
   registration. T3 owns later thread/delegate worktrees; no sibling development worktree is required.
3. For mirror creation/repair read `../../git/github-mirror/SKILL.md`. It owns private-source
   authentication, preservation, server credentials, actual API capabilities, and completed sync.
   Do not copy tokens into argv/logs, create a public intermediate private repository, or bypass
   an unresolved visibility/access decision.
4. Preserve canonical `git.quinntyx.dev/quinntyx/<name>` source declarations for personal delivery.
   Genuine foreign origins keep their host; verified transport rewrites are distinct from identity.
5. Return to pi-plugin Stage 3 when source is ready. Planning-only stops at its report; a source-only
   task never enters hosted creation/publication just because this reference was read.

## Source publication

1. Bind the assigned branch and exact accepted local SHA after required checks. Read all branch/tag
   refs at canonical and mirror hosts before a force/prune-capable server sync.
2. Follow the mirror procedure for containment/divergence checks. Preserve destination-only refs;
   uncertain history or visibility ends with a concrete decision, not a speculative synchronization.
3. Commit/push only owned source through Git's assigned publication route. Inspect the exact remote
   branch and required hosted checks for the accepted SHA. Queue acceptance is not completed CI.
4. For assigned mirror delivery verify its destination/options, completed sync after publication,
   empty error, and accepted branch/tag ref parity at both hosts. A bounded timeout remains pending.
5. Verify actual configured default branches for a new bootstrap. Do not change an established
   repository's branch policy or server credentials incidentally to deliver a plugin update.
6. Return to pi-plugin Stage 4 ref selection when accepted publication is verified. Report pending
   required effects before installation; retain all partial state and unrelated user changes.

## Workspace boundaries

- `t3_project_clone`/registration establish the source project. `delegate_task(isolation:'worktree')`
  allocates a same-project worker from the coordinator's committed baseline; it does not accept
  an arbitrary source root or child tip by mentioning one in a brief.
- Own-thread worktree handoff is a T3 operation in the already bound project and ends the live turn.
  A newly created project's registration does not rebind an unrelated scratch thread.
- A new top-level project thread requires the user's request. Do not replace T3 binding with shell
  worktrees, shell `cd`, or Pi `/move`, and do not duplicate setup already owned by another agent.
