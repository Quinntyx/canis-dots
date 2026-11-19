# Daily email triage: one existing thread, native tools only

1. Verify the coordinator's existing daily thread, stable run ID and original local date. Discover
   `coursework_mail_review`; use `status` to inspect private native and legacy history, then `begin`
   with verified `email_accounts` names. Writes require the matching runtime `T3_THREAD_ID`;
   do not synthesize missing identity. Inspect ordinary and account-scoped history in `legacy.runs`.
   Preserve the same date/accounts on continuation, including after midnight. Never launch another
   digest or run coordinator ticks from the daily thread.
2. Load [priorities](priorities.md) and private mappings. Verify all requested/default accounts.
   Use `email_refresh` under daily authority, recording its actual result/freshness in a journal
   checkpoint. On failure continue with existing-index native search and disclose the limitation.
   A missing account or unavailable capability is not an empty inbox; there is no shell fallback.
3. Enumerate `tag:unread` through `email_search` for every selected account, following every page.
   Checkpoint exact `{account, messageId}` candidates before reading them. Resume selected-but-
   unreviewed entries from the journal even if their flags changed. For unresolved legacy IDs,
   identify their real native account and reread them; legacy reports are historical evidence, not
   native marking eligibility. Explicitly queued previously-read items stay read. No count cap.
4. Use `email_read` for each candidate. Follow text `nextOffset`, paginate MIME metadata with
   `partsOffset`, and inspect relevant attachments using `email_attachment` byte chunks plus the
   appropriate local reader. Never execute attachment content or load remote images. Ordinary MIME,
   size, links, signatures or copy differences do not reject readable content. Record genuine
   inaccessible/encrypted-content limits. Leave unread messages whose meaning cannot be determined.
   For large sets follow [delegated review](delegated-review.md): Haiku 5.5 screeners inspect full
   native-read evidence and return exact coverage; the parent rechecks important original messages.
   The parent owns all journal/mail/Omn/calendar mutations; screening summaries alone prove no review.
5. Classify every fully reviewed candidate privately, including routine no-action mail. Use a
   `checkpoint` with actual read evidence, per-message classification/summary and `markEligible` (see
   [read flags](read-flags.md)). Evidence-only related reads are never candidates. Record failed or
   incomplete reads in coverage and leave them unreviewed. `uncertain` reviews stay ineligible;
   no global report or placeholder summary is needed yet. Merge duplicate announcements/shipments/
   obligations across accounts in the visible report; retain each account/ID's private receipt.
   Check narrow native sent-mail evidence before claiming a reply is owed.
6. Follow [course records](course-records.md) for daily assignment/exam reconciliation. Check before
   writing, preserve unrelated state, reconcile each underlying obligation once, read changes back
   and report per-item failures. Mail review does not prove the human performed an obligation.
7. Finish enumerating before marking (removing unread changes search offsets). After a complete
   pass, rescan from offset zero and deduplicate by account/ID; continue until no unseen messages
   appear. Every selected candidate must have a review or explicit read error. Coverage stays
   incomplete for missing accounts/pages/content. After classification/reconciliation, use a separate
   `checkpoint` with `finalize_report: true`, the substantive private `summary`, coverage, read limits,
   freshness and Omn/calendar results. No new `reviews` or `outcomes` in that checkpoint. Only its
   reported eligible set may be marked; drafts and newly appended unfinalized reviews grant no marks.
8. Follow [read flags](read-flags.md) using only `email_tag` on the committed eligible set, isolating
   failures and checkpointing outcomes. Resume pending marks from durable state; do not discard
   earlier classifications or receipts. Continue other items after an individual failure.
9. Make an editorial pass: what must the user notice or decide now? Deliver a natural selective
   summary inline, not a concatenation of reviewer findings or an inbox checklist. Omit irrelevant
   details and group obsolete backlog broadly. Mention material assignment/exam/calendar outcomes
   and actual access/marking limits briefly. Private complete coverage does not mandate public
   inclusion. Relevant actual professor originals come last as required by priorities; GitHub
   notifications and obsolete professor-associated mail do not belong in that section.

No sends/replies, archiving/deleting, unsubscribing, purchases, arbitrary planner/calendar writes or
new task threads. Only this route grants native refresh and reviewed-only read marking; assignment
context remains read-only. Reading never implies blanket permission to mark read.
