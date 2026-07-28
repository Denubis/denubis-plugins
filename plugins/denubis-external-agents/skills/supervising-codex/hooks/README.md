# Codex hook wiring

The supervision relay is **global**, in `~/.codex/hooks.json`. Install it once per
machine:

```sh
uv run "${CLAUDE_PLUGIN_ROOT}/skills/supervising-codex/hooks/install-codex-hooks.py"
```

Then run `/hooks` in Codex to trust the new entries, and restart any running Codex
session, because Codex reads its hooks at startup.

## Why global rather than per-project

A project-local `.codex/hooks.json` only wakes the monitor in directories somebody set
up in advance. That leaves a Codex started in a fresh directory unsupervised precisely
when nobody was thinking about supervision, which is the case that needs supervision
most.

The relay was project-local upstream for a reason that no longer applies: the script it
called lived in the project. That script now sits at a stable path in the installed
plugin, so nothing project-shaped is left to justify per-project wiring.

**Leaving it wired everywhere is cheap and safe.** The relay addresses a per-pane socket
derived from its inherited `$TMUX_PANE`, so it only ever reaches the monitor watching
that exact pane, and with no monitor listening it prints nothing and exits 0. Verified
2026-07-28 by piping a `Stop` payload through the exact installed command string with
nothing listening. The cost is one short-lived process per hook event, bounded by the
five-second timeout.

## What the installer does

Five events, each at `timeout: 5`: `SessionStart`, `UserPromptSubmit`,
`PermissionRequest`, `PostToolUse`, `Stop`.

It **merges**. It edits a file it does not own, which may hold hooks other tools wrote,
so it preserves everything it did not write and backs the file up before touching it.
On this machine it sits alongside a `Stop` hook firing a desktop notification.

It is **idempotent**, and it **repairs a stale path**. The relay names an absolute
path, so moving or reinstalling the plugin leaves a command that still looks like the
relay but points at a script that is gone. The installer rewrites those rather than
seeing the marker and skipping, because presence and correctness are different
questions. `tests/test_codex_hooks_installer.py` pins all three behaviours.

**Which copy it points at is decided by where you run it from**, since it resolves the
supervisor relative to its own location. Prefer the managed checkout under
`~/.claude/plugins/marketplaces/`, not a development checkout: a working tree
mid-edit can carry a syntax error, and a global hook pointing at it breaks Codex hooks
machine-wide. Re-run the installer after moving anything.

## Privacy

The relay sends event kinds, scope flags and opaque digests. It does not transport
prompts, commands, tool results, transcripts, or assistant messages.
`tests/test_codex_supervisor.py` pins that with a generative property test over
arbitrary text.

## Prior machine state, recorded 2026-07-28

`~/.codex/hooks.json` previously held one hook, a `Stop` firing
`session-runner/bin/notify-agent.sh`, which is the operator's own tool and is not
shipped here. Drop that entry if the tool is absent.

`~/.codex/config.toml` must carry `hooks = true` under `[features]`, or none of this
fires.

### Deliberately not restored

Until 2026-07-20 the global file also wired four events to `tmux-agent-status`. The
backup at `~/.codex/hooks.json.pre-state-glyph-disable-20260720` records what was there,
and its name records the intent: the glyph was switched off on purpose. Noted so a
rebuild can tell "deliberately disabled" from "lost".

### Stale trust state, unresolved

`config.toml` holds `[hooks.state]` entries naming slots that no longer match the file,
including a `stop:0:0` whose command changed since it was trusted. Whether Codex
re-prompts on a hash mismatch or silently declines to run the hook is **not
established**. Confirm with `/hooks` rather than assuming.
