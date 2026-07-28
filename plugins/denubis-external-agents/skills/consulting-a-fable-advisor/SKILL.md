---
name: consulting-a-fable-advisor
description: Use when a human asks for a Fable advisor - spawns a different-model advisor in a tmux pane, structurally unable to implement, for judgement calls that mechanical checks cannot settle.
user-invocable: true
---

# Consulting a Fable Advisor

## Overview

A consultation with a different model, in a pane you can watch, on the questions verification cannot answer. The advisor advises; it does not implement, and that is enforced by removing its write and orchestration tools rather than by asking it nicely.

This skill is **mechanism, not judgement**. A capable agent already knows how to brief an advisor well, and the model facts it needs are recorded in `denubis-extending-claude`'s `model-tier-notes.md`. What is not obvious is the spawn incantation, which flag actually restricts a tool surface, and the availability handling. That is what lives here.

## The gate: human-invocable only

**Fable-tier invocations are human-triggered only.** The standing cost gate (`plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md`, "Cost gate") forbids any directive, skill, plan, or agent prompt from auto-dispatching Fable-tier work. Only a dated operator note revokes it; no model release, price change, or doc update does.

So:

- **No other skill, agent, hook, or command may reference this skill as a step.** A skill that says "then consult the Fable advisor" is auto-dispatch, and it breaches the gate.
- `tests/test_fable_cost_gate.py` enforces this mechanically, because prose guarding a cost gate is a silent failure mode: the breach would otherwise surface on your bill, not in review.
- A human typing the request is the only valid trigger.

## When to use

After the implementer has drafted and the verifier has run its mechanical checks. The advisor's value is judgement on what tests cannot settle: is this design coherent, is the fix right for the right reason, did the verification check the thing that matters or something adjacent to it.

**When NOT to use:**

- Before the mechanical checks. The consultation is wasted on anything a test would have caught.
- For work an ordinary subagent handles. If the question does not need a different model, it does not need this.
- Automatically, ever. See the gate.

## How to run

**Default: dispatch it as a background agent** (operator preference, 2026-07-21). Use the Agent tool with `model: "fable"` and a read-oriented agent type, and brief it in the prompt exactly as below. The work returns as a completion notification, follow-ups go through `SendMessage`, and there is no pane to babysit.

What this costs, stated plainly: **the Agent tool has no tool-restriction parameter.** Agent types carry fixed tool sets, and the most restricted one available still has `Bash`. So a dispatched advisor *can* write to disk. Those writes are permission-prompted rather than silent, so the residual risk is alert fatigue on the operator's side, not unguarded modification. "Advises, never implements" is therefore a **brief it is asked to honour**, not a property the harness enforces. Do not describe it as enforced.

### The pane variant, when the restriction must be real

```bash
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/fable-advisor-spawn.sh [cwd] [model]
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/advisor-send.sh <pane-id> -   # brief on stdin
```

Use this when the advisor is reviewing something it could damage, and accept the extra handling in exchange for a surface that genuinely lacks `Write` and `Bash`. The spawn prints the pane id, the model, and the denied count; `advisor-send.sh` ships alongside it and handles bracketed paste and submit confirmation.

The advisor starts with a role brief appended to its system prompt and a **deny list of 36 tool names plus `--disable-slash-commands`**. What survives is `Glob`, `Grep`, `Read`, `ReportFindings`, and `EndConversation` — the last deliberately, since an advisor that cannot end its own session is worse than one that can (operator ruling, 2026-07-21).

**A pane advisor finishes silently.** Nothing notifies you, so arm a monitor when you dispatch one, or you will discover it concluded twenty minutes ago. This is the main practical reason the dispatched variant is the default.

**`--disallowed-tools` is the only flag that restricts.** `--allowed-tools` means "pre-approve these without prompting"; it hides nothing. Getting that backwards was tried, and the advisor spawned under the resulting "allowlist" wrote a file on its first attempt.

The deny list was derived from an advisor enumerating its own loaded schema, not from memory, because a first attempt written from memory named twelve tools and missed `Workflow`, `CronCreate`, `ScheduleWakeup`, `Skill`, `DesignSync`, and the worktree tools, while blocking four names that did not exist in that surface at all. `Workflow` was the worst omission: its agents inherit the session model, so one call was both fan-out and Fable spend multiplication.

**A deny list fails open, and not only when someone edits it.** Re-verify at the start of *each* consultation, rather than when the list changes. The second verification run (2026-07-21) found `EndConversation` present in the advisor's schema while the deny list still named it: nothing in this repository had been touched, and the harness had re-injected a deferred tool underneath a claim that was already stale at ship time. Keying re-verification to list edits would never have caught that, because upstream renames do not edit the list.

The verification is one consultation: ask the advisor to enumerate its surface and attempt a write. That consultation *is* the test, and it has now caught four wrong mechanisms. A correct configuration answers a write attempt with `No such tool available: Write. Write exists but is not enabled in this context.`

Two residuals are closed and worth knowing about, because both were found this way rather than by reading: generic MCP resource tools (`ListMcpResourcesTool` and siblings) are built-ins that do **not** match an `mcp__*` pattern and still reach an attached server, and a `PreToolUse` hook approver auto-approved a Bash call independently of any flag. Denying `Bash` closes the latter here, but the hook pipeline is a surface no command-line flag controls.

**Give it paths, not summaries.** Name the diff, the task brief, and the verification notes, and tell it to read them itself. A summary launders your own reading into its input and wastes the second opinion.

**Read a pane advisor's reply from its transcript, not the pane.** The Claude Code TUI redraws in place, so `capture-pane` returns the current viewport rather than what the advisor said, and `-S -` does not help. The durable copy is the advisor's own session JSONL under `~/.claude/projects/<slugified-cwd>/`; take the newest file that is not your own session. A dispatched advisor has no such problem, since its report comes back as the agent's result.

**The pane lands where the caller is.** `fable-advisor-spawn.sh` passes `-t "$TMUX_PANE"` so the split targets the pane that ran it. Without that, tmux splits whatever window is *active*, which is the one the operator is looking at rather than the one that called — so an advisor dispatched from a background session appeared on top of unrelated work (observed 2026-07-21, and fixed).

## If Fable is unavailable

Fable-tier access is intermittent; it lapsed through June 2026. The script exits non-zero rather than substituting anything, because a silently swapped model destroys the only thing the consultation was for.

Falling back to Opus 4.8 is the operator's call, taken knowingly, and the consultation is then **labelled as the fallback model**. Never present an Opus consultation as a Fable one.

## Between consultations

The advisor pane persists between questions, and it will usually sit unused for a long stretch. **When it has been idle long enough to emit its recap, take that as the cue to compress it**, because the recap means it is between jobs and the next consultation is not imminent.

**The judgement rides on the slash command, not on a chat message.** `/compact` takes preservation instructions as its argument, the way `executing-an-implementation-plan` already suggests them at a phase boundary, so the keep/drop list belongs there. A message *asking* the advisor to compress its own context is a task: it reads files to answer you, and the context gets heavier rather than lighter.

Compact it deliberately rather than generically. Name what to keep:

- the numbered rulings in force, verbatim;
- the findings it has already delivered, as pointers to where they are recorded rather than as restated text;
- the repo facts it established for itself, with their `file:line` pins.

And name what to drop: the file contents it read, the paths it explored getting there, and any reasoning superseded by a later ruling. Fable-tier sessions stay cheap when their context is pointers rather than payload, so a directed compact is worth more than letting it auto-compact on its own terms.

Reach for `/clear` only when the next consultation is genuinely unrelated to everything before it. Clearing discards precisely the material that is expensive to rebuild: the rulings and the repo facts the session established for itself.

**This does not carry across to a codex pane, and assuming it did cost a session.** Codex is a different tool, its `/compact` is not known to accept an argument, and a prose brief sent in place of the slash command is read as work: on 2026-07-28 a carefully written keep/drop brief moved a codex pane's meter from 21% to 18% and ended with codex reporting "Context compressed as specified" while nothing had been compacted. A codex pane is also cleared between prompts as a matter of course rather than compacted on an idle cue, because its numbered prompt files are written to be self-contained. `supervising-codex` carries that practice.

## Handling the output

The same discipline as `codex-peer-review`, for the same reason: a fluent review is not evidence it read the file.

1. **Provenance gate.** `grep -nF` two or three verbatim quotes from its findings against the files it attributes them to. A quote absent from its cited file voids that finding; broad failure means discard the review and report the confabulation.
2. **Present source-tagged and unmerged.** It is the advisor's voice, not yours. Do not merge, dedup, or re-rank its findings by what you think is genuine. Your own take goes separately and labelled.
3. **Where the advisor and the implementer disagree, record both.** Per this repo's "Conflicting Authoritative Sources Are Recorded, Not Resolved", the disagreement is the signal, and averaging it away destroys it.
4. **Findings go to the human one at a time**, per `CLAUDE.md`'s halting rule. Batch-fixing skips the step where embedded assumptions surface, which is what the consultation was bought for.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Referencing this skill as a step in another skill | Breaches the cost gate. Only a human triggers it. |
| Consulting before the mechanical checks | Run the tests first; do not spend a different model on what a test settles. |
| Handing the advisor your summary | Give it paths and let it read. Otherwise you are consulting your own reading. |
| Silently falling back to Opus when Fable is down | Label the fallback, or do not run it. |
| Presenting its advice merged with yours | Keep the voices separate, as with codex. |
| Treating a fluent consultation as verified | Run the provenance gate. Fluency is not provenance. |
| Saying a dispatched advisor "cannot implement" | It can; the Agent tool has no restriction flag. Its writes are prompted, not blocked. Say that. |
| Spawning a pane and walking away | It finishes silently. Arm a monitor, or dispatch it as an agent instead. |
| Re-verifying the tool surface only when the deny list changes | The surface moves upstream with no local edit. Verify every consultation. |
| Asking a session to compress its own context in prose | That is a task, so it reads files and the context grows. Put the keep/drop list in `/compact`'s argument. |
| Sending a codex pane the same keep/drop brief | Codex is not Claude Code. Clear it between prompts; see `supervising-codex`. |
