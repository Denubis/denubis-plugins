# denubis-hook-branch-bg — Context (Level 0)

> System boundary: a single Python script invoked by Claude Code or Codex on session start
> that recolours the terminal background based on the current Git repo and branch.

## Diagram

```mermaid
flowchart LR
    CC[Claude Code or Codex host]
    Git[git CLI]
    Proc@{ shape: das, label: "/proc filesystem" }
    TTY[Terminal device\n/dev/pts/* or /dev/tty*]

    Hook((0.0\nbranch-bg.py))

    CC -->|"SessionStart event\n(matcher: startup|resume|clear|compact)"| Hook
    Hook -->|"git rev-parse --git-common-dir\ngit rev-parse --abbrev-ref HEAD"| Git
    Git -->|"common dir path, branch name"| Hook
    Hook -->|"read /proc/<pid>/fd/0\nread /proc/<pid>/stat (ppid walk)"| Proc
    Hook -->|"OSC 11 escape sequence\n\\033]11;#RRGGBB\\007"| TTY
    Hook -->|"no model context on ordinary success"| CC
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| Agent host | Claude Code or Codex emits the `SessionStart` event that triggers the hook. | `SessionStart` event payload; the script itself does not consume provider-specific fields | No stdout on ordinary success; the hook's useful output goes directly to the terminal device (`plugins/denubis-hook-branch-bg/hooks/branch-bg.py::main`) |
| git CLI | Invoked twice as a subprocess to learn the repo identity and current branch. | `git rev-parse --git-common-dir`; `git rev-parse --abbrev-ref HEAD` (`branch-bg.py::get_git_info`, `f0d1846`) | Common-dir path; branch name |
| `/proc` filesystem | Read to walk the process tree from the hook's PID up to the controlling terminal. | `readlink /proc/<pid>/fd/0`; `cat /proc/<pid>/stat` (`branch-bg.py::find_terminal`, `f0d1846`) | File-descriptor target; parent PID |
| Terminal device | The `/dev/pts/*` or `/dev/tty*` device file the OSC 11 escape sequence is written to. | OSC 11 string `\033]11;#RRGGBB\007` (`branch-bg.py::set_terminal_bg`, `f0d1846`) | (none) |

## System Boundary

**In scope:**
- Mapping `(git common-dir, branch name)` to an RGB colour and emitting OSC 11 to set the terminal background. Repo path → base hue at L=0.12 / S=0.60; non-main/master branches offset hue ±40°, lightness ±0.03, saturation ±0.10 from the base (`branch-bg.py::git_info_to_colour`, `f0d1846`).
- Walking the process tree from the hook's own PID up to the first PID whose stdin is a `/dev/pts/*` or `/dev/tty*` device, to find the right TTY to write to (`branch-bg.py::find_terminal`, `f0d1846`).
- Remaining silent to the model on ordinary success (`branch-bg.py::main`).

**Out of scope:**
- Persisting or restoring the prior terminal colour (the hook does not save what it overwrites).
- Non-`SessionStart` events — both provider registrations contain only `SessionStart`.
- Non-git directories — `get_git_info` returns `(None, None)` and `main` skips the colour step (`branch-bg.py`, `f0d1846`).
- Platforms without `/proc` — `find_terminal` returns `None` and `set_terminal_bg` returns without writing (`branch-bg.py::find_terminal`, `f0d1846`).
- Failure reporting — `subprocess` errors, `OSError`, and `PermissionError` are caught silently (`branch-bg.py::get_git_info`, `set_terminal_bg`, `f0d1846`).

## Hook Registration

Claude Code registers `plugins/denubis-hook-branch-bg/hooks/claude-hooks.json`:

- **Event:** `SessionStart`
- **Matcher:** `startup|resume|clear|compact`
- **Command:** `uv run --no-project --no-config python "${CLAUDE_PLUGIN_ROOT}/hooks/branch-bg.py"`
- **Timeout:** 5 seconds
- **suppressOutput:** `true`
- **Why `--no-project --no-config`:** the launcher must ignore the caller's cwd. A malformed `pyproject.toml` there (e.g. git conflict markers mid-merge) otherwise wedges `uv` in settings discovery before the hook runs. Guarded by `tests/test_hook_launcher_cwd_independence.py`.

Codex registers `plugins/denubis-hook-branch-bg/hooks/codex-hooks.json`. It invokes the
same standard-library script with `python3 "${PLUGIN_ROOT}/hooks/branch-bg.py"`, has no
Claude lifecycle matcher, and remains subject to Codex's native hook-trust boundary.

## Cross-References

- **Plugin manifests:** `plugins/denubis-hook-branch-bg/.claude-plugin/plugin.json` and
  `plugins/denubis-hook-branch-bg/.codex-plugin/plugin.json`, version 0.2.6.
- **Marketplace entries:** `.claude-plugin/marketplace.json` and
  `.agents/plugins/marketplace.json`.
- **Related architecture docs:** `../../README.md` (index), `../../glossary.md`, `../../constraints.md`.
- **Sibling hook plugins** (peer entities under Claude Code's hook system, not consumers of this plugin's output): `denubis-hook-gh-fork-guard`, `denubis-hook-pretooluse-dispatcher`.
