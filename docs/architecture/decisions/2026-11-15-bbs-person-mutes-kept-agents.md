# ADR 2026-11-15-bbs-person-mutes-kept-agents — the person mutes a kept agent with a quiet-agents subcommand

**Status:** Accepted (2026-11-15). Records a human ruling, and a second that narrows
what a mute does (see "Correction, 2026-11-15" below). Applied in
`denubis-hook-quiet-agents` 0.1.4. ADR 2026-11-15-bbs-quiet-agents-names-agents-once and
ADR 2026-11-15-bbs-waiting-agents-are-not-idle still hold.

## Authority evidence

Claude Code session `c06f9205-3224-4dbf-b681-82abb13bdb37`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl`.
Times are UTC on 2026-11-15.

- Line 1204, human, record `5aaa1a68-1ef6-46c3-b3a7-5cf9538c004b` (05:12:51.673Z): "no,
  that nudge is silly, it's more that ... hrm.... argh, I don't know. is there a way to do
  an easy "mute" on something that runs, goes idle, runs, etc?"
- The assistant then proposed, in chat, a `/mute <name>` command only the person types,
  with `/unmute <name>` and `/mute` alone to list. For a muted agent the plugin would
  take out every idle notice, leave it out of the idle line and the nudge, show it as
  muted on the status line, and keep `/tidy` from stopping it, while its own messages
  still come through. The mute would end at unmute or when the agent is stopped, and
  would go by the agent's id.
- Line 1273, human, a message sent while the assistant was working (a `queued_command`
  attachment, record `d759ef26-5531-42e2-991f-bcf10f588d69`, 05:14:03.285Z): "yeah,
  sure I am happy to do this".
- Line 1290, human, likewise (record `761b78d8-eff1-452a-a11f-42907e2b7318`,
  05:14:14.299Z): "not mute but like as a subcommend of this mod".

Exact raw resolver:

```sh
sed -n '1204p;1273p;1290p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl
```

The assistant read line 1290 as: the mute is a subcommand of one command named after the
mod, `/quiet-agents`, rather than a top-level `/mute`. `/tidy` keeps its own name. That
reading is the assistant's.

## Context

An agent kept on purpose that runs, goes idle and runs again on its own is still noisy
after ADR 2026-11-15-bbs-quiet-agents-names-agents-once. Its idle notices reach the model
once the main conversation has messaged it. Each idle cycle names it in the next prompt's
idle line, and the status line keeps naming it idle. The mods API registers a command as
`/<name>` with no plugin prefix (`CommandSpec.name`, Claude Code 2.1.325).

## Decision

`/quiet-agents mute <agent>` mutes an agent, `/quiet-agents unmute <agent>` ends the mute,
and `/quiet-agents mute` alone lists the muted agents. Only the person types it; the model
has no tool to mute with. For a muted agent the plugin:

- leaves it out of the next prompt's idle line and the turn-end nudge;
- names it as `muted` on the status line, not as idle; and
- leaves it out of `/tidy`.

It changes nothing about which deliveries are queued or taken out: its own messages and
its idle notices are handled as an unmuted agent's are (corrected 2026-11-15, below). A
mute goes by the agent's id, so a new agent under
the same name is not muted. It ends at unmute, or once the agent is stopped: at the first
main-loop turn end whose agent list lists the agent as `killed` or no longer holds it.

## Consequences

- Applied in `plugins/denubis-hook-quiet-agents/hooks/register.tsx` (the `muted` atom
  under the shape tag `muted-ids-1`, `quietAgentsCommand`, and the mute checks in
  `statusLine`, `turnEndStep`, `tidy`, the reminder as it rides, and `prompt.submit`). The command
  is registered `immediate`, so it runs while a turn is in flight.
- A muted agent unmuted while idle or finished is named once at the next answered turn
  end, unless a nudge named it before it was muted.
- Established by the plugin's tests. The mute as first applied was used live on
  2026-11-15 and lost answers (below); the corrected mute was seen once in a live retest
  the same day (below).

## Correction, 2026-11-15

Live testing on 2026-11-15 showed the mute losing answers carried in idle notices. Claude
Code session `f5abbd01-7d51-4a05-bed0-d76573d3f3e6`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-parallel-plans-waiting-agents/f5abbd01-7d51-4a05-bed0-d76573d3f3e6.jsonl`:
the person muted the agent `ping-test` (the command's output came with their message at
line 102, 10:50:30.953Z UTC; the assistant confirmed it at line 112), the main
conversation then sent it two pings (lines 107 and 117), and neither reply reached the
main conversation (line 121). At line 240 the assistant there
reported that the agent's own transcript shows both replies, `pong: Ping two after the
mute,` and `pong: Ping three after the mute,`. That agent answered by ending its turn,
sending no report, so each answer was only in its idle notice's `result`, and the mute
took out every idle notice from a muted agent, reported or not.

The person then ruled, verbatim (raw resolver: `sed -n '3244p;3255p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl`): "this is for long
running things that wake up and go idle and wake up and go idle" and "we just don't want
the nag. we're musting *this nag*" (sic; "muting").

So a mute silences only the naming of the agent: the reminder, the next prompt's idle
line, the status line's idle names, and `/tidy`. It changes nothing about which
deliveries are queued or taken out. A muted agent's idle notice is taken out only when an
unmuted agent's would be, after its report was received, and is then still kept off the
idle names and the reminder. One with no report before it reaches the model with the
prefix, as an unmuted agent's does. Removing the mute's own case for idle notices, rather
than adding another, is the assistant's design.

A live retest the same day showed those answers arriving behind the full prefix, whose
last sentence tells the model to stop a finished agent with TaskStop. The assistant reads
the ruling's "this nag" as every prompt to stop the agent, so for a muted agent the plugin
gives the model no such prompt on any path it can match to the agent: a muted agent's
queued idle notice comes behind the prefix without that sentence. An agent notice that
arrives as a prompt carries no agent name or id (`PromptSubmitInput`, Claude Code 2.1.325
declarations), so its context keeps the sentence. The system prompt's hygiene section
still tells the model, in general, to stop a finished agent.

A second live retest the same day saw the corrected mute once. At line 3361 of the
transcript above (human, record `a3dd932a-59c6-4983-8b0e-737f19b582a2`, 11:48:08.956Z;
raw resolver: `sed -n '3361p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl`)
the person pasted a test session's report: "The mute fix works. ping-test-2's reply came
through as pong: Ping one after the mute,, and the line in front no longer tells me to
stop it." Its table shows the line in front ending at "…do not restate pending
decisions." after the mute, where before the mute it went on to "stop it with TaskStop
in this turn." The same report lists, as not yet seen, a muted agent left out of the
reminder. This is that session's report, not a reading of its transcript.
