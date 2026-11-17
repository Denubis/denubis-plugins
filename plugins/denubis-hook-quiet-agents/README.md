# quiet-agents

A Claude Code mod (a plugin built from a hooks module) that keeps subagents and
agent-team teammates from filling the conversation with turns that say nothing new.

## The problem

When a teammate finishes, it sends its report to the main conversation, then goes idle.
Its idle notice arrives a few seconds after the report and starts a turn of its own. In
that turn the model tends to restate what the person was already told: the report again,
the decisions still waiting on the person, "waiting on you". Finished agents also tend to
stay idle across many turns, because nothing asks the model to stop them.

## What it does

**The report-received rule.** When a teammate or subagent sends the main conversation a
message, the plugin marks it as reported. If its idle notice arrives while the mark
stands, the plugin takes the notice out of the conversation: the model never sees it and
no turn starts. The mark lasts until the main conversation next sends that agent a
message. From then on the agent is working on something new, so its next idle notice is
let through.

The mark is set at two points, and neither takes a name from the message text:

- A message that arrives through the team mailbox is marked on arrival, when the mailbox
  has verified the sender or the name it carries is one Claude Code lists for an agent of
  this session. The name is the one the mailbox stamps. A teammate in a terminal pane of
  its own writes to the team's inbox file, which the mailbox cannot check, so its messages
  always arrive unverified. Anything that can write that file can claim a listed agent's
  name; the most that does is hide that agent's next idle notice.
- A message that an agent of this session sends to the main conversation, addressed
  `main` or `team-lead`, is marked once the send is delivered. The name is the one Claude
  Code lists for that agent. An agent it cannot name is not marked, and the debug log
  says so. A message from one agent to another marks nothing.

The second point exists because a subagent's report can reach the conversation after its
idle notice. On 2026-10-24 a subagent's idle notice arrived at 22:59:24.29Z, and its
report was taken from the queue at 22:59:24.99Z. Marking only on arrival let that notice
through.

**A one-line prefix for unreported idle notices.** An idle notice from a teammate whose
report has not arrived, or whose mark was cleared, reaches the model with this line in
front of it:

```text
[quiet-agents] An agent went idle. If this adds nothing the human has not been told, it gets no reply; do not restate pending decisions. If its task is complete and you have no further work for it, stop it with TaskStop in this turn.
```

**Named once, at the next prompt.** The teammates whose idle notices were taken out are
named once, as context beside the next prompt that enters the conversation. A prompt
that is dropped before it enters leaves the names for the one after. An agent the
end-of-turn reminder names, beside a prompt or on a delivery from an agent, is not named
on this line as well, beside that prompt or a later one, and the line is left out when no
name is left
([ruled 2026-11-15](../../docs/architecture/decisions/2026-11-15-bbs-reminder-rides-next-message.md)).
An idle notice of that agent taken out later is named as usual. A message that does not
go in leaves both for the one after.

**An agent Claude Code lists as `waiting` is not idle.** Claude Code's types document
`waiting` as "on background work it owns, on a plan's approval or, in a background
subagent, on an Agent call alone"; a shell or a monitor the agent started and that is
still running is one such case. Every `waiting` agent, whatever it waits on, is left off
the status line's idle names, out of the next prompt's names, and out of the end-of-turn
reminder, even when its idle notice was taken out.
Once Claude Code lists it as idle, it is treated like any other idle agent. Any status
other than `waiting` leaves a taken-out idle notice standing, because the roster can
still say `running` when the notice arrives.

**Repeated notices are muted.** An agent notice that arrives as a prompt, such as a
background task's notification, is dropped when its text matches the last notice under
the same key, ignoring whitespace. A new or changed notice passes with context telling the
model that an agent, not the person, started the turn, and that it gets no reply when it
adds nothing new.

**A hygiene section in the system prompt.** Each system prompt the plugin sees composed
ends with one section on agents and their notices: stop a finished agent with TaskStop in
the same turn you acknowledge it, give an agent notice that carries nothing new no reply,
treat notices as inputs to work rather than requests for a reply, follow up and close
workers once their work is verified, and tell the person only changed results,
consequential corrections or a decision they must make. An in-process
teammate's render of the lead's prompt does not get it.

**The status line.** The plugin's status line names the idle teammates whose idle notice
it took out, less any listed as `waiting`, and every idle agent a turn end has named for
the reminder, and counts the finished and failed agents, for example `agents idle: helper, scout; 1 done, 1 failed`, or
`agents: 1 done` when none is idle. So an agent the model keeps stays in view
([ruled 2026-11-15](../../docs/architecture/decisions/2026-11-15-bbs-quiet-agents-names-agents-once.md)).
It updates when an idle notice is taken out, when a message from the main conversation
takes an agent off the list, and at the end of each turn of the main conversation. An agent that is no longer listed,
because it was stopped, drops off at the next turn end.

**The end-of-turn reminder.** At the end of a main-conversation turn, the plugin
gathers the idle teammates and every listed agent that is idle, completed or failed,
leaving out any agent a plugin started (such as question-zone's checkers), which is the
plugin's to manage, any agent listed as `waiting`, and any muted agent. The agents in that
set that no turn end has named yet wait for the next message to the main conversation; the
plugin starts no turn of its own
([ruled 2026-11-15](../../docs/architecture/decisions/2026-11-15-bbs-reminder-rides-next-message.md)).
The reminder rides on that message, as context beside the next prompt that enters, or as a
leading line on the next delivery from an agent that is queued, such as a teammate's
report. Any other delivery, such as your own message from a Remote Control client or
Slack, is queued as it came, so no plugin text is written into your words, and the
reminder waits:

```text
quiet-agents: idle or finished agents: <names>. Stop each with TaskStop, unless its work is unfinished: then continue it instead. Ask the person any question through the question zone's mcp__denubis-hook-question-zone__ask tool, never in chat.
```

A message that does not go in, a prompt that is dropped or a delivery that is taken out,
leaves the reminder for the one after. An agent it names is not named again on the line
of agents that went idle (above). An idle notice queued with its own prompt to stop that
agent carries no reminder naming that agent: the reminder leading it names only the
others due, and that agent waits in it for the next message. As it rides, it names only the agents still listed,
still idle or finished by the rule a turn end uses, not muted, and not messaged by the
main conversation since. So an agent listed as `waiting` by then, a muted one, and one no
longer listed as idle, completed or failed wait in the reminder until they stop again or
are unmuted. The rule has one limit: an agent whose idle notice the plugin took out still
counts as idle while it is listed as `running`, because the roster can lag the notice, so
one that woke on its own after that notice is still named. A finished agent is not
prompted for a stop until something else wakes the session.

A teammate in a terminal pane of its own is listed as `running` or `idle` by what it last
wrote in its team's roster, never `waiting`, so the plugin cannot tell that its own shells
or monitors still run.

**Each agent is named once.** An agent the model was told about and did not stop is
treated as kept, and later reminders leave it out. Its waking and going idle again on its
own does not bring it back, and neither do other agents joining or leaving the set; an
agent leaving adds nothing to the reminder. When the main conversation next sends that agent a
message, it has new work, so its next idle or finished state is named once more. If Claude
Code cannot list its agents at that moment, the message is not matched to the agent, and
its next stop is not named. The record holds
agent ids, not names, so a new agent that takes a named agent's name is named. A kept
agent stays on the status line, named while idle and counted once done or failed, and
`/tidy` still stops it
([ruled 2026-11-15](../../docs/architecture/decisions/2026-11-15-bbs-quiet-agents-names-agents-once.md)).
The text assumes `denubis-hook-question-zone` is installed, which registers that tool.

**The answer-only guard.** Only a turn that ended with an answer names agents for the
reminder. A turn the person interrupted, a refusal, or an API error names no one. Those
turn ends still update the status line.

**`/quiet-agents mute`.** For an agent you keep that runs, goes idle and runs again on its
own, type `/quiet-agents mute <agent>`, by its name or id. Until you type
`/quiet-agents unmute <agent>`, or the agent is stopped (at the next turn end Claude Code
lists it as `killed` or no longer lists it), the plugin leaves it out of the next
prompt's idle names and the end-of-turn reminder, names it as `muted` on the status line
(for example `agents idle: helper; muted: shepherd`), and leaves it out of `/tidy`. A mute
silences only this naming. It changes nothing about which deliveries are queued or taken
out: the agent's messages and idle notices are handled as an unmuted agent's are. So an
idle notice with no report before it, which carries the answer of an agent that replied by
ending its turn, still reaches the model with the prefix, less its last sentence: for a
muted agent the plugin gives the model no prompt to stop it. That reading of the ruling is
the assistant's. An agent notice that arrives as a prompt names no agent the plugin can
match, so its context keeps that sentence even for a muted agent. `/quiet-agents mute`
alone lists the muted agents. The mute goes by
the agent's id, so a new agent under the same name is not muted, and neither is a stopped
agent later resumed under its id. Only you can mute: the
model has no tool for it
([ruled 2026-11-15](../../docs/architecture/decisions/2026-11-15-bbs-person-mutes-kept-agents.md)).
The command runs at once, even while a turn is in flight.

**`/tidy`.** Typing `/tidy` stops every idle, completed or failed agent, one at a time,
through TaskStop and the usual permission check. It then says which it stopped, which the
permission check refused, and which failed. Running agents, muted agents, and agents a
plugin started are left alone.

**Nothing is stopped automatically.** The plugin never calls TaskStop on its own. Agents
stop only when the person runs `/tidy` or the model calls TaskStop after a reminder, and
each stop goes through the permission check as usual.

The report marks, the idle list, the ids of the agents already named, the agents the
reminder still waits to name, and the muted agents' ids live in the session's state. They survive a reload of the plugin and start empty in a new session.
The first load of 0.1.3 reads what 0.1.2 stored as empty, so a teammate whose report was
already marked may have one more idle notice let through, and agents already named are
named once more.

## Not yet verified

- **The nudge of 0.1.2 and earlier has been observed live many times**: 105 nudges across
  14 sessions by 2026-11-15, counted from session transcripts. Those transcripts showed the
  repeated naming 0.1.3 removes. The answer-only guard has not been checked against them
  and is established by the plugin's tests only.
- **Naming each agent once, and keeping a named idle agent on the status line, have not
  been seen live.** They ship in 0.1.3, and the plugin's tests establish them. The documentation says a teammate in a terminal pane of its own
  goes by its address as its id, and that a respawn under the same name keeps that
  address. If both hold, such a teammate respawned after it was named is not named again
  until the main conversation sends it a message.
- **The reminder riding on the next prompt was seen live on 2026-11-15.** The turn end
  started no turn, and the reminder came once, as context beside the person's next prompt.
  That prompt also named the same agent on the line of agents that went idle, which 0.1.4
  now leaves out; that change has not been seen live. The reminder riding on a delivery
  from an agent has not been seen live, and neither has how a leading line on a
  teammate's delivery reads to the model; the plugin's tests establish the ride.
- **`/quiet-agents mute` was used live on 2026-11-15, and lost answers.** A muted agent
  that replied by ending its turn had each answer only in its idle notice, which the mute
  took out. 0.1.4 now leaves deliveries alone. A live retest the same day saw the
  correction once: by a test session's report, which the person pasted in, a muted
  agent's answer came through, and the line in front of it no longer told the model to
  stop the agent. That retest did not show a muted agent left out of the reminder. The
  plugin's tests establish the rest.
- **Leaving out a `waiting` agent has not been seen live.** It ships in 0.1.4 and relies
  on the documented `waiting` status ("on background work it owns, on a plan's approval
  or, in a background subagent, on an Agent call alone"). Which of these puts an agent
  there in practice, a background subagent's shell or monitor or a teammate's, has not
  been observed. The plugin's tests establish the rest.
- **Recognising a teammate in its own pane by the agent list has not been seen live.** It
  relies on the documented listing of such teammates by name. The plugin's tests
  establish the rest.
- **The mark set at an agent's send has not been seen live.** It ships in 0.1.1 and stays
  unobserved until that release is installed. It relies on the documented `session.send`
  event for a send from an agent's own loop. The plugin's tests establish its behaviour.
- **Which hook clears the report mark is not known.** Both the `session.send` hook and the
  SendMessage `tool.call` hook clear it, and whichever runs second finds nothing left to
  clear. The `session.send` documentation describes a plain-text message, while
  SendMessage also carries plan approvals and shutdown requests, which only `tool.call` is
  known to see. A live session has not shown which of the two fires.
- **The muting of repeated notices runs on a path not yet seen carrying a notice.** In
  the observations this plugin was built from, teammate reports and idle notices arrived
  as deliveries, not as prompts. The prompt-side matching is derived from the type
  documentation.

## Install

At the prompt of a Claude Code terminal session:

```text
/plugin install denubis-hook-quiet-agents --marketplace Denubis/denubis-plugins
```

With the `denubis-plugins` marketplace already added:

```text
/plugin install denubis-hook-quiet-agents@denubis-plugins
```

The plugin needs a Claude Code build that loads mods. It was written against the mods API
of Claude Code 2.1.309 and tested with 2.1.310. The teammate parts need agent teams.

## Development

```bash
claude plugin validate plugins/denubis-hook-quiet-agents
claude plugin test plugins/denubis-hook-quiet-agents
```

The top-level `tsconfig.json` extends `.claude-plugin/types/tsconfig.json`, which Claude
Code writes, and keeps out of git, only when it loads this folder as a mod under
development (`claude --plugin-dir`). Elsewhere, type-check with a config kept outside the
plugin folder that includes the `claude-code.d.ts` your build writes for the
plugin-authoring skill, plus this folder's `hooks`, `types` and `tests`.
