# Only inspect standalone navigation: never evaluate text from the command line.
function __dotdot_preview
    set -l input (commandline --current-buffer | string collect)
    set input (string trim -- "$input")
    set -l relative
    if string match -rq '^\.\.+$' -- "$input"
        set relative (string repeat -n (math (string length -- "$input") - 1) ../)
    else if string match -rq '^cd (\.\./)*\.\./?$' -- "$input"
        set relative (string sub --start 4 -- "$input")
    else
        return 1
    end

    # Fish's cd follows logical parents, including when PWD contains a symlink.
    path normalize -- "$PWD/$relative"
end
