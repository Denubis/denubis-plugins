# Architectural Decision Records

This directory holds short, dated records of architectural decisions whose
rationale would otherwise be lost. Format is loosely MADR (Markdown
Architectural Decision Records): each file has a status, context, decision,
and consequences section. One ADR per decision.

## Status lifecycle

- **Proposed** — decision drafted during implementation; awaits acceptance
  in the post-implementation review.
- **Accepted** — decision has been used and the post-acceptance pass
  promoted it from Proposed.
- **Superseded by ADR-NNNN** — kept for the audit trail; a later ADR
  records the change.

## Numbering

Four-digit zero-padded, in the order ADRs were authored. Numbers are
permanent and never reused; if an ADR is withdrawn, its number stays and
the body documents the withdrawal.

## When to write an ADR vs. a constraint row

- **Constraint row** (in `../constraints.md`): an enforced invariant the
  codebase tests for. Lives close to verification evidence.
- **ADR** (here): a decision whose rationale needs preserving across time
  — what was considered, what was chosen, what consequences followed. ADRs
  may pair with a constraint row that locks the same decision in code; the
  ADR captures the *why* and the constraint row captures the *how to verify*.
