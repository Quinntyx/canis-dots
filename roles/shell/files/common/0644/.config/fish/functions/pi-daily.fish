function pi-daily --description 'Open daily_assistant: pi on the left, fish shell on the right'
    # Make the profile's bin/ (da, bb) available in both panes
    set -gx PATH $HOME/.config/pi/profiles/daily_assistant/bin $PATH

    if not tmux has-session -t daily 2>/dev/null
        tmux new-session -d -s daily -n work
        # Left pane: the daily assistant (pi under the daily_assistant profile)
        tmux send-keys -t daily 'ppi use daily_assistant --' Enter
        # Right pane: fish shell for taskwarrior
        tmux split-window -t daily -h
        tmux select-pane -t daily -L
    end

    tmux switch-client -t daily
end
