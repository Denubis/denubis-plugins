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

**The report-received rule.** When a teammate sends the main conversation a message, the
plugin marks the teammate as reported. If that teammate's idle notice arrives while the
mark stands, the plugin takes the notice out of the conversation: the model never sees it
and no turn starts. The mark lasts until the main conversation next sends the teammate a
message. From then on the teammate is working on something new, so its next idle notice
is let through. Only verified teammate messages to the main conversation count. The
teammate is the one the mailbox stamps, never the name the notice text claims.

**A one-line prefix for unreported idle notices.** An idle notice from a teammate whose
report has not arrived, or whose mark was cleared, reaches the model with this line in
front of it:

```text
[quiet-agents] An agent went idle. If this adds nothing the human has not been told, reply in one line or none; do not restate pending decisions. If its task is complete and you have no further work for it, stop it with TaskStop in this turn.
```

**Named once, at the next prompt.** The teammates whose idle notices were taken out are
named once, as context beside the next prompt that enters the conversation. A prompt
that is dropped before it enters leaves the names for the one after.

**Repeated notices are muted.** An agent notice that arrives as a prompt, such as a
background task's notification, is dropped when its text matches the last notice under
the same key, ignoring whitespace. A new or changed notice passes with context telling the
model that an agent, not the person, started the turn, and to answer in one line or not
at all when it adds nothing new.

**A hygiene section in the system prompt.** Each system prompt the plugin sees composed
ends with one short section: stop a finished agent with TaskStop in the same turn you
acknowledge it, and answer an empty agent notice in one line or none. An in-process
teammate's render of the lead's prompt does not get it.

**The status line.** The plugin's status line names the idle teammates and counts the
finished and failed agents, for example `agents idle: helper, scout; 1 done, 1 failed`,
or `agents: 1 done` when no teammate is idle. It updates when an idle notice is taken out,
when a message to an idle teammate takes it off the list, and at the end of each turn of
the main conversation. A teammate that is no longer listed, because it was stopped, drops
off at the next turn end.

**The turn-end nudge.** At the end of a main-conversation turn, the plugin gathers the
idle teammates and every listed agent that is idle, completed or failed. When that set is
not empty and differs from the set it last named, it queues one prompt, sent under the
plugin's name and not as the person's words, which starts once the session is idle:

```text
quiet-agents: idle or finished agents: <names>. Stop each with TaskStop. Then work through the pending questions in .notes/project_open-questions.md with the user one at a time, first looking for the answer in .notes, docs/architecture/decisions, and prior chat logs, and asking only where no evidence settles it. Where an agent's work is unfinished, continue it instead.
```

The same set at the next turn end raises no second nudge. When the set empties, the
record clears, so the same agents coming back are named again. The text assumes the
project keeps its open questions in `.notes/project_open-questions.md`, as
`denubis-project-notes` does.

**The answer-only guard.** The nudge fires only when the turn ended with an answer. A turn
the person interrupted, a refusal, or an API error raises no nudge, so a plugin prompt
never jumps ahead of what the person meant to type next. Those turn ends still update the
status line.

**`/tidy`.** Typing `/tidy` stops every idle, completed or failed agent, one at a time,
through TaskStop and the usual permission check. It then says which it stopped, which the
permission check refused, and which failed. Running agents are left alone.

**Nothing is stopped automatically.** The plugin never calls TaskStop on its own. Agents
stop only when the person runs `/tidy` or the model calls TaskStop after a nudge, and
each stop goes through the permission check as usual.

The report marks, the idle list and the last nudged set live in the session's state. They
survive a reload of the plugin and start empty in a new session.

## Not yet verified

- **The nudge has not been observed in a live session.** Its behaviour is established
  by the plugin's tests only.
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
