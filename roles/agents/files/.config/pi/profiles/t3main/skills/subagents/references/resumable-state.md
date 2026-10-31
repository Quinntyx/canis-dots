# Durable workflow state

## Record

- Keep a private task-local record beside workflow artifacts. Store the user's outcome and effects,
  graph/version, input revisions, logical child identities, stage, status, dependencies, assignment
  owner, `taskId`/child thread id, worktree path and branch, current SHA and acceptance evidence.
- Record processed wake turns, review/repair counters, blocked descendants, producer cursor,
  buffered case identities, publication intents and receipts, resource ownership and next actions.
- Give artifacts durable paths. Persist transitions atomically with a temporary sibling and rename;
  keep one writer. Treat external side effects as separately reconciled transactions.
- Record launch intent and brief identity before calling `delegate_task`, then associate the
  returned `taskId` and thread id. A wake turn's content is observation of a moment; the durable
  record is the state.

## Resume sequence

1. Inspect the existing record and the T3 thread's task/thread state before relaunching anything.
   Match `taskId` and thread identities to record entries and actual worktree artifacts
   (`t3_worktree_list` for branches and checkout paths).
2. Reconcile every in-flight intent. For an uncertain launch, check whether its thread exists
   (`t3_thread_list` / `t3_thread_read`) before deciding whether a launch is missing: a lost wake
   does not undo a finished child. For an uncertain hosted write, inspect the remote issue/comment/
   PR and capture its receipt before scheduling another attempt.
3. After a child's completion wake, use `task_status` to consume its final summary once. A task
   without a completion wake is still live/unknown; do not probe `task_status` to discover completion.
   Use the bounded thread/launch reconciliation above only for genuinely uncertain identities,
   never as a polling loop. A timeout or lost response is not failure. Preserve its wake or follow
   the returned `next`; cancel/relaunch are separate, explicitly recorded decisions.
4. Continue retained work with a new `delegate_task` whose brief carries the prior child's summary,
   artifacts and open questions; retain the returned new `taskId`. There are no resumable sessions:
   continuation is brief-merging, so keep summaries dense.
5. Revalidate changed baselines, target SHAs and inputs before releasing downstream work. Retain
   already accepted immutable evidence when its inputs remain unchanged.
6. For a dropped thread or lost record, reconstruct the handoff from worktree branches, PR links,
   ledger artifacts and `t3_thread_read`. Recreate only confirmed missing logical work under an
   explicit recovery decision, and report orphan identities rather than silently duplicating them.
7. Recheck shared-resource ownership against live processes before releasing leases. Mark stalled
   work as blocked with a next action when safe progress requires new authority or restored service.
8. Resume ready work under the original limits. At completion retain artifacts and PR links; clean
   workspaces only under delivery authority, preserving dirty, unmerged and unrelated user work.

# Transaction boundaries

- A publication record includes repository, root-cause or request identity, content digest, intended
  action, remote ID/URL and confirmation state. A network timeout leaves an uncertain action until
  remote reconciliation resolves it.
- A resource lease records its resource, owner, process and lifecycle. Actual process ownership
  determines release; a settled child reply alone does not establish that a GPU model was unloaded.
- Public readers receive only the requested result and useful evidence. Private session, machine,
  path and execution details remain in the private record.
