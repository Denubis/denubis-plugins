# denubis-hook-gh-fork-guard — Context (Level 0)

> System boundary: a Python script auto-discovered by the `pretooluse-bash` dispatcher that inspects `gh` CLI invocations and denies any that target a repo other than the currently-configured fork.

## Diagram

```mermaid
flowchart LR
    Disp[pretooluse-bash dispatcher\n(sibling plugin)]
    Env@{ shape: das, label: "ALLOWED_GH_REPO env var\n(if set)" }
    Git[git CLI]

    Hook((0.0\ngh-fork-guard.py))

    Disp -->|"PreToolUse:Bash event\n(tool_name + tool_input.command\non stdin, via priority-10\npretooluse-bash.sh wrapper)"| Hook
    Env --> Hook
    Hook -->|"git remote get-url origin\n(fallback when env var unset)"| Git
    Git -->|"origin URL → owner/repo"| Hook
    Hook -->|"deny + systemMessage if any\ngh sub-command targets a\nnon-fork repo; otherwise\nadvisory additionalContext\nor no output"| Disp
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| `denubis-hook-pretooluse-dispatcher` | Discovers this plugin's `pretooluse-bash.sh` (priority 10) and runs it with the original `PreToolUse:Bash` stdin. Merges this plugin's output into the dispatcher's reply to Claude Code. | `tool_name` and `tool_input.command` (`plugins/denubis-hook-gh-fork-guard/hooks/gh-fork-guard.py::main`, `f62e8a6`) | `permissionDecision: "deny"` with a `systemMessage` naming the bad repo and the allowed one; or `additionalContext` advising default-repo verification when no `--repo` is given; or no output if no `gh` command is present (`gh-fork-guard.py::deny`, `gh-fork-guard.py::main`, `f62e8a6`) |
| `ALLOWED_GH_REPO` env var | Optional explicit allow-list of one repo in `owner/repo` form. Takes precedence over the git-origin fallback. | The variable value at script-import time (`gh-fork-guard.py::get_allowed_repo`, `f62e8a6`) | (none) |
| git CLI | Fallback source of the allowed repo when `ALLOWED_GH_REPO` is unset. | `git remote get-url origin` (`gh-fork-guard.py::get_allowed_repo`, `f62e8a6`) | Origin URL (https or ssh) which the script normalises to `owner/repo` (`gh-fork-guard.py::get_allowed_repo`, `f62e8a6`) |

## System Boundary

**In scope:**
- Split the Bash command on shell operators (`&&`, `||`, `;`, `|`) and find each individual `gh ...` sub-command (`gh-fork-guard.py::extract_gh_commands`, `f62e8a6`).
- For each, run three checks: `--repo`/`-R` flag value, `gh api repos/OWNER/REPO/...` path, and explicit `owner/repo` positional after a `gh repo <verb>` (`gh-fork-guard.py::check_repo_flag`, `check_api_path`, `check_explicit_repo_arg`, `f62e8a6`).
- Compare each candidate repo case-insensitively against the allowed repo, after normalising `.git` and URL prefixes (`gh-fork-guard.py::repo_is_allowed`, `f62e8a6`).
- A single bad sub-command in a compound expression denies the entire Bash call (`gh-fork-guard.py::main`, `f62e8a6`).
- When no explicit `--repo` is given but the call touches a repo-interacting subcommand (`issue`, `pr`, `release`, `run`, `workflow`, `label`, `milestone`, `project`, `variable`, `secret`, `cache`, `ruleset`, `deploy-key`), emit an advisory `additionalContext` telling the model to verify `gh repo set-default` (`gh-fork-guard.py::main`, `f62e8a6`).

**Out of scope:**
- Tools other than `Bash` — the script exits silently (`gh-fork-guard.py::main`, `f62e8a6`).
- Calls when neither `ALLOWED_GH_REPO` nor a git origin is available — the script exits silently with nothing to protect (`gh-fork-guard.py::main`, `f62e8a6`).
- `gh` invocations that don't reference a repo at all (e.g. `gh auth status`).

## Hook Registration

`plugins/denubis-hook-gh-fork-guard/hooks/hooks.json` (`3c1a04f`) is `{"hooks": {}}` — this plugin does **not** register itself directly with Claude Code. Discovery happens via `denubis-hook-pretooluse-dispatcher`, which scans enabled marketplace plugins for `hooks/pretooluse-bash.sh`. This plugin's wrapper:

- `plugins/denubis-hook-gh-fork-guard/hooks/pretooluse-bash.sh` (`566f230`):
  - First-line metadata: `# dispatcher-priority: 10` (early — security runs before rewrites).
  - Body: `exec uv run python3 "$SCRIPT_DIR/gh-fork-guard.py"`.

## Cross-References

- **Plugin manifest:** `plugins/denubis-hook-gh-fork-guard/.claude-plugin/plugin.json` (`6557abb`), version 1.2.2.
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **Dispatcher that runs this plugin:** `denubis-hook-pretooluse-dispatcher`.
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
