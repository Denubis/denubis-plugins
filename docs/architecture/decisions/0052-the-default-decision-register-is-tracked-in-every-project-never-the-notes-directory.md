# ADR 0052 — The default decision register is tracked in the repository in every project, never the notes directory

**Status:** Accepted (2026-11-06). Amends the fourth Decision bullet of ADR 0005. Carries
ADR 0043 beyond this repository. ADR 0044 stands: the ticket file is not a register.

## Authority evidence

Original human message in session `cb745005-ae08-49f1-8b3c-5b7d04a3657b`
(`/home/brian/.claude/projects/-home-brian-llm-QuestForForge/cb745005-ae08-49f1-8b3c-5b7d04a3657b.jsonl`;
the session ran from the QuestForForge directory, so its transcript sits under that
project's folder):

- Line 662, `user` record `810f32ed-686b-440f-a189-8a566eff70d9` (2026-11-06T03:39:45Z,
  2026-11-06 14:39 Australia/Sydney), answering the ticket quoted under Context after the
  dispatcher had said ADR 0043 did not settle it for other projects: "no, .notes shouldn't
  have anything durable that other instances will need"

```sh
sed -n '662p' /home/brian/.claude/projects/-home-brian-llm-QuestForForge/cb745005-ae08-49f1-8b3c-5b7d04a3657b.jsonl
```

The ruling the ticket asked about is line 1322, `user` record
`67512a84-9c30-40ab-9a7d-8d7ac59bacac` (2026-10-25T02:25:58Z) of session
`e159b867-7a1e-4e2a-a524-058f6b7e72b6`: "ADRs should be in docs/ because they need to be
carried with the repo".

```sh
sed -n '1322p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl
```

## Context

On 2026-10-25 the five decision records this repository kept in its notes directory moved
into this register; they landed as ADRs 0047 to 0051. The agent doing that work filed a
ticket, because Brian's global gitignore ignores the notes directory in every repository,
so a register there is never carried with any clone, yet ADR 0005 made that directory the
default register for a project that has none. The ticket asked:

> Should that default move to a tracked location for every project, or does your ruling
> cover only this repository?

ADR 0043 had since ruled that the notes directory holds nothing durable that other
machines rely on, but recorded it as a decision about this repository's register.

## Decision

1. In every project, decision records live in a register tracked in the repository. The
   notes directory is never a project's default register.
2. A project that already keeps a tracked register keeps it. Rulings found only in a
   project's notes directory move into a tracked register, as ADRs 0047 to 0051 did here.
3. The open-questions ticket file stays in the notes directory under ADR 0044. A question
   is situational; its answer is the durable thing, and the answer goes to the register.
4. This ruling does not name the tracked path that becomes the default for a project with
   no register. The release that amends the owners below brings that choice to Brian.

## Consequences

- ADR 0005's fourth Decision bullet is superseded by decision 1.
- These owners name the notes-directory default and must change in a plugin release:
  `plugins/denubis-project-notes/skills/recording-project-notes/SKILL.md` (Open questions
  and decisions), `plugins/denubis-project-notes/skills/scanning-project-notes/SKILL.md`
  (section 6), and `plugins/denubis-external-agents/skills/supervising-codex/SKILL.md`.
- Brian's global Claude instructions file, outside this repository, must agree with
  decision 1 on the register and with ADR 0044 on the ticket file.
- The commit skill's checker lists a notes-directory register among the registers it
  reads. This decision does not rule on that list.
