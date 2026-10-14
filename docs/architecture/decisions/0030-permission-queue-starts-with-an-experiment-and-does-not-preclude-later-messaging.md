# ADR 0030 — Start with a permission experiment; later messaging is not precluded

**Status:** Accepted scope and experiment authorization (2026-10-14); implementation
and interaction remain to be tested.

## Authority evidence

Original human messages in
`/home/brian/.codex/sessions/2026/10/14/rollout-2026-10-14T14-18-06-01a1386a-d0ab-7f33-93bd-14b696a3edf3.jsonl`:

- Line 166, message `msg_01a1387c-614c-7313-8018-274f3d253f9a`:
  `the language is "not precluded"`
- Line 190, message `msg_01a1387d-df36-7fe3-81cf-a1b0b986f4f9`:
  "that works fine, the ... hrm... having a second byobu... alt-up/down... in a ... there will be some interesting ux here. But yes, go build an experiment with sol subagents. Your job is to be very critical and consider my ux. My current ux is tabbing through with alt left-right"

Resolver (both records have `payload.role = user`):

```sh
sed -n '166p;190p' /home/brian/.codex/sessions/2026/10/14/rollout-2026-10-14T14-18-06-01a1386a-d0ab-7f33-93bd-14b696a3edf3.jsonl
```

## Context

The October messaging synthesis includes mail, supervision, acknowledgement, identity,
and escalation machinery. It remains a draft. The immediate proposal was a small
permission/status board and, first, an approval round-trip experiment: capture a
request, answer centrally, and repeat with a native-pane answer first.

## Decision

- Build that experiment using Sol subagents and critically assess the interaction
  against Brian's existing Alt-Left/Right navigation.
- Later supervision and agent messaging must be **not precluded**. They are not
  infrastructure requirements for this experiment.
- Central and native-pane answers remain the intended interaction under ADR 0012.
  The experiment must distinguish returning a hook answer from observing its effect.
- The human has raised placement and navigation as a concern, not selected a new
  binding, session, server, or window arrangement.

## Consequences

The experiment may exercise isolated scratch approval requests needed for that
round trip. This does not authorize the broader draft's wake tests, deployment into
existing working sessions, or a change to live approval policy. Temporary fixture
transport is experimental evidence, not a second durable mail system. ADR 0026
continues to own the eventual database choice. Human interaction is still needed to
judge whether the resulting screen improves the current workflow.
