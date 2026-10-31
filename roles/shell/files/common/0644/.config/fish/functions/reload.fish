function reload --description "Reload fish config"
    set -l abbrs (abbr --list)
    if set -q abbrs[1]
        abbr --erase $abbrs
    end
    source ~/.config/fish/config.fish
    for fn in (functions --names)
        set -l src (functions --details $fn)
        if string match -q "$__fish_config_dir/functions/*" $src
            functions --erase $fn
        end
    end
end