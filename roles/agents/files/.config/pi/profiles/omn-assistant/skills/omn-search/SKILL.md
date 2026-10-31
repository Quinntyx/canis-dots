---
name: omn-search
description: Use when retrieving or querying the user's local omn record store (courses, assignments, events, notes), or when explaining omn's data model and CLI.
---

# omn-search

`omn` is the user's local, criterion-free record store: it ingests external facts
(Canvas courses/assignments/events, notes, published artifacts) and answers
queries against them. You are the search/coverage layer — use this skill to pull
facts out of the store so you can answer the user without guessing.

## Where the data lives

The omn storage dir is set by `~/.config/omn/config.json`:

```json
{
  "storage_dir": "~/docs/omn"
}
```

That means:

- `~/docs/omn/omn.db` — the SQLite record store
- `~/docs/omn/artifacts/` — copied artifact files (opaque `file://` URIs)

The binary is `omn` (installed from the `omn-git` package). Overrides, highest
first: `--database`/`--artifacts` flags, `OMN_DB`/`OMN_ARTIFACTS` env vars, the
config file (`OMN_CONFIG` overrides the config path), then the XDG default.

## The record model

A record is one JSON envelope:

```json
{
  "id": "canvasical:...:course:cs-4337",
  "record": "item",               // "item" | "relationship"
  "type": "course",               // connector-defined
  "from": "...", "to": "...",     // only relationships
  "title": "CS 4337",             // items usually have one
  "tags": ["canvas", "ical"],
  "meta": { ... },                // arbitrary JSON, type-specific
  "artifacts": { "description": "file:///..." }   // opaque URI map
}
```

Common types: `task` (`meta.due` RFC 3339), `event` (`meta.start`/`meta.end`,
optional `meta.rrule`), `course` (`meta.code`/`meta.canvas`), and
`enrolled-in` relationships (from `omn:self` to a course).

## Commands (current)

```sh
omn import                 # read JSON array or JSON Lines from stdin
omn list                   # table of records (default command)
omn count                  # number of records
omn export                 # every record as JSON (great for you to inspect)
omn information ID         # one record as JSON
omn put SOURCE [--no-copy] # copy a file into artifacts, print its file:// URI
omn mv SOURCE DEST [-f]    # move an artifact + rewrite file:// refs in records
omn get SOURCE DEST        # copy an artifact out of the artifacts folder
```

When the user asks about their courses, deadlines, or schedule, run these and
read the JSON. `export`/`information` return machine-readable output; prefer
them for analysis over the human `list` table.

## Query syntax (taskwarrior-style)

The query language is modeled on Taskwarrior filters — this is the mental model
to use when helping the user search, and the grammar the `omn-parser` crate
implements:

- `type:task` — filter on the record type
- `meta.due.before:tomorrow` — range/relative checks on metadata
- `+canvas` / `+tag` — require/deny a tag
- boolean `and` / `or` and parentheses for grouping

Filters combine into a single SQL-over-records query. Exact relative-date words
(`today`, `tomorrow`, `eom`, `now`) and ranges (`<`, `>`, `before`, `after`)
follow the `` taskwarrior `` vocabulary so muscle memory carries over.

## Notes

- Artifacts are intentionally opaque: `file://` URIs are identity/location
  handles. The core never dereferences or repairs them, so a `mv`-moved or
  missing file is expected, not a bug in omn.
- `omn` records facts; it does **not** create or move tasks in Taskwarrior.
  When you compare the user's taskwarrior plan against these facts, read both
  stores and report differences — do not silently promote a fact into a task.
