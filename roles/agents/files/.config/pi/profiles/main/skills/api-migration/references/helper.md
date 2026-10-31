# Migration Audit Interface

## Invocation and Side Effects

- The installed entry is `bin/migration-audit`; invoke its absolute path or use Python 3.11+.
- Dependencies are Python's standard library, Git and POSIX `fcntl` locking. No installation occurs.
- `scan` reads Git indexes and worktree files. `classify` rereads approved files and sends approved
  chunk snapshots directly to `https://api.typesafe.ai/v1/systemone` when credentials are present.
- Source files, indexes and repository metadata stay unchanged. All artifact destinations resolve
  outside the helper package and every inventory repository. Use a private external run directory.
- Artifacts use mode 0600 on creation, and new artifact directories use mode 0700. Existing parent
  directories and files retain their permissions. Place artifacts in an access-controlled directory.
- The artifact directory may contain sensitive paths, context-derived hashes and search terms.
  Classifier journals store decisions, not source chunks or credentials. Coverage reports overwrite
  their prior version; preserve reports per discovery pass when retaining audit history.
- Each `classify` output directory permits one active process using a nonblocking POSIX lock.
- Exit 0 means the operation succeeded; it does not certify migration completeness. Exit 2 means
  invalid input, a failed operation or selected work not fully classified. Inspect artifacts and
  captured process status. A process interruption can leave an incomplete journal or temporary file.

## Scan Arguments

- `scan --repo ROOT --terms FILE --out FILE` is the required interface.
- Repeat `--repo` for every authorized exact Git worktree root, each with an existing HEAD.
- `--terms` names a UTF-8 JSON array of nonempty single-line literal strings. Matching is
  case-insensitive using Python regular-expression Unicode case matching, with literals escaped.
- `--out` names the inventory JSON file. Use a new path per discovery pass to preserve provenance.
- `--chunk-bytes` accepts 256 through 12000; the default is 6000 UTF-8 source bytes.
- `--max-file-bytes` accepts 1 through 1099511627776; the default is 33554432. Larger files receive
  a full streamed hash, byte count and line count, with `manual_large` status and zero chunks.
  Raise the bound for locally manageable files, or inspect their entire content by another recorded
  method. Each unclassified range stays explicit in the human ledger.

## Inventory Schema

- The inventory has `schema: 1`, `repositories`, `terms`, size bounds, `files` and
  `inventory_sha256`. The hash covers canonical ASCII-escaped JSON excluding its own hash field.
- Each repository has its absolute `root`, `head` and a SHA-256 of `git ls-files --stage -z` output.
- Every tracked path is represented, including README, prose, configuration, fixtures and generated
  files. Every nonignored untracked path is also represented. Ignored untracked files, remote
  repositories and submodule contents require explicit scope reconciliation outside this scanner.
- File records have stable `id`, `repo`, `path`, index stages, origin, status, `chunks` and `hits`.
  Readable regular files also have SHA-256, full bytes/lines and working-tree `mode_bits`.
- Text status means nonempty, NUL-free strict UTF-8. Binary, non-UTF-8, large, empty, conflicted,
  deleted, unreadable, submodule and symlink paths have explicit manual statuses. Text-like binary
  encodings need human decoding and inspection. All suffixes are included.
- Git symlinks and submodule entries receive manual statuses. Filesystem opens use `O_NOFOLLOW`
  on every path component and accept only regular files. Symlink replacement or path escape becomes
  manual work. Submodules become separate repositories only when authorized and passed as roots.
- SHA-256 and counts cover the entire file, even above the text limit. A detected concurrent write
  produces a manual read status. A scan is a sequential snapshot; quiesce writers and compare
  consecutive inventories to establish an exact validation snapshot.
- Every text byte belongs to a chunk; UTF-8 code points stay intact. Chunks have content-bound
  IDs, SHA-256, zero-based half-open byte bounds and one-based inclusive line bounds. Long lines
  can span chunks and share line numbers. Empty files are manual entries rather than lost chunks.
- Hits include literal term, one-based line and one-based half-open character columns. Matching
  spans entire lines before chunking, so boundary-crossing literals are found. Hit records contain
  neither source excerpts nor a claim of semantic relevance. All hits remain in the inventory.

## Classification Inputs

- `classify --inventory FILE --context FILE --selection FILE --out DIRECTORY` is required.
- `--context` names a UTF-8 JSON object with nonempty `migration_contract` and `connected_context`.
  These can be structured JSON values. Include source-derived meaning, type relationships and
  provenance. Additional top-level fields are retained except `items`, which the helper owns.
- `--selection` names a JSON array of unique, approved inventory chunk IDs. Build it from the
  inventory after the transmission review. Every unselected chunk appears as `not_selected`.
- `--out` holds `decisions.jsonl`, `coverage.json` and `run.lock`. Reuse it to resume valid results.
- `--model` defaults to `jev-latest`. Record the actual response model; aliases can move.
- `--key-env` defaults to `TYPESAFE_API_KEY`. Supply the key through that environment variable.
  The helper reads its value only for HTTP authorization and reports missing credentials explicitly.
- `--workers` accepts 1 through 3, default 2; it bounds concurrent HTTP requests and queued bodies.
- `--attempts` accepts 1 through 6, default 4; `--timeout` accepts 1 to 120 seconds, default 45.
  The timeout bounds socket operations, not an entire run or a guaranteed total request deadline.
- `--max-body-bytes` accepts 4096 through 24000, default 24000. ASCII-escaped JSON body admission
  includes state, all questions and rubrics. This conservative byte budget reserves room beneath
  the documented 32k per-question and 64k per-request context limits and 32 MiB HTTP body limit.
- `--dry-run` performs input/hash validation and body packing without HTTP or successful decisions.
  Its planned chunks still need classification; exit 2 is expected when planned work remains.

## Direct API and Routing

- Requests are POSTs to the fixed official TypeSafe endpoint, with Bearer authorization and JSON
  fields `state`, `model` and `questions`. Redirects are rejected. Endpoint selection has no CLI
  override. Alternate providers and similarly named domains are outside this helper's interface.
- State carries the contract, connected context and bounded source chunks. Each `choice` question
  has explicit instructions identifying its chunk in state, plus meaning-bearing criteria for
  `relevant`, `uncertain` and `unrelated`. IDs correlate answers; instructions carry meaning.
- Files are read once per selected file during a pass and verified against inventory hash/mode.
  A mismatch becomes `source_changed_or_unreadable`, including for cached decisions. Source can
  change after that read; fixed-point rescanning and validation bind results to the final snapshot.
- Individual requests that cannot fit become `oversize_request`. Reduce chunk bytes or partition
  connected context and rebuild selection. Every partition needs its own reconciled inventory IDs.
  Content, hits and connecting context are retained completely; omission is never implicit.
- Retries cover HTTP 429, 529, 500, 502, 503 and 504, plus transient transport errors. Exponential
  backoff adds jitter. Retry-After seconds and HTTP dates are honored up to 60 seconds; longer
  delays become `retry_after_deferred` for a later run. Other HTTP errors remain explicit failures.
- Responses must contain the exact question keys, model, nonnegative integer usage and valid choice
  answers. Options and distributions must match, finite values stay in [0, 1], probabilities sum
  to one within 0.001, and the chosen option has maximal probability. Invalid responses fail.
- `inspect` routing includes any file with lexical hits, relevant/uncertain choices, unrelated
  confidence below 0.9 or relevant probability above 0.1. Other decisions use `review_negative`.
  These thresholds route inspection only. Every negative needs reviewer-supported ledger evidence.

## Journal, Resume and Completion

- Each successful journal row contains chunk ID, cache key, request SHA-256, actual model, answer,
  attempts, token usage and route. Usage is per request and repeats across that request's rows.
  Deduplicate by request hash before computing token totals. Failure rows retain explicit errors.
- Cache identity binds chunk/file hashes, root/path, ranges, mode, hits, context, requested model,
  instructions and rubric. Context or contract changes invalidate prior decisions automatically.
  A moving model alias keeps prior recorded decisions; use a versioned model or fresh output
  directory when a fresh model evaluation is required.
- Resume validates cached answer shape, identity and provenance fields. A malformed or partial
  journal causes exit 2. Preserve the original, repair only demonstrably incomplete records or
  start a fresh output directory. Failed decisions are retried on the next invocation.
- Successful rows flush and fsync individually. Coverage lists all chunks and every manual file,
  including omitted selection and credential failures. Interruptions require a resumed run to
  produce a reconciled report. Reports always set `migration_complete` to false.
- `all_selected_classified` concerns only selected chunks. It can be true with an empty selection,
  unselected files, manual files or outstanding human decisions. Reconcile all inventory/ledger
  rows and external scope before claiming completion; classifier confidence is never that proof.
