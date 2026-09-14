# ADR 0005 — Questions are durable tickets in `.notes`, and rulings go to a register there

**Status:** Accepted (2026-09-14)

## Authority evidence

- Queueing ruling (2026-08-09):
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/8817410d-fd26-45b2-9cda-e70122d94955.jsonl:310`
  Exact resolver: `cc-search-chats context 679e51c6-3460-4d1c-bc25-1ccaffff87be --json`
- Durable-file and pause ruling (2026-09-14):
  `/home/brian/.claude/projects/-home-brian-llm-approxup/f04f08aa-e5d9-4f16-9e68-2d86db190d47.jsonl:94`
  Exact resolver: `cc-search-chats context 08b7e82f-7ee7-452f-a45b-5c38ead74e6b --json`
- Create-without-approval and ADR-in-`.notes` ruling (2026-09-14):
  `/home/brian/.claude/projects/-home-brian-llm-approxup/f04f08aa-e5d9-4f16-9e68-2d86db190d47.jsonl:179`
  Exact resolver: `cc-search-chats context 9d3ff63c-4059-469b-a23d-3d8c69836a49 --json`

The human messages supply the rulings; this ADR does not reproduce them.

## Context

Questions raised by a subagent or an external Codex pane were surfaced in conversation and
then lost: scrolled past, compacted away, or treated as settled once the reminder stopped.
The 2026-08-09 cross-model-coordination dossier recorded as a human constraint that
timeout or context loss is not settlement and that agents must rediscover open tickets
from a durable queue. No skill implemented that queue. Separately, `supervising-codex`
required an ADR register but let each project choose its location, so new projects had no
default and rulings made in a pane stayed oral.

## Decision

- A question for the human is a ticket appended to
  `<main-repository-root>/.notes/project_open-questions.md`, resolved through Git's common
  directory so worktrees share it. Any agent, including a dispatched subagent, may pause
  and file one at any point; pausing to push back is always welcome.
- A ticket closes only when the human answers it. Compaction, `/clear`, scroll, elapsed
  time, or repetition never closes one. `scanning-project-notes` reads open tickets at
  every task entry.
- Creating the ticket file and creating a decision record need no prior approval. Every
  other `.notes` write keeps the proposal gate.
- The default decision register is `<main-repository-root>/.notes/decisions/` with a
  `README.md` index. A project with an existing register keeps it. This repository keeps
  `docs/architecture/decisions/`.
- An indifferent human answer is not delegation; the agent thinks the implications through
  with the human before recording.
- `.notes/` is durable passive memory, never transport. Prompt exchange, mail, and other
  operational state live in their own gitignored directories.

## Consequences

- `recording-project-notes` owns the ticket and register formats;
  `scanning-project-notes` owns rediscovery; `supervising-codex` requires both records and
  creates the defaults.
- The global `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` carry the same rule in their
  Delegation and Open Questions sections, synced through `claude-settings-sync`.
- A repository gains a `.notes/` directory the first time an agent has a question, even if
  it had none before.
- Two register conventions now coexist across repositories; the default applies only where
  none existed.
