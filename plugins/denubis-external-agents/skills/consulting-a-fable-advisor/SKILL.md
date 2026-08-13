---
name: consulting-a-fable-advisor
description: Use when a human explicitly asks for a Fable consultation on a judgment question that mechanical evidence cannot settle.
user-invocable: true
disable-model-invocation: true
---

# Consulting a Fable advisor

## Boundary

Fable work is human-triggered only. This skill is visible to the human and unavailable to
Claude's model invocation. The authority record is
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/e4421bb3-2615-4b37-944c-86e5dd65eccc.jsonl:12`;
resolve it with
`cc-search-chats context 0a1beea2-2d45-455f-9ced-9ec278afb8e8 --json`.

A consultation supplies another model's judgment. It neither authorises changes nor proves
its own claims. The main session checks the cited source before acting.

## Choose the execution surface

Use a background Agent when completion notification and easy follow-up matter more than
tool isolation. The Agent surface has no per-dispatch tool restriction, so describe it
honestly: the advisor is instructed not to implement, but the harness does not make that
impossible.

Use the pane variant when a restricted tool surface matters:

```fish
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/fable-advisor-spawn.sh [cwd] [model]
bash plugins/denubis-external-agents/skills/consulting-a-fable-advisor/advisor-send.sh <pane-id> -
```

The pane launcher denies the known mutation, orchestration, network, and MCP tools. The
tool namespace can change upstream, so its deny list is not a permanent proof. Before
giving the advisor repository work, ask it to enumerate its callable tools and attempt a
write. Continue only when the observed surface matches the intended read-only boundary.

## Brief

Give the advisor:

- one judgment question;
- exact paths to the implementation, contract, and verification evidence;
- the scope it must not widen; and
- the requested output: findings with source locations, consequence, confidence, and any
  assumption that could reverse the finding.

Do not give it a model-authored summary as evidence. Let it open the sources. Do not ask
for internal reasoning or self-critique.

## Consume the result

For each finding that could change an action:

1. Open the cited file or evidence producer.
2. Check that the cited observation exists and bears the claimed consequence.
3. Separate what the advisor read from what it inferred.
4. Accept, reject, or return a genuine ambiguity to the human.

Do not merge the advisor's voice into the implementer's account or treat an approval label
as a gate. If a citation cannot be resolved, discard that finding. If the model is
unavailable, report that fact and stop; substituting another model requires a new human
choice.

Pane output is durable in the advisor's JSONL transcript under
`~/.claude/projects/<slugified-cwd>/`. The TUI viewport is not the transcript.
