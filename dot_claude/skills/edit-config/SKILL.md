---
name: edit-config
description: "Use when creating, changing, or removing persistent configuration, dotfiles,
  rcfiles, application settings or agent-harness configuration. Owns finding the real source,
  publishing it and applying only what changed; the harness-config skill supplies what the
  harness itself owns."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The configuration change wanted and the file it should end up in.
- Access to whatever owns that file. For dotfiles that is usually chezmoi, whose source
  directory defaults to `~/.local/share/chezmoi`.
- How far the task goes: edit the source only, or also commit, push and apply.

## Output Contract

- The change made in the source that owns the file, not in a generated or installed copy.
- When the task covers the whole chezmoi lifecycle: the change committed and pushed, then applied
  to the files you changed and no others.
- A short report that says separately what was edited, what was published, what was applied, and
  whether the running program has picked it up.

# Entrypoint

## Stage 1: Find the owner

Read the target file and the configuration around it. Write down the exact paths this task owns.

Ask chezmoi whether it manages the target:

```sh
chezmoi managed --path-style absolute -- "$target"
```

`chezmoi source-path -- "$target"` locates the source of a managed file. It is not proof of
management: it prints a path even when no such source file exists.

Then choose the route:

- chezmoi manages it: go to Stage 2.
- A package manager, plugin manager or generator produced it: go to Stage 1A.
- Nothing manages it and it is the user's own configuration: go to Stage 1B.
- You cannot tell who owns it: stop and report what you could not determine. A file missing from
  chezmoi is not thereby safe to edit in place; resolve symlinks and wrappers to the real target
  first.

## Stage 1A: Change it through its owner

Installed files are the manager's output. Find the thing the user is meant to edit instead: a
declaration, a documented override, or the upstream repository they own.

- Package managers own installed application files and libraries. Use a supported user override,
  or change the package's source.
- Claude's plugin manager and Pi's Git/npm package manager own fetched plugins, extensions and
  skill caches. Change the owned fork and its installation declaration, then update that one
  package through the manager, and check which revision ended up installed.
- A generated file belongs to its generator, template or schema. Change that.

Make the change there and update through the manager. If software is missing, give the user the
command to install it. Then go to Stage 5.

## Stage 1B: Unmanaged configuration

Adopt a file into chezmoi only when the user wants it managed and it is durable personal
configuration that belongs on their machines. Add that one file, never a whole directory.
Generated output, downloaded packages, credentials, caches, sessions and databases stay out.

If it is adopted, go to Stage 2. Otherwise edit the file in place, check it, and go to Stage 5,
saying that it remains unmanaged.

## Stage 2: Edit the source

Change only the source paths from Stage 1. For this agent harness's own settings, skills, hooks
or profile files, load the `harness-config` skill first: it says what the harness owns and how
its settings work.

- Keep the source file's chezmoi attributes, templates and permissions.
- Keep credentials and runtime state out of tracked source. Ask before tracking a secret or a
  value that only makes sense on one machine. Use a template or a host condition for real
  differences between machines.
- `.chezmoiignore` takes destination-relative paths. Ignoring a path stops chezmoi managing it;
  it neither deletes the existing file nor removes a secret already committed. A secret that is
  already in history has to be revoked and the history cleaned, which is the user's decision.

Run the application's own syntax check on the result, read the diff of the paths you own, and run
`git diff --check` in the source directory.

If the task ends at the source, go to Stage 5 and name what is still pending. Otherwise go to
Stage 3.

## Stage 3: Publish

Use `../git/SKILL.md`. Stage the task's exact paths, read the staged diff, commit those paths and
push. Other changes in the source repository are someone else's: leave them unstaged and
untouched.

If the push fails, check whether the remote took the commit, then go to Stage 5 with application
pending. Otherwise go to Stage 4.

## Stage 4: Apply what you changed

For each file you own, look at the diff and apply that file alone:

```sh
chezmoi diff -- "$target"
chezmoi apply --exclude=scripts -- "$target"
```

- Name files one at a time. Applying a parent directory also applies everyone else's pending
  changes under it.
- If an owned file's parent directory does not exist yet, create only the directory entries,
  shallowest first, then apply the file:

  ```sh
  chezmoi apply --recursive=false --exclude=scripts -- "$owned_parent"
  ```

- `--exclude=scripts` keeps chezmoi's run scripts from firing as a side effect. Run a script the
  change needs on purpose.
- A change to a shared template, an ignore rule or an external affects several targets. List the
  ones it affects and apply those.
- To remove a file, remove it through chezmoi or trash the destination. Deleting the source or
  ignoring the path leaves the existing file where it is.

Finish by checking that both of these print nothing for each file you own:

```sh
chezmoi diff -- "$target"
chezmoi status -- "$target"
```

A removed file is checked by its absence. Drift in files that are not yours is out of scope.

## Stage 5: Report

Say which source and destination paths changed and who owns them, the commit and push result if
there was one, exactly which targets were applied, and the checks you ran. Say separately whether
the running program needs a reload or restart to pick the change up.
