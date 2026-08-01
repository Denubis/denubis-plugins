# Review records

Keep canonical records separate from author-facing feedback. Stable identifiers
survive line drift, revisions, disagreement, and re-review.

## Identifier forms

| Form | Meaning |
|---|---|
| `{unit}-Pnnn` | Paragraph or paragraph-equivalent unit |
| `{unit}-Cnnn` | Explicit, implicit, presupposed, or uncertain claim |
| `{unit}-{lane}-nnn` | Lane finding |
| `X-{lane}-nnn` | Cross-document finding |
| `SRC-E-nnn` | One manuscript-claim × cited-source evidence record |
| `PR-nnn` | Author-facing peer-review issue |

Assign IDs in reading order and never renumber them. Keep deleted items as
dated tombstones. Pair volatile line numbers with short verbatim anchors.

## Source-lock record

```markdown
## Source lock

- Review baseline:
- Outer repository/index state:
- Submodule or nested-repository states:
- Lock created:

| Path | Role | Status | Repository/commit | Bytes | SHA-256 | Rationale |
|---|---|---|---|---:|---|---|
| | | INCLUDED | | | | |

| Checkpoint | Checked at | Manifest verdict | Changed paths | Disposition |
|---|---|---|---|---|
| Before Stage 1 | | MATCH | — | — |
| After Stage 1 | | | | |
| After Stage 3 | | | | |
| After Stage 5 | | | | |
```

Use `EXCLUDED` only with a rationale and `BLOCKED-SOURCE` when required
material is unavailable. Digest every `INCLUDED` file; directory names and a
commit alone are not a content lock.

## Paragraph record

```markdown
## {PARAGRAPH ID} — "{opening-text anchor}"

- Source:
- Unit/heading:
- Function:
- Claims served:
- Service verdict:
- External context needed:

| Lane | Result | Finding IDs or rationale |
|---|---|---|
| ARG | UNREVIEWED | |
| APP | UNREVIEWED | |
| TRN | UNREVIEWED | |
| SRC | UNREVIEWED | |
| COH | UNREVIEWED | |
| SCAR | UNREVIEWED | |
| REG | UNREVIEWED | |
| CUT | UNREVIEWED | |

- Cross-lane convergences:
- Tensions or disagreements:
- Candidate feedback IDs:
```

## Claim record

```markdown
### {CLAIM ID}

- Paragraphs:
- Exact expression:
- Normalised proposition:
- Visibility: EXPLICIT | IMPLICIT | PRESUPPOSED | UNCERTAIN
- Type and role:
- Competing reading:

| Toulmin relation | Status | Content or linked claim IDs |
|---|---|---|
| Grounds | | |
| Warrant | | |
| Backing | | |
| Qualifier/scope | | |
| Rebuttal/reservation | | |

- Upstream dependencies:
- Downstream dependants:

| Implication ID | Proposition or target claim | Status | Assessment |
|---|---|---|---|
| | | STATED / ENTAILED / INVITED / SPECULATIVE / OVEREXTENDED / CONTRADICTED | |

| Trigger | Expected falsifying text | Search scope | Strongest recovery or competing reading | Result |
|---|---|---|---|---|
| MISSING / OVEREXTENDED / CONTRADICTED / N/A | | | | SUPPORTED / WEAKENED / FALSIFIED / UNRESOLVED / N/A |

- ARG verdict:
- ARG completeness: COMPLETE | INCOMPLETE
- Related findings:
```

## Source-claim ledger (`source-claims.md`)

Create this as a separate canonical file in the recorded review work directory.
Record one row for every source-dependent manuscript claim × cited-source pair;
split grouped citations. The physical page is required for the audit trail even
when the manuscript paraphrase does not require a page locator.

```markdown
# Source-claim ledger

- Review baseline:
- Claim-map version:
- Citation inventory version:
- `using-bibliography` authority loaded:
- Prepared at:

| Citekey | Resolved identity | Render state | `full.md` path | Digest/meta | OCR note |
|---|---|---|---|---|---|
| | | RENDERED / UNVERIFIED | | | |

| Evidence ID | Claim ID | Paragraph and anchor | Citekey | Proposition attributed to source | Physical page(s) | Source passage or precise source paraphrase | Verdict | Material scope/qualification | Finding ID |
|---|---|---|---|---|---:|---|---|---|---|
| SRC-E-001 | | | | | | | SUPPORTED / PARTIAL / QUALIFIED / CONTRADICTED / NOT-FOUND / UNVERIFIED | | |
```

Verdicts mean:

- `SUPPORTED` — the source directly supports the attributed proposition at the
  manuscript's strength and scope;
- `PARTIAL` — the source supports only some components of a compound
  proposition;
- `QUALIFIED` — the broad proposition is present, but the manuscript drops a
  material condition, limitation, population, uncertainty, or scope boundary;
- `CONTRADICTED` — the source states or demonstrates an incompatible result;
- `NOT-FOUND` — the resolved, readable source was searched in full and no
  supporting passage was found; record the strongest nearby passage and search
  scope;
- `UNVERIFIED` — the source, render, identity, or claim mapping could not be
  inspected reliably. This is not an adverse source verdict.

## Finding record

```markdown
### {FINDING ID} — {diagnostic title}

- Lane:
- Paragraph/claim IDs:
- Source anchor:
- Observed issue:
- Reader or validity consequence:
- Competing interpretation:
- Confidence:
- What would change the assessment:
- Status: CLEAR | CONCERN | UNCERTAIN | N/A
- Classification: {lane-specific classification} | N/A
- Promotion disposition: UNTRIAGED | AUTHOR-FACING | EVIDENCE-ONLY | MERGED-INTO | BATCHED-INTO | DEFERRED
- Promotion parent or batch:
- Promotion rationale:
- Hostile-recheck result:
```

`Status` is the common coverage vocabulary. `Classification` preserves a
lane-specific diagnosis and never substitutes for `Status`.

## Serial gate record

```markdown
## Stage {n} gate

- Source-lock checkpoint:
- Required lane ledgers:
- Unit coverage: COMPLETE | INCOMPLETE
- Claim/Toulmin coverage: COMPLETE | INCOMPLETE | N/A
- Claim/source coverage: COMPLETE | INCOMPLETE | N/A
- New canonical IDs assigned:
- Validity or dependency decision:
- Cross-lane links added:
- Disagreements preserved:
- Blocks, stale records, or contamination:
- Explicitly unreviewed cells:
- Decision: ADVANCE | RETURN-TO-LANE | ASK-OWNER | STOP
```

## Author-facing issue

```markdown
## PR-{nnn} — {short title}

- Status: OPEN
- Priority: P1 | P2 | P3 | P4
- Lanes:
- Location and exact anchor:
- Paragraph, claim, and finding IDs:
- Required response: EVIDENCE | AUTHOR-DECISION | EDITORIAL-ACTION | REVIEWER-LIMIT

### Issue
One precise diagnosis.

### Discussion
Why it affects validity, evidence, transparency, argument, coherence,
self-sufficiency, register, or concision.

### Competing reading
The strongest reasonable case for retaining the current text.

### Why this survives promotion
Why textual recovery, consolidation, and the hostile recheck did not retire,
merge, batch, defer, or narrow the issue further.

### Required response
The evidence, author decision, editorial action, or acknowledged reviewer limit
needed to resolve the record. Ask one pointed question only when intent is
genuinely required.

### Consequences and interactions
What changes, weakens, or becomes redundant under each ruling.

### Suggested contribution
None unless wording is genuinely necessary; mark any proposal unmistakably.

### Author ruling
Pending.

### Application and recheck
- Applied:
- Affected lanes:
- Verification:
```

## Coverage and completion

Maintain a unit × lane matrix plus synthesis, discussion, and recheck columns.
A lane is complete only when every unit has a result. Record counts from the
ledger rather than estimating them.

`ARG` is complete only when every canonical claim has all Toulmin relations
statused, every implication is classified, and every triggered falsification
test has a recorded search scope and result. A gate is complete only when its
record is written and its source-lock checkpoint matches.

`SRC` is complete only when every source-dependent claim × cited-source pair
has a `source-claims.md` row with a physical-page pinpoint and verdict, or an
explicit `UNVERIFIED` record explaining why no reliable pinpoint was possible.

Use issue states `OPEN`, `DISCUSSED`, `RULED-KEEP`, `RULED-CHANGE`,
`RULED-CUT`, `DEFERRED`, `SUPERSEDED`, `APPLIED`, and `RECHECKED`.

Before creating an author-facing ID, apply
[promotion-triage.md](promotion-triage.md). Keep non-promoted findings in the
evidence ledger with their disposition and parent link. Counts demonstrate
coverage or report composition; they never establish review quality.
