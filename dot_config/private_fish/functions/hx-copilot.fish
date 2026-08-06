function hx-copilot
    # Custom-built helix with LSP inline completion (PR #14876 merge).
    # Uses its own config/languages under ~/.config/helix-copilot so the
    # system helix (~/.config/helix) stays untouched.
    env XDG_CONFIG_HOME="$HOME/.config/helix-copilot" \
        /home/henry/.local/bin/hx --config "$HOME/.config/helix-copilot/config.toml" $argv
end
