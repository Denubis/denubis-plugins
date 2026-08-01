# Proleptic-challenge ↔ Kudina warrant audit — 2026-06-16

Design input for the future `codex-proleptic` skill. **Decision (Brian, 2026-06-16):
carry into codex-proleptic only — the native skill is NOT edited this session.**
The `skill-skills-upstream-sync` branch already does "proleptic-challenger
tightening" (see skill-audit-campaign tracker, Collisions); reconcile that branch
before any native edit ever happens.

## Audited

- `plugins/denubis-plan-and-execute/skills/proleptic-challenge/SKILL.md`
- `plugins/denubis-plan-and-execute/agents/proleptic-challenger.md`
- against Kudina, Ballsun-Stanton & Alfano (2025), *Asian Journal of Philosophy*
  4:24, DOI 10.1007/s44204-025-00247-1. Rendered, page-keyed:
  `~/zettelkasten/papers/kudinaUseLargeLanguage2025/` (18 pp, pymupdf4llm, no OCR).
  Quotes verified with `blockquote.py`; "gatekeeper" and "quota" grep-confirmed
  absent from the paper.

## Headline

The skill is **substantively faithful** to the paper's argument. No misreading.
The one real gap is **warrant/attribution**: operational design choices sit under
the skill's "Theoretical Foundation / Based on proleptic reasoning (Kudina…)"
banner, claiming paper-warrant for decisions the paper does not make.

## Organising lens

The paper's setting is **one person** — the student proposes, evaluates, and
learns from the objections (p.1 "evaluating them stimulates learning"). The skill
**splits the roles**: Claude proposes and challenges; the human evaluates and
decides. Most operational rules (present ALL, no pre-filtering, dismissal-requires-
evidence, don't auto-proceed) are principled responses to that split, not things
the paper needed to address. Engage this steelman before calling any addition a
"tension."

## Findings

### Keep — genuinely Kudina-grounded (inherit as paper-warranted)

- **Drunk tutor.** Faithful to p.5 ("always authoritative and usually correct")
  and p.9 (responses "might be decisive… however… also be flawed… arrive at a
  verdict on each").
- **"Value is in the evaluation, not the counterarguments."** Anchored in the
  abstract, p.1 ("evaluating them stimulates learning").
- **Charitable articulation of objections.** The paper's own definition of
  proleptic reasoning ("anticipation, charitable articulation, and response to
  potential objections", p.6/§3).
- **Dismissal-requires-evidence.** The *most* grounded addition, not a divergence.
  It operationalises the Meno *tether* (p.6 "tether them by working out a reason";
  p.9 "exercise their critical reasoning… to arrive at a verdict on each
  objection"). Producing the reason that lets you hold position *is* the tether.
  (Do not file this as contradicting "scaffold not gatekeeper" — that conflates
  the challenger-as-scaffold with the human's dismissal discipline.)

### Re-attribute — sound denubis design, currently miscredited to Kudina

- **No-quota rule** (agent §"Generate Counterarguments"). Denubis-original;
  "quota" absent from the paper. Orthogonal to the paper's "three counterarguments"
  (p.11) / "handful" (p.8) — those are *elicitation* prompts (how many the model
  should produce); the no-quota rule governs *what the challenger surfaces*.
  Different level. Motivated by decision-support efficiency, not Kudina. (If
  anything the paper's "evaluating even wrong outputs stimulates learning" cuts
  toward *more*, because it optimises learning where the skill optimises a busy
  human's decision — the meta-point again.)
- **The three fire-points** (skill §"When to Invoke": design-final / phase-
  transition / UAT). The paper's iteration (claim→challenge→response, p.6) is
  iteration *within* an episode; fire-points govern *when an episode starts* —
  different granularity, no conflict. The paper's examples even fire at
  consolidation points: editing a paper (p.9), preparing a debate position (p.11),
  marking an essay before submission (p.8). Phase-gating *maps* the paper but is a
  denubis workflow mapping, not a Kudina prescription.

### Reconsider — the only genuine (minor) divergence

- The dismissal gate accepts **artifact citations** ("file::symbol, design
  section, test") where the paper's tether would also accept **worked-out
  reasoning**. Slightly narrower than the paper; "design plan section" already
  softens it. Could occasionally force a citation where sound reasoning suffices.

## Implication for codex-proleptic

- Inherit the **keep** bucket as Kudina-warranted.
- Inherit the **re-attribute** bucket as **denubis design with its own rationale**
  (decision-support efficiency; workflow mapping) — not dressed as paper-derived.
- The proposer≠evaluator split is the design's load-bearing premise and should be
  stated explicitly, since codex-proleptic deepens the split (separate model /
  separate process generating the challenge).
- Open for the reconsider item: decide whether codex-proleptic's dismissal gate
  accepts reasoned argument, not only artifact citations.

## 2026-06-17 addendum — proposer≠evaluator re-attributed (author-confirmed)

A live dogfood of the external-agents design (the designed two-voice peer review
run on the design itself) surfaced a disagreement: the Claude reviewer called
"proposer≠evaluator" the design's strongest, *Kudina-warranted* premise; the codex
(GPT-5) voice flagged it as stretched beyond the paper. **Author (Brian) resolved:
proposer≠evaluator is NOT warranted by the paper, but is required for good agent
use.** It moves to the **re-attribute** bucket.

Warrant (denubis, not Kudina): Kudina's loop is one human who proposes, evaluates,
and is the *learning beneficiary* — self-evaluation is the point (acquiring the
tether). Agents have no such beneficiary; the goal is decision quality now. A
proposer that evaluates its own proposal applies the same priors to generation and
evaluation and cannot catch its own correlated errors. Evaluator independence
(the human, or a heterogeneous model) is what makes the critique non-vacuous.

Meta: the over-attribution to Kudina recurred three times — in the original skill
(this audit), in the Claude reviewer, and in the orchestrator's own design framing.
A shared-model blind spot; the independent codex voice caught it — itself evidence
for evaluator independence. Action: re-audit every Kudina citation in the
external-agents design for paper-warrant vs denubis-design-warrant.
