# ADR 0027 — The default Codex model is whatever the latest Sol-class release is, at xhigh, read from the catalogue rather than pinned

**Status:** Accepted (2026-10-10). Released as `denubis-external-agents` 0.23.0.
Extends ADR 0006, which fixed the default at "Sol/xhigh" without saying how Sol is
resolved; the Astra/Fable gate in ADR 0006 is unchanged.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d8536e45-ac36-41df-a1f9-8b31a931af99.jsonl`:

- Line 72, record `be552cbc-0e37-4ac6-b609-88f1087046e2` (2026-10-10T03:02:53Z), on
  finding both runners pinned to `gpt-6-sol` after `gpt-6.1-sol` had shipped: "yeah,
  we don't... argh, how do we generalise this without needing to revise this each
  release but also without having multi-discovery steps?"
- Line 91, record `4e88a846-c1ca-43c0-af98-2707e9d7b5c7` (2026-10-10T03:03:50Z),
  answering the proposed rule (lowest-priority listed `-sol` slug from the catalogue
  `--spawn` already reads, fallback to the pinned constant, effort stays xhigh):
  "great"
- Line 568, record `63f3fc4c-9a64-4bec-99f6-d9f74cce7125` (2026-10-10T03:50:15Z),
  asked whether the rule should become an ADR: "great, commit and push please, and
  yes, the ADR is sol-class (opus class) at xhigh whatever the latest is is the
  default. Astra/Fable only on command, default medium."

Exact raw-record resolver:

```sh
awk 'NR==72 || NR==91 || NR==568' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d8536e45-ac36-41df-a1f9-8b31a931af99.jsonl
```

The last message's "default medium" for Astra/Fable is not recorded here as a ruling:
it conflicts with ADR 0006 ("If the human names the model but omits effort, ask for
the missing level before launch") and is an open ticket in
`.notes/project_open-questions.md` until Brian resolves the conflict.

## Context

`codex-peer-review.sh` and `codex_supervisor.py --spawn` each carried the literal
`gpt-6-sol`. A new Sol release therefore meant an edit to both, and until that edit
every review ran a model behind the one Brian had on hand. Resolving the model at run
time risked the opposite cost: a chain of discovery steps before each launch.

Observed on codex-cli 0.160.1 (2026-10-10): `codex debug models`, which `--spawn`
already reads to strip the queued-question tools (ADR 0010), lists each model with a
`slug`, an integer `priority` and a `visibility` of `list` or `hide`. `gpt-6.1-sol` sat
at priority 1, `gpt-6-astra` at 2, `gpt-6-sol` at 3, `gpt-5.6-sol` at 5; hidden entries
shared priorities with listed ones. The operator's `config.toml` named `gpt-6-astra` at
medium, which the runners deliberately do not inherit.

## Decision

- The default Codex model is the latest Sol-class release (the Opus-class tier), at
  `xhigh`. No slug is pinned as the default.
- "Latest" is read from Codex's own catalogue in the read `--spawn` already makes: the
  listed slug containing `-sol` with the lowest `priority`. Hidden entries, entries
  without a numeric priority, and other families are never candidates.
- `gpt-6-sol` remains as a fallback only when no listed `-sol` slug carries a priority
  or no catalogue can be read, and the output says `fallback` when it was used.
- `codex_supervisor.py --default-model` exposes the resolved slug alone on stdout, with
  the reason on stderr, and `codex-peer-review.sh` substitutes it when `--model` is
  absent, so both runners share one rule in one owner.
- An explicit `--model` still wins. Astra and Fable are used only on Brian's explicit
  command, per ADR 0006.

## Consequences

- A new Sol release is picked up by the next spawn or review with no edit to the
  plugin. A Sol release that is hidden, unprioritised, or renamed out of the `-sol`
  family falls through to the fallback, and the `fallback` line is how the operator
  learns that the rule has stopped tracking.
- The `priority` ordering is observed, not documented by OpenAI; nothing guarantees it
  tracks release order. If a lower-priority older Sol ever appears, the rule would pick
  it, and the printed slug is the check.
- The widget-stripping evidence in ADR 0010 was measured on `gpt-6-sol` only; the
  current default `gpt-6.1-sol` is unverified there.
- Tests: `tests/test_codex_supervisor_default_model.py` (the rule, every no-candidate
  case, spawn and verb wiring, fallback reporting) and the catalogue cases in
  `tests/test_codex_peer_review.bats`.
