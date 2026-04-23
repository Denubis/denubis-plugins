---
name: model-tier-notes
description: Per-model behavioural specifics for Opus 4.7, Sonnet 4.6, Haiku 4.5 — referenced from writing-claude-directives SKILL.md
last-verified: 2026-04-17
---

_Last verified: 2026-04-17_
_Amended 2026-04-22: operator-empirical Haiku-no-judgement framing added (see Haiku 4.5 section)._
_Amended 2026-04-23: Haiku-no-judgement assertion tightened with V4 constructs (Route judgement-heavy work / mechanical instruction-following)._

This file carries per-model behavioural specifics (effort levels, steerability notes, instruction-following characteristics, extended-thinking behaviour) for the current 2026-04 Claude tier: Opus 4.7, Sonnet 4.6, Haiku 4.5. It is a supporting file for [`SKILL.md`](SKILL.md) in this skill — refresh cycles for model-specific claims decouple from the orchestrator file so model notes can be updated without touching the directive-writing guidance itself. If the dated header above is more than one model release behind current, treat every claim below as unverified and re-verify against the cited URLs.

## Opus 4.7

These are vendor-guidance summaries; no operator-empirical override is active for this model tier as of 2026-04-22.

**Literal instruction-following:** Opus 4.7 interprets prompts more literally than Opus 4.6, particularly at lower effort levels. It will not silently generalize an instruction from one item to another — if the directive says "for tool X, do Y", the model will not extend "do Y" to tool Z without being told. Authors must enumerate cases explicitly rather than rely on the model to infer intent. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-04-17).

**Effort levels (first-class control):** Opus 4.7 supports five effort levels: `low`, `medium`, `high`, `xhigh` (new in 4.7), and `max`. Anthropic's current guidance: "Start with the new `xhigh` effort level for coding and agentic use cases." At `low` and `medium` the model scopes tightly and finishes sooner; at `xhigh` and `max` it reasons more, explores more alternatives, and uses tools less per unit of work. Directive authors writing prompts for Opus 4.7 should pick an effort level deliberately rather than leaving it to the default — the behavioural spread between `low` and `xhigh` is large enough to change how a directive reads in practice. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-04-17).

**Tool-use vs reasoning tradeoff:** Opus 4.7 uses tools less than Opus 4.6 and reasons more. Increasing the effort setting increases tool-use to a degree, but the default behaviour is reasoning-weighted. For agentic workflows that depend on tool-call cadence (e.g. Claude Code loops), authors should verify cadence empirically rather than assume parity with 4.6. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-04-17).

**Agentic focus:** Opus 4.7 is designed for long-horizon agentic work. It is better at refusing malicious agentic requests and at resisting prompt injection in Claude Code and computer-use settings than prior Opus releases. For directive authors, this means safety-framing instructions in directives ("refuse if X") are more reliable on 4.7 than on 4.6. Source: <https://www.anthropic.com/news/claude-opus-4-7> (verified 2026-04-17).

**Model ID (API):** `claude-opus-4-7`

## Sonnet 4.6

These are vendor-guidance summaries; no operator-empirical override is active for this model tier as of 2026-04-22.

**Steerability:** Sonnet 4.6 is more steerable than Opus 4.6. Corrective instructions — "do not do X", "always do Y after Z" — are more effective than on prior Sonnets. Directive authors can lean on corrective phrasing rather than scaffolding elaborate workarounds. Source: <https://www.anthropic.com/news/claude-sonnet-4-6> (verified 2026-04-17).

**Proactive default and GUI overtriggering:** Sonnet 4.6 has a proactive default: in GUI / browser-use settings it may show overly agentic behaviour (taking unsanctioned actions, clicking through flows the user did not authorise). Anthropic's framing: "aggressive behavior is much more steerable by prompting than Opus 4.6's equivalent" — so the mitigation is prompt-side, not a model-swap. Directive authors for GUI workflows should include an explicit "ask before acting" clause. Source: <https://www.anthropic.com/news/claude-sonnet-4-6> (verified 2026-04-17).

**Parallel tool-calling:** Sonnet 4.6 achieves parallel tool calling at roughly 100% with prompting guidance. Directives that benefit from parallel calls should explicitly invite them ("call these tools in parallel where possible") rather than assume the default. Source: <https://www.anthropic.com/news/claude-sonnet-4-6> (verified 2026-04-17).

**Adaptive thinking:** Sonnet 4.6 supports extended thinking and adaptive thinking (adaptive thinking is the recommended mode). Source: <https://platform.claude.com/docs/en/about-claude/models/overview> (verified 2026-04-17).

**Aggressive-language guidance:** Dial back "CRITICAL / YOU MUST" phrasing. See the aggressive-language section in [`SKILL.md`](SKILL.md) for the primary discussion and the before/after example. Anthropic's current position: *"The fix is to dial back any aggressive language. Where you might have said 'CRITICAL: You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'"* Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-04-17).

**Model ID (API):** `claude-sonnet-4-6`

## Haiku 4.5

**Instruction-following for mechanical tasks:** Claude Haiku 4.5 follows detailed mechanical instructions well — data extraction, structured output generation, tool-call loops, summarisation. Anthropic's 2026-04 announcement describes it as *"more consistent instruction following for nuanced tasks"*; the Anthropic framing is cited here as the upstream claim, but the scope under which that framing applies is bounded by the operator-empirical note below. Source: <https://www.anthropic.com/news/claude-haiku-4-5> (verified 2026-04-17).

**Context and extended thinking:** 200k total context, up to 128k extended-thinking budget, up to 64k output tokens. Directives for long-input summarisation or structured-output extraction can rely on this envelope. Source: <https://platform.claude.com/docs/en/build-with-claude/extended-thinking> (verified 2026-04-17).

**Safety profile:** Haiku 4.5 shows a statistically lower rate of misaligned behaviours than Sonnet 4.5 or Opus 4.1 per Anthropic's announcement. Source: <https://www.anthropic.com/news/claude-haiku-4-5> (verified 2026-04-17).

**Operator-empirical note on judgement (2026-04-22 plan-amendment pass):** Haiku 4.5 is unsuitable for any task requiring judgement. This is the project's empirical position based on operator experience, and it overrides Anthropic's 2026-04 marketing framing of *"more consistent instruction following for nuanced tasks"* — that framing describes mechanical instruction-following, not evaluative or reflective judgement. Route judgement-heavy work (code review, proleptic challenge, coherence review, rubric application, scope decisions) to Sonnet 4.6 or Opus 4.7. Haiku 4.5 is appropriate for mechanical, bounded, low-judgement tasks only — which aligns with AbsenceJudgement.tex:868's three success conditions for AI-assisted work. This note retains and strengthens (does not retire) the structural principle encoded in `testing-skills-with-subagents`; Phase 3 of the upstream-sync plan reframes the SKILL.md-level Haiku-judgement passage with the same operator-empirical framing rather than removing it.

**Model ID (API):** `claude-haiku-4-5-20251001`

## Cross-model patterns

All three current models (Opus 4.7, Sonnet 4.6, Haiku 4.5) share several characteristics that matter for directive authoring:

- **Extended / adaptive thinking:** all three support extended thinking; Sonnet 4.6's adaptive-thinking mode is the recommended default where applicable.
- **Prompting responsiveness:** all three are more responsive to prompting than pre-4.x generations. Aggressive-language patterns that helped older models (`CRITICAL:`, `YOU MUST`, `NEVER`) can overtrigger current models — they read the urgency markers as content-signals rather than emphasis. Dial the tone back to direct-declarative phrasing.
- **Explicit-over-implicit:** all three prefer explicit enumeration over implicit generalisation. Opus 4.7 is the most literal, Sonnet 4.6 and Haiku 4.5 are less strict but still more literal than 4.1-era models.

Common source for the prompting-responsiveness and aggressive-language points: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-04-17).

---

_This file is dated 2026-04-17. When Anthropic releases new models or updated prompting guidance, re-verify each citation URL and update the dated header. The design plan's Additional Considerations note "Model-note staleness" is the authority for this maintenance pattern._
