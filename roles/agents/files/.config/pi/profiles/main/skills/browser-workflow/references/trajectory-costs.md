# Trajectory cost calculation

- Stable interface: `bin/trajectory-costs INPUT [--plan PLAN] [--summary]`.
- Runtime: Python 3 standard library. Inputs are local UTF-8 JSON files; output is JSON on stdout.
- The helper reads files and calculates costs. Its only other effect is diagnostics on stderr.
- Exit status 0 means valid input and calculations; status 2 means invalid input or a read failure.

# Recorded input

- Supply a top-level array of operation objects, or an object whose `calls` field holds that array.
- Each operation has `tool` and nonnegative finite `ms` or `durationMs` fields.
- Identity comes from `n`, then `id`, then its one-based position, normalized to a string.
- Other operation fields remain available in output, including page, query, target, and condition.
- The output includes normalized source calls, baseline duration, count, and totals by tool.
- `--summary` returns only aggregate costs and counts for compact verification and reporting.

# Coverage plan

- `retained_ids` lists source identities whose recorded cost and behavior remain unchanged.
- `removed` lists objects with an `id` and an evidence-based `reason` for redundant work.
- `replacements` lists objects with `source_ids`, `tool`, `estimated_ms`, and `reason` fields.
- Every source identity belongs to exactly one retained, removed, or replacement operation.
- A condition-bearing source operation stays retained or maps to a replacement whose
  `completion_conditions` list includes that exact condition.
- One replacement represents one proposed tool invocation. Its cost includes the assumed cost
  of all its underlying actions and required observations.
- The calculated result reports estimated revised calls, duration, and savings. It remains an
  estimate even though its baseline arithmetic is calculated from recorded observations.
