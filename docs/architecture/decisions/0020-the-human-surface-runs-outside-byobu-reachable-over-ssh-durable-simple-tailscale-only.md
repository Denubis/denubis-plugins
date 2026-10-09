# ADR 0020 — The human surface runs outside the main byobu session, is reachable from anywhere over SSH or Tailscale, is launched from a terminal on this machine, and is whatever is durable and simple

**Status:** Accepted (2026-10-09).

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`, answering ticket M9 (surface placement and
contents) in sequence:

- Line 1006, record `6253414c-970f-45dc-85bc-2059536be212` (2026-10-09T03:40:19Z):
  "side monitor screen runs preferably outside byobu, so I can run it on my home machine
  or this machine on a second monitor or on my phone?"
- Line 1019, record `bc1967a0-cbfa-4abe-9441-d68d2776a796` (03:40:38Z), after the
  dispatcher inferred a web app: "I mean, I've got ssh on my phone? I don't care if it's a
  webapp or tmux or whatever"
- Line 1033, a `queue-operation` record sent mid-turn (03:40:56Z): "whatever is durable
  and simple"
- Line 1047, record `a9606ba1-fbad-4bf0-bd83-95e4e40de844` (03:41:08Z): "and secure (but
  of course this will route only on tailscale so that should be fine)"
- Line 1063, record `dbe11221-d13d-4b05-8c5b-950bf294de59` (03:41:31Z): "and happy to
  launch it via terminal on this box"

Exact raw-record resolver:

```sh
sed -n '1006p;1019p;1033p;1047p;1063p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

Proposal 07 proposed a Textual terminal app in its own tmux session on the side monitor,
reattachable over SSH, and asked whether that or a window inside the main byobu session
was wanted. It also asked whether completions and crashes belong on the needs-Brian list.

## Decision

- The surface runs outside the main byobu session, as its own process launched from a
  terminal on this machine.
- It must be usable from a second monitor here, from Brian's home machine, and from his
  phone. Reach is over SSH or the Tailscale network; the technology is not constrained.
  A terminal app in its own tmux session satisfies this, and so would a web app.
- The choice between them is made on durability and simplicity, Brian's words, and the
  design records why the chosen one wins on those two.
- It is not exposed outside Tailscale. Whatever actions it offers (answering approvals
  under ADR 0012, replying to tickets, withdrawing mail under ADR 0015) are available only
  to a session Brian has opened over that network; a web variant needs its own login as
  well, because a browser tab is not a shell.
- Adopted default, not separately ruled: completions and crashes appear in the traffic
  view, not on the needs-Brian list (proposal 07 Q3; Brian did not address it and the
  proposer's default stands until he does).

## Consequences

- Function 7 chooses the implementation under the durability-and-simplicity test and
  states the reach test it passed (opened over SSH from a phone, actions taken, state
  consistent after reconnect).
- Verification 07 confirmed Textual 8.2.8 is current and already cached here, and that
  the tmux server runs one `main` session so a second session is possible; that is
  evidence for the terminal route, not a ruling for it.
- No ADR 0009 regression: the surface is a view of the record and a place to act; it
  never re-sends, counts a wait, or nags.
