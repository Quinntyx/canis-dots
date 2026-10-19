# Named tmux persistence

`~/.tmux.conf` loads `~/.config/tmux/persistence.conf`. The `tmux-persist`
helper serializes startup restores, manual operations, and timer saves under a
per-socket lock. Numeric session names remain disposable. Only verified Pi and
Neovim processes are replayed; other panes reopen as shells.

## New machines

A chezmoi `run_onchange_after` hook reloads user systemd, enables and starts
`tmux-resurrect-save.timer`, and loads persistence into an existing tmux server.
It reruns when the helper, service, timer, or persistence configuration changes. With
no user systemd manager available, it prints the remaining activation step.

Snapshots, application sessions, and launch metadata remain machine-local and
are not synchronized by chezmoi.

## Restore and save lifecycle

Neither restores nor saves have a fixed execution deadline. The save service
also has `TimeoutStartSec=infinity`: waiting behind a large restore must not
cause systemd to kill the next save. The timer waits one minute after each save
finishes (`OnUnitInactiveSec`), rather than counting from its start. Saves that
take longer than a minute therefore do not turn into continuous back-to-back
runs.

The helper runs each plugin operation in an owned process group. It cleans up
that group, including background spinners, on success, script failure, or a
handled termination signal. Restored tmux panes are not members of that group.

Before restoring, the helper clears the server's readiness marker. After the
plugin finishes, it checks that every saved pane exists, then marks the server
ready. A cancelled or incomplete restore records an error and leaves autosaving
blocked so the last-good snapshot is not replaced by a partial layout. Saving
before readiness reports an error instead of silently succeeding.

Re-sourcing configuration after a successful startup does not replay old
sessions. To explicitly retry a failed restore:

```sh
tmux-persist restore
```

## Runtime checks

```sh
tmux show-option -g -v @tmux-persist-state
tmux show-option -g -v @tmux-persist-ready
tmux show-option -g -v @tmux-persist-error  # only present after failure
systemctl --user status tmux-resurrect-save.timer
journalctl --user -u tmux-resurrect-save.service -n 20
readlink ~/.local/state/tmux/resurrect/last
```

Readiness must match `tmux display-message -p '#{pid}'`. The state should be
`ready` and the timer active. A changed layout advances the selected snapshot;
identical snapshots are deliberately discarded, so an unchanged `last` symlink
does not mean saving stopped. Check the service's successful completion records
and its next timer deadline as well. Normal state is `restoring` until the entire
plugin operation and pane verification complete; there is deliberately no
60-second cutoff.

Run regression tests from the chezmoi source directory:

```sh
python docs/host/tests/test_tmux_persistence.py
```

The isolated runtime check uses the real plugin on a private socket, deliberately
waits 65 seconds during restoration, then checks cancellation cleanup, retry,
and a real filtered save (allow about 75 seconds):

```sh
python docs/host/tests/check_tmux_persistence_runtime.py
```
