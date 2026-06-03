# denubis-plugins

Claude Code plugins for Python/SQL/LaTeX development workflows, customized for academic research.

Forked from [ed3d-plugins](https://github.com/ed3dai/ed3d-plugins) and adapted for:
- **Python 3.14+** with t-strings, deferred annotations, and modern idioms
- **Academic workflows** with proper citations, LaTeX conventions, and scholarly rigor
- **Quality over velocity** - Opus for implementation, halt-on-failure policy

## The Big Stick: `denubis-plan-and-execute`

An RPI (research-plan-implement) loop that avoids hallucination by separating design from implementation:

```
Rough Idea
    │
    ▼
/start-design-plan  ──────► Design Document (committed to git)
    │
    ▼
/start-implementation-plan ──► Implementation Plan (phase files)
    │
    ▼
/execute-implementation-plan ──► Working Code (reviewed & committed)
```

Key philosophy changes from upstream:
- **Opus for task implementation** (not Haiku) - fewer mistakes, fewer review cycles
- **Halt on non-obvious failures** - don't grind for 30 minutes working around problems
- **Block on ALL severities** - quality over velocity

**Customization:** Create `.ed3d/design-plan-guidance.md` and `.ed3d/implementation-plan-guidance.md` in your project to provide project-specific constraints, terminology, and standards. Run `/how-to-customize` for details.

## Plugin Catalogue

### Core — install these first

These are the foundation. Other plugins depend on them.

| Plugin | What it does |
|--------|-------------|
| **`denubis-plan-and-execute`** | Three-phase workflow: design → plan → execute. The main event. |
| **`denubis-basic-agents`** | Generic agents (haiku/sonnet/opus) plus `python-developer` and `academic-researcher`. Other plugins expect this. |
| **`denubis-research-agents`** | Codebase investigation and internet research agents. Other plugins expect this. |

### Recommended — quality of life

These make Claude Code noticeably better to work with.

| Plugin | What it does |
|--------|-------------|
| **`denubis-hook-skill-reinforcement`** | Reminds Claude to actually use its skills (you'd be surprised how often it forgets). |
| **`denubis-hook-shortcut-detection`** | E-STOP when Claude tries to take shortcuts — blocks and asks before proceeding. |
| **`denubis-extending-claude`** | Meta-skills for writing plugins, agents, skills, CLAUDE.md maintenance, and syncing with upstream. |
| **`denubis-git-commit`** | `/commit` as a proper skill with multi-commit support. |
| **`denubis-hook-claudemd-reminder`** | Reminds Claude to update CLAUDE.md before committing when things have changed. |

### Infrastructure hooks — Linux/macOS only

These bash-heavy hooks do not work on Windows (even with Git Bash). Skip them on Windows.

| Plugin | What it does | Requires |
|--------|-------------|----------|
| **`denubis-hook-pretooluse-dispatcher`** | Dispatcher that auto-discovers and runs PreToolUse:Bash hooks from plugins. | bash, Unix paths |
| **`denubis-hook-gh-fork-guard`** | Blocks `gh` CLI commands targeting repos you don't own. | dispatcher, `gh` |

### Terminal-specific

| Plugin | What it does | Requires |
|--------|-------------|----------|
| **`denubis-hook-branch-bg`** | Colours your terminal background by repo+branch. | OSC 11 terminal (Ghostty, iTerm2) |

### Onboarding

| Plugin | What it does |
|--------|-------------|
| **`denubis-00-getting-started`** | This guide. Run `/getting-started` or `/setup`. Can disable after setup. |

### Domain Agents

**`python-developer`** (Sonnet) - Python 3.14+ with:
- T-strings for SQL/HTML/shell (security-sensitive strings)
- Deferred annotations (no quotes for forward references)
- Bracketless exception handling
- `concurrent.interpreters` for CPU-bound parallelism

**`academic-researcher`** (Opus) - Academic rigor with:
- Proper citations and source attribution
- LaTeX conventions (environments, BibTeX)
- Scholarly argument structure

### Transcript Archiving

Transcript archiving is provided by the separate [`transcript-archive`](https://github.com/Denubis/claude-code-research-transcript-hook) plugin. Install it as a marketplace plugin for the `/transcript` command, bulk archival, status reporting, and more.

## Prerequisites

| Tool | Required for | Install |
|------|-------------|---------|
| **Node.js 18+** | Claude Code itself | [nodejs.org](https://nodejs.org/) |
| **Git** | Everything | [git-scm.com](https://git-scm.com/) |
| **Python 3.11+** | Hook scripts | [python.org](https://www.python.org/) |
| **uv** | Running Python hooks | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |

**Linux/macOS only:**

| Tool | Required for | Install |
|------|-------------|---------|
| **jq** | Dispatcher / gh-fork-guard hooks | Package manager (`apt`, `brew`) |

## Installation

### Add the marketplace

Inside Claude Code:
```
/plugin marketplace add https://github.com/Denubis/denubis-plugins.git
```

### Choose your plugins

**Recommended set** (works on all platforms including Windows/Git Bash):
```
/plugin install denubis-00-getting-started@denubis-plugins
/plugin install denubis-plan-and-execute@denubis-plugins
/plugin install denubis-basic-agents@denubis-plugins
/plugin install denubis-research-agents@denubis-plugins
/plugin install denubis-hook-skill-reinforcement@denubis-plugins
/plugin install denubis-hook-shortcut-detection@denubis-plugins
/plugin install denubis-extending-claude@denubis-plugins
/plugin install denubis-git-commit@denubis-plugins
/plugin install denubis-hook-claudemd-reminder@denubis-plugins
```

**Add infrastructure hooks** (Linux/macOS only):
```
/plugin install denubis-hook-pretooluse-dispatcher@denubis-plugins
/plugin install denubis-hook-gh-fork-guard@denubis-plugins
```

**Add terminal colouring** (Ghostty/iTerm2 only):
```
/plugin install denubis-hook-branch-bg@denubis-plugins
```

Then run `/setup` to verify everything is configured correctly.

## Windows Setup (Git Bash)

If you're on Windows using Git Bash (the default from [git-scm.com](https://git-scm.com/)), follow these extra steps.

### 1. Configure line endings

Git on Windows defaults to converting LF → CRLF on checkout. This breaks bash shebangs in hook scripts. Fix it **before** adding the marketplace:

```bash
git config --global core.autocrlf input
```

If you've already cloned or installed plugins, re-checkout to fix existing files:
```bash
# In the marketplace directory (~/.claude/plugins/marketplaces/denubis-plugins/)
git checkout -- .
```

### 2. Install uv

Most hook scripts run via `uv run python3`. Install uv for Windows:

```powershell
# In PowerShell (not Git Bash)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify it's on your Git Bash PATH:
```bash
uv --version
```

If not found, add uv's install directory to your Windows PATH (typically `%USERPROFILE%\.local\bin`).

### 3. Install the recommended plugin set

Install the **recommended set** listed above. **Do not install** the infrastructure hooks (`pretooluse-dispatcher`, `gh-fork-guard`) or `branch-bg` — they require Unix-only tooling.

### 4. Run setup

```
/setup
```

The setup skill detects Windows and adjusts its checks accordingly.

### Known limitations on Windows

- **No fork guard** — The `gh` CLI guard depends on the dispatcher. Be careful with `gh` commands on repos you don't own.
- **No terminal background colouring** — OSC 11 support varies across Windows terminals.
- **Hook performance** — Some users report [hook-related hangs on Windows](https://github.com/anthropics/claude-code/issues/34457). If Claude Code becomes sluggish, disable hooks one at a time to isolate the problem.

## Forking

To create your own variant:

1. Fork this repo on GitHub
2. Edit plugins to suit your workflow (change agent models, add skills, remove what you don't need)
3. Update `.claude-plugin/marketplace.json` with your name and repo URL
4. Install your fork: `/plugin marketplace add https://github.com/YOUR-USER/YOUR-FORK.git`

## Repository Structure

```
denubis-plugins/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── denubis-00-getting-started/
│   ├── denubis-plan-and-execute/
│   ├── denubis-basic-agents/
│   ├── denubis-research-agents/
│   ├── denubis-extending-claude/
│   ├── denubis-git-commit/
│   ├── denubis-hook-skill-reinforcement/
│   ├── denubis-hook-shortcut-detection/
│   ├── denubis-hook-claudemd-reminder/
│   ├── denubis-hook-pretooluse-dispatcher/
│   ├── denubis-hook-gh-fork-guard/
│   └── denubis-hook-branch-bg/
├── CHANGELOG.md
└── README.md
```

## Removed from Upstream

These plugins were removed as not relevant to Python/SQL/LaTeX workflow:
- `ed3d-house-style` - TypeScript/React focused
- `ed3d-playwright` - JavaScript E2E testing

## Attribution

Derived from [`ed3dai/ed3d-plugins`](https://github.com/ed3dai/ed3d-plugins) by Ed Ropple, which itself derives from [`obra/superpowers`](https://github.com/obra/superpowers) by Jesse Vincent.

## License

Original [obra/superpowers](https://github.com/obra/superpowers) code is MIT License, copyright Jesse Vincent.

All other content is [CC-BY-SA-4.0](http://creativecommons.org/licenses/by-sa/4.0/).
