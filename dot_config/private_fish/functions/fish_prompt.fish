# Keep Starship's renderer and shell context; only change its directory input.
function fish_prompt
    set -l last_pipestatus $pipestatus
    set -l last_status $status
    set -l duration "$CMD_DURATION$cmd_duration"
    set -l keymap insert
    switch "$fish_key_bindings"
        case fish_hybrid_key_bindings fish_vi_key_bindings fish_helix_key_bindings
            set keymap "$fish_bind_mode"
    end
    __starship_set_job_count
    set -l args --terminal-width="$COLUMNS" --status=$last_status --pipestatus="$last_pipestatus" --keymap=$keymap --cmd-duration=$duration --jobs=$STARSHIP_JOBS

    # Preserve both Fish's native transient prompts and Starship's older binding.
    if contains -- --final-rendering $argv; or test "$TRANSIENT" = 1
        if test "$TRANSIENT" = 1
            set -g TRANSIENT 0
            printf '\e[0J'
        end
        if functions -q starship_transient_prompt_func
            starship_transient_prompt_func $args
        else
            printf '\e[1;32m❯\e[0m '
        end
        return
    end

    set -g __dotdot_previewing (__dotdot_preview)
    set -l directory "$PWD"
    if set -q __dotdot_previewing[1]
        set directory "$__dotdot_previewing[1]"
    end
    command starship prompt $args --path="$directory" --logical-path="$directory"
end
