function fish_user_key_bindings
    function __dotdot_repaint
        # Ordinary typing should not launch Starship for every keystroke.
        if set -q __dotdot_previewing[1]; or __dotdot_preview >/dev/null
            commandline -f repaint
        end
    end

    # Bracketed and clipboard paste bypass self-insert. Delegate all of Fish's
    # quoting/multiline handling, then invalidate the preview just as typing does.
    if not functions -q __dotdot_original_paste; and type -q __fish_paste
        functions --copy __fish_paste __dotdot_original_paste
    end
    if functions -q __dotdot_original_paste
        function __fish_paste
            __dotdot_original_paste $argv
            __dotdot_repaint
        end
    end

    set -l modes insert
    if test "$fish_key_bindings" = fish_default_key_bindings
        set -a modes default
    end
    for mode in $modes
        bind -M $mode '' self-insert __dotdot_repaint
        bind -M $mode space self-insert expand-abbr __dotdot_repaint
        bind -M $mode backspace backward-delete-char __dotdot_repaint
        bind -M $mode ctrl-h backward-delete-char __dotdot_repaint
        bind -M $mode shift-backspace backward-delete-char __dotdot_repaint
        bind -M $mode alt-backspace backward-kill-word __dotdot_repaint
        bind -M $mode ctrl-alt-h backward-kill-word __dotdot_repaint
        bind -M $mode ctrl-backspace backward-kill-token __dotdot_repaint
        bind -M $mode delete delete-char __dotdot_repaint
        bind -M $mode alt-delete kill-word __dotdot_repaint
        bind -M $mode ctrl-delete kill-token __dotdot_repaint
        bind -M $mode ctrl-u backward-kill-line __dotdot_repaint
        bind -M $mode ctrl-w backward-kill-path-component __dotdot_repaint
        bind -M $mode ctrl-k kill-line __dotdot_repaint
        bind -M $mode ctrl-c clear-commandline __dotdot_repaint
        bind -M $mode ctrl-g cancel __dotdot_repaint
        bind -M $mode up up-or-search __dotdot_repaint
        bind -M $mode down down-or-search __dotdot_repaint
        bind -M $mode ctrl-p up-or-search __dotdot_repaint
        bind -M $mode ctrl-n down-or-search __dotdot_repaint
        bind -M $mode pageup beginning-of-history __dotdot_repaint
        bind -M $mode pagedown end-of-history __dotdot_repaint
        bind -M $mode ctrl-y yank __dotdot_repaint
        bind -M $mode alt-y yank-pop __dotdot_repaint
    end
    if test "$fish_key_bindings" = fish_default_key_bindings
        bind ctrl-z undo __dotdot_repaint
        bind ctrl-/ undo __dotdot_repaint
        bind ctrl-_ undo __dotdot_repaint
        bind ctrl-shift-z redo __dotdot_repaint
        bind alt-/ redo __dotdot_repaint
    end
end
