# Authorized daily read-flag procedure

This separate procedure owns only the user's standing daily-triage authority to remove `unread`.
It is not part of `aerc-email` and is never selected by assignment preparation. The processed set
comes from the durable private report's successful reads and classifications; daily confirmation
of exact IDs is unnecessary. A source-only implementation/rehearsal does not authorize live mail.

## Supported manager semantics

Verified against notmuch 0.40's installed `notmuch-tag(1)`, `notmuch-config(1)` and
`notmuch-search-terms(7)` on 2026-10-30: `notmuch tag -unread` removes that tag; when
`maildir.synchronize_flags=true`, notmuch propagates tag changes to Maildir flags (`S` is the
inverse of `unread`). It can synchronize other mapped flags as well. The managed source enables
this setting, but runtime preflight must verify the effective configuration. This establishes
local index/Maildir state only, not an IMAP-server acknowledgement. Do not invoke a mailbox sync
or `notmuch new` as a side effect to claim remote propagation.

## Runtime helper

Use the coordinator's real `helper_cwd` and `helper_argv`, retaining `--config`, `--run`
and required `--day` on every call. Inspect `--help`; then `begin`, `search`, exact candidate
`read --id RAW_ID`, `report --input FILE`, `mark`, and `status`. Related sent/previously-read
context uses `read --id RAW_ID --evidence`, which never confers mark eligibility. `mark` takes
**no IDs**: the helper derives them from the durable report. The manager argv below describes
what that helper enforces, not permission to bypass it with raw tag commands.

Report JSON is `{summary, classifications: [{id, classification, summary, actions?}]}`;
classification is `important`, `action`, `no_action` or `uncertain`. Classify only successful
complete candidate reads. One immutable report lives at the returned per-run `report.json`;
finish needed reads before committing it. Failed/unsupported MIME, unreviewed candidates and
budget backlog stay unmarked for a later authorized review. Report save failure permits zero marks.

## Per-run execution

1. Load the persisted run/report and verify its thread, authorized account scope and successfully
   reviewed IDs. Resolve any offered mail helper through its actual schema/help; a suggested
   helper name is not proof that it exists. The helper must enforce this same procedure.
2. Read the effective `database.path` and `maildir.synchronize_flags` narrowly and require the
   verified intended index and `true`. Check index/Maildir consistency and serialize against the
   configured sync/triage writer using its supported locking route. A stale mapping, unavailable
   lock or unverifiable consistency blocks marking, leaving the report ready with pending IDs;
   it does not authorize repair, configuration changes, refresh or raw Maildir edits.
3. Preflight each reported ID immediately before changing it. Read current tags and all associated
   filenames/flags through the supported manager or a verified helper. notmuch IDs can cover
   duplicate copies: a matching account `path:` does not constrain which copies tag synchronization
   affects. Every copy must be within the authorized account scope. Require all other mapped
   flags/tags consistent so synchronization will not change draft/flagged/passed/replied state.
4. Use the report's canonical raw message ID, not the `id:`-prefixed selector returned by search;
   `show`'s message `id` is already raw. Build one exact literal ID selector, Xapian-quote the value
   (double embedded quotes), and pass it as one process argument. Verify it resolves to precisely
   that one reported ID, not a pattern/regex/thread query. For each eligible ID still unread run:

   ```text
   argv = ["notmuch", "tag", "-unread", "--", exact_id_query]
   ```

   The only tag operation is `-unread`. Already-read IDs are idempotent no-ops. Unknown,
   out-of-scope, missing or incompletely reviewed IDs remain pending; never substitute a broad
   account/unread query, `--remove-all`, or a result list containing unseen candidates.
5. Read back tags and manager-observed flags. Require only removal of `unread` and addition of
   `S` on affected copies, with all other flags/tags preserved. Persist each success/no-op/failure
   and the still-pending set privately. If the command result is lost, inspect state before retry;
   if a concurrent change makes preservation uncertain, stop and report it, without reverting
   user state or declaring success. Retain the writer lock through verification and receipt update.
6. Update the durable report/receipt with local marking outcomes and remote freshness limitations.
   A retry uses only its persisted reviewed/pending-mark set under the same run identity and budget.
   Unseen backlog, decoding failures and unrelated sent-message evidence remain unchanged.
