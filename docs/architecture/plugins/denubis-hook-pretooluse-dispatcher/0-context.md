# denubis-hook-pretooluse-dispatcher — Context (Level 0)

> System boundary: a single Python script registered as the `PreToolUse:Bash` hook, which auto-discovers sibling-plugin and drop-directory hooks and runs them sequentially with merged outputs.

## Diagram

```mermaid
flowchart LR
    CC[Claude Code host]
    Settings@{ shape: das, label: "~/.claude/settings.json\nenabledPlugins map" }
    Marketplace@{ shape: das, label: "$DISPATCHER_MARKETPLACE_DIR\n(default ~/.claude/plugins/marketplaces)" }
    DropDir@{ shape: das, label: "$DISPATCHER_DROP_DIR\n(default ~/.claude/hooks/pretooluse-bash.d)" }
    Cache@{ shape: das, label: "$DISPATCHER_CACHE_FILE\n(default ~/.claude/hooks/.pretooluse-bash-cache)" }
    SubHooks[Sub-hook scripts\n(plugin pretooluse-bash.sh\nor drop-dir executables)]

    Disp((0.0\npretooluse-bash-dispatcher.py))

    CC -->|"PreToolUse:Bash event\nJSON on stdin"| Disp
    Settings --> Disp
    Marketplace --> Disp
    DropDir --> Disp
    Cache <-->|"read cached hook list /\nwrite new list on miss"| Disp
    Disp -->|"original stdin (each)"| SubHooks
    SubHooks -->|"per-hook JSON output"| Disp
    Disp -->|"merged hookSpecificOutput\n(deny wins immediately;\nallow / updatedInput / context /\nsystemMessage accumulated)"| CC
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| Claude Code host | Emits `PreToolUse:Bash` events. | `PreToolUse:Bash` JSON payload on stdin (`plugins/denubis-hook-pretooluse-dispatcher/hooks/pretooluse-bash-dispatcher.py::main`, `dd9c992`) | Merged `hookSpecificOutput` JSON (and optional `systemMessage`) on stdout, or an immediate `deny` short-circuit (`pretooluse-bash-dispatcher.py`, `dd9c992`) |
| `~/.claude/settings.json` (`$DISPATCHER_SETTINGS_FILE`) | Source of the `enabledPlugins` map used to filter discovered plugin hooks. Read with Python `json`. | `.enabledPlugins[<plugin>@<marketplace>]` boolean (`pretooluse-bash-dispatcher.py::_discover_plugins`, `dd9c992`) | (none) |
| Marketplace plugin directory (`$DISPATCHER_MARKETPLACE_DIR`) | Default `~/.claude/plugins/marketplaces`. Scanned for `*/plugins/*/hooks/pretooluse-bash.sh`. | Glob of plugin convention files; first 5 lines of each, parsed for `# dispatcher-priority: N` (default 50) (`pretooluse-bash-dispatcher.py::_read_priority`, `dd9c992`) | (none) |
| Drop directory (`$DISPATCHER_DROP_DIR`) | Default `~/.claude/hooks/pretooluse-bash.d/`. Scanned for executables; numeric filename prefix is the priority. | Executable filenames (`pretooluse-bash-dispatcher.py::_discover_drop`, `dd9c992`) | (none) |
| Cache file (`$DISPATCHER_CACHE_FILE`) | Default `~/.claude/hooks/.pretooluse-bash-cache`. Stores the discovered hook list keyed by the size and mtime of the source-directory contents plus the settings file mtime. | Cached hook list (`pretooluse-bash-dispatcher.py::get_hook_list`, `dd9c992`) | New cache file on cache miss (`pretooluse-bash-dispatcher.py::get_hook_list`, `dd9c992`) |
| Sub-hook scripts | Plugin `pretooluse-bash.sh` files and drop-directory executables. Each receives the original `PreToolUse:Bash` stdin. | The original stdin (`pretooluse-bash-dispatcher.py::run_hooks`, `dd9c992`) | JSON output that the dispatcher parses for `permissionDecision`, `updatedInput`, `additionalContext`, `systemMessage` (`pretooluse-bash-dispatcher.py::_merge_hook_output`, `dd9c992`) |

## System Boundary

**In scope:**
- Discover plugin hooks at `$DISPATCHER_MARKETPLACE_DIR/*/plugins/*/hooks/pretooluse-bash.sh` that are executable and whose enclosing plugin is `true` in `enabledPlugins` (`pretooluse-bash-dispatcher.py::_discover_plugins`, `dd9c992`).
- Discover drop-dir hooks at `$DISPATCHER_DROP_DIR/*` that are executable, with numeric prefix as priority (`pretooluse-bash-dispatcher.py::_discover_drop`, `dd9c992`).
- Sort the union by priority (lower = earlier) and run each with the original stdin (`pretooluse-bash-dispatcher.py::run_hooks`, `dd9c992`).
- Merge per-hook outputs per these rules: a `deny` from any hook short-circuits the loop and is returned as-is; `allow` decisions are preserved with their reason; `updatedInput` from later hooks overrides earlier ones; `additionalContext` and `systemMessage` are concatenated (`pretooluse-bash-dispatcher.py::_merge_hook_output`, `dd9c992`).
- Cache the discovered list keyed on the size and mtime of both source directories' contents plus the settings file's mtime, refreshed on miss (`pretooluse-bash-dispatcher.py::compute_cache_key`, `get_hook_list`, `dd9c992`).
- Support `--list` diagnostic mode that prints the discovered hooks, sources, and current cache state (`pretooluse-bash-dispatcher.py::_print_list`, `dd9c992`).

**Out of scope:**
- Any policy of its own — every decision comes from a sub-hook. The dispatcher is purely orchestration.
- Modifying or reordering a sub-hook's stdin — each receives the original input verbatim (`pretooluse-bash-dispatcher.py::_run_one`, `dd9c992`).
- Watching for new sub-hooks during a single dispatch — discovery is per-event.

## Hook Registration

Registered in `plugins/denubis-hook-pretooluse-dispatcher/hooks/hooks.json` (`dd9c992`):

- **Event:** `PreToolUse`
- **Matcher:** `Bash`
- **Command:** `uv run python "${CLAUDE_PLUGIN_ROOT}/hooks/pretooluse-bash-dispatcher.py"`
- **Timeout:** 15 seconds

## Cross-References

- **Plugin manifest:** `plugins/denubis-hook-pretooluse-dispatcher/hooks/.claude-plugin/plugin.json` (`a9b22d8`), version 1.1.0.
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **README:** `plugins/denubis-hook-pretooluse-dispatcher/README.md`.
- **Sub-hooks discovered today (in this marketplace, both with empty `hooks.json` and a `pretooluse-bash.sh` wrapper):** `denubis-hook-gh-fork-guard` (priority 10), `denubis-hook-rtk-rewrite` (priority 50).
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
