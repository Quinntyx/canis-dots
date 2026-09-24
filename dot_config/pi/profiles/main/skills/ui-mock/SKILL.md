---
name: ui-mock
description: >-
  Run a Lovable-style UI mock design session: spawn a design subagent on the
  design-subagents profile with the mock folder as its cwd, let it drive the
  tldraw mock editor with the user, and collect the final design — which the
  parent then replicates pixel-near in the real codebase.
---

# ui-mock: design-subagent loop

The design loop (propose → annotate → revise → approve) runs entirely inside a
**design subagent** on the dedicated `design-subagents` pi profile. Your job is
to spawn it correctly, wait for it, and replicate the final design.

## Spawning

```python
import pi_subagents as subagents

h = subagents.agent(
    brief,
    name="designer",
    profile="design-subagents",   # dedicated profile: pi-ui-forge tools live here
    cwd=mock_folder,              # durable, your choice of location
)
result = await h                  # resolves when the user approves or closes the editor
```

- **`mock_folder`** is the session home. Choose it deliberately: inside the
  project when the mock belongs with the code, or a dedicated worktree if the
  user wants the mock synced to git. The subagent writes `app/` (React
  source), `dist/`, `ann/`, `shots/`, and `design-notes.md` there.
- **`brief`**: what the user asked for, which pages to propose, product and
  brand constraints. The profile's system prompt and skills carry the design
  discipline — keep the brief about the *product*, not the mechanics.
- **The await is long by design**: the subagent blocks inside a feedback tool
  for as long as the user is marking up the mock. That is the loop working,
  not a hang. Pass a generous `wait_async` timeout (4+ hours) or poll
  `h.status`.
- **Context lifecycle — the subagent is disposable.** Design rounds
  accumulate images in the subagent's context (review canvas shots,
  screenshot reads) and providers cap request size — long sessions start
  failing with 4xx errors (413/400). Watch the context row in the viewer
  (`h.state()`): at roughly **25% or after ~15 review rounds**, finish that
  subagent and spawn a fresh one from the SAME mock folder — it resumes
  from `design-notes.md` (the design contract) and `app/`, which carry all
  state. Never treat the subagent's memory as the source of truth; the
  contract file is.
- Do not spawn extra agents to "help" the design loop; the alternation is
  user-driven and single-threaded.
- You may keep working in your own session meanwhile; the design subagent is
  independent. Only reconcile after it settles.
- When it settles: read `mock_folder/design-notes.md`, look at the page
  images under `mock_folder/shots/` (they arrive in the subagent's final
  summary too), then `subagents.finish()`.

## Replicating the design

The user closing/approving the editor is the *end of the design conversation*,
not the end of your work. **Replicate the approved mock pixel-near** in the
real codebase:

1. Read `design-notes.md` + the final page images (`shots/<last round>/`).
2. Read the React source in `mock_folder/app/` — copy components, spacing,
   colors, and structure as written; it was authored with real ids, dummy
   data, and no incidental state, so it ports directly.
3. Wire the dummy data to your real data sources; keep the visual result
   matching the screenshots closely — the user approved those pixels.
4. Report what you built and where the mock source lives.
