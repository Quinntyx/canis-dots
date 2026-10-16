# Owned PTY capture

## Bindings and prerequisites

- Run the shell blocks in one Bash process or restore their recorded bindings in the controller.
- Bind `cwd` to the absolute checkout, `argv` to the real application argument vector as a Bash
  array, `cols` and `rows` to positive PTY dimensions, and `term` to its supported TERM name.
- Include required environment overrides through an explicit `env` argument vector in `argv`.
  Record the effective application environment with secrets redacted, theme and state paths.
- Resolve Bash, tmux, util-linux script/scriptreplay, mktemp, sleep and chmod. Read local help.
  The commands use util-linux `script` with advanced timing logs and its command-string interface.
  Installed help may advertise argv syntax while `script` still interprets it through a shell.
  The task-local Bash launcher below preserves argument boundaries with Bash's `printf %q`.
- Verify the installed capture syntax on a bounded run. Missing capture support returns to Stage 6:
  Deliver in `SKILL.md`; supported capture continues with Allocate and launch.
- Keep stdout logging private: output and terminal echo can contain sensitive data. Select sanitized
  inputs and authorized accounts. The recorder below logs output and timing; explicit inputs belong
  in the task's sanitized event trace.

## Allocate and launch

1. Allocate a fresh directory and socket. These commands never select an existing tmux server.
   Each run gets its own token and starts with a bounded setup placeholder.

```bash
umask 077
run=$(mktemp -d /tmp/tui.XXXXXX)
token=${run##*/}
printf '%s\n' "$token" > "$run/owner"
t=(env -u TMUX -u TMUX_PANE tmux -S "$run/tmux.sock" -f /dev/null)
pane=$("${t[@]}" new-session -d -P -F '#{pane_id}' -s terminal-ui \
  -c "$cwd" -x "$cols" -y "$rows" /usr/bin/sleep 30)
"${t[@]}" set-option -p -t "$pane" @terminal_ui_owner "$token"
"${t[@]}" set-option -p -t "$pane" remain-on-exit on
"${t[@]}" set-option -g status off
"${t[@]}" set-option -g default-terminal "$term"
window=$("${t[@]}" display-message -p -t "$pane" '#{window_id}')
"${t[@]}" resize-window -t "$window" -x "$cols" -y "$rows"
```

2. Write `manifest.json` with owner token, directory, socket, session/window/pane IDs, source/build
   identity, argv, cwd, terminal environment, versions and initial trace/configuration hashes.
   Record the actual application PID and loaded executable/modules once the readiness signal fires.
   Preserve each command's exit status; a failed allocation reports the retained state at Stage 6:
   Deliver in `SKILL.md`. A successful allocation continues at step 3.
3. Verify the marker before every mutation, input injection, capture or shutdown. Match it with both
   the recorded manifest token and owner file. A mismatch reports the ownership failure at Stage 6:
   Deliver in `SKILL.md`; a match continues with the selected operation.

```bash
test "$(cat "$run/owner")" = "$token"
test "$("${t[@]}" show-options -p -v -t "$pane" @terminal_ui_owner)" = "$token"
```

4. Write a private launcher from the bound argv, then replace only this run's setup placeholder.
   Bash serializes arguments for its own parser; the launcher's explicit interpreter preserves those
   boundaries. Record the launcher digest in the manifest. The recorder propagates child exit status
   and records ANSI output and timing from startup through its nested PTY.

```bash
launch="$run/launch"
{
  printf '#!/bin/bash\nexec'
  printf ' %q' "${argv[@]}"
  printf '\n'
} > "$launch"
chmod 700 "$launch"
"${t[@]}" respawn-pane -k -t "$pane" -c "$cwd" \
  /usr/bin/env SHELL=/bin/sh TUI_LAUNCH="$launch" script -qef -m advanced \
  -O "$run/output.ansi" -T "$run/output.time" -c 'exec "$TUI_LAUNCH"'
```

5. Wait for the declared readiness signal with the trace's deadline. Query actual PTY geometry and
   verify it inside the application when size matters. Record the server socket and pane alongside
   the process identity; the pane's initial PID belongs to the recorder, not necessarily the app.
   The setup placeholder alone is replaceable. Subsequent runs allocate fresh directories and IDs.

## Drive and capture

1. Use a task-local controller to persist `events.jsonl` from startup through completion and exit.
   Each event records its index, monotonic time before/after the operation, kind, byte payload in
   hex or logical payload, expected state, return status and observed readiness. Record stream
   chunk boundaries, resize dimensions, theme changes and clock advances. At each selected boundary
   include observed geometry, screen/metadata paths and timed-output offsets. A planned trace in
   the manifest is not an executed event index; never invent missing event timing after the run.
2. Bind `hex_bytes` to the event's bytes as two-digit hexadecimal Bash array entries. Inject them
   only into the recorded pane. Bind `cols` and `rows` to each resize event and target its window.
   For mouse, paste and keyboard protocols, encode the application's actual negotiated protocol.

```bash
"${t[@]}" send-keys -H -t "$pane" "${hex_bytes[@]}"
"${t[@]}" resize-window -t "$window" -x "$cols" -y "$rows"
```

3. Apply those commands only for their corresponding event type. Drive stream data through the
   application's real input/provider boundary. Prefer an existing fixture adapter with controlled
   chunks over a live nondeterministic producer for the decisive comparison. Retain the integrated
   application's normal startup, renderer, event loop and terminal writes.
4. At each declared boundary, wait for the render barrier or controlled-clock state. Bind `step`
   to its integer event index, then capture the active grid and terminal metadata. Bracket sampling
   with controller timestamps; a live animation without a barrier is a timed observation, while a
   controlled boundary can support a deterministic assertion.

```bash
"${t[@]}" capture-pane -p -e -N -t "$pane" > "$run/screen-$step.ansi"
fmt='#{pane_id} #{pane_width} #{pane_height} #{alternate_on}'
fmt+=' #{cursor_x} #{cursor_y} #{cursor_flag}'
fmt+=' #{pane_pid} #{pane_dead} #{pane_dead_status} #{pane_dead_signal}'
"${t[@]}" display-message -p -t "$pane" "$fmt" > "$run/screen-$step.meta"
```

5. Inspect cell text, attributes and cursor/viewport assertions, including completion and redraw
   at every selected geometry. Compare the full affected rows against expected cells and blank
   remainder; distinguish intended borders from stale suffixes using the declared expectation.
   Capture settled completion before exit, separately from the dead-pane screen. `capture-pane -e`
   reconstructs styled cells; it is not the original escape stream or a timing record.
   `output.ansi` and `output.time` supply the emitted stream and timing. The typescript also has
   recorder headers/trailers; interpret it with the matching timing file.
6. For terminal-owned scrollback, capture the normal-screen history at the relevant settled point.
   The active-grid command above captures the current screen. Use `capture-pane -a` only for a
   specifically required alternate-buffer capture, with its state recorded separately.

```bash
"${t[@]}" capture-pane -p -e -N -S - -E - -t "$pane" > "$run/history.ansi"
```

7. Verify SIGWINCH and effective dimensions in the application after resizing. Selective terminal
   replies and rendering may differ through tmux and the nested recorder. Retain those limits and
   run the decisive interaction in the actual target emulator when its behavior is implicated.

## Complete, inspect and seal

1. Send the application's documented graceful exit event, or observe its declared natural exit,
   and wait for the owned pane's `pane_dead` state with a deadline. Persist the exit event and final
   pane status/signal as `final.meta` with field names or the exact queried format. Reconcile them
   with recorder status; `script -e` reports its child's status. A deadline reports a live handle
   at Stage 6: Deliver in `SKILL.md`; an exited process continues at step 2. Cancellation and forced
   shutdown follow the task's explicit authority.
2. Inspect the typescript tail for terminal restoration. Record expected and observed cursor,
   input-mode and screen cleanup in the manifest, citing final raw byte intervals and metadata.
   For modes never changed, record that fact and its evidence rather than assuming restoration.
   tmux's dead-pane footer is harness output, not an application completion frame or restoration
   proof. Parse the recorder summary without replaying arbitrary escapes into the agent's terminal.

```bash
scriptreplay --summary -T "$run/output.time" > "$run/recording-summary.txt"
```

3. Verify output/timing are nonempty, expected ANSI/state transitions are present, selected screens
   contain the asserted cells without redraw residue and all event indices resolve to retained
   screens, metadata and timed-output intervals. Read the actual artifacts, not only process exit
   codes. Retain failing comparisons with expected values; a passing width check is not a passing
   completion/redraw check.
4. When playback is useful, launch `scriptreplay` with `--log-out` and `--log-timing` bound to these
   files inside another fresh owned PTY. Use the recorded geometry and apply recorded resizes from
   the controller. Playback visualizes recorded output; rerunning the application trace verifies
   behavior. Treat replayed escape sequences as untrusted terminal input.
5. After verifying the owner marker and exited state, retire only this private server. Retain its
   directory and all evidence; a live server remains addressable by the recorded socket and token.

```bash
"${t[@]}" kill-server
```

6. Finalize `manifest.json` with actual HEAD, dirty-source/runnable digests, observed process/build
   identity, exit/restoration findings, coverage and limits. Write a separate `checksums.json`
   SHA-256 map of every regular evidence file, including the finalized manifest, except the map
   itself; exclude the socket. Embedded manifest hashes do not replace this map. Reopen every file,
   verify its digest and resolve every event/frame path. Record verification results in the receipt
   outside the sealed run; any subsequent evidence edit requires resealing and verification.
   Completion requires the whole tuple: manifest/source identity, timed raw output, event index
   with screens/metadata, exit/restoration provenance and verified checksums. Missing evidence goes
   to Stage 6: Deliver in `SKILL.md` as incomplete; a complete tuple returns to Stage 5: Verify the
   integrated run in `SKILL.md` for acceptance, not automatic certification from captures.

## Sources

- Installed tmux help and `tmux(1)` define argv execution, isolated sockets, pane targeting,
  `capture-pane`, `send-keys`, resizing, formats and exit retention.
  <https://man.openbsd.org/tmux.1>
- util-linux `script(1)` and `scriptreplay(1)` define PTY recording, timing and replay semantics.
  <https://github.com/util-linux/util-linux/tree/master/term-utils>
- Verify the installed versions at invocation; local help/source governs supported flags.
