---
name: research-report
description: "Produce a source-backed narrative report as Markdown and self-contained HTML.
  Wraps native research with the requested evidence, output and T3 execution boundaries."
argument-hint: "<topic or URL>"
disable-model-invocation: true
metadata:
  type: procedure
---

# Contract

## Input Contract

- Research topic/URL and audience: $ARGUMENTS.
- Source access, depth, output directory and any child/model/budget or effect limits.

## Output Contract

- `report.md` and self-contained `report.html`, backed by inspected sources and explicit uncertainty.
- A source ledger and truthful rendering/verification coverage; no fabricated citations or consensus.

# Entrypoint

1. Resolve the question, audience, timeframe, outputs and execution limits. Native `/deep-research`
   is a dynamic workflow in the installed Claude catalog: use it through `Skill` only when the user
   explicitly requested that workflow, it is exposed, and its orchestration fits those limits.
   Use that one research engine rather than starting another report-specific agent fan-out.
   An explicitly requested but unavailable workflow is a stated blocker, not a silent substitute.
2. For an ordinary report without Workflow authority, research directly with native web tools and
   inspected originals. Use `../librarian/SKILL.md` for source-code claims and `../subagents/SKILL.md`
   only for justified, authorized delegation. This report skill does not grant Workflow, extra
   children, provider substitutions or publication authority.
3. Keep a compact source ledger: identity/date, claim, locator and uncertainty. Cross-check important
   claims against independent primary evidence; agents repeating one source are not corroboration.
   Check the native engine's evidence too. Write a coherent account of mechanisms, trade-offs,
   conclusions and unknowns rather than concatenating agent summaries.
4. Preserve Markdown and render with an existing authorized renderer. With pandoc use the co-located
   `research-report.css`, `--standalone --embed-resources --toc --toc-depth=3`. Missing rendering
   capability leaves HTML pending; it does not authorize installation.
5. Check citations, quotations, numbers, links and generated structure. Browser evidence needs
   current browser-work/page/tab scope or an existing permitted capture route. Deliver paths and
   actual coverage. For requested T3 visual showback use `html_preview` then `html_render` with the
   actual HTML; a filename is not display.
