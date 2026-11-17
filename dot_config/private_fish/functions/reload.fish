function reload --description "Reload fish config"
    set -l abbrs (abbr --list)
    if set -q abbrs[1]
        abbr --erase $abbrs
    end
    # Drop cached functions before sourcing: config may explicitly define a prompt.
    for fn in (functions --names)
        set -l src (functions --details $fn)
        if test "$fn" != reload; and string match -q "$__fish_config_dir/functions/*" $src
            functions --erase $fn
        end
    end
    source ~/.config/fish/config.fish
    if type -q fish_user_key_bindings
        fish_user_key_bindings
    end
end