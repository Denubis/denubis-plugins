# ADR 2026-11-15-bbs-waiting-agents-are-not-idle — quiet-agents treats an agent waiting on its own shell or monitor as not idle

**Status:** Accepted (2026-11-15). Records a human ruling. Applied in
`denubis-hook-quiet-agents` 0.1.4. ADR 2026-11-15-bbs-quiet-agents-names-agents-once and
ADR 0049 still hold.

## Authority evidence

Claude Code session `c06f9205-3224-4dbf-b681-82abb13bdb37`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl`.
Times are UTC on 2026-11-15.

- Line 9, human, record `4b931702-e597-4100-9a99-be37031905e1` (04:35:35.506Z), the third
  of three requested changes: "3) for the idle thing, if it's waiting on a shell or monitor
  it shouldn't be marked idle)".
- Line 287, human, a message sent while the assistant was working (a `queued_command`
  attachment, record `742f90b5-cf56-415e-88d3-6e2915a1086b`, 04:46:54.892Z): "there's no
  api cross-work here, it's just different subagents".
- Line 304, human, likewise (record `7edc8edb-906e-4dce-a2f2-072035196dd9`, 04:47:31.487Z):
  "or mod, honestly, the cross-linked ones in the mod can just be declared in the notice
  or ... if it's to ohard, skip".

- Line 1204, human, record `5aaa1a68-1ef6-46c3-b3a7-5cf9538c004b` (05:12:51.673Z), after
  the assistant reported adding a nudge clause ("leave it be while a shell or monitor of
  its own still runs") for the agents the plugin cannot see waiting: "no, that nudge is
  silly, it's more that ... hrm.... argh, I don't know. is there a way to do an easy
  "mute" on something that runs, goes idle, runs, etc?"

Exact raw resolver:

```sh
sed -n '9p;287p;304p;1204p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl
```

The assistant read lines 287 and 304 together as: mark nothing idle that the plugin can
tell is waiting, and where it cannot tell, say so in the nudge's text. That reading is the
assistant's, not Brian's words. Line 1204 rejected the nudge clause.

## Context

The mods API's `AgentStatus` documents `waiting` as "on background work it owns, on a
plan's approval or, in a background subagent, on an Agent call alone" (Claude Code 2.1.325
declarations). It lists no shells or monitors per agent: the only per-task list,
`background_tasks` on the classic `Stop` and `SubagentStop` inputs, names no owner.

Before 0.1.4, a teammate whose idle notice the plugin took out was shown idle on the
status line, named as gone idle in the next prompt's context, and named by the turn-end
nudge, whatever its listed status. That rule is deliberate for `running`: the roster can
still say `running` when the idle notice arrives (the test of a failed agent list relies
on it).

A teammate in a terminal pane of its own is listed `running` or `idle` by what it last
wrote in its team's roster, never `waiting`, so the plugin cannot see that its shells or
monitors still run. The kept teammate `shepherd` of ADR 2026-11-15-bbs-quiet-agents-names-agents-once
arrived unverified, as such a teammate's messages do.

## Decision

An agent Claude Code lists as `waiting` is not idle. The plugin leaves it off the status
line's idle names, out of the next prompt's names, and out of the turn-end nudge, and does
not record it as named, even when its idle notice was taken out. Any other status leaves a
taken-out idle notice standing.

The nudge's text is unchanged: a clause telling the model to leave an agent be while its
shell or monitor runs was proposed and rejected (line 1204). A teammate in a terminal pane
of its own, which the plugin cannot see waiting, is therefore treated as before.

## Consequences

- Applied in `plugins/denubis-hook-quiet-agents/hooks/register.tsx` (`waitingNames`,
  `statusLine`, `turnEndStep`, and the `prompt.submit` hook). The stored state's shape is
  unchanged.
- A `waiting` agent that later turns `idle` is named once, as any idle agent is.
- `/tidy` already left `waiting` agents alone and is unchanged.
- Established by the plugin's tests. Not yet observed live: which background work puts an
  agent in `waiting` rests on the type documentation.
