# AgentPool binding

## Preparation

- Use an explicitly named persistent Python kernel and inspect its existing namespace first.
- Inspect the installed package when signatures differ. The runtime owns scheduling, admission
  identity, reservations and sessions; the coordinator owns dependencies, acceptance, resource
  leases and side-effect receipts. Use public construction/submission to establish admission.
- An inconsistent inherited admission state ends the delegated path with its original error and
  incomplete stages recorded. Resume after the runtime owner restores a valid admission context.
- Import `AgentPool` and `Task` from `pi_subagents`. Pool construction accepts `concurrency` and
  keyword `name`. The default concurrency comes from `PI_SUBAGENTS_MAX_CONCURRENT`; an explicit
  value must be a positive integer within that ceiling. Runtime admission is shared across pools.
- `pool.stage(name, slots=n)` creates a stage; stage names are unique within a pool. Slots are
  non-negative integer soft priorities whose sum stays within pool concurrency. Idle capacity is
  borrowed across stages. A stage with one slot can still run several tasks; hard exclusion belongs
  in coordinator admission or an external resource lock.

## Submission and routing

- `Task` accepts `prompt`, `name`, `model`, `thinking`, `schema`, `cwd`, `agentDir`, `timeout` and
  `metadata`. Set the real launch directory with `cwd`; use the chosen profile with `agentDir`.
- Write a brief containing the overall goal, assigned outcome, ready inputs, workspace, permitted
  effects, acceptance checks and result artifact path. Let the worker select its implementation.
- `stage.submit(task)` returns a handle. `stage.submit_all(tasks)` returns a list of handles.
  Retain stable logical task identities separately from the generated handle IDs.
- Metadata is immutable task lineage, not an external resource lock. `rounds` is a non-negative
  integer. Explicit child metadata overrides inherited fields; the automatic zero preserves the
  parent's round count when it was not explicitly set. Increment repair counters deliberately.
- The coordinator submits dependent tasks after acceptance. Stage creation itself defines neither
  a dependency graph nor a hard resource cap. Keep serial publication in the coordinator or admit
  one publisher handle at a time.

## Completion and failure

- `await pool.pop()` yields completions in observed completion order. `None` means currently
  quiescent; an external producer or later submission may still have work. Preserve producer state.
- `await handle` also returns the result, and that outcome remains in the pool completion queue.
  Choose one accounting path per handle; deduplicate by handle ID when reconciling observations.
- Result fields include `task`, `stage`, `handle`, `body`, `error`, `status`, `duration_ms`,
  `parent` and `session`. Status is `settled`, `failed` or `cancelled`. Only an accepted settled
  body
  releases dependencies. Schema conformance establishes structure, not semantic correctness.
- A failed `pop()` raises `AgentPoolFailureError`; its `.result` is the failed completion and its
  `__cause__` is the underlying error. Catch only at the individual pop boundary, test the exact
  allowed cause type and unit containment, record that handle once, and block its dependents.
- Declare recoverable cause types before scheduling. Confined retained-session diagnostic failures
  can qualify when inputs, artifacts and the shared baseline remain intact. Unexpected causes and
  shared-state uncertainty propagate for coordinator inspection.
- `AgentPoolTimeoutError` carries `.pool` and `.snapshot`; it is a waiting interruption, not a task
  outcome. Provider errors, process death and cancellation carry their real failure semantics.
- Schema repair belongs to the runtime. After its repair policy is exhausted, retain the failed
  outcome and make any further work an explicit coordinator decision with a recorded reason.

## Continuation and lifecycle

- `stage.submit(task, parent=result, session_handle=result.handle)` schedules a retained-session
  continuation and returns a new handle. `parent` carries lineage; `session_handle` selects reuse.
- Reused sessions inherit omitted model, thinking, cwd and agentDir. Conflicting session settings
  raise `SessionReuseError`; a different model needs a fresh task/session with explicit lineage.
- At most one queued or active continuation owns a session. Keep the new handle for every turn.
  `await handle.send_async(text)` steers active work. A terminal send acknowledges scheduling and
  returns a new handle rather than the new agent answer.
- Inspect `pool.snapshot()`, `pool.handles()`, `handle.state()`, `handle.activity()` and
  `handle.get_session()` as appropriate. Inspecting a dormant session keeps it dormant; the runtime
  resumes successful retained sessions only when a continuation is admitted.
- Keep setup, scheduling and teardown separate. Cell interruption preserves the pool. Close only
  the owned pool through `pool.close()` after work and continuation needs end; closure permanently
  invalidates handles. Keep live kernels attached while their pools are active.
