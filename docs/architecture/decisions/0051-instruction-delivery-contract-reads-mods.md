# ADR 0051 — The instruction-delivery contract reads mods; quiet-agents' system-prompt section and its prompt context are permitted

**Status:** Accepted (2026-10-24 and 2026-10-25). Enforced by
`tests/test_instruction_delivery.py` from `cee8d18` (quiet-agents 0.1.1). Recorded first
in the untracked `.notes/decisions/0005`; moved here, with question 3's answer added,
2026-10-25.

## Authority evidence

Records in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl`.
"Human" marks an original human message; "dispatcher" marks the team lead's assistant
record, which puts a question and rules nothing.

Question 1, whether the contract extends to mods:

- Line 938, dispatcher, record `2fe501a7-874d-4be4-8a2e-459c186411c2`
  (2026-10-24T05:46:08.297Z), first putting it: "Should the contract extend to mods,
  which would mean the test learning to read hooks modules, or are mods outside its
  scope?"
- Line 963, dispatcher, record `f075a6dd-cadb-44b6-bba6-7db5572e1868`
  (2026-10-24T22:53:44.984Z), putting it again in plain words after the human wrote "I
  don't understand the question" (line 957), and recommending that mods stay outside the
  contract for now: "The question is whether that is fine, or whether the test should be
  taught to look at mods too."
- Line 974, human, record `7dcc4829-6d13-4c02-a8f1-2ea29083bf58`
  (2026-10-24T22:54:37.082Z): "ok, well, 1) how do we install this? 2)  yes, teach to
  look at mods. But let's go install, then see if you can drive a subagent?" Point 2
  answers question 1.

Question 2, whether quiet-agents may keep its two deliveries under the extended
contract:

- Line 1225, dispatcher, record `dbfde869-690a-4ff8-ae56-474ce9ef32cc`
  (2026-10-25T00:32:24.335Z), naming "the system-prompt section carrying the
  agent-hygiene rule" and "the context line attached to prompts ("these agents went idle
  since your last turn")", recommending compliance, and asking "Comply by dropping both
  deliveries, or exempt quiet-agents, and at what effort should Opus run it?"
- Line 1237, human, record `2e705937-f326-469e-b25c-9e95e1441cea`
  (2026-10-25T01:58:12.242Z): "I... system prompt adjusting in the plugin is fine. And
  context line is fine."

Question 3, whether "context line is fine" also covers quiet-agents' second context
string, the framing on a turn an agent notification started:

- Line 1308, dispatcher, record `d0de7416-85e0-4295-a313-c42fb9d29958`
  (2026-10-25T02:18:08.505Z): "your "context line is fine" was taken to cover both of
  the plugin's context strings. Say if you meant only the one naming idle agents."
- Line 1322, human, record `67512a84-9c30-40ab-9a7d-8d7ac59bacac`
  (2026-10-25T02:25:58.992Z): "well, commit. and yes, we inject what we need to make it
  work. Fix the housekeeping cleanup please. though uh, huh... ADRs should be in docs/
  because they need to be carried with the repo". "yes, we inject what we need to make
  it work." answers question 3. The last sentence is the ruling that moved this record
  into `docs/architecture/decisions/`.
- Line 1311, human, record `b3b55655-bf2d-43bc-b323-0693cf8f8b37`
  (2026-10-25T02:25:45.022Z): an earlier send of the same message's first three
  sentences, 14 seconds before line 1322 and with the same parent. It got no reply; the
  session continued from line 1322.

Exact raw-record resolver:

```sh
sed -n '938p;957p;963p;974p;1225p;1237p;1308p;1311p;1322p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl
```

## Context

The repository's instruction-delivery contract is enforced by
`tests/test_instruction_delivery.py`; among its checks, no marketplace plugin may run a
settings hook on every user prompt (`UserPromptSubmit`). Before `cee8d18` the test read
only hooks configured in settings, so it could not see hooks modules (mods).
quiet-agents, a mod, adds a system-prompt section at `prompt.compose` and attaches
context at `prompt.submit`, the mod counterparts of always-on and per-prompt delivery.

## Decision

1. The per-prompt and always-on instruction contract extends to mods (question 1).
2. quiet-agents' system-prompt section (`prompt.compose`) and its context attached to
   prompts (`prompt.submit`) are permitted (question 2).
3. The permission covers both context strings quiet-agents attaches at `prompt.submit`:
   the names of idle agents (`idleContext`) and the framing on a turn an agent
   notification started (`NOTICE_CONTEXT`), in
   `plugins/denubis-hook-quiet-agents/hooks/register.tsx` (lines 33 to 37 at
   `cee8d18`) (question 3).

## Consequences

- `tests/test_instruction_delivery.py` inventories mod hooks. A mod's `prompt.submit`
  context or `prompt.compose` section fails unless `PERMITTED_MOD_DELIVERIES` lists the
  plugin and door with this ADR as its authority. Listed: quiet-agents' `prompt.compose`
  and `prompt.submit`.
- The allowance is per door, so it covers every text that door delivers; question 3's
  answer confirms that reading for quiet-agents' two context strings.
- An allowance whose delivery is gone also fails, so no exemption outlives its subject.
