# Toulmin argument analysis

Use this reference for the `ARG` lane. Map argumentation exhaustively, but do
not let it monopolise the peer review.

## Include claims broadly

Stage 0 creates the canonical claim inventory. `ARG` audits it and returns any
omission with an exact anchor; only the orchestrator assigns the next unused
stable ID. Include every proposition the manuscript asks the reader to accept:

- empirical observations and numerical statements;
- definitions and classifications;
- descriptions of authorial action;
- causal and comparative propositions;
- interpretations and generalisations;
- limitations and qualifications;
- recommendations and normative propositions;
- contribution and reach metaclaims;
- propositions carried by contrast, presupposition, transition, heading,
  caption, or example.

Do not assign a separate claim ID to purely grammatical support. When commitment
is ambiguous, create an `UNCERTAIN` claim and state the competing readings.

## Record each claim

- Exact expression and normalised proposition.
- Visibility: `EXPLICIT`, `IMPLICIT`, `PRESUPPOSED`, or `UNCERTAIN`.
- Type and argumentative role.
- Grounds: evidence or reasons offered.
- Warrant: rule connecting grounds to claim.
- Backing: support for that warrant.
- Qualifier or scope condition.
- Rebuttal or reservation.
- Upstream dependencies and downstream dependants.
- Competing reading and evidence that would change the assessment.

For every Toulmin relation use:

- `EXPLICIT`
- `IMPLICIT-RECOVERABLE`
- `MISSING`
- `DISPUTED`
- `N/A`

Prefer linked claim IDs over repeated paraphrase when one claim supplies
grounds, warrant, or backing for another.

## Classify implications

- `STATED` — the manuscript expressly draws it.
- `ENTAILED` — it follows from the stated premises.
- `INVITED` — wording pragmatically encourages the reading.
- `SPECULATIVE` — plausible but not established.
- `OVEREXTENDED` — stronger than the premises permit.
- `CONTRADICTED` — conflicts with another mapped proposition.

Do not attribute an invited or speculative implication to the authors as though
they stated it.

## Falsify the map

For every `MISSING`, `OVEREXTENDED`, or `CONTRADICTED` diagnosis:

1. Identify the exact textual evidence expected if the diagnosis were false.
2. Search the whole canonical manuscript, including tables and supplements.
3. State the strongest recoverable implicit warrant or competing reading.
4. Distinguish absence in the manuscript from absence in the accessible source
   set.
5. Record the result as supported, weakened, falsified, or unresolved.

## Cross-check other lanes during synthesis

Lane readers do not perform these checks by reading other lane packets. The
orchestrator adds cross-links without altering the raw verdicts:

- Stage 2 — `ARG` ↔ `APP`: does the design and evidence warrant the central
  claims?
- Stage 2 — `ARG` ↔ `TRN`: can the evidential path be inspected or
  reconstructed?
- Stage 4 — `ARG` ↔ `SRC`: do the cited works supply the grounds, warrants, or
  backing the manuscript attributes to them, at the claimed strength and scope?
- Stage 4 — `ARG` ↔ `COH`: does paragraph order expose the real dependency
  structure?
- Stage 4 — `ARG` ↔ `SCAR`: is a rebuttal textually motivated or answering an
  absent interlocutor?
- Stage 6 — `ARG` ↔ `CUT`: would a deletion remove grounds, warrant,
  qualification, or rebuttal?
