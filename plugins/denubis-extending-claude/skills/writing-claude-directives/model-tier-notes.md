---
name: model-tier-notes
description: Per-model behavioural specifics for Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5 — referenced from writing-claude-directives SKILL.md
last-verified: 2026-06-10
---

_Last verified: 2026-06-10_

This file carries per-model behavioural specifics (effort levels, steerability notes, instruction-following characteristics, extended-thinking behaviour) for the current Claude tier: Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5. Opus 4.7 is retained below as previous-generation Opus (same API surface as 4.8). It is a supporting file for [`SKILL.md`](SKILL.md) in this skill — refresh cycles for model-specific claims decouple from the orchestrator file so model notes can be updated without touching the directive-writing guidance itself. If the dated header above is more than one model release behind current, treat every claim below as unverified and re-verify against the cited URLs.

## Fable 5

These are vendor-guidance summaries, except the cost gate below, which is an operator-empirical rule.

**Over-prescription degrades output:** Skills written for prior models are often too prescriptive for Fable 5. Anthropic's guidance: *"Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality."* A brief instruction steers Fable 5 as well as an enumerated list — reviewing and removing older step-by-step instructions can raise output quality rather than lower it. Directive authors targeting Fable 5 should prefer intent + constraints + trigger conditions over mechanical enumerations. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> (verified 2026-06-10).

**Reasoning-echo refusal risk:** Instructions that tell the model to echo, transcribe, or explain its internal reasoning as response text can trigger the `reasoning_extraction` refusal category on Fable 5, causing elevated fallbacks to Opus 4.8. Ask for evidence and justification *in the output*; do not ask the model to reproduce its thinking. If reasoning visibility is needed, read the structured `thinking` blocks instead. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> (verified 2026-06-10).

**Longer turns by default:** Individual requests on hard tasks can run for many minutes at higher effort; autonomous runs can extend for hours. Directive authors should account for this in client timeouts, streaming, and progress-indicator expectations, and should not write directives that assume a short turn. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> (verified 2026-06-10).

**Parallel-subagent affinity:** Fable 5 dispatches parallel subagents more readily than prior models and manages long-running subagents reliably. Directives can lean on delegation; provide explicit guidance about when delegation is appropriate and prefer asynchronous orchestration over blocking. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> (verified 2026-06-10).

**Memory-system affinity:** Fable 5 performs particularly well when it can record and reference lessons across runs. Directives for long-horizon work should provide a place to write notes — one lesson per file with a one-line summary at the top works well. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> (verified 2026-06-10).

**Cost gate (operator-empirical, 2026-06-10):** Fable-tier invocations are human-triggered only. No directive, skill, plan, or agent prompt may auto-dispatch Fable-tier subagents or schedule unattended Fable runs — they burn real money. Automated work routes to Haiku/Sonnet/Opus; Fable verification appears in test plans as a manual checkpoint.

**No advisor route to Fable judgement (protects the cost gate):** The advisor tool (beta `advisor-tool-2026-03-01`, tool type `advisor_20260301`) lets a cheaper executor consult a stronger advisor mid-generation, but it offers no cross-tier path to Fable. Per the model-compatibility table, a Fable 5 executor pairs only with a Fable 5 advisor, and no other executor may name Fable 5 as its advisor; an invalid pair returns `400 invalid_request_error`. So a cheaper automated executor cannot borrow Fable judgement through the advisor channel — the cost gate has no advisor-shaped bypass. Source: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool> (verified 2026-06-10). Operator-empirical evidence (2026-06-10, in session): Claude Code's `/advisor` set to Opus 4.8 under a Fable 5 session returned a live API error, verbatim: `400 tools.30.model: 'claude-opus-4-8' cannot be used as an advisor when the request model is 'claude-fable-5'`.

**Model ID (API):** `claude-fable-5`

## Opus 4.8

These are vendor-guidance summaries; no operator-empirical override is active for this model tier. Opus 4.8 keeps the same API surface as Opus 4.7 (adaptive thinking only; sampling parameters and `budget_tokens` removed) and performs well out of the box on existing Opus 4.7 prompts.

**Conservative tool/subagent/memory triggering:** Opus 4.8 favours reasoning over tool calls and spawns fewer subagents by default; it under-reaches for tools, subagents, and file-based memory unless reasonably sure they are needed. The fix is prescriptive trigger conditions in the description — state *when* to call a capability ("call this when the user asks about X"), not just what it does. This gives measurable should-call lift; louder language does not, and overtriggers other tiers (see Cross-model patterns). Raising effort is a secondary lever. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).

**Literal severity-filter following:** Opus 4.8 follows severity and confidence filters literally. In review harnesses, "only report high-severity issues" or "be conservative" makes it investigate just as thoroughly but report fewer findings — precision rises, measured recall can fall. For review harnesses, instruct it to report everything with confidence + severity and filter downstream (report-everything-filter-downstream), rather than self-filtering at the finding stage. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).

**Increased default narration:** Opus 4.8 provides more regular, higher-quality user-facing updates throughout long agentic traces. Forced-progress scaffolding ("after every N tool calls, summarize progress") is now counterproductive — remove it. If narration length or content is miscalibrated, describe the desired updates explicitly rather than forcing cadence. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).

**Literal instruction-following:** Opus 4.8 interprets prompts literally and explicitly, particularly at lower effort levels — it does not silently generalize an instruction from one item to another. If an instruction should apply broadly, state the scope explicitly ("apply this to every section, not just the first"). Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).

**Effort levels:** Opus 4.8 supports `low`, `medium`, `high`, `xhigh`, `max`. Anthropic's guidance: start at `xhigh` for coding and agentic use cases, minimum `high` for intelligence-sensitive work. It respects effort levels strictly, especially at the low end. Effort matters more here than on any prior Opus — re-tune it deliberately and run long-horizon work at `high`/`xhigh` with the full task spec given up front. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).

**Model ID (API):** `claude-opus-4-8`

## Opus 4.7 (previous-generation Opus)

Retained as previous-generation Opus. Same API surface as Opus 4.8 (adaptive thinking only; sampling parameters and `budget_tokens` removed); 4.8 inherits these behaviours and re-tunes them. These are vendor-guidance summaries; no operator-empirical override is active for this model tier.

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

**Operator-empirical note on judgement (2026-04-22 plan-amendment pass):** Haiku 4.5 is unsuitable for any task requiring judgement. This is the project's empirical position based on operator experience, and it overrides Anthropic's 2026-04 marketing framing of *"more consistent instruction following for nuanced tasks"* — that framing describes mechanical instruction-following, not evaluative or reflective judgement. Route judgement-heavy work (code review, proleptic challenge, coherence review, rubric application, scope decisions) to Sonnet 4.6 or Opus 4.8. Haiku 4.5 is appropriate for mechanical, bounded, low-judgement tasks only — which aligns with AbsenceJudgement.tex:868's three success conditions for AI-assisted work. This note retains and strengthens (does not retire) the structural principle encoded in `testing-skills-with-subagents`; Phase 3 of the upstream-sync plan reframes the SKILL.md-level Haiku-judgement passage with the same operator-empirical framing rather than removing it.

**Model ID (API):** `claude-haiku-4-5-20251001`

## Cross-model patterns

The current models (Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5) share several characteristics that matter for directive authoring:

- **Extended / adaptive thinking:** all support adaptive thinking; it is the recommended mode where applicable.
- **Prompting responsiveness:** all are highly responsive to prompting. Aggressive-language patterns (`CRITICAL:`, `YOU MUST`, `NEVER`) stacked on ordinary instructions can overtrigger current models — they read the urgency markers as content-signals rather than emphasis. Dial the tone back to direct-declarative phrasing. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-06-10).
- **Trigger explicitness beats emphasis:** the correct fix for under-triggering on Opus 4.8 and Fable 5 is plain, specific when-to-use conditions in the description ("Use when X", "call this when the user asks about Y"), which give measurable should-call lift — not louder language, which overtriggers Sonnet 4.6 and the Opus 4.6 tier. Put the trigger condition in the capability's own description, not just the surrounding prose. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).
- **Explicit-over-implicit:** all prefer explicit enumeration over implicit generalisation. Opus 4.8 and Fable 5 follow instructions literally and will not silently generalize from one item to another — state the scope explicitly. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).
- **Fable cost gate (operator-empirical, 2026-06-10):** Fable-tier invocations are human-triggered only. No directive, skill, plan, or agent prompt may auto-dispatch Fable-tier subagents or schedule unattended Fable runs — they burn real money. Automated work routes to Haiku/Sonnet/Opus; Fable verification appears in test plans as a manual checkpoint.
- **Advisor pairing for automated work (inside the cost gate):** the sanctioned quality lift for automated runs is pairing a Haiku 4.5 or Sonnet 4.6 executor with an Opus 4.8 advisor (beta `advisor-tool-2026-03-01`, tool type `advisor_20260301`). The advisor reads the full transcript mid-generation and returns a plan; it is billed at advisor rates per sub-inference, typically 1,400–1,800 tokens including thinking — cap it with `max_tokens: 2048` on the tool definition. This stays within the Fable cost gate (no Fable tier is touched). Claude Code exposes it per session via `/advisor`. Source: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool> (verified 2026-06-10).
- **Task budgets (cumulative cost bound):** for long agentic runs, `output_config.task_budget` (beta `task-budgets-2026-03-13`, minimum 20,000 tokens; Fable 5 / Opus 4.7 / Opus 4.8 only) gives the model a running token countdown it self-moderates against — a model-aware cumulative bound, distinct from `max_tokens` (an enforced per-response ceiling the model does not see). Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).
- **Effort parameter (per-turn cost lever):** `output_config.effort` (`low`/`medium`/`high`/`xhigh`/`max`) trades intelligence against latency and token spend, and matters more on the Opus 4.8 / Fable 5 tier than on prior generations — re-tune it deliberately. `xhigh` is Claude Code's default for coding and agentic use cases; a minimum of `high` suits most intelligence-sensitive work. Source: <https://platform.claude.com/docs/en/build-with-claude/effort> (verified 2026-06-10).

---

_When Anthropic releases new models or updated prompting guidance, re-verify each citation URL and update the dated header. The design plan's Additional Considerations note "Model-note staleness" is the authority for this maintenance pattern._
