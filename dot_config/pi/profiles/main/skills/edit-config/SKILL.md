---
name: edit-config
description: "Use whenever changing user configuration or dotfiles managed by chezmoi."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A request to change user configuration or dotfiles managed by chezmoi.
- Access to the chezmoi source repository and its Git remote.
- The destination path or application whose configuration must change.
- Explicit approval before adding any secret or machine-specific value to version control.

## Output Contract

- Make the intended change in `~/.local/share/chezmoi`, not directly in the live destination.
- Commit and push every source-state change before applying it to the system.
- Run `chezmoi apply` after the push succeeds.
- Leave the chezmoi Git working tree clean and synchronized with its upstream branch.
- Leave `chezmoi diff` empty after applying the change.
- Keep secrets and runtime state outside the managed source state through `.chezmoiignore`.

# Entrypoint

## Stage 1: Locate the Managed Source

1. Run `chezmoi source-path` and confirm the source is
   `~/.local/share/chezmoi`.
2. Run `chezmoi source-path <destination-path>` for an existing managed target.
3. Inspect the source file and relevant neighboring files before editing.
4. If the target is unmanaged, determine whether it is persistent configuration, generated state,
   or a secret before proceeding to Stage 2.

## Stage 2: Classify Secrets and Runtime State

1. Never place credentials, tokens, private keys, refresh tokens, or private feeds in the source
   repository.
2. Keep secrets in a dedicated destination file when practical and add that destination-relative
   path to `~/.local/share/chezmoi/.chezmoiignore`.
3. Add caches, sessions, logs, generated databases, cloned repositories, and other runtime state to
   `.chezmoiignore` when they belong inside an otherwise managed configuration tree.
4. Proceed to Stage 3 when all files are classified. Stop and ask the user if a file mixes secrets
   with configuration and cannot be split safely.

## Stage 3: Edit the Source State

1. Edit files only under `~/.local/share/chezmoi`.
2. Preserve chezmoi source naming attributes such as `dot_`, `private_`, `executable_`, and
   `symlink_`.
3. For a new non-secret target, add it deliberately to the source state and inspect the generated
   source path before continuing.
4. Do not use a live destination copy to overwrite source changes unless the user explicitly wants
   that live drift preserved.
5. Validate the changed configuration with the application's syntax or validation tools.
6. Run `git -C ~/.local/share/chezmoi diff --check` and inspect the complete Git diff.
7. Proceed to Stage 4 only when the source changes are correct and contain no secrets.

## Stage 4: Commit and Push

1. Stage only the intended source-state changes.
2. Review the staged paths and staged diff.
3. Commit the changes with a concise message describing the affected configuration.
4. Push the current branch to its configured upstream.
5. Confirm that `git -C ~/.local/share/chezmoi status --short --branch` reports a clean working tree
   with no unpushed commit.
6. Proceed to Stage 5 only after the push succeeds. Do not apply an unpushed config change.

## Stage 5: Apply and Verify

1. Run `chezmoi apply`.
2. Run the relevant application validation again when applying can alter rendered content,
   permissions, links, or templates.
3. Run `chezmoi diff` and require empty output.
4. Run `chezmoi status` and require empty output.
5. If either command reports drift, return to Stage 1, reconcile the source deliberately, commit and
   push the correction, and then run `chezmoi apply` again.
6. Report the commit, push result, apply result, and final clean checks.

# `.chezmoiignore` Rules

- The ignore file is `~/.local/share/chezmoi/.chezmoiignore`.
- Its paths describe destination entries relative to the chezmoi destination root, normally `$HOME`.
- Blank lines and lines beginning with `#` are documentation and do not define patterns.
- Directory and wildcard patterns may exclude generated subtrees or classes of machine-local files.
- An ignored destination is omitted from chezmoi's desired target state, so `chezmoi apply` does not
  create, replace, or remove it.
- Keep patterns as narrow as possible so adjacent non-secret configuration remains managed.
- Treat `.chezmoiignore` as tracked policy: review, commit, and push every change to it.
- Ignoring a path does not remove a secret already committed to Git history. Stop and report any
  discovered committed secret so it can be revoked and removed through an explicit cleanup process.
