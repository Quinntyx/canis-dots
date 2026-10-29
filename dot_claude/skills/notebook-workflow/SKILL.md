---
name: notebook-workflow
description: "Use when authoring, exploring in, or handing over a Jupyter notebook: select an available execution runtime, keep scratch work separate from durable cells, and verify a clean top-to-bottom run. Not for a single throwaway Python check or unrelated Python work."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The notebook/task, requested outputs, permitted effects and available project dependencies.
- Native Claude `Read` and `NotebookEdit`; an execution backend only if actually available.
- A configured notebook MCP service, or the project's existing Jupyter/nbclient runner, for execution.

## Output Contract

- A coherent `.ipynb` with narrative, useful cell boundaries and explicit dependencies.
- Fresh saved outputs from a clean ordered execution, or an explicit unexecuted boundary.
- Reconciled external effects; rerunning a notebook does not silently launch another task roster.

# Entrypoint

## Stage 1: Select the execution adapter

1. Inspect the notebook and project instructions. Use `ToolSearch` to discover an already configured
   notebook service when relevant; inspect its real schemas before selecting it.
2. Native `NotebookEdit` edits one cell by `cell_id` using its supported edit mode. It does not
   execute Python, inspect variables, attach to a kernel, approve execution or clear runtime state.
   Pi's 1-based cell numbers are not Claude cell IDs.
3. For an MCP runner, record server/tool identity, notebook/kernel identity, indexing convention,
   output persistence, execution status, cancellation and recovery semantics. Reuse or reattach to
   an existing kernel only if that service actually supports it.
4. Otherwise inspect the project's existing notebook execution command. `Bash` may run that command,
   but separate Bash invocations do not share a Python namespace. A Python process or environment
   existing on disk is not evidence of an execution service.
5. If no runner exists, make source-only notebook edits and report execution as blocked. Authorized
   project-local dependency setup may add a runner through the project manager; no global install
   or invented MCP tool is implied. Continue to Stage 2 with the selected capability boundary.

## Stage 2: Explore and author

1. Keep exploration in the selected scratch runtime or a saved temporary `.py` script run with Bash.
   Use `Write` for the script; inline Python `-c` and shell heredocs remain prohibited by policy.
2. Promote proven logic into durable cells with `NotebookEdit`. Use a meaningful analytical step per
   cell, not every experimental expression. Keep compact results in chat and large intermediates
   in local artifacts. Explicitly import NumPy/pandas/matplotlib if needed; no preimports exist.
3. Order narrative, imports, data access, transformations, results and interpretation so the notebook
   reads as a finished explanation. Define variables before use; avoid hidden scratch state.
4. Inspect source and saved outputs separately. Editing a file does not update a live kernel or
   refresh saved output. Use the runner's supported notebook-save operation after execution.
5. For plots, save concrete image artifacts and inspect them with `Read`. Native Claude does not
   automatically attach matplotlib figures or summarize images for a non-vision model. For a
   requested T3 visual showback use its available HTML tools; otherwise state the output boundary.

## Stage 3: Execute within authority

1. Save and inspect the exact cell/script before substantial execution. Ask for review only when
   the existing task authority requires it; an autonomous request does not need repeated approval.
   Native NotebookEdit is not a private approval/review card.
2. Keep pure calculations separate from downloads, publication, deployment, writes and orchestration.
   Guard effectful cells with explicit execution flags and inspect prior receipts before rerunning.
   T3 children follow `../subagents/SKILL.md` and coordinator-owned lifecycle, not a Python agent pool.
3. After an execution timeout/lost result, inspect execution identity/status or saved outputs first.
   With uncertain effects and no inspectable identity, reconcile the real target before retrying.
4. Missing kernel continuity, namespace inspection or output persistence is a stated limitation,
   not permission to claim Pi-pycells semantics. Continue to Stage 4 after actual execution or with
   the precise blocked execution boundary.

## Stage 4: Hand over

1. Remove dead experiments, unused imports and stale outputs that contradict edited source. Preserve
   intentional exploratory evidence when it explains a real decision, not merely execution history.
2. Restart the selected runner and execute the notebook from the first cell in order. Inspect and
   save fresh outputs; verify effect guards before this run. Check package/data prerequisites.
3. Confirm the result reads well top-to-bottom and the key claims match saved outputs/artifacts.
4. Report notebook path, actual runner, clean-run result, needed dependencies/data and unexecuted
   boundaries. If no runner was available, report source validation only—not an execution pass.

# Provenance and limits

Claude-specific adaptation of the user's Pi-pycells notebook-workflow; source revision and digest
are recorded in `~/.claude/migration/manifest.json`. The Pi installation is unchanged. Persistent
kernel tools, scratch/recorded-cell APIs, attachment/recovery and private cell-review cards require
a separate supported MCP bridge; native editing is not a replacement for those capabilities.
