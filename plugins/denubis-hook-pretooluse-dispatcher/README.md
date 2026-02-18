# PreToolUse:Bash Dispatcher

Solves Claude Code's parallel hook execution problem. When multiple PreToolUse:Bash hooks are registered, Claude Code runs them all in parallel and their outputs conflict — `updatedInput` from one hook can be discarded by another's empty output.

This plugin registers as the **single** PreToolUse:Bash hook and sequentially runs scripts from a drop directory, merging their outputs deterministically.

## Setup

The `/setup` command handles this automatically. Manual setup:

1. Create the drop directory:
   ```bash
   mkdir -p ~/.claude/hooks/pretooluse-bash.d
   ```

2. Add hooks as executable scripts with numeric prefixes:
   ```bash
   # Security hooks run first (low numbers)
   ln -sf <path-to-fork-guard>/gh-fork-guard-wrapper.sh ~/.claude/hooks/pretooluse-bash.d/10-fork-guard

   # Token optimisation runs last (high numbers)
   ln -sf ~/.claude/hooks/rtk-rewrite.sh ~/.claude/hooks/pretooluse-bash.d/50-rtk-rewrite
   ```

3. Remove any standalone PreToolUse:Bash hooks from `~/.claude/settings.json` — the dispatcher replaces them.

4. Disable the `denubis-hook-gh-fork-guard` plugin's self-registration (the dispatcher calls it directly).

## Drop Directory Convention

```
~/.claude/hooks/pretooluse-bash.d/
  10-fork-guard        # Security: blocks non-fork gh commands
  50-rtk-rewrite       # Optimisation: rewrites commands for rtk
```

- **00-19:** Security and safety hooks (deny takes priority)
- **20-49:** Validation and advisory hooks
- **50-79:** Optimisation hooks (rtk, output filtering)
- **80-99:** Logging and telemetry hooks

## Merge Rules

Scripts are run in sorted order. Each receives the **original** stdin (not modified by prior hooks).

| Output field | Merge behaviour |
|-------------|----------------|
| `permissionDecision: "deny"` | Wins immediately — stops processing, returns deny |
| `permissionDecision: "allow"` | Preserved if any hook sets it |
| `updatedInput` | Last hook's value wins |
| `additionalContext` | Concatenated from all hooks |
| `systemMessage` | Concatenated from all hooks |

## Adding a New Hook

1. Write your hook script (reads JSON from stdin, outputs JSON to stdout)
2. Make it executable: `chmod +x your-hook.sh`
3. Symlink into the drop directory with an appropriate prefix number
4. Test: `echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | your-hook.sh`

**Do NOT** register PreToolUse:Bash hooks in `settings.json` or plugin `hooks.json` — they will conflict with the dispatcher. All PreToolUse:Bash hooks go through the drop directory.
