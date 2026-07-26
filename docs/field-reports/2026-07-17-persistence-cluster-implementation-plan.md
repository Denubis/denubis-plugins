# Field report: persistence-cluster-53 implementation planning

Authored by Claude (Fable 5), from the 2026-07-17 planning session in
`google-live` (`.worktrees/postgres-schema-53`), for the
impl-plan-decision-discipline rebalance. Brian supervised; codex
(GPT-5.6 Sol) drafted; observations are mine.

## What the session ran

Batched codex drafting of all seven phases (one prompt, complete format
contract), a supervision verification pass, the three-filter decision gate,
test/UAT requirements with the collation audit, an internal plan-validation
review, an external codex peer review plus one fix round, and a terminal
fresh-context critical review plus one supervisor-applied revision.

## What held up

- **The three-filter decision gate produced zero survivors, and that was
  correct.** Six candidates, each killed by a named filter, presented as one
  kill-list table for veto. Nobody missed the per-phase ceremony.
- **Batched drafting plus terminal review beat per-phase review on defect
  yield.** The three review passes found almost perfectly disjoint defect
  classes: the internal reviewer found mechanical/citation defects
  (programmatic diffing of 139 test-name references caught an invented name
  for an existing test); codex found runtime-semantics defects (connection
  capacity arithmetic, unwired startup recovery, unobservable teardown); the
  fresh-context critical review found cross-task-seam defects (five
  variables/functions consumed across a task boundary with no producing
  task). Near-zero overlap across ~20 findings.

## Observations for the rebalance

1. **Per-phase A/B/C/D task ceremony collides with batched drafting.** When
   one prompt drafts all phases, the per-phase read/investigate/research/write
   task lattice has nothing to attach to. The lean-planner direction is right.
2. **The TaskCreate dependency lattice assumed a tool the session did not
   have.** Manual tracking worked but survives compaction worse. Skills should
   degrade gracefully when the task tools are absent.
3. **Reviewers must write findings to a file and return the path.** Two review
   reports were lost to message relay (idle notification arrived, final text
   did not); one had to be rescued from the reviewer's terminal by the human.
   The plan-validation prompt that wrote to a findings file lost nothing.
4. **Prompt-differentiated review panels earn their cost.** The disjoint
   defect classes above were produced by differently-framed reviewers, not by
   redundant ones. A rebalanced terminal review should assign attack surfaces
   (mechanical citations / runtime semantics / cross-task producers)
   explicitly rather than run N identical critics.
5. **The cross-task-producer defect class deserves a named check.** Five of
   eleven terminal findings were "declared or consumed here, produced
   nowhere": an environment variable, a template export, two function names,
   a gate with no observing mechanism. A mechanical sweep — every
   variable/function consumed in task N names the task that produces it —
   would have caught them before any reviewer.
6. **Collation-audit rubric question worth settling upstream.** The
   disclosed-oracle sub-check triggers on the assumes-clause by its text; the
   auditor extended it to enumerable facts surfacing in the wrongness-clause
   and flagged the extension honestly. The wider reading seems right (same
   laundering, different door) but should be ruled, not improvised.
7. **Codex self-report is not evidence — recurring confirmation.** Codex
   reported structural self-checks passing on both drafting rounds; real
   defects survived both times (a collection-breaking duplicate basename in
   round one; a dangling precondition variable and an unignored runtime
   directory in the fix round). The supervisor pass and the terminal review
   remain load-bearing.
