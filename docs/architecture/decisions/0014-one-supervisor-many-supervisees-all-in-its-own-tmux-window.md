# ADR 0014 — One supervisor may drive many supervisees, and all of them sit in the supervisor's own tmux window

**Status:** Accepted (2026-10-09).

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 752, record `4aa3b952-78f7-4004-9efe-52ed5f6d5444` (2026-10-09T02:10:35Z),
  answering ticket M4 ("may a supervisor type into a pane in a different tmux window?"):
  "I... wouldn't mind if one supevisor could drive many sub-panes? But... we need a good
  way of managing things"
- Line 758, record `7b235438-2778-473c-85d8-223d9dbe00e0` (2026-10-09T02:12:34Z),
  answering the follow-up ("with many supervisees, where do their panes live? Same
  window, or anywhere?"):
  "same window. I don't want this spreading across multiple tmux windows. It would be
  impossible to track"

Exact raw-record resolver:

```sh
sed -n '752p;758p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

The current Codex supervisor drives only a pane in its own tmux window, and only when
exactly one Codex pane is there (`codex_supervisor.py`, same-window uniqueness rule).
Proposal 05 of the 2026-10-09 design asked whether a database-recorded pane binding plus
a liveness check could replace that rule and allow cross-window driving. Verifier 05
found the proposed Claude-side liveness check too weak to make that safe.

## Decision

- A supervisor may hold several supervisees at once. The set is recorded as supervision
  edges in the Record and shown on the human surface; the supervisor does not track it
  from memory.
- Every supervisee a supervisor drives is a pane in the supervisor's own tmux window.
  The design never drives a pane in another window.
- The same-window rule therefore stays, and its uniqueness clause changes: a window may
  hold several supervisee panes, so the pane for a given supervisee is resolved by its
  recorded binding and confirmed live, not by "the only Codex pane here".

## Consequences

- Pane resolution in functions 3 and 5 is: the Record's edge gives the pane id; the
  pane must be in the caller's window; its live identity must match the edge's session.
  Any failure refuses, naming both ids.
- The weak-liveness finding in verification 05 still has to be fixed for Claude
  supervisees, because two Claude panes in one window must be told apart by process,
  not by title.
- The "good way of managing things" Brian asks for is the surface's view of edges per
  window (function 7) and the Record's edge table (function 1); neither is built yet.
- Window geometry bounds the fan-out in practice; that is an operator limit, not a
  design one.
