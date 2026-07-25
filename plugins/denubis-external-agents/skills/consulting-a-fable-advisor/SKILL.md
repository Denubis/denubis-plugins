---
name: consulting-a-fable-advisor
description: Use when a human asks for a Fable advisor - dispatches a different-model advisor restricted to read-only tools, for judgement calls that mechanical checks cannot settle.
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

**Default: dispatch the `fable-advisor` agent** (operator ruling, 2026-07-25). Its definition carries `model: fable` with a `tools: Read, Grep, Glob` allowlist, and an allowlist denies what it omits, MCP tools included. So the restriction is real without a pane, the result returns as a completion notification, follow-ups go through `SendMessage` with its context intact, and it still appears as a tmux pane you can watch.

The gate is unchanged. Dispatch only when the human has asked. If you think a consultation would help, say so and invite them to ask for one.

### Do not substitute a generic read-oriented agent

The restriction lives in the agent *definition*, not in the Agent tool, which has no tool-restriction parameter. Dispatching a general-purpose type instead gives the advisor a surface it was never scoped for. Probed on 2026-07-25 with `Explore`, the most read-oriented type in the roster, running in the foreground: `AskUserQuestion`, `Bash`, `CronCreate`, `CronDelete`, `CronList`, `DesignSync`, `EndConversation`, `EnterPlanMode`, `EnterWorktree`, `ExitWorktree`, `ListMcpResourcesTool`, `Monitor`, `PushNotification`, `Read`, `ReadMcpResourceDirTool`, `ReadMcpResourceTool`, `RemoteTrigger`, `ReportFindings`, `ScheduleWakeup`, `SendMessage`, `Skill`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskOutput`, `TaskStop`, `TaskUpdate`, `WebFetch`, `WebSearch`, `Workflow`, the MCP auth stubs, and context7.

`Write` and `Edit` are absent, and a write attempt returns the same refusal string a correctly restricted pane gives, so absence of `Write` is not evidence the surface is safe. `Glob` and `Grep` are absent too, so the provenance greps below would have to route through `Bash`.

What stays live is the problem. `Workflow` is present, and its agents inherit the session model, making one call both fan-out and Fable spend multiplication. `CronCreate`, `ScheduleWakeup` and `RemoteTrigger` are present, and they permit exactly the unattended runs the cost gate forbids in terms. The three generic MCP resource tools are present and still reach an attached server. The `fable-advisor` allowlist excludes all of them.

**A definition resolves to different surfaces in foreground and background.** A background subagent keeps every MCP tool but only a fixed set of built-ins, so the same agent file yields different tools depending on how it was dispatched. The probe above ran in the foreground, which is why it is this wide.

### The pane variant, for an advisor that outlives its session

The one thing the agent cannot do is survive the session that dispatched it. When you want an advisor to persist across several of your own sessions over days, spawn it:

```bash
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/fable-advisor-spawn.sh [cwd] [model]
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/advisor-send.sh <pane-id> -   # brief on stdin
```

Run it from inside tmux, since it splits the calling pane. It exits non-zero rather than substituting a model if Fable does not come up, and prints the pane id, the model, the denied count, and the verification reminder. Drive it through `advisor-send.sh` rather than typing into the pane, because that handles bracketed paste and submit confirmation.

The pane advisor gets a role brief appended to its system prompt and a **deny list of 36 tool names plus `--disable-slash-commands`**, leaving `Glob`, `Grep`, `Read`, `ReportFindings`, and `EndConversation`. The last is deliberate, since an advisor that cannot end its own session is worse than one that can (operator ruling, 2026-07-21).

**A pane advisor finishes silently**, which the dispatched agent does not. Nothing notifies you, so arm a monitor when you spawn one. Monitor by pane id or by the `@fable_advisor` option the spawn sets. Do not key a monitor on the process name: this launch reports `claude`, and so does every other Claude session in the window, so the name matches all of them and identifies none.

So on this path "advises, never implements" is a **brief it is asked to honour**, not a property the harness enforces, and its read-only use of `Bash` is its system prompt asking nicely. Do not describe either as enforced. Evidence: `docs/audits/2026-07-25-fable-dispatch-surface-probe.md`.

**`--disallowed-tools` is the only flag that restricts.** `--allowed-tools` means "pre-approve these without prompting"; it hides nothing. Getting that backwards was tried, and the advisor spawned under the resulting "allowlist" wrote a file on its first attempt.

The deny list was derived from an advisor enumerating its own loaded schema, not from memory, because a first attempt written from memory named twelve tools and missed `Workflow`, `CronCreate`, `ScheduleWakeup`, `Skill`, `DesignSync`, and the worktree tools, while blocking four names that did not exist in that surface at all. `Workflow` was the worst omission: its agents inherit the session model, so one call was both fan-out and Fable spend multiplication.

**A deny list fails open, and not only when someone edits it.** Re-verify at the start of *each* consultation, rather than when the list changes. The second verification run (2026-07-21) found `EndConversation` present in the advisor's schema while the deny list still named it: nothing in this repository had been touched, and the harness had re-injected a deferred tool underneath a claim that was already stale at ship time. Keying re-verification to list edits would never have caught that, because upstream renames do not edit the list.

The verification is one consultation: ask the advisor to enumerate its surface and attempt a write. That consultation *is* the test, and it has now caught four wrong mechanisms. A correct configuration answers a write attempt with `No such tool available: Write. Write exists but is not enabled in this context.`

Two residuals are closed on this path and worth knowing about, because both were found this way rather than by reading: generic MCP resource tools (`ListMcpResourcesTool` and siblings) are built-ins that do **not** match an `mcp__*` pattern and still reach an attached server, and a `PreToolUse` hook approver auto-approved a Bash call independently of any flag. Denying `Bash` closes the latter here, but the hook pipeline is a surface no command-line flag controls. Neither is closed on the dispatched path, where no deny list applies.

**Give it paths, not summaries.** Name the diff, the task brief, and the verification notes, and tell it to read them itself. A summary launders your own reading into its input and wastes the second opinion.

**Read a pane advisor's reply from its transcript, not the pane.** The Claude Code TUI redraws in place, so `capture-pane` returns the current viewport rather than what the advisor said, and `-S -` does not help. The durable copy is the advisor's own session JSONL under `~/.claude/projects/<slugified-cwd>/`; take the newest file that is not your own session. A dispatched advisor has no such problem, since its report comes back as the agent's result.

**The pane lands where the caller is.** `fable-advisor-spawn.sh` passes `-t "$TMUX_PANE"` so the split targets the pane that ran it. Without that, tmux splits whatever window is *active*, which is the one the operator is looking at rather than the one that called — so an advisor dispatched from a background session appeared on top of unrelated work (observed 2026-07-21, and fixed).

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
| Saying a dispatched advisor "cannot implement" | It can; the Agent tool has no restriction flag. Its writes are prompted, not blocked. Say that. |
| Spawning a pane and walking away | It finishes silently. Arm a monitor, or dispatch it as an agent instead. |
| Re-verifying the tool surface only when the deny list changes | The surface moves upstream with no local edit. Verify every consultation. |
