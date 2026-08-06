function dev
    # ---- resolve optional target (file or folder) ----
    set -l target $argv[1]
    set -l dir $PWD
    set -l helix_cmd 'helix'
    if test -n "$target"
        if test -d "$target"
            set dir (realpath "$target")
            set helix_cmd (string join ' ' helix (string escape -- (realpath "$target")))
        else if test -e "$target"
            set dir (realpath (dirname "$target"))
            set helix_cmd (string join ' ' helix (string escape -- (realpath "$target")))
        else
            # doesn't exist yet — helix will create it; work in its parent if valid
            set -l d (dirname "$target")
            if test -d "$d"
                set dir (realpath "$d")
            end
            set helix_cmd (string join ' ' helix (string escape -- "$target"))
        end
    end
    set -l broot_cmd 'broot -g -c ":watch"'

    if test -n "$TMUX"
        # Inside tmux: split the current pane into the 20/60/20 layout.
        # The pane you run `dev` in becomes the left (pi) pane.
        tmux split-window -h -p 80 -c "$dir" "$helix_cmd"
        tmux split-window -h -p 25 -c "$dir" "$broot_cmd"
        tmux select-pane -t '{left-of}'    # focus helix (middle)
        cd "$dir"
        exec pi -c
    else
        # Outside tmux: fresh session every time — never re-attaches.
        # Use the session ID ($N), not the name: auto-names are bare numbers
        # and `-t 0` would be ambiguous with pane 0.
        set -l sid (tmux new-session -d -P -F '#{session_id}' -c "$dir" 'pi -c')
        tmux split-window -h -p 80 -t "$sid" -c "$dir" "$helix_cmd"
        tmux split-window -h -p 25 -t "$sid" -c "$dir" "$broot_cmd"
        tmux select-pane -t "$sid":.1    # focus helix (middle)
        tmux attach -t "$sid"
    end
end
