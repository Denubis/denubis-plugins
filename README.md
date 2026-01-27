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

## Plugins

| Plugin | Description |
|--------|-------------|
| **`denubis-00-getting-started`** | Getting started guide. Run `/getting-started`. |
| **`denubis-plan-and-execute`** | Three-phase workflow: design → plan → execute. Slow and steady. |
| **`denubis-basic-agents`** | Generic agents (haiku/sonnet/opus) plus domain variants: `python-developer`, `academic-researcher` |
| **`denubis-research-agents`** | Codebase investigation and internet research agents |
| **`denubis-extending-claude`** | Meta-skills for plugins, agents, skills, CLAUDE.md maintenance, and `/transcript` archiving |
| **`denubis-hook-skill-reinforcement`** | UserPromptSubmit hook that reminds to activate relevant skills |
| **`denubis-hook-claudemd-reminder`** | PostToolUse hook that reminds to update CLAUDE.md before commits |

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

The `/transcript` command archives conversations with IDW2025 research metadata:

```
/transcript
```

Outputs:
- **SUMMARY.md** - Human-readable markdown summary
- `index.html` - Full HTML transcript
- `session.meta.json` - Structured metadata (Three Ps framework)

## Installation

### Add the marketplace
```bash
/plugin marketplace add https://github.com/Denubis/denubis-plugins.git
```

### Install plugins
```bash
/plugin install denubis-plan-and-execute@denubis-plugins
/plugin install denubis-basic-agents@denubis-plugins
/plugin install denubis-research-agents@denubis-plugins
/plugin install denubis-extending-claude@denubis-plugins
/plugin install denubis-hook-skill-reinforcement@denubis-plugins
/plugin install denubis-hook-claudemd-reminder@denubis-plugins
```

Or install the getting-started guide first:
```bash
/plugin install denubis-00-getting-started@denubis-plugins
```

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
│   ├── denubis-hook-skill-reinforcement/
│   └── denubis-hook-claudemd-reminder/
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
