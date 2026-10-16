---
name: research-book
description: "Use when creating a technical mdBook, textbook, or study guide; turning notes or
  papers into a book; or authoring a researched learning guide with step-by-step derivations."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The subject or target system, reader's known baseline, desired depth, and learning goal.
- Supplied papers, local PDFs, repositories, notes, and constraints on source access or versions.
- The requested deliverable format, language, project destination, and delivery authority.
- Available research, PDF/text extraction, rendering, and browser tools; missing tools are
  reportable.
- Infer reversible layout and presentation choices from project context; resolve material
  ambiguity in audience, target identity, source access, destination, or publication before that
  work proceeds.

## Output Contract

- A coherent guide bridging the stated baseline to the target, in the requested project and
  format.
- A source audit, dependency map, curriculum, claim/source locator ledger, and explicit
  uncertainties, scaled to the requested scope; these may share one concise notes file.
- Chapters with prerequisites, intuition, actual derivations, defined notation, and primary
  citations.
- Retained sources, synthesis, applicable extraction notes, and license records within the task
  workspace; supplied sources may remain in place.
- Build, link, mathematics, and rendered-page verification evidence with precise pass/blocked
  status.
- Requested delivery only within the authorized scope, plus reproducible commands and remaining
  gaps.

# Entrypoint

## Stage 1: Bind the study and workspace

1. Read the request, project instructions, existing deliverable, and supplied materials. Resolve
   the reader's baseline, target identity/version, depth, scope, output format, and completion
   criteria.
2. Bind `project_root` to the requested workspace. Record paths for source downloads, extracted
   text, research notes, the source ledger, curriculum, deliverable, and verification evidence
   there. Reuse established paths and preserve existing author content. Keep private research
   separate from distributable content while retaining both within the project context. Scale
   artifacts to the request: a short guide can keep its audit, ledger, dependency map, curriculum,
   and checks in one notes file without extra research directories or chapter expansion.
3. Select the requested format. For a book-shaped study guide without a selected tool, choose
   mdBook. For a focused researched explanation, retain the requested document scale and format.
   Record the choice and renderer requirements; source adequacy and derivation continuity apply
   at either scale.
4. Inventory local tools and source access. Inspect installed tool help, local docs, and project
   configuration before selecting exact commands. Record unavailable tools as pending
   dependencies.
5. If a material input remains unresolved, proceed to Stage 8: Deliver with the specific question
   and retained state. Otherwise proceed to Stage 2: Audit primary sources.

## Stage 2: Audit primary sources

1. Read supplied sources first and identify their relationship to the requested target. Record
   title, authors, date, version, and stable identifier where available; label missing metadata
   honestly. A supplied primary note can be sufficient for the entire requested guide.
2. Trace essential prerequisites to the reader's baseline and identify factual gaps in supplied
   material. Select external research only to close those gaps or meet an explicit research
   request, not to meet a source count. Ground added claims in inspected originals and check
   relevant corrections or revisions. Independently reconstruct derivations even when no external
   research is needed; do not widen the subject or chapter count merely to add sources.
3. Retain supplied sources in place and download additional accessible originals only as needed
   into the bound source directory. Record applicable URLs, retrieval dates, versions, local paths,
   checksums, licenses, and redistribution conditions in the ledger; do not invent metadata for
   local notes. Preserve attribution and notices. Retain restricted material privately and
   distribute only citations or permitted excerpts according to its terms.
4. Read plain-text sources directly with heading or line locators. For PDFs or layout-sensitive
   sources, extract searchable text and inspect original pages for equations, diagrams, tables,
   and notation. Reconcile OCR and extraction errors against page images. Record printed page and
   PDF page indices when they differ; do not require PDF tooling for plain-text notes.
5. Assign stable source and claim IDs. For each substantive claim, record its chapter destination,
   primary source ID, exact section/page/equation or code revision/line locator, and inspected
   support. Distinguish reported result, author interpretation, derived result, hypothesis, and
   open question.
6. Record inaccessible sources, conflicting accounts, missing evidence, and confidence with
   reasons. State their effect on the guide's scope. Use secondary sources for orientation with
   explicit attribution and retain unresolved primary verification as a visible limitation.
7. Write the source audit and dependency map, including why each dependency is necessary and what
   the baseline already supplies. Proceed to Stage 3: Architect the curriculum.

## Stage 3: Architect the curriculum

1. Order concepts by prerequisite edges rather than publication date alone. Trace a continuous
   route from the known baseline through necessary mechanisms to the target; identify optional
   branches.
2. Write a curriculum with chapter learning goals, assumed knowledge, new concepts, required
   sources, key derivations, and observable comprehension checks. Allocate depth to the actual
   learning goal.
3. Define a shared symbol glossary and notation policy. Record each symbol's meaning, domain,
   units, tensor shape and axis order where relevant, and local scope when notation differs across
   papers.
4. Give each chapter a clear role in the argument and a bridge to the next chapter. Introduce each
   prerequisite before its first essential use; provide a focused prerequisite section when
   needed.
5. If essential evidence is missing, return to Stage 2: Audit primary sources. Otherwise proceed
   to Stage 4: Author the guide.

## Stage 4: Author the guide

1. Write the requested deliverable using the curriculum. Explain motivation and intuition, then
   definitions, assumptions, derivation, interpretation, limitations, and its role in the target.
2. Derive important equations through explicit intermediate steps. Name the algebraic,
   probabilistic, analytic, or algorithmic justification for each nontrivial transition. State
   approximation regimes, boundary conditions, normalization, dimensions, and computational
   assumptions before using them.
3. Align notation with original sources or document a precise mapping. Separate the source's
   result from the guide's reconstruction and indicate exactly where each supporting citation
   applies. Explain what the math establishes and what remains an empirical or unverified
   assertion.
4. Write coherent chapter prose and transitions, with local prerequisite reminders, chapter
   summaries, and comprehension checks. Tie comparisons and tradeoffs to cited evidence and stated
   assumptions.
5. Maintain the claim ledger as text changes. Include usable in-text citations and a bibliography
   with stable links and precise locators. Attribute diagrams, quotations, and adapted material.
6. For mdBook, read `references/mdbook.md`, bind `book_root`, and author `book.toml`, source
   chapters, and `SUMMARY.md`. Select one verified math renderer and its actual delimiter syntax.
   Keep raw downloads and private notes outside `book.src`, whose non-Markdown files enter the
   built output. For another format, use its requested structure and record its rendering path.
   Both routes proceed to Stage 5: Verify evidence and mathematics.

## Stage 5: Verify evidence and mathematics

1. Reopen the primary locator for every central mechanism, factual comparison, equation, and
   quoted result. Reconcile guide wording and bibliography with the inspected version and claim
   ledger.
2. Recompute derivations independently at the requested depth. Check symbol definitions,
   dimensions, units, index bounds, assumptions, equality versus approximation, and applicable
   limiting cases. Use symbolic or numerical checks when useful, recording method and tolerances
   in research notes. Treat numerical agreement as supporting evidence with its tested domain
   stated explicitly.
3. Walk the guide from the stated baseline. Resolve forward references, unexplained prerequisites,
   contradictions, unconnected chapters, and gaps concealed by summary-level prose.
4. Record a verification result and unresolved uncertainty for each central claim or derivation.
   Evidence gaps return to Stage 2: Audit primary sources. Writing or math defects return to Stage
   4: Author the guide. A completed audit proceeds to Stage 6: Build and check links.

## Stage 6: Build and check links

1. For a source-only deliverable, resolve local links against source paths and check citation URLs
   with bounded requests and redirects. Record results and unresolved access. Authoring defects
   return to Stage 4: Author the guide; completed source-only checks mark rendering inapplicable
   and proceed to Stage 8: Deliver. Rendered deliverables continue Stage 6 at step 2.
2. For mdBook, follow the build procedure in `references/mdbook.md`. If mdBook or a required
   preprocessor is unavailable, retain complete source and record the blocked build and dependent
   checks. Provide the documented user-install command and proceed to Stage 8: Deliver. With
   available dependencies, continue Stage 6 at step 3. For another format, use the verified
   project rendering command. Successful rendering continues at step 4; authoring failures return
   to Stage 4: Author the guide. An unavailable renderer proceeds to Stage 8: Deliver as blocked.
3. Record tool versions, exact command, working directory, output directory, logs, and exit status
   for `mdbook build "$book_root"`. Run `mdbook test "$book_root"` when Rust snippets require it;
   record its scope as Rust code testing. Other code and derivation checks use their actual
   runtime. An authoring failure returns to Stage 4: Author the guide; a dependency failure
   proceeds to Stage 8: Deliver with diagnostics. Successful commands continue Stage 6 at step 4.
4. Enumerate generated pages and confirm every intended chapter is present. Determine the actual
   HTML output directory from configuration and enabled renderers. Audit rendered links and assets
   with the project checker or an HTML parser: resolve document-relative and site-root paths,
   decode URL paths/fragments, check destination files, and match fragments against emitted IDs or
   anchors.
5. Check external citation URLs with bounded requests and redirects. Record final URLs and
   statuses; classify authentication, rate limits, and inaccessible hosts as unverified rather
   than valid. Cross-check bibliography locators against the retained source ledger.
6. Save commands, coverage counts, broken destinations, and unresolved links in verification
   notes. Authoring defects return to Stage 4: Author the guide. Otherwise proceed to Stage 7:
   Inspect rendered pages, retaining external-access limitations explicitly.

## Stage 7: Inspect rendered pages

1. Discover the available browser tools or project browser runtime and inspect its supported
   actions. For mdBook, start the verified local preview command from `references/mdbook.md` on
   loopback in a retained background job. Record its URL and owned process handle. Other formats
   use their actual renderer preview. An unavailable preview or browser proceeds to Stage 8:
   Deliver with inspection blocked; available tools continue Stage 7 at step 2.
2. Open the actual built pages. Check every chapter for navigation, citations, missing assets,
   browser errors, and rendered equations. Wait for the installed engine's typesetting completion
   and fonts; use that engine version's documented readiness mechanism and observable rendered
   content.
3. Compare central and structurally distinct equations with source pages and authored math.
   Inspect inline and display layout, multi-line alignment, matrices, subscripts, special symbols,
   numbering, and references wherever present. Confirm intended math became rendered math rather
   than raw TeX.
4. Inspect long equations, diagrams, and chapter navigation at reading-width and narrow viewports.
   Verify legibility, horizontal overflow behavior, accessible text, and citation/anchor
   navigation. Inspect screenshots visually alongside DOM or accessibility evidence; HTML
   existence alone proves file generation rather than successful typesetting or readable layout.
5. Save page URLs, viewport sizes, observed checks, screenshots, and console/network failures in
   the bound evidence directory. Stop only the preview process started for this task after
   capture.
6. Rendering defects return to Stage 4: Author the guide, then repeat build and inspection.
   Completed inspection proceeds to Stage 8: Deliver.

## Stage 8: Deliver

1. Assemble requested sources, guide, bibliography, and verification notes. Inspect the actual
   output tree for distribution rights, private notes, and accidentally included downloads before
   packaging.
2. For authorized publishing with the required checks passed, verify the exact destination,
   visibility, deployment path, and included files. Use the project's verified publishing
   procedure and inspect the resulting live pages. Otherwise retain local artifacts and identify
   publication as pending or outside the requested scope. Both routes continue at step 3.
3. Report source and rendered paths, reading entrypoint, build/test commands and outcomes,
   citation and math coverage, inspection evidence, and remaining uncertainty. Distinguish passed,
   failed, blocked, and inapplicable checks. A blocked build leaves rendered/link/browser checks
   pending.
4. Provide the next concrete dependency or decision needed to resume any blocked stage. Preserve
   all research artifacts and the source ledger in the requested project/context, then finish.
