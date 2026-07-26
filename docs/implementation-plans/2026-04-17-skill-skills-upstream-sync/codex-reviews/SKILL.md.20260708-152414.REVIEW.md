# Critical Peer Review: SKILL.md

Reviewer: Codex (GPT-5)
Date: 2026-07-08
Document reviewed: context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md

## Hidden Assumptions

- **Load-bearing, weakly supported:** The rubric’s Scope screen preserves Jones’s 90% threshold when operationalised. The target quotes “90%+” at `SKILL.md:29`, but restates it as “the majority of the time” at `SKILL.md:35`.
- **Load-bearing, unverified in staged context:** Claims attributed to `AbsenceJudgement.tex` are source-faithful. The target repeatedly cites `AbsenceJudgement.tex` directly, but the raw `.tex` file is not under `./context/`; only `absencejudgement-citations.md` is staged.
- **Load-bearing, partially supported:** The rubric generalises from skill/DoD review to “agent scaffold” and “automated task” review. The target declares that scope, but its only worked example is a pytest-based skill-authorship example.
- **Load-bearing, weakly specified:** A reader can turn rubric failures into an action. The target diagnoses failure but does not provide a verdict aggregation or remediation path inside the target file.

## ACH Matrix

| Evidence | H1: target is fit as-is | H2: target is useful but needs revision | H3: target should not be a skill |
|---|---:|---:|---:|
| `SKILL.md:29` quotes “90%+” but `SKILL.md:35` says “majority” | − | + | ? |
| `SKILL.md:17-20` covers skills, agents, automation, DoD, but `SKILL.md:55-57` gives only pytest example | − | + | ? |
| `self-application.md:88-92` records the same scope/example and fast-failure weaknesses | − | + | ? |
| `writing-skills/SKILL.md:42`, `testing-skills...:36`, `writing-claude-directives/SKILL.md:135` all integrate the rubric | + | + | − |
| Raw `AbsenceJudgement.tex` absent from `context/` | − | + | ? |
| Target has bounded sections and source-citation support file | + | + | − |

Decision rule: H2 requires the fewest contradictions. The target is structurally useful and already integrated, but several load-bearing claims need correction or qualification before the skill is fit as a screening rubric.

## Findings

### High (count: 1)

- **Issue**: The Scope checklist dilutes Jones’s hard 90% threshold into a “majority” threshold.
  **Evidence**: The target quotes Jones as “the agent finishes the task 90%+ of the time without rescue” at `SKILL.md:29`, then operationalises the same condition as “The artefact finishes its task the majority of the time without outside intervention” at `SKILL.md:35`.
  **GRADE factors**: Internal inconsistency; load-bearing assumption unverified. A 51% completion rate satisfies “majority” but fails “90%+.”
  **Ripple**: This weakens the main screen for whether an agent/task/skill “earns its existence.” It also propagates into `self-application.md:16`: “without requiring outside intervention the majority of the time.”
  **Corrected language**: “The artefact finishes its task at least 90% of the time without outside intervention.”
  **Location**: context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md:35

### Medium (count: 3)

- **Issue**: The declared scope is broader than the target’s examples and scaffolding.
  **Evidence**: The target invokes the rubric for “Agent-scaffold decision” and “Automation-task authorisation” at `SKILL.md:18-19`, but its only worked example is “`pytest plugins/denubis-extending-claude/skills/epistemic-humility/tests/ --strict-markers` exits 0” at `SKILL.md:57`. The supporting self-application records the same weakness: “The single worked example in `## Observability` is a pytest invocation — a skill-authorship example” at `self-application.md:90`.
  **GRADE factors**: Incomplete enumeration; indirectness. The skill/task/DoD case is covered better than the agent/automation case.
  **Ripple**: The description claims “proposed skill, agent scaffold, or automated task” at `SKILL.md:3`; `writing-claude-directives/SKILL.md:135` depends on it for “agent-task-or-skill.”
  **Corrected language**: Add at least one agent-scaffold example and one automation-task example, or narrow the target scope to skill/DoD screening.
  **Location**: context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md:17-20,55-57

- **Issue**: The target diagnoses rubric failure but does not tell the reader what to do next.
  **Evidence**: The target says, “If the artefact under review exhibits any of these, the rubric fails” at `SKILL.md:81`, and asks whether the artefact “enable[s] the next question” at `SKILL.md:73`, but it does not name remediation steps after a fail verdict. The independent self-application says: “if an artefact fails one of the four sections, the rubric says ‘fails the rubric’ and stops” at `phase-01-independent-self-application.md:52`.
  **GRADE factors**: Missing upgrade path. This weakens whole-skill fitness because a screening skill should route failure to re-scope, rewrite, reject, or gather evidence.
  **Ripple**: The orchestrators supply some remediation externally, e.g. `writing-skills/SKILL.md:42` says “re-scope, not to author,” but the target itself does not.
  **Corrected language**: Add a “Verdict and next action” section: fail Scope → re-scope; fail Observability → rewrite DoD/AC; fail Process → stop for human reflection; fail Failure-pattern → gather evidence or reject.
  **Location**: context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md:79-88

- **Issue**: Direct source-fidelity claims to `AbsenceJudgement.tex` cannot be verified from the staged evidence.
  **Evidence**: The target says “AbsenceJudgement.tex:203 introduces `technoscholasticism`” at `SKILL.md:13` and cites many exact `.tex` line numbers. The staged source file is absent: `find context -name '*Absence*' -o -name '*absence*' -o -name '*.tex'` returned only `context/plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md`. The citations file points outside the staged context: “Working paper at `/home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex`” at `absencejudgement-citations.md:3`.
  **GRADE factors**: Reporting/provenance gap. The citations file may be accurate, but the raw source is not present for this review.
  **Ripple**: This affects every exact `AbsenceJudgement.tex:<line>` claim in the target.
  **Corrected language**: Stage the raw source excerpt needed for verification, or mark these as `[unverified — needs external check: raw AbsenceJudgement.tex at cited lines]`.
  **Location**: context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md:7,13,31,66,83-88

### Low (count: 1)

- **Issue**: The Cross-references note is stale.
  **Evidence**: The target says, “These cross-references point forward; the referring skills are updated in Phases 2-4” at `SKILL.md:98`. Current context shows the references already exist: `testing-skills-with-subagents/SKILL.md:36` and `writing-claude-directives/SKILL.md:135` both call the rubric, and `writing-skills/SKILL.md:42` does too.
  **GRADE factors**: Temporality/staleness; low severity because the references resolve.
  **Ripple**: A future broken cross-reference could be misclassified as “not a Phase 1 bug” even though the forward phase has already landed.
  **Corrected language**: Replace the forward-looking note with “These cross-references are expected to resolve; broken references are cross-reference-audit failures.”
  **Location**: context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md:98

## Verification

Commands actually run and relevant real output:

- `ls -R context`
  Output included the target path and sibling files:
  `context/plugins/denubis-extending-claude/skills/epistemic-humility: SKILL.md absencejudgement-citations.md self-application.md`

- `test -f context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md && nl -ba .../SKILL.md`
  Output showed the target exists and has 108 numbered lines.

- `nl -ba REVIEW-METHOD.md`
  Output showed the required review format at lines 235-283 and severity levels at lines 227-233.

- `find context -name '*Absence*' -o -name '*absence*' -o -name '*.tex'`
  Output:
  `context/plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md`

- `find context/plugins/denubis-extending-claude/skills/epistemic-humility -maxdepth 1 -type f -printf '%f\n' | sort`
  Output:
  `SKILL.md`
  `absencejudgement-citations.md`
  `self-application.md`

- `wc -l context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md ...`
  Output:
  `108 .../SKILL.md`
  `140 .../absencejudgement-citations.md`
  `94 .../self-application.md`
  `342 total`

- `for d in writing-skills testing-skills-with-subagents writing-claude-directives; do test -d ...; done`
  Output:
  `writing-skills: exists`
  `testing-skills-with-subagents: exists`
  `writing-claude-directives: exists`

- `rg -n "epistemic-humility|Rubric Callback|rubric callback" ...`
  Output included `writing-skills/SKILL.md:42`, `testing-skills-with-subagents/SKILL.md:36`, and `writing-claude-directives/SKILL.md:135`.

- `for code in TEMP RAND SCOP VIBE FABR MECH MTCH SCAF BOUN; do ... rg -n -w "$code" ...; done`
  Output showed each code appears only in `SKILL.md:106` and `absencejudgement-citations.md:138`, both rejection contexts.

## Strongest Hypothesis

The strongest hypothesis is that the target is a useful but unfinished screening rubric. The evidence is convergent: the orchestrators integrate it, the citation support file is careful, and the self-application names real vulnerabilities; but the target weakens a hard threshold, overextends its scope examples, and lacks an internal remediation path.

## Weakest Hypothesis

The weakest hypothesis is that the target is unfit as a standalone skill. The existing cross-skill integration and structured four-part rubric contradict that stronger rejection. The defects are revision-sized, not removal-sized.

## Pre-Mortem

If this review is wrong and the target is ready as-is, the next evidence would show agents applying it successfully to non-skill agent scaffolds and automation hooks without extra human interpretation.

Alternative failure scenarios still consistent with available evidence:

- A reader applies “majority” literally and approves a task far below the quoted 90% threshold.
- A reader applies the pytest-shaped Observability example to an agent scaffold and misses tool-permission or handoff failure modes.
- A reader treats the citations file as source verification even though the raw `AbsenceJudgement.tex` was not staged.

## Fastest Next Test

Apply the target rubric to one real agent scaffold and one real automation hook from `context/`, recording the verdict and remediation path. This would directly test the declared scope beyond skill-authorship examples and expose whether the rubric actually screens those artefacts.

## Overall Assessment

Needs revision before presenting as a whole-skill fitness screen. Fix the 90%/majority inconsistency first, then either narrow the declared scope or add agent/automation worked examples, and add an explicit fail-to-next-action section. The scholarly citations are mostly load-bearing in structure, but raw `AbsenceJudgement.tex` fidelity is `[unverified — needs external check: staged raw source or cited excerpts from the paper]`.