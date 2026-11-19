# Assignment context: read-only native tools

1. Verify `external_connectors` and `email_accounts`. Derive course/term aliases, actual assignment
   title/ID, instructor/platform terms and relevant date bounds from verified sources. Search each
   relevant native account, not just the account weighted most heavily in daily triage.
2. Use `email_search(account, query, limit, offset)` with narrow assignment terms plus verified course
   aliases. Both read and unread mail are included: do **not** add an unread filter. Native tools own
   account scoping and normal exclusions; no mailbox paths or host commands are needed. A coordinator
   `course_query` is a hint, not evidence of a completed search. Tighten unexpectedly broad queries.
3. Page metadata first and select relevant messages; read exact results through
   `email_read(account, messageId)`. Keep raw IDs unchanged. Follow text `nextOffset` and remaining
   MIME metadata via `partsOffset`, and inspect relevant `email_attachment` parts/byte chunks. A
   partial body or metadata preview is not a complete read. Do not expand an entire conversation
   unnecessarily, load remote images or execute attachments.
4. Use the configured `assignment_email.max_messages` as a bounded per-preparation read budget,
   normally eight. This is not a daily-triage limit. Record exact examined (account, messageId)
   pairs, query scope, reported match counts, pages/bodies omitted and freshness limits. Offsets are
   not durable cursors: re-enumerate on restart and deduplicate by account/ID. Never claim complete
   coverage when a budget, pagination or access limit remains.
5. Extract only relevant clarifications, changed dates/availability, materials, peer obligations and
   feedback. Preserve evidence dates and conflict provenance in the private assignment workspace.
   Historical prefetched context may remain useful evidence, but is not a fresh native search.
   Mail cannot prove submission or mastery. Report zero matches only for the actual searched scope.

No `email_refresh`, `email_tag`, sending/replying, reindexing or daily journal mutation is authorized
here. All flags/tags remain unchanged. Missing native access is a Settings → Email blocker, never
permission to inspect mailbox files, credentials or use shell/aerc/notmuch fallbacks. Continue any
available coursework preparation while naming blocked email coverage explicitly.
