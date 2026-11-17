# Fish dot navigation

In command position, `..` expands to `cd ../`, `...` to `cd ../../`, and each
extra dot adds another parent. There is no fixed maximum. Expansion happens on
Space or Enter; dots in arguments and quoted strings remain literal.

While the buffer contains just the dots (or their expanded `cd ../…` command),
the prompt previews the destination directory. This does not change the shell's
working directory: only Enter runs `cd`. Editing, deletion, paste, cancellation,
and undo restore or update the preview. Logical parents are retained for symlinked
working directories, and navigating above `/` stays at `/`.

## Rendering and activation

Starship is retained with the existing `starship.toml`, colors, status/pipeline
context and transient prompt. `fish_prompt.fish` supplies the prospective directory
to Starship's `--path` and `--logical-path` options. It only recognizes standalone
parent navigation; it never evaluates text from the command line. Normal typing
does not request an extra prompt redraw unless a preview is active.

`config.fish` loads the renderer after `starship init`; `fish_user_key_bindings`
adds repaint checks to the normal insert/edit bindings. The paste wrapper delegates
to Fish's existing paste handler, retaining its escaping and multiline behavior.
The `reload` helper clears cached functions before sourcing the configuration and
reinstalls the bindings, so repeated reloads keep both Starship and paste handling.
After applying these files, start a new Fish shell (or run `exec fish`) to activate
the new bindings. Applying files cannot replace functions in an already-running
shell.

## Verification

Run `python docs/host/tests/test_fish_dotdot.py` with Fish, Starship and `trash`
available. The tests start real interactive Fish readers under PTYs with isolated
homes, using the tracked Fish and Starship configuration. A separate pipe observes
the reader without printing to the terminal or requesting a repaint. Coverage
includes arbitrary lengths, Space/Enter, root clamping, logical symlinks and spaces,
noncommands, deletion/cancellation (including Alt+Backspace), paste/undo, repeated
reloads and native Starship byte-for-byte
render/status/pipeline/transience parity. Fixtures are removed recoverably with
`trash`. Verified with Fish 4.9.3 and Starship 1.26.0.
