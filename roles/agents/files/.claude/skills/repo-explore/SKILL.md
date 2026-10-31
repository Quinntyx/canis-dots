---
name: repo-explore
description: "Inspect an actual verified upstream checkout before explaining or proposing a patch to a library, framework, tool, CLI, SDK or API."
argument-hint: "<repo or question>"
disable-model-invocation: true
metadata:
  type: procedure
---

# Contract

## Input Contract

- Repository/question: $ARGUMENTS; requested version and permitted acquisition effects.

## Output Contract

- An answer from inspected source, with actual checkout/ref provenance and immutable evidence.
- No edits, fork, publication or new thread implied by source exploration alone.

# Entrypoint

1. Read `../git/SKILL.md` and `../librarian/SKILL.md`. Check supplied/established checkouts and any
   existing `~/.cache/repo_cache` entry for matching origin/ref before downloading duplicates.
   A cache name is not identity; preserve collisions and use the Git procedure's source route.
2. Inspect repo guidance/docs, relevant implementation, callers and tests. Use scoped `rg` and
   `Read`; blocked grep/find commands are not a fallback. Keep large intermediates out of chat.
3. Trace the question through actual symbols/branches and check relevant history if rationale is
   asked. Separate current checked-out behavior, version-specific changes and inference.
4. Answer with the mechanism, exact paths/lines and host-appropriate full-SHA code permalinks.
   Describe a patch only when requested; implementation/publication remains a separate effect.
5. State inaccessible evidence, missing dependencies and unresolved uncertainty. Do not claim that
   native WebFetch cloned source or that a summary proves uninspected internals.
