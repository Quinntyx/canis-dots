# Migration Mechanics Sources

## Direct Semantic Screening

- https://docs.typesafe.ai/api.md
  Official POST endpoint, Bearer credentials, state/questions shape, choice answers and retry codes.
- https://docs.typesafe.ai/models.md
  Model aliases, actual response versions and default per-request/per-question context limits.
- https://docs.typesafe.ai/patterns/fan-out.md
  Shared-state question fan-out. Pack related chunks with explicit question targets and complete
  contract context; bound HTTP concurrency independently from the number of questions in a body.
- https://docs.typesafe.ai/llms.txt
  Official documentation index for refreshing endpoint, model and limit assumptions.

## Transformation Selection

- https://martinfowler.com/articles/codemods-api-refactoring.html
  Source-graph discovery, AST transformations, aliases, composition and test-driven codemods.
  Select transformations by binding identity and behavior, then verify actual consumer outcomes.
- https://docs.codemod.com/jssg/semantic-analysis
  Workspace indexing and cross-file definition/reference resolution. Empty reference results can
  reflect unavailable providers or indexing rather than absence of consumers. Check language and
  workspace support before using a semantic query as migration evidence.

## Evidence Interpretation

- Deterministic searches expose exact occurrences; symbol graphs expose linked consumers; semantic
  screening finds conceptually affected prose and code. Reconcile their union in the ledger.
- Generated output is evidence to trace back to its authoritative source and generator.
- Fixed-point discovery plus exact-snapshot validation supports a scoped completion claim.
  Any unreviewed exclusion, unavailable consumer or failed classifier request limits that claim.
