---
name: mail-check
description: "Use when performing a daily brief or Taskwarrior scheduling, when
  refreshing upstream data, or whenever the current discussion could involve email
  content such as course logistics, professor or lab communication, registration,
  deadlines, career events, or announcements."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A notmuch index at `/home/zlare/docs/mail` (config `~/.config/notmuch-config`-equivalent
  via XDG; `notmuch config list` confirms `database.path`).
- An mbsync configuration at `~/.mbsyncrc` with a `utdallas` channel syncing the UTD
  mailbox into the `utdallas-local` maildir store.
- Authority to mutate exactly one thing: the `unread` tag on UTD messages, after the
  user has reviewed the surfaced summary.

## Output Contract

- A surfaced summary: every unread UTD email classified, with items the user may care
  about or attend listed proactively and conservatively.
- After the user has reviewed the summary: all surfaced unread UTD messages marked as
  read (`notmuch tag -unread`).
- omn records only for items the user expressed interest in; nothing else is pushed,
  created, or scheduled from mail.

# Entrypoint

## Stage 1: Refresh the Mailbox

1. Sync new mail: `mbsync utdallas` (the UTD channel only; never `mbsync -a`, which
   also pulls the gmail channel).
2. Index it: `notmuch new`.
3. If either command fails, continue with the existing index and note the failure in
   one status line; never block the brief or schedule on a mail-sync failure.
4. Enumerate unread UTD mail: `notmuch search --format=json path:utdallas/** and
   tag:unread`. Treat this set as the review batch. If the batch is empty, report one
   line (mail clear) and stop; go to Stage 4 only when the discussion context needs no
   summary.

## Stage 2: Triage and Surface

1. Read each batch message with `notmuch show <msgid>` (use `--format=text` and read
   the body; skip decoding failures without blocking the batch).
2. Classify every message into: potentially attendable events (talks, fairs,
   luncheons, programs), deadlines or course logistics, personal-action mail
   (professors, lab, registration), and no-relevant-content mail (marketing,
   digests whose contents are already known).
3. For Canvas notification digests, cross-check each embedded item against the omn
   store; surface only what omn does not already contain, so the feed flood does not
   reach the user.
4. Produce the summary as a compact table: date, sender, subject, why it may matter,
   and any date/time to attend. Be conservative: include items whose relevance is
   uncertain and mark them uncertain, rather than omitting them.
5. Present the summary and wait for the user's reaction; do not proceed to Stage 4
   until the user has seen it.

## Stage 3: Handle Expressed Interest

1. Only when the user says they are interested in, want to attend, or want to track a
   surfaced item, push it into omn as an `event` or `task` record following the
   omn-store conventions, with `meta.source` naming the message (message-id, sender,
   date).
2. Never push mail content into omn, and never create Taskwarrior tasks from mail,
   on the agent's own judgment. Scheduling for user-accepted items happens only
   through the normal planning pipeline after the omn record exists.
3. If the user asks for a standing rule (for example, always track employer events),
   record the rule in the assistant configuration; until then, interest is per-item.

## Stage 4: Mark As Read

1. After the user has reviewed the summary for the batch, mark the batch read:
   `notmuch tag -unread -- path:utdallas/** and tag:unread` limited to the surfaced
   message-ids.
2. Messages the user already read through aerc are already untagged; never re-surface
   or search for them. If something important appeared in mail the user read
   themselves, the user reports it directly.
3. Marking read means the content is considered surfaced and addressed; do not
   archive, move, delete, or reply to anything.

# Constraints

## Standing classification rules (user-set)

- Secret Lair drop announcements are actionable: surface them with the named drop
  date, and create a purchase-errand block (0.5h, `+managed`) on the drop date, since
  drops sell out and the user wants a reserved time block to buy before that.
- Handshake and other employer job-match blasts are low priority: flag only when the
  offering is notably strong or matches the user's existing interests and projects
  (frontier LLMs, agents, developer tooling, research); otherwise skip silently.
- Orthodontist-related mail requires no new tasks; the payment obligation is already
  scheduled in Taskwarrior.
- Canvas peer-review assignments are real obligations the user must complete; treat
  them as actionable course work, not notifications.
- Canvas "assignment graded" emails carry the policy: report the grade to the user in
  the brief and log it on the assignment's omn record (`meta.graded_at`, and
  `meta.grade` when the email carries a score — score only arrived after the user
  enabled scored notifications on 2026-09-21). If an assignment has been due for more
  than two weeks with no graded email, surface a "check on this grade" item. When the
  score is below 90%, create a 2h `+managed` review block that week to read the
  feedback and revisit the material.
- When the user defers a decision with phrasing like "let's come back to this later"
  or "I have to ask someone", create a revisit task (`+managed`, 0.5h default) a few
  days out from the current date, naming the open question and any deadline it must
  precede, rather than leaving the thread dangling in mail or conversation.
- Even when an item carries no actionable content (e.g. a request is denied), a
  reply is still owed when it comes from somebody important — the National Merit
  Scholars Program, the Bursar's Office, professors, and similar offices — to be
  polite. Schedule a short reply task (`+managed`, 0.25-0.5h) for such items
  regardless of the outcome.
- Before scheduling a reply task, check the sent-mail folder for an existing
  reply to that thread (query the sent folder for the sender's address or the
  thread subject); if one is already sent, do not create the task.

- Treat the mailbox as read-only except for the single authorized mutation: removing
  the `unread` tag from surfaced UTD messages after user review.
- Never send mail, and never alter gmail messages or tags unless the user explicitly
  asks for gmail in that request.
- Scope every query to UTD mail with `path:utdallas/**` so gmail stays excluded by
  default.
- Refresh the mailbox (Stage 1) before answering any question whose answer could
  depend on recent email, whenever the user mentions email, and at the start of every
  daily brief and scheduling session; mail changes faster than the user messages.
- Keep digests and known items out of the summary when their content is already
  represented in omn; surface only deltas.
- When unsure whether an item matters to the user, include it with an uncertainty
  flag; omission is the failure mode, not inclusion.
