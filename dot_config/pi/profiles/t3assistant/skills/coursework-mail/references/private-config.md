# Private mail configuration and runtime evidence

Use the authoritative desktop's existing `~/.local/state/t3assistant/config.private.json`, or the
configured service's equivalent private record on another host. Resolve the configured mail host
through its authorized connection; having this skill on a machine is not evidence of a local
mailbox or login. Read relevant fields only, never credentials or the full private configuration.
A missing mapping is a named coverage/marking blocker, not permission to guess another account.

The coordinator supplies `assignment_email` for read-only context and `email_digest` for daily
triage. Do not invent an unimplemented top-level `mail` section. The helper's actual `--help`
defines its nested schema; inspect only the relevant private fields:

- `email_digest.index_path`, `account_roots`, `account_queries`, `daily_accounts`,
  `queued_ids`, `refresh_argv` and `report_dir` are the helper contract. The entire selected unread
  scope is reviewed; legacy `max_reviews`, `sync_lock` and `writer_lock_verified` are ignored.
  The scheduled default includes both academic and personal mappings; an explicit account request
  can narrow a run. `accounts` returns composer-compatible
  account names/From identities; `--account NAME` selects the requested account. `accounts_file`
  may override discovery; otherwise use T3's `emailAccountsFile` setting and the same
  `$XDG_CONFIG_HOME/aerc/accounts.conf` fallback as the composer.
- The coordinator supplies `run_id`, local date, `helper_cwd` and `helper_argv`. The base argv
  includes `--config`, `--run` and `--day`; retain them when resuming that run. For an ad-hoc
  account-specific review, omit `--run` and use the requested `--account` so the helper derives
  an account-specific identity. `accounts` requires only `--config`.
  `begin`/`report`/`status` return the actual private report snapshot path.

## Additional private evidence

- Host/index identity and verified read-only access route; account names and notmuch path queries.
  Assignment searches cover all configured relevant accounts, not just the daily triage account.
- Requested/default account queries, exact dedicated thread/project identity, timezone, private report
  root and persistent run/continuation key. No message-count cap applies. No thread creation
  belongs to the mail skill.
- Verified sent-folder queries for the scoped accounts and private own/correspondent aliases, used
  to identify actual replies rather than merely matching a sender.
- Relevant course/term/platform aliases, professor identities, important people/offices, the two
  parent email addresses and the always-surface universities. Keep actual sender addresses,
  student identifiers and message IDs private. Use these mappings for both mail accounts.
- A private priority-evidence pointer, suggested location
  `~/.local/state/t3assistant/mail-evidence.private.md`, containing current effective overrides:
  purchase abstention/resumption, former/current residence and effective move, package return
  policy, important correspondents, already-covered payment obligations and interest exceptions.
  The source-controlled [priorities](priorities.md) own generic policy; the private profile resolves
  parent addresses, academic/personal account roles and university identities without duplicating
  public policy. New always-surface rules override older filters. Purchase abstention concerns
  purchases, not reporting new Secret Lair drops.
- The coordinator's `omn_export_argv` points to the actual Omn binary/database. Resolve existing
  Google account/calendar and exam-event links through configured tools/private records. Daily
  assignment/exam reconciliation follows [course records](course-records.md); other coursework
  email context remains read-only.
- Effective `maildir.synchronize_flags` and an actual helper entrypoint/schema for report storage,
  durable run receipts and read-flag changes. The supplied helper is
  `python -B -m t3assistant.mail_triage` from the coordinator's `helper_cwd`; verify its real help
  before use. It uses notmuch's native database locking; legacy `sync_lock` and
  `writer_lock_verified` fields are ignored. Missing account scope remains a named blocker.

Reports and receipts are private runtime files (owner-only directories/files), outside repositories.
They retain exact IDs, relevant excerpts, query scope, read outcomes, priority decisions, durable
review evidence and mark/pending/failure sets. Assignment evidence and daily run receipts are
separate; reading a message for an assignment does not mark it triaged.
