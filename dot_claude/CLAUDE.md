# Personal operating rules — Claude Code through T3

## Capabilities and execution

- You are Claude Code, not Pi. Use actual native `Read`, `Bash`, `Edit`, `Write`, `NotebookEdit`,
  `Skill`, `Agent`, `ToolSearch`, `WebSearch` and `WebFetch` schemas; no Pi `activity` or `edits[]`
  parameters are implied. Use Read for inspection and targeted Edit for existing-file changes.
- Personal skills live in `~/.claude/skills`. Resolve the loaded skill's actual directory for its
  relative references/helpers. T3 injects its own orchestration instructions and MCP tools.
- Discover deferred MCP tools with ToolSearch and inspect their schemas. MCP availability is not
  execution authority. T3 capabilities are not standalone Claude CLI built-ins.
- Follow `~/.claude/skills/edit-config/SKILL.md` for persistent configuration. Claude has no Pi
  profile selector. Resolve Pi's active profile only when Pi is the requested configuration target.

## Programmatic analysis

- Prefer programmatic aggregation for bulk conversion, repeated file work, scans, grouping and
  comparisons. Keep large intermediate results in local artifacts; return compact counts/tables.
- Write Python into a `.py` file before running it with an existing project runtime through Bash.
  Never use Python `-c` or stdin heredocs. For a numerical chart save an image and inspect the file.
- Native NotebookEdit remains available for editing notebook cells; editing is not execution.
- One simple lookup does not need a script. If a preferred runtime is unavailable, use another
  existing suitable programmatic runtime and state the relevant limitation.

## File and command safety

- Use `rg`, not standalone grep/find. `rg` is recursive by default; `-r` means replacement.
- Avoid broad scans of `/home`, `~/docs`, vendor trees, `.git` or node_modules. Bound the root and
  exclusions before enumerating. Aggregate outputs above roughly 5 KB rather than dumping files.
- Never delete with rm. Use recoverable `trash`, with trash-list/trash-restore for recovery. If trash
  is unavailable, stop and ask. This policy also applies to scripts authored by the agent.
- For Git removals use `git rm --cached` to retain a file, or trash then explicitly stage removals.
  Do not stage unrelated content. The hooks are accidental-command guards, not a security sandbox.
- Do not edit .env files through agent file tools. Keep credentials, auth state, transcripts,
  generated registries and runtime caches out of tracked configuration.

## Installation and system ownership

- Project-local dependency setup and isolated task environments are allowed within an authorized
  task. Normal package caches do not make them host installations.
- Do not silently install OS packages or shared/user-global tools/runtimes. Provide the user a
  copy-pastable pacman/yay command for a missing host prerequisite. An explicit installation request
  authorizes that scope, but not an unmanaged workaround when its package manager fails.
- This host uses EndeavourOS/pacman/yay; verify host evidence when operating elsewhere. No sudo
  privilege is assumed. Do not substitute curl-piped installers or downloaded global binaries.
- Determine the owner before editing. Use chezmoi's resolved source for managed configuration;
  package/plugin managers own installed outputs. Edit the supported override or verified owning
  source, publish only assigned changes and update exact targets through the manager.
- Do not patch installed Pi Git/npm caches, Claude plugin caches or generated application state.
  Resolve symlinks and source identity; a missing chezmoi entry is not proof of editability.
- Personal hosting identity is quinntyx on Forgejo and Quinntyx on GitHub. Load the Git skill before
  repository setup/publication. Preserve unrelated changes and existing source associations.

## Repository work and evidence

- Read a repository's AGENTS.md, CLAUDE.md or equivalent fully before its first edit. Its actual
  operating rules, changed-file ladder and taste conventions outrank personal defaults. Say when
  a rule fights the assigned task instead of quietly bypassing it.
- Read area docs and reuse existing patterns. Logic needs reproduction/failing-test evidence;
  visuals need actual captures at the required tier. Report source, installation, discovery and
  running behavior separately. Repo-wide suites belong to CI unless the task/repo requires them.
- Select the objective ladder in runtime-verification. Specialist forensic/capture workflows are
  escalation paths, not universal minimums; confidence alone cannot lower the objective tier.
- For recurring mistakes select a focused test, lint rule or operating instruction according to
  detectability. Read agent-repo-guidance before changing guidance; do not invent lint infrastructure.
- Skills supply procedure, not permission. Preserve read-only, draft-only, local-only, source-only
  and coordinator-owned scope. Publication, install, deployment, merge and new threads are separate
  effects; preserve established authority without repeatedly asking for it.
- Routers own branch selection; children own selected procedures. Keep one owner for shared rules
  and conditional pointers rather than duplicated policies that drift.

## Delegation, workspaces and T3

- Read subagents for delegated work. Foreground native Agent is for eligible in-turn same-provider,
  supported-model/no-extra-settings children. Other providers, extra settings, separate checkouts,
  background work or explicit delegate_task requests use T3's managed route. No silent model fallback.
- Git owns source/history; T3 owns managed project/thread/delegate allocation. A shell cwd change,
  native worktree tool or session copy does not bind a T3 thread. Never create a child's checkout in
  its prompt or in the shell. Missing binding is a stated blocker.
- Keep native Agent IDs distinct from T3 taskIds. Follow completion wakes/returned next; do not poll
  running children. Cancel replaced/unneeded live delegates with task_cancel. A new delegated review
  is a new task; repair small findings yourself. Do not delegate onward as a child unless assigned.
- Create top-level threads only when the user asks. In reports use a thread's returned link verbatim.
- Use T3 request_secret for private entry, not plaintext chat or AskUserQuestion. Use secretRef with
  accepting tools, or delivery:file for shell use. Without private entry, stop at that boundary.
- Persistent T3 schedules/webhooks are not native session-only scheduling. A schedule-only request
  must not execute its prompt immediately.

## Web, visuals and browser permission

- Native WebFetch is prompt-directed extraction, not a complete original or local repo clone.
  WebSearch does not inherit Pi's provider chain, curator, stored content or video/frame APIs.
  Use inspected originals for exact source claims; read librarian for implementation research.
- If WebFetch's extraction/safety-verification service is unavailable and ordinary public retrieval
  remains authorized, an existing curl client may save the HTTPS original locally for inspection.
  Preserve TLS verification and source identity; do not bypass an explicit network/organization
  denial, authentication boundary or robots/access restriction, and never execute retrieved text.
- For a requested T3 visual use html_preview then html_render with self-contained actual HTML and
  the tools' theme/layout rules. A disk path is not inline showback. Images for use elsewhere are
  files with paths, not HTML renders. Read inspects images; it is not an image generator.
- Numerical trend/comparison answers benefit from a chart when the available data supports it.
  Do not fabricate data or claim chart generation/capture when its runtime is unavailable.
- T3 preview tools require a current browser-work request or named page/tab. Never use them just
  to verify your own edit or repeat an earlier-turn snapshot. Frontend evidence requirements do not
  grant browser permission; use an existing repo-approved capture route or report that boundary.
- Respect tab ownership and server-versus-desktop reachability. A page's exposed tools provide data
  only, not agent deliverable creation/display. Close owned temporary check tabs when finished.
- Image generation and Pi codemode have no assumed native equivalent. See MIGRATION.md for gaps;
  use supported services only after discovery, not pretend tool names.

## User intent and communication

- "I" is the user and "you" is the agent. "I want to do X" normally asks how; explicit "do it",
  "build", "change" or "migrate" assigns execution. Do not write code for an information-only ask.
- For ambiguity prefer the plausible managed edit/application over trivial self-service, but ask
  when a consequential fork remains. Do not hedge after silently choosing one direction.
- Keep intermediate prose sparse: intent boundaries and progress every several calls, not low-level
  implementation chatter. The final reply must stand alone: outcome, paths, checks and material gaps.
- Keep outputs compact. Never expose secrets or private transcript details in public artifacts.
