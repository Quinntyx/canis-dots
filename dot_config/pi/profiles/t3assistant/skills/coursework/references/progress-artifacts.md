# Assignment progress, private artifacts, and learning debt

Read on every coursework activation. These are logical fields and operations, not a new service
schema or literal tool catalog. The live MCP schema is authoritative.

## Service path and failure boundary

1. Discover t3assistant's available assignment-service tools and inspect schemas for the operations
   `get_assignment` and `update_progress`. Use the former for the resolved assignment and existing
   progress, and the latter for authorized task-owned changes. Do not pretend either is available
   just because this skill names it. Do not create an ad hoc SQLite/omn write fallback.
2. Preserve stable identity: semester, course/section, service record ID, Canvas host/course ID and
   assignment ID, canonical detail URL, source timestamps, due/unlock/lock bounds and timezone.
   Retain unresolved conflicts with provenance. An iCal override/event ID is not an assignment ID.
3. Save preparation state independently of submission: not started, materials gathered, preparing,
   ready for human, blocked, or user-confirmed completed, mapped only to supported schema fields.
   Include packet paths, material citations, observed tab handoff, next action, blocker, estimate
   provenance, and last verified time. Avoid replacing unrelated progress or an explicit user
   completion with a stale Canvas snapshot.
4. Read back persisted progress. If a write's response is lost, read current state before retrying;
   use revisions/idempotency only when the actual schema supports them. On conflict, preserve
   concurrent user changes and retry only the intended update. Never claim a failed write saved.
5. If the service is absent, deliver a partial result and, when local artifact writes are allowed,
   keep `progress.md` in the assignment directory marked `service sync pending`. Include the
   identity and intended delta for later reconciliation through the service. Do not invent a
   service invocation, trigger background sync, or mutate another profile. Source-only work
   produces source/report files only, not these runtime artifacts.

## Private artifact layout

- Use an existing user-approved private coursework root; otherwise propose
  `~/.local/share/t3assistant/coursework/<semester>/<course-section>/<assignment-id>/` for authorized
  runtime preparation. Use stable sanitized IDs, not untrusted path fragments. Keep unknown term
  or assignment identity explicit and resolve it before creating the final assignment directory.
- Keep `sources/`, `guide.md`, `practice.md`, `checkpoints.md`, optional `reference-answers.md`,
  `progress.md`, and `learning-gaps.md` as needed, not as an obligatory empty-file scaffold.
  Keep full reference answers separate from the concept guide and independently attempted work.
- Directories/materials are private: use owner-only directory access and private file permissions
  when creating them. Keep restricted slides/textbooks local; never commit, publish, or upload
  course materials into a public repository or external sharing service.
- Record each source's Canvas/file ID or stable URL, original name, course/term, retrieved time,
  local relative path, and SHA-256 when bytes exist. Before downloading, check the manifest by
  stable source ID and then content hash. Reuse matching local material; a changed version gets
  a distinct hash/version and provenance, not an overwrite. Across assignments, reuse a verified
  private course `_materials/` copy by manifest path instead of downloading duplicates.
- Cite the actual slide/page or textbook edition/section/page in each explanation. Downloading
  without reading does not support a claim. Mark unavailable pages and missing OCR clearly;
  secondary public sources supplement rather than impersonate assigned materials.
- Before calling an export ready, open/read its actual contents; render PDFs locally with available
  authorized tools to check pages, annotations and legibility. File existence alone is insufficient.
  If rendering is unavailable, record content verification as blocked rather than claiming it
  passed or installing an alternate stack. Final attachment choice and submission stay human.

## Completion and learning follow-up

- Keep learning debt separate from submitted status: concept, specific gap/misconception, evidence
  (attempt/checkpoint/grader feedback), independent practice needed, next review action, and any
  user-agreed follow-up. Seeing a worked solution is not evidence of independent mastery.
- Preparation can be ready while learning gaps remain. A human submission can be complete while
  review remains open. Keep grade/feedback as separate evidence: a low/zero grade may open review
  debt without proving missing submission. User reports are attributed with time; an observed
  receipt includes its assignment identity/time. A downloaded file, open Codio editor, or checked
  prep box is neither submission nor mastery.
- Stop after handing off ready/blocked work and saving the next action. Preserve the dedicated
  browser tab and leave the thread available, not auto-settled. Do not schedule follow-up jobs or
  write Taskwarrior/GCal unless separately requested outside this coursework procedure.
