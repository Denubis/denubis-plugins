# ADR 0006 — Astra and Fable require explicit human model and effort selection

**Status:** Accepted human policy (2026-09-24); implementation awaiting live acceptance.

## Authority evidence

Original human messages in
`/home/brian/.codex/sessions/2026/09/24/rollout-2026-09-24T10-02-38-01a0d0b8-ab46-78a3-9e7b-0d0f7ed514f2.jsonl`:

- Line 382, message `msg_01a0d0cf-54c4-70e0-8464-50b339f35498`:
  "oh yeah, there should never be a case where automated chooses astra/fable without my specific invocation and a specific level to load at."
- Line 389, message `msg_01a0d0cf-9bd7-7100-bd4c-e0d7d0bff442`:
  "and I literally have to say something like \"Go run this at astra on medium\" -- no inference of \"oh I should use astra/fable\" for this."

Exact raw-record resolver, independent of chat-index freshness:

```sh
sed -n '382p;389p' /home/brian/.codex/sessions/2026/09/24/rollout-2026-09-24T10-02-38-01a0d0b8-ab46-78a3-9e7b-0d0f7ed514f2.jsonl
```

## Decision

An automated dispatcher may use Astra or Fable only when the human names the model and
effort for that particular task. Difficulty, a request for review or a different model,
parent-model inheritance, and configured defaults cannot supply either selection.
If the human names the model but omits effort, ask for the missing level before launch.
Preserve the request in the scoped brief; do not increase the requested effort.

## Implementation and consequences

- Generic Codex delegation and external Codex review default explicitly to Sol/xhigh.
- Supervisor and review launchers reject Astra/Fable when effort is omitted.
- The Fable pane launcher requires both model and effort operands and forwards them.
- Shared routing, supervision, review, advisor, and model guidance carry the human gate.
- CLI argument validation proves explicit arguments, not that the human supplied them.
  Callers still own checking the actual human message and verifying live settings.
- No live Astra or Fable invocation is authorized by this policy record itself.
