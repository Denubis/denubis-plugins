---
name: annotated-bibliography
description: Use to draft or revise annotated bibliographies with source evidence and interpretation checks.
---

# Annotated bibliography

Produce one source-grounded entry per resolved citekey, calibrated to the
project's question. Preserve what the source complicates or contradicts as well
as what it supports. A matching quotation does not validate its interpretation.

Load [using-bibliography](../using-bibliography/SKILL.md) for source preparation,
quote verification and note-write rules. Read the project brief, intended note
location and existing entries. Use [literature-scout](../literature-scout/SKILL.md)
if the task first needs new sources. Do not silently expand the source set.

## Prepare once

Resolve each source through the bibliography front door, then inspect its
`meta.json`, physical page files and extraction limitations. Re-render legacy
PyMuPDF/Docling caches before relying on their OCR flags or page assignments.
Give each source its own working entry and record the source hash. Do not copy
PDF text into a tracked project corpus or start another extraction pipeline.

Read [entry contract](references/entry-contract.md) before drafting and
[review and revision](references/review-and-revision.md) before verification.
For a large batch, pilot a few diverse sources first and keep a per-source
status/path list. Resume from artifacts that actually exist; an interrupted
worker is not a completed entry.

## Draft, check, review, revise

1. Read the whole source, including relevant tables and limitations, before
   selecting its main contributions. If only part is accessible/read, label the
   entry partial and identify that coverage. Do not write a whole-paper summary
   from an abstract or from another model's note.
2. Draft a summary, project-specific positioning, and salient points pairing a
   paraphrase with a short exact span and physical page. Carry conditions,
   denominators and qualifications with the claim. Add secondary caveats where
   needed; neither a word target nor a point quota justifies padding or omission.
3. Run the bundled checker against the resolved paper directory. A failure
   requires returning to the source or correcting the locator; never edit the
   source cache to make a quotation pass. A match establishes text presence only.
4. Give a fresh reviewer the entry, source cache/provenance and project question,
   without the drafting reasoning or desired verdict. It checks interpretation,
   summary and relevance, not merely the quotations. Delegate only when permitted.
   If fresh context is unavailable, report that limitation and leave independent
   review pending rather than claiming it occurred.
5. Re-read the source for every substantive correction. Apply, adapt or decline
   with evidence; a verifier is fallible too. Recheck changed quotations and
   return changed interpretations to review. Preserve unresolved disagreements
   and stop when resolving them requires new evidence or an author decision.

For OCR, inspect the matching physical PDF page before calling exact wording
verified. Record which span/page was inspected, by whom, and any discrepancy.
Uninspected spans remain candidates even after a successful text check. Printed
page labels require separate verification; never treat the physical file number
as the printed citation page by default.

## Deliver

Write entries to the project's chosen literature-note location, following
using-bibliography's note conventions (`ai-generated: true`, human `verified-by`
unset until actually verified). Keep the working entry and review dispositions
available for audit. Report source coverage, text-check count, OCR visual-check
state, interpretation-review state and any unresolved points separately. Link
the source and use only the resolver's exact citekey. Do not write to Zotero or
the central permanent-note collection without the corresponding authorisation.

Method provenance: [Shawn Ross's AB+ workflow](../../references/workflow-provenance.md).
