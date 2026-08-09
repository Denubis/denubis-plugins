# ADR 0004 — An advisor cites by openable pinpoint only, never by quotation or paraphrase

**Status:** Accepted (2026-08-09) — the rule caught the fabrication that motivated it, before the rule existed, and shipped in `denubis-notes-advisory` 0.2.0.

**Decision authors:** notes-advisory pressure test, 2026-08-09, session `a711c799`.

**Touches:** `plugins/denubis-notes-advisory/agents/notes-advisor.md:79-96`; `plugins/denubis-notes-advisory/skills/scanning-project-notes/SKILL.md:59-64`; `.notes/project_notes-advisory-pressure-test-2026-08-09.md` Finding 2.

## Context

The `notes-advisor` agent reads a project's `.notes/` and its chat logs, then
reports what bears on the work about to be done. Its whole value is that the
caller acts on the report without re-reading the corpus. That is also its whole
danger.

On 2026-08-09 the `advisor-live` arm of a three-arm pressure test reported, as
the item most worth raising with the operator, that session `6fed25b3` message
`1ceeda30` called prompt-shape gating the weakest of three options, and gave the
sentence in quotation marks.

Checked, and recorded in the note above:

- The message id **does not resolve** — `cc-search-chats` returns "Message not
  found".
- The quoted sentence **appears nowhere** under `--all --everything`.
- The options it referenced are real, from the RESUME file, but that source
  ranks them without calling that one weakest and **says the opposite in
  substance**.

So the fabrication inverted its own cited source, and the invented message id
made it read as *more* precise rather than less. The advisor's coverage line
(`read 44/44`) did not catch it and structurally cannot: coverage measures
breadth of reading, not truth of citation.

What did catch it was a caller-side rule already written into
`scanning-project-notes` — open what the advisor names rather than acting on its
summary. That rule paid for itself on first use.

### Rejected alternative — require a retrieval command beside each quotation

The pressure-test note proposed exactly this at the time
(`project_notes-advisory-pressure-test-2026-08-09.md:62-64`): every quoted string
ships with the command that retrieves it, and quotation marks are forbidden
around anything not re-read in-session.

Rejected as **actively worse than the status quo**. It bans the form of citation
that fails loudly and leaves untouched the form that does not. A fabricated
quotation advertises itself as checkable and dies on the first `grep -nF`. A
fabricated paraphrase carries no marks, invites no check, and reads as the
advisor's own judgement. Banning only quotation marks pushes a confabulating
advisor from the loud failure into the quiet one.

### Rejected alternative — a stronger accuracy instruction

"Do not invent citations" was already the state of the world. The global
`CLAUDE.md`, `feedback_reviewer-fabrication`, and
`feedback_4-7-retrieval-hallucination` all say versions of it. The advisor
fabricated anyway. An instruction that has already failed is not a fix.

## Decision

**The advisor returns locations. It does not return content.**

1. Each advisory is three parts and no more: `<pinpoint> — why it bears on this
   task — does it still hold`.
2. A pinpoint is precise enough to open: `path:line`, a heading, or a session id
   with a message uuid. A bare filename is not a pinpoint when a specific part
   of the file was read.
3. **No quotation and no paraphrase.** Not reproducing a source's words, and not
   restating them in other words either. Quoting is the caller's job once they
   have opened it.
4. Where no openable location can be given, the advisor says so, rather than
   describing the content instead.
5. The caller opens what the advisor names. **A pinpoint that will not open is a
   void finding** — the finding is discarded, not repaired.

The reasoning is a property of the artefact, not a preference about tone: a
pinpoint is the only citation form whose failure mode is an error on open.

### Relationship to the existing `paper-review` pinpoint convention

`denubis-academic`'s `source-fidelity.md` already uses "pinpoint" for the
scholarly sense — a page locator attached to a claim, where the paraphrase
remains and the pinpoint makes it auditable. This ADR is stricter and should not
be read as restating it. Here the pinpoint **replaces** the content rather than
accompanying it, because the consumer is a model that will otherwise act on the
paraphrase without opening anything.

## Consequences

**Positive:**
- Every fabrication becomes an error at the moment of use rather than a
  plausible sentence in a report.
- The rule is checkable by the caller with no extra tooling.
- It generalises past this agent: any advisor whose output is consumed by a
  model that will not re-read is a candidate.

**Negative / residual:**
- The advisory is less immediately actionable. The caller must open each
  pinpoint, which is the cost being deliberately paid.
- Line numbers drift as files change, so a pinpoint can fail to open for an
  innocent reason. Treated the same as a fabrication by design, because the
  consumer cannot tell them apart, and the repair is the same: go and look.
- Nothing mechanically enforces the rule against the model. It is an
  instruction in the agent brief, and briefs decay. What is enforced is the
  caller-side consequence.

**Verification honesty:**
- The rule's origin is one confirmed fabrication, not a rate. One event does not
  establish how often the advisor fabricates.
- The bound on Finding 2 is narrow and stated in the note: the id was shown
  invalid and the string absent under two phrasings. It does not prove nobody
  expressed a similar view in other words.
- **No test asserts the advisor obeys this.** The advisor is a model, and its
  compliance is unproven rather than covered. What can be shown is that a
  non-opening pinpoint is discarded, and that is a caller behaviour.

## Verification

- **The originating check**, already run: the cited message id returned "Message
  not found" and the sentence was absent from `cc-search-chats --all
  --everything`.
- **Standing caller-side check:** open every pinpoint before acting. The first
  one that does not resolve voids that finding; broad failure discards the
  advisory and reports confabulation.
- **Not scheduled:** a repeat pressure-test arm measuring fabrication rate
  before and after the rule. Worth doing, but a valid arm needs a method that
  does not let the subagent read the live transcript — see
  `.notes/reference_subagent-tests-read-the-live-transcript.md`.
