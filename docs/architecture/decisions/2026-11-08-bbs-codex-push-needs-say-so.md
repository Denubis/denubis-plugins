# ADR 2026-11-08-bbs-codex-push-needs-say-so — Codex, like Claude, needs Brian's explicit say-so to push, merge into the main branch, or delete a branch

**Status:** Accepted (2026-11-08). Settles the push authority that ADR
2026-11-08-bbs-critiques-need-demonstrated-flaws item 9 left out.

## Authority evidence

Session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`),
2026-11-08 UTC:

- Line 6655, the supervisor's question through the question box (`assistant` record
  `6419b4fb-a34d-4c39-8d89-3bebefd290e6`, 02:53:04Z): "Should the Codex instructions file also
  say that pushing, merging into the main branch, or deleting a branch needs your explicit
  say-so?" Its context: `~/.claude/CLAUDE.md` has "Push, integration, and cleanup need
  authority"; `~/.codex/AGENTS.md` has no such rule.
- Line 6659, Brian (`user` record `9e4bba57-3fdf-4caa-8540-fd548235b31c`, 02:53:16Z), pasting the
  question and answering: "yes".

```sh
sed -n '6655p;6659p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

A fresh Sonnet checker found no earlier ruling. It found two related complaints of 2026-08-20,
after a Codex session pushed to a feature branch when Brian wanted main:
`ccchat:v1:codex:01a01eca-648f-7f71-8c4d-b2a6330d676a:id:msg_01a01ef6-2dc6-7310-b4e6-f11a8f9b9d0d`
("no, don't fucking push to a fucking branch, merge it") and
`ccchat:v1:codex:01a01eca-9a95-7511-8067-e6440fa8e763:id:msg_01a0218c-73e9-7120-9ca9-ee8864aeb014`
("why do you keep pushing feature branches?!").

## Decision

The Codex instructions file says that pushing, merging into the main branch, or deleting a branch
needs Brian's explicit say-so, as the Claude file does.
