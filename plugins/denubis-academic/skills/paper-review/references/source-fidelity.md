# Cited-source fidelity lane

Use this reference for `SRC`. Its product is a project file named
`source-claims.md`: a pinpointed audit of whether each cited paper supports each
manuscript claim attributed to it. The pinpoints make the review auditable; they
do not imply that ordinary paraphrases need page locators in the manuscript.

## Freeze the claim-source inventory

Run `SRC` only after the Stage 2 gate has incorporated `ARG` omissions into the
canonical claim map. Include every source-dependent claim in scope and every
cited work presented as supporting it.

- Split a grouped citation into one claim-source pair per cited work.
- Split a sentence when its cited source is asked to support more than one
  independently assessable proposition.
- Preserve enough immediate manuscript context to disambiguate the attributed
  proposition.
- Do not silently treat a citation as decorative or as support for the whole
  surrounding paragraph. Mark an indeterminate claim-citation relationship
  `UNVERIFIED` and raise a placement concern separately.

## Prepare rendered sources on the orchestrator side

Load `using-bibliography` and follow its current workflow rather than copying
commands from this reference.

1. Resolve each work through its real citekey. Never construct or truncate a
   citekey. When only author/title/DOI evidence is available, use the resolver
   to discover the real key and then continue by that key.
2. Let the bibliography workflow reuse a quality-checked render or render the
   source once. Do not hand-extract a PDF or let lane readers re-render it.
3. Check the reported state, then prove that
   `papers/<citekey>/full.md` exists and is non-empty. Read `meta.json` and
   record renderer/OCR caveats.
4. Record the render path and provenance in `source-claims.md`. Lock or digest
   the rendered file when the local review protocol supports it.
5. If the source is absent, lacks a usable PDF, has an uncertain identity, or
   needs confirmation-gated OCR/fetching, record `UNVERIFIED`. Fetching or a
   gated OCR escalation requires the user's explicit confirmation. Do not
   improvise an internet fetch.

An inaccessible source has not failed to support a claim; it has not been
checked.

## Fan out by paper

Give one independent reader one rendered paper and all claim-source pairs
assigned to it. The packet contains:

- the exact real citekey;
- the `full.md` path and OCR note;
- each canonical claim ID, manuscript wording, normalised attributed
  proposition, paragraph ID, and short local context;
- the required result schema below.

Readers inspect only the supplied `full.md` and its sibling `pages/NNN.md`.
They do not query Zotero, fetch, convert, or re-render anything. Batch paper
readers within the available agent limit; the orchestrator reserves its own
slot and owns the canonical ledger.

For each pair, the reader must read enough of the paper to interpret the
pinpoint in context and search the full render before returning `NOT-FOUND`.
The nearest `<!-- page:N -->` marker supplies the physical PDF page. Recheck
the matching per-page markdown before finalising the evidence record.

## Return one evidence record per pair

Return:

- evidence ID placeholder, claim ID, paragraph and exact manuscript anchor;
- real citekey and resolved source identity;
- the precise proposition the manuscript attributes to this source;
- physical page or pages;
- a short verbatim source passage, or a precise source paraphrase when quoting
  would add noise;
- verdict and material source scope/qualification;
- strongest competing interpretation;
- confidence, search scope, and what would change the verdict;
- render/OCR caveat.

Use these verdicts:

- `SUPPORTED` — direct support at the manuscript's strength and scope;
- `PARTIAL` — support for only part of a compound proposition;
- `QUALIFIED` — broad support whose material conditions, limits, population,
  uncertainty, or scope the manuscript omits;
- `CONTRADICTED` — an incompatible source statement or result;
- `NOT-FOUND` — no support after inspecting the resolved readable source in
  full; include the strongest nearby passage and the search scope;
- `UNVERIFIED` — inaccessible source, unreliable render, unresolved identity,
  or ambiguous attribution.

Do not aggregate verdicts into a score. One weak source in a citation group is
not rescued by another source unless the manuscript clearly distributes the
claim between them.

## Synthesis boundary

The orchestrator writes verified raw results into `source-claims.md`, assigns
stable `SRC-E-nnn` IDs, and cross-links them to `ARG` and author-facing
findings at Stage 4. It may reconcile duplicate evidence but must not turn a
reader's `PARTIAL`, `QUALIFIED`, `CONTRADICTED`, `NOT-FOUND`, or `UNVERIFIED`
result into `SUPPORTED` without recording the new evidence.

Keep three questions separate:

1. Does the cited paper support the attributed proposition?
2. Is the citation placed clearly and attached to the right words?
3. Does the venue require a particular citation style or page locator?

`SRC` answers the first. `COH`/`REG` may answer the second and third. Internal
physical-page pinpoints remain required even when the answer to question 3 is
"no page locator for this paraphrase."
