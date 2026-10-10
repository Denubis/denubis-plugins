# ADR 0012 — Approvals are answerable from the side-monitor surface and from the pane; first answer wins

**Status:** Accepted (2026-10-09).

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 680, record `3ece6040-7f79-4485-aa97-93ac428a4c9d` (2026-10-09T01:58:59Z),
  answering ticket M2 as restated ("Option A: the side-monitor screen shows the request
  with the full command, and you can press y or n right there. Option B: the side-monitor
  screen only tells you this pane is waiting for an approval. A or B?"):
  "A, please, I'd like to manage extant approvals in one place. (Or as I'm alt <-> ing
  through them, but if I've got the big thing up, I'd like to be able to command from
  both"

Exact raw-record resolver:

```sh
sed -n '680p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

Earlier in the same session, the goal: "I don't care about picking, I care about seeing
the 'approve' requests in a new byobu terminal or app or... whatever I need."

## Context

The 2026-10-09 design fanout's function 7 (human surface) proposed a side-monitor view
that lists pending approvals with the full command and returns Brian's answer through
the vendor's held PermissionRequest hook, so no keystroke reaches the pane. Verifier 7
established from docs and field reports (claude-code#79651, #12176, remi#1126) that
Claude draws its pane dialog immediately and concurrently with a blocking hook, and that
answering at the pane does not cancel the hook. Codex already registers
PermissionRequest hooks in `~/.codex/hooks.json`. agy has no PermissionRequest event.

## Decision

- A pending approval from any vendor is shown on the surface with its full request and
  can be answered there. The answer is returned through the vendor's held hook as its
  typed allow or deny. The surface never types into a pane.
- The same approval remains answerable at the pane. Whichever answer arrives first
  settles it; the other place must then retire its copy. The mechanism is function 6's
  to build and test. The dispatcher's first wording named PermissionDenied as a Claude
  retirement signal; verification 06 and the synthesis (2026-10-09) corrected that from
  the Claude hooks documentation, which says PermissionDenied fires only in auto mode
  and not on a manual deny. PostToolUse covers a pane-answered allow; a pane-answered
  deny is learnt only at turn end (Stop or UserPromptSubmit) unless a live test finds
  an earlier signal. The ruling is unaffected.
- An intake hook may wrap the approver's existing Codex and agy entries and add a Claude
  PermissionRequest registration (proposal 06 Q4, answered by this ruling's "one place").
- agy approvals are shown only; they cannot be answered from the surface until agy
  exposes an approval hook.

## Consequences

- The first live test before implementation commits: with a PermissionRequest hook held
  on Claude 2.1.29x, confirm the dialog appears in the pane during the hold, and that a
  pane answer followed by hook retirement leaves no stale item.
- The existing `Notification` desktop ping in `~/.claude/settings.json` fires on every
  Claude dialog; whether it stays is an operator choice, not changed here.
- Not ruled: what "may drive" grants a supervisor (ticket M3), which bounds what a
  supervisor, rather than Brian, may answer.
