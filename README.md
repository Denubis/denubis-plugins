# denubis-plugins

A shared source repository for customized Claude Code, Codex, and Antigravity CLI
plugins. Provider-neutral skills live once under `plugins/<name>/skills/`; provider
manifests, hook registrations, invocation metadata, commands, and agent adapters express
only the provider-specific transport.

The repository is forked from [ed3d-plugins](https://github.com/ed3dai/ed3d-plugins).

## Core workflow

`denubis-plan-and-execute` routes non-trivial design, implementation, debugging, review,
verification, human acceptance, and Git integration work to the procedure that owns the
next consequential decision.

An approved implementation plan authorizes private feature-branch checkpoints. Those may
be frequent. Fix rounds and superseded checkpoints remain provisional. After all outcomes
are assembled, the agent completes mechanical checks, independent sanity checks,
documentation reconciliation, and diff/status inspection. Human UAT then touches an
irreducible implication of the finished behavior. Only explicit UAT acceptance authorizes
folding provisional history into coherent outcome commits. Push, publication, deployment,
and inherited-history rewriting remain separate authorities.

There is no phase or commit-count quota. A coherent outcome is an independently
understandable, usable or verifiable change with its consumer, failure path, tests, and
operator or user documentation where those are real parts of the behavior.

## Provider support

All 58 skills in the 11 active skill-bearing Claude plugins are exposed from the same
`SKILL.md` trees to Claude Code, Codex, and Antigravity. Provider manifests and invocation
metadata are adapters; they do not copy the procedures.

| Plugin | Shared behavior |
|---|---|
| `denubis-plan-and-execute` | Design through implementation, verification, UAT, and Git lifecycle |
| `denubis-00-getting-started` | Package-install safety policy and onboarding |
| `denubis-basic-agents` | Provider-native delegation by functional role |
| `denubis-research-agents` | Codebase, internet, combined, remote-code, and academic research routing |
| `denubis-extending-claude` | Claude plugin, agent, skill, directive, and project-context maintenance from any host |
| `denubis-academic` | Academic revision, manuscript review, and Zotero-backed source work |
| `denubis-git-commit` | Intentional local commits at authorized boundaries |
| `denubis-crash-recovery` | Claude session-state triage callable from any host |
| `denubis-external-agents` | Provenance-bounded Codex and Fable consultation and supervision |
| `denubis-project-notes` | Project-owned notes and relevant prior-chat retrieval |
| `denubis-token-estimator` | Reproducible Claude Code and Codex usage measures |

Claude and Codex additionally share native transports for the branch-background hook,
the concrete code-quality guard, and the GitHub fork guard. Claude alone installs the
PreToolUse dispatcher because it compensates for Claude's hook aggregation; Codex
aggregates those hooks natively. Antigravity validates and installs all 11 skill-bearing
plugins and converts its supported command and agent surfaces. Hook-only plugins are not
claimed for Antigravity: its current documented hook interface does not expose an
equivalent blocking pre-tool contract for the two guards.

The provider boundaries and runtime evidence are recorded in the
[Codex compatibility matrix](docs/audits/2026-08-16-codex-plugin-compatibility-matrix.md).

## Install for Codex CLI

Codex reads the repository marketplace at `.agents/plugins/marketplace.json`. From a local
checkout:

```bash
codex plugin marketplace add /absolute/path/to/denubis-plugins
codex plugin add denubis-00-getting-started@denubis-plugins
codex plugin add denubis-plan-and-execute@denubis-plugins
codex plugin add denubis-basic-agents@denubis-plugins
codex plugin add denubis-research-agents@denubis-plugins
codex plugin add denubis-extending-claude@denubis-plugins
codex plugin add denubis-academic@denubis-plugins
codex plugin add denubis-git-commit@denubis-plugins
codex plugin add denubis-crash-recovery@denubis-plugins
codex plugin add denubis-external-agents@denubis-plugins
codex plugin add denubis-project-notes@denubis-plugins
codex plugin add denubis-token-estimator@denubis-plugins
codex plugin add denubis-hook-code-quality-guard@denubis-plugins
codex plugin add denubis-hook-gh-fork-guard@denubis-plugins
codex plugin add denubis-hook-branch-bg@denubis-plugins
codex plugin list --marketplace denubis-plugins --available --json
```

`denubis-hook-branch-bg` is useful only in a terminal that supports OSC 11 and on a system
with `/proc`. Codex applies its normal hook-trust boundary. Start the CLI with `codex`,
inspect `/hooks`, and trust the installed hook only after its source and command are the
ones you intend.

Per-skill `agents/openai.yaml` files provide human-readable discovery metadata. Commit,
pull-request creation, local main merges, upstream synchronization, crash triage, and
external-agent operations are explicit-only; ordinary planning, coding, review, and
research procedures may be selected when the task matches.

## Install for Claude Code

Inside Claude Code, add the marketplace:

```text
/plugin marketplace add https://github.com/Denubis/denubis-plugins.git
```

Install only the components you need. A provider-neutral working set is:

```text
/plugin install denubis-plan-and-execute@denubis-plugins
/plugin install denubis-academic@denubis-plugins
/plugin install denubis-git-commit@denubis-plugins
/plugin install denubis-project-notes@denubis-plugins
/plugin install denubis-token-estimator@denubis-plugins
```

Claude-specific optional components remain in `.claude-plugin/marketplace.json`. The
PreToolUse dispatcher and its fork guard require Bash, `jq`, Unix paths, and a separate
safety review of the guard's actual coverage. The branch-background hook additionally
requires an OSC 11 terminal and `/proc`.

If an older installation reports `denubis-bib` or still has
`denubis-bibliography`, follow the
[academic setup and migration runbook](plugins/denubis-academic/skills/using-bibliography/references/setup-and-migration.md).

## Install for Antigravity CLI

All 11 skill-bearing bundles carry native `plugin.json` manifests beside their existing
shared skill trees. Validate and install them with:

```bash
scripts/install_antigravity_plugins.sh
```

The installer validates every bundle before installing any of them. Start a new `agy`
session after installation, then use `agy plugin list` to inspect the imported set.
Supported agents and commands are converted by Antigravity's validator. Codex metadata,
Claude hook registrations, and unsupported hook bundles are skipped rather than copied
into a parallel repository.

## Requirements

- Git for repository and worktree operations.
- Python 3.9+ for Claude hook scripts.
- Python 3.14+ and `uv` for the academic bibliography helpers and token-estimator scripts.
- Zotero with Better BibTeX for bibliography resolution and rendering.
- `gh` only for requested pull-request operations.

Project-local configuration, supported language versions, test runners, cache locations,
database conventions, and architecture ownership come from the project being changed.
The plugins do not replace those decisions with universal defaults.

## Repository layout

```text
denubis-plugins/
├── .agents/plugins/marketplace.json       # Codex catalogue
├── .claude-plugin/marketplace.json        # Claude Code catalogue
├── plugins/
│   └── <plugin>/
│       ├── plugin.json                    # when Antigravity-compatible
│       ├── .codex-plugin/plugin.json      # when Codex-compatible
│       ├── .claude-plugin/plugin.json     # Claude Code package
│       ├── skills/<skill>/SKILL.md        # shared semantic procedure
│       ├── skills/<skill>/agents/openai.yaml
│       └── hooks/                         # provider registrations + shared scripts
├── docs/architecture/
├── docs/design-plans/
└── tests/
```

The [architecture index](docs/architecture/README.md) describes behavior by system
boundary before subsidiary plugin packaging views. Current design and compatibility
audits explain decisions; living skills and architecture describe current behavior.

## Attribution and license

Derived from [`ed3dai/ed3d-plugins`](https://github.com/ed3dai/ed3d-plugins) by Ed Ropple,
which derives from [`obra/superpowers`](https://github.com/obra/superpowers) by Jesse
Vincent. Original Superpowers material is MIT-licensed. Other content is
[CC-BY-SA-4.0](http://creativecommons.org/licenses/by-sa/4.0/).
