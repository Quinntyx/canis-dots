---
name: create-report
description: "Use when creating, reviewing, rendering, or sharing evidence-based Markdown reports,
  including research comparisons, illustrated UI or design reports, and tailnet report pages."
metadata:
  type: procedure
compatibility: "Python 3.10+, Pandoc 3; serving also needs Tailscale, tmux, and tmux-jobs."
---

# Contract

## Input Contract

- A reporting question, audience, authorized scope, and Markdown source or permission to author it.
- Available evidence, research sources, artifacts, and relevant production or capture conditions.
- A separate generated output directory; the source directory is never the web root.
- Python 3.10+ and Pandoc 3 for rendering. No Python packages or frontend build are required.
- For serving: an online Tailscale node and the original `TMUX` and `TMUX_PANE` connection.
- The installed `tmux-jobs` executable; set `TMUX_JOBS_BIN` if it is not in its sibling skill.

## Output Contract

- An evidence-based Markdown report with a concise methods opening and content-focused body.
- Clear explanatory footers for every table and figure, plus traceable sources and limitations.
- Externally sourced numeric claims cited immediately with Markdown footnote references.
- A rendered HTML page with bundled CSS/JS, readable tables, footnotes, and large inspectable
   images.
- When requested, an HTTP service and verified MagicDNS URL, with a numeric Tailscale fallback.
- A retained native tmux job handle and concise validation result; no production approval claim.

# Entrypoint

## Stage 1: Scope and evidence

1. Resolve the question, audience, source, intended findings, and authority to edit and publish.
2. Inspect existing artifacts and distinguish direct observations from inference or preference.
3. Record source revision, capture conditions, units, dates, and relevant validation limitations.
4. For UI or design work, collect actual rendered screenshots for the states under discussion.
   Make small text legible; retain original resolution and useful context rather than thumbnails.
5. When authoring or revising content, proceed to Stage 2. For conversion-only work, inspect the
   existing report against Stage 2, preserve its claims, and proceed to Stage 3 with limitations.

## Stage 2: Author the report

1. Open with a short, plain-language description of what was done and how it was produced.
   When agents were used, identify their count, exact model names, orchestration, independence,
   shared starting conditions, and material coordinator intervention. Do not invent agent use.
2. Concentrate production metadata in that opening or a compact adjacent methods block. Thereafter
   discuss findings, design choices, evidence, trade-offs, and recommendations, not the agent run.
   Repeat methods only when needed to qualify a particular result or prevent a misleading claim.
3. Support conclusions with linked evidence. Separate verified behavior, synthetic fixtures,
   source-based interpretation, subjective judgment, and untested capabilities.
4. Put each figure in its own Markdown paragraph with descriptive alternative text. Follow it with
   an italic paragraph beginning `Figure N —` that explains what is shown and why it matters.
   Include its evidence link and any local qualification essential to interpreting that figure.
5. Follow every table with an italic paragraph beginning `Table N —` explaining its scope, rows,
   columns, units, and interpretation where relevant. A title alone is not an explanation.
6. Number figures and tables independently in document order. Do not rely on the viewer's inferred
   fallback captions to satisfy the authored-caption requirement.
7. Use Markdown footnote references and definitions for numeric facts obtained externally. Put the
   reference beside the claim; include the source URL and enough context to locate the value.
   Do not substitute a general bibliography, model assertion, or unrelated link for that citation.
8. Cite internal counts and measurements to actual logs, captures, manifests, or methodology.
   Label estimates and derivations, show inputs when useful, and state unavailable evidence.
9. End with a reasoned conclusion and actionable next steps. Keep reproduction details and optional
   methods material compact; do not repeat the opening throughout the report.
10. Verify facts and citations against the evidence, then proceed to Stage 3.

## Stage 3: Render

1. Resolve this skill directory as `SKILL_DIR`, the Markdown path as `SOURCE`, and a separate
   generated directory as `OUTPUT`. Bind paths to absolute values before invoking commands.
2. Run `"$SKILL_DIR/bin/create-report" render "$SOURCE" --output "$OUTPUT"`.
3. Use `--title` when the filename is not an appropriate page title. Use `--asset-root` only for an
   explicitly authorized parent tree containing the source and its referenced local files.
4. The script copies referenced local files only, rejects escaped or missing assets and directory
   links, and preserves external URLs. It does not publish the source tree or follow dependencies
   inside linked archives, stylesheets, or Markdown documents.
5. Use a fresh output or a directory already marked by `_report.json`. Rerendering updates owned
   output; old copied assets can remain. Choose a fresh output to retire previously linked files.
6. Treat raw HTML as trusted report content: Pandoc preserves it. Do not publish unreviewed active
   content or secrets. The renderer does not fact-check, research, or manufacture citations.
7. The viewer provides 150% image scale, fit/100/150/200% controls, horizontal panning, original
   image links, section navigation, collapsed contact sheets, and table/figure footer placement.
8. If serving is requested, proceed to Stage 4. Otherwise proceed to Stage 5 using a local preview.

## Stage 4: Serve and share

1. Preserve the original `TMUX` and `TMUX_PANE`; bind the original pane ID as `ORIGIN`.
2. Run `"$SKILL_DIR/bin/create-report" serve "$SOURCE" --output "$OUTPUT" --origin "$ORIGIN"`.
   A requested fixed port uses `--port`. Without one, the script selects an available port.
3. Serving renders first, then starts `_host` through `tmux-jobs` using an argument vector. Keep
   its returned `job.pane`, `job.run`, and `origin` together. Do not replace this with shell jobs,
   terminal input injection, output-file redirection, or a different tmux allocation strategy.
4. The default listener is Tailscale IPv4 only. An explicitly requested local preview uses
   `--local`.
   No wildcard binding, public tunnel, firewall edit, or Tailscale configuration change is made.
5. Prefer the returned verified `url`: short MagicDNS name first, full MagicDNS name next, numeric
   address last. Verify the advertised hostname reaches this report, not just that DNS resolves.
   A loopback hostname alias may receive an additional loopback-only listener on the same port.
6. Keep `numeric_url` as a fallback, not the primary link when verified MagicDNS works. Tailnet
   access still depends on the recipient's DNS, membership, and ACLs; do not promise universal
   access.
7. For status or capture, invoke the resolved `TMUX_JOBS_BIN` with `--origin "$ORIGIN"`, followed
   by `status` or `capture` and the returned `--pane` and `--run`. Retain native job output.
8. Stop only an owned server when authorized, targeting its recorded pane. Never kill a process
   merely because it occupies the desired port. Otherwise leave the requested service running.
9. Proceed to Stage 5.

## Stage 5: Validate and deliver

1. Verify that the page, stylesheet, script, figures, linked evidence, and footnote targets load.
2. In a browser, exercise image scaling, horizontal panning, originals, section navigation, and
   footnote links at desktop and narrow widths. Check for document-wide overflow and script errors.
3. Inspect actual images for readability. Confirm every table and figure has a meaningful footer,
   not an inferred placeholder; preserve source links, units, and qualifications after rendering.
4. Confirm the opening explains production once and the rest primarily discusses the subject.
   Audit externally sourced numeric claims for adjacent, accurate Markdown footnote citations.
5. Report the Markdown path, rendered destination, preferred verified URL when served, and any
   unresolved evidence or validation limit. Keep the final user-facing response concise.
