# ADR 0018 — Every session gets a ping that it has mail through its vendor's own channel, and pulls the body from the record; Claude-to-Claude mail goes through the record too

**Status:** Accepted (2026-10-09). Qualifies ADR 0011: native same-family
infrastructure carries supervision mechanics and the ping, not message content.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 908, record `1b2c1c14-2d5b-4ab9-8043-b2884c2c87cc` (2026-10-09T03:19:57Z),
  answering ticket M7 after the bypass-permissions half was dropped as moot ("watcher
  yes, or leave idle Claude sessions to the tmux path?"):
  "I mean, I'd prefer that mailbox pings be done through these things, rather than
  direct messages? but I don't understand the rest here."
- Line 918, record `8e3f7f73-2886-46c0-93db-673d2977cc59` (2026-10-09T03:22:26Z),
  confirming the restatement ("pings go through each vendor's native channel where one
  exists, bodies are pulled from the record, and typing into a pane is the fallback for
  a vendor with no channel. Is that the ruling?"):
  "yes, basically everything should get a ping that it has mail, so that it can choose
  when to check it, with whatever infra each thing uses. And preferably claude-to-claude
  also uses mail than whatever talking is going on"

Exact raw-record resolver:

```sh
sed -n '908p;918p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

Dropped as moot in the same exchange: a `crossSessionInbound: accept` setting for
Claude sessions in bypass-permissions mode. Brian: that mode "gets NO i/o. It's...
honestly that should never be run" (line 902, record
`4f3bfc23-6e72-459f-9efd-b566f7f54179`, same file; `sed -n '902p'`). No ruling was needed
because the mode is not used.

## Decision

- A message for any session is written to the record first. The session then receives a
  ping that mail exists, carrying the message id and subject, never the body, through
  whatever channel its vendor provides: Claude's cross-session socket and its hook
  system (a Stop-launched listener that wakes the session when mail for it arrives);
  Codex's hook system; agy's hooks where they fire. Where no channel exists or it fails,
  the guarded tmux actuator types the same one-line pointer into the pane.
- The session chooses when to read. Reading is a deliberate pull from the record
  (function 4's read tool), which is also where acknowledgement begins.
- Claude-to-Claude messages use the same path: record first, ping through the socket.
  Direct content-bearing messages between sessions (the SendMessage pattern) are not the
  design for mail. ADR 0011 still governs supervision mechanics and approvals for
  same-family pairs; this ADR governs mail content for all pairs.

## Consequences

- Function 3's Claude adapter order becomes: socket ping for a Claude sender, hook
  listener ping for any other sender, tmux pointer as fallback. The listener's wake
  behaviour on a fully idle session (hook exit code 2) is the first live test.
- Function 1's record holds every message including same-family ones; Brian's earlier
  ruling that a message present in transcripts is unimportant in Postgres still bounds
  retention.
- Agent teams and sub-agents inside one Claude session are not sessions for this
  purpose; their in-process traffic is untouched.
- The verifier for proposal 03 was stopped before checking the socket and listener
  claims against the docs; a re-verification restricted to documentation is owed before
  implementation.
