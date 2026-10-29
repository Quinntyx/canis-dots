---
name: change-report
description: "Summarize local code changes as a narrative Markdown and self-contained HTML report covering the requested changes and decisions."
argument-hint: "[scope: branch | last N commits | ref..ref]"
disable-model-invocation: true
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested repository and change scope: $ARGUMENTS.
- Existing source/history access and report output authority; no publication is implied.

## Output Contract

- A source-backed `report.md` and self-contained `report.html`, or a named missing renderer.
- Coverage of every material change in the verified scope; no invented rationale or testing.

# Entrypoint

1. Read the active Git and runtime-verification skills. Resolve repository, exact base/head and
   uncommitted-change policy from the request. Inspect status before changing anything. Verify the
   chosen commit range; ask only if ambiguity changes coverage. Preserve unrelated work.
2. Read diffs, affected context, tests and relevant history. Explain what changed, its previous/new
   behavior, causal rationale supported by evidence, compatibility and risk. Separate inference.
3. Write the report in an owned task directory, using the existing report directory if established.
   Use detached analyst voice: describe the change, not "we did" or ownership claims. Start with an
   executive summary, scope/revisions, then cohesive subsystem/decision narratives, verification,
   risks and remaining work. Include every material change without dumping the raw diff.
4. Use `../subagents/SKILL.md` only when delegation is justified and permitted. Keep review finite
   and inside user limits; no scout agent, fixed cheap model or automatic three-reviewer launch is
   assumed. Verify source claims and fix observed issues before final rendering.
5. Render using an existing authorized renderer. With pandoc, resolve this skill's actual directory
   and use its `change-report.css` sidecar, `--standalone --embed-resources --toc --toc-depth=3`.
   Keep CSS beside this skill; do not write into Pi's prompt directory. Missing renderer means
   Markdown delivered with HTML generation blocked, not an implicit global installation.
6. Inspect generated HTML structure, links and representative content. Browser inspection follows
   the current browser-work permission gate; otherwise use a permitted existing capture route or
   state that visual validation is incomplete. Do not claim a screenshot was inspected if not.
7. Give report paths and actual checks. If a visual was requested in T3, pass the actual HTML through
   available `html_preview` then `html_render`; file-only delivery is not inline presentation.
