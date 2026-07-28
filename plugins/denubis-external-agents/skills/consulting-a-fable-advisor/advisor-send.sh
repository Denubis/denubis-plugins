#!/usr/bin/env bash
# Send one literal message to an advisor pane and confirm it actually submitted.
#
# Bundled here because the spawn script used to tell operators to drive the pane
# with `codex-send.sh`, a script this plugin does not ship: it lived only in two
# unrelated project checkouts, so anyone installing denubis-external-agents from
# the marketplace was handed an invocation that did not exist on their machine.
# Ported from that script (melica/scripts/codex-send.sh, 2026-07-18 lineage) and
# generalised, since the mechanics are the same for any agent pane.
#
# Multi-line safe: the message goes through tmux bracketed paste (load-buffer +
# paste-buffer -p), so embedded newlines land as soft newlines in the composer
# rather than as premature Enter keystrokes. Pass "-" to read from stdin.
#
# The composer sometimes swallows the first Enter after a paste, so submission
# is confirmed rather than assumed: the pane going busy, or the composer no
# longer showing our text, counts as submitted. Enter is retried twice before
# giving up, because reporting a send that never happened is worse than failing.
#
# Usage: advisor-send.sh <pane-id> <message...|->

set -u

pane="${1:?usage: advisor-send.sh <pane-id> <message|->}"
shift
msg="$*"
[ "$msg" = "-" ] && msg="$(cat)"
[ -n "$msg" ] || { echo "empty message" >&2; exit 2; }

# Refuse to drive a pane that is not an agent pane in the caller's window.
#
# The check this replaced only asked whether the pane existed *somewhere*,
# using `list-panes -a`, which is every pane in every session. A stale or
# mistyped id therefore passed it and typed the message into whatever pane now
# holds that id. `tmux-send-guard` additionally requires the pane to be in the
# caller's own window and to be running claude, codex or agy2 (walking the
# pane's process descendants, because a Claude pane reports its foreground
# command as `bash`).
#
# The guard ships beside this script, so a marketplace install carries its own
# copy and there is no machine where it can be missing. `~/.claude/bin` is
# checked first because claude-sync carries a copy there for send scripts that
# live outside this plugin, and one guard on the machine beats two that drift.
#
# There is deliberately no fallback. An earlier draft degraded to the old
# existence check with a warning, reasoning that this was no worse than before;
# but "no worse than before" here means a stale id still types into somebody
# else's window, which is the whole defect. A guard with a documented bypass is
# a suggestion. If it cannot run, neither should the send.
_guard=""
for _candidate in \
  "$HOME/.claude/bin/tmux-send-guard" \
  "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/../../scripts/tmux-send-guard" \
  "$(command -v tmux-send-guard 2>/dev/null)"
do
  [ -n "$_candidate" ] && [ -x "$_candidate" ] && { _guard="$_candidate"; break; }
done

[ -n "$_guard" ] || {
  echo "advisor-send: tmux-send-guard not found; refusing to send unguarded" >&2
  exit 1
}
"$_guard" "$pane" || exit 1

printf '%s' "$msg" | tmux load-buffer -b advisor-send - || exit 1
tmux paste-buffer -b advisor-send -t "$pane" -p -d || exit 1
sleep 1

# First line, truncated: enough to recognise our own text still sitting in the
# composer, short enough to survive the pane's wrapping.
probe="$(printf '%s' "$msg" | head -n 1 | head -c 40)"

for _attempt in 1 2 3; do
  tmux send-keys -t "$pane" Enter
  for _ in 1 2 3 4; do
    sleep 1
    title="$(tmux display-message -p -t "$pane" '#{pane_title}' 2>/dev/null)" || {
      echo "pane $pane went away mid-send" >&2
      exit 1
    }
    case "$title" in
      *Working* | *working* | *✳*) echo "submitted (pane busy)"; exit 0 ;;
    esac
    if ! tmux capture-pane -t "$pane" -p | tail -6 | grep -qF "$probe"; then
      echo "submitted (composer cleared)"
      exit 0
    fi
  done
done

echo "NOT SUBMITTED after 3 Enter attempts — inspect the pane" >&2
exit 3
