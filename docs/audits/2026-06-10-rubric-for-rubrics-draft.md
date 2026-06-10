# Rubric-for-Rubrics — DRAFT 2026-06-10

A meta-rubric: the standard that directive-writing standards (writing-claude-directives, writing-skills, testing-skills-with-subagents, model-tier-notes) must themselves satisfy. Motivated by the requirement that every directive in this harness works on Sonnet 4.6, Opus 4.8, and Fable 5 simultaneously — main loop typically Fable, subagents Sonnet/Opus/Haiku.

**Status: DRAFT.** This document is reconciliation input for `skill-skills-upstream-sync` Phase 2, which owns writing-claude-directives. It does not authorise edits to that skill on main. Provenance convention follows model-tier-notes.md: vendor-guidance claims carry source URLs and verification dates; operator-empirical claims are dated and override vendor marketing where they conflict.

## R1. Declare the executor

Every directive names which model tier executes it (main-loop vs subagent, and which subagent model). A rule written for one tier silently misfires on another, so the audience must be explicit before any other rule applies.

- Vendor basis: "Test your Skill with all the models you plan to use it with" (skill-authoring best practices, verified 2026-06-10).
- Operator basis: Haiku-no-judgement position (2026-04-22, feedback_haiku-no-judgement.md) — judgement-heavy work routes to Sonnet or above.

## R2. Prescriptiveness budget scales inversely with executor capability

The same content needs three intensities:

| Executor | Register |
|---|---|
| Haiku | Exact steps, no judgement calls, validation gates after each step |
| Sonnet | Structured guidance; corrective phrasing works well |
| Opus 4.8 / Fable 5 | Intent, constraints, and trigger conditions; brief instructions replace enumerations |

Vendor basis: "Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality" (Prompting Claude Fable 5, verified 2026-06-10). A standard that mandates one fixed intensity for all executors fails this rubric. Where one skill serves multiple tiers, split mechanical steps (safe everywhere) from judgement latitude (model-gated), or state the floor model.

## R3. Trigger explicitness beats emphasis

When-to-use conditions are stated plainly and specifically ("Use when X", "Call this when the user asks about Y"). This is the correct fix for under-triggering on Opus 4.8/Fable 5 — not louder language, which overtriggers Sonnet 4.6/Opus 4.6+.

- Vendor basis: prescriptive trigger conditions in tool/skill descriptions give measurable should-call lift on Opus 4.8 (migration guide + prompting best practices, verified 2026-06-10); aggressive-language dial-back remains current for all models.

## R4. Imperative dichotomy (retain from skill-skills-upstream-sync)

Rhetorical emphasis (CRITICAL/YOU MUST stacked on ordinary instructions) is dialled back; true boundaries (irreversibility, secrets, data loss) keep the imperative. A standard must teach the distinction, not a blanket tone rule. (Already drafted on the branch; keep.)

## R5. No reasoning-echo instructions

Directives must not tell the model to echo, transcribe, or explain its internal reasoning as response text. On Fable 5 this can trigger the `reasoning_extraction` refusal category and cause fallbacks. Audit existing skills for show-your-thinking phrasing. Asking for *evidence and justification in the output* is fine; asking to *reproduce the thinking* is not.

- Vendor basis: Prompting Claude Fable 5, Recommended scaffolding changes (verified 2026-06-10).

## R6. Version-pinning discipline

- Model-specific claims live only in a dated supporting file (the model-tier-notes pattern), never inline in an orchestrator skill.
- Era-claims ("Claude 4.x models…") and benchmark numbers are banned — they age silently and mislead precisely when they sound most confident.
- Staleness tripwire: when the dated header is more than one model release behind current, every claim in the file is treated as unverified (model-tier-notes' own rule; as of 2026-06-10 that file has tripped its own wire — Opus 4.8 and Fable 5 postdate it).
- Legacy guidance that must remain visible goes in an "old patterns" collapsed block, not the main flow (skill-authoring best practices, verified 2026-06-10).

## R7. Tool-availability is environmental, not assumed

A directive that names a harness tool (AskUserQuestion, EnterPlanMode, Agent/Task, MCP tools) states the fallback when the tool is absent ("if unavailable, ask inline"). Tool rosters vary per session (operator evidence: the `claudew` alias disables specific tools, 2026-06-10). MCP tool references use the fully qualified `Server:tool` form.

## R8. Frontmatter and discovery constraints

- `name`: ≤64 chars, lowercase/numbers/hyphens, gerund preferred, no reserved words "claude"/"anthropic", no XML.
- `description`: ≤1024 chars, third person, "Use when…" + concrete trigger keywords (symptoms, file types, error strings), states both what and when.
- Vendor basis: skill-authoring best practices frontmatter validation (verified 2026-06-10).

## R9. Token economy with progressive disclosure

Body <500 lines; heavy reference in supporting files one level deep; TOC at the top of any reference file >100 lines; one excellent example over multi-variant dilution; single default with an escape hatch over option menus.

## R10. Test on every executor tier (RED first)

No standard ships without baseline failures observed (RED), compliance verified (GREEN), and loopholes countered (REFACTOR) — on each model tier that will execute it. Evaluations precede documentation. A skill passing on Fable but unread-able by Sonnet (or vice versa: tuned for Sonnet, over-prescriptive on Fable) fails the matrix, not the skill type.

- Bases: writing-skills (repo), testing-skills-with-subagents (repo), "build evaluations first" + "test with all models" (vendor, verified 2026-06-10).
- **Fable cost gate (operator rule, 2026-06-10):** Fable-tier invocations are human-triggered only — they burn real money. Automated RED/GREEN passes run on Haiku/Sonnet/Opus; Fable verification appears in test plans as a manual checkpoint. No directive, skill, plan, or agent prompt may auto-dispatch Fable-tier subagents or schedule unattended Fable runs.

## R11. Operator-empirical override channel

Vendor guidance is the default; recorded operator evidence overrides it where they conflict, and the override must be dated, filed (`.notes/feedback_*.md` or equivalent), and cited where applied. Precedent: Haiku-no-judgement (2026-04-22) overriding Anthropic's "nuanced tasks" marketing. The override itself is subject to R6 staleness review.

## R12. Living documents carry current truth; git carries the change history

A directive, standard, plan instruction, or note states its current position only — no amendment blocks, dated "we decided" markers, RESOLVED stacks, or passages arguing with earlier versions of themselves. Edit the content in place; the rationale for the change goes in the commit message. Exception: designated append-only audit artefacts (review verdicts, GREEN verifications, postmortems) are archives, must declare themselves as such, and are exempt. A single dated `last-verified` header is provenance metadata, not scar.

- Operator basis: `.notes/feedback_scar-tissue.md` (2026-06-10), maintenance register.

## Pending reconciliation items (for skill-skills-upstream-sync Phase 2 or successor)

1. model-tier-notes.md: add Opus 4.8 section (under-triggering, narration defaults, ask-rate, literal severity filters, same API surface as 4.7) and Fable 5 section (prescriptiveness warning, reasoning_extraction, longer turns, parallel subagents, memory affinity); refresh dated header.
2. writing-claude-directives: fold R3 (trigger explicitness as the under-trigger fix) into the Compliance Techniques section the branch already rewrote; add R5 and R7 as new entries; align the description-writing section with R8 limits.
3. writing-skills: add Discipline to the skill-type table; add R10's model matrix to the checklist.
4. testing-skills-with-subagents: add per-tier testing requirement; remove its own dated-narrative violation.
