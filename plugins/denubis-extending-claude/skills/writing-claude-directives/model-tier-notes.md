---
name: model-tier-notes
description: Current Claude model roster, dispatch boundaries, and directive-writing differences
last-verified: 2026-08-12
---

# Current Claude model guidance

This is the current reference for model-dependent directive choices. Recheck the linked
vendor pages when a model alias or product surface changes.

## Current roster

| Role | Model | API ID |
|---|---|---|
| Highest available capability | Fable 5 | `claude-fable-5` |
| Complex agentic and judgement work | Opus 5 | `claude-opus-5` |
| Default dispatch tier | Sonnet 5 | `claude-sonnet-5` |
| Fastest tier; unsanctioned here | Haiku 4.5 | `claude-haiku-4-5-20251001` |

Source: <https://platform.claude.com/docs/en/about-claude/models/overview> (verified
2026-08-12).

## Operator boundaries

### Dispatch floor

Sonnet is the lowest sanctioned dispatch tier. Default agents and subagents to Sonnet;
use Opus when the task needs deeper judgement. Haiku has no sanctioned dispatch site.
`haiku-general-purpose` remains a legacy callable definition and requires a new human
ruling before use.

Authority records:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/f7df1451-ba25-41cb-a76b-6deb33e53dad.jsonl:329`
  (`cc-search-chats context 0f4e9cd4-8cbd-4e40-866e-d7a69a35731c --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/28ff5c79-c20e-4039-bd82-c4ed1478bce3.jsonl:916`
  (`cc-search-chats context ece0feb2-ffbd-4f4e-a466-1a5120d1ce46 --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/28ff5c79-c20e-4039-bd82-c4ed1478bce3.jsonl:1116`
  (`cc-search-chats context 4766cd4c-359f-4644-a9b9-6baae0e43796 --json`)

### Fable cost gate

Fable work is human-triggered only. No skill, agent, hook, command, or unattended run may
auto-dispatch it. The Fable consultation skill therefore disables model invocation.

Authority record:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/e4421bb3-2615-4b37-944c-86e5dd65eccc.jsonl:12`
  (`cc-search-chats context 0a1beea2-2d45-455f-9ced-9ec278afb8e8 --json`)

### Advisor selection

Do not configure Sonnet as an advisor. Use Opus when an automated advisor is warranted.
Fable remains subject to the human-triggered cost gate.

Authority record:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/3c2ab09a-2af3-4252-9dc6-5d7d7b449b8d.jsonl:225`
  (`cc-search-chats context c23e1e60-9f9b-4169-8399-eda3d29c073f --json`)

The Claude Code advisor is experimental. It currently does not offer Fable as an advisor,
and subagents inherit the configured advisor subject to their own model-pairing check.
Recheck the table before changing configuration. Source:
<https://code.claude.com/docs/en/advisor> (verified 2026-08-12).

## Directive-writing differences

### Fable 5

- Prefer intent, boundaries, and success conditions over inherited step-by-step
  scaffolding. Ground progress claims in tool results.
- Do not ask it to reproduce internal reasoning; ask for evidence and conclusions in the
  output.
- It delegates readily. State when delegation is appropriate and cap it where cost or
  ownership matters.

Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5>
(verified 2026-08-12).

### Opus 5

- Do not request generic self-critique, double-checking, or a separate verification
  performance. Bind completion to external evidence and ask for a correction only when it
  changes the user's code, conclusion, or decision.
- Constrain scope and delegation explicitly. Calibrate visible response length directly;
  effort controls thinking cost, not prose length.
- Default effort is `high`; use `xhigh` for demanding coding or agentic work after a real
  need is established.

Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5>
(verified 2026-08-12). The operator observation about performative self-critique is bound
as `IC04` in `deployment/instruction-control/foa4008439/candidate-manifest.json`; inspect
that raw record with the manifest's source verifier.

### Sonnet 5

- State scope explicitly: at lower effort it follows the literal request rather than
  silently generalising it.
- Default effort is `high`; use `xhigh` for the hardest coding and agentic tasks.
- Review prompts should request coverage and attach confidence/severity as metadata; vague
  instructions to be conservative can suppress reported findings.

Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5>
(verified 2026-08-12).

### Haiku 4.5

No local directive should route work to Haiku while the dispatch-floor decision remains
active. Vendor capability claims do not revise that human boundary.
