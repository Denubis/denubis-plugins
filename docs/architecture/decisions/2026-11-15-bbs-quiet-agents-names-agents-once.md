# ADR 2026-11-15-bbs-quiet-agents-names-agents-once — quiet-agents' turn-end nudge names each agent once

**Status:** Accepted (2026-11-15). Records a human ruling. Applied in
`denubis-hook-quiet-agents` 0.1.3. It replaces the nudge's set-difference trigger; ADR
0049 (the nudge fires only after an answered turn) still holds.

## Authority evidence

Claude Code session `18da81a1-f9a1-43b1-9c27-9278cca368df`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/18da81a1-f9a1-43b1-9c27-9278cca368df.jsonl`.
Times are UTC on 2026-11-15.

- Line 13, human, record `61c2a4f6-ed07-47cc-b326-40214d61b5a2` (01:11:34.862Z): "we need
  to change the quiet agents mod to not keep complaining about something kept around. (or
  increase the duration of timeouts or something) because sometimes there are
  long-running subagents and that's ok. Thoughts?"
- Line 229, human, record `303dad60-0c12-4b54-b325-c17cf6846fc4` (01:15:18.114Z), sent
  while the assistant was working: "I mean it's fine like after the second nudge to just
  have it ping a "write /tmp/nudge.foo.lock for agent foo to not be nudged about it
  again" or... just have exponential backoff or something?"
- Line 251, assistant, record `a426ff71-eb6f-4b8b-adb2-5986eefbe814` (01:16:06.137Z): the
  question as put through the question zone. Its context, then the question:

  > The quiet-agents plugin reminds the model, at the end of a turn, to stop idle or finished agents. Right now it re-sends that reminder whenever the list of such agents changes, so an agent you are deliberately keeping (for example a long-lived teammate that watches background jobs) gets named again and again. The proposed fix: name each agent once. If the model does not stop it, treat it as kept and stay quiet about it, until the main conversation next sends that agent a message (new work), after which its next idle period gets one reminder again. The status line and /tidy still show and stop kept agents. The alternatives were a lock file the model writes to silence one agent, or reminders that back off exponentially. Your answer decides which of these gets built.
  >
  > Should the reminder name each agent once and then leave it alone until the main conversation gives that agent new work?

- Line 262, assistant, record `d209ed2f-7f75-41b3-bdea-ee0b1fe0745f` (01:16:15.387Z): the
  proposal in chat, with the evidence below and the case against the lock file and the
  back-off.
- Line 265, human, record `f95cb105-4f9f-4355-af44-6a64a86c2165` (01:16:36.756Z): "yes,
  that's a good heuristic in your question"

- Line 1187, human, record `01b5b1a0-c899-419d-948a-fc3d93aba184` (02:06:13.573Z), a
  message sent while the assistant was working (a `queued_command` attachment). It quotes
  the question put through the question zone after the fresh review found that the line-251
  context's claim, that kept agents stay on the status line, was false for an idle agent
  whose idle notice the plugin had not taken out. The quoted context, then the question,
  then Brian's answer:

  > You approved the quiet-agents change so that its end-of-turn reminder names each idle or finished agent once and then leaves it alone until the main conversation gives that agent new work. When I asked, I said a kept agent would still show on the plugin's status line. That was partly wrong. The status line names only teammates whose idle notice the plugin swallowed after their report arrived, and counts finished and failed agents. An agent that is idle without having reported (for example a teammate that went quiet with no report, or one that went idle again after being given new work) appears nowhere on the status line, so after its one reminder it is invisible until you run /tidy, which still stops it. If you say yes, I'll extend the status line to name every idle agent that a reminder has already named. That is a small addition beyond what you approved. If you say no, I'll correct the plugin's notes to say such agents are not shown, and leave the status line as it is.
  >
  > Should the status line name every idle agent the reminder has already named, so a kept agent stays visible?

  Brian, verbatim: "yes"

Exact raw resolver:

```sh
sed -n '13p;229p;251p;262p;265p;1187p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/18da81a1-f9a1-43b1-9c27-9278cca368df.jsonl
```

## Context

From 0.1.0 to 0.1.2, each answered main-loop turn end gathered every idle, completed or
failed agent and nudged the model whenever that set differed from the set it last named,
naming the whole set. An empty set cleared the record. The nudge has no timer, so there
was no timeout to lengthen.

Observed in Claude Code transcripts on 2026-11-15, counting the nudge prompts the plugin
submitted in each main-session transcript that holds one:

- 105 nudges across 14 sessions; 33 named only agents already named earlier in the same
  session.
- In session `daf93e55-5471-427c-bbad-b086a5c4af8a`, in another project's transcripts,
  the teammate `shepherd`, kept on purpose to watch background jobs, was named in 13 of
  21 nudges. The model's replies included "The shepherd's job isn't finished … so I'm
  leaving it running." Lines 6428, 6453, 6474 and 6485 are four nudges in 19 seconds
  (01:08:54.878Z to 01:09:13.207Z), each naming `shepherd`. The nudges at 6474 and 6485
  fired only because another agent had just left the set.

## Decision

The turn-end nudge names each agent once. An agent a nudge has named, and the model did
not stop, is treated as kept and not named again until the main conversation next sends
that agent a message. After that message, its next idle or finished state is named once
more.

The status line names every idle agent a nudge has named, so a kept agent stays visible
(line 1187).

The lock file the model would write, and an exponential back-off, were proposed and not
chosen.

## Consequences

- Applied in `plugins/denubis-hook-quiet-agents/hooks/register.tsx`. The record holds the
  ids of the agents named (`nudgedIds`, under the shape tag `teammate-reports-5`), so a
  new agent that takes a named agent's name is named. `forget`, which runs at the main
  conversation's `session.send` and SendMessage `tool.call`, removes the recipient's ids.
- An agent leaving the set no longer raises a nudge, and a nudge names only the agents
  not yet named.
- A nudge that Claude Code dropped, or could not take, named no one, so its agents leave
  the record and are named at the next answered turn end.
- If Claude Code cannot list its agents when the main conversation sends one a message,
  the message is not matched to the agent's id, and its next stop is not named.
- An agent that wakes and stops on its own, with no message from the main conversation,
  is not named again. It stays on the status line, named while idle and counted once done
  or failed, and `/tidy` still stops it. Before this change the status line named only
  teammates whose idle notice the plugin had taken out.
- Established by the plugin's tests. Not yet observed live.
- The nudge's wording, the system-prompt section and the answer-only guard are
  unchanged.
