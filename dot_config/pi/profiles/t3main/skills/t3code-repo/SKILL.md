---
name: t3code-repo
description: "Use when working in the t3code repository or any fork of it (agent-facing GUI for
  coding agents) - setup, dev servers, verification, tests, PRs, docs, and its lint/taste guardrails."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A change request, bug report, or review task against the t3code repo (upstream pingdotgg/t3code
  or your fork), its checkout path, and the target surface (web, desktop, mobile, server, docs).
- The repo's own agent-surface files: `AGENTS.md` (environment rules, surface checklist, verifying,
  taste), `docs/internals/*` (architecture, testing, effect services, web UI, mobile navigation,
  performance), `CONTRIBUTING.md`, `docs/operations/development.md`.

## Output Contract

- Changes that pass the repo's own verification ladder, honored on every applicable surface.
- Evidence proportional to the change: failing-test-first for logic bugs, before/after captures for
  visual ones, per-surface walk-through notes for frontend work.
- No PR unless explicitly asked; no repo-wide check runs; no plan/scratch artifacts committed.

# Entrypoint

## Stage 1: Read before touching

1. Read the checkout's `AGENTS.md` end to end on entering the repo. Its rules outrank your
   habits: environment safety ("three ways to hurt yourself"), the surfaces checklist, the
   verification ladder, and Taste. Re-read the Taste section before writing code.
2. Read the internals doc for the area before adding code there: `effect-services.md` before server
   work, `web-ui.md` before components, `mobile-navigation.md`/`mobile-development.md` before
   native/mobile work, `testing.md` plus AGENTS.md's Verifying before any test, `overview.md` for
   architecture constraints, `performance-regressions.md` when touching hot paths.
3. If `.t3/setup-running` names a live PID, wait for `.t3/setup-done` or `.t3/setup-failed`; run
   `vp i` only when no marker exists. Read which state actually applies from the dev-runner output.

## Stage 2: Plan surfaces and scope

1. Walk the "Hit every surface" checklist for the requested behavior and record which entries
   apply: entry points, clients (web desktop mobile, `packages/client-runtime`), providers,
   agents/MCP, contracts (`packages/contracts`), reverse states, connection modes, docs.
2. Keep the change at the stated scope: adapters own complexity; orchestration stays pure; UI stays
   dumb. Fight scope creep; prefer reuse of named existing patterns over invention.
3. Plans, research notes and scratch material live outside the worktree. Never commit them.

## Stage 3: Build and verify

1. Iterate with `vp test run <files>`; before any handoff run `vp run check:changed`. Never run
   `vp check`, `vp run -r test`, or `vp run -r typecheck` unasked; CI owns the full suite.
2. Use `vp run typecheck` (never bare `npx tsc`). Run `node -e` snippets from `apps/server` or the
   owning package, not the repo root.
3. Bug proof by class: logic/data/state/protocol failures get a failing test first on `main`'s
   baseline in the module's existing test file, then the fix. Purely visual defects get
   before/after captures, no test. Server-only fixes ship test plus a short runtime transcript.
4. Obey the test-writing rules in `docs/internals/testing.md` exactly: event-sourced waiting via
   `OrchestrationEffectWorkerV2.drain`, `Deferred`, or `Queue.take`; no sleeps, polling loops,
   per-test timeouts, `Date.now()` deltas, or wall-clock browser asserts. Skips need a
   `// quarantine: #<issue>` line. Lint rules `t3code/no-*` and `t3code/require-*` encode these;
   when one fires, take its stated legitimate alternative rather than suppressing it.
5. Lint suppressions need a one-line reason (`// oxlint-disable-next-line <rule> -- <why>`);
   `react-effect-budget` overruns go through the reason comment with the actual motivation.
6. When authorized for a device pass, use the repo's own install paths (`test-t3-app`,
   `vp run mobile:install`, `test-t3-mobile`); one integrated pass by the primary agent only;
   never launch your own dev servers as a subagent.

## Stage 4: Deliver

1. Never open a PR unless explicitly asked. Use conventional commit titles in plain language; body
   states the problem and the fix, ends with the model and harness that did the work.
2. UI changes attach before/after images; motion or timing attach a short video. PR evidence goes
   to GitHub, never into the repo (no `.github/pr-assets/`).
3. One request is one PR. While babysitting, call `watch_pull_request` and end the turn; T3 wakes
   on checks or comments. Verify each bot finding against source; dismiss false positives with a
   written reason.
4. Docs follow AGENTS.md's Documentation rules: internals only for cross-boundary reasoning and
   traps the source cannot show; user docs task-shaped, in the shipped product's voice; rewrite or
   remove stale text instead of appending.

# Pitfall register

- Kill only PIDs you captured at spawn or the confirmed owner of your port checked through
  `/proc/<pid>/cwd`; never `pkill`/`pgrep|kill` by pattern against this repo's process names.
- The dev live database is read-only truth: copy into your worktree's `.t3` sandbox via the
  documented seed/migrate steps; never run a server against `~/.t3/userdata`.
- Never set `VITE_HTTP_URL`/`VITE_WS_URL` for dev; dev is single-origin via Vite proxy.
- `.repos/` references are read-only: mirror their patterns, do not edit or import them.
- Default to no comment; state constraints in at most four lines. Suppression reasons and
  quarantine markers are the two comment categories the lint rules expect to see.
