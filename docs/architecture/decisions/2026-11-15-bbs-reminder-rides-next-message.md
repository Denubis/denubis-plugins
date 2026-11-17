# ADR 2026-11-15-bbs-reminder-rides-next-message — the quiet-agents reminder rides on the next message instead of starting a turn

**Status:** Accepted (2026-11-15). Records a human ruling, "for now", and a second, "we
shouldn't have double-reminders". Applied in
`denubis-hook-quiet-agents` 0.1.4. It replaces how the turn-end nudge is delivered; which
agents it names (ADR 2026-11-15-bbs-quiet-agents-names-agents-once), the answered-turn
guard (ADR 0049), and the nudge's wording are unchanged.

## Authority evidence

Claude Code session `c06f9205-3224-4dbf-b681-82abb13bdb37`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl`.
Times are UTC on 2026-11-15.

- Line 1804, human, a message sent while the assistant was working (`queued_command`
  attachment, record `07a9d883-c627-4a7e-a559-4f9d0f564839`, 05:24:24.147Z). It pasted a
  session in which each quiet-agents nudge started a turn only for the model to answer
  that the agent was still working, for example "The merge worker stays: it is
  mid-merge, waiting on its test run."
- Line 1822, likewise (record `56bf14a9-1511-4b30-85a8-83783d50425e`, 05:24:50.192Z):
  "this is just such a waste of tokens".
- The assistant then asked through the question zone: "Should the quiet-agents reminder
  stop starting a turn of its own and instead ride along as a note on the next message
  that arrives?" Its context said the note would be attached to the next message that
  arrives anyway, "whether yours or an agent's", and that a finished agent would then not
  be prompted until something else wakes the session.
- Line 1874, human, record `fb149ba0-6aef-4d48-aac8-9843d2762ffd` (05:26:09.495Z): "yes,
  it should ride along, that'd be good for now".

Exact raw resolver:

```sh
sed -n '1804p;1822p;1874p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl
```

A second ruling, on one agent named twice in one message, comes from Claude Code session
`87de1afb-a1b7-429f-9fd0-ec0f8c5f00e6`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-parallel-plans-waiting-agents/87de1afb-a1b7-429f-9fd0-ec0f8c5f00e6.jsonl`,
during live testing of 0.1.4. Times are UTC on 2026-11-15.

- Line 169, the plugin's `prompt.submit` context beside the person's prompt "and...
  ping?" (record `50ab146e-86c0-4626-ab28-d6086ed495ef`, 10:18:00.515Z). It held two lines
  naming the same agent: "quiet-agents: these agents went idle since your last turn,
  their reports already received: uat-probe-2." and the reminder, "quiet-agents: idle or
  finished agents: uat-probe-2. Stop each with TaskStop, ...".
- Line 186, the assistant asked through the question zone (record
  `28cb17ea-9d9e-4ff6-8d70-2a8ed8655016`, 10:18:11.541Z): "When the stop-it reminder already
  names a finished agent, should the plugin drop the separate 'went idle, report already
  received' line for that agent?" (inner quotation marks shown as single; the record has
  double).
- Line 217, human, record `92b49579-e333-427f-8ff9-93416978db09` (10:18:51.201Z): "what
  feedback do we give the main session? I don't understand the question, but yes, we
  shouldn't have double-reminders?"

Exact raw resolver:

```sh
sed -n '217p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-parallel-plans-waiting-agents/87de1afb-a1b7-429f-9fd0-ec0f8c5f00e6.jsonl
```

## Context

From 0.1.0 to 0.1.3 the nudge was a prompt the plugin submitted under its own name, so
each one started a model turn. The mods API cannot add context at `turn.start` or
`turn.step` (Claude Code 2.1.325 declarations: `TurnStartResult` is `{ turnId }` alone,
and `TurnStepInput` carries no messages). `prompt.submit` takes `context`. A
`session.receive` delivery takes only a rewritten `text`; the plugin already puts a
leading line on an idle notice that way.

## Decision

At an answered main-loop turn end the plugin records the agents to name as it did, but
submits no prompt. The note waits and rides on the next message to the main
conversation: as context on the next prompt that enters, or as a leading line on the next
delivery from an agent (origin `peer`) that is queued. Any other delivery, such as the
person's own message from a Remote Control client or Slack, is queued as it came and the
note waits, so no plugin text is written into the person's words; limiting the leading
line to an agent's delivery is the assistant's design, not words of the ruling. A message
that does not enter leaves the note for the one after. An agent that the main
conversation messages before the note rides is left out of it.

As the note rides, it names only agents still listed, still idle or finished by the rule
a turn end uses, and not muted. One now listed as `waiting`, one muted, and one no longer
listed as idle, completed or failed wait in the note until they stop again or are
unmuted, so each agent is still named once. The rule has one limit: an agent whose idle
notice the plugin took out still counts as idle while it is listed as `running`, because
the roster can lag the notice, so one that woke on its own after that notice is still
named. This re-check is the assistant's design, not words of the ruling: the delay until
the next message makes a stale name likely for an agent that runs, goes idle and runs
again.

The reminder and the idle line name an agent once between them. The second ruling answered a question about
two lines in one message naming the same agent, and the person said they did not
understand the question, so it settles the outcome, not the mechanism. The rule and its
reach are the assistant's design. Once the reminder has named an agent on a message that
went in, beside a prompt or leading a delivery from an agent, that agent's name no longer
waits for the line of agents whose idle notices were taken out. So the line does not name
it beside that prompt or a later one, and the line is left out when no name is left. An
agent only on that line is still named there, and an idle notice of the agent taken out
later is named as usual. The reach past one message is there because the plugin's test
engine showed the same agent named again on the next prompt after the reminder rode on a
delivery; that case has not been seen live. A message that does not go in leaves both the
reminder and the name for the next one.

By the same outcome, a delivery that already carries the plugin's prompt to stop an
agent, an idle notice queued behind the full prefix, does not also carry the reminder for
that agent. The reminder leading it names only the other agents due, and the entry for
that agent waits in the note for the next message. A fresh review found the case: an
unmuted agent that answers by ending its turn is named by a turn end, wakes on its own and
goes idle again, and its second idle notice carried both prompts. Applying the rule by
the agent the prefix prompts, rather than to that sequence, is the assistant's design.

## Consequences

- No turn is started for the reminder. A finished agent is not prompted for a stop until
  something else wakes the session.
- A note on a teammate's delivery shows as a leading `quiet-agents:` line on that message.
- Applied in 0.1.4 and established by the plugin's tests. The ride on the next prompt was
  observed live on 2026-11-15 (session `87de1afb-a1b7-429f-9fd0-ec0f8c5f00e6`, lines
  161-169): the turn that `uat-probe-2`'s report started ended at 10:17:49.505Z, no turn
  started before the person's next prompt at 10:18:00.479Z, and the reminder came once,
  as context beside it. The ride on a delivery from an agent, leaving the reminder's
  agents off the idle line, keeping the reminder off a delivery that already prompts a
  stop of its agent, and leaving a muted agent out of the reminder have not been observed
  live. The corrected mute's notice prefix was seen once; see ADR
  2026-11-15-bbs-person-mutes-kept-agents.
