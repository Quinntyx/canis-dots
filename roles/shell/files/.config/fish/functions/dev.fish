function dev
    # ---- resolve optional target (file or folder) ----
    set -l target $argv[1]
    set -l dir $PWD
    set -l helix_cmd helix
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
        tmux select-pane -t '{left-of}' # focus helix (middle)
        cd "$dir"
        # Route through the fish `pi` function (profile routing + cwd handoff).
        # `exit` closes this pane when pi exits, matching the old `exec`.
        pi -c
        exit
    else
        # Resolve the terminal size so the split happens at real width:
        # a detached session defaults to 80x24 and tmux's attach-resize
        # hands each pane roughly equal extra columns, collapsing 20/60/20
        # toward thirds (16/47/16 at 80 cols becomes 114/146/114 at 376).
        # Note: `tput rows` is not a valid capability everywhere (rc=4;
        # the terminfo name is `lines`), so prefer `stty size`, which
        # reads the winsize directly and needs no terminfo.
        set -l dims (stty size 2>/dev/null)
        set -l cols
        set -l rows
        if test (count $dims) -eq 2
            set rows $dims[1]
            set cols $dims[2]
        else if string match -qr '^[0-9]+$' -- "$COLUMNS"
            set cols $COLUMNS
            set rows $LINES
        else
            set cols (tput cols 2>/dev/null)
            set rows (tput lines 2>/dev/null)
        end
        set -l size_flags
        if string match -qr '^[0-9]+$' -- "$cols"; and string match -qr '^[0-9]+$' -- "$rows"
            set size_flags -x $cols -y $rows
        end
        set -l sid (tmux new-session -d -P -F '#{session_id}' $size_flags -c "$dir" 'pi -c')
        tmux split-window -h -p 80 -t "$sid" -c "$dir" "$helix_cmd"
        tmux split-window -h -p 25 -t "$sid" -c "$dir" "$broot_cmd"
        tmux select-pane -t "$sid":.1 # focus helix (middle)
        tmux attach -t "$sid"
    end
end
