function __fish_codex_ponytail_needs_worktree
    set -l tokens (commandline -pxc)
    set -e tokens[1]

    for token in $tokens
        if test "$token" != --dry-run
            return 1
        end
    end

    return 0
end

complete -c codex-ponytail \
    -l dry-run \
    -d 'Validate and print actions without changing files'
complete -c codex-ponytail \
    -n __fish_codex_ponytail_needs_worktree \
    -f \
    -a '(codex-ponytail --complete-worktrees)' \
    -d 'Existing worktree'
