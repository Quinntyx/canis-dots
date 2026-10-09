---
name: tmux-jobs
description: "Use when running commands expected to exceed 10–15 seconds, interactive commands,
  parallel terminal jobs, or starting, monitoring, capturing, or rerunning jobs in tmux."
metadata:
  type: procedure
compatibility: "Linux, Python 3, tmux with empty panes and respawn-pane; an existing tmux session."
---

# Contract

## Input Contract

- A command argument vector, an absolute working directory, and an existing tmux session.
- `TMUX` and `TMUX_PANE` identifying the agent's original connection and pane.
- Optional stable job label when command arguments change but the job should retain its slot.
- User authorization for the command's side effects; this skill does not grant extra permission.
- Python 3, tmux, `/usr/bin/env`, and `/usr/bin/sleep`; only Python's standard library is used.

## Output Contract

- Visible command output in detached, dedicated job windows within the original session.
- A JSON result containing session, window, pane, run token, state, exit code, and signal.
- Stable pane IDs and geometry across reruns of the same job, without stealing user focus.
- Completed processes exit normally; their inert panes retain output until reuse or explicit
  cleanup.
- No output redirection to files, completion-channel waits, blocked input prompts, or global tmux
  edits.
- Runtime locks reside in the system temporary directory, never in the skill or configuration tree.

# Entrypoint

## Stage 1: Prepare

1. Resolve this skill's absolute directory and use its `bin/tmux-jobs` executable for every
   operation.
2. Bind the absolute working directory and the command's argument vector before calling the helper.
   Do not construct nested shell strings for the helper, tmux, and the command.
3. Preserve the original `TMUX` connection and `TMUX_PANE` across tool calls. If either is absent,
   stop and report the prerequisite. Otherwise continue preparing the invocation.
4. If the caller has changed panes, supply the original ID through the global `--origin` option,
   before the subcommand. Never infer the origin from the currently active client pane.
5. Proceed to Stage 2: Start.

## Stage 2: Start

1. Invoke `bin/tmux-jobs run --cwd` with the bound directory, optional `--label`, and `--` followed
   by the actual argument vector. `run` returns immediately without waiting for completion.
2. Use an explicit shell executable with its command-string option only when shell syntax is needed.
   Never assume tmux's default shell understands Bash. Do not use `send-keys` to launch commands.
3. Keep a label stable across reruns of one logical job. Without a label, identity is the resolved
   directory plus exact command arguments. With a label, identity is the directory plus label.
4. Preserve the returned `pane` and `run` token together. A new run receives a new token even when
   its pane is reused. Never monitor or capture a rerun using a previous token.
5. If the helper reports an error, stop and report it; do not fall back to splitting the active
   pane.
   If the matching job is still running, proceed to Stage 3 using its previously recorded handle,
   or report the busy slot if that handle is unavailable. Otherwise proceed to Stage 3: Monitor.

## Stage 3: Monitor

1. Invoke `bin/tmux-jobs wait --pane` and `--run` with the returned handle. `--seconds` defaults
   to 10, accepts 0–60, and bounds one monitoring interval, not the command's lifetime.
2. If state is `running`, either repeat Stage 3 within the task's time budget or report that the
   job is still running and return its handle. A monitoring deadline must not kill the command.
3. If state is `done`, proceed to Stage 4: Inspect. If state is `empty` or the helper reports an
   error, stop and report the unexpected state, missing pane, stale token, or tmux failure.
4. `bin/tmux-jobs status --pane` with `--run` performs one immediate status check.
5. Completion comes from tmux's retained process state, not a signal the command must emit.
   Inspect `exit_code` and `signal`; helper success alone does not mean command success.

## Stage 4: Inspect

1. Invoke `bin/tmux-jobs capture --pane` with `--run` to read terminal output. `--lines` defaults
   to 200 and is capped at 2,000. Output remains visible in the pane; it is not redirected to a
  file.
2. Report the command outcome, relevant output, and the handle when follow-up is needed.
3. If a rerun is needed, return to Stage 2 with the same directory and job identity. Otherwise
   finish
   without closing the pane or window. No keypress is required after completion.
4. Only when workspace cleanup is requested, invoke `bin/tmux-jobs cleanup` with the original
   origin. It removes completed owned panes and skips running ones, then finish with its result.

# Workspace and Geometry

- The helper creates detached windows named `pi-jobs-<origin>-<number>` in the original session.
- Window ownership is stored in tmux options, not inferred from names. Other agents and user windows
  are not reused, split, renamed, or closed. No session or window index is used as a stable handle.
- An exited matching job is respawned in place; allocation happens only for a new job identity.
- Allocation prefers alternating left/right (`-h`) and top/bottom (`-v`) splits of the largest
  eligible pane. If the preferred axis cannot fit, the other axis is checked before making a window.
- Default minimum child dimensions are 80 columns and 15 rows, with at most four panes per window.
  `run` accepts `--min-width`, `--min-height`, and `--max-panes` to override these constraints.
- A full window smaller than those thresholds stays unsplit; the helper cannot enlarge the terminal.
- Existing layouts are never automatically retiled. Adding a new job changes only its chosen split;
  reruns do not change geometry. Overflow jobs receive another detached window.
- Split slots are empty panes. New windows use a setup-only, 30-second sleep placeholder because
  `new-window` does not support empty panes. Retention is configured before the real command starts.
- Only that newly created placeholder is replaced with `respawn-pane -k`; existing job processes are
  never force-respawned. An interrupted setup leaves at most a bounded placeholder, not a stuck
  shell.
- Concurrent starts are serialized with a bounded runtime lock. A busy job is never overwritten.
  Missing panes are errors, not grounds for indefinite waiting.

# Safety and Lifecycle

- Helper exit 0 means the requested helper operation succeeded; exit 2 means a reported error.
- tmux requests have a five-second timeout. Missing executables or invalid paths are reported.
- Commands retain normal terminal input and output. The user may select the jobs window to interact;
  the helper never switches focus, sends input, or answers prompts on the user's behalf.
- For cancellation, obtain authorization and target the recorded pane explicitly. Do not signal or
  close unrelated panes. Monitoring timeouts are not cancellation authorization.
- Do not place secrets in command arguments or labels. Pass credentials through the normal secure
  environment or credential mechanism. The helper does not persist command arguments in lock files.
- Captured terminal scrollback may include earlier runs. The token verifies the current run's
  identity, not each output line's provenance. Capture relevant output before reuse; terminal
  scrollback is finite and is not an archival or complete log for verbose commands.
- Do not automatically clean up after each command: preserving inert panes is necessary for stable
  rerun locations. Cleanup is explicit and intentionally retires those locations.
