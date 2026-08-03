# Author-facing promotion triage

Exhaustive review and a short author-facing report are compatible only when
coverage evidence is kept separate from promoted issues. A lane `CONCERN`, a
missing Toulmin relation, or a checklist trigger is evidence that something was
tested. It is not by itself an author-facing problem.

Raw lane and claim records default to `EVIDENCE-ONLY`. Never delete them merely
because they do not survive promotion.

## First promotion pass

For every candidate issue:

1. **Verify the current text.** Recheck the exact anchor against the source lock
   and follow its cross-references through the whole in-scope manuscript.
2. **Name the minimum defect.** State what the current text actually does, not
   the broadest implication a reviewer can construct. A trigger, unfamiliar
   choice, or possible alternative is not yet a defect.
3. **State a concrete consequence.** Identify the effect on validity, evidence,
   transparency, source fidelity, argument, self-sufficiency, central
   terminology, or materially costly flow. “Could be clearer” is insufficient.
4. **Test textual recovery.** Search for an on-page definition, qualification,
   distinction, rebuttal, or evidential boundary that resolves the concern.
   Recovery must be supplied by the locked manuscript, not an imagined intended
   premise. Apply genre locality: an abstract, definition, table, or other
   stand-alone unit may still fail when the reader must wait until a much later
   section to discover its evidential object.
5. **Respect review mode.** In `CRITICAL-FRIEND` and `ADVERSARIAL` modes,
   supported methodological, ethical, transparency, reporting, and
   source-fidelity failures are peer-review findings even when they would be
   outside a final copy-edit. Do not import a copy-edit-only “actual errors” bar
   to suppress them. The common requirement is evidence plus consequence.
6. **Choose a disposition.** Record `AUTHOR-FACING`, `EVIDENCE-ONLY`,
   `MERGED-INTO`, `BATCHED-INTO`, or `DEFERRED`, with a short reason and any
   parent record.

When a claimed contradiction becomes coherent under a boundary the manuscript
itself partly supplies, narrow the diagnosis to the missing or unstable boundary.
Do not preserve the stronger title merely because it sounds more consequential.

## Consolidate by response, not by lane

- Merge findings that require the same author decision or repair the same root
  defect. Preserve every contributing lane, claim, and evidence link.
- Batch local faults that need no separate author judgement, such as a group of
  unambiguous grammatical or terminology errors. Do not turn each one into a
  pointed question.
- Keep factual or source-access requests separate from authorial decisions. An
  evidence gap asks for evidence, not a prose preference.
- Promote a proposed cut only when it removes a complete unused branch,
  demonstrably costly repetition, or another concrete burden without removing
  a claim, warrant, qualification, or necessary orientation. Hypothetical word
  reserves and micro-cuts stay evidence-only unless the owner requests them.
- Maintain one canonical author-facing issue register. Retire duplicate
  feedback essays or queues with provenance links rather than making the author
  reconcile parallel presentations.

## One hostile recheck

After consolidation, run exactly one fresh hostile recheck over the survivors.
For each record ask:

- Is this still merely arguable, or does the locked text support a defect with a
  concrete consequence?
- Does the title or consequence overstate what the evidence establishes?
- Does textual recovery elsewhere in the manuscript resolve it at the required
  locality?
- Is it based only on an invited or speculative implication?
- Does another survivor require the same author decision?
- Can local faults be batched without hiding their anchors?
- Is it optional polish masquerading as a submission problem?

Demote, merge, batch, defer, or narrow any record that fails. Record the
disposition in the evidence ledger so coverage remains auditable.

There is no target count, target rejection rate, or target report length. A
large reduction can be correct, but it is an outcome of applying the gate, not
evidence that the gate worked. Stop after the one hostile recheck; further loops
risk optimising the report to its own rubric rather than reviewing the paper.

## Author-facing minimum

Every promoted issue must contain:

- the exact current-text anchor and linked evidence IDs;
- the minimum supported diagnosis;
- the concrete consequence;
- the strongest surviving competing reading;
- why the issue survived promotion and the hostile recheck;
- the required response class: `EVIDENCE`, `AUTHOR-DECISION`,
  `EDITORIAL-ACTION`, or `REVIEWER-LIMIT`;
- one pointed question only when authorial intent is genuinely required.

