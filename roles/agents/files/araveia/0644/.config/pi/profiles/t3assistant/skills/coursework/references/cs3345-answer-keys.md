# CS3345 worked answer keys

## Scope and defaults

Use this reference after verifying a CS3345 data-structures offering, including its theory
assignments. A generic programming request routed through `cs-3345.md` does not establish that
identity. Apply this reference alongside the relevant mathematical/programming workflow.

Every assignment preparation or resumption must produce or update a complete worked answer key
by default. The user need not request the key again. This standing preference satisfies the
generic mathematical route's "when requested" condition. An explicit narrower request still
wins: inspection-only work does not start preparation, and a browser-only Codio handoff does not
authorize writing code in the live activity. Timed/attendance access boundaries and the
prohibition on submitting remain unchanged.

## Read private course preferences first

Locate `COURSE_PREFERENCES.md` in the verified course's existing directory under the configured
private coursework workspace. Read it before drafting or resuming. Resolve matches by actual
course/term evidence, not by choosing the first filename. Keep the student's identity, exact
term, paths and assignment history in that private record, not in this reusable skill.

- Populate the answer key's name field with the student's configured full name on every key.
  Never substitute "Your Name," "Reference Answer Key," or an agent name. Preserve existing
  user edits. If the preference is missing, use an already verified user-edited header; ask only
  if the identity is genuinely unknown or ambiguous. Distinguish the key from independent work
  through its file/role, not by replacing the student's name.
- Deliver the editable source and compiled PDF in the established visible assignment directory,
  following prior assignment naming. Internal `.private/` builds are not the sole delivery.
  Identify the canonical file before editing, merge rather than discard user changes, and keep
  generators, checks and path records pointed at that canonical file.
- Reuse the supplied template and retain question wording and original source files. Keep the
  blank independent attempt separate. Follow the private preference on any resources section;
  retain source provenance separately when the key should not contain one.

## Course coverage and notation

Read the actual relevant slides before writing the key. Record which lecture/pages support the
methods, definitions and notation used. A download, an empty text extraction, a lecture title,
or general knowledge is not evidence that the student has covered something.

Use only material introduced in the course by that assignment, together with definitions and
requirements supplied in the assignment itself. Textbooks may clarify covered material, but do
not authorize introducing later methods or notation. If slides cannot be read or coverage is
uncertain, identify the missing evidence, finish only supported portions, and do not present an
unverified extension as something the student should already know.

The standing notation default is **Big-O only** until an actual course slideshow introduces a
new notation. Keep the correct function inside O( ), such as O(log N); do not label every
operation O(N). Do not use Theta or Omega notation before its own introduction is verified.
Record the lecture/page when that restriction is lifted for a particular notation. Explain
necessary work in ordinary language when appropriate; never replace a mathematical lower bound
with Big-O mechanically or make a false claim just to avoid another symbol.

## Writing and separate decision log

Read and follow the private writing preferences. Explain the reasoning in connected, grammatical
prose rather than compressed strings of facts. Use the problem's vocabulary, defining additional
terms before using them. Remove table-reading directions, redundant summaries and commentary
about how the document is laid out. Do not remove necessary reasoning or assumptions to make
an answer shorter. Keep pseudocode in ordinary Python-style code blocks unless the user changes
that preference.

When a problem supplies a visual, prefer a sequence of diagrams with arrows and short
annotations showing what changes. Draw intermediate states, not just the final result. For
binomial-heap merging, show the forest at each linking step, with an arrow from the root being
attached to its new parent and a clear retained-tree annotation when needed. Drop accompanying
link-by-link prose and symbolic tree descriptions that merely duplicate those drawings. Use
formal notation or a formal proof when the problem explicitly asks for it; the visual preference
does not remove a requested proof or excuse an unexplained, ambiguous diagram.

For every key, create or update `writing-decisions.md` beside the delivered files, outside the
key. Record the assignment/date, concrete edits actually made and why they improve clarity,
any short before/after example worth preserving, course-coverage/notation evidence, and any user
feedback applied. Keep this brief and specific; do not paste a generic checklist or claim edits
that were not made. Carry lasting preferences into `COURSE_PREFERENCES.md` so later assignments
benefit, rather than leaving the feedback only in a build log.

## Verification and handoff

Check the full name in both source and rendered PDF. Check every question is answered, the
reasoning stays within verified course coverage, the requested notation is respected, and user
edits survive regeneration. Compile and open every final PDF page; saving alone is not enough.
Link the canonical editable source and PDF in a concise handoff. Keep submission and independent
learning unconfirmed unless the user supplies the corresponding evidence.
