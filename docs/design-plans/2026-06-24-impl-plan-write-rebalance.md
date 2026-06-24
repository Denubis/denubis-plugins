# Rebalance proposal: distribute the decision-discipline across plan / execute / review

**Status:** Proposal for external review, 2026-06-24. Companion to `2026-06-23-impl-plan-write-decision-discipline.md` (the arc design). This revises the earlier plan, which encoded the whole arc into `impl-plan-write`, in light of how the upstream lineage evolved.

## Context: what the lineage did

The planning skill's lineage is superpowers `writing-plans` → ed3d `writing-implementation-plans` → denubis `impl-plan-write`. superpowers kept `writing-plans` lean (about 174 lines) and pushed decision-adjudication and review rigor into a `subagent-driven-development` execution layer. denubis's `impl-plan-write` instead grew to about 1329 lines with three review modes, three-lens decision machinery, and UAT routing, and it is the thing that manufactured the "DR1–DR4" non-decisions this work set out to kill. The earlier arc design added *more* to `impl-plan-write`. This proposal rebalances toward superpowers' split.

(superpowers and ed3d live in read-only clones under `/tmp`, outside this repo, so their specifics here cannot be verified from this repo and should be treated as external claims.)

## The rebalanced decomposition

Distribute the arc's pieces across denubis's existing skills rather than cramming them into `impl-plan-write`:

- **`impl-plan-write` (trim to lean):** the plan itself, plus the three heuristics as a planning-time discipline — test what is testable (run it), research what is settled (read it, including academic papers via `using-bibliography`), else articulate the tradeoff — producing genuine decisions as one batched set. Borrow superpowers' structure: a Global Constraints block (spec values verbatim), Interfaces (Consumes / Produces) blocks, a No-Placeholders rule, and a short Self-Review checklist.
- **`executing-an-implementation-plan`:** the pre-flight batched plan review — scan the plan once, surface every conflict and decision beside the plan text that mandates it, as one question before Task 1. Plus the operational hygiene: file handoffs, a durable progress ledger, explicit model tiering.
- **`requesting-code-review` and the `code-reviewer` agent:** the challenger discipline — evidence-first, never pre-judge a finding ("if the prompt says 'do not flag' / 'at most Minor' / 'the plan chose', stop"), and plan-mandated finding = the human adjudicates (present the finding beside the plan text, ask which governs). The wider net that hunts buried load-bearing decisions lives here, not in the plan skill.
- **Terminal dual review** (`critical-peer-review` plus `codex-peer-review`) as the final-review tier of the execution skill, reusing that reviewer discipline, tasked to hunt buried load-bearing decisions (data model, seams, state and lifecycle, external contracts, error strategy).

Principle: the arc's *thinking* (run / read / ask, articulate tradeoffs) stays in planning; its *review and adjudication* move to the execution and review layer.

## What to borrow from subagent-driven-development

1. Pre-flight batched question — all conflicts and decisions surfaced once before Task 1, each beside its mandating text.
2. No pre-judging reviewers — the "if your prompt says 'do not flag' / 'the plan chose' / 'at most Minor', stop" rule.
3. Plan-mandated finding goes to the human to adjudicate.
4. Global Constraints as the reviewer's attention lens; Interfaces blocks for cross-task signatures.
5. Evidence rule leads positive — trust the report's test evidence, do not re-run or re-deliberate what is already evidenced.
6. File handoffs, progress ledger, model tiering.

## The decision discipline (planning-time)

Three channels settle any question, and speculation is none of them: run it (experiment), read it (literature), ask it (world-state only the human holds). A genuine fork is one that survives test and research; its pivot is usually a human-held fact. Each tradeoff is articulated with both sides sourced to a test result or a citation, never vibed. The planner's pickiness about what counts as a tradeoff worth surfacing is tunable, but the threshold must itself be research-grounded.

## Open questions

1. The run / read / ask plus articulate discipline is needed in both planning and review. Inline in each skill, or one shared sub-skill they both reference?
2. Container: this touches `impl-plan-write`, `executing-an-implementation-plan`, and `requesting-code-review` / `code-reviewer`. One worktree branch, or coordinate with concurrent plan-and-execute work?
3. Scope of the first cut: `impl-plan-write` only, or all three skills together?
