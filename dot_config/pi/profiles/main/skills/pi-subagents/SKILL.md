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
subagents.finish()      # CLOSE every subagent permanently (kills tmux windows)
```

## Choosing a model or effort level

The subagent profile can reach **every** model its pi install knows (610 of them
across 9 providers), so **never guess a slug and never refuse a named model** —
look it up:

```python
caps = subagents.capabilities()          # no catalog dump: counts, providers, defaults, caps
# {"default_model": "deepseek-router/deepseek-v4.1-flash", "default_thinking": "high",
#  "thinking_levels": ["off", ..., "xhigh", "max"], "scoped_models": [...],
#  "model_count": 610, "providers": [...], "max_concurrent": 8, ...}

subagents.thinking_levels()              # valid values for agent(thinking=...)
subagents.scoped_models()                # the subagent profile's picker set (NOT a limit on agent(model=))
subagents.model_slugs("astra")           # every matching slug
subagents.resolve_models("opus")         # matching ModelInfo rows (provider, context, thinking, images)
subagents.best_model_match("astra")      # one pick: .slug, .context, .thinking, .images
```

`best_model_match` prefers an exact slug, then the profile's own default provider,
then first-party entries over proxied ones, so `"astra"` resolves to
`openai-codex/gpt-6-astra` and `"flash"` to `deepseek-router/deepseek-v4.1-flash`.
It returns `None` when nothing really matches (the CLI search is fuzzy and returns
unrelated neighbours, which the helper filters out). When the user names a specific
provider's variant, pass the full `provider/model` slug — exact slugs always win.

The catalog is re-read every couple of minutes (`PI_SUBAGENTS_CATALOG_TTL`), so a
model added since the session started still resolves; a lookup that misses is
re-checked live before giving up. If a model you expected is `None`, try the slug
you know, or `list_models(refresh=True)`.

Prompts have no size limit: they are delivered to the subagent over pi-sock (not
through the tmux command), so a very long prompt is fine.

**Whenever the user names a model or an effort level, resolve it first:**

```python
# "spin up an Astra subagent to review your code"
model = subagents.best_model_match("astra")      # -> openai-codex/gpt-6-astra
reviewer = subagents.agent("Review the diff for correctness", name="reviewer",
                           model=model.slug, thinking="high")

# "use the cheap model for the mechanical ones, max effort for the synthesis"
cheap  = subagents.agent(count_prompt,  name="counter",  model=subagents.best_model_match("flash").slug,
                         thinking="low")
strong = subagents.agent(synth_prompt,  name="synth",    model=subagents.best_model_match("opus").slug,
                         thinking="max")
```

If a lookup returns `None`, or `capabilities()["depth"] > 0` says spawning is
unavailable, say so plainly instead of spawning on an unintended model. Use
`list_models(search)` when you need the full rows (context window, max output,
thinking support, image support) to choose between candidates — for example to
prefer a model with a bigger context for a large migration batch.

## Closing subagents (always do this)

Every spawned subagent is a **real pi process in its own tmux window** — if you
never close them, they pile up as orphaned windows. So the last line of every
fan-out chunk, after the results are in and no resume/steer/history inspection is
needed, is:

```python
subagents.finish()            # close everything this session spawned
subagents.finish(handles)     # or just the handles from this fan-out
```

`finish()` kills the tmux windows and cleans their sockets; it is safe to call
twice. Per-handle equivalents: `h.kill()` (close permanently) vs `h.abort()`
(stop the run but keep the window for a later resume). If the model may still
want to continue a subagent's work, leave that one open and finish the rest.

## Rules

- Top-level `await` is already available inside `python_exec` — `await h`, never `asyncio.run(...)`.
- Cap fan-outs sensibly (`PI_SUBAGENTS_MAX_CONCURRENT`, default 8) and prefer small, focused prompts per agent; each subagent's context is isolated, so pass file paths and context **inside the prompt string**.
- Spawned agents cannot spawn agents (they run at depth 1; `import pi_subagents` raises there).
- Statuses: `starting → running → settled`, or `stopped` (aborted), `failed` (its pi never came up), `dead` (pi died). `await` on an aborted handle raises `ValueError: await on closed handle` — resume explicitly with `h.resume(...)` first.
- Deadlines: `wait_async(timeout=...)` defaults to `PI_SUBAGENTS_SETTLE_TIMEOUT` (30 min). Set explicit, generous timeouts for long fan-outs.
- `python_exec` uses an **idle** timeout (`PTC_EXECUTION_TIMEOUT_MS`, default 270s): every interpreter frame — progress, output, nested tool calls, and each subagent activity update — re-arms it. A fan-out may run for hours as long as agents keep reporting; the chunk is only interrupted after that window with no activity at all.
- **Interrupts never kill the session.** Aborting the call (Esc, or `/ptc interrupt`) or hitting the idle timeout sends Ctrl-C into the interpreter: the chunk stops where it is, and you learn the exact line plus the Python traceback (`Stopped at: chunk line 4: await subagents.wait_all_async(handles)`). A timeout reports that in the tool error field; an Esc abort reports it as a queued `ptc-interrupt` message on your next turn (pi rejects the call with its own AbortError first). The namespace survives, so `handles` and friends are still usable — an interrupted fan-out can simply be awaited again in a later chunk: `responses = await subagents.wait_all_async(handles)`. `/ptc kill` drops the session entirely.
- **Per-subagent model and thinking level**: `subagents.agent(prompt, name=..., model="<provider>/<model>", thinking="high")` passes `--model` / `--thinking` to the spawned pi. Model ids come from the subagents profile (e.g. `openai-codex/gpt-6-astra`), so a request like "spin up an Astra subagent" is `model="openai-codex/gpt-6-astra"`. Use a cheaper model for narrow mechanical work and a stronger one for review/synthesis.
- Each subagent is a real interactive pi in its own tmux window — the user can watch and steer them by hand at any time.
- When a fan-out pattern is worth rerunning, export the session (`python_session_to_script`) and commit the script.
