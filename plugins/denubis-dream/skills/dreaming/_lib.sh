#!/usr/bin/env bash
# denubis-dream skill helper. Sourced by SKILL.md Bash blocks.
# Each function is idempotent and safe to call multiple times.
#
# Convention: variable assignments do NOT persist across separate Bash tool
# calls. Functions defined here re-derive their values each time, so any
# block that needs MAIN_SLUG, DATED_DIR, etc. can source this file and call
# the appropriate function.

# Resolve the main project slug (strips /.worktrees/<name> if present).
# Exits 0 with an error message on stderr if not inside a git repo.
dream_main_slug() {
  local git_top main_path
  git_top=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$git_top" ]; then
    echo "denubis-dream: unable to resolve project slug — not inside a git repository." >&2
    return 1
  fi
  main_path=$(printf '%s' "$git_top" | sed -E 's|/\.worktrees/[^/]+$||')
  printf '%s' "$main_path" | sed -E 's|^/||; s|/|-|g; s|^|-|'
}

# Resolve the absolute path to the main project's ~/.claude/projects/<slug>/ dir.
dream_main_dir() {
  local slug
  slug=$(dream_main_slug) || return 1
  printf '%s' "$HOME/.claude/projects/$slug"
}

# Today's date in ISO 8601 (sorts lexically).
dream_today() {
  date +%Y-%m-%d
}

# Absolute path to today's dated audit directory under the main slug.
dream_dated_dir() {
  local main_dir today
  main_dir=$(dream_main_dir) || return 1
  today=$(dream_today)
  printf '%s' "$main_dir/memory.dream-$today"
}

# Newline-separated list of discovered slugs (main slug + any matching
# --worktrees-<name> siblings under ~/.claude/projects/).
# Empty if no transcript dirs exist yet (first session).
dream_discovered_slugs() {
  local slug
  slug=$(dream_main_slug) || return 1
  ls -1 "$HOME/.claude/projects/" 2>/dev/null \
    | grep -E "^${slug}\$|^${slug}--worktrees-.+\$" \
    || true
}
