function __fish_claude_ponytail_needs_worktree
    set -l tokens (commandline -pxc)
    set -e tokens[1]

    for token in $tokens
        if test "$token" != --dry-run
            return 1
        end
    end

    return 0
end

complete -c claude-ponytail \
    -l dry-run \
    -d 'Validate and print actions without changing files'
complete -c claude-ponytail \
    -n __fish_claude_ponytail_needs_worktree \
    -f \
    -a '(claude-ponytail --complete-worktrees)' \
    -d 'Existing worktree'
