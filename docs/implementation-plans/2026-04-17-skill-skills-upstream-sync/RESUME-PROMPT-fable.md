# RESUME PROMPT — Fable external review pass + Phase 5 finalization

**Branch:** `skill-skills-upstream-sync`
**Worktree:** `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync`
**Written:** 2026-07-09.

## Where things stand

Phase 5 (terminal) of the skill-skills-upstream-sync plan. The **codex** external
review-and-fix cycle is DONE and committed. Resume here to run the held **Fable**
pass, fold its findings in, then finish Phase 5 (packaging + audits + ADRs).

Codex reviewed the 5 substantive touched skills (whole-file fitness, 3 axes), all
provenance-gated. 10 findings fixed + committed (below); 4 dispositioned won't-fix
with reasons. Working tree clean except two parked untracked audits.

The 5 codex-fix commits:
- `cdedacd` fix(epistemic-humility): restore 90%+ threshold, scrub plan-vocab, add fail-routing
- `b4c87e0` fix(testing-skills): harden RED-baseline gate, add AskUserQuestion fallbacks
- `711434e` fix(writing-claude-directives): hedge unprovenanced claims, add rubric/testing pointers
- `d5a0f5b` fix(writing-skills): reorder Iron Law workflow so RED precedes authoring
- `0293bdb` fix(impl-plan-write): reconcile UAT write-path

## FIRST ACTION — run the Fable pass

The cost gate is satisfied — a human started this session. **Pin `model: "fable"` on every review subagent.**

**Mode: independent.** Review subagents see the skills blind — no codex findings in their
prompts; the blindness is what buys a second voice. Codex re-enters at synthesis: weigh
Fable's reports against codex's findings and won't-fixes when deciding what to act on.

Spawn **one subagent per skill** via the Agent tool. Codex's 3 axes, plus a fourth:
1. Does the skill do its job in its plugin?
2. Did the branch's changes make it more effective?
3. Does it follow the project's own skill-authoring protocols (writing-skills orchestration,
   writing-claude-directives phrasing, testing-skills pressure-testing, epistemic-humility rubric)?
4. Scar tissue: does the skill argue with its own past selves — change-log residue, relitigated
   decisions, hedges against superseded versions? A skill presents the world we care about;
   history lives in git.

Ask for structured findings: severity + `file:line` + verbatim quote + why + suggested fix.

**Scope (post-fix files):**
- `writing-claude-directives/` — SKILL.md + model-tier-notes.md + long-running-state-patterns.md + graphviz-conventions.dot
- `epistemic-humility/` — SKILL.md + absencejudgement-citations.md + self-application.md
- `writing-skills/` — SKILL.md + anthropic-best-practices.md (obra-vendored) + render-graphs.js + README.md + examples/CLAUDE_MD_TESTING.md
- `testing-skills-with-subagents/SKILL.md`
- `impl-plan-write/SKILL.md` — review it, but deliver any fixes as a note into the
  `impl-plan-decision-discipline` worktree (the impl-plan teardown); no impl-plan-write
  fixes on this branch

Small plan-and-execute deltas (proleptic-challenger.md, design-write, exec-refactoring-rubric,
exec-uat-gate, systematic-debugging) ride along in context — no dedicated runs. Exclude
plan-artifact docs + repo infra.

**Verify quotes before acting** — spot-grep a few (`grep -nF '<quote>' <file>`). Any model can misquote.

## Discipline (carry-over — the operator was emphatic)

- **Overclaim is the through-line.** `epistemic-humility` exists specifically to curb Claude's
  tendency to overclaim (operator's words). Apply calibrated confidence to Fable's findings AND
  your own. Codex over-rated a mechanical heuristic to "High" (the model-tier finding); a year of
  model-family stability deflated it. **Lead with whether a finding is a REAL problem, not whether
  it trips a rule.** Do not inflate Fable's severity labels.
- **One finding at a time. Halt-and-discuss. No batch-fixing.** Discuss what each fix reveals before the next.
- **Won't-fix from codex — do NOT re-open unless Fable brings genuinely new evidence:**
  - model-tier behavioural "current models" claims (stable across 4.x + into 5; the freshness test
    is version-strings-only by design)
  - "usually" softeners (testing:36, WCD rubric-callback tail) — more accurate than the orchestrator's flat version
  - writing-skills checklist vs Anthropic's 3-evals/model-matrix — deliberate denubis method, not a gap
  - epistemic-humility scope-vs-examples — the four screens are general; the example is illustrative
- Codex reviews saved at `.review/SKILL.md.20260708-15*.REVIEW.md` for comparison.

## Remaining Phase 5 after Fable

1. **Package:** bump versions (denubis-extending-claude, denubis-plan-and-execute) + CHANGELOG.md
   + marketplace.json. **Read current versions from each `.claude-plugin/plugin.json`** — prior
   notes carried stale numbers. Coordinate the denubis-plan-and-execute bump with the
   `impl-plan-decision-discipline` worktree; both touch its versioning.
2. **Frustration audit (AC5.8)** — joint pass with the operator.
3. **Finalization ADRs (M2/M6).**

## Also open

- The two untracked `docs/audits/2026-07-02-*.md` are parked. **`skill-engagement-audit.md` awaits
  the operator's read.** Its verdict: enforcement ("teeth"), not prose, moves the compliance
  numbers — a separate design task, not this branch's.
- `systematic-debugging` "guarantees rework" / "guarantees bugs" hyperbole — left as discipline-skill
  register; operator to decide whether to hedge.

## Guardrails

- Commits on this branch only, never on main. Don't push without explicit approval.
- Don't `git worktree remove` this worktree from inside it.
