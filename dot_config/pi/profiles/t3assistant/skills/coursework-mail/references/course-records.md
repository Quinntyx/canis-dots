# Email-derived assignment and exam reconciliation

This is part of daily triage only. The user authorizes recording missing assignments in Omn,
reconciling exam dates/venues there, and checking/synchronizing exam events to Google Calendar.
An assignment-preparation email search remains read-only. Updating this skill does not itself
perform live reconciliation; exercise these effects when reviewing the relevant mail.

## Resolve the existing tools and records

1. Use the coordinator's `omn_export_argv`, or the configured existing Omn command/private mapping.
   Inspect that binary's real help. Read through its supported `export`/`information` interface;
   writes use its supported `import` upsert, never direct SQLite edits. Use the same database/path
   flags as the read command, replacing `export --read-only` with `import` for a write.
2. Match assignments/exams by course/offering, source ID or URL, title and actual dates/content.
   Search existing records before creating anything; email subjects and Message-IDs are not the
   identity of an academic obligation. Related mail across accounts is evidence for one item.
3. Preserve unrelated fields, artifacts, lifecycle/completion state and source identity. Merge
   sourced changes into the full existing record before importing it. For a new record reuse the
   established connector ID when available, otherwise a stable mail-derived academic-item ID.
   Tasks use `type: task` and `meta.due`; scheduled exams use `type: event`, `meta.start`/`meta.end`
   and the existing location convention. Keep email/source evidence in private record metadata.
   Record known facts, leaving unknown dates or venues explicitly unknown rather than invented.

## Assignments

- If the assignment already exists in Omn, briefly mention it is already recorded; email alone
  is not evidence of completion or submission. Preserve the existing record unless an exam-related
  correction below applies. Report a conflicting assignment deadline for clarification rather than
  silently changing it under the narrower missing-assignment grant.
- If absent, import a source-backed task with course, description, known deadline and provenance.
  Read it back and report that it was recorded only after the write is verified.

## Exams and Google Calendar

1. Reconcile the exam's current dates, times, timezone and venue against Omn and the latest relevant
   instructor/course evidence. Update changed date/venue fields, or record the exam if missing.
   Retain provenance and distinguish a verified correction from an unresolved contradiction.
2. Discover the configured Google account/calendars and the available authenticated calendar tool.
   The installed `gog` interface was checked on 2026-11-14: `gog auth list --json`,
   `gog calendar calendars --json`, `gog calendar events --all --all-pages --from START --to END
   --json`, and `gog calendar event CALENDAR_ID EVENT_ID --json` are read paths. Inspect actual
   `--help` and use a verified calendar account/ID rather than assuming the mail From account owns it.
   An existing MCP/calendar connector may supply equivalent operations.
3. Check stored event/source links and matching events across relevant calendars, including the old
   and corrected date windows. Omn containing an exam is not proof Google Calendar contains it.
   Match the actual exam/course/source rather than creating a duplicate under a renamed title.
4. If a matching event is current, retain it and report already synced. If it is stale, update that
   same writable event. If absent, create one in the configured appropriate writable calendar.
   The checked CLI uses `gog calendar create CALENDAR_ID --summary TITLE --from START --to END
   --location VENUE --json` and `gog calendar update CALENDAR_ID EVENT_ID` with changed fields.
   Use sourced start/end times or an existing verified duration; missing required details or a
   read-only/unavailable calendar are explicit item-level limits, not fabricated appointments.
5. Read back the created/updated event. Retain its verified calendar/event link with the Omn exam
   using the existing metadata convention so retries can find it. Report the actual result inline:
   Omn date/venue corrected, exam recorded, calendar event created/updated, already synced, or the
   specific write/verification limit. A failed calendar step leaves the Omn facts and other mail
   review intact; it does not turn an attempted write into a success claim.

These grants concern course assignments/exams, not purchasing, sending mail, creating preparation
threads, marking obligations completed, changing grades, or scheduling arbitrary suggested actions.
