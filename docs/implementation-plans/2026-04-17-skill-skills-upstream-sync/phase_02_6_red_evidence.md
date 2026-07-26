# Phase 2.6 RED Evidence — Staleness Tripwire (static, preventive)

**Date:** 2026-06-10
**Restructure framing:** PREVENTIVE (staleness tripwire), per the 2026-04-22 amendment precedent recorded in `phase_02_red_evidence.md`. No transcript search required — the deficiency is the file's own dated header tripping its own rule, not an observed in-the-wild failure.

## The tripwire

`model-tier-notes.md` carries this rule (line 11, pre-edit SHA below):

> "If the dated header above is more than one model release behind current, treat every claim below as unverified and re-verify against the cited URLs."

The file's header reads **2026-04-17** and describes the **2026-04 tier: Opus 4.7, Sonnet 4.6, Haiku 4.5**. As of 2026-06-10:

- **Claude Opus 4.8** has shipped (current Opus tier; vendor prompting page exists and postdates 2026-04-17).
- **Claude Fable 5** has shipped (new tier above Opus; vendor prompting page exists and postdates 2026-04-17).

That is two model releases since the header date (Opus 4.7 → Opus 4.8, plus the new Fable 5 tier). By the file's own one-release rule, every claim below the header is now **unverified**. The file has tripped its own staleness wire. This is the RED state Phase 2.6 corrects.

## Two new model names entering scope

| Model | Tier | API model ID | Vendor prompting page (verified 2026-06-10) |
|---|---|---|---|
| Claude Fable 5 | new tier above Opus | `claude-fable-5` | <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> |
| Claude Opus 4.8 | current Opus | `claude-opus-4-8` | <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> |

## Pre-edit SHAs (Task 4 line numbers will drift once edits apply)

- `model-tier-notes.md`: `1b0ba8c5d6f3fd112a879efa9872c72ce4d4ded1` (67 lines)
- `SKILL.md`: `4c4399a585d0c1305372a4c7ca344ab4226911d5` (279 lines)

## Task 1 — source confirmation (no drift beyond noting)

The four cited URLs in the phase file's Sources section were fetched 2026-06-10 and confirm what `2026-06-10-rubric-for-rubrics-draft.md` (R3, R5, R7, R10 cost-gate) summarises. Verbatim confirmations:

1. **Prompting Claude Fable 5** — confirms AC2.6.3 verbatim: *"Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality."* Also confirms: the `reasoning_extraction` refusal category triggered by instructions to *"echo, transcribe, or explain its internal reasoning as response text"* (with elevated fallbacks to Opus 4.8); "Longer turns by default"; "Parallel subagents … dispatches parallel subagents more readily than prior models"; and the memory-system affinity (*"Store one lesson per file with a one-line summary at the top"*).
2. **Prompting Claude Opus 4.8** — confirms: *"It performs well out of the box on existing Claude Opus 4.7 prompts"* (same API surface as 4.7); conservative tool/subagent triggering (*"a tendency to favor reasoning over tool calls"*, *"tends to spawn fewer subagents by default"*) with the fix being explicit/prescriptive prompting and effort; *"More literal instruction following"* (*"does not silently generalize an instruction from one item to another"*); more narration by default (*"provides more regular, higher-quality updates … If you've added scaffolding to force interim status messages … try removing it"*); literal severity-filter following with the report-everything-filter-downstream remedy for code-review harnesses.
3. **Prompting best practices** — confirms aggressive-language dial-back is current guidance (*"The fix is to dial back any aggressive language. Where you might have said 'CRITICAL: You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'."*).
4. **Skill authoring best practices** — confirms *"Test your Skill with all the models you plan to use it with"* and the build-evaluations-first / evaluation-driven-development pattern, plus the frontmatter constraints (name ≤64 chars lowercase/hyphens, no reserved words "claude"/"anthropic", no XML; description ≤1024 chars, third person, what+when), TOC for reference files >100 lines, and the "old patterns" `<details>` block for time-sensitive content.

### Drift noted (not a contradiction; recorded per Task 1)

The **Prompting best practices** page attributes the aggressive-language overtrigger explicitly to *"Claude Opus 4.5 and Claude Opus 4.6"* and frames the dial-back as a 4.6-migration item. The rubric draft (R3) generalises the dial-back to "all models". The **Prompting Claude Fable 5** page corroborates the generalisation at the new tier (over-prescription degrades Fable 5 output; brief instructions steer as well as enumerations). So the generalisation is sound and confirmed by a second source; the narrower attribution on the best-practices page is a scoping nuance, not a contradiction. No HALT condition triggered.

## Tool-availability tripwire (R7) — operator evidence

`claudew` alias disables specific tools per session (operator evidence, 2026-06-10, recorded in `2026-06-10-skill-audit-campaign.md` Discarded findings). A directive that names a harness tool without an if-unavailable fallback misfires in any session where that tool is absent. This is the basis for the R7 addition to SKILL.md.
