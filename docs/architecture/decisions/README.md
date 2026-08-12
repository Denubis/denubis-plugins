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
- **Superseded by ADR-NNNN** — the replacement records the current decision. Retire the
  superseded document to Git or an explicit archive rather than layering corrections
  into a living decision.

## Numbering

Four-digit zero-padded, in the order ADRs were authored. Numbers are never reused. A gap
means that Git or an explicit archive holds a retired decision; it is not an invitation
to reconstruct the old argument in the living set.

## Decision-source integrity

Every accepted ADR identifies what selected the decision. When a human instruction or
approval selected it, include the raw source path and line plus an exact resolver
invocation that opens the original human message. Do not substitute a quotation,
paraphrase, model summary, or bare session identifier. When current technical evidence
determines the decision, label and cite that evidence without inventing human approval.

A missing, stale, ambiguous, or wrong-role source is an integrity defect. Repair it when
found or return the ADR to Proposed until a focused human invocation resolves it.

## When to write an ADR vs. a constraint row

- **Constraint row** (in `../constraints.md`): an enforced invariant the
  codebase tests for. Lives close to verification evidence.
- **ADR** (here): a decision whose rationale needs preserving across time
  — what was considered, what was chosen, what consequences followed. ADRs
  may pair with a constraint row that locks the same decision in code; the
  ADR captures the *why* and the constraint row captures the *how to verify*.
