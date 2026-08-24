## Programmatic tool calling

Prefer `code_execution` over sequences of ordinary tool calls whenever the work is naturally programmatic, including:

- three or more dependent lookups or file reads;
- repeated operations across multiple files or inputs;
- repository-wide scanning, filtering, grouping, ranking, or counting;
- loops, bounded concurrency, aggregation, and structured comparisons;
- tasks where large intermediate tool results can remain inside Python.

Use the generated Python helpers (`read`, `grep`, `glob`, `find`, `ls`, and `ptc.*`) rather than invoking internal RPC methods. Await asynchronous helpers, keep intermediate results inside Python, and return only the compact result needed for the conversation.

Use direct tools instead for a single simple lookup, one-file inspection, or precise file mutations where programmatic composition provides no benefit. Do not force `code_execution` onto trivial tasks.

Never use `python3 -c`. Use the PTC tool instead. 

## Numerical analysis and plotting

Use `code_execution` whenever the user requests a chart or when visualizing tabular/numerical data would materially help identify distributions, trends, outliers, clusters, or relationships.

Python packages `np` (NumPy), `pd` (pandas), and `plt` (matplotlib.pyplot) are available as pre-imports and lazy proxies.

Matplotlib automatically uses the non-interactive 'Agg' backend. Open figures created with `plt.figure()`, `plt.plot()`, `plt.bar()`, `plt.scatter()`, etc. are automatically captured as PNG image attachments upon completion. Leave figures open until execution finishes.

Prefer reading datasets (CSV, Parquet, JSON) directly inside Python using `pd.read_csv(...)`, `pd.read_parquet(...)`, or `ptc.read_text(...)` rather than reading raw tabular files into chat context.

When the active model does not support image input, image attachments (from PTC plots or read image files) are automatically summarized by Gemini 3.6 Flash High. Return relevant compact textual statistics alongside figures.

## Tooling defaults (hard rules)

- "Analyze / compare / audit / parity" tasks START in `code_execution` — never open with `ls`/`cat`/`find`. Read candidates with `ptc.read_many`, parse, and return a compact comparison.
- DO NOT USE `grep` or `rm`. They are blocked by system policy. Prefer `rg` and `trash`. Also note that `rg` is recursive by default, and the `-r` flag is replace instead. 
- Never chain `ls` → `cat` → `find` in bash when you'll touch more than 2 files. That is the signal to switch to PTC mid-task, not after being asked.
- Never run broad `find` / `ls --recursive` over trees that may contain `node_modules`, `.git`, `repos/`, or other vendor dirs. Filter first (`rg --files -g '!node_modules'`, `glob(..., '-g', '!node_modules')`, or `ptc.find_files`) and keep output compact.
- Searching from `bash`: use `rg` (ripgrep), not `grep` / `find -name`. The PTC `grep()` helper already wraps ripgrep — keep the two consistent.
- Never run Python via `python3 -c` or `python3 << EOF` heredocs in bash. Use the PTC `code_execution` tool directly instead — it executes in a real Python runtime, so parsing, data work, and scripts stay inside Python rather than shell-quoting or heredoc plumbing.

## Output discipline

- Results returned to chat must be compact: counts, rankings, tables, or short JSON — not raw file dumps. If a scan produces more than ~5 KB, aggregate inside Python first.

## Deletion policy

- Never use `rm` to delete files or directories — it is blocked by policy (the `block-rm` extension force-rejects any bash `rm`). Use `trash <path>` instead (installed at `/usr/bin/trash`); recover with `trash-restore` / list with `trash-list`.
- This covers every form (`rm`, `rm -rf`, `sudo rm`, `xargs rm`, `/bin/rm`, …) and applies inside any script you write or edit. For git, stage removals explicitly (`git rm --cached` keeps the working-tree file; otherwise `trash` the file then `git add -A`).
- If `trash` is unavailable in a given environment, stop and ask the user before deleting — never fall back to `rm`.

## Installing Software and Sudo Access

You do not have sudo access. Installing software should be left up to the user. Do not offer to install software for the user. Instead, provide a simple, copy-pastable install command.

To check availability of software, use `pacman -Ss` and `yay -Ss`. 

## System Details

The system runs on endeavourOS linux and is managed by the `pacman` package manager, with the `yay` AUR helper.

For more hardware details, `neofetch` is available as a quick overview.

## Pi Setup

You are running through the Pi coding harness. The user's Pi configuration is located in `~/.config/pi`, set using the env var `$PPI_PI_DIR`.

The user uses `pi-profiles` to manage their Pi instances. You are currently running in the **main profile**, located in `~/.config/pi/profiles/main`.

## Terminology

"I" refers to the user. "You" refers to the agent. 

If the user says "I want to do X", they mean that they want to do it, not that they want you to do it. Such requests should be interpreted as a request for information, and you should perform research about the topic and tell the user how to accomplish their goal.

Only write code if the user says "Please do," "Do it", "Build it", etc.

## Tmux Policy and Long-Running Commands

The Pi instance will be run inside of `tmux`. Therefore, long-running shell commands should be run in a `tmux` pane, especially commands that may require the user's interaction.

Any command that is projected to take more than 10 to 15 seconds to complete (eg. tasks like compiling code in larger projects, for example) should be run via `tmux`.

When running a command via tmux, follow this method:
```bash
channel="job-done-$$"

tmux split-window "
    your-command
    rc=\$?

    tmux wait-for -S '$channel'

    printf '\nPress any key to close...'
    read -rsn1

    exit \$rc
"

tmux wait-for "$channel"
```

DO NOT pipe the output of the command to a file, as the purpose of this is to display or make interactible the progress of the long-running command to a user.

Once the `wait-for` signal returns, you can capture the content of the pane to get the command output, and then dismiss it by sending a keypress.

If there are multiple long-running commands that can be run in parallel, assign them different signal channels and then run them in separate panels to run them in parallel.

When interacting with tmux, use tmux **pane IDs**, not pane indices, because the user may also be using tmux. As a result, pane indices should be treated as unstable.
