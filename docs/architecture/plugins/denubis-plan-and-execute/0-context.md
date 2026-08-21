# denubis-plan-and-execute — Context

## Boundary

The plugin owns provider-neutral methods for design, outcome planning, implementation,
verification, human acceptance, architecture maintenance, and Git lifecycle. Claude
metadata, agent definitions, commands, a live-marker hook, wrapper, and statusline adapt
those methods to Claude Code. Codex metadata controls discovery and consequential
invocation without duplicating the method.

    Human
      └─ intent, decisions, UAT, integration authority → Plan-and-execute methods
           ├─ designs, plans, todo, worklog, code, tests, private history ↔ Project repository
           ├─ bounded brief → Optional agent role → diff or evidence leads
           ├─ loaded by Claude Code host
           │    └─ SessionStart transcript identity → Live-marker adapter
           │         └─ owned marker update → Crash-recovery contract
           └─ loaded by Codex host through discovery and invocation metadata

## Semantic components

- Workflow entry routes consequential work to the procedure that owns its next decision.
- Design resolves intent and material trade-offs into an accepted project artifact.
- Implementation planning groups work by independently understandable, usable or
  verifiable outcomes rather than chronological phases. Stable plan content, unresolved
  tasks, and completed work/evidence have separate durable files.
- Execution uses project-native TDD or positive operational probes, creates recoverable
  private checkpoints in task-owned isolation, and assembles the complete surface. Its
  workspace rubric requires a worktree for concurrent or overlapping work and human
  assent before beginning on the default branch. The top-level executor owns this
  ordinary lifecycle directly and loads another procedure only for a concrete unresolved
  condition.
- Verification completes mechanical gates, independent sanity checks, boundary
  reconciliation, documentation, and diff/status inspection before human UAT.
- UAT asks the human to interact with an irreducible implication of the finished surface.
- Post-UAT normalization folds fixes and superseded checkpoints into coherent outcomes
  while preserving the accepted tree. Selected delivery then integrates and optionally
  publishes the intended branch before removing only task-owned isolation.
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
Write/Edit warnings were removed from this workflow bundle because matching contextual
source phrases does not establish behavior. Two concrete Claude-only refusals now belong
to the standalone `denubis-hook-code-quality-guard` plugin.

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
- An approved execution request permits private checkpoints only on its task-owned branch.
  A skill/plugin `commit, marketplace, push` or `ship` request selects complete default-
  branch delivery after accepted UAT; it does not select the current feature branch.
  Other publication, deployment, inherited-history rewriting, and destructive cleanup
  remain separate actions.
- Human UAT happens after complete mechanical and sanity evidence. A failed observation
  returns to implementation and invalidates affected evidence.
- Investigation, tracking, secondary checks, and progress reporting have a current
  consumer. Pending work lives in `todo.md`; completed work and evidence live in
  `worklog.md`; stable outcomes remain in the plan. Resume text points to those owners
  rather than copying them. Routine execution does not search historical chats or narrate
  each command transition.
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
