# ADR 0005 — Questions are durable tickets in `.notes`, and rulings go to a register there

**Status:** Accepted (2026-09-14). Amended 2026-10-26: the default decision register moves
into the tracked docs tree (see the amendment below); the ticket file stays in the notes
directory (ADR 0044).

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
  the `project_open-questions.md` file in the main checkout's notes directory, resolved through Git's common
  directory so worktrees share it. Any agent, including a dispatched subagent, may pause
  and file one at any point; pausing to push back is always welcome.
- A ticket closes only when the human answers it. Compaction, `/clear`, scroll, elapsed
  time, or repetition never closes one. `scanning-project-notes` reads open tickets at
  every task entry.
- Creating the ticket file and creating a decision record need no prior approval. Every
  other `.notes` write keeps the proposal gate.
- The default decision register is the `decisions` directory in the main checkout's notes directory, with a
  `README.md` index. A project with an existing register keeps it. This repository keeps
  `docs/architecture/decisions/`.
- An indifferent human answer is not delegation; the agent thinks the implications through
  with the human before recording.
- The notes directory is durable passive memory, never transport. Prompt exchange, mail, and other
  operational state live in their own gitignored directories.

## Consequences

- `recording-project-notes` owns the ticket and register formats;
  `scanning-project-notes` owns rediscovery; `supervising-codex` requires both records and
  creates the defaults.
- The global `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` carry the same rule in their
  Delegation and Open Questions sections, synced through `claude-settings-sync`.
- A repository gains a notes directory the first time an agent has a question, even if
  it had none before.
- Two register conventions now coexist across repositories; the default applies only where
  none existed.

## Amendment (2026-10-26): the default decision register is a `decisions` directory under tracked `docs`

The ticket stays a note (ADR 0044), but a decision register is durable material that other
machines and sessions cite, so under ADR 0043 it does not live in the notes directory. Brian,
asked whether to repair the registers the 2026-10-26 survey found inside notes directories
across his repositories, ruled: "let's go fix those repos please. both telling and the 15."
(line 5997, `user` record `0f7e5856-cc69-40bd-843b-7d77a2450c2f`, 2026-10-26T05:25:17Z, in
session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`; "the 15" are the fifteen registers found under
a notes directory.)

- The default register for a project without one is a `decisions` directory directly under
  the main checkout's tracked `docs` directory, with a `README.md` index. The
  `docs/architecture/decisions/` form this repository uses and the one-file
  `adr-register.md` form inside such a directory remain accepted existing conventions.
- A register found inside a notes directory is moved into `docs/`, each record keeping its
  original-message resolvers, and the register index and project instructions repointed.
- The skills that create or read the default register follow this amendment in their next
  releases; until then the ADR governs.

```sh
sed -n '5997p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```
