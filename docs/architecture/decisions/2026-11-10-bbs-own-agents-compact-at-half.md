# ADR 2026-11-10-bbs-own-agents-compact-at-half — Subagents of this repository's own agent types compact at about half their context window

**Status:** Accepted (2026-11-10). Records a human ruling. It corrects the premise of
the question behind line 699 in ADR 2026-11-10-bbs-compact-nag-leaves-engine-threshold.

## Authority evidence

Claude Code session `d4590dde-909a-4cc7-a999-be56c975149c`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d4590dde-909a-4cc7-a999-be56c975149c.jsonl`.
The timestamp is UTC on 2026-11-10.

- Line 1643 (record `0eb270e9-830f-4393-abb3-7dd4cfe45deb`, a user message,
  00:53:57.618Z). It holds the question as the question zone put it, followed by
  Brian's answer. The context the question carried, then the question:

  > Your new compact-nag plugin puts a reminder into a session at 40% context use. The reminder tells the session to save its state (TODO list, worklog, decision proposals) and then say it is ready, so it can be compacted with a summary brief it writes itself. The plugin can compact the main session when it says it's ready, but it cannot compact a subagent. A subagent only compacts when Claude Code's own automatic compaction fires, close to its full context window. Earlier I told you the only way to change that was a global setting that would also affect the main session. That was wrong. Each agent definition file can carry its own compaction point, a token count between 100,000 and 1,000,000, that applies only to subagents of that type. Your plugins repository's agent files (general-purpose, deep-judgment, task-implementor, the reviewers and the others) could each be set to 500,000 tokens, half of a 1M window. Claude Code's built-in agent types can't be changed this way. This is documented, but I haven't seen it work yet. If you say yes, I'll add the setting to your agent files in a follow-up release. I'll also correct the decision record about the plugin's compaction threshold, which repeats my wrong claim. If you say no, subagents keep getting the reminder but still compact only near their full window. The main session is unaffected either way.
  >
  > Should subagents of your own agent types compact automatically at about half their context window?

  Brian, verbatim: "yes"

Exact raw resolver:

```sh
sed -n '1643p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d4590dde-909a-4cc7-a999-be56c975149c.jsonl
```

## Context

The `compact-nag` mod can compact the main session when it asks, but not a subagent. A
subagent compacts only when Claude Code's own automatic compaction fires. When the mod's
thresholds were ruled on, the question claimed that the only way to move that point was
the global `autoCompactWindow` setting, which applies to every loop. That was wrong.

- Documented, in build 2.1.321's API declarations: an agent definition takes
  `autoCompactWindow`, a "Token count, 100000 to 1000000, at which the agent compacts its
  own conversation as a subagent. It only lowers the window the agent would otherwise
  get." The same declarations say every field an agent file may carry takes effect as
  it does in a definition the API registers.
- Observed on 2026-11-10 in build 2.1.321, using copies of `denubis-basic-agents` under a
  temporary directory, each loaded with `claude -p --plugin-dir` and `--debug-file`:
  - An agent file with `autoCompactWindow: 50` or `banana` logged "has invalid
    autoCompactWindow … Must be an integer from 100000 to 1000000". With `500000` it
    logged no warning.
  - A `general-purpose` subagent (model `sonnet`) spawned from the copy with `500000`
    logged `effectiveWindow=480000`. The main session (model `haiku`) and a subagent of
    the copy with the invalid value each logged `effectiveWindow=980000`.
  - `claude plugin validate --strict` passed all three copies, so it does not check
    this field.

## Decision

Every agent file in this repository's plugins carries `autoCompactWindow: 500000`.

## Consequences

- A subagent of one of these types gets a compaction window of 480000 tokens instead of
  980000 (observed for a `sonnet` subagent only). The point inside that window at which
  it compacts (`autoCompactThreshold` in the declarations) was not observed. If a
  model's window is already 500000 or smaller, the line changes nothing.
- Claude Code's built-in agent types and the main session are unchanged.
- The mod's notes at 40% and 45% of a 1M window come before this point, so a subagent
  that called `ready_to_compact` should have its brief used at this compaction. No
  subagent has yet been observed reaching it.
- No test makes a new agent file carry the line.
- The Antigravity projection (`scripts/project_antigravity_plugin.py`) rewrites an
  agent file's `model` and `tools` and passes this line through unchanged. Whether
  Antigravity reads the field has not been checked.
- The compact-nag mod's notice to the main conversation still says "Subagents are not
  compacted early". That is true of the mod but no longer of these agent types. Whether
  to change that text is open.
