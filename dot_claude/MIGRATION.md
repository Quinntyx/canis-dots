# Pi → Claude Code migration

Prepared 2026-10-29 for Claude Code 2.1.312 through T3 Code on araveia.
This is a capability migration, not installation of Pi extensions into Claude. Pi is unchanged.

## Scope and ownership

- Reviewed the original 23 advertised skills, their routed children/references/helpers, five prompt
  templates plus CSS assets, 17 active package declarations and two transitive runtime dependencies.
  Undeclared cached packages, old GitHub mirrors and the explicitly excluded pi-subagents skill are
  not migration inputs. The full skill audit read 369 files / 1,760,812 bytes, plus 7 prompt files;
  current source was rescanned before copying because it changed while the task was paused.
- Current personal migration: **22 skills + 5 command-template skills = 27 advertised entrypoints**.
  There are seven read-through child skills, five executable helpers and two CSS sidecars.
- `t3code-apk`, present in the original audit, was removed from personal Pi configuration by
  concurrent commit c8b0a8a and moved to its owning T3 repository. This migration preserves that
  ownership and does not resurrect a stale global copy. Use that repository's current skill when
  working there; its discovery belongs to that repository's agent configuration.
- Local source: chezmoi `dot_claude/skills`, `dot_claude/CLAUDE.md`, hooks and settings. Freya and
  Wrangler remain upstream-managed `.chezmoiexternal.toml` targets, not locally patched copies.
- Notebook-workflow and librarian are explicitly Claude-specific adaptations, with source Git SHA
  and tree digests in `migration/manifest.json`; Pi's installed packages are not edited or adopted.
- Personal Claude config lives in `~/.claude`; no Pi profile/environment selector applies to it.
  Claude runtime/auth files, plugin caches and transcripts stay outside chezmoi.

## Skill migration matrix

| Skill | Claude binding / retained capability | Important boundary |
|---|---|---|
| 3d | Native Bash/Read/ToolSearch; complete current parametric/non-parametric tree and helpers | Blender/build123d and authorized scene access remain prerequisites |
| aerc-email | Existing Bash/mail commands, same privacy and synchronization scope | Kept off syssec-canis, which has no mail installation |
| agent-repo-guidance | Native file tools; same repository authority and proportionate evidence | No automatic new lint/CI infrastructure |
| browser-workflow | Native ToolSearch → existing T3 preview tools | Server tab ownership/current browser-work permission; not WebFetch |
| cloudflare | Native web/file/Bash tools, complete product-reference tree | Product APIs/models are subjects, not agent runtime instructions |
| create-skill | Claude roots/loader semantics and supported native/T3 rehearsal routing | Removed hard-coded Pi provider/model; bulk rehearsal stays optional |
| edit-config | Native file/Bash tools; Claude settings/plugin ownership added | Authoritative source and scoped commit/push/apply remain mandatory |
| freya | Unmodified upstream skill through chezmoi external | Actual Rust/GUI/capture environment still required |
| full-send | Native implementation + retained T3 review/PR workflow | Explicit full-send supplies merge scope |
| full-stop | Read-through full-send workflow | Never merge |
| git | Native Bash and all four routed children, retained T3 allocation | Shell/native worktree tools do not rebind managed T3 threads |
| pi-plugin | Claude can still develop Pi packages using Pi's real APIs | Pi is the subject here; rewriting ExtensionAPI into Claude APIs would break it |
| profiling | Native Bash and existing capture helper/runtime | No invented persistent-kernel or trace privileges |
| project-plan | Native files/questions and existing document roles | Planning does not authorize implementation |
| research-book | Native research/local originals, math/build tooling and existing capture route | Fetch summaries are insufficient evidence for exact math/source |
| runtime-verification | Same objective evidence ladder using actual Claude/T3 tools | Missing capture/runtime is reported, not installed around |
| subagents | Foreground native Agent for eligible children; T3 for heterogeneous/isolated/background work | Native model options and T3 target.options/catalog are different |
| terminal-ui | Native Bash + existing real PTY/tmux route | Pi TUI reference remains for Pi development; browsers are not terminal evidence |
| visual-design | Native Read + existing capture/image runtime; retained T3 HTML showback | Input images, screenshots and generation are different capabilities |
| wrangler | Unmodified upstream skill through chezmoi external | Existing project CLI/config/account scope remains authoritative |
| notebook-workflow | Substantive native NotebookEdit + existing runner/MCP adapter rewrite | Editing is not execution; no runner means source-only delivery |
| librarian | Native WebSearch/WebFetch + inspected checkout/full-SHA permalinks | No assumed fetch clone, stored response reader, video analyzer or Gemini fallback |

The five former prompt templates are native, user-invoked skills: `/change-report`,
`/research-report`, `/plan-architecture`, `/repo-explore`, `/pylingual-ab`. They use `$ARGUMENTS`,
co-located CSS, and the shared subagents procedure rather than obsolete scout calls, fixed cheap
models, automatic ten-agent rounds or Pi prompt-directory writes. They retain their output/effect
contracts; `disable-model-invocation:true` prevents unsolicited report commands.

## Plugin migration matrix

A native equivalent below means its documented capability, not byte-identical Pi UI behavior.

| Active Pi package | Claude treatment | Parity / remaining work |
|---|---|---|
| pi-pycells@dev | NotebookEdit + capability-gated existing runner/MCP procedure | **Partial:** no native persistent kernel, namespace, attachment, saved-cell review card or auto plot attachments |
| pi-web-access | Native WebSearch; capability-gated WebFetch + Git/HTTPS-original acquisition | **Partial:** search verified, native fetch blocked on this host; provider chain, response ledger, curator and video analysis absent |
| pi-permissions | Native deny rules for env-file edits + PreToolUse file/command guard | Relevant active rules carried; not a security sandbox |
| pi-block-find-grep | PreToolUse command guard | rg policy preserved, including common pipeline/wrapper/path forms |
| pi-block-inline-python | PreToolUse command guard; saved scripts or actual notebook service | Global hard policy retained; Pi extension's retry-once escape hatch deliberately not copied |
| pi-block-rm | PreToolUse command guard | Recoverable trash policy retained |
| pi-idle-time@dev | UserPromptSubmit timing hook | Per-session local time/elapsed context, machine-local state |
| pi-undo-latest | Native CLI rewind/checkpoint options where exposed; T3's own history UI otherwise | Not a custom Claude /undo port; Pi editor prompt restoration differs |
| pi-continue | Another user turn; native CLI --continue/--resume where appropriate | No Pi hidden trigger-message/filter API port |
| pi-session-move | Durable handoff/resume using supported T3/Claude interfaces | **Gap:** no Pi relocation lineage/restart-script semantics; do not edit transcript JSONL |
| billion-context-pi@dev | Native/T3 compaction, durable notes and bounded research delegation | **Gap:** reversible selective ranges, decompress/search_context and ACP cache ledger absent |
| pi-session-quota@dev | CLIProxyAPI still routes Claude; Pi quota extension is not loaded | **Gap:** dynamic session quota header and quota-aware pause/resume not migrated |
| pi-antigravity-auth | Keep model/account routing in CLIProxyAPI/T3 where supported | Pi OAuth/provider commands are not Claude extensions |
| pi-opencode-zen-free@v0.2.0 | Eligible external-model children remain T3 targets | Native Agent does not acquire the free OpenCode provider/model catalog |
| pi-codex-disconnect-retry | Claude/SDK transport retry behavior | Codex-specific Pi error rewrite is inapplicable |
| pi-setup-command | Use existing/authorized project-local runner setup | Pi /setup and tmux kernel bootstrap not ported |
| pi-update-command | Claude's supported updater / owning package manager | Pi update/clipboard housekeeping is inapplicable |

Transitive `pi-activity` is Pi tool-label/UI infrastructure, not a missing Claude execution tool.
Transitive `pi-sock` is Pi live-session IPC, not Claude's MCP. No unused cache/plugin was enabled.
Stale Pi overrides mentioning intercom/contact_supervisor were not imported: the active audit could
not identify their provider. Existing Pi configuration is not cleaned up as part of this migration.

## Gaps and recommended fixes

### 1. Persistent notebooks — highest practical workflow gap

Native NotebookEdit edits a cell; Bash starts processes rather than preserving Python namespaces.
No notebook-execution MCP was established in the T3 tool catalog. The migrated skill explicitly
selects an existing service/runner or delivers source-only work. It imports libraries explicitly,
saves/inspects figures and does not pretend native private review cards or Pi attachment exist.

**Fix:** expose the Pi-pycells backend through a separately maintained MCP adapter, preserving named
kernels, notebook/output persistence, execution identity/status, cancellation and clean-run checks.
Do not merely rename the tools or assume loading the Pi package inside Claude works. For a smaller
initial solution, add Jupyter/nbclient to the relevant project's local environment and execute saved
notebooks there. That restores execution, not live-kernel parity. No host-wide runner was installed.

### 2. Rich web and video — native web is a reduced adapter

Native WebSearch uses its own backend; gateway support must be exercised, not inferred from tool
presence. Native WebFetch is prompt-directed extraction with different limits, not the entire raw
page or an automatic repository clone. Pi's provider fallback, retrieved-content ledger, curator,
YouTube/video questions and frame extraction are not native equivalents.

**Observed here:** native WebSearch succeeded through CLIProxyAPI. Native WebFetch failed on the
public Claude documentation with `Unable to verify if domain code.claude.com is safe to fetch.
This may be due to network restrictions or enterprise security policies blocking claude.ai.`
The public HTTPS Markdown original was accessible with the already-installed curl client (HTTP 200,
118,669 bytes), so the migrated instructions include saving/inspecting authorized public originals
without disabling TLS verification or bypassing explicit access policy. Fetch is not marked fixed.

**Fix:** use that scoped original-source route for normal public docs; investigate native domain
verification connectivity separately. For missing search/video functionality, configure a supported
search/video MCP or port the separable Pi-web-access backend behind MCP.
Preserve exact-source retrieval and inspected local repositories for implementation evidence.
Existing yt-dlp/ffmpeg can cover authorized media retrieval/frame extraction, with native Read for
manual inspection when the selected model supports images. That does not restore the integrated
transcript/question-focused analyzer, provider fallback or retrieved-content ledger.

### 3. Selective context compression and session relocation

Native/T3 compaction and durable handoff notes are useful alternatives, not Pi ACP reversible range
compression, original-message lookup, cache economics or session-move lineage. An MCP server alone
cannot generally rewrite Claude's provider context/history the way a Pi extension can.

**Fix:** keep Pi available for workflows requiring those exact semantics. Use supported T3/Claude
resume/compaction plus concise checkpoint notes for normal work. Full parity requires host/SDK
integration, not a prompt-only skill or manual session-file copying.

### 4. CLIProxyAPI session quotas

Claude still uses the configured CLIProxyAPI base URL/key helper. Pi-session-quota additionally
injects `X-CLIProxyAPI-Session`, handles provisioned-quota exhaustion and coordinates waiting state
with Pi orchestration deadlines. Native Claude retries are not evidence of this behavior.

**Fix:** implement stable T3-thread/session identity and quota-aware waits in the T3 Claude adapter
or proxy integration, preserving cancellation and child timeouts. A static global header can share
one quota identity and is not per-thread parity. Do not claim the gateway alone restored the plugin.

### 5. Image generation and Pi codemode

Native Read accepts images as input; it does not generate/edit images, invoke Pi classifiers or
provide Pi codemode. T3 HTML showback, browser screenshots and Blender renders are different tools.

**Fix:** configure an existing supported image/model MCP/service if those tasks are needed; preserve
its real output/auth contract. Otherwise use licensed existing assets and report generation as a
gap. No substitute generator or automation stack was silently installed.

### 6. T3 capabilities versus standalone Claude

T3-managed delegation/model catalogs, project/worktree binding, private secret cards, HTML render,
server previews, devices and durable schedules remain available only when the T3 MCP/server host
provides them. They were not Pi-only features and need no duplicate Claude plugin.

**Fix:** use Claude through T3 for those workflows. A standalone CLI needs separately configured
supported MCP access and suitable hosts; never copy temporary T3 auth headers into chezmoi.

## Migration/update process

1. Resolve the active Pi profile and actual package declarations; distinguish active skills from
   excluded skills, cached duplicates, transitive dependencies and repository-local skills.
2. Read complete selected trees plus package README/registration/behavior paths. Record source Git
   SHAs/tree digests. Reconcile source changes since the prior audit; compare manifest identities.
3. Classify every dependency as native Claude, retained T3 MCP, supported adapter or explicit gap.
   Preserve subject APIs: developing a Pi plugin/TUI from Claude still needs Pi's actual APIs.
4. Edit only owning chezmoi/native adapter source. Keep upstream externals upstream-owned. Review
   each changed procedure; never bulk-replace the word Pi or execute a copying script over local
   Claude refinements. Keep helpers/modes, routed references, CSS and provenance together.
5. Validate frontmatter/links/stale executing-host bindings, native settings syntax and hook tests.
   Use realistic missing-tool/source-only/model-choice cases; bulk migrations do not require a
   rehearsal child for every skill. Static checks are not model-behavior proof.
6. Commit/push exact owned paths under the edit-config lifecycle, then review/apply exact files
   through chezmoi with scripts excluded. For shared external/ignore declarations enumerate only
   their affected Claude targets; preserve unrelated Pi or live drift.
7. Verify fresh Claude initialization actually lists the intended skills/tools and exercises hooks.
   Check the real T3 SDK loading path as well as standalone CLI discovery. Run representative web,
   notebook/source-only and native/T3 boundary checks, recording what was and was not executed.
8. Start a fresh Claude/T3 session after adding skill roots/hooks. Existing sessions may retain
   prior system prompts. Use supported skill/plugin reload only when available; do not equate files
   on disk with activation in a pre-existing thread. Report publication, apply and runtime separately.

## Verification and references

- Hook regression command: `node --test ~/.claude/hooks/*.test.cjs` (37 passing regression cases).
- Staged Claude 2.1.312 initialized against CLIProxyAPI/claude-opus-5-5, discovered all 27 intended
  personal entries plus built-ins, fired the timing hook and returned the requested sentinel.
  Native built-ins included plugin-authoring, debugging/review and repository guidance support;
  no duplicate third-party plugin was installed to supply those features. A real foreground native
  Agent canary succeeded once with inherited model and no worktree/extra settings. The initialization
  inventory labels that capability `Task`, while its actual model-facing schema/call is `Agent`;
  tool definitions and executed calls, not a catalog-name substitution, determine the binding.
- Real source-only notebook rehearsal invoked the migrated skill, wrote/read back a valid two-cell
  notebook, preserved null execution counts/empty outputs and explicitly declined to claim a run
  when only editing tools were exposed. Claude executed the PreToolUse and timing hooks successfully.
- Native web rehearsal called both tools once: search succeeded, fetch failed as recorded above.
- Migration manifest records source identities and produced file hashes; it is provenance, not an
  auto-sync instruction or a copy of credentials/runtime state.
- Static validation: valid frontmatter, explicit relative links, helper source attributes, stale
  Pi-only execution references, settings JSON and chezmoi diff checks. Freya/Wrangler validation
  additionally follows their external target rendering, not a local patch. Adapted/new files pass
  whitespace checks; byte-identical reference snapshots retain their original Markdown whitespace.
- Completed representative behavior checks: native foreground child and notebook source-only
  boundary. Further bulk samples remain: T3 allocation, private secret entry, browser permission
  and source permalink generation. No claim is made that all skills have been rehearsed or every
  specialist runtime installed. No new top-level T3 thread was created solely for verification;
  standalone fresh initialization and the T3 adapter's user-settings loading path were checked.
- Official contracts: https://code.claude.com/docs/en/skills,
  https://code.claude.com/docs/en/tools, https://code.claude.com/docs/en/hooks,
  https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/sub-agents,
  https://code.claude.com/docs/en/mcp and https://code.claude.com/docs/en/context-window.
  Runtime help and actual initialization take precedence over newer-doc assumptions.
