# ==============================================================================
# Completions for g - git helper for a worktree-based source layout.
# Mirrors the layout logic from functions/g.fish (g_src, primary worktree).
# ==============================================================================

# --- shared helpers -----------------------------------------------------------

function __g_src_dir
    if set -q g_src; and test -n "$g_src"
        string trim -r -c / -- $g_src
    else
        echo $HOME/docs/src
    end
end

function __g_src_containers
    set -l base (__g_src_dir)
    for d in $base/*
        test -d $d; or continue
        printf '%s\t%s\n' (basename $d) $d
    end
end

# --- g cd: top-level dirs under the src root ----------------------------------

function __g_cd_completions
    __g_src_containers
end

# --- g clone: already-cloned dirs + your GitHub repos (live search w/ slash) --

function __g_clone_completions
    set -l token (commandline -ct)
    __g_src_containers
    if string match -q '*/*' -- $token
        # owner/repo: live GitHub repo search
        command -q gh; and gh search repos "$token" --limit 15 --json fullName --jq '.[].fullName' 2>/dev/null
    else
        # your own repos on GitHub
        command -q gh; and gh repo list --limit 200 --json name --jq '.[].name' 2>/dev/null
    end
end

# --- g wt: base branches from the primary worktree ----------------------------

function __g_wt_completions
    set -l root (git rev-parse --show-toplevel 2>/dev/null)
    if test -n "$root"
        set -l primary (git worktree list --porcelain 2>/dev/null | string match 'worktree *' | head -n1 | string replace 'worktree ' '')
        if test -n "$primary"
            git -C $primary for-each-ref --format='%(refname:short)' refs/heads refs/remotes/origin 2>/dev/null | string replace 'origin/' '' | string match -v origin | string match -v HEAD
        else
            git branch -a --format='%(refname:short)' 2>/dev/null | string replace 'origin/' '' | string match -v origin | string match -v HEAD
    end
    else if test -d $PWD/main/.git -o -f $PWD/main/.git
        # Container dir holding the main worktree (~/docs/src/foo)
        git -C $PWD/main for-each-ref --format='%(refname:short)' refs/heads refs/remotes/origin 2>/dev/null | string replace 'origin/' '' | string match -v origin | string match -v HEAD
    end | sort -u
end

# --- g fork: live GitHub repo search ------------------------------------------

function __g_fork_completions
    set -l token (commandline -ct)
    command -q gh; and gh search repos "$token" --limit 15 --json fullName --jq '.[].fullName' 2>/dev/null
end

# --- registrations ------------------------------------------------------------

complete -c g -f -n '__fish_use_subcommand' -a 'cd'       -d 'cd to ~/docs/src[/name]'
complete -c g -f -n '__fish_use_subcommand' -a 'clone'    -d 'worktree-style clone of [owner/]repo'
complete -c g -f -n '__fish_use_subcommand' -a 'wt'       -d 'add a worktree; no args lists worktrees'
complete -c g -f -n '__fish_use_subcommand' -a 'worktree' -d 'alias for wt'
complete -c g -f -n '__fish_use_subcommand' -a 'fork'     -d 'gh-fork, clone, add upstream remote'
complete -c g -f -n '__fish_use_subcommand' -a 'help'     -d 'show usage'
complete -c g -f -n '__fish_use_subcommand' -a '-h'       -d 'show usage'
complete -c g -f -n '__fish_use_subcommand' -a '--help'   -d 'show usage'

complete -c g -f -n '__fish_seen_subcommand_from cd'       -a '(__g_cd_completions)'
complete -c g -f -n '__fish_seen_subcommand_from clone'    -a '(__g_clone_completions)'
complete -c g -f -n '__fish_seen_subcommand_from wt worktree' -a '(__g_wt_completions)'
complete -c g -f -n '__fish_seen_subcommand_from fork'     -a '(__g_fork_completions)'
