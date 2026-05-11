# denubis-hook-rtk-rewrite — Context (Level 0)

> System boundary: a single bash script auto-discovered by the `pretooluse-bash` dispatcher that rewrites a long list of CLI invocations to their `rtk` equivalents, returning an `updatedInput` so Claude Code runs the rewritten command instead.

## Diagram

```mermaid
flowchart LR
    Disp[pretooluse-bash dispatcher\n(sibling plugin)]
    Rtk[rtk binary on PATH]
    Jq[jq binary on PATH]

    Hook((0.0\npretooluse-bash.sh))

    Disp -->|"PreToolUse:Bash JSON on stdin\n(via priority-50\npretooluse-bash.sh wrapper)"| Hook
    Hook -->|"presence check"| Rtk
    Hook -->|"parse + emit JSON"| Jq
    Hook -->|"updatedInput.command\nwith rtk-prefixed rewrite,\npermissionDecision: allow"| Disp
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| `denubis-hook-pretooluse-dispatcher` | Discovers this plugin's `pretooluse-bash.sh` (priority 50) and runs it with the original `PreToolUse:Bash` stdin. Merges this plugin's `updatedInput` into the dispatcher's reply. | `tool_input.command` extracted via `jq` (`plugins/denubis-hook-rtk-rewrite/hooks/pretooluse-bash.sh::INPUT`, `c580ff0`) | `hookSpecificOutput` with `permissionDecision: "allow"`, `permissionDecisionReason: "RTK auto-rewrite"`, and `updatedInput.command` set to the rewritten command (`pretooluse-bash.sh`, `c580ff0`) |
| `rtk` binary | The user's Rust Token Killer CLI. If missing, the hook exits silently and the original command runs as-is. | `command -v rtk` presence check (`pretooluse-bash.sh`, `c580ff0`) | (the rewritten command is later executed by Claude Code, but this hook does not invoke `rtk` itself — it only emits the rewritten string) |
| `jq` binary | Required for stdin parsing and output construction. If missing, the hook exits silently. | `command -v jq` presence check (`pretooluse-bash.sh`, `c580ff0`) | (used internally for JSON I/O) |

## System Boundary

**In scope:**
- Match the first command in a Bash invocation against a fixed list of regex patterns and prefix it with `rtk` (often via `sed` substitution) — covering git, gh, cargo, file ops (`cat`, `rg`/`grep`, `ls`, `tree`, `find`, `diff`, `head`), JS/TS tooling (`vitest`, `pnpm`, `npm`, `npx`, `tsc`, `vue-tsc`, `eslint`, `prettier`, `playwright`, `prisma`), Docker (`compose`, `ps`, `images`, `logs`, `run`, `build`, `exec`), `kubectl` (`get`, `logs`, `describe`, `apply`), network (`curl`, `wget`), pnpm (`list`/`ls`/`outdated`), Python tooling (`ruff`, `mypy`, `bandit`, `uv sync`, `uv pip`, `pip`), Go tooling (`go test`/`build`/`vet`, `golangci-lint`), `env`, `wc`, `psql`, `aws` (`pretooluse-bash.sh`, `c580ff0`).
- Preserve a leading environment-variable prefix (e.g. `TEST_SESSION_ID=2 npx playwright test`) by stripping it for pattern matching but re-attaching for the rewrite (`pretooluse-bash.sh`, `c580ff0`).
- Special-case `uv run <tool>` invocations so the rewrite becomes `uv run rtk <tool>` (preserving the uv venv context) (`pretooluse-bash.sh`, `c580ff0`).
- Skip `git -C <path>` (rtk-git doesn't support it) and `git commit` with flags rtk doesn't support (`--amend`, `--no-edit`, `--fixup`, `--squash`, `--allow-empty`, `-F`) (`pretooluse-bash.sh`, `c580ff0`).
- Skip `gh` calls that include `--json` (rtk reformats output, breaking JSON parsing) (`pretooluse-bash.sh`, `c580ff0`).
- Skip commands that already start with `rtk` or that contain heredocs (`<<`) (`pretooluse-bash.sh`, `c580ff0`).

**Out of scope:**
- Rewriting `pytest` (deliberately — the author's comment notes that RTK's pytest wrapper causes doubled output in Claude Code's Bash tool when exit code is non-zero) (`pretooluse-bash.sh`, `c580ff0`).
- Any command not in the matched list — the script exits without rewriting (`pretooluse-bash.sh`, `c580ff0`).
- Tools other than `Bash` — handled by `tool_name` filtering upstream.

## Hook Registration

`plugins/denubis-hook-rtk-rewrite/hooks/hooks.json` (`3467c0a`) is `{"hooks": {}}` — this plugin does **not** register itself directly with Claude Code. Discovery happens via `denubis-hook-pretooluse-dispatcher`. The wrapper file:

- `plugins/denubis-hook-rtk-rewrite/hooks/pretooluse-bash.sh` (`c580ff0`):
  - First-line metadata: `# dispatcher-priority: 50` (the default — security plugins run earlier).
  - Body: the rewrite logic itself (it is both the convention file and the implementation).

## Cross-References

- **Plugin manifest:** `plugins/denubis-hook-rtk-rewrite/hooks/.claude-plugin/plugin.json` (`52da338`), version 1.1.0.
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **README:** `plugins/denubis-hook-rtk-rewrite/README.md`.
- **Dispatcher that runs this plugin:** `denubis-hook-pretooluse-dispatcher`.
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
