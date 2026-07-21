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

```bash
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/fable-advisor-spawn.sh [cwd] [model]
```

It prints the pane id, the model, and the blocked tool list. Drive that pane with the same send-and-read mechanics as any other agent pane.

The advisor starts with a role brief appended to its system prompt, and with a **deny list of 37 tool names plus `--disable-slash-commands`**. What survives is `Glob`, `Grep`, `Read`, and `ReportFindings`. Read and search are the whole surface needed to ground a finding.

**`--disallowed-tools` is the only flag that restricts.** `--allowed-tools` means "pre-approve these without prompting"; it hides nothing. Getting that backwards was tried, and the advisor spawned under the resulting "allowlist" wrote a file on its first attempt.

The deny list was derived from an advisor enumerating its own loaded schema, not from memory, because a first attempt written from memory named twelve tools and missed `Workflow`, `CronCreate`, `ScheduleWakeup`, `Skill`, `DesignSync`, and the worktree tools, while blocking four names that did not exist in that surface at all. `Workflow` was the worst omission: its agents inherit the session model, so one call was both fan-out and Fable spend multiplication.

**A deny list fails open on every rename and addition, so the claim needs re-verifying empirically whenever the list changes.** Spawn an advisor and ask it to enumerate its surface and attempt a write. That consultation is the test, and it has caught three wrong mechanisms so far. A correct configuration answers a write attempt with `No such tool available: Write. Write exists but is not enabled in this context.`

Two residuals are closed and worth knowing about, because both were found this way rather than by reading: generic MCP resource tools (`ListMcpResourcesTool` and siblings) are built-ins that do **not** match an `mcp__*` pattern and still reach an attached server, and a `PreToolUse` hook approver auto-approved a Bash call independently of any flag. Denying `Bash` closes the latter here, but the hook pipeline is a surface no command-line flag controls.

**Give it paths, not summaries.** Name the diff, the task brief, and the verification notes, and tell it to read them itself. A summary launders your own reading into its input and wastes the second opinion.

**Read its reply from its transcript, not the pane.** The Claude Code TUI redraws in place, so `capture-pane` returns the current viewport rather than what the advisor said, and `-S -` does not help. The durable copy is the advisor's own session JSONL under `~/.claude/projects/<slugified-cwd>/`; take the newest file that is not your own session.

## If Fable is unavailable

Fable-tier access is intermittent; it lapsed through June 2026. The script exits non-zero rather than substituting anything, because a silently swapped model destroys the only thing the consultation was for.

Falling back to Opus 4.8 is the operator's call, taken knowingly, and the consultation is then **labelled as the fallback model**. Never present an Opus consultation as a Fable one.

## Between consultations

The advisor pane persists between questions, and it will usually sit unused for a long stretch. **When it has been idle long enough to emit its recap, take that as the cue to compress it**, because the recap means it is between jobs and the next consultation is not imminent.

Compress it deliberately rather than generically. Name what to keep:

- the numbered rulings in force, verbatim;
- the findings it has already delivered, as pointers to where they are recorded rather than as restated text;
- the repo facts it established for itself, with their `file:line` pins.

And name what to drop: the file contents it read, the paths it explored getting there, and any reasoning superseded by a later ruling. Fable-tier sessions stay cheap when their context is pointers rather than payload, so a directed compress is worth more than letting it auto-compact on its own terms.

Reach for `/clear` only when the next consultation is genuinely unrelated to everything before it. Clearing discards precisely the material that is expensive to rebuild: the rulings and the repo facts the session established for itself.

This is not advisor-specific. Any persistent external session consulted intermittently — a codex pane included — wants the same treatment on the same cue.

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
