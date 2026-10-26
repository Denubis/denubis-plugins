# ADR 0042 — No durable record cites a gitignored object; the check for that, and proper note-taking, belong to the commit skill and run in every repository

**Status:** Accepted (2026-10-24). Extends `denubis-git-commit:commit`. Applies ADR 0008
(open questions only) and ADR 0041 (nothing durable cites the exchange directory).

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 1732, `user` record `65dd7be6-0e20-4c18-891c-f95d697b45a5` (2026-10-24T00:38:53Z,
  2026-10-24 11:38 Australia/Sydney), interrupting: "and another issue is that stateful
  shit keeps leaking into documents that shouldn't have stateful shit"
- Line 1940, `user` record `f7b4c6f4-c055-4096-9c40-7ce7c207cad6` (2026-10-24T02:11:31Z):
  "um, sorry, say aghain? Yes, no ADR can cite a gitignored object. Is this not possible
  to hae a linter on? Also, is it possible to have a global quality check before commit,
  since uh... things tend to get bad"
- Line 1966, `user` record `149010f7-2d08-4aa9-8ab9-2b0aba9fd9c9` (2026-10-24T02:15:06Z),
  answering a proposal to add the citation check as a test in this repository and to
  ratchet this repository's lint gate: "except that we need this to be a tool, since
  multiple repos will need it and we will adjust the commit skill. No, not repo, global,
  fuckit, just make it part of the commit skill. because also, note taking properly
  should be part of the commit skill"

```sh
sed -n '1732p;1940p;1966p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

## Context

Durable records in this repository (ADRs, project notes, architecture pages) had acquired
citations into the prompt-exchange directory, which is gitignored by ruling (2026-07-21) and
whose paths "should have nothing depending on them" (2026-10-22, both cited in ADR 0041),
and had acquired transitional wording ("until the migration lands", "still to be ruled",
"to be proven in P0") that describes a moment rather than a decision. Both defects recur
across Brian's repositories, not only here, so a test in one repository's suite would not
catch them elsewhere. The commit skill is the one procedure every repository's commit
already passes through, and it already runs the repository's configured gates.

## Decision

1. **No durable record cites a gitignored object.** A tracked document under a project's
   decision register, notes, or architecture pages may not reference a path that is
   gitignored, lies under a worktree directory, or does not exist in the checkout. The
   artefact is landed as a document and cited there, or the transcript record is cited.
2. **The check is a tool shipped by the commit plugin**, not a per-repository test. It
   runs from the commit skill in any repository, over the tracked documents the commit
   touches and the registers they live in, and a hit blocks the commit. It has no
   baseline allowlist.
3. **Note-taking is part of committing.** Before recording a commit the skill confirms
   that rulings made in the work are in the decision register with their original-record
   resolvers, that the open-questions file holds open questions only, that answered
   tickets have left it for a decision or a documentation reference, and that decision
   records carry no transitional state. Transitional wording is listed for the committer
   to justify or remove; it cannot be waved through silently.
4. **Quality gates stay the repository's.** The skill runs the gates the repository
   configures, as it already does; this ADR adds the global checks above to that step. It
   does not move ruff, ty or complexipy configuration into the plugin.

## Consequences

- `denubis-git-commit` gains a script (run through `uv run --script`, ADR 0038's launcher
  pattern) and the skill's "Inspect the real scope" step gains the citation and memory
  checks; the plugin version, marketplace entry and changelog move together.
- The tool needs the repository's register locations; it reads the project's
  `CLAUDE.md` finding aids and falls back to the default register paths from ADR 0005 and
  the plugins' conventions (`docs/architecture/decisions/`, the decisions folder of the
  project notes directory, and the notes directory itself).
- Existing citations into the prompt-exchange directory in this repository (ADR 0011, the
  messaging critical-review note) block the first commit that touches them, and are
  repaired by landing the cited design documents under `docs/design-plans/`.
- The commit skill's prose grows; its tests travel with it.

## Amendment (2026-10-26): the rule covers every tracked document under `docs/`

Decision 1 names the decision register, notes and architecture pages. Asked whether the
rule extends to design and implementation plans and the other pages under `docs/`, Brian
ruled that it covers all of them:

- Line 4384, `user` record `560f8a29-c556-4e87-9972-119ea827301e` (2026-10-26T00:20:20Z,
  2026-10-26 11:20 Australia/Sydney), on "Running the blocking rule over any staged design
  plan or implementation plan": "fine, since these are the things that cite."
- Line 4440, `user` record `8fb6da78-890f-455b-80a6-191dc77ec5b8` (2026-10-26T00:23:29Z),
  on whether notes and architecture pages are covered: "um, but yes, nothing in docs can
  cite gitignored shit."

No tracked document under `docs/` or in the notes directory cites a gitignored path, a
worktree path or the prompt-exchange directory; the check blocks on any of them wherever
it finds one. A citation of a path that merely does not exist stays blocking in the
decision register and is advisory elsewhere, since the ruling is about gitignored objects.

```sh
sed -n '4384p;4440p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```
