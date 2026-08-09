# ADR 0004 — An advisor cites by openable pinpoint only, and the caller controls its check

**Status:** Accepted (2026-08-09). **Rationale corrected the same day** — see the Correction
below. The decision stands on the operator's ruling and on the corrected incident; the
first version's account of that incident was false and is retained here rather than
deleted.

**Decision authors:** operator ruling, 2026-08-09; incident corrected by an external
cross-check the same day, verified independently against the primary transcript.

**Touches:** `plugins/denubis-notes-advisory/agents/notes-advisor.md:79-94`;
`plugins/denubis-notes-advisory/skills/scanning-project-notes/SKILL.md:59-72`;
`.notes/project_notes-advisory-pressure-test-2026-08-09.md:41-64`.

## Correction (2026-08-09)

**The first version of this ADR said an advisor fabricated a citation. It did not.**

The advisor reported that session `6fed25b3` message `1ceeda30` called prompt-shape gating
the weakest of three options. The supervisor ran two checks, got nothing from both, and
wrote the result up as a fabricated uuid attached to an invented sentence that inverted its
own source.

Every part of that was wrong. The message is
`1ceeda30-fb5e-443d-a6a2-15c8e54e02d3`, timestamped 2026-08-01T06:23:24Z in session
`6fed25b3-c413-4978-a3f8-2a7112cdf319`, eight days before the test. It contains the
attributed sentence verbatim. The list it belongs to is headed *"Three alternatives,
strongest first"* and places prompt-shape gating third, so "weakest" was a correct reading
of an explicit ranking rather than an inversion of it. **The advisor's citation was accurate
in every particular**, including the eight characters of uuid, which are a correct prefix.

Both supervisor checks were structurally incapable of succeeding:

| The check | Why it could not have found it |
|---|---|
| `cc-search-chats context 1ceeda30 --json` | the helper resolves a full uuid; an 8-char prefix returns "Message not found" |
| fixed-string search for `gating on prompt shape` | the source sentence opens the paragraph, so it reads `Gating` |

Neither had a positive control. Re-running each with the fault removed — the full uuid, and
`-i` — returns the message and the sentence.

This is the same failure the notes-advisory work exists to prevent, committed by the
supervisor, on the day it shipped, and then written into an architecture record. It is kept
here because the reasoning that produced it is the thing worth recognising: **a search that
cannot succeed returns the same silence as a search that succeeded and found nothing.**

## Context

The `notes-advisor` agent reads a project's `.notes/` and its chat logs, then reports what
bears on the work about to be done. Its value is that the caller acts on the report without
re-reading the corpus. That is also its danger, and the danger runs in both directions:

- **Toward the advisor**, an unfounded claim reads as fluently as a founded one.
- **Toward the caller**, a check on the advisor can fail for reasons that have nothing to do
  with whether the advisor was right — which is what happened above, and which turned a
  correct advisory into a discarded finding and then into an accusation.

The operator ruled the citation form directly on 2026-08-09: *"no paraphrases, a pinpointed
citation to go look up is probably best."* This ADR records why the form is right and what
the caller owes it in return.

### What the corrected incident actually argues

It argues **for** pinpoints, by a different route than the false version did.

The pinpoint is what made the claim checkable at all. It survived a botched check, and it
was still there to be checked properly afterwards — which is how the truth was recovered.
A paraphrase would have offered nothing to open, so neither the wrong conclusion nor its
correction would have been reachable. The citation form did its job; the check did not.

It also argues that **a failed open is a fact about the check until proven otherwise.**

### Rejected alternative — require a retrieval command beside each quotation

Proposed in `.notes/project_notes-advisory-pressure-test-2026-08-09.md:62-64`: every quoted
string ships with the command that retrieves it, and quotation marks are forbidden around
anything not re-read in-session.

Rejected as worse than the status quo. It bans the form of citation that fails loudly and
leaves untouched the form that does not. A fabricated quotation invites a check; a
fabricated paraphrase carries no marks and reads as the advisor's own judgement. Banning
only quotation marks pushes a confabulating advisor from the loud failure into the quiet
one.

The corrected incident adds a second objection the first version could not see: the
supervisor *had* a retrieval command, ran it, and drew the wrong conclusion from it. Pairing
a citation with a command does nothing when the command is the broken part.

### Rejected alternative — withdraw the rule, since its evidence evaporated

Tempting and wrong. The rule rests on an operator ruling, not on the incident, and the
corrected incident supports it rather than undermining it. What the correction retires is
the *fabrication story*, not the citation form.

### Rejected alternative — a stronger accuracy instruction

"Do not invent citations" was already the state of the world in the global `CLAUDE.md` and
in two `.notes/` feedback notes. Instructions that have already failed are not fixes.

## Decision

**The advisor returns locations. It does not return content. The caller controls its own
check before calling a location bad.**

Advisor side:

1. Each advisory is three parts and no more: `<pinpoint> — why it bears on this task — does
   it still hold`.
2. A pinpoint is precise enough to open: `path:line`, a heading, or a session id with a
   message uuid. A bare filename is not a pinpoint when a specific part of the file was
   read. **Give identifiers in full** — an abbreviated uuid is a pinpoint that needs repair
   before it opens, and the repair will not always happen.
3. **No quotation and no paraphrase.** Quoting is the caller's job once they have opened it.
4. Where no openable location can be given, say so rather than describing the content
   instead.

Caller side — added by the correction, and load-bearing:

5. **Open what the advisor names.** A finding acted on without opening its pinpoint is a
   finding taken on trust.
6. **A pinpoint that will not open is void only after a controlled check.** Before treating
   a location as non-opening: use the identifier in full, case-fold the search, and run a
   positive control — feed the same check something that must match and watch it fire. A
   check whose control does not fire is broken, and broken is no evidence.
7. **Never escalate a failed lookup into an accusation.** "I could not open this" is a
   report about the check. "This was fabricated" is a claim about the advisor, and it needs
   a control that fired.

## Consequences

**Positive:**
- A fabricated *location* becomes an error at the moment of use rather than a plausible
  sentence in a report.
- The check is cheap and needs no tooling beyond what the caller already has.
- Rule 6 makes the caller's own failure visible instead of attributing it to the advisor.

**Negative / residual:**
- The advisory is less immediately actionable. The caller must open each pinpoint, which is
  the cost being deliberately paid.
- **Openable does not mean faithful.** Only a non-resolving locator fails at open. A
  pinpoint that points at a real but irrelevant line opens fine, and a correct pinpoint can
  carry a false "why it bears". Both survive rule 6 and are caught, if at all, by the
  caller reading the material. The form forces the caller onto primary sources; it does not
  verify the attribution.
- Line numbers drift, so a pinpoint can fail to open innocently. Rule 6 covers this: the
  repair is the same as for any failed open, which is to look harder before concluding.
- Rules 5–7 are the caller's discipline and nothing enforces them mechanically. The
  supervisor broke all three on the day they were written.

**Verification honesty:**
- **There is no confirmed instance of this advisor fabricating a citation.** The one
  suspected case was the supervisor's error. The rule is justified by the operator's ruling
  and by the argument above, not by an observed fabrication rate.
- **No test asserts the advisor obeys this**, and none can straightforwardly: the advisor is
  a model and compliance with its own brief is not a codebase invariant. Recorded as
  deliberately unproven, which is why this ADR takes no paired row in
  `docs/architecture/constraints.md`.
- The correction itself was found by an external cross-check rather than by the supervisor
  re-examining its own work, which is a fact about how it was caught and not a claim that
  such passes are reliable.

## Verification

- **The correction, reproducible:** `cc-search-chats context
  1ceeda30-fb5e-443d-a6a2-15c8e54e02d3 --json` returns the message; the same call with the
  eight-character prefix returns "Message not found". A case-folded search of session
  `6fed25b3`'s transcript finds the sentence; the case-sensitive lower-case form finds
  nothing. Each was run with a positive control first.
- **Standing caller-side check:** rules 5–7 above.
- **Not scheduled:** a repeat pressure-test arm measuring whether the advisor cites
  accurately at any rate. The one arm run so far produced a false positive from the
  supervisor, so the method needs fixing before the measurement means anything — see
  `.notes/reference_subagent-tests-read-the-live-transcript.md`.
