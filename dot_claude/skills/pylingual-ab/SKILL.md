---
name: pylingual-ab
description: "Work with the running PyLingual A/B regression harness in its actual development checkout."
argument-hint: "[request]"
disable-model-invocation: true
metadata:
  type: procedure
---

# Contract

## Input Contract

- The real non-ephemeral PyLingual checkout/worktree and request: $ARGUMENTS.
- An already configured `pylingual-ab` command; do not provision a benchmark service.

## Output Contract

- The requested focused investigation/fix and actual focused-test evidence, with pending refresh
  clearly distinguished from completed validation.

# Entrypoint

1. Run `pylingual-ab agent-help` with native Bash and read its task instructions as project evidence
   under the user's authority. The current working directory is the development checkout: preserve
   it, and keep benchmark-owned runtime clones outside the editing scope.
2. If no request was supplied, inspect reported regressions, group root causes/severity and recommend
   priority. Otherwise do the assigned task and validate with focused tests in this checkout.
3. Follow the task's explicit regression-refresh contract rather than waiting, watching or polling
   refresh jobs. If publishing a fix is assigned, use the Git procedure's exact commit/push scope.
4. Report actual tests/results, revision where relevant, and remaining asynchronous refresh work.
