# t3assistant native email migration

Mail operations belong exclusively to T3's native connector. Agents check `external_connectors`
then `email_accounts`, and discover `email_search`, `email_read`, `email_attachment`, `email_refresh`
and `email_tag` schemas. Missing access is a Settings → Email blocker; there is no shell fallback.
Assignment context is read-only (including already-read messages); refresh and reviewed-only tagging
are authorized only in the dedicated daily thread. Existing selective-reporting, screening-model,
professor-originals and assignment/exam reconciliation preferences remain in the skills.

The coordinator lives in the private operator's Omn source checkout, `adapters/t3assistant/`.
`mail_context.py` now builds per-assignment search hints only, with no mail backend or shared helper
import. `mail.py` launches native-tool instructions without a helper argv/cwd. `mail_review.py` is
private journal storage exposed as `coursework_mail_review` through the existing coursework MCP
server. It does not read/tag/refresh mail. The shell mail implementation and account-discovery
module, their obsolete tests, and t3assistant's aerc-email skill symlink are retired.

## Preserve and activate

1. Back up the configured private report root and both effective/private config files outside git;
   retain a SHA-256 manifest. Keep the coordinator's SQLite run/release ledger and existing T3
   conversations. Historical launch prompts remain in the private ledger but are omitted from
   status/tick responses so obsolete instructions cannot masquerade as a new resumption request.
2. Use verified native account names in `email_digest.daily_accounts` (empty means all available).
   Retain `enabled`, `report_dir` and `rules_path`; archive obsolete index/root/query/executable/
   refresh-wrapper fields. Do not inspect or copy credentials. Preserve the private-config symlink.
3. Install only the changed t3assistant skill/system files and MCP description. Remove the stale
   t3assistant aerc skill symlink, not other profiles' mail skills. Do not modify installed plugins,
   caches, unrelated settings, T3 databases, browser tabs or sessions.
4. Keep the existing persistent 08:05 America/Chicago email timer. Coordinator launch/dedup and
   uncertain-launch recovery are unchanged. Validate scheduling with fixtures and `systemd-analyze
   calendar`, not a live tick that might create a thread. Existing agents need a profile/session
   reload to discard already-loaded old instructions; do not interrupt them automatically.

## History and resumption

Legacy `<report_root>/<run_id>/receipt.json`, `report.json`, immutable report snapshots and supporting
private evidence stay byte-for-byte unchanged. The journal discovers both ordinary and account-scoped
receipts matching the project/local date, verifies report filenames/content against hashes, and returns
all source pointers/unresolved IDs in `legacy.runs`. Legacy reads confer no native marking authority. Identify actual accounts and reread unresolved
messages natively before a new mark. Historical summaries remain useful deduplication evidence.

New state is separate under `<run_id>/native-v1/`, with owner-only immutable hash-addressed reports
and an atomic, fsynced HEAD. `begin` binds verified accounts to the existing daily run; writes require
the actual matching runtime `T3_THREAD_ID` (absent identity blocks writes, not read-only status).
`checkpoint` uses a CAS revision. Save complete native-read attestations/classifications first; no
placeholder global summary is required. After reconciliation, use a separate `finalize_report: true`
checkpoint with the substantive summary; only that set becomes `ready_to_mark`. Drafts, `uncertain`
reviews and newly added unfinalized reviews grant no marking. `final_report_path` points to the
verified immutable final report; `report_path` is the latest checkpoint. Tag outcomes are a later
checkpoint than both reviews and finalization. Nested entry fields are strictly validated. A timeout/crash after tagging but
before saving outcomes requires native tag verification before retrying. Resume with the original
local date/run ID after midnight; page all journal entries and preserve committed classifications.
The journal records attestations, not independent proof of native calls.

## Verification

```sh
python -B -m unittest discover -s docs/host/tests -p 'test_t3assistant_native_email.py' -v
# From the Omn source checkout:
PYTHONDONTWRITEBYTECODE=1 python -W error::ResourceWarning -m unittest discover -s adapters/tests -p 'test_t3assistant*.py' -v
```

Tests cover native handoffs without subprocess mail access, daily scheduling/dedup, uncertain launches,
DST and midnight, real stdio MCP discovery/resumption, CAS/immutable receipts, legacy preservation,
account-qualified IDs, pagination, partial failures, report-save failures and private permissions.
They do not perform a live mail refresh/review/tag, launch real threads or change assignment state.
