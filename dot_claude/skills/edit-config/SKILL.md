---
name: edit-config
description: "Use when creating, changing, or removing persistent configuration, dotfiles,
  rcfiles, application settings, Claude Code configuration, or Pi profile files, including managed-source changes."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Requested configuration change, exact destination paths, active host/profile, and permitted effects.
- Access to the owning source and manager; chezmoi source normally lives at `~/.local/share/chezmoi`.
- Publication/application ownership: this agent, a coordinator, or an explicit source-only handoff.
- Approval before tracking secrets or nonportable machine-specific values.

## Output Contract

- Changes in the authoritative source, with validated rendering and only owned targets applied.
- For an assigned complete chezmoi lifecycle: owned changes committed and pushed before application.
- For source-only, no-push, or coordinator scope: validated source changes and pending effects named.
- Task paths clean after completed application; unrelated source changes and live drift untouched.
- A concise receipt distinguishing source, publication, application, and runtime validation.

# Entrypoint

## Stage 1: Establish ownership and scope

1. Read the target and relevant neighboring source, instructions, and manager configuration.
   Record exact task-owned paths and baseline changes; never broaden them to make global status clean.
2. Query `chezmoi managed --path-style absolute -- "$target"` for the exact destination and inspect
   source/external declarations. Use `chezmoi source-path -- "$target"` to locate an established
   source, not as proof of management: it can calculate a path that does not exist.
3. Classify the owner using Other managers below. A chezmoi target goes to Stage 2: Edit source.
   A package/plugin/generated target goes to Stage 1A: Follow the owning manager. A genuinely
   unmanaged personal configuration goes to Stage 1B: Decide adoption. Unclear ownership ends at
   Stage 5: Report with the missing evidence; it never defaults to a direct edit.

## Stage 1A: Follow the owning manager

1. Locate the user's editable declaration, override, or owned upstream repository. Inspect installed
   files for identity only. Read the Git procedure before repository setup or publication.
2. Make the authorized change in that source and use the manager's supported update mechanism.
   Keep secrets out of process arguments and logs. Do not install missing software; report its
   user-run setup command or other prerequisite.
3. Verify the selected installed revision/effective configuration, then go to Stage 5: Report.
   With coordinator ownership, stop at validated source and name the remaining update instead.

## Stage 1B: Decide adoption

1. Consider adoption only for durable personal configuration that belongs on the intended machines.
   Generated output, downloaded packages, credentials, caches, sessions, and databases stay unmanaged.
2. If adoption is authorized, import the current live content deliberately with correct source
   attributes and narrow exclusions, then go to Stage 2: Edit source. Do not sweep a whole directory
   into management. Otherwise make only an authorized direct edit to genuinely unmanaged content,
   validate it, and go to Stage 5: Report explaining why it remains unmanaged.

## Stage 2: Edit source

1. Change only the resolved source paths. Preserve chezmoi attributes, templates, permissions, and
   unrelated edits. Reconcile relevant live drift deliberately; do not overwrite source from live
   simply because a tool recently rewrote it.
2. Keep credentials and runtime state outside tracked source. Add narrow destination-relative
   exclusions to `.chezmoiignore` when needed. Existing committed secrets require an explicit
   revocation/history-cleanup decision, not merely an ignore entry.
3. Use host/profile templates or capability gates for genuine machine differences. Check the current
   host and a relevant alternate render without exposing unrelated data or secrets.
4. Run application syntax checks and inspect the owned diff. Run `git diff --check` in source.
   Validate only the relevant rendered destinations and supporting declarations.
5. A validated self-owned complete lifecycle goes to Stage 3: Publish. Source-only, coordinator,
   no-commit, or no-push scope goes to Stage 5: Report with the appropriate stages pending.
   Failed validation stays in Stage 2 for repair or ends at Stage 5 with a precise blocker.

## Stage 3: Publish

1. Read `../git/SKILL.md` for assigned publication, then verify the intended source branch/upstream.
   Stage exact task paths, review their staged diff, and commit only those paths. Existing unrelated staged content must not enter this commit.
2. Push the assigned branch normally and verify its remote SHA. Preserve concurrent changes and
   unrelated untracked files; do not ask to clean them up or include them for cosmetic cleanliness.
3. A verified push goes to Stage 4: Apply owned targets. A failed/uncertain push goes to Stage 5:
   Report with application pending, after checking whether the remote accepted the commit.

## Stage 4: Apply owned targets

1. For each exact owned file inspect `chezmoi diff -- "$target"`, then run
   `chezmoi apply --exclude=scripts -- "$target"`. List individual files rather than a parent
   containing another agent's work. For a missing owned parent, create only its directory entry
   first with `chezmoi apply --recursive=false --exclude=scripts -- "$owned_parent"`, shallowest
   first. Do not recurse through it to create one file. Broad apply needs whole-configuration scope.
2. Changes to shared templates, ignore rules, or externals require an explicit affected-target list.
   Review it before applying; a shared declaration is not permission to reconcile all drift.
   Inspect applicable hooks too. For file-only work exclude unassigned scripts with
   `--exclude=scripts`; run a necessary authorized hook deliberately, not as an unrelated side effect.
3. For removals, confirm the exact target and source ownership. Ignoring a path or deleting its
   source does not remove an existing destination. Use supported manager removal or authorized
   recoverable cleanup; do not use a global apply as a deletion mechanism.
4. Re-run relevant rendered syntax/effective-configuration checks. Require empty output from
   `chezmoi diff -- "$target"` and `chezmoi status -- "$target"` for owned managed targets.
   Explicitly ignored/removed targets are verified by their intended absence instead.
5. Task-owned drift returns to Stage 2 for deliberate reconciliation. Passing checks go to Stage 5:
   Report. Unrelated drift is outside scope and does not block completion.

## Stage 5: Report

1. State changed source/destination paths, source owner, commit/push result where assigned, exact
   applied targets, checks, and any pending reload or other lifecycle effect.
2. Distinguish a source handoff from applied configuration and actual running behavior. Mention
   unrelated drift only if it affects the task; do not turn its presence into new work.

# Other managers

- Package managers own installed application files and libraries. Use supported user overrides or
  change the package's owned source; do not patch installed files or adopt them into chezmoi.
- Claude plugin managers and Pi's Git/npm package manager own fetched plugins, extensions, and skill caches.
  Change an owned fork and its installation declaration, then update only that package through its
  manager. Record the installed revision rather than assuming a successful pull means activation.
- Generated files belong to their generator, schema, template, or runtime settings. Change that
  source or a documented override; preserve generated state unless regeneration is assigned.
- Symlinks and wrappers can cross ownership boundaries. Resolve the actual target and declarations
  before choosing a source. A missing chezmoi entry does not mean the file is safe to edit directly.
- `.chezmoiignore` describes destination-relative paths and is tracked policy. Ignored entries are
  omitted from desired state; they are neither secret-history cleanup nor automatic file deletion.

# Claude Code ownership

- `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, and owned personal skills can be chezmoi targets.
- `~/.claude.json` contains runtime/auth/MCP state; use supported Claude MCP/settings commands for that state.
- Never adopt `~/.claude/plugins/cache`, transcripts, credentials, or generated installed-plugin registries.
- Changes to skills/hooks must be checked in a fresh Claude session; T3 injects its own MCP and settings.
