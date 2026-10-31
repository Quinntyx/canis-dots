function auth --description "Run the interactive auth flow for one of my services"
    # Nested so the whole thing stays self-contained for fish autoloading.
    function __auth_usage
        echo "usage: auth <service>"
        echo
        echo "Services:"
        echo "  gcal-sync   Google Calendar OAuth for the 'managed' calendar"
        echo "              (run this after a token expiry, before syncing)"
    end

    set -l service $argv[1]

    # ------------------------------------------------------------------
    # Services registry: adding a project = one case below, one line in
    # __auth_usage, and one entry in ~/.config/fish/completions/auth.fish.
    # ------------------------------------------------------------------
    switch $service
        case gcal-sync
            set -l script ~/.config/pi/profiles/omn-assistant/skills/gcal-sync/bin/gcal-sync
            if not test -x $script
                echo "auth: gcal-sync not found at $script" >&2
                return 1
            end
            echo "→ authorizing gcal-sync (managed Google Calendar)"
            echo "  tip: publish the OAuth consent screen, otherwise the refresh"
            echo "       token expires every 7 days (Testing status)."
            command $script --auth

        case -h --help list
            __auth_usage
            return 0

        case ''
            __auth_usage >&2
            return 1

        case '*'
            echo "auth: unknown service '$service' — run 'auth' for the list" >&2
            return 1
    end
end
