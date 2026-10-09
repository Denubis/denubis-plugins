#!/usr/bin/env bash
# tmux pane-border-format helper: print the coloured title strip for one pane.
#
# Usage (installed into the server by branch-bg.py, or by hand in tmux.conf):
#   set -g pane-border-status top
#   set -g pane-border-format '#(bash /path/to/branch-strip.sh "#{q:pane_current_path}" "#{q:pane_title}" "#{pane_id}")'
#
# tmux runs this every status-interval for every visible pane, so the answer is
# cached per (path, title) for a short while and Python runs only on a miss.
# On a miss the pane's background field is also (re)applied.
set -u
path="${1:-}"
title="${2:-}"
pane="${3:-}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ttl="${BRANCH_BG_STRIP_TTL:-20}"

cache_dir="${XDG_RUNTIME_DIR:-/tmp}/branch-bg-$(id -u)"
mkdir -p "$cache_dir" 2>/dev/null || exit 0
key="$(printf '%s\n%s' "$path" "$title" | md5sum | cut -c1-32)"
cache="$cache_dir/$key"

if [ -f "$cache" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$cache" 2>/dev/null || echo 0) ))
  if [ "$age" -lt "$ttl" ]; then
    head -n 1 "$cache"
    exit 0
  fi
fi

if command -v uv >/dev/null 2>&1; then
  out="$(uv run --no-project --no-config python "$here/branch-bg.py" --strip "$path" "$title" 2>/dev/null)"
else
  out="$(python3 "$here/branch-bg.py" --strip "$path" "$title" 2>/dev/null)"
fi
[ -n "$out" ] || exit 0
printf '%s\n' "$out" > "$cache.tmp" && mv -f "$cache.tmp" "$cache"
field="$(printf '%s\n' "$out" | sed -n 2p)"
if [ -n "$pane" ] && [ -n "$field" ]; then
  # A pane option, never select-pane: that would also move focus to the pane.
  tmux set-option -p -t "$pane" window-style "bg=$field" 2>/dev/null
fi
printf '%s\n' "$out" | head -n 1
