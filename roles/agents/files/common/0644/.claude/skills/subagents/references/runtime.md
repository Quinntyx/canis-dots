# T3 delegation binding

## Preparation

- This profile runs inside a T3 Code environment with the `t3-code` MCP server attached. The MCP
  supplies delegation; the coordinator (this thread) owns scope, acceptance, dependencies, resource
  ownership and side-effect receipts.
- Call `orchestrator_capabilities` once per thread before the first `delegate_task`. It lists
  providers, models, options (such as effort settings) and runtime modes. Call it again only after
  an error or a user-named provider change. Pass child model/option overrides in `target`:
  `target.model`, `target.options` (list of `{id, value}` objects or a map). Given values override
  inherited ones; `[]` or `{}` clears options. A named provider not in the list is unavailable:
  say so, never silently fall back.
- Make no checkout for a child in the shell or inside the task text. Checkouts are T3's job through
  `isolation: 'worktree'`.

## Launching

- `delegate_task(task, target, role, isolation, mode, timeoutMs, interactionMode, runtimeMode,
  title, clientRequestId)`. Only `task` is required.
- `task` is the child's entire universe: give it the outcome, ready inputs by path, workspace
  authority, permitted effects, acceptance checks and report destination. A self-contained brief
  makes the child browsable later in the T3 UI.
- `role`: `implementation`, `research`, `review`, `design`, `test` or `general` — a routing hint to
  the child's setup, not an execution label.
- `isolation`: `'shared'` (default) runs at the parent checkout — right for read-only and
  non-conflicting children. `'worktree'` creates a new prepared checkout from the parent commit on
  its own branch; uncommitted parent edits stay out. PR publication still requires task authority.
- `mode`: `'async'` (default) returns immediately; the child's completion arrives as a wake turn.
  `'wait'` blocks only when this turn cannot proceed without the result; default wait timeout is
  10 minutes and a timeout does not cancel the child — the result still arrives later.
- `runtimeMode`: omit unless the user asks for a specific one. Above-the-parent modes are rejected;
  `inherit` stays inside the ceiling. `interactionMode: 'plan'` plans before editing.
- Keep `title` meaningful: the T3 UI lists children by it.
- Do not create top-level threads for delegation. `t3_thread_launch` / `create_threads` are for a
  user-asked new thread. A `worktree` delegate is the correct substitute for "give it its own
  workspace" in ordinary parallel work.

## Completion and failure

- Do not poll a running child: no `task_status` before its completion wake, no sleep loops.
- `task_status(taskId)` reads one delegated task: `workState` is `working`, `waiting_for_children`
  or `result_available`; `summary` is the final result and reading it marks it delivered. On a
  provider-throttle retry, resume exactly where the interrupted step left off.
- On a Claude host, supported `t3_background_wait([taskId], waiting)` can retain Working while
  background children run; `waiting:false` clears it. Other hosts follow `next`. Do not use it for
  intentionally retained dev servers/watchers, which are environment resources rather than children.
- Read a child thread with `t3_thread_read(threadId)` when you need its transcript rather than its
  final summary; in a reply, name the thread as its `link` verbatim.

## Steering, repair and review continuity

- Follow a running delegate's `next` instruction; do not steer it off-turn except with
  `t3_thread_send(threadId, message, mode)` when the child is a steering target and the user asked
  for live guidance. Steering is not a review or re-check — those are always a new
  `delegate_task`.
- Stop a replaced or no-longer-needed run with `task_cancel(taskId, reason)` — it stops the task,
  its queue and its PR watches. Never use `t3_thread_interrupt` on a child's `childThreadId`.
- Repair only small review findings yourself; start no delegate for them. Every new review or
  re-check is a new `delegate_task` with a brief containing the findings and objections — never a
  `t3_thread_send`, never a resumed session. A delegate task is one shot.
- Retry a failed child as a new `delegate_task`, citing the failed child's summary and diagnostics
  in the new brief; keep the failed `taskId` in the record with its actual failure text.

## Model resolution and task settings

- `../model-selection/SKILL.md` owns child model defaults, tiers and effort. Resolve its choice
  through `orchestrator_capabilities` output and set it on the child with `target.model` /
  `target.options`. Registration does not imply quota; retain the child's actual startup failure
  when a selected model cannot execute.
- `timeoutMs` in `mode:'wait'` expresses an operational wait boundary, not the child's lifetime
  limit. Delivery deadlines belong in the brief.
- Same-repo concurrent writers use T3 worktree isolation after verifying the bound project.
  Distinct coordinator-prepared repositories may each have one exclusive shared-mode writer with
  exact path ownership. A path in a brief does not change the repository T3 isolates.
- These are T3 bindings under the parent contract. Native eligible children use their native join,
  not T3 task-status/cancel tools. Select checks through the shared verification ladder.

## Claude Code binding

Discover T3 MCP tools with native `ToolSearch`; read the actual schemas. The T3 branch requires
the `t3-code` server in the current session. Native foreground Agent IDs and T3 task IDs are
different. Standalone Claude sessions without T3 cannot perform managed allocation, T3 secret
entry, durable T3 schedules, or thread operations; report the precise blocker.
