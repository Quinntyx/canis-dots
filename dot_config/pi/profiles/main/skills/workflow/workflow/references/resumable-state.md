# Durable workflow state

## Ledger

- Keep a private task-local ledger beside workflow artifacts. Store the user's outcome and effects,
  graph/version, input revisions, logical task IDs, stage, status, dependencies, assignment owner,
  handle/pool IDs, session path, workspace/branch, current SHA and acceptance evidence.
- Record processed handle IDs, review/repair counters, blocked descendants, producer cursor,
  buffered case identities, publication intents and receipts, resource ownership and next actions.
- Give artifacts durable paths. Persist transitions atomically with a temporary sibling and rename;
  keep one ledger writer. Treat external side effects as separately reconciled transactions.
- Record launch intent and submission identity before scheduling, then associate the returned
  handle.
  A notebook cell's saved output and the live namespace can represent different moments.

## Resume sequence

1. Inspect the existing named kernel and its pool, handles and saved notebook before execution.
   Match live handle identities to ledger entries and actual task/session artifacts.
2. Reconcile every in-flight intent. For an uncertain submission, inspect existing pool handles and
   retained sessions before deciding whether any launch is missing. For an uncertain public write,
   inspect the remote issue/comment/PR and capture its receipt before scheduling another attempt.
3. Inspect failed, cancelled and dormant outcomes as their actual state. A cell interrupt or pop
   timeout leaves the pool alive; resume collection and account for already completed handles once.
4. Continue retained sessions with `stage.submit` using `parent` and `session_handle`, and retain
   the returned new handle. Schedule one continuation per session after its prior turn settles.
5. Revalidate changed baselines, target SHAs and inputs before releasing downstream work. Retain
   already accepted immutable evidence when its inputs remain unchanged.
6. For a lost kernel, use retained session files, workspace evidence and the ledger to reconstruct
   a handoff. The installed API has no public attach-existing-pool operation. Report live orphan
   identities for an authorized recovery path and preserve their resources while ownership is
   uncertain. Recreate only confirmed missing logical work under an explicit recovery decision.
7. Recheck shared-resource ownership against live processes before releasing leases. Mark stalled
   work as blocked with a next action when safe progress requires new authority or restored service.
8. Resume ready work under the original limits. At completion retain artifacts and close only the
   owned pool when its sessions are no longer needed; clean workspaces under delivery authority.

# Transaction boundaries

- A publication record includes repository, root-cause or request identity, content digest, intended
  action, remote ID/URL and confirmation state. A network timeout leaves an uncertain action until
  remote reconciliation resolves it.
- A resource lease records its resource, owner, process and lifecycle. Actual process ownership
  determines release; a settled agent reply alone does not establish that a GPU model was unloaded.
- Public readers receive only the requested result and useful evidence. Private session, machine,
  path and execution details remain in the private ledger.
