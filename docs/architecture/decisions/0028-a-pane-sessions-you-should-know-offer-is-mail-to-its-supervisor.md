# ADR 0028 — A pane session's "You should know" offer is mail from that pane to its supervising session; the offer is kept, not suppressed, and the sending pane is identified

**Status:** Accepted (2026-10-12). Applies ADR 0018 (record first, ping through the
vendor's channel) and ADR 0025 (identity follows the pane) to one new message source.
Interim carrier released as `denubis-external-agents` 0.24.0; the record sink waits on
ADR 0026's `agent_record`.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/09d5a455-3e7a-4091-ab59-2fe3bd675523.jsonl`:

- Line 292, record `d579824c-acda-439f-86e6-0c1b06c0ebc5` (2026-10-12T05:10:15Z), sent
  mid-turn while the dispatcher was preparing to test disabling the plugin per pane:
  "I mean, I don't actually mind those alerts, we just need to see them"
- Line 362, record `c9a78218-0024-4987-83cc-a7c46ad3efed` (2026-10-12T05:23:08Z),
  answering the question whether a pane's offer is mail to Brian or mail to the
  supervising session: "um, I'm so confused, but yes, if we have a way of bubbling these
  up to main, especially if we can identify the subagent, that's fine. it's mail to
  supervisor"

- Line 426, record `d0cc394c-3666-45dc-a3a5-9eced9f0581f` (2026-10-12T05:25:12Z), on
  whether to build a Stop-hook detector or wait for the mail infrastructure: "it's fine
  if we have some sort of hook that bubbles that up right now, but ultimately I do think
  I want this you should know offer to be part of mail proper, regardless. No point in
  building a mail thing that isn't part of the larger mail infra"

Exact raw-record resolver:

```sh
awk 'NR==292 || NR==362 || NR==426' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/09d5a455-3e7a-4091-ab59-2fe3bd675523.jsonl
```

## Context

Claude Code bundles a builtin plugin, `cc-plugin-you-should-know` (shown as "You should
know" / "Heads up"), that forks a tool-less side agent on the session's own context every
sixth tool step of a turn and, when the side agent finds something consequential the
person likely missed, shows a one-line offer with an explanation above the prompt box.

Observed in the 2.1.296 binary on 2026-10-12 (minified source carved from
`~/.local/share/claude/versions/2.1.296`; labelled observed):

- The `turn.step` hook returns early when the step carries an `agentId`, so in-process
  Agent-tool sub-agents never produce offers.
- Brian's "subagent panes" are agent-team teammates: with `claudew` setting
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, Claude Code itself splits a tmux pane and
  runs `claude --agent-id <name>@<team> --agent-name <name> --team-name <team>
  --parent-session-id <lead> ...` there, recording the team in
  `~/.claude/teams/<team>/config.json` (`leadSessionId`; per member `name`, `agentId`,
  `tmuxPaneId`, `model`, `cwd`, `joinedAt`, `backendType: "tmux"`). No session id is
  passed or recorded; the teammate's transcript under `~/.claude/projects/<cwd-slug>/`
  carries `teamName` and `agentName` on its first records. Such a teammate process has
  no `agentId` in the plugin's sense and an interactive surface, so it receives full
  offers that nobody is watching. The stored offer found during the investigation came
  from teammate `gemini-files` of team `session-e957317c`.
- Each offer is written at show time to the shared store
  `~/.claude/plugins/store/cc-plugin-you-should-know_builtin-19776595df2c.json`, under
  `sessions[].view` with `kind: "offer"`, `line`, `explanation`, `shownAt`, keyed by the
  pane's session ID. The view is cleared after two further prompts; `seen` keeps the last
  80 offer lines without attribution.
- The plugin exposes no hook, setting, or environment variable for forwarding an offer.
  `CLAUDE_CODE_YOU_SHOULD_KNOW_DEBUG` only adds check counters to the same file.
- The "Chat in main session" choice fills the pane's own prompt box with "Here is a note
  offered by a side agent: …", which in an unattended pane sits until the next
  `send-keys` prepends it. This is the stuck prompt that prompted the investigation.

Brian's first instinct was to suppress offers in panes; he withdrew that at line 292.

## Decision

- A "You should know" or "Heads up" offer shown in a pane session is a message **from
  that pane** (its own identity, per ADR 0025) **to its supervising session**. It is not
  addressed to Brian; the supervisor decides whether to act on it or raise it.
- The offer is not suppressed in panes. Its line and explanation are the body; the
  sending pane (pane id, session ID, cwd, model where known) is carried with it so the
  supervisor can tell which supervisee produced it.
- Per ADR 0018 the body goes to the record and the supervisor receives a ping, never the
  body, through its own channel. Until the record (`agent_record`, ADR 0026) exists, an
  interim hook may carry the same item, and it must not create a second mail store: the
  offer is part of mail proper when mail exists, and nothing built in the interim is a
  parallel mail system (line 426).
- The interim detector is a hook in the **lead** session (`supervisee-offers.py`,
  PostToolUse only: the marketplace's standing gate in `tests/test_instruction_delivery.py`
  rules UserPromptSubmit out as an action boundary). It finds the team config whose
  `leadSessionId` is its own session, takes the tmux-backed members, resolves each one's
  session id from the transcript Claude Code wrote for it, reads the plugin's store for
  those sessions, and hands any unforwarded `offer` or `explained` view to the model as
  additional context naming the teammate. Forwarded keys live in a pane option on the
  lead's pane. Everything read is written by Claude Code; nothing is stamped, spooled, or
  watched by a daemon (`.notes/project_cross-provider-messaging-critical-review.md`: no
  epicycles). When the record exists, the same read becomes a record insert and the
  pointer travels by ADR 0018's channel.
- A session with no supervisor has no recipient under this ADR; whether its offers go to
  Brian's surface is not ruled here.

## Consequences

- The messaging design gains one message source whose sender is a pane and whose body is
  not model-written prose but a plugin artefact; the record's message schema must admit
  it (a `kind` or subject prefix is the implementer's choice).
- The hook depends on three undocumented layouts: the plugin's store, the team config,
  and the transcript's `teamName`/`agentName` fields. A Claude Code release that moves or
  reshapes the store is reported as "store unreadable" rather than swallowed; one that
  changes the team config or transcript fields fails silently, and the observations above
  are the checks to repeat.
- The two-prompt lifetime of the `view` bounds how late the lead may look. A lead that
  polls its teammates with tool calls reads on every PostToolUse; an idle lead reads at
  its first tool call after Brian next prompts. A teammate driven through two prompts
  while its lead is idle loses the view, though the line survives in `seen`.
- Only agent-team teammates are covered. A hand-launched pane, the `consulting-a-fable-advisor`
  spawner's pane, and a Codex-supervised Claude pane lead nowhere in the team config, so
  their offers stay in the pane until the record exists and gives them an address.
- Every session now runs this hook on every tool call; the cost is reading the team
  configs and an early exit when the session leads no team.
