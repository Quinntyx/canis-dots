# ==============================================================================
# g - git helper for a worktree-based source layout
#
# Layout (all repos live under ~/docs/src):
#     ~/docs/src/foo/main               # the primary clone of the repo
#     ~/docs/src/foo/<worktree>        # worktrees registered against foo/main
#     ~/docs/src/other_foo/main        # someone else's foo, namespaced
#
# Subcommands:
#     g cd [name]          cd to ~/docs/src[/name]
#     g clone [owner/]repo worktree-style clone (owner defaults to you)
#     g wt [base-variant]  add a worktree; bare `g wt` lists worktrees
#     g fork other/foo     gh-fork someone's repo, clone, add upstream remote
#
# Test/override hooks (fish globals):
#     g_src            destination root   (default: $HOME/docs/src)
#     g_github_base    hosts the repos    (default: https://github.com)
#     g_default_owner   fallback owner    (default: gh login, else quinntyx)
# ==============================================================================

# --- shared helpers -----------------------------------------------------------

function __g_src
    if set -q g_src; and test -n "$g_src"
        string trim -r -c / -- $g_src
    else
        echo $HOME/docs/src
    end
end

function __g_github_base
    if set -q g_github_base; and test -n "$g_github_base"
        string trim -r -c / -- $g_github_base
    else
        echo https://github.com
    end
end

function __g_default_owner
    if set -q g_default_owner; and test -n "$g_default_owner"
        echo $g_default_owner
        return
    end
    if command -q gh
        set -l me (gh api user --jq .login 2>/dev/null)
        if test -n "$me"
            echo $me
            return
        end
    end
    echo quinntyx
end

function __g_usage
    echo "g - git helper for worktree-based source"
    echo
    echo "  g cd [name]           cd to ~/docs/src[/name]"
    echo "  g clone [owner/]repo  clone into <src>/<repo>/main"
    echo "                        (a foreign owner becomes <src>/<owner>_<repo>/main)"
    echo "  g wt [base-variant]   add a worktree; no args lists existing worktrees"
    echo "  g fork other/foo      gh-fork, clone, add an upstream remote"
    echo
    echo "examples:"
    echo "  g clone pylingual"
    echo "  g clone other/pylingual"
    echo "  g wt dev-extended_masking    # attach to the remote branch"
    echo "  g wt dev-extended_feature    # new branch from dev, pushed to origin"
end

# --- g cd ---------------------------------------------------------------------

function __g_cd
    set -l base (__g_src)
    if not test -d $base
        echo "g cd: $base does not exist" >&2
        return 1
    end

    if test (count $argv) -eq 0
        builtin cd -- $base
        return 0
    end

    set -l target $base/$argv[1]
    if not test -d $target
        echo "g cd: $target does not exist" >&2
        for d in $base/*/
            echo "  $d"
        end
        return 1
    end

    builtin cd -- $target
end

# --- g clone ------------------------------------------------------------------

function __g_do_clone -a owner repo
    set -l base (__g_src)
    set -l me (__g_default_owner)

    set -l target $base/$repo
    if test "$owner" != "$me"
        set target $base/{$owner}_$repo
    end

    if test -e $target
        echo "g clone: $target already exists" >&2
        return 1
    end

    set -l host (__g_github_base)
    set -l url $host/$owner/$repo
    if not git ls-remote $url >/dev/null 2>&1
        echo "g clone: no such repo: $url" >&2
        return 1
    end

    mkdir -p $target
    if not git clone $url $target/main
        echo "g clone: clone failed" >&2
        if command -q trash
            trash $target >/dev/null
        else if test -z (ls -A $target 2>/dev/null)
            rmdir $target
        end
        return 1
    end

    echo "g clone: $owner/$repo -> $target/main"
    builtin cd -- $target/main
end

function __g_clone
    if test (count $argv) -ne 1
        echo "usage: g clone [owner/]repo" >&2
        return 1
    end

    set -l spec $argv[1]
    set -l parts (string split -- '/' $spec)
    switch (count $parts)
        case 1
            __g_do_clone (__g_default_owner) $parts[1]
        case 2
            __g_do_clone $parts[1] $parts[2]
        case '*'
            echo "g clone: invalid spec '$spec'" >&2
            return 1
    end
end

# --- g fork --------------------------------------------------------------------

function __g_fork
    if test (count $argv) -ne 1
        echo "usage: g fork other/foo" >&2
        return 1
    end

    set -l parts (string split -- '/' $argv[1])
    if test (count $parts) -ne 2
        echo "g fork: expected other/foo" >&2
        return 1
    end

    set -l other $parts[1]
    set -l repo $parts[2]
    if not command -q gh
        echo "g fork: gh CLI not found" >&2
        return 1
    end

    if not gh repo fork $other/$repo --remote=false
        echo "g fork: gh repo fork failed" >&2
        return 1
    end
    set -l me (__g_default_owner)

    __g_do_clone $me $repo
    or return 1

    set -l host (__g_github_base)
    set -l target (__g_src)/$repo
    if git -C $target/main remote add upstream $host/$other/$repo
        echo "g fork: upstream -> $other/$repo"
    else
        echo "g fork: could not add upstream (already exists?)" >&2
    end
end

# --- g worktree ----------------------------------------------------------------

function __g_wt
    set -l primary
    set -l container

    # Resolve the repo anchor (the "main" clone). Works from any worktree of the
    # repo, or from the plain container dir (which is not itself a git repo).
    set -l root (git rev-parse --show-toplevel 2>/dev/null)
    if test -n "$root"
        # fish gotcha: `set -l` inside a block is block-scoped, so use bare `set`
        # here to update the function-local primaries declared above.
        set primary (git worktree list --porcelain 2>/dev/null | string match 'worktree *' | head -n1 | string replace 'worktree ' '')
        if test -z "$primary"
            echo "g wt: could not resolve the main worktree" >&2
            return 1
        end
        # new worktrees are siblings of "main", inside the container
        set container (dirname $primary)
    else if test -d $PWD/main/.git -o -f $PWD/main/.git
        # We're in the container dir itself (~/docs/src/foo); anchor on ./main
        set primary $PWD/main
        set container $PWD
    else
        echo "g wt: not inside a g-managed repo ($PWD)" >&2
        return 1
    end

    # Bare `g worktree list`: no arg, just list them all.
    if test (count $argv) -eq 0
        git -C $primary worktree list
        return
    end

    set -l name $argv[1]

    # Split on the LAST '-' so base-variant and base-a-b stay discoverable.
    set -l parts (string split -r -m 1 -- '-' $name)
    if test (count $parts) -lt 2
        echo "g wt: '$name' has no '-' separator (expected base-variant)" >&2
        return 1
    end
    set -l base $parts[1]

    set -l target $container/$name

    # Fail fast when the worktree or its local branch already exist.
    if test -e $target
        echo "g wt: worktree already exists: $target" >&2
        return 1
    end
    if git -C $primary show-ref --verify --quiet refs/heads/$name
        echo "g wt: local branch '$name' already exists" >&2
        return 1
    end

    # Does the remote already have this branch?
    set -l has_remote 0
    if git -C $primary show-ref --verify --quiet refs/remotes/origin/$name
        set has_remote 1
    else if git -C $primary ls-remote --heads --exit-code origin $name >/dev/null 2>&1
        git -C $primary fetch origin $name
        set has_remote 1
    end

    if test $has_remote -eq 1
        # Create a local tracking branch, then attach a worktree to it.
        # (Modern git refuses `--track` on `worktree add` unless `-b` is given.)
        git -C $primary branch --track $name origin/$name
        or return 1
        git -C $primary worktree add $target $name
        or return 1
        echo "g wt: attached $name to origin/$name"
    else
        # New branch. The base must exist locally, or on the remote.
        set -l base_ref
        if git -C $primary show-ref --verify --quiet refs/heads/$base
            set base_ref $base
        else if git -C $primary show-ref --verify --quiet refs/remotes/origin/$base
            set base_ref origin/$base
        else
            echo "g wt: base branch '$base' does not exist (local or origin)" >&2
            return 1
        end
        git -C $primary worktree add -b $name $target $base_ref
        or return 1
        # Sync the new branch to the origin and set up tracking.
        git -C $target push -u origin $name
        or return 1
        echo "g wt: created $name from $base_ref and pushed to origin"
    end

    builtin cd -- $target
end

# --- dispatch ------------------------------------------------------------------

function g --description 'git helper for a worktree-based source layout'
    set -l cmd $argv[1]
    switch "$cmd"
        case cd
            __g_cd $argv[2..-1]
        case clone
            __g_clone $argv[2..-1]
        case wt worktree
            __g_wt $argv[2..-1]
        case fork
            __g_fork $argv[2..-1]
        case help '--help' -h
            __g_usage
        case '*'
            __g_usage
            return 1
    end
end