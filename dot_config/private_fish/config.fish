# ==========================================
# Environment Variables
# ==========================================
set -gx SUDO_EDITOR helix

# Silence the first-run greeting ("Welcome to fish..." / "Type help...")
set -g fish_greeting

# Permit pi-ptc-next's local Python subprocess. Pi already has unrestricted
# bash access in this setup, so this does not widen the practical trust boundary.
set -gx PTC_ALLOW_UNSANDBOXED_SUBPROCESS true
set -e PTC_USE_DOCKER

# ==========================================
# Abbreviations
# ==========================================
abbr -a hx helix
abbr -a nvim helix
abbr -a icat "kitty +kitten icat"
abbr -a l "ls -ltrau --color"
abbr -a sizeof "du --si --max-depth=0"
abbr -a wl-dump "wl-paste --type text/plain >"
abbr -a pyc "python3 -m py_compile"
abbr -a lock swaylock

# Let /move (and other Pi session switches) hand the final cwd back to this shell.
# Route through the `main` ppi profile; when already under a profile
# (PI_CODING_AGENT_DIR set, e.g. from inside a ppi session), launch pi directly
# so the current profile is preserved.
function pi --wraps pi --description 'Pi coding agent with canonical cwd and cwd handoff'
    set -l handoff (mktemp --tmpdir pi-cwd-handoff.XXXXXX)
    set -l logical_cwd $PWD
    set -l canonical_cwd (realpath -- .)

    # Pi keys session buckets by the cwd string. Launch from the physical path
    # so symlink aliases such as ~/docs and ~/Documents share one history.
    if set -q PI_CODING_AGENT_DIR
        command env --chdir=$canonical_cwd PWD=$canonical_cwd PTC_USE_DOCKER=false PTC_ALLOW_UNSANDBOXED_SUBPROCESS=true PI_CWD_HANDOFF_FILE=$handoff pi $argv
    else
        command env --chdir=$canonical_cwd PWD=$canonical_cwd PTC_USE_DOCKER=false PTC_ALLOW_UNSANDBOXED_SUBPROCESS=true PI_CWD_HANDOFF_FILE=$handoff ppi use main -- $argv
    end
    set -l pi_status $status

    if test -s $handoff
        set -l destination (string collect < $handoff | string trim)
        if test -d "$destination"
            # Preserve the user's shorter logical spelling when Pi stayed in
            # the same directory; use the handoff path after a real /move.
            if test (realpath -- "$destination") = "$canonical_cwd"
                builtin cd -- "$logical_cwd"
            else
                builtin cd -- "$destination"
            end
        end
    end

    command rm -f -- $handoff
    return $pi_status
end

# ==========================================
# Fish Colors (Light Theme Fix)
# ==========================================
# Inline autosuggestion (ghost text) - Using a readable medium blue-grey
set -g fish_color_autosuggestion 6c90b8

# General syntax highlighting
set -g fish_color_command 5b7fa6 --bold
set -g fish_color_param 2b3440
set -g fish_color_keyword c06c84
set -g fish_color_quote d4a85c
set -g fish_color_error c06c84 --bold
set -g fish_color_valid_path --underline

# Tab completion dropdown (pager)
set -g fish_pager_color_completion 2b3440
set -g fish_pager_color_description 6c90b8
set -g fish_pager_color_prefix 5b7fa6 --bold
set -g fish_pager_color_progress fffff0 --background=5b7fa6

starship init fish | source

if test (string match -r '^\d+' -- $version | string join '') -ge 4
    enable_transience
end

if command -q pyenv
    pyenv init - | source
else if command -q python3; and python3 -m pyenv init - >/dev/null 2>&1
    python3 -m pyenv init - | source
end
