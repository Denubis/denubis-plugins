# RTK architecture notes (from 2026-05-22 research)

Captured here for the next person picking up the approver/rtk work. Source: remote-code-researcher agent reading `https://github.com/rtk-ai/rtk` @ commit `7d31049c88e8bd17aaf70949958fbae9158ad99f`.

## RTK extension surface

**rtk has no runtime extension mechanism.** Rewrite rules are hardcoded Rust in `src/discover/rules.rs::RULES`. Adding a new rewrite requires either:
1. Upstream PR + new rtk release.
2. Maintaining a fork.
3. External hook that does the rewriting before rtk's hook sees the command.

## `~/.config/rtk/config.toml`

```toml
[hooks]
exclude_commands = []
```

- Accepts **source command names** (first token, e.g. `"find"`, `"curl"`).
- Compiled in `src/discover/registry.rs::compile_exclude_patterns()` (~line 650–670) to `^command($|\s)` regex.
- Matched in `is_excluded()` (~line 715) against the full command string.
- Both bare command names AND user-provided `^...` regex patterns work.

## `~/.config/rtk/filters.toml`

**Output-only post-processing.** Schema in `src/core/toml_filter.rs::TomlFilterDef` (~line 85).

A filter block:
- `match_command` — regex matching which command's output to filter.
- 8 pipeline stages: `strip_ansi`, `replace`, `match_output`, `strip_lines_matching`/`keep_lines_matching`, `truncate`, `head`/`tail`, `max_lines`, `on_empty`.

**Cannot be used to add new command rewrites.** Only transforms output of commands rtk already knows about.

## RTK rewrite rules (partial list, from `src/discover/rules.rs`)

| Source command | rtk subcommand | Notes |
|---|---|---|
| `cat`, `head`, `tail` | `rtk read` | pattern `^(cat\|head\|tail)\s+`, line ~83 |
| `curl` | `rtk curl` | line ~475 |
| `wget` | `rtk wget` | line ~483 |
| `find`, `ls`, `tree`, `grep`, `diff`, `wc`, `env` | corresponding rtk subcommand | |
| `git ...` | `rtk git ...` | most subcommands |
| `gh pr/issue/run/api/release` | `rtk gh ...` | |
| `cargo test/build/clippy/check/install/fmt` | `rtk cargo ...` | |
| `docker ps/images/logs/...` | `rtk docker ...` | |
| `kubectl get/logs/describe/apply` | `rtk kubectl ...` | |
| `aws ...` | `rtk aws ...` | |
| `psql` | `rtk psql` | |
| `uv sync` and `uv pip install` | `rtk uv ...` | **ONLY these two uv subcommands** |

**rtk-native does NOT rewrite:**
- `uv run <anything>` (preserves the wrong way — strips uv venv context)
- `uvx <anything>`
- `pnpm test` (does not map to vitest)
- `vue-tsc`
- `bandit`

These were the unique cases the parallel `denubis-hook-rtk-rewrite` shell script handled. With that plugin disabled (2026-05-22), there is currently no automatic rewriting for them. User intends to introduce "a new mechanism" — undefined as of this snapshot.

## CLI knobs worth knowing

- `rtk hook check <cmd>` — dry-run, shows what rtk would rewrite the command to.
- `rtk hook claude` — the PreToolUse hook entry point, reads JSON from stdin, returns `hookSpecificOutput.updatedInput`.
- `rtk config --create` — writes a default config file.
- `rtk gain` — shows token savings analytics from rtk's own tracking.
- `rtk cc-economics` — compares spend (via ccusage) vs savings.

## What ships with `rtk hook claude` cleanly

A full mirror of the hardcoded RULES — `rtk hook claude` rewrites every command listed above. The `denubis-hook-rtk-rewrite` plugin was a parallel rewriter; for commands rtk-native handles, the custom script was effectively a no-op because rtk's hook fires first in the PreToolUse chain and the custom script's `case "$FIRST_CMD" in rtk\ *) exit 0` short-circuits when it sees the already-rewritten command.

## Pinned versions

- rtk: `0.40.0` (per `rtk --version` at /home/brian/.local/bin/rtk on 2026-05-22).
- Investigation conducted against rtk source at commit `7d31049c88e8bd17aaf70949958fbae9158ad99f`.
- Claude Code: `2.1.145` (from stop_hook_summary event metadata in the stalled session).
