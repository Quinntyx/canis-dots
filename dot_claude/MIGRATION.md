# Pi → Claude Code migration

Prepared 2026-10-29 for Claude Code 2.1.312 through T3 Code on araveia.
This is a capability migration, not installation of Pi extensions into Claude.
Python kernels, ACP and Pi session relocation are outside the Claude migration scope. Pi retains
those capabilities. Per-session proxy quota integration is discontinued in both configurations.

## Scope and ownership

- Reviewed the original 23 advertised skills, their routed children/references/helpers, five prompt
  templates plus CSS assets, 17 active package declarations and two transitive runtime dependencies.
  Undeclared cached packages, old GitHub mirrors and the explicitly excluded pi-subagents skill are
  not migration inputs. The full skill audit read 369 files / 1,760,812 bytes, plus 7 prompt files;
  current source was rescanned before copying because it changed while the task was paused.
- Current personal migration: **21 skills + 5 command-template skills = 26 advertised entrypoints**.
  The original 17-package audit now corresponds to 16 active Pi declarations after quota removal.
  There are seven read-through child skills, five executable helpers and two CSS sidecars.
- `t3code-apk`, present in the original audit, was removed from personal Pi configuration by
  concurrent commit c8b0a8a and moved to its owning T3 repository. This migration preserves that
  ownership and does not resurrect a stale global copy. Use that repository's current skill when
  working there; its discovery belongs to that repository's agent configuration.
- Personal guidance, skills, hooks and settings now follow Ansible source ownership through
  edit-config: resolve exact destinations with the controller's `scripts/dots-source` and the
  applicable role manifest. Freya/Wrangler remain upstream-owned resources acquired through Ansible
  declarations, not locally patched copies. The older `dot_claude` paths and Chezmoi provenance in
  the migration manifest describe the original audit, not the current deployment procedure.
- Librarian is an explicitly Claude-specific adaptation, with source Git SHA and tree digests in
  `migration/manifest.json`; Pi's installed packages are not edited or adopted.
- The Claude notebook-workflow skill is retired. Use saved scripts with existing project runtimes;
  native NotebookEdit remains available for cell editing. No kernel/MCP bridge is queued.
- Personal Claude config lives in `~/.claude`; no Pi profile/environment selector applies to it.
  Claude runtime/auth files, plugin caches and transcripts stay outside normal Ansible manifests.

## Skill migration matrix

| Skill | Claude binding / retained capability | Important boundary |
|---|---|---|
| 3d | Native Bash/Read/ToolSearch; complete current parametric/non-parametric tree and helpers | Blender/build123d and authorized scene access remain prerequisites |
| aerc-email | Existing Bash/mail commands, same privacy and synchronization scope | Kept off syssec-canis, which has no mail installation |
| agent-repo-guidance | Native /init for authorized new CLAUDE.md; local curation and existing-file repair | No regeneration of existing guidance or automatic lint/CI infrastructure |
| browser-workflow | Native ToolSearch → existing T3 preview tools | Server tab ownership/current browser-work permission; not WebFetch |
| cloudflare | Native web/file/Bash tools, complete product-reference tree | Product APIs/models are subjects, not agent runtime instructions |
| create-skill | Claude roots/loader semantics and supported native/T3 rehearsal routing | Removed hard-coded Pi provider/model; bulk rehearsal stays optional |
| edit-config | Native /update-config for Claude settings semantics, inside resolved-source ownership | Authoritative source and scoped commit/push/apply remain mandatory |
| freya | Unmodified upstream skill through Ansible resource acquisition | Actual Rust/GUI/capture environment still required |
| full-send | Shared native /verify policy layer and one compatible /code-review or T3 review | Explicit full-send supplies merge scope; managed allocation remains mandatory |
| full-stop | Read-through full-send workflow | Never merge |
| git | Native Bash and all four routed children, retained T3 allocation | Shell/native worktree tools do not rebind managed T3 threads |
| pi-plugin | Claude can still develop Pi packages using Pi's real APIs | Pi is the subject here; rewriting ExtensionAPI into Claude APIs would break it |
| profiling | Native Bash and existing capture helper/runtime | Only actual capture/trace privileges |
| project-plan | Native files/questions and existing document roles | Planning does not authorize implementation |
| research-book | Native research/local originals, math/build tooling and existing capture route | Fetch summaries are insufficient evidence for exact math/source |
| runtime-verification | Native /verify owns runtime exercise; local objective tiers and permissions remain | No duplicate proof workflow or unauthorized project-skill bootstrap |
| subagents | Native Agent owns eligible child mechanics; T3 references own managed execution | Native /batch does not bypass T3 allocation or authorize PRs |
| terminal-ui | Native Bash + existing real PTY/tmux route | Pi TUI reference remains for Pi development; browsers are not terminal evidence |
| visual-design | Native /dataviz owns charts; local UI integration, evidence and T3 showback remain | Input images, screenshots, generation and connector publication are separate effects |
| wrangler | Unmodified upstream skill through Ansible resource acquisition | Existing project CLI/config/account scope remains authoritative |
| librarian | Native WebSearch/WebFetch + inspected checkout/full-SHA permalinks | No assumed fetch clone, stored response reader, video analyzer or Gemini fallback |

The five former prompt templates are native, user-invoked skills: `/change-report`,
`/research-report`, `/plan-architecture`, `/repo-explore`, `/pylingual-ab`. They use `$ARGUMENTS`,
co-located CSS, and the shared subagents procedure rather than obsolete scout calls, fixed cheap
models, automatic ten-agent rounds or Pi prompt-directory writes. They retain their output/effect
contracts; `disable-model-invocation:true` prevents unsolicited report commands.

## Native workflow policy layers

Updated 2026-10-29 against the installed Claude Code 2.1.312 SDK command catalog. The native-only
catalog advertises 48 commands; adding the 26 personal entries produces 74, with no exact-name
collisions. These are additive policy layers, not copies of built-in skill bodies:

- `/verify`: runtime-verification selects the evidence tier, target and permitted capture route;
  the built-in owns runtime exercise. Docs/test-only changes use relevant checks. Native project
  run/verify-skill generation stays within the user's repository-writing authority.
- `/update-config`: edit-config resolves the actual manager/source first. The built-in supplies
  Claude settings/hook semantics, without bypassing Ansible source publication or writing live targets.
- `/init`: agent-repo-guidance uses its initial survey/draft only for an authorized new CLAUDE.md;
  existing guidance is curated in place with real local checks and one owner per rule.
- Native `Agent` and `/code-review`: subagents owns routing/limits, not another native lifecycle.
  Full-send selects one compatible independent-review path and reuses shared verification evidence.
  T3 batches use managed delegates, not `/batch`'s automatic native worktrees and PR creation.
- `/deep-research`: research-report retains Markdown/HTML output and evidence requirements.
  The advertised built-in is a dynamic workflow, so it is selected only when explicitly requested
  and compatible with model/child/effect limits. Ordinary reports use native web/original-source
  research without silently granting Workflow authority or starting a second fan-out engine.
- `/dataviz`: visual-design loads it before chart decisions/code and supplies actual product tokens,
  data and output constraints. Broader UI work, capture permission and showback stay local. `/design`
  is an access-consent command in this installation, not a replacement UI or 3D procedure.

Use native `Skill` when the relevant built-in is exposed and compatible with the assignment.
An absent/incompatible recipe is an explicit boundary with the documented existing-project route,
not authority to install a replacement, launch another Claude process or fabricate a tool call.
The separate `3d` tree and all Pi skills are unchanged by this refinement. Bulk static/discovery
checks do not establish end-to-end success of each native workflow through CLIProxyAPI; scoped
per-workflow rehearsals remain a follow-up, not an automatic seven-child campaign.

## Plugin migration matrix

A native equivalent below means its documented capability, not byte-identical Pi UI behavior.

| Audited Pi package | Claude treatment | Parity / remaining work |
|---|---|---|
| pi-pycells@dev | Retained in Pi only; no Claude workflow or adapter | Deliberately outside Claude scope |
| pi-web-access | Native WebSearch; capability-gated WebFetch + Git/HTTPS-original acquisition | **Partial:** search verified, native fetch blocked on this host; provider chain, response ledger, curator and video analysis absent |
| pi-permissions | Native deny rules for env-file edits + PreToolUse file/command guard | Relevant active rules carried; not a security sandbox |
| pi-block-find-grep | PreToolUse command guard | rg policy preserved, including common pipeline/wrapper/path forms |
| pi-block-inline-python | Not carried; inline `-c`/heredoc Python allowed with existing project runtimes | Lifted for Claude: without a Pi-style Python cell runtime there is no preferred alternative to redirect to. Pi keeps its block |
| pi-block-rm | PreToolUse command guard | Recoverable trash policy retained |
| pi-idle-time@dev | UserPromptSubmit timing hook | Per-session local time/elapsed context, machine-local state |
| pi-undo-latest | Native CLI rewind/checkpoint options where exposed; T3's own history UI otherwise | Not a custom Claude /undo port; Pi editor prompt restoration differs |
| pi-continue | Another user turn; native CLI --continue/--resume where appropriate | No Pi hidden trigger-message/filter API port |
| pi-session-move | Retained in Pi only; no Claude relocation integration | Deliberately outside Claude scope |
| billion-context-pi@dev | Retained in Pi only; no Claude ACP integration | Deliberately outside Claude scope |
| pi-session-quota@dev | Removed from Pi's active profile and Claude migration metadata | Discontinued; no adapter or quota-aware wait work remains |
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

### 1. Rich web and video — native web is a reduced adapter

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

### 2. Image generation and Pi codemode

Native Read accepts images as input; it does not generate/edit images, invoke Pi classifiers or
provide Pi codemode. T3 HTML showback, browser screenshots and Blender renders are different tools.

**Fix:** configure an existing supported image/model MCP/service if those tasks are needed; preserve
its real output/auth contract. Otherwise use licensed existing assets and report generation as a
gap. No substitute generator or automation stack was silently installed.

### 3. T3 capabilities versus standalone Claude

T3-managed delegation/model catalogs, project/worktree binding, private secret cards, HTML render,
server previews, devices and durable schedules remain available only when the T3 MCP/server host
provides them. They were not Pi-only features and need no duplicate Claude plugin.

**Fix:** use Claude through T3 for those workflows. A standalone CLI needs separately configured
supported MCP access and suitable hosts; never copy temporary T3 auth headers into tracked config.

## Migration/update process

1. Resolve the active Pi profile and actual package declarations; distinguish active skills from
   excluded skills, cached duplicates, transitive dependencies and repository-local skills.
2. Read complete selected trees plus package README/registration/behavior paths. Record source Git
   SHAs/tree digests. Reconcile source changes since the prior audit; compare manifest identities.
3. Classify every dependency as native Claude, retained T3 MCP, supported adapter, explicit gap or
   deliberately excluded. Preserve the exclusions above instead of restoring retired features.
   Preserve subject APIs: developing a Pi plugin/TUI from Claude still needs Pi's actual APIs.
4. Edit only the owning Ansible/native adapter source resolved by edit-config and the role manifest.
   Keep upstream resources upstream-owned. Review each changed procedure; never bulk-replace the
   word Pi or execute a copying script over local Claude refinements. Keep helpers/modes, routed
   references, CSS and original-audit provenance together.
5. Validate frontmatter/links/stale executing-host bindings, native settings syntax and hook tests.
   Use realistic missing-tool/source-only/model-choice cases; bulk migrations do not require a
   rehearsal child for every skill. Static checks are not model-behavior proof.
6. Follow edit-config for assigned task-branch commits/pushes and separately authorized deployment.
   Ansible uses explicit inventory host/component scope through `scripts/deploy`; components are
   not exact-file filters. Enumerate all affected destinations/handlers before a secret-safe
   `--check --diff` preview. If a component would reconcile unrelated drift, stop for a narrower
   supported plan. Source-only/no-deploy/coordinator handoffs leave application pending. Keep
   secrets in approved Vault `encrypted_files/<host>/...` under `policy/secrets.yml`, never logs/Git
   plaintext. Preserve unrelated Pi source, live drift, and runtime/auth state.
7. Verify fresh Claude initialization actually lists the intended skills/tools and exercises hooks.
   Check the real T3 SDK loading path as well as standalone CLI discovery. Run representative web
   and native/T3 boundary checks, recording what was and was not executed.
8. Start a fresh Claude/T3 session after adding skill roots/hooks. Existing sessions may retain
   prior system prompts. Use supported skill/plugin reload only when available; do not equate files
   on disk with activation in a pre-existing thread. Report publication, apply and runtime separately.

## Verification and references

- Hook regression command: `node --test ~/.claude/hooks/*.test.cjs` (37 passing regression cases).
- Claude 2.1.312 initializes against CLIProxyAPI/claude-opus-5-5, discovers all 26 intended
  personal entries plus built-ins, fires the timing hook and returns the requested sentinel.
  Native built-ins included plugin-authoring, debugging/review and repository guidance support;
  no duplicate third-party plugin was installed to supply those features. A real foreground native
  Agent canary succeeded once with inherited model and no worktree/extra settings. The initialization
  inventory labels that capability `Task`, while its actual model-facing schema/call is `Agent`;
  tool definitions and executed calls, not a catalog-name substitution, determine the binding.
- Native web rehearsal called both tools once: search succeeded, fetch failed as recorded above.
- Migration manifest records Pi source identities and produced Claude file hashes; it is provenance,
  not Claude plugin activation, an auto-sync instruction or a copy of credentials/runtime state.
- Original-migration static validation covered frontmatter, relative links, helper source attributes,
  stale Pi-only execution references, settings JSON and then-current Chezmoi diff checks. Those are
  historical evidence, not Ansible runtime/deployment proof. Future changes use edit-config's
  Ansible manifest/render/application checks; Freya/Wrangler use their upstream acquisition path,
  not local patches. Byte-identical reference snapshots retain original Markdown whitespace.
- Completed representative behavior check: native foreground child. Further bulk samples remain:
  T3 allocation, private secret entry, browser permission
  and source permalink generation. No claim is made that all skills have been rehearsed or every
  specialist runtime installed. No new top-level T3 thread was created solely for verification;
  standalone fresh initialization and the T3 adapter's user-settings loading path were checked.
- Official contracts: https://code.claude.com/docs/en/skills,
  https://code.claude.com/docs/en/tools, https://code.claude.com/docs/en/hooks,
  https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/sub-agents,
  https://code.claude.com/docs/en/mcp and https://code.claude.com/docs/en/context-window.
  Runtime help and actual initialization take precedence over newer-doc assumptions.
