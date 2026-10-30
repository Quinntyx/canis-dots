# Assignment context: read-only

1. Derive course/term aliases, assignment title/ID, instructor/platform sender aliases and relevant
   date bounds from the actual assignment and private account mappings. Search all configured
   accounts that can hold related context. Daily academic-account-only triage is a different scope.
2. Build a narrow query combining verified account paths with course/assignment terms; include
   read and unread mail equally. Keep normal spam/deleted exclusions. Use assignment-specific
   terms first; if no matches, broaden one verified alias at a time within the course/term.
3. Count first, then retrieve at most 50 message selectors per batch using `notmuch search
   --format=json --output=messages --limit=50 --offset=N -- "$QUERY"`. Inspect selected metadata
   with `notmuch show --format=json --body=false --entire-thread=false -- "$EXACT_MESSAGE_QUERY"`.
   Read only relevant selected bodies using the same exact selector without `--body=false`.
   `search --output=messages` returns `id:...` selectors: remove that selector prefix once before
   building a quoted ID term. In contrast, `show`'s message `id` is already raw; do not strip it.
   Xapian-quote literal values and pass queries as single process arguments. Retain canonical raw
   IDs in receipts. Do not expand a whole thread to obtain one assignment clarification.
4. Continue relevant batches until covered or the invocation budget is reached. Persist/report
   total matches, exact examined set and remaining coverage; offsets are only a current-query
   convenience, not a durable cursor. Recount/re-enumerate on restart and deduplicate by exact ID.
   An unexpectedly broad result set calls for tighter assignment terms, not reading every body.
5. Extract only assignment-relevant clarifications, changed dates/availability, material links,
   peer-review obligations and feedback. Preserve evidence date and conflict provenance. Email
   cannot prove the user submitted work or mastered a concept; use the coursework policy gate
   before turning a mail-discovered instruction into preparation.
6. Keep necessary evidence in the private assignment workspace/progress. Report existing-index
   freshness honestly, including an unknown last successful refresh and any omitted batches.
   A zero-match result means no matches in the searched index/scope, not no message on the server.

The allowed mail operations are configured discovery, count, search and selected-message show.
They preserve all flags/tags, including `unread`, on both read and unread results. Use the existing
index; automatic refresh, `notmuch new`, sync hooks, interactive aerc and repair are outside this
path because they can mutate flags, tags or routing. A genuinely read-only remote query requires
verified semantics first; otherwise retain the existing-index/access limitation.
