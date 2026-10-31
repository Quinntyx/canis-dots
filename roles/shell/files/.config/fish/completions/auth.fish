# Completions for `auth` — keep in sync with ~/.config/fish/functions/auth.fish
complete -c auth -f
complete -c auth -n "not __fish_seen_subcommand_from gcal-sync" \
    -a gcal-sync -d "Google Calendar OAuth for the 'managed' calendar"
