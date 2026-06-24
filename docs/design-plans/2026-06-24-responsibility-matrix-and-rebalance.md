# Responsibility matrix and rebalance spec: the plan / execute / review edifice

**Status:** Authoritative spec, 2026-06-24. Supersedes `2026-06-24-impl-plan-write-rebalance.md` (the proposal) and folds in its codex review (test/UAT ownership retained, pre-flight over a lightweight index, a plan-conflict verdict, terminal-review contracts, `using-bibliography` scoped). The current-state ("is") column is grounded in a four-investigator read of the actual skill files; cited line numbers were grep-confirmed against the files in this branch. The target-state ("should") column is design judgment, not yet implemented.

**Scope:** `impl-plan-write`, `executing-an-implementation-plan`, `requesting-code-review` + `agents/code-reviewer.md`, `exec-coherence-review` + `agents/coherence-reviewer.md`, `critical-peer-review`, `proleptic-challenger`, and the research path (`internet-researcher`, `using-bibliography`).

## Headline

The edifice already contains almost every piece the decision-discipline design wanted, distributed across existing skills. The rebalance is redistribution plus five borrowed mechanisms, not new scaffolding. The single most important constraint: the planner **keeps** ownership of `test-requirements.md` (`impl-plan-write/SKILL.md:1227`) and `uat-requirements.md` (`:1277`); leaning the planner down must not orphan them, because the executor and the UAT gate read them.

## One branch, not separable

The change is interlocking: the planner emits a plan index that the executor's pre-flight scan consumes, and the reviewers share one no-pre-judging discipline. These cannot land independently without leaving dangling contracts, so the work belongs on one branch (this worktree), not split across isolated branches.

## Responsibility matrix

One owner per concern. Owner = the skill or agent that produces the authoritative artifact or makes the call. Handoff = who consumes it. Human gate = where a human decides.

| Concern | Current owner (is) | Target owner (should) | Artifact | Handoff | Human gate |
|---|---|---|---|---|---|
| Genuine-fork discovery | impl-plan-write — three modes + three-lens, per phase | impl-plan-write — heuristic gate, batched | batched decision set in plan | executor pre-flight | yes: world-state forks only, batched |
| Run-it (experiment) | none; delegated to codebase-investigator | impl-plan-write discipline + codebase-investigator | findings | planner | no |
| Read-it (codebase/web) | impl-plan-write dispatches codebase-investigator + internet-researcher | unchanged | findings | planner | no |
| Read-it (academic) | not wired | internet-researcher identifies; using-bibliography reads corpus | rendered markdown | planner | yes: loading to Zotero is confirmed |
| Ask-it (world-state) | impl-plan-write, many gates incl. mode selection | impl-plan-write, world-state forks only, batched | answers recorded in plan | — | yes |
| Tradeoff articulation | impl-plan-write ("What it implies") | impl-plan-write, each side sourced to test/citation, pivot named | decision entry | human | yes |
| test-requirements.md | impl-plan-write (`SKILL.md:1227`) | impl-plan-write — UNCHANGED | test-requirements.md | test-analyst | optional approval |
| uat-requirements.md | impl-plan-write (`SKILL.md:1277`) | impl-plan-write — UNCHANGED | uat-requirements.md | exec-uat-gate | none (generated) |
| Lightweight plan index | none | impl-plan-write emits | index: global constraints + interfaces + decisions + phase summaries | executor pre-flight | no |
| Pre-flight conflict scan | none; executor strict JIT (`executing.../SKILL.md:12`, `:197`) | executing-an-implementation-plan, over the index | one batched question | human | yes: once, before Task 1 |
| Code defects | code-reviewer diff-scoped (`code-reviewer.md:8`, `:104`); requesting-code-review auto-dispatches fixer on any finding (`requesting.../SKILL.md:197`), one cycle, then HALT | unchanged scope + no-pre-judging + plan-conflict verdict | code-review-findings | bug-fixer / human | yes: plan-conflict + after re-review |
| Plan-mandated finding | none; flagged Critical and auto-fixed | requesting-code-review plan-conflict verdict | finding beside plan text | human adjudicates | yes: HALT before fix |
| Buried load-bearing decisions | coherence-reviewer "baked-in assumptions" (drift where design was silent) + critical-peer-review | same, strengthened — the wider net | coherence / critical reports | human | yes |
| Terminal review | critical-peer-review (Claude) | critical-peer-review + terminal codex-peer-review, with contracts | review reports | human | yes |
| Coherence with design | exec-coherence-review + coherence-reviewer | unchanged | exec-coherence-review.md | human | yes |
| Adversarial (proleptic) | proleptic-challenger, per phase | unchanged + eat-the-pudding binding | counterarguments | human | yes |
| Progress durability | executor resume prompt; no durable ledger | executor + durable ledger | ledger file | self (recovery) | no |
| File handoffs | executor, already as files | unchanged | scratchpad files | subagents | no |
| Model tiering | executor turn budgets; model via subagent defs | optional explicit per-role model | — | — | no |

## The five changes (the queue)

1. **`impl-plan-write` — lean and emit.** Replace the three modes and three-lens decision machinery with the heuristic gate: settle by run-it / read-it / ask-it, surface only forks that survive test and research, name the pivot (the human-held fact), and present the survivors as one batched set. Emit a lightweight plan index (global constraints, interfaces, decisions, phase summaries). **Keep** `test-requirements.md` and `uat-requirements.md` generation exactly as today.

2. **`executing-an-implementation-plan` — pre-flight and ledger.** Add a pre-flight scan that reads the **index** (not the phase bodies, preserving "Never load all phases upfront", `:12`) and surfaces conflicts and decisions as one batched question before Task 1. Add a durable progress ledger that survives compaction (a real delta: today only a paste-after-clear resume prompt exists, no ledger).

3. **`requesting-code-review` / `code-reviewer` — discipline and verdict.** Add the no-pre-judging rule: never instruct a reviewer not to flag an issue or to pre-rate a severity. Add a plan-conflict verdict that HALTs for human adjudication **before** the bug-fixer runs, because today any finding auto-dispatches the fixer (`:197`) and a plan deviation is auto-classified Critical with no adjudication path. Keep the diff scope (`code-reviewer.md:8`, `:104`).

4. **`coherence-reviewer` + `critical-peer-review` (+ terminal `codex-peer-review`) — the wider net.** Task them to hunt buried load-bearing decisions (data model, seams, state and lifecycle, external contracts, error strategy), building on coherence's existing baked-in-assumptions dimension. The terminal `codex-peer-review` carries explicit contracts: a disclosure precondition (the repo minus gitignored files goes to OpenAI), a provenance gate (quote-grep before believing it), a dedup policy against the Claude review, and a defined human path for conflicting findings.

5. **Research path — academic protocol and scope.** `internet-researcher` identifies papers (DOI), loading to Zotero happens behind confirmation, reading is via `using-bibliography`. `using-bibliography` reads papers already in the corpus; it is not a discovery engine.

## Residual risks and open questions

- The plan index is new surface. It must stay cheap to produce and cheap to scan, or it reintroduces the load-everything cost that JIT avoids. Its exact contents and a size bound need defining.
- The plan-conflict verdict adds a human gate mid-execution. It must batch into one question, not interrupt per finding, or it recreates the per-discovery thrash the batched pre-flight was meant to kill.
- The terminal dual review risks duplicating the per-phase reviews. The dedup contract is load-bearing, not optional.
- The run / read / ask plus articulate discipline is needed in both planning and review. Inline in each skill, or one shared sub-skill they both reference? Current lean: inline.
- Model tiering is optional and low priority; flagged, not scheduled.
