# denubis-plugins

Claude Code plugins for Python/R/SQL/LaTeX development workflows, customised for academic research.

Forked from [ed3d-plugins](https://github.com/ed3dai/ed3d-plugins) and adapted for:
- **Python 3.14+** with t-strings, deferred annotations, and modern idioms
- **Academic workflows** with proper citations, LaTeX conventions, and scholarly rigour
- **Quality over velocity** - Opus for implementation, halt-on-failure policy

## The Big Stick: `denubis-plan-and-execute`

An RPI (research-plan-implement) loop that avoids hallucination by separating design from implementation:

```
Rough Idea
    |
    v
/start-design-plan  --------> Design Document (committed to git)
    |
    v
/start-implementation-plan --> Implementation Plan (phase files)
    |
    v
/execute-implementation-plan -> Working Code (reviewed & committed)
```

Key philosophy changes from upstream:
- **Opus for task implementation** (not Haiku) - fewer mistakes, fewer review cycles
- **Halt on non-obvious failures** - don't grind for 30 minutes working around problems
- **Block on ALL severities** - quality over velocity

**Customisation:** Create `.ed3d/design-plan-guidance.md` and `.ed3d/implementation-plan-guidance.md` in your project to provide project-specific constraints, terminology, and standards. Run `/how-to-customize` for details.

## Plugins

### Core (install these)

These are platform-independent skills and agents. They work on Linux, macOS, and Windows.

| Plugin | What it does |
|--------|-------------|
| **`denubis-plan-and-execute`** | Three-phase workflow: design, plan, execute. 34 skills, 7 agents. The backbone. |
| **`denubis-basic-agents`** | Generic agents (haiku/sonnet/opus) plus `python-developer` and `academic-researcher`. Other plugins depend on this. |
| **`denubis-research-agents`** | Codebase investigation, internet research, and combined-research agents. |
| **`denubis-hook-skill-reinforcement`** | UserPromptSubmit hook that reminds Claude to check for and activate relevant skills. |

### Recommended (quality of life)

| Plugin | What it does |
|--------|-------------|
| **`denubis-extending-claude`** | Meta-skills for writing plugins, agents, skills, CLAUDE.md files, and `/transcript` archiving. |
| **`denubis-git-commit`** | `/commit` as a proper skill with analysis, message drafting, and project conventions. |
| **`denubis-hook-shortcut-detection`** | Stop hook that detects when Claude takes shortcuts and blocks for your go/no-go decision. |
| **`denubis-hook-claudemd-reminder`** | PostToolUse hook that reminds to update CLAUDE.md before commits when changes warrant it. |

### Infrastructure hooks (Linux/macOS only)

These use bash scripts and Unix tooling. **Skip on Windows** unless running WSL.

| Plugin | What it does |
|--------|-------------|
| **`denubis-hook-pretooluse-dispatcher`** | Bash dispatcher that auto-discovers PreToolUse hooks from plugins and a drop directory. |
| **`denubis-hook-rtk-rewrite`** | Rewrites CLI commands to [RTK](https://github.com/rtk-ai/rtk) equivalents for 60-90% token savings. Requires `rtk` + `jq`. |
| **`denubis-hook-gh-fork-guard`** | Blocks `gh` CLI commands targeting repos other than your fork. Auto-discovered by the dispatcher. |

### Terminal-specific

| Plugin | What it does |
|--------|-------------|
| **`denubis-hook-branch-bg`** | Sets terminal background colour by repo/branch via OSC 11. Requires a terminal that supports OSC 11 (Ghostty, iTerm2, WezTerm). |

### Onboarding

| Plugin | What it does |
|--------|-------------|
| **`denubis-00-getting-started`** | This README, plus `/setup` to verify and configure your installation. |

### Domain Agents

**`python-developer`** (Sonnet) - Python 3.14+ with:
- T-strings for SQL/HTML/shell (security-sensitive strings)
- Deferred annotations (no quotes for forward references)
- Bracketless exception handling
- `concurrent.interpreters` for CPU-bound parallelism

**`academic-researcher`** (Opus) - Academic rigour with:
- Proper citations and source attribution
- LaTeX conventions (environments, BibTeX)
- Scholarly argument structure

### Transcript Archiving

The `/transcript` command archives conversations with IDW2025 research metadata:

```
/transcript
```

Outputs:
- **SUMMARY.md** - Human-readable markdown summary
- `index.html` - Full HTML transcript
- `session.meta.json` - Structured metadata (Three Ps framework)

## Prerequisites

### All platforms

- **Claude Code** with a Pro, Max, Team, or Enterprise account
- **Git** (for version control and plugin marketplace)

### For hook plugins (recommended)

- **Python 3.11+** and **[uv](https://docs.astral.sh/uv/)** - used by Python-based hooks (shortcut-detection, claudemd-reminder, code-quality-guard)

### Linux/macOS only

- **bash** - used by infrastructure hooks (dispatcher, RTK rewrite, fork guard)
- **[RTK](https://github.com/rtk-ai/rtk)** and **jq** - for token-optimised output (optional)

## Installation

### Step 1: Install Claude Code

**Linux / macOS / WSL:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://claude.ai/install.ps1 | iex
```

Windows requires [Git for Windows](https://git-scm.com/downloads/win). Claude Code uses Git Bash internally to run commands regardless of which terminal you launch it from.

### Step 2: Install uv (for Python-based hooks)

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Verify: `uv --version`

### Step 3: Add the marketplace

Launch Claude Code and run:
```
/plugin marketplace add https://github.com/Denubis/denubis-plugins.git
```

### Step 4: Install plugins

Choose a profile or pick individual plugins.

**Academic Python/R developer (recommended):**
```
/plugin install denubis-plan-and-execute@denubis-plugins
/plugin install denubis-basic-agents@denubis-plugins
/plugin install denubis-research-agents@denubis-plugins
/plugin install denubis-extending-claude@denubis-plugins
/plugin install denubis-git-commit@denubis-plugins
/plugin install denubis-hook-skill-reinforcement@denubis-plugins
/plugin install denubis-hook-shortcut-detection@denubis-plugins
/plugin install denubis-hook-claudemd-reminder@denubis-plugins
```

**Add infrastructure hooks (Linux/macOS only):**
```
/plugin install denubis-hook-pretooluse-dispatcher@denubis-plugins
/plugin install denubis-hook-rtk-rewrite@denubis-plugins
/plugin install denubis-hook-gh-fork-guard@denubis-plugins
/plugin install denubis-hook-branch-bg@denubis-plugins
```

Or install the getting-started guide first and use `/setup` to verify:
```
/plugin install denubis-00-getting-started@denubis-plugins
```

### Step 5: Verify

Run `/setup` (from the getting-started plugin) to check that plugins are enabled, versions match, and hooks are configured.

## Windows Setup (Git Bash)

Claude Code on Windows uses Git Bash internally for all shell commands. You can launch `claude` from any terminal — PowerShell, CMD, Git Bash, or Windows Terminal.

### Recommended terminal: Windows Terminal

[Windows Terminal](https://aka.ms/terminal) is free, built into Windows 11, and available from the Microsoft Store on Windows 10. It provides:
- Tabs and split panes
- Proper Unicode and colour support for Claude Code's output
- OSC escape sequence support
- Multiple shell profiles (PowerShell, CMD, Git Bash) in one window

**Add a Git Bash profile** to Windows Terminal via Settings > Add a new profile:
- Command line: `C:\Program Files\Git\bin\bash.exe --login -i`
- Starting directory: `%USERPROFILE%`
- Name: `Git Bash`

This gives you Git Bash inside Windows Terminal — the best of both worlds.

### If Claude Code can't find Git Bash

Add to your Claude Code `settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"
  }
}
```

### Line endings

Git for Windows defaults to converting line endings (`core.autocrlf=true`). This can break hook scripts with `bad interpreter` errors. Check your setting:

```bash
git config --global core.autocrlf
```

If it returns `true`, you have two options:

1. **Per-repo override** (safer): the denubis-plugins repo includes a `.gitattributes` that forces `*.sh` files to LF. No action needed if you clone after this is set.
2. **Global change**: `git config --global core.autocrlf input` — converts CRLF to LF on commit but doesn't convert on checkout.

### What works on Windows

| Category | Status |
|----------|--------|
| All skills and agents (plan-and-execute, basic-agents, research-agents, etc.) | Works |
| Python-based hooks (shortcut-detection, claudemd-reminder, code-quality-guard) | Works (needs `uv`) |
| Trivial bash hooks (skill-reinforcement, session-start) | Works via Git Bash |
| Bash dispatcher + RTK rewrite + fork guard | **Skip** — heavy bash, Unix paths |
| Branch background colour (OSC 11) | **Skip** — limited terminal support |

### Alternative terminals

If you want more than Windows Terminal:

- **[WezTerm](https://wezterm.org/)** — cross-platform, GPU-accelerated, Lua-configurable, good OSC support. Would enable the branch-bg plugin.
- **[Alacritty](https://alacritty.org/)** — fast, minimal, TOML-configured. No tabs (pair with tmux or a multiplexer).
- **[Tabby](https://tabby.sh/)** — Electron-based, built-in SSH, split panes, plugin ecosystem.

For most users, **Windows Terminal with a Git Bash profile** is the simplest and best-supported option.

## Repository Structure

```
denubis-plugins/
+-- .claude-plugin/
|   +-- marketplace.json
+-- plugins/
|   +-- denubis-00-getting-started/
|   +-- denubis-plan-and-execute/
|   +-- denubis-basic-agents/
|   +-- denubis-research-agents/
|   +-- denubis-extending-claude/
|   +-- denubis-git-commit/
|   +-- denubis-hook-skill-reinforcement/
|   +-- denubis-hook-shortcut-detection/
|   +-- denubis-hook-claudemd-reminder/
|   +-- denubis-hook-pretooluse-dispatcher/
|   +-- denubis-hook-rtk-rewrite/
|   +-- denubis-hook-gh-fork-guard/
|   +-- denubis-hook-branch-bg/
+-- CHANGELOG.md
+-- README.md
```

## Removed from Upstream

These plugins were removed as not relevant to Python/R/SQL/LaTeX workflow:
- `ed3d-house-style` - TypeScript/React focused
- `ed3d-playwright` - JavaScript E2E testing

## Attribution

Derived from [`ed3dai/ed3d-plugins`](https://github.com/ed3dai/ed3d-plugins) by Ed Ropple, which itself derives from [`obra/superpowers`](https://github.com/obra/superpowers) by Jesse Vincent.

## License

Original [obra/superpowers](https://github.com/obra/superpowers) code is MIT License, copyright Jesse Vincent.

All other content is [CC-BY-SA-4.0](http://creativecommons.org/licenses/by-sa/4.0/).
