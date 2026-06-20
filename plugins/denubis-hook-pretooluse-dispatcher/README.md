# PreToolUse:Bash Dispatcher

Solves Claude Code's parallel hook execution problem. When multiple PreToolUse:Bash hooks are registered, Claude Code runs them all in parallel and their outputs conflict — `updatedInput` from one hook can be discarded by another's empty output.

This plugin registers as the **single** PreToolUse:Bash hook and runs hooks sequentially, merging their outputs deterministically.

## Hook Sources

Hooks are discovered from two sources, merged by priority, and run in order:

### 1. Plugin convention files (auto-discovered)

Any marketplace plugin with an executable `hooks/pretooluse-bash.sh` is automatically discovered. Declare priority via a comment in the first 5 lines:

```bash
#!/usr/bin/env bash
# dispatcher-priority: 10
```

Default priority if not declared: 50. Lower numbers run first.

Only plugins enabled in `settings.json` are discovered.

### 2. Drop directory (manual)

`~/.claude/hooks/pretooluse-bash.d/` — for non-plugin hooks. Numeric prefix = priority:

```
~/.claude/hooks/pretooluse-bash.d/
  50-my-hook           # Symlink to ~/.claude/hooks/my-hook.sh
```

## Priority Ranges

- **00-19:** Security and safety hooks (deny takes priority)
- **20-49:** Validation and advisory hooks
- **50-79:** Optimisation and output-filtering hooks
- **80-99:** Logging and telemetry hooks

## Merge Rules

Hooks are run in priority order. Each receives the **original** stdin (not modified by prior hooks).

| Output field | Merge behaviour |
|-------------|----------------|
| `permissionDecision: "deny"` | Wins immediately — stops processing, returns deny |
| `permissionDecision: "allow"` | Preserved if any hook sets it |
| `updatedInput` | Last hook's value wins |
| `additionalContext` | Concatenated from all hooks |
| `systemMessage` | Concatenated from all hooks |

## Caching

Discovered hooks are cached at `~/.claude/hooks/.pretooluse-bash-cache`. The cache is automatically invalidated when:
- Convention files are added, removed, or modified
- Drop directory contents change
- `settings.json` changes (plugin enable/disable)

## Diagnostics

Run with `--list` to see discovered hooks and cache state:

```bash
uv run python /path/to/pretooluse-bash-dispatcher.py --list
```

## Setup

The `/setup` command handles this automatically. Manual setup:

1. Remove any standalone PreToolUse:Bash hooks from `~/.claude/settings.json` — the dispatcher replaces them.

2. For non-plugin hooks, create the drop directory and add entries:
   ```bash
   mkdir -p ~/.claude/hooks/pretooluse-bash.d
   ln -sf /path/to/hook.sh ~/.claude/hooks/pretooluse-bash.d/50-my-hook
   ```

3. For plugin hooks, add `hooks/pretooluse-bash.sh` to your plugin with a `# dispatcher-priority:` comment. The dispatcher discovers it automatically when the plugin is enabled.

## Adding a New Hook

**Plugin hook (recommended):** Add an executable `hooks/pretooluse-bash.sh` to your plugin. Include `# dispatcher-priority: N` in the first 5 lines. The dispatcher auto-discovers it.

**Non-plugin hook:** Write a script, make it executable, symlink into the drop directory with a numeric prefix: `ln -sf /path/to/hook.sh ~/.claude/hooks/pretooluse-bash.d/50-my-hook`

**Do NOT** register PreToolUse:Bash hooks in `settings.json` or plugin `hooks.json` — they will conflict with the dispatcher.

## Adding Priority Overrides (future)

Currently, plugin hook priorities come from the `# dispatcher-priority:` comment (or default 50). If a third-party plugin needs a different priority than it declares, the workaround is: disable the plugin, create a drop directory wrapper at the desired priority that calls the plugin's convention file directly.

A dedicated priority override mechanism can be added when this becomes a real need.
