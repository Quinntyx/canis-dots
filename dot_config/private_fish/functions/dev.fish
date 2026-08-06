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
    # Run helix inside a fish subshell so :q drops you to a fish prompt
    # in that directory instead of closing the pane (reopen with `hx`).
    set helix_cmd (string join -- ' ' fish -C (string escape -- "$helix_cmd"))
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
        # Create the session at the current terminal size: a detached
        # session defaults to 80x24, and tmux's attach-resize hands each
        # pane roughly equal extra columns, collapsing 20/60/20 toward
        # thirds (16/47/16 at 80 cols becomes 114/146/114 at 376).
        set -l cols (tput cols 2>/dev/null)
        set -l rows (tput rows 2>/dev/null)
        set -l size_flags
        if string match -qr '^[0-9]+$' -- "$cols" ; and string match -qr '^[0-9]+$' -- "$rows"
            set size_flags -x $cols -y $rows
        end
        set -l sid (tmux new-session -d -P -F '#{session_id}' $size_flags -c "$dir" 'pi -c')
        tmux split-window -h -p 80 -t "$sid" -c "$dir" "$helix_cmd"
        tmux split-window -h -p 25 -t "$sid" -c "$dir" "$broot_cmd"
        tmux select-pane -t "$sid":.1    # focus helix (middle)
        tmux attach -t "$sid"
    end
end
