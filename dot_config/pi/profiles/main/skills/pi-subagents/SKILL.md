---
name: pi-subagents
description: "Use when a task fits dynamic subagent workflows - fanning work out
  across multiple pi agents (per-file audits, cross-checked research, migrations,
  multi-stage implement-review-fix loops), when the user asks for
  subagents/workflows/parallel agents/pools, or whenever several pi instances
  must be orchestrated. NOT for single-step tasks or simple multi-tool calls."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A task whose work decomposes into agent-sized units (files, features, topics,
  review passes) or a user request naming subagents, pools, or workflows.
- A provisioned PTC python session (`provision_python_session`), or the ability
  to provision one.
- A tmux environment with the `subagents` pi profile (checked at import; the
  API raises plainly when absent).
- Model or effort-level requests, when the user names them, resolved through
  the catalog helpers rather than guessed.

## Output Contract

- One or more `AgentPool` workflows that submit `Task`s, consume results in
  completion order, and terminate (cyclic workflows gated by a round limit).
- Aggregated findings returned to the caller; durable orchestration exported
  with `python_session_to_script` when the pattern is worth rerunning.
- Every spawned pi window destroyed via `pool.close()` (or `finish()`) before
  the chunk ends, unless results are deliberately kept for follow-ups.
- No orphaned tmux windows, no unclosed pools, no silently ignored failures
  (failed results are reported, not dropped).

# Entrypoint

1. Classify the work: one unit -> single `Task` through a one-slot pool;
   many units or stages -> pool with stages sized to the fan-out. State the
   stages and the termination condition (especially any review/fix cycle and
   its round cap) before writing code.
2. `provision_python_session` once per task (optionally with a seeding script).
3. In ONE `python_exec` chunk: define the tasks, build the pool, submit, and
   consume. Blocking is intended: a live subagent viewer renders under the code
   view while the chunk runs.
4. Consume with `while (result := await pool.pop(timeout=...)) is not None:`
   and route by `result.stage`; submit follow-ups inside the loop.
5. After the loop, either keep specific settled sessions for follow-ups (submit
   with `session_handle=...`) or close: `pool.close()` kills every window and
   invalidates handles. `subagents.finish()` closes all live pools.
6. When the orchestration should be rerunnable, export it with
   `python_session_to_script` and commit the script.

Do not split one workflow across parallel `python_exec` calls: a session has
one interpreter, so the calls serialize and each sees stale state. One chunk
per workflow step; if a chunk is interrupted, the pool survives in the
namespace and the next chunk resumes with `pool.pop()`.

# API

```python
import pi_subagents as subagents   # also autoimported as `subagents`

pool = subagents.AgentPool(concurrency=8, name="migration")
build = pool.stage("build", slots=4)     # slots are soft priority reservations
review = pool.stage("review", slots=4)   # stage names are unique per pool

# A Task is an immutable spec; metadata always carries an integer "rounds"
# (roots default to 0). Prompts have no size limit (delivered over pi-sock).
task = subagents.Task("Migrate module X", name="build-x",
                      model="provider/model", thinking="high",
                      schema={"type": "object", "required": ["ok"],
                              "properties": {"ok": {"type": "boolean"}}},
                      metadata={"file": "x.py", "rounds": 0})

h = build.submit(task)          # returns immediately; status queued
hs = build.submit_all(tasks)    # fan out

# Consume in completion order; None = quiescent (pool stays usable).
while (result := await pool.pop(timeout=3600)) is not None:
    if result.stage is build and result.ok:
        # parent=result copies metadata; only explicit overrides change it
        review.submit(subagents.Task(f"Review:\n{result.body}"),
                      parent=result)
    elif result.stage is review:
        verdict = result.unwrap()          # body, or raises the stored error
        rounds = result.task.metadata["rounds"]
        if not verdict["ok"] and rounds < 5:
            nxt = build.submit(subagents.Task("Fix it", metadata={"rounds": rounds + 1}),
                               parent=result)
    # failures arrive as results (result.ok False, result.error set);
    # only pop timeouts raise (AgentPoolTimeoutError with .pool/.snapshot).

pool.close()   # the ONLY teardown: invalidates handles, kills every window
```

Handle operations: `await h` / `h.wait(timeout)` -> `AgentResult`;
`h.cancel()` (queued or running); `h.send(text)` steers the running turn only;
`h.state()`, `h.activity()`, `h.agent_state()` for inspection. A settled
session continues via `stage.submit(new_task, session_handle=h)` - same tmux
window, new handle and result, old results untouched; omitted model/thinking/
cwd/profile inherit the session, conflicts raise `SessionReuseError`, and
`session_name="..."` renames the live session.

Result fields: `task`, `stage`, `handle`, `body` (str or dict response),
`error`, `status` (settled/failed/cancelled), `duration_ms`, `parent`, `ok`,
`unwrap()`, `session` (tool_calls, thinking, prose, trajectory).

# Model and effort selection

- Resolve every named model: `subagents.best_model_match("flash")` returns one
  pick (exact slug > profile default provider > first-party > proxied);
  `model_slugs`/`resolve_models`/`list_models` give full rows. Pass a full
  `provider/model` slug when a specific provider's variant matters.
- The catalog expires (`PI_SUBAGENTS_CATALOG_TTL`, 120 s) and re-checks live on
  a miss; `list_models(refresh=True)` forces a re-read.
- Budget per stage: cheap fast models for mechanical units, stronger models
  for review/synthesis; set `thinking` explicitly for hard work.

# Rules

- Top-level `await` is available in `python_exec`; never `asyncio.run(...)`.
- Gate every cyclic workflow on `metadata["rounds"] >= N` unless the user
  explicitly says unbounded; `pop()` returning None means quiescent, so an
  ungated cycle never terminates.
- Pop timeouts (`AgentPoolTimeoutError`) leave the pool and work intact: inspect
  `pool.snapshot()` / `pool.handles(status={"queued","starting","running"})` and
  continue in the same or a later chunk.
- Set explicit `Task.timeout` values for models that can fail at the provider;
  an errored turn may otherwise wait out the default settle timeout (30 min).
- `PI_SUBAGENTS_MAX_CONCURRENT` (default 8) caps all pools globally; stage
  slots are priorities, not hard limits - idle slots are borrowed.
- Spawned agents cannot spawn agents; keep orchestration in the parent chunk.
- Each subagent is a real interactive pi in a tmux window titled
  `pi - (subagent) <name> - <cwd>`; the user can watch and steer them by hand.
- Interrupts (Esc, `/ptc interrupt`) stop the chunk, not the pool; `/ptc kill`
  drops the interpreter and orphans running windows - avoid it mid-workflow.
