# Codex hook wiring

Two separate files, two separate homes. Recorded here so a new machine can be brought up
without rediscovering them, since `claude-sync` covers `~/.claude` and nothing covers
`~/.codex`.

Codex runs a hook `command` through a shell, so `$HOME` and `$(…)` expand. Captured
2026-07-28 from a working machine.

## `project-codex-hooks.json` → `<project>/.codex/hooks.json`

Wakes the supervision monitor immediately instead of leaving it on its poll deadline.
Five events, each with `timeout: 5`: `SessionStart`, `UserPromptSubmit`,
`PermissionRequest`, `PostToolUse`, `Stop`.

Install, then trust it with `/hooks` inside Codex, then **restart any already-running Codex
session** in that project, because the hook file is read at startup.

```sh
mkdir -p .codex
cp "$HOME/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-external-agents/skills/supervising-codex/hooks/project-codex-hooks.json" .codex/hooks.json
```

**Why that script path and not the versioned one.** The plugin cache is version-pinned
(`~/.claude/plugins/cache/denubis-plugins/denubis-external-agents/0.7.0/…`) and the
directory is replaced on every release, so a hook pinned there breaks at the next version
bump. The `marketplaces/` checkout is a git clone that updates in place, so the path
survives.

**The relay is privacy-bounded by construction.** It sends event kinds, scope flags and
opaque digests. It does not transport prompts, commands, tool results, transcripts, or
assistant messages. `tests/test_codex_supervisor.py` pins that with a generative property
test over arbitrary text.

**It is safe to leave installed when nothing is watching.** With no monitor listening the
hook is a silent no-op and exits 0. Verified 2026-07-28: a `Stop` payload piped to `--hook`
with no listener returned 0 and printed nothing.

## `global-codex-hooks.json` → `~/.codex/hooks.json`

Machine-level, one hook: a desktop notification on `Stop`. Requires
`session-runner/bin/notify-agent.sh`, which is the operator's own tool and is not shipped
here. Drop the hook if that repo is absent.

`~/.codex/config.toml` must also carry `hooks = true` under `[features]`, or none of this
fires.

### What was removed on 2026-07-20, and is deliberately not restored

The global file previously wired four events to `tmux-agent-status`. The backup lives at
`~/.codex/hooks.json.pre-state-glyph-disable-20260720`, and its name records the intent:
the glyph was switched off on purpose. Kept here so a rebuild does not silently resurrect
it, and so a future session can tell "deliberately disabled" from "lost".

```json
"SessionStart":     "bash ~/.config/tmux/plugins/tmux-agent-status/hooks/codex-hook.sh SessionStart",
"UserPromptSubmit": "bash ~/.config/tmux/plugins/tmux-agent-status/hooks/codex-hook.sh UserPromptSubmit",
"PreToolUse":       "bash ~/.config/tmux/plugins/tmux-agent-status/hooks/codex-hook.sh PreToolUse",   // matcher: Bash
"Stop":             "bash ~/.config/tmux/plugins/tmux-agent-status/hooks/codex-hook.sh Stop"
```

### Stale trust state, unresolved

`~/.codex/config.toml` still holds `[hooks.state]` entries for five slots in the global
file — `pre_tool_use:0:0`, `session_start:0:0`, `stop:0:0`, `stop:0:1`,
`user_prompt_submit:0:0` — while the file now contains one hook. `stop:0:0` was
`codex-hook.sh` when trusted and is `notify-agent.sh` now: same slot, different command,
and `stop:0:0` and `stop:0:1` carry an identical `trusted_hash`, which the file alone does
not explain.

Whether Codex re-prompts for trust on a hash mismatch or silently declines to run the hook
is **not established**. Confirm with `/hooks` in a live pane before assuming the surviving
notification still fires on a fresh machine.
