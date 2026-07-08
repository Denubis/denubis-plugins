---
name: self-application
audit_date: 2026-04-17
---

# Epistemic Humility Rubric — Applied to Itself

This file is the AC4.5 coherence demonstration: the rubric applied to the rubric. It is a **walk-through with surfaced vulnerabilities, not a pass/fail gate** (per H4 revision of `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md`). Zero vulnerabilities surfaced would itself be a flag — a rubric that passes its own screens without any honest discomfort has not applied them honestly. Two vulnerabilities are surfaced below; they are the rubric's first concrete act of the epistemic humility its opening memento names.

The design-plan's Additional Considerations section defines the standard this walk-through must meet: *"The rubric is a judgment aid — Schön's questions are reflective by design, not algorithmic. Self-application passes when the rubric demonstrably probes the same question categories it asks of other skills (i.e. the rubric's sections map back onto itself without contradiction), not when every checkbox is mechanically satisfied."*

## Scope — applied to this rubric

Walking Jones's three conditions (from `SKILL.md`'s `## Scope — Jones's three conditions` section) over the rubric itself as the artefact under review:

1. **90%+ unrescued completion.** A reader applying the rubric to a proposed skill reaches a judgement — pass, fail, or "needs more reflection" — without requiring outside intervention 90%+ of the time. The rubric's four sections are short and self-contained; the three supporting files are named and stable. "Needs more reflection" is a valid unrescued outcome, not a failure: Process is irreducibly reflective by design, and the rubric acknowledges this in its own `## Process` section. **Pass.**

2. **Failures are bounded, auditable, and reversible.** Bounded: every rubric claim is attributable to a quotation in `absencejudgement-citations.md` with a line number; the space of possible claims is therefore enumerable against that file. Auditable: a reader can re-walk from SKILL.md → citations → source file with no hidden inferences. Reversible: the rubric is markdown, reversible via `git revert`, and its failure modes are advisory — no automation acts on a rubric verdict. **Pass on all three adjectives.**

3. **Every miss surfaces fast enough for a human — not a cron job — to decide whether to roll back or roll forward.** No automation surfaces the rubric's outputs; a human reads the rubric and applies it to an artefact. No cron job can trigger a "roll forward" on a rubric verdict. A misapplied rubric verdict is visible to the next reader who revisits the call. **Pass.**

Scope judgement: the rubric passes Scope by construction — it is a reference document, not an agent. This is an honest "pass" only because the rubric is intentionally small and non-automated; a future revision that wired rubric verdicts into CI would need to re-walk this section with different assumptions.

## Observability — applied to this rubric

Walking the three screens (from `SKILL.md`'s `## Observability — three screens` section) over the rubric itself:

- **Screen 1: Form-gate.** The rubric presents itself as a checklist the reader applies. Actor = reader, action = apply each screen to the artefact under review. Every H2 names what the reader does (not what the rubric "is" or "provides"). **Pass.**

- **Screen 2: Tautology-screen — the reflective pinch-point.** Could a reader claim to have applied the rubric correctly while producing no useful judgement? **Yes.** A reader could rubber-stamp each section — tick "Scope satisfied", "Observability satisfied", "Process satisfied", "Failure-pattern clean" — without any genuine engagement. The rubric is vulnerable to its own Screen 2. This is an explicit honesty-note, surfaced here per AC4.5.

  Mitigation — how the rubric addresses this without resolving it:
  1. The `## Process` section is irreducibly reflective. Mechanical yes/no answers to Schön's four questions are themselves the failure mode Process is designed to catch (`SKILL.md`'s `## Process` section names this explicitly). A reader who rubber-stamps Process has, by that act, failed Process — the two non-identical forms cross-check each other.
  2. Screen 2 itself applies to *operational claims* ("has this been verified?"), and Process is not an operational claim; it is a reflective one. The rubric's Observability and Process sections are intentionally non-identical in form for this reason — the two sections catch different failure modes and a reader cannot rubber-stamp both.
  3. The honesty-note is surfaced here, in a committed file under version control, so future readers cannot treat the rubric as a self-proving black box.

  The tautology vulnerability is **not resolved**. It is named and mitigated; residual risk remains. This is the coherence-check AC4.5 calls for: the rubric's form is consistent with its own content, including the parts that cannot fully close on themselves.

- **Screen 3: Named-falsifier.** The rubric names its falsifier explicitly as "the human applying it" (see `SKILL.md`'s `## Process` reflection-as-non-algorithmic discussion). There is no passive-voice "the rubric decides" or "validation runs"; the applier is always named. **Pass.**

Observability judgement: **pass with an explicit honesty-note about the Screen 2 tautology vulnerability.** The honesty-note is the rubric's opening memento made concrete — the rubric cannot fully solve the problem it addresses, and says so rather than hiding the gap behind confident form.

## Process — applied to this rubric

Walking Schön's four questions (from `SKILL.md`'s `## Process — Schön's four questions` section) asked *of the rubric itself*:

- **Can I solve the problem I have set?** The rubric's problem is "prevent skill authorship, agent scaffolds, and automation decisions from substituting textual authority for evidence of falsifiable claims." The rubric can demonstrably screen out artefact-only DoD ("X committed"), modifier-only DoD ("terse", "production-ready"), and passive-voice falsifiers ("the code is reviewed"). The rubric cannot demonstrably screen out subtle cases where a reader rubber-stamps the rubric itself — that failure requires Process, and Process is reflective, not algorithmic. **Partial solution, by design.** The paper's own argument at `AbsenceJudgement.tex:267-269` is that no rubric can fully solve this for LLMs; a rubric claiming to fully solve it would fail its own Failure-pattern screen (specifically the vibes-based-operation pattern — "fully solved" would be a vibe, not a named observable).

- **Do I like what I get when I solve this problem?** Applied to a toy proposed skill with DoD wording like "SKILL.md is terse and production-ready, all tests pass," the rubric produces a named failure: modifier-only DoD fails Screen 1 (Form-gate); "all tests pass" fails Screen 2 (Tautology-screen). The output is a named failure mode, not a vibe. **Yes, the output matches the intent.** A reader gets a diagnostic they can act on.

- **Have I made the situation coherent?** The rubric's four sections have distinct jobs and do not overlap in a way that would produce conflicting verdicts:
  - `## Scope` bounds what the artefact may claim to do.
  - `## Observability` bounds how those claims may be written.
  - `## Process` asks whether the reflection behind the claims is real.
  - `## Failure-pattern screen` catches residual drift the first three missed.
  A reader cannot satisfy Scope while violating Observability (a bounded, auditable artefact whose DoD is modifier-only has still claimed something unverifiable). A reader cannot satisfy Observability while failing Process (a well-formed falsifiable claim that the reader stamped without reflection is still unverified in Schön's sense). The sections cross-check rather than contradict. **Yes, coherent.**

- **Have I kept inquiry moving?** Applying the rubric should produce the next question — "should this scope be narrower?", "is this DoD entry self-proving?", "would I actually reflect on this if I had time?" — not close the inquiry. If a reader ever experiences the rubric as closing inquiry (stamping "approved" with no residual question), that IS the rubric failing its own Schön screen. **This is the rubric's primary failure mode, surfaced here per AC4.5.**

  The primary failure mode is not a bug in the rubric's construction; it is a foreseeable misuse pattern. A reader pressed for time, applying the rubric mechanically to reach a quick verdict, has re-enacted the exact technoscholasticism the rubric is designed to guard against. The honesty-note is named here so future readers — including this rubric's authors applying it to their own work — cannot pretend the misuse mode was unforeseen.

Process judgement: the rubric passes Process with an explicit honesty-note about its primary failure mode. Consistent with Observability's tautology-screen honesty-note: both name a residual risk the rubric cannot fully close.

## Failure-pattern screen — applied to this rubric

Walking the four failure patterns (from `SKILL.md`'s `## Failure-pattern screen` section) over the rubric itself:

- **Temporality blindness.** The rubric cites 2025 sources (Jones, AbsenceJudgement) and 1994/1987/1999 sources (Schön, Latour). Dates are named in `absencejudgement-citations.md` and in SKILL.md's bibliographic pointers. The rubric does not assume its sources are eternal: a future revision must re-verify `AbsenceJudgement.tex` line numbers against the then-current paper version (the paper is actively drafted), and Latour ISBNs may shift across editions. **Pass, with documented staleness risk.** The audit date (2026-04-17) in `absencejudgement-citations.md` lets a future reader spot-check when re-verification is due.

- **Scope/confabulation.** The rubric's scope is narrow: four screens for one kind of artefact (skills, agent scaffolds, automation tasks). Claims stay within that scope; the rubric does not claim to screen, for example, the correctness of a skill's code or the quality of a commit message. A reader applying the rubric to an artefact outside its declared scope would surface the mismatch by finding that Jones's three conditions do not map cleanly — the rubric's misuse is visible to the user, not hidden. **Pass.**

- **Stamp-collecting without evaluation.** The rubric explicitly separates Observability (the screen — a form-check on claims) from Process (the evaluation — reflection on whether the claims are real). A reader who stamp-collects — ticks each Observability screen without Process — has, by that act, failed Process. The failure is diagnosable via the Process section's "these are reflective, not algorithmic" language. **Pass with a named vulnerability** — the vulnerability is the same one Observability's Screen 2 honesty-note names, viewed from a different angle.

- **Vibes-based operation.** The rubric names its sources, line numbers, section headings, and secondary sources. A rubric verdict tied to a named screen ("fails Screen 1 because DoD is modifier-only") is not a vibe; it is an observable with a named failure condition. **Pass.**

Failure-pattern judgement: the rubric passes all four screens, with the Screen 2 / Process-stamp-collecting vulnerability surfaced as one honesty-note viewed from two angles (Observability and Failure-pattern converge on it).

## Closing coherence note

The rubric passes its own screens with two explicitly-named honesty-notes: the Observability tautology vulnerability (Screen 2 cannot prevent a reader from rubber-stamping the rubric itself) and the Process primary failure mode (a reader pressed for time re-enacts the technoscholasticism the rubric is designed to guard against). Those honesty-notes are not failures of construction; they are the rubric's first concrete act of the epistemic humility its opening memento names — acknowledging that the rubric, like the AI applying it, cannot fully solve what it addresses. A rubric that claimed to fully solve technoscholasticism would be evidence it had not understood the problem.

## Subsidiary vulnerabilities — independent re-read (2026-04-22)

This section was added after the original walk-through (dated 2026-04-17, sections above) in response to C4 of the 2026-04-20 proleptic challenge: the same session that authored `SKILL.md` also authored the walk-through above, and surfaced exactly the two vulnerabilities the Phase 1 Task 3 spec pre-named. A fresh-session independent walk-through (`docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase-01-independent-self-application.md`) confirmed both load-bearing vulnerabilities and surfaced three subsidiary ones the original walk-through missed. Those subsidiary vulnerabilities are recorded here rather than silently merged into the sections above, so the timeline of what-the-authoring-session-saw vs what-the-independent-read-saw stays legible for future readers.

The companion independence-check document (`docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase-01-self-application-independence-check.md`) contains the full comparison. The three subsidiary vulnerabilities:

- **Scope condition (3) reframing.** The original walk-through (line 20) graded Jones's condition (3) as *"Pass"* on the reasoning that no automation runs on rubric outputs. The independent re-read reads condition (3) as asking whether the *rubric's own misfires* surface fast enough for a human to decide — not whether the rubric itself is automated. Under that reading, a rubric misfire (approving an artefact that later turns out to be technoscholastic) surfaces only when downstream consumers of the approved artefact encounter problems, which is slow by construction. The rubric has no named fast-failure channel for its own misses; the Phase 5 cross-reference audit audits cross-references, not rubric effectiveness. Condition (3) is weak, not a clean pass.

- **Declared scope breadth vs worked-example coverage.** `SKILL.md`'s `## When to invoke` section names four distinct application domains: skill authorship, agent-scaffold decisions, automation-task authorisation, and Definition-of-Done review. The single worked example in `## Observability` is a pytest invocation — a skill-authorship example. Applied to agent scaffolding (tool permissions, context management, handoffs), the four sub-rubrics could produce plausible-sounding answers that do not grip the agent-specific concerns. The rubric's declared surface is broader than its worked examples cover; that is a scope/confabulation exposure in the paper's own sense (fixed effort spread over a wider scope), and the original walk-through at line 70 did not catch it because it read the scope as narrow.

- **Evidence-grade inline visibility in SKILL.md.** `absencejudgement-citations.md` carefully grades Jones as *"Substack newsletter, not peer-reviewed"* and names Latour as a secondary source not cited from `AbsenceJudgement.tex`. Those grades do not appear in `SKILL.md`'s body; a reader of `SKILL.md` alone inherits the framing without the grading. The original walk-through at line 74 graded Vibes-based-operation as a *"Pass"* because sources are named. The independent re-read observes that *named* is not the same as *graded*, and that surfacing the Substack and secondary-source caveats inline would reduce the risk a casual reader of SKILL.md treats Jones's and Latour's citations as equivalent to Schön's and AbsenceJudgement's.

These subsidiary vulnerabilities are recorded as additions to the rubric's self-knowledge, not as corrections to the sections above. The original walk-through's two load-bearing vulnerabilities (Observability Screen 2 tautology; Process primary failure mode) hold up; the independent re-read confirmed them. The three subsidiary notes are what the authoring session did not see — not because the session was dishonest, but because a session that reads a Task 3 spec pre-naming two vulnerabilities tends to find those two vulnerabilities and stop searching. That pattern is itself an instance of the Process primary failure mode the rubric warns about: the spec supplied a map, and the authoring session walked the map. Recording the subsidiary vulnerabilities here closes the gap without rewriting what the original session honestly saw.
