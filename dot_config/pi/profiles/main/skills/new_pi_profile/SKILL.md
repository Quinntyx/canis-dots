---
name: new_pi_profile
description: Use whenever creating a new pi profile. Creates the profile directory layout, symlinks shared config (auth, models, router) to ~/.config/pi/agent instead of copying, ports extensions/skills/settings from an existing profile, and verifies the result.
---

# Creating a new pi profile

Profiles live in `~/.config/pi/profiles/<name>/` and are activated with
`ppi use <name> --` (the fish `pi` function does this; `ppi` sets
`PI_CODING_AGENT_DIR` to the profile dir). The default profile is chosen in
`~/.config/pi/profiles/default.json` (`{ "default": "main" }`).

## 1. Layout

```
~/.config/pi/profiles/<name>/
├── settings.json               model, theme, packages, enableSkillCommands
├── APPEND_SYSTEM.md            extra system-prompt content (auto-appended)
├── extensions/                 .ts factories, all auto-loaded
├── skills/                     <skill>/SKILL.md, auto-loaded (recursive)
├── prompts/                    name.md -> /name prompt templates
├── bin/                        prepended to PATH under this profile
├── auth.json            -> ../../agent/auth.json
├── models.json          -> ../../agent/models.json
├── deepseek-router.json -> ../../agent/deepseek-router.json   (only if router used)
├── models-store.json          real file, per-profile catalog cache
└── git                  -> ../../git                          (optional, shared clones)
```

## 2. Shared config is SYMLINKED, never copied

Point these at `~/.config/pi/agent/` (relative `../../agent/...`, like main):

- `auth.json` — all provider credentials (opencode, opencode-go, openrouter,
  openai-codex, antigravity, zai). Symlinking means `/login` in one profile
  applies everywhere and no credentials get duplicated.
- `models.json` — hand-written provider/model definitions.
- `deepseek-router.json` — router tiers + OpenCode Go quota block (only if the
  profile uses the deepseek-router extension).

Do NOT symlink or copy `models-store.json` as shared state: it is a
per-profile provider-catalog cache (pi refreshes it). `~/.config/pi/agent/`
contains no models-store — give the new profile its own.

`git -> ../../git` (i.e. `~/.config/pi/git`) is optional: main symlinks it to
share package clones across profiles. Only do this when the profiles pin the
same package commits; otherwise pi's `pi install`/reconcile of different pins
into a shared dir will fight.

## 3. settings.json

Base it on an existing profile's settings (mirror main's shape):

- `theme`, `defaultProvider`, `defaultModel`, `defaultThinkingLevel`,
  `enabledModels` (provider/model ids, e.g. `deepseek-router/deepseek-v4-flash`,
  `openai-codex/gpt-5.6-sol`)
- `packages`: `git:github.com/owner/repo@commit` or `npm:name@version` pins.
  Pi installs these into the profile's own `git/` and `npm/` dirs on startup.
- `enableSkillCommands: true` (registers `/skill:<name>`)
- `hideThinkingBlock`, `compaction` — mirror main if desired.
- Provider-specific config like `providers.openrouter.modelOverrides` when the
  router's openrouter tier needs routing pins.

## 4. Port extensions by COPYING the .ts files

Extensions are per-profile code, so real copies are correct (unlike the
symlinked config above). Plain TS factories, auto-discovered from
`extensions/`:

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
	pi.registerCommand("hello", {
		description: "Say hello",
		handler: async (_args, ctx) => {
			ctx.ui.notify("hello", "info");
		},
	});
}
```

Common ports from main: `deepseek-router.ts` (needs the router config symlink),
`undo-latest.ts` (`/undo`), `exit-command.ts` (`/exit`), `opencode-prompt.ts`
(opencode-style editor UI). Deeper APIs import from `@earendil-works/pi-ai`
and `@earendil-works/pi-tui` (dependencies of the pi package; resolvable from
extensions).

Command API: `pi.registerCommand(name, { description?, getArgumentCompletions?, handler: (args: string, ctx) => Promise<void> })` — notify via `ctx.ui.notify(msg, "info" | "warning" | "error")`; completions return `{ value, label }[] | null`. See `docs/extensions.md` in the pi package for tools (`pi.registerTool`) and events.

## 5. Skills & prompts

- `skills/<name>/SKILL.md` — frontmatter `name` + `description` (one line,
  when-to-use). Auto-discovered recursively; `/skill:<name>` when
  `enableSkillCommands` is on.
- `prompts/<name>.md` — becomes `/name` template.

## 6. First run

1. `ppi use <name> --` — packages install, extensions/skills load.
2. `/login` only for providers NOT already in the shared `auth.json`.
3. If the profile is meant to run in a tmux split (e.g. daily_assistant's
   `pi-daily` fish function), make sure the profile `bin/` is on PATH for both
   panes.

## 7. Verify

```sh
ls -la ~/.config/pi/profiles/<name>/      # symlinks point at ../../agent/...
node --check ~/.config/pi/profiles/<name>/extensions/*.ts
```

Reference docs (installed pi package):
`~/.npm-global/lib/node_modules/@earendil-works/pi-coding-agent/docs/` —
`skills.md`, `prompt-templates.md`, `extensions.md`, `packages.md`, `settings.md`.
