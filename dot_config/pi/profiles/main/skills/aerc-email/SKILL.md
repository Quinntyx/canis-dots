---
name: aerc-email
description: >-
  Use when asked to refresh, access, inspect, read, list, or search the user's UTDallas
  email through aerc, notmuch, mbsync, the local Maildir, or the mail sync services.
metadata:
  type: procedure
compatibility: >-
  Requires the configured local aerc, notmuch, mbsync, OAMA, systemd user services,
  and mail scripts under /home/zlare.
---

# Contract

## Input Contract

- A request involving the user's locally mirrored UTDallas email.
- Search criteria sufficient to form a bounded notmuch query when search or reading is requested.
- Explicit user intent to refresh when current server state is required.
- Explicit confirmation before any send, reply, archive, delete, move, or tag mutation.

## Output Contract

- Refresh the local mirror when requested, or report its current background-service state.
- Return only the message metadata or content needed to answer the request.
- Keep search output bounded and summarize it rather than dumping raw email data.
- Preserve messages, files, tags, flags, folders, configuration, and credentials.
- Report the query, result count, freshness state, and any relevant failure concisely.

# Entrypoint

## Stage 1: Classify the Request

1. Treat list, inspect, search, and read requests as read-only operations.
2. If the user requests current server state, new mail, synchronization, or refresh, proceed to
   Stage 2: Refresh the Mirror. Otherwise, proceed to the next classification step.
3. If the user requests an interactive aerc session, proceed to Stage 4: Use aerc Interactively.
   Otherwise, proceed to the next classification step.
4. If the user requests listing, search, metadata, addresses, or message content, proceed to
   Stage 3: Query the Local Index. Otherwise, proceed to the next classification step.
5. If the request would send, reply, archive, delete, move, retag, or edit mail, proceed to
   Stage 6: Stop or Diagnose. Otherwise, ask for the missing email-related intent and remain in
   Stage 1: Classify the Request.

## Stage 2: Refresh the Mirror

1. Recognize that refresh is not read-only. The configured cycle downloads IMAP changes, runs
   `notmuch new`, changes routing tags, invokes the Pi mail router for new inbox messages, and may
   expunge local Maildir files that were removed remotely.
2. Run the configured entrypoint in a tmux pane because reconciliation can exceed 15 seconds:

```sh
/home/zlare/.local/bin/mail-sync.sh
```

3. Let the pane finish, capture its exit status and final output, and close it according to the
   harness tmux policy. Do not start a second refresh while the first is active.
4. Treat exit status zero as a successful refresh. The script serializes callers through
   `~/.local/state/mail-router/sync.lock`, runs `mbsync -a`, and then runs `notmuch new`.
5. If refresh succeeds and the request also needs mail data, proceed to
   Stage 3: Query the Local Index. If refresh succeeds without a data request, proceed to
   Stage 5: Report Results.
6. If refresh fails, proceed to Stage 6: Stop or Diagnose. Do not replace the configured script
   with direct `mbsync`, `notmuch tag`, or Maildir file operations.
7. Use forced reconciliation only when diagnosing a verified server-to-local discrepancy and the
   user asked for repair. Run this command through tmux, then proceed to Stage 6: Stop or Diagnose:

```sh
MAIL_SYNC_FORCE_RECONCILE=1 /home/zlare/.local/bin/mail-sync.sh
```

## Stage 3: Query the Local Index

1. Use `/home/zlare/docs/mail` through the configured notmuch database. Do not scan Maildir files
   directly unless notmuch reports a missing or corrupt index.
2. Build one bounded notmuch query from the user's criteria. Supported selectors include:
   - `tag:` for local state and virtual-folder tags.
   - `from:`, `to:`, `subject:`, and `body:` for indexed fields.
   - `date:` for a date or closed or open date range.
   - `id:` and `thread:` for exact follow-up access.
   - `path:` or `folder:` for physical Maildir location.
   - `attachment:` and `mimetype:` for attachment metadata.
   - `and`, `or`, `not`, parentheses, quoted phrases, and trailing wildcards for composition.
3. Apply the local tag model correctly:
   - `tag:inbox and not tag:deleted` is the aerc `inbox` virtual folder.
   - `tag:unread and tag:inbox` is the aerc `unread` virtual folder.
   - `tag:routed` is the aerc `routed` virtual folder.
   - `tag:sent` is the aerc `sent` virtual folder.
   - `*` is the aerc `all` virtual folder.
   - `tag:archive` locates archived mail even though it is not mapped as an aerc virtual folder.
   - Deleted and spam messages are excluded by default unless named explicitly in the query.
4. Count matches before retrieving metadata. Substitute the complete query and keep it one quoted
   shell argument:

```sh
notmuch count -- "$QUERY"
```

5. If the count is unexpectedly broad, refine the query and repeat this stage. If it is bounded,
   retrieve at most 50 metadata records without bodies:

```sh
notmuch show --format=json --body=false --entire-thread=false \
  --sort=newest-first --limit=50 -- "$QUERY"
```

6. For compact shell output, project only necessary headers and identifiers with `jq`:

```sh
notmuch show --format=json --body=false --entire-thread=false \
  --sort=newest-first --limit=50 -- "$QUERY" |
  jq '[.. | objects | select(has("id")) |
    {id, date:.headers.Date, from:.headers.From, to:.headers.To,
     subject:.headers.Subject, tags}]'
```

7. If the user requested only a list or search, proceed to Stage 5: Report Results. If the user
   requested message content, continue in this stage.
8. Select exact message IDs from the metadata result. Never retrieve bodies for every match merely
   to identify the intended message.
9. Retrieve one selected message as structured JSON. Keep whole-thread expansion disabled:

```sh
notmuch show --format=json --entire-thread=false -- "id:$MESSAGE_ID"
```

10. Extract only requested text parts when full MIME structure is unnecessary:

```sh
notmuch show --format=json --entire-thread=false -- "id:$MESSAGE_ID" |
  jq -r '.. | objects | select(."content-type"? == "text/plain") |
    .content // empty'
```

11. Use `notmuch address` only for an address request, with the same bounded query. Then proceed to
    Stage 5: Report Results.
12. Never use `notmuch tag`, `notmuch insert`, `notmuch reply`, raw Maildir writes, or message-file
    deletion during this procedure.

## Stage 4: Use aerc Interactively

1. Launch aerc in an interactive tmux pane and retain its pane ID:

```sh
tmux split-window -P -F '#{pane_id}' aerc
```

2. Tell the user that the configured virtual folders are `inbox`, `unread`, `routed`, `sent`, and
   `all`. Physical `INBOX` and `Sent Items` are intentionally excluded from the folder list.
3. Use `:check-mail` for a manual refresh inside aerc. Automatic checks run every minute, IMAP IDLE
   triggers sync on new inbox mail, and `mail-sync.timer` provides a five-minute fallback.
4. Use `/` to start `:search`, `\` to start `:filter`, `k` and `K` to move between results, and
   `Esc` to clear search or filter state.
5. Remember that `:search` and `:filter` accept full notmuch syntax but apply on top of the active
   folder query. Use `:cf` with a notmuch query when a new top-level scope is required.
6. Do not send keystrokes that mutate mail unless the user explicitly confirms the exact action.
7. After launching the session and providing the controls, proceed to Stage 5: Report Results.

## Stage 5: Report Results

1. State whether data came from the existing index or from a newly completed refresh.
2. Report the notmuch query and total match count for searches.
3. Present at most the requested number of results with date, sender, subject, tags, and message ID.
4. Summarize or quote body content only when requested, and omit unrelated recipients, signatures,
   tracking links, attachment bytes, and quoted thread history unless they are material.
5. If output was truncated, state the limit and ask whether to continue with a narrower query.
6. End the procedure without changing mail state.

## Stage 6: Stop or Diagnose

1. For a requested mutation, state that this skill is read-only except for refresh, request explicit
   confirmation, and stop this procedure. Do not infer approval from a search or read request.
2. For refresh failures, inspect only bounded service state and recent logs:

```sh
systemctl --user is-active goimapnotify.service mail-sync.timer mail-sync.service
journalctl --user -u mail-sync.service -n 50 --no-pager
```

3. Distinguish lock timeout, IMAP or OAMA authentication, mbsync, notmuch indexing, and Pi routing
   failures. Report the failing layer and exact non-secret error.
4. Never run `oama access` for diagnosis or print, capture, store, or summarize its bearer token.
5. Do not read the routing log unless needed for a routing failure. If needed, inspect only its last
   bounded entries and do not expose email content from the log.
6. If diagnosis identifies a safe read-only retry, return to Stage 2: Refresh the Mirror only when
   the user requested retry. Otherwise, proceed to Stage 5: Report Results.

# Implementation Facts

- aerc account configuration: `/home/zlare/.config/aerc/accounts.conf`.
- aerc query map: `/home/zlare/.config/aerc/query-map`.
- notmuch configuration: `/home/zlare/.notmuch-config`.
- mbsync configuration: `/home/zlare/.mbsyncrc`.
- local Maildir and notmuch database: `/home/zlare/docs/mail`.
- sync entrypoint: `/home/zlare/.local/bin/mail-sync.sh`.
- sync cycle: `/home/zlare/.local/bin/mail-sync-cycle.sh`.
- notmuch routing hook: `/home/zlare/docs/mail/.notmuch/hooks/post-new`.
- background refresh: `goimapnotify.service` and `mail-sync.timer`.
- credentials are supplied by OAMA through configured commands and must never be surfaced.
