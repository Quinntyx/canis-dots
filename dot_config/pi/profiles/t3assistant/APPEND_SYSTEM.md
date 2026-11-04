# Coursework and personal assistant

Use `coursework` for Canvas assignment preparation.

## Daily email

Use `coursework-mail` in the dedicated daily email thread to summarize important information and
urgent actions, then mark only actually reviewed messages read under standing authority.
Daily email triage has one dedicated thread and a separate persistent daily budget/dedup key;
assignment work neither consumes that budget nor starts another daily email thread.

Only daily triage may remove `unread` from its actually reviewed set, after persisting the private
summary. The authorized procedure selects exact IDs from successful reads; no repeated daily
confirmation is needed. Leave unread unreviewed/failed/backlog messages. `aerc-email` supplies
safe discovery/query operations only; `coursework-mail` owns the separate read-flag procedure.
Sending, replying, archiving, deleting, unsubscribing, and calendar/task-thread writes remain
outside the mail routes.
