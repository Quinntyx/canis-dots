#!/usr/bin/env bash
# MPRIS player management for Waybar
# Tracks the selected player and provides commands for cycle/play-pause/next/previous/stop

STATE_FILE="${XDG_RUNTIME_DIR:-/tmp}/waybar-mpris-current"

get_players() {
    playerctl -l 2>/dev/null
}

get_current() {
    local current=""
    [[ -f "$STATE_FILE" ]] && current=$(cat "$STATE_FILE")

    local players
    players=$(get_players)

    if [[ -z "$current" ]] || ! echo "$players" | grep -qx "$current"; then
        current=$(echo "$players" | head -1)
        [[ -n "$current" ]] && echo "$current" > "$STATE_FILE"
    fi
    echo "$current"
}

cmd_status() {
    local current
    current=$(get_current)

    if [[ -z "$current" ]]; then
        printf '{"text": "No player", "tooltip": "No MPRIS player active", "class": "stopped"}\n'
        return
    fi

    playerctl --player="$current" metadata \
        --format '{"text": "{{playerName}}: {{markup_escape(title)}}", "tooltip": "{{playerName}}\n{{markup_escape(title)}} - {{markup_escape(artist)}}\n{{status}}", "class": "{{lc(status)}}"}' \
        2>/dev/null || \
        printf '{"text": "No player", "tooltip": "No MPRIS player active", "class": "stopped"}\n'
}

cmd_cycle() {
    local current
    current=$(get_current)

    local players=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && players+=("$line")
    done < <(get_players)

    [[ ${#players[@]} -eq 0 ]] && return 0

    local idx=-1
    for i in "${!players[@]}"; do
        if [[ "${players[$i]}" == "$current" ]]; then
            idx=$i
            break
        fi
    done

    local next_idx=$(( (idx + 1) % ${#players[@]} ))
    echo "${players[$next_idx]}" > "$STATE_FILE"
}

cmd_play_pause() {
    local current
    current=$(get_current)
    [[ -n "$current" ]] && playerctl --player="$current" play-pause
}

cmd_next() {
    local current
    current=$(get_current)
    [[ -n "$current" ]] && playerctl --player="$current" next
}

cmd_previous() {
    local current
    current=$(get_current)
    [[ -n "$current" ]] && playerctl --player="$current" previous
}

cmd_stop() {
    playerctl -a pause
}

case "${1:-status}" in
    status)     cmd_status ;;
    cycle)      cmd_cycle ;;
    play-pause) cmd_play_pause ;;
    next)       cmd_next ;;
    previous)   cmd_previous ;;
    stop)       cmd_stop ;;
esac