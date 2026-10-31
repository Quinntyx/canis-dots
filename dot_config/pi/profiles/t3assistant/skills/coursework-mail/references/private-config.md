# Private mail configuration and runtime evidence

Use the authoritative desktop's existing `~/.local/state/t3assistant/config.private.json`, or the
configured service's equivalent private record on another host. Resolve the configured mail host
through its authorized connection; having this skill on a machine is not evidence of a local
mailbox or login. Read relevant fields only, never credentials or the full private configuration.
A missing mapping is a named coverage/marking blocker, not permission to guess another account.

The coordinator supplies `assignment_email` for read-only context and `email_digest` for daily
triage. Do not invent an unimplemented top-level `mail` section. The helper's actual `--help`
defines its nested schema; inspect only the relevant private fields:

- `email_digest.index_path`, `account_roots`, `account_queries`, `daily_accounts`, `sync_lock`,
  `writer_lock_verified`, `max_reviews`, `queued_ids` and `report_dir` are the helper contract.
  The configured academic daily scope and wider assignment scope are different grants.
- The coordinator supplies `run_id`, local date, `helper_cwd` and `helper_argv`. The base argv
  includes `--config`, `--run` and required `--day`; retain all three on every invocation.
  `begin`/`report`/`status` return the actual private per-run `report.json` path.

## Additional private evidence

- Host/index identity and verified read-only access route; account names and notmuch path queries.
  Assignment searches cover all configured relevant accounts, not just the daily triage account.
- Daily academic-account query, exact dedicated thread/project identity, timezone, private report
  root, persistent run/continuation key and independent daily review budget. No thread creation
  belongs to the mail skill.
- Verified sent-folder queries for the scoped accounts and private own/correspondent aliases, used
  to identify actual replies rather than merely matching a sender.
- Relevant course/term/platform aliases and important-person/office categories. Keep actual sender
  addresses, student identifiers and message IDs private.
- A private priority-evidence pointer, suggested location
  `~/.local/state/t3assistant/mail-evidence.private.md`, containing current effective overrides:
  purchase abstention/resumption, former/current residence and effective move, package return
  policy, important correspondents, already-covered payment obligations and interest exceptions.
  The source-controlled [generic decisions](priorities.md) remain the policy, not a copy of those
  private identities. Current purchase abstention is the conservative default pending an explicit
  user update; uncertain coverage/residence relevance is surfaced rather than suppressed.
- Verified sync-writer lock/consistency procedure and, if supplied, an actual helper entrypoint and
  schema for report storage, bounded run receipts and read-flag changes. The supplied helper is
  `python -B -m t3assistant.mail_triage` from the coordinator's `helper_cwd`; verify its real help
  before use. Missing scope or an unverified writer-lock attestation blocks marking honestly.

Reports and receipts are private runtime files (owner-only directories/files), outside repositories.
They retain exact IDs, relevant excerpts, query scope, read outcomes, priority decisions, durable
review evidence and mark/pending/failure sets. Assignment evidence and daily run receipts are
separate; reading a message for an assignment does not mark it triaged or consume the daily budget.
