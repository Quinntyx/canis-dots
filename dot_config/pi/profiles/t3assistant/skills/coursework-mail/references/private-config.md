# Private mail configuration and review history

The coordinator supplies `assignment_email` search hints or the daily `email_digest` context.
Read only relevant fields from the authoritative desktop's existing
`~/.local/state/t3assistant/config.private.json` or equivalent private record. Never dump full
configuration, inspect credential declarations or use private host/index paths as a mail backend.

## Native capability and scope

- `external_connectors` → `email_accounts` is authoritative for native email availability and
  exact account names. `email_digest.daily_accounts` contains those names; an omitted/empty list
  means all available native accounts. An explicit narrower user scope takes precedence.
- Verify every name; an unavailable requested account remains a named coverage blocker. Never
  translate academic/personal role labels into guessed native accounts. Private mappings identify
  roles, professors, parents, universities, course/term/platform aliases and sent-mail terms.
  Retain `email_digest.account_roles` as private role-to-native-name evidence and
  `email_digest.sent_queries` keyed by native account name for narrow reply-history searches;
  these are trusted search terms, never permission for direct index access.
- Assignment searches cover all relevant configured accounts, including read mail. Native search
  and reads have no refresh/flag side effects. Record existing-index freshness honestly.
- Keep relevant correspondent identities and effective priority overrides in the private
  `rules_path` (normally `~/.local/state/t3assistant/mail-evidence.private.md`). Generic priorities
  remain in [priorities](priorities.md); private purchase/residence/payment facts and screening-model
  preferences resolve them. Current user instructions and relevance judgments override older
  always-surface wording: priority categories do not mandate obsolete or irrelevant public details.
- `omn_export_argv` identifies the supported Omn read command/database. Daily assignment/exam
  reconciliation uses [course records](course-records.md); other mail reads grant no such writes.

## Durable daily journal

- Context supplies `run_id`, `local_date`, `report_root`, and `review_tool: coursework_mail_review`.
  Discover that MCP tool; it stores private review data only and performs **no mailbox operations**.
  No Python module, shell helper, repository cwd or mail configuration file is needed by an agent.
- Use the coordinator's original local date throughout resumption, even after midnight. The journal
  resolves the stable run ID from the existing daily coordinator record; never create another run
  or substitute today's date. `begin` binds verified native account names permanently for that run.
  `begin`/`checkpoint` require the actual matching runtime `T3_THREAD_ID`; an unset identity blocks
  writes (read-only operator status remains available). Never manufacture runtime identity.
- `status` pages `entries` and `ready_to_mark` with `offset`/`limit` (maximum 100). Follow
  `nextOffset`. `checkpoint` needs `expected_revision` from the latest response; on a stale-revision
  failure reload and merge, never overwrite a newer receipt. All checkpoints are immutable private
  snapshots; `report_path` is the latest checkpoint. Save classifications first, then a separate
  `finalize_report: true` checkpoint with the substantive report after reconciliation. Only that
  committed set is mark-eligible; `final_report_path` retains the verified immutable final report.
  Drafts and newly added unfinalized reviews are not ready to mark. There is no daily review-count cutoff.
- Legacy `<report_root>/<run_id>/receipt.json`, `report.json`, `report-*.json` and other private
  review artifacts stay untouched. `status` discovers ordinary and account-scoped receipts for
  the same project/local date in `legacy.runs`, verifies report filenames/content against hashes,
  and returns each source's pointers and unresolved IDs. Read relevant historical summaries to
  avoid reporting old information as new. Never rename,
  delete, rewrite or convert legacy history in place, and never import a legacy read as native
  marking authority. Resolve each unresolved ID's actual native account with narrow native searches,
  then reread it before a new classification/mark. Preserve already-committed legacy outcomes.
- New state lives separately under `<run_id>/native-v1/`: owner-only, fsynced, hash-addressed reports
  plus an atomic HEAD pointer. It records the agent's actual native-read attestations and native
  tagging results; it cannot independently prove tool reads. Report save failure permits no marking.

Missing journal access blocks daily marking, not read-only review. Retain any report privately and
state the limitation; do not invent a replacement helper or fall back to mailbox files.
