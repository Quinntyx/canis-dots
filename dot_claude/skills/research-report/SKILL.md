---
name: research-report
description: "Produce a deeply researched, cross-checked narrative report as Markdown and self-contained HTML, using inspected primary evidence."
argument-hint: "<topic or URL>"
disable-model-invocation: true
metadata:
  type: procedure
---

# Contract

## Input Contract

- Research topic/URL and audience: $ARGUMENTS.
- Source access, requested depth, authorized effects and any child/model/budget limits.

## Output Contract

- `report.md` and self-contained `report.html`, with source-backed claims and explicit uncertainty.
- A source ledger and honest coverage; no fabricated consensus, citations or renderer pass.

# Entrypoint

1. Resolve the question, audience, timeframe and output directory. Decompose it into bounded
   evidence questions. Use native WebSearch/WebFetch for discovery; verify source originals for
   exact quotes, code and numbers. Read `../librarian/SKILL.md` for source-code research.
2. Use `../subagents/SKILL.md` for justified research delegation within the user's limits. Start the
   smallest useful finite roster; no obsolete scout tool, automatic ten-child rounds or guaranteed
   free/Gemini quota exists. Named providers remain exact choices, not fallback suggestions.
3. Maintain a ledger of source identity, date/version, claim, locator and confidence. Cross-check
   consequential claims with independent primary evidence. Multiple agents repeating one source
   are not independent corroboration. Resolve contradictions and discard unsupported assertions.
4. Write a cohesive article in detached analyst voice. Include executive summary, question/scope,
   necessary background, evidence-led sections, trade-offs/counterevidence, conclusions, remaining
   unknowns and references. Explain mechanisms and decision implications rather than pasting agent
   reports or tool logs. Attribute disputed facts and distinguish inference from documentation.
5. Check citations, quotations, quantitative reasoning and claimed coverage against inspected
   evidence. Reuse a scoped permitted review if needed, not an unbounded convergence loop. Apply
   supported corrections; report inaccessible sources and remaining uncertainty.
6. Render with the project's existing authorized renderer. With pandoc use this skill's actual
   `research-report.css` sidecar plus `--standalone --embed-resources --toc --toc-depth=3`. Preserve
   the source Markdown. Missing renderer is a stated HTML-generation boundary, not install authority.
7. Inspect generated HTML links, structure and representative content. Browser evidence still needs
   current browser-work/page/tab scope or an existing permitted local capture route; do not infer
   permission from report generation. State any untested visual boundary.
8. Deliver paths and actual verification. For requested T3 visual showback use available
   `html_preview` then `html_render` with the actual HTML, not a filename or claim of display.
