# Daily durable reporting and native read marking

Only the dedicated daily route may remove `unread`, after saving its private report. Assignment
reads grant no marking authority. Use native `email_tag` only; never shell tag commands or helpers.

## Journal protocol (no mailbox operations)

Discover `coursework_mail_review` and inspect its schema. All calls use the coordinator's original
`day` (local ISO date), not a new resumption date. `begin` binds verified native `accounts`. `status`
returns revision, report path, summary, coverage and paginated entries/`ready_to_mark`; follow
`nextOffset` using `offset`. The original legacy receipt/report paths remain read-only history.

Use `action: "checkpoint"` and the latest `expected_revision` to append any of:

- `candidates: [{account, messageId}]`: exact native pairs selected for this review.
- `reviews: [{account, messageId, readComplete: true, readEvidence, markEligible,
  classification, summary, actions?}]`: only genuinely reviewed candidates. `readEvidence` states
  the actual native body/MIME/attachment coverage, including completed chunk offsets/limits.
  Classifications are `important`, `action`, `no_action`, `uncertain`; summary is nonempty.
  Set `markEligible: false` when meaning could not be determined. Partial/failed reads remain
  candidates without a review, with exact errors recorded in `coverage`. Never attest a complete
  read based only on metadata, truncated text, a screening summary or an old helper receipt.
  Complete delegated native-read coverage may support routine classifications; the parent verifies
  important original sources and retains per-account/ID chunk coverage, not merely a confidence score.
- `summary`: the private substantive report, including deduplicated information and verified
  Omn/calendar outcomes. A nonempty durable summary is required for any reviewed set.
- `coverage`: account/query enumeration, read-error pairs, freshness, remaining set and limits.
  Related evidence reads are separate context, never eligible just because they were read.
- `outcomes: [{account, messageId, state, detail?}]`: `pending`, `marked`, `noop`, or `failed` for
  an already committed eligible review. This is a **later** checkpoint than its classification.
  Record actual native results/verification; do not claim remote acknowledgment.

Committed classifications and successful marking outcomes are immutable. New candidates/reviews
append in new hash-addressed snapshots. A stale revision requires reload/merge, not overwriting a
newer receipt. Save failure, missing journal or uncertain read evidence means **no marking**.
The journal records agent attestations; it does not independently observe native read calls.

## Native flag change

1. Verify the private report checkpoint succeeded; use only its committed `ready_to_mark` pairs.
   Do not include evidence-only reads, unreviewed candidates or unresolved legacy IDs. Complete
   candidate enumeration before marking so shrinking unread results cannot shift search pages.
2. Call `email_tag` with the exact native `account`, explicit `messageIds`, `add: []`,
   `remove: ["unread"]`. Preserve all unrelated tags. Small account-specific batches are allowed
   (schema maximum 100); isolate failed items and continue successful ones. Never use wildcard,
   query-wide, mailbox-wide or invented-ID marking.
3. Persist results in a later journal checkpoint. Successful native local marking is not proof of
   remote IMAP acknowledgment. Already-read messages are no-ops, not a reason to restore unread.
4. After a timeout, partial/unclear result or interruption before the outcome checkpoint, verify
   current tags with a narrow exact-ID `email_search` before retrying. Quote the complete raw ID as
   one literal query term (`id:"..."`, doubling embedded quotes). Reconcile only that committed
   eligible pair. Keep failed/unverifiable marks pending; never reclassify an old review to retry it.

Present material read/mark/freshness limits briefly, keeping low-impact exceptions private. Routine
or obsolete reviewed mail need not appear publicly. Relevant actual professor originals, if any,
come last; no private inventories or report links. This adds no send/task/calendar authority.
