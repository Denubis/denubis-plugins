# ADR 0041 — The prompt exchange is the Record, not a gitignored directory; telemetry comes from hooks; AskUserQuestion is denied and a worker's question lives in open-questions until a human answer moves it out

**Status:** Accepted (2026-10-24). Resolves design decisions D2, D4 and D5 of the stage-1
Codex-supervises-Claude design (Sol's draft against
`docs/design-plans/2026-10-24-claude-supervision-spec.md`). Applies ADR 0008 (the
open-questions file holds open questions only) and ADR 0039 (one Postgres-backed service).
Amends the `supervising-codex` skill's contract for the untracked prompt-exchange directory.

## Authority evidence

Original human messages. Session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 1639, `user` record `6d34e753-833d-40ae-bc32-ec750197270d` (2026-10-24T00:36:32Z,
  2026-10-24 11:36 Australia/Sydney), answering the three questions in turn: "d2 I'd
  prefer we just have this be postgres? It's so frustrating having things cite
  codex-prompts (go search chats), d4 yes and hooks as needed, d5 yeah, I hate the ask
  user question tool, it needs to go into open questions, then the supervisor needs to
  understand project context, search decisions and notes, and figure out if we've already
  answered it, and only then it stays in open questions. When answered it leaves open
  questions either into a decision or into some sort of useful documentation reference."

```sh
sed -n '1639p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

Prior rulings the "go search chats" instruction pointed at, found by one semantic search
of Brian's messages (`cc-search-chats search --semantic --role user`):

- 2026-07-21, `claude:5f52f866-35c4-4790-9374-d3fa12101194`, record
  `649007d2-718c-47c0-b937-e181e487ab43`: "I mean, codex-prompts are epheemeral. If we're
  doing some sort of audit report or whatever, that's a new document properly. There's a
  reason in-progres prompts are gitignored and it shall remain so"
- 2026-10-22, `claude:2d1da565-33eb-4f4e-aa15-bc8728dd5f72`, record
  `0690bfb9-59a8-4362-b7ff-4626a90c7a9d`: "well, codex prompts should have nothing...
  depending on them. and... worktree paths in ADRS and notes are unacceptable. We in fact
  have notes on this bullshit. Do better."

```sh
cc-search-chats context 649007d2-718c-47c0-b937-e181e487ab43 --json
cc-search-chats context 0690bfb9-59a8-4362-b7ff-4626a90c7a9d --json
```

The questions answered, as asked by the supervising session: D2 asked whether the new
mode should reuse the prompt-exchange directory or use a directory named `agent-prompts`;
D4 "Should first-release telemetry use verified hooks only, or add a composed
session-scoped statusline exporter?"; D5 "When a
Claude worker has a question for a human, should it be denied the native AskUserQuestion
tool and made to write the question as plain text and end its turn, so the question
becomes mail to the supervisor through the Record?" The D2 answer was given as a
preference with a question mark; the two prior rulings it cited make its consequence
clear, and this ADR records that consequence.

## Context

The `supervising-codex` skill exchanges prompts and deliverables through a gitignored
prompt-exchange directory. Durable records then cite those paths: on 2026-10-24 ADRs
0011, 0035, 0036, 0037 and 0039 and the messaging critical-review note all pointed into
that directory, which is ephemeral by ruling and absent from every other
checkout. ADR 0039 makes one Postgres-backed service the home of supervision events and
mail, so a prompt and its deliverable can be rows with stable identifiers instead.

Sol's design offered telemetry (context usage, model, effort) either from the worker's
own hooks or from a composed statusline exporter, and offered the question path either
as the native AskUserQuestion tool, whose dialog nobody outside the pane can answer, or
as a denied tool with plain-text questions.

## Decision

1. **The exchange is the Record.** A dispatch (prompt text, its rulings and context
   references, the intended worker) and its return (the deliverable or a reference to
   files the worker wrote, its manifest and digest, the worker's notes) are rows in the
   Record with stable identifiers. The worker reads its dispatch through the package's
   client in one call and writes its return the same way. Nothing durable cites a path
   under a gitignored exchange directory; a durable artefact that comes out of an exchange
   is landed as a proper document and cited there. Files a worker edits in a repository
   stay in that repository; the Record refers to them, it does not copy them.
2. **Telemetry comes from hooks.** Context usage, model and effort are whatever the
   worker's own hooks (SessionStart, PostModelSwitch, PreCompact, PostCompact, Stop) and
   its statusline payload report through the one call; a value no hook has reported is
   "unknown", never inferred. No statusline exporter is composed over the operator's
   statusline. Further hooks are added as a specific reading needs them.
3. **AskUserQuestion is denied** for spawned Claude workers (`--disallowed-tools
   AskUserQuestion`). A worker with a question for a human writes it as a ticket in
   the `project_open-questions` file in the notes directory, with its blocking
   consequence and evidence, and ends its turn.
4. **The supervisor triages the ticket before it reaches Brian.** It reads the project
   context, searches the decision register and the project notes, and when needed prior
   chats, for an existing human answer. An existing answer closes the ticket only after
   its original record, scope and supersession are verified, and is cited rather than
   restated. Only a question with no such answer stays open and is raised to Brian, one
   at a time.
5. **An answered question leaves the file.** Its destination is a decision record when
   the answer is a ruling, or a documentation reference (the architecture pages, a
   skill, a README) when the answer is a fact future work needs. Nothing else lives in
   the open-questions file (ADR 0008).

## Consequences

- The `supervising-codex` skill's prerequisite for an untracked prompt-exchange directory
  and its layout of `NN-<task>.md` files plus output and context subdirectories are
  replaced by dispatch and return rows; `--send PROMPT_FILE` becomes a send of a dispatch
  identifier. The skill's prose
  and the driver verbs change together.
- The Record schema (ADR 0026) gains dispatch and return tables alongside mail and
  supervision edges; the schema is the package's (ADR 0040).
- Existing citations into the prompt-exchange directory in ADRs and notes are defects
  under the 2026-10-22 ruling and are repaired by landing the cited artefact as a
  document or by citing the transcript record.
- A worker's question has one shape and one home; the supervisor's triage is the
  gate, and Brian sees only questions nobody has answered.
