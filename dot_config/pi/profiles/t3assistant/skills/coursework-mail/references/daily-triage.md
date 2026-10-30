# Daily email triage: one existing thread

1. Verify the configured dedicated email thread and the coordinator's claimed daily run ID in
   America/Chicago. The coordinator owns persistent deduplication, continuation and a separate
   email-review budget; assignment launch caps and attention gates do not consume this budget.
   A duplicate/completed run returns its persisted receipt. A missing run claim is a blocker,
   not authority to create another thread or start a scheduled job.
2. Load [priority decisions](priorities.md) and the relevant private profile overrides. Search the
   configured academic account by default, preserving the Omn triage account boundary. Other
   accounts require explicit triage configuration/authority. Use the existing index; sync,
   refresh/index hooks and interactive mail clients are outside this standing authority.
3. Count unreviewed unread candidates in that scope and enumerate metadata-first batches of at
   most 50 exact message IDs. Sort deterministically and retain pending IDs privately. On a
   continuation, re-enumerate and exclude processed IDs; changing `unread` invalidates offsets.
   Include any explicitly queued previously-read important item without restoring its unread tag.
4. Select within the run's remaining review budget and read each selected exact message with
   `notmuch show --format=json --entire-thread=false`. Parse the required MIME content; decoding
   failures, inaccessible attachments needed for classification and incomplete/truncated reads
   stay pending. A search hit or metadata preview alone is not reviewed. Use only relevant
   metadata/bodies, not unrelated history, remote images or executed attachments.
5. Classify every successfully read message with the priority rules. For digest items, cross-check
   read-only coursework/Omn records by source identity and current facts: summarize meaningful
   deltas, not known notification floods. If the store is inaccessible, keep the item uncertain,
   not silently suppressed. Check only narrowly relevant sent-mail evidence for an owed reply.
6. Persist an owner-only private report before marking anything read. Include the run/date/thread,
   scope/query, index freshness, total/candidate/selected counts, exact successfully reviewed IDs,
   per-message classification (including reviewed low-value/no-action items), important information,
   urgent suggested actions/deadlines, and pending/unreadable IDs with reasons. Record unrelated
   sent-mail reads separately: they are evidence, not triage candidates to mark. If report storage
   fails, leave all mail unchanged and report the blocker.
7. Present the important information and urgent tasks in this daily email thread, using the durable
   report. The user's standing authority covers marking this reviewed set without another exact-ID
   confirmation or waiting for a reaction. Follow [read flags](read-flags.md); derive the set from
   successful reads/classifications in that report, not a fresh broad unread query.
8. Persist the per-ID marking outcome and remaining backlog to the report/receipt and summarize it
   here. If marking fails, retain the report and pending-mark set for an idempotent retry under
   the same run identity. Never label mail clear while unreadable, unprocessed or unmarked work
   remains. Stop at the separate daily budget; resume only through the coordinator's bounded run.

Urgent tasks are recommendations in this thread. They are not Taskwarrior/Omn/calendar writes,
new assignment/task threads, drafts or sent replies. Completion of triage does not imply an
obligation was performed. A message can be marked read while its clearly surfaced human action
remains outstanding in the durable daily report.
