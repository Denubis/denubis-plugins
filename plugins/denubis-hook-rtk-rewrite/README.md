# denubis-hook-rtk-rewrite

PreToolUse:Bash hook that rewrites CLI commands to their [RTK (Rust Token Killer)](https://github.com/rtk-ai/rtk) equivalents for token-optimised output.

Auto-discovered by the `denubis-hook-pretooluse-dispatcher` at priority 50.

## How it works

When Claude Code invokes a Bash command, this hook intercepts it and rewrites known commands to pass through `rtk`, which filters verbose output before it reaches the context window. The rewrite is transparent — Claude sees the filtered output as if it ran the original command.

## Rewrite rules

### Simple rewrites: `<tool> args` → `rtk <tool> args`

These commands run directly through rtk's matching subcommand:

| Command | RTK subcommand |
|---|---|
| `git status/diff/log/...` | `rtk git ...` |
| `gh pr/issue/run/api/release` | `rtk gh ...` |
| `cargo test/build/clippy/...` | `rtk cargo ...` |
| `ruff check/format` | `rtk ruff ...` |
| `docker ps/images/logs/...` | `rtk docker ...` |
| `kubectl get/logs/describe/...` | `rtk kubectl ...` |
| `curl`, `wget` | `rtk curl/wget` |
| `ls`, `tree`, `find` | `rtk ls/tree/find` |
| `cat file` | `rtk read file` |
| `head -N file` | `rtk read file --max-lines N` |

### uv run preservation: `uv run <tool>` → `uv run rtk <tool>`

**Critical:** `uv run` provides the project's virtual environment. Stripping it would cause the system tool to run instead of the venv's, potentially using wrong dependencies or the wrong binary entirely.

| Command | Rewrite |
|---|---|
| `uv run ruff check/format ...` | `uv run rtk ruff ...` |
| `uv run playwright ...` | `uv run rtk playwright ...` |
| `uv run ty check ...` | `uv run rtk err ty check ...` |
| `uv run bandit ...` | `uv run rtk err bandit ...` |

### uv subcommand preservation: `uv <subcmd>` → `rtk uv <subcmd>`

| Command | Rewrite |
|---|---|
| `uv pip list/outdated/...` | `rtk summary uv pip ...` |
| `uv sync` | `rtk summary uv sync` |

### uvx wrapping: `uvx <tool>` → `rtk err uvx <tool>`

uvx creates ephemeral environments, so we wrap the entire invocation:

| Command | Rewrite |
|---|---|
| `uvx ty check ...` | `rtk err uvx ty check ...` |
| `uvx bandit ...` | `rtk err uvx bandit ...` |

## Adding new rewrite rules

Edit `hooks/pretooluse-bash.sh`. The pattern is:

```bash
# For bare commands:
elif echo "$MATCH_CMD" | grep -qE '^newtool([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}$(echo "$CMD_BODY" | sed 's/^newtool/rtk newtool/')"

# For uv run commands (MUST preserve uv run):
elif echo "$MATCH_CMD" | grep -qE '^uv[[:space:]]+run[[:space:]]+newtool([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}$(echo "$CMD_BODY" | sed 's/^uv run newtool/uv run rtk newtool/')"

# For uvx commands (wrap entire invocation):
elif echo "$MATCH_CMD" | grep -qE '^uvx[[:space:]]+newtool([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}$(echo "$CMD_BODY" | sed 's/^uvx newtool/rtk err uvx newtool/')"
```

After editing, run tests: `bats tests/test_rtk_rewrite.bats`

## Maintenance

- **Source of truth:** `plugins/denubis-hook-rtk-rewrite/hooks/pretooluse-bash.sh` in this repo
- **After enabling this plugin:** Remove the drop directory symlink to avoid double-rewriting:
  ```bash
  rm ~/.claude/hooks/pretooluse-bash.d/50-rtk-rewrite
  ```
  The dispatcher auto-discovers convention files from enabled marketplace plugins, so the drop directory entry is no longer needed.
- **When adding rtk support for a new tool:** add the bare form, then check if `uv run` and `uvx` variants are also needed
- **Test after changes:** `bats tests/test_rtk_rewrite.bats`

## Skip conditions

The hook exits silently (no rewrite) when:
- `rtk` or `jq` not installed
- Command already starts with `rtk`
- Command contains heredocs (`<<`)
- Command starts with `cd` or other non-matching prefix (compound commands)
- No pattern matches
