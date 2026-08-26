---
name: edit-config
description: "Use whenever the user asks to edit a configuration file or dotfile,
  or whenever you create or modify any config, rcfile, profile, or dotfile for
  any reason."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A request to change, create, or remove any user configuration, dotfile, rcfile,
  application setting, Pi profile file, or similar persistent machine
  configuration - regardless of whether chezmoi currently manages it.
- Access to the chezmoi source repository at `~/.local/share/chezmoi` when the
  target turns out to be managed or is being adopted into management.
- The destination path of the target file or directory.
- Explicit approval before adding any secret or machine-specific value to version
  control.

## Output Contract

- For managed targets: every change made in `~/.local/share/chezmoi`, never
  directly in the live destination; committed and pushed before
  `chezmoi apply`; clean `git status`, empty `chezmoi diff` and `chezmoi status`
  afterward.
- For adopted targets: the same lifecycle as managed targets, beginning from the
  current live content imported into source state.
- For genuinely unmanaged targets: a direct live edit plus a report stating that
  the path is outside chezmoi and why it was left unmanaged.
- Secrets and runtime state always stay out of the tracked source tree through
  `.chezmoiignore`.
- No edited configuration is ever left as an untracked or modified-but-uncommitted
  source-state change; grouping into logical commits happens within the same run.

# Entrypoint

## Stage 1: Determine management status

1. Run `chezmoi source-path -- <destination-path>` for the exact target.
2. Branch on the result:
   - Target is managed: proceed to Stage 2 with the resolved source path.
   - Target is not managed: proceed to Stage 2A (adoption decision).

## Stage 2: Classify secrets and runtime state

1. Inspect the target's source file and neighboring source files before editing.
2. Classify every component as tracked configuration, secret, or runtime state.
3. Never place credentials, tokens, private keys, refresh tokens, or private feed
   URLs in the source repository.
4. Keep secrets in dedicated destination files where practical and add those
   destination-relative paths to `~/.local/share/chezmoi/.chezmoiignore`.
5. Add caches, sessions, logs, generated databases, cloned repositories, token
   stores, and other runtime state to `.chezmoiignore` when they belong inside an
   otherwise managed tree.
6. Stop and ask the user if a single file mixes secrets with configuration and
   cannot be split safely.
7. Proceed to Stage 3.

## Stage 2A: Decide whether to adopt the target

1. Classify the target as durable personal configuration or machine-local
   transient state, using its contents, location, and lifetime so far.
2. Adopt when the target is configuration the user would expect on another
   machine: application config, editor/shell/tool settings, Pi profile files.
3. Do not adopt caches, session data, downloaded artifacts, generated databases,
   or credentials.
4. Branch on the decision:
   - Adopting: import the current live content into
     `~/.local/share/chezmoi` using correct source naming attributes (`dot_`,
     `private_`, `executable_`, `symlink_`), exclude secret and runtime paths via
     `.chezmoiignore` per Stage 2 rule 4-5, then proceed to Stage 3.
   - Not adopting: edit the live destination file directly, skip Stages 3
     through 5, confirm the edit works, and report that the path is deliberately
     outside chezmoi management.

## Stage 3: Edit the source state

1. Edit files only under `~/.local/share/chezmoi`; for adoption edits, begin from
   the freshly imported live content.
2. Preserve chezmoi source naming attributes such as `dot_`, `private_`,
   `executable_`, and `symlink_`.
3. Do not use a live destination copy to overwrite source changes unless the user
   explicitly wants that live drift preserved; when live content is newer than
   source because the owning tool rewrote it, treat live as authoritative and
   bring it into source deliberately.
4. Validate the changed configuration with the application's syntax or validation
   tools where they exist.
5. Run `git -C ~/.local/share/chezmoi diff --check` and inspect the complete Git
   diff.
6. Proceed to Stage 4 only when the source changes are correct and contain no
   secrets.

## Stage 4: Commit and push

1. Stage only the intended source-state changes belonging to this task.
2. Review the staged paths and staged diff.
3. Commit with a concise message describing the affected configuration.
4. Push the current branch to its configured upstream.
5. Confirm `git -C ~/.local/share/chezmoi status --short --branch` shows no
   unpushed commit; leave unrelated pre-existing dirty files untouched rather
   than sweeping them into this task's commits.
6. If unrelated dirty source-state files from earlier work are present, report
   them explicitly and ask whether to commit them; never leave files you touched
   yourself uncommitted.
7. Proceed to Stage 5 only after the push succeeds. Do not apply an unpushed
   config change.

## Stage 5: Apply and verify

1. Run `chezmoi apply`; when unrelated live drift blocks a full apply, apply the
   specific changed targets by path instead of forcing the conflicting ones.
2. Run the relevant application validation again when applying can alter rendered
   content, permissions, links, or templates.
3. Run `chezmoi diff` and `chezmoi status` and require empty output for the paths
   this task changed.
4. If those commands still report drift in changed paths, return to Stage 1,
   reconcile deliberately, commit and push, and apply again.
5. Report the commit, push result, apply result, and final clean checks.

# `.chezmoiignore` Rules

- The ignore file is `~/.local/share/chezmoi/.chezmoiignore`.
- Its paths describe destination entries relative to the chezmoi destination
  root, normally `$HOME`.
- Blank lines and lines beginning with `#` are documentation and do not define
  patterns.
- Directory and wildcard patterns may exclude generated subtrees or classes of
  machine-local files.
- An ignored destination is omitted from chezmoi's desired target state, so
  `chezmoi apply` does not create, replace, or remove it.
- Keep patterns as narrow as possible so adjacent non-secret configuration
  remains managed.
- Treat `.chezmoiignore` as tracked policy: review, commit, and push every change
  to it.
- Ignoring a path does not remove a secret already committed to Git history. Stop
  and report any discovered committed secret so it can be revoked and removed
  through an explicit cleanup process.
