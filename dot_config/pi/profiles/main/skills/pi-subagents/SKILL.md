---
name: pi-subagents
description: >-
  Use when the task fits dynamic subagent workflows — fanning work out across
  multiple agents (per-file audits, cross-checked research, migrations,
  multi-angle plans), when the user asks for subagents/workflows/parallel
  agents, or whenever orchestration of several pi instances is needed. Covers
  spawning, monitoring, steering, and collecting results from pi subagents via
  the pi_subagents Python API inside PTC sessions. NOT for single-step tasks or
  simple multi-tool calls.
---

# pi-subagents: dynamic subagent workflows through PTC

This environment has a native subagent orchestration system. There is **no MCP
server, no Task tool, and no background-runtime** for this: subagents are
spawned **from Python code running in a `python_exec` chunk** via the
autoimported `pi_subagents` module. Do not look for another mechanism — this is
the one.

## The workflow (always this shape)

1. `provision_python_session` — once per task (optionally with a seeding script). Returns a session id.
2. `python_exec` — **one synchronous chunk that does the whole fan-out**: define
   the prompts, spawn subagents, wait for them, aggregate, return the summary.
3. `python_session_to_script` — when the orchestration stabilizes and should be
   rerunnable, export it as a durable script.

Run everything **synchronously inside a single `python_exec` chunk**. Do not
use `background: true` (it is WIP/deferred and currently disabled). Blocking is
the intended behavior: while the chunk runs, a live subagent viewer renders
under the code view in the transcript, so the user can watch each agent's
status, tool calls, thinking time, and current activity in real time.

Do **not** split one task across several parallel `python_exec` calls in the same
message. A session has one interpreter, so those calls are serialized: the later
ones wait (reporting `Queued: …`) instead of streaming, and each sees the
namespace only as of its turn. One chunk that does the whole job is faster and
renders better.

## API

```python
import pi_subagents as subagents   # also autoimported as `subagents`

# Label phases (optional but recommended for the live viewer):
subagents.phase("reading sources")          # agents spawned after this group under this label
subagents.phase(None)                       # close the current phase

# Spawn — returns an AgentHandle immediately, does NOT block:
h = subagents.agent("Analyze the failing tests in tests/ and report root causes",
                    name="test-digger")      # unique short name, shown in the viewer

# Await the settled result (str when no schema, dict when schema given):
resp = await h                              # AgentStrResponse(str)
d = await subagents.agent("Classify these tests", name="c",
                          schema={"type": "object",
                                  "required": ["root_causes"],
                                  "properties": {"root_causes": {"type": "array",
                                                                 "items": {"type": "string"}}}})
d["root_causes"]                            # AgentDictResponse(dict)

# Fan out N agents and wait for all of them (responses in input order):
handles = [subagents.agent(p, name=n) for n, p in prompts]
subagents.phase("aggregation")              # optional second group
responses = await subagents.wait_all_async(handles, timeout=900)

# Mid-flight control (each is also available as send_async/abort_async/resume_async):
h.send("focus on the auth module first")    # steer between tool calls
h.abort()                                   # stop the current run ("pause")
h.resume("continue with X")                 # re-send a prompt; the session continues
h.kill()                                    # abort + close the tmux window

# Inspection — responses are str/dict, plus .get_session():
s = resp.get_session()
s.tool_calls   # [{tool, arguments, durationMs, isError, result_preview}]
s.thinking     # concatenated thinking blocks
s.prose        # assistant text
s.trajectory() # ordered event stream
s.turns; s.duration_ms; s.session_file

subagents.list()        # snapshot rows for every spawned agent
subagents.stop_all()    # abort everything spawned by this session
```

## Rules

- Top-level `await` is already available inside `python_exec` — `await h`, never `asyncio.run(...)`.
- Cap fan-outs sensibly (`PI_SUBAGENTS_MAX_CONCURRENT`, default 8) and prefer small, focused prompts per agent; each subagent's context is isolated, so pass file paths and context **inside the prompt string**.
- Spawned agents cannot spawn agents (they run at depth 1; `import pi_subagents` raises there).
- Statuses: `starting → running → settled`, or `stopped` (aborted), `failed`, `dead` (pi died). `await` on an aborted handle raises `ValueError: await on closed handle` — resume explicitly with `h.resume(...)` first.
- Deadlines: `wait_async(timeout=...)` defaults to `PI_SUBAGENTS_SETTLE_TIMEOUT` (30 min). Set explicit, generous timeouts for long fan-outs.
- `python_exec` uses an **idle** timeout (`PTC_EXECUTION_TIMEOUT_MS`, default 270s): every interpreter frame — progress, output, nested tool calls, and each subagent activity update — re-arms it. A fan-out may run for hours as long as agents keep reporting; the chunk is only terminated after that window with no activity at all (and the session is then disposed, so provision a new one).
- Each subagent is a real interactive pi in its own tmux window — the user can watch and steer them by hand at any time.
- When a fan-out pattern is worth rerunning, export the session (`python_session_to_script`) and commit the script.
