# denubis-plan-and-execute — Context

## Boundary

The plugin owns provider-neutral methods for design, outcome planning, implementation,
verification, human acceptance, architecture maintenance, and Git lifecycle. Claude
metadata, agent definitions, commands, a live-marker hook, wrapper, and statusline adapt
those methods to Claude Code. Codex metadata controls discovery and consequential
invocation without duplicating the method.

    Human
      └─ intent, decisions, UAT, integration authority → Plan-and-execute methods
           ├─ designs, plans, code, tests, private history ↔ Project repository
           ├─ bounded brief → Optional agent role → diff or evidence leads
           ├─ loaded by Claude Code host
           │    └─ SessionStart transcript identity → Live-marker adapter
           │         └─ owned marker update → Crash-recovery contract
           └─ loaded by Codex host through discovery and invocation metadata

## Semantic components

- Workflow entry routes consequential work to the procedure that owns its next decision.
- Design resolves intent and material trade-offs into an accepted project artifact.
- Implementation planning groups work by independently understandable, usable or
  verifiable outcomes rather than chronological phases.
- Execution uses project-native TDD or positive operational probes, creates recoverable
  private checkpoints, and assembles the complete surface. The top-level executor owns
  this ordinary lifecycle directly and loads another procedure only for a concrete
  unresolved condition.
- Verification completes mechanical gates, independent sanity checks, boundary
  reconciliation, documentation, and diff/status inspection before human UAT.
- UAT asks the human to interact with an irreducible implication of the finished surface.
- Post-UAT normalization folds fixes and superseded checkpoints into coherent outcomes
  while preserving the accepted tree.
- Architecture maintenance maps current implementation and updates its existing semantic
  owner directly; there is no second architecture-writer skill or compulsory template set.

The coding skills select project-specific language, testing, and database decisions.
Python versions and tools, PostgreSQL keys and transaction conventions, mocking strategy,
and Hypothesis settings come from the project and current consumers rather than universal
plugin defaults. They are specialist procedures, not a mandatory stack beneath every
plan execution.

## Runtime adapters

Claude Code discovers the plugin through
plugins/denubis-plan-and-execute/.claude-plugin/plugin.json. Agent files define only their
provider role, edit authority, and evidence return. Commands are thin entry points. Codex
discovers the same skill tree through `.codex-plugin/plugin.json`; each skill's
`agents/openai.yaml` supplies display and invocation policy only.

hooks/update-live-marker.py handles one Claude SessionStart boundary: when the wrapper
supplies an owned CR_LIVE_FILE, it atomically updates the transcript identity consumed by
crash recovery. It does not emit workflow guidance or establish skill compliance. Textual
Write/Edit quality detectors were removed because matching chosen source phrases does not
establish behavior and their tool payload was provider-specific.

The Claude registration is `hooks/claude-hooks.json`. The Codex registration is an
explicit empty `hooks/codex-hooks.json`, so Codex cannot load the Claude crash-live marker
through default hook discovery. The wrapper and statusline are observed runtime utilities,
not execution gates. On each Claude statusline render, the statusline persists the
per-window `timestamp|used_pct|resets_at` quota snapshot under
`$XDG_CACHE_HOME/claude-statusline/quota-*`; that file is an external contract consumed by
the tmux-codex-quota Byobu cell.

## Evidence and failure boundaries

- Project files, Git state, tests, builds, and runtime observations establish technical
  results; task labels, commits, and model verdicts do not.
- An approved execution request permits private checkpoints only on its feature branch.
  Push, publication, deployment, inherited-history rewriting, and destructive cleanup are
  separate actions.
- Human UAT happens after complete mechanical and sanity evidence. A failed observation
  returns to implementation and invalidates affected evidence.
- Investigation, tracking, secondary checks, and progress reporting have a current
  consumer. A supplied one-outcome plan is not copied into another tracker, and routine
  execution does not search historical chats or narrate each command transition.
- An optional agent receives an exact brief and returns a diff or cited leads. The main
  session verifies them before continuing.
- The live-marker adapter and crash-recovery consumer can drift independently; their
  cross-plugin file contract requires direct runtime tests.

## Sources

- Provider-neutral skills: plugins/denubis-plan-and-execute/skills/
- Claude roles and transport: plugins/denubis-plan-and-execute/agents/,
  plugins/denubis-plan-and-execute/commands/,
  plugins/denubis-plan-and-execute/hooks/claude-hooks.json
- Codex transport: plugins/denubis-plan-and-execute/.codex-plugin/plugin.json,
  plugins/denubis-plan-and-execute/hooks/codex-hooks.json,
  plugins/denubis-plan-and-execute/skills/*/agents/openai.yaml
- Wrapper and statusline: plugins/denubis-plan-and-execute/scripts/
- [Cross-cutting constraints](../../constraints.md)
- [Crash recovery](../denubis-crash-recovery/0-context.md)
