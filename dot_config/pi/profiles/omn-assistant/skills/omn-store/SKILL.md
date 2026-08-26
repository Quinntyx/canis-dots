---
name: omn-store
description: "Use when creating, importing, updating, relating, deduplicating, or deleting
  records in the user's omn store, including tasks, events, courses, schedules, projects,
  notes, and artifacts."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A request or clear need to persist, modify, relate, deduplicate, or remove information in omn.
- The omn configuration at `~/.config/omn/config.json`, unless an explicit path override applies.
- Existing records from `omn export` when any record may be updated or linked.
- User confirmation for destructive deletion unless the request already requires correction or
  removal.
- Source files for artifacts, or content sufficient to create a managed artifact.

## Output Contract

- Stable, idempotent records imported through `omn import` whenever the CLI supports the operation.
- Every record contains an explicit `meta` object, including when no type-specific metadata exists.
- Existing fields, tags, metadata, artifacts, and relationships are preserved unless intentionally
  changed.
- Project records have managed Markdown artifacts and explicit omn relationships where applicable.
- Active and prospective facts remain distinguishable without duplicating the same real entity.
- Every managed file is registered through `omn put` before its URI is written into a record.
- Imports and repairs are verified with counts, exports, targeted lookups, and relationship checks.

# Entrypoint

## Stage 1: Resolve and inspect the store

1. Run `omn count`, `omn list`, and `omn export` before writing.
2. Resolve storage paths in this order: CLI flags, environment variables, omn configuration, then
   XDG defaults.
3. Treat the configured SQLite database as authoritative and the artifacts directory as managed
   storage.
4. Search existing records by stable identity, title, external identifier, course code, and tags.
5. If the requested entity already exists, proceed to Stage 2 with an update plan.
6. If no matching entity exists, proceed to Stage 2 with a creation plan.

## Stage 2: Select identity and structure

1. Choose `record: item` for entities and `record: relationship` for directed links.
2. Choose a stable namespaced ID derived from the authoritative source and durable identifiers.
3. Never encode mutable state, titles, dates, enrollment status, or filesystem paths into an ID
   unless the date or term is part of the entity's durable identity.
4. Select an open-ended `type` that expresses the entity or relationship semantics.
5. Populate the common envelope fields required for the selected record kind.
6. Populate the explicit `meta` object according to the conventions in this skill.
7. If the record needs a local artifact, proceed to Stage 3.
8. If no artifact is needed, proceed to Stage 4.

## Stage 3: Create and register artifacts

1. Create source content at a descriptive local path when content does not already exist.
2. Run `omn put SOURCE` and capture the returned opaque `file://` URI.
3. Store the URI under a connector-defined key in the record's `artifacts` object.
4. Never hand-build, canonicalize, dereference, repair, or rewrite an artifact URI in record data.
5. Use `omn mv` to relocate managed artifacts and rewrite stored references.
6. Use `omn get` to copy a managed artifact out of storage.
7. For a project, apply the project artifact rules before proceeding to Stage 4.

## Stage 4: Relate and import records

1. Build complete JSON records or JSON Lines outside the database.
2. For updates, begin from the full exported record and preserve all fields not intentionally
   changed.
3. Add directed relationship records for meaningful dependencies, containment, enrollment, lineage,
   implementation, or association.
4. Ensure every relationship endpoint names the stable ID of an existing or same-import record.
5. Pipe the completed records to `omn import`; rely on record IDs for idempotent upserts.
6. Never write directly to SQLite for creation or ordinary updates.
7. If the operation requires deletion or deduplication, proceed to Stage 5.
8. Otherwise, proceed to Stage 6.

## Stage 5: Delete or deduplicate records

1. Confirm that deletion is required and identify exact record IDs plus incoming and outgoing links.
2. Prefer an omn deletion command when one becomes available.
3. When the installed CLI has no deletion command, create a SQLite backup before direct repair.
4. Open one immediate transaction and delete relationship rows before their parent record rows
   unless foreign-key cascading is explicitly enabled for that connection.
5. Delete only the exact IDs approved by the correction plan, then commit atomically.
6. Roll back on any error and retain the backup path in the report.
7. Never delete a shared entity merely because it appears in more than one schedule, feed, or
   source.
8. Proceed to Stage 6.

## Stage 6: Verify and report

1. Run `omn count` and compare the result with the expected insert, update, or deletion count.
2. Run `omn export` or `omn information ID` and inspect every changed record.
3. Confirm that required tags, explicit `meta`, artifact URIs, and relationship endpoints are
   present.
4. Confirm that no unintended duplicate entity was introduced.
5. After direct database repair, confirm that no relationship row lacks a corresponding record row.
6. Report created, updated, and deleted IDs; artifact locations; the final count; and any
   assumptions.

# Record Envelope

## Item records

- Required fields are `id`, `record`, `type`, `tags`, and `meta`.
- Set `record` to `item`.
- Add `title` when the entity has a human-readable name.
- Add `artifacts` only when the entity owns or references opaque resources.
- Keep connector-defined structured facts under `meta`, not in the title or tags.

## Relationship records

- Required fields are `id`, `record`, `type`, `from`, `to`, `tags`, and `meta`.
- Set `record` to `relationship`.
- Treat direction as semantic: `from` is the subject and `to` is the object.
- Use a stable relationship ID so repeated imports update rather than duplicate the link.
- Put role, state, confidence, provenance, and relationship-specific details in `meta`.

## Tags

- Use tags for low-cardinality classification, lifecycle selection, source selection, and planning
  filters.
- Use metadata for values, timestamps, codes, status detail, names, locations, and external IDs.
- Use `manual` for manually transcribed facts and connector tags for imported facts.
- Use `prospective`, `future-schedule`, `inactive`, and `not-enrolled` together for tentative
  classes.
- Do not apply prospective tags to entities already represented by confirmed active records.

# Metadata Conventions

## Universal rules

- Always write `meta` as a JSON object.
- Preserve unknown metadata fields during updates.
- Use RFC 3339 strings for timestamps and ISO calendar dates only when the source has no time.
- Use IANA names for time zones.
- Use RFC 5545 recurrence rules under `meta.rrule`.
- Use compact decimal-hour or day strings with explicit units under `meta.est`.
- Never store ISO 8601 duration forms under `meta.est`.
- Put provenance under `meta.source` when a record is manually derived or references another record.
- Use `meta.active` for planning eligibility when lifecycle tags alone are insufficient.
- Never store secrets, access tokens, private feed URLs, or credentials in record metadata or
  artifacts.

## Task metadata

- `meta.due` holds the authoritative completion deadline.
- `meta.est` holds the agreed total duration estimate.
- `meta.course_id` links an assignment to its course when the source supports the association.
- Connector-specific payloads remain nested under a connector-named object.
- Completion state may be stored only when it is an upstream fact rather than a Taskwarrior plan.

## Event metadata

- `meta.start` and `meta.end` hold the first occurrence's timestamps.
- `meta.rrule` holds recurrence when the event repeats.
- `meta.timezone`, `meta.location`, and `meta.instructor` preserve scheduling context.
- `meta.course_id` identifies the owning course when applicable.
- `meta.active` determines whether the event consumes current planning capacity.

## Course metadata

- `meta.code`, `meta.subject`, and `meta.course` hold catalog identity.
- `meta.term`, `meta.section`, and `meta.class_number` hold offering identity.
- Multiple linked sections use arrays for section and class-number values.
- `meta.registration_status` records confirmed, planned, or not-enrolled state.
- `meta.source` identifies the schedule or connector record supplying the fact.

## Schedule metadata

- `meta.term` and `meta.timezone` define the schedule's scope.
- `meta.active` distinguishes the capacity-bearing schedule from retained alternatives.
- `meta.planning_status` distinguishes confirmed and prospective schedule snapshots.
- `meta.base_schedule` links an alternative schedule to the confirmed schedule it modifies.
- `meta.existing_course_ids` references reused confirmed courses.
- `meta.prospective_course_ids` references only genuinely tentative additions.

## Project metadata

- `meta.status` records lifecycle state.
- `meta.domain` records the project's broad area.
- `meta.summary` provides a concise structured description.
- `meta.created` and `meta.updated` use RFC 3339 timestamps or ISO calendar dates.
- `meta.parent_id` may identify a single canonical parent when containment is unambiguous.
- `meta.source` identifies the originating note, conversation, import, or parent record.
- Additional fields must remain structured, stable, and meaningful without parsing Markdown.

## Note metadata

- `meta.created` and `meta.updated` record note lifecycle timestamps.
- `meta.subject_ids` lists entities discussed by the note when useful.
- `meta.source` records provenance.
- The full note body belongs in an artifact when it exceeds a short summary.

# Item Type Conventions

- `task` represents work completed before an authoritative deadline.
- `event` represents fixed or recurring time on a calendar.
- `course` represents a catalog offering or enrolled section group.
- `schedule` represents a sourced schedule snapshot or proposed schedule state.
- `project` represents sustained work with goals, state, and evolving documentation.
- `note` represents authored knowledge or observations that are not themselves projects or tasks.
- New item types are permitted when none of these semantics fit; document their metadata contract.

# Relationship Type Conventions

- `enrolled-in` links the user to a confirmed course offering.
- `planned-enrollment` links the user to a genuinely tentative course offering.
- `part-of` links a component or subproject to a containing project.
- `depends-on` links blocked work to the prerequisite entity.
- `related-to` expresses a meaningful association without stronger semantics.
- `implements` links an implementation project to a design, model, language, or protocol project.
- `uses` links a project to a significant dependency represented in omn.
- `supersedes` links a replacement record or artifact to the record it replaces.
- Connector-defined relationship types remain valid and must preserve their source semantics.

# Project Artifacts

- Every `type: project` record must have a managed Markdown artifact under `artifacts.document`.
- The Markdown document must use a knowledge-article layout rather than a transient task list.
- Begin with one level-one title and a concise lead defining the project and its purpose.
- Include a compact metadata table aligned with the structured project metadata.
- Include sections for goals, scope, current state, architecture or approach, roadmap, decisions,
  references, and related records when applicable.
- Keep detailed prose, research, and evolving design in Markdown.
- Keep queryable state, dates, identifiers, estimates, and lifecycle values in record metadata.
- Mirror relevant omn relationship IDs in the related-records section without treating Markdown
  links as substitutes for relationship records.
- Update the artifact and `meta.updated` together when project knowledge materially changes.

# Schedule Deduplication

- A screenshot or alternative schedule is a source snapshot, not a reason to clone every class.
- Reuse confirmed course and event records when the same class, section, meeting, and term recur.
- Create prospective course and event records only for classes not represented by confirmed records.
- Keep an alternative schedule as its own `schedule` item with a screenshot artifact.
- Reference reused records under `meta.existing_course_ids`.
- Reference tentative additions under `meta.prospective_course_ids`.
- Tag tentative records as inactive until the user confirms enrollment.
- When enrollment becomes confirmed, update or merge the tentative record rather than retaining
  active duplicates.

# Canvas and Taskwarrior Boundaries

- Canvas adapters emit source facts and import them through `omn import`.
- Store the private Canvas feed URL in shell environment configuration, never in omn.
- Omn owns durable existence, recurrence, source state, and relationships.
- Taskwarrior records concrete work and attendance actions only.
- Begin every Taskwarrior description with an imperative verb.
- In Taskwarrior, `due` is the real deadline and `scheduled` is the planned action date.
- Give each Taskwarrior task a compact action-specific `est` string.
- Use decimal hours or days with explicit units; never use ISO 8601 durations.
- Represent each active fixed event occurrence as an independent action task.
- Give fixed events local `starttime` and `endtime` values in 24-hour `HH:MM`.
- Copy `meta.location` into the Taskwarrior `location` UDA for every fixed event.
- Use an explicit schedule-check instruction when the location varies or is unknown.
- Tag fixed events with `+managed +fixed`; add `+class` only for classes.
- Split multi-action assignments into independent tasks sharing the real deadline.
- Never add deadline trackers, parents, deliverables, work blocks, hierarchy, or relationship tags.
- Do not create Taskwarrior tasks merely because an omn fact exists unless the user approves a plan.
- Write agreed assignment estimates back to `meta.est` before registering managed Taskwarrior work.
