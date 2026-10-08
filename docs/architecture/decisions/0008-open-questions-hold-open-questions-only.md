# ADR 0008 — The open-questions file holds open questions only

**Status:** Accepted (2026-10-08). Amends ADR 0005, which stands for everything it says
except "an answered ticket stays in the file as the record".

## Authority evidence

Original human messages:

- 2026-09-28, MELICA project, line 3018, record `41719b71-6b44-4091-8187-ee73f37efb42`
  of `/home/brian/.claude/projects/-media-brian-storage-people-Adela-melica--worktrees-98-markup-requirements/f9ff1c6c-4ac9-4901-a8ae-4506baf6f7f5.jsonl`:
  "*human* ADRs are moved. AI chatter that is no longer relevant is removed."
  The same session carries the earlier instruction "turn concluded properly human ruled
  open questions into ADRs properly so open questions doesn't become a second decision
  register", found only as a relayed quotation in subagent briefs
  (`cc-search-chats search "second decision register" --literal --all`); the line above
  is the original record this ADR rests on.
- 2026-10-08, this repository, line 98, record `14b58d35-082c-49d3-8d3c-495e8211cbb2`
  of `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/0d6c5c17-8b49-4d6b-a132-63beecccf129.jsonl`:
  "go look at me recently grumbling about open questions. That has just become a data
  dump and is not acceptable. It is for *open* questions, not *answered* questions.
  Those go wherever they need to go."

Exact raw-record resolver:

```sh
sed -n '3018p' /home/brian/.claude/projects/-media-brian-storage-people-Adela-melica--worktrees-98-markup-requirements/f9ff1c6c-4ac9-4901-a8ae-4506baf6f7f5.jsonl
sed -n '98p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/0d6c5c17-8b49-4d6b-a132-63beecccf129.jsonl
```

## Context

ADR 0005 made `.notes/project_open-questions.md` the durable queue and said an answered
ticket stays in the file as the record. In practice every answered ticket accumulated its
answer, the dispatcher's reading of the answer, follow-up measurements, and "state of the
fix" status paragraphs. This repository's own file reached five tickets, four of them
answered and released weeks ago, plus two status sections; the MELICA file needed a
subagent pass on 2026-09-28 to move 21 human-ruled tickets into decision records. The
file had become a second decision register that nobody could read for the open items.

## Decision

- The open-questions file holds tickets awaiting a human answer, and nothing else.
- When the human answers, the ruling goes into a decision record in the project's
  register, with the question it answered, the human's words verbatim, and a resolver to
  the original message. The ticket is then removed from the file.
- A ticket that no longer matters (the work it blocked is finished or abandoned, or it
  was an agent's one-off nobody will act on) is removed without a record.
- Progress notes, status summaries, measurements, and evidence that no open question
  needs do not go in the file.
- Everything else in ADR 0005 stands: who may file, that only the human closes a ticket,
  rediscovery at task entry, and the register locations.

## Consequences

- `recording-project-notes` owns the ticket lifecycle including the move-out; the global
  `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` Delegation and Open Questions sections
  carry the same rule; `supervising-codex` restates it for Codex's tickets.
- This repository's file is reduced to its open tickets; the rulings it held are now ADR
  0007 (session files) and ADR 0010 (the queued-question widget and `--cwd`).
- A reader of the file sees only what is waiting on them.
