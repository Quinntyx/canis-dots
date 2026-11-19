# One-to-one reference and reusable class templates

Read whenever producing or revising reference answers. A reference is separate from the user's
independent attempt **as an artifact**, not a visibly different kind of homework document.

## Submission-format reference

1. Make a 1:1 submission-format solution: use the actual assignment title, problem order, numbering,
   nested subpart labels, requested deliverables, and appropriate derivation detail. Match the user's
   verified prior submissions and class conventions rather than creating a generic study handout.
2. Do not add a `Reference Answers`, `Separate Reference`, `Draft`, `Human Review Required`, or
   similar header, subtitle, watermark, cover page, or repeated caution. The filename/private notes
   can identify its reference role; the document itself should look like the corresponding assignment.
3. Default to **no citations, source keys, bibliography, lecture/page references, or provenance notes
   in the solution artifact**, unless the user requests them or the assignment explicitly requires
   them. Keep the actual source citations and retrieval evidence in a separate private companion
   note, source manifest, or concept guide. An explicit user request for no citations applies to the
   solution document; it does not authorize discarding the underlying source evidence.
4. Keep preparation status, missing-source inventories, review dates, learning gaps, independent
   practice, access history, and submission reminders outside the solution. Preserve mathematically
   necessary assumptions and interpretations concisely in the relevant answer; never silently repair
   an ambiguous problem or conceal uncertainty that changes a result.
5. Include the explanations, calculations, units, required code, and genuine code output expected in
   the actual submission. Use clear steps, not just final numbers. Do not copy mistakes or unrelated
   content from earlier submissions merely to imitate their style.
6. Match sentence-level grammar and reasoning flow, not a collection of visual habits. Read each
   prose-to-equation transition as a continuous sentence, interpreting symbols as spoken words.
   For example, `Differentiating gives` followed by `therefore f(z)=...` is an incorrect transition;
   use `Differentiating gives` followed directly by the formula. Do not stack equivalent connectives
   or repeat a conclusion mechanically. Review punctuation and what each “so/therefore” actually infers.

## Prior-submission evidence and style

- When prior-submission retrieval is requested or authorized within browser preparation, inspect the
  user's own relevant submissions in the same verified course through read-only Canvas access.
  Download the actual attached files into the private course workspace; do not submit or resubmit.
- Prefer the nearest comparable assignment; use additional relevant submissions to distinguish
  recurring conventions from one-off choices. A local draft is not a verified submitted file. Compare
  hashes when matching an actual uploaded PDF to an existing local source/template.
- Read the real submitted text and inspect representative rendered pages. Match title/name placement,
  fonts, margins, page headers/numbers, problem/subpart labels, math notation, answer boxes, code/output
  sections, and the user's sentence length and explanation-to-equation flow. Do not invent names,
  identifiers, dates, or instructor requirements. Report unavailable access rather than claiming a match.
- Preserve stable assignment/file IDs, submission timestamps and byte hashes privately. Do not retain
  signed download URLs, authentication tokens, or unrelated grades in style notes or reusable skills.
  Historical submission evidence does not establish submission of the current assignment or mastery.

## Shared LaTeX template

When requested, leave a reusable class template beside the class materials, with a blank starter and
a shared layout/macro file. Keep personal details and course-specific evidence out of generic skills.

- Put placeholder title, name/header and problem/subpart content in the blank starter. Supply simple
  commands for the assignment header, problem and part labels, final answers, and code/output blocks.
- Derive the layout from verified submitted work. Preserve its style without forcing unrelated future
  assignments to have the same number of problems or pages.
- Formatting macros must control presentation, not insert logical words or claims. A box helper
  must not automatically prepend `therefore`, an implication sign, or similar connective; write those
  explicitly only where the surrounding sentence and inference warrant them. Keep sentence punctuation
  explicit (for example, optional punctuation outside a box), not accidentally inside result content.
- Deliver plain editable `.tex` files and direct PDF/instruction links by default. Do not create or offer
  a ZIP unless the user asks for one; make shared-file paths and copying instructions straightforward.
- The populated solution must **load that same layout file directly** with `\input` or `\usepackage`;
  do not maintain an independent copied preamble that can drift. Provide concise copy/build directions
  and make required relative paths explicit. Keep one canonical editable solution source.
- Compile and inspect both the populated solution and the blank template. Verify all problem/subpart
  labels, actual mathematical content, absence of reference/meta/citation clutter, template dependency,
  page breaks, boxes and code legibility. Keep source/progress/learning records separately.

The user owns final edits, attachment choice and submission. Matching format and successful
compilation establish neither submission nor independent mastery.
