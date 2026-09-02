function off --description 'Put the focused monitor in DDC standby'
    set -l output (niri msg --json focused-output | jq -r '.name')
    set -l display

    switch $output
        case HDMI-A-1
            set display 1
        case DP-1
            set display 2
        case '*'
            printf 'off: unsupported focused output: %s\n' "$output" >&2
            return 1
    end

    ddcutil --display $display --noverify setvcp D6 02
end
