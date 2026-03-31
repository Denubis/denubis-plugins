---
name: critical-peer-review
description: Use when reviewing debugging analyses, postmortems, incident investigations, design plans, implementation plans, generated artifacts, or another agent's technical reasoning for overclaiming, internal inconsistency, and evidence-grade violations - falsification-first audit that treats prior output as untrusted
user-invocable: true
---

# Critical Peer Review

Evidence-led review of technical artifacts. Treats prior reasoning as something to audit, not trust. (Adapted from Codex critical-crash-review protocol, enhanced with ACH, GRADE, ABP, and pre-mortem methodologies.)

## Core Principle

**The artifact you are reviewing was produced by a system that is incentivised to sound confident.** Your job is to find where that confidence outstrips the evidence. Every claim must earn its grade.

## When to Use

- Reviewing a debugging analysis (Phase 3d self-audit in systematic-debugging)
- Reviewing a postmortem or incident report
- Reviewing a design plan
- Reviewing an implementation plan
- Reviewing generated artifacts such as `.pdf`, `.html`, screenshots, logs, or compiled outputs
- Reviewing another agent's technical reasoning
- Reviewing your own prior analysis after being told you overclaimed
- Any time a technical document makes causal claims that affect decisions

## Artifact Classification

Before reviewing, classify the artifact explicitly:

- `debugging-analysis`
- `incident-analysis`
- `design-plan`
- `implementation-plan`
- `generated-artifact`
- `technical-reasoning`

State the artifact type in the review output. This determines which additional checks are mandatory.

## Workflow

### 1. Establish the evidence universe

Read the exact artifacts first:

- The document, output, or reasoning being reviewed
- Logs, test output, stack traces, screenshots, generated artifacts, or diffs it references
- Source files, issue threads, plan files, or design docs it cites
- Prior reviewer notes if any exist

**Call out missing evidence immediately.** If the analysis references artifacts you cannot access, flag this — you cannot verify claims about evidence you haven't seen.

When the evidence includes logs, timelines, or postmortem material, inventory every source before analysing it:

- file path
- line count
- first timestamp
- last timestamp
- timestamp timezone or offset convention
- file size when relevant

Choose one reference timezone for cross-source comparison and state it explicitly. Never assume all sources share the same timezone.

**Positive control:** Before trusting any filter or query result, verify it against one event you already know must appear in-window. If a query returns zero, re-run the positive control before reporting "no evidence."

### 2. Protect provenance

Assume tmp directories, logs, copied outputs, screenshots, and generated artifacts may be contaminated.

Check:
- Whether local reruns may have overwritten server artifacts
- Whether copied files still point at the original context
- Whether "latest" files may actually be from a different run
- Whether cited diffs or file paths belong to the same branch, commit range, or artifact version under review

Treat provenance failure as a first-class finding. A contaminated log or output weakens every downstream claim.

When analysing multiple log sources:
- Apply time filtering before grouping or aggregation
- Enumerate the full category space before drilling into specific error codes or event names
- Compare important timestamps against reference events such as deploys, restarts, migrations, or config changes

Do not aggregate unfiltered data and then pretend the result belongs to the requested window.

### 3. Extract hidden assumptions (ABP)

Before evaluating evidence, extract the analysis's **hidden assumptions** — claims stated as background rather than evidence.

Examples: "the system was in steady state," "log timestamps are accurate," "network latency was not a factor," "feature flags were as documented."

For each assumption:
- **Load-bearing:** Does the conclusion fail if this assumption is wrong? If yes, the analysis must provide evidence or hedge.
- **Non-critical:** Conclusion survives even if wrong.
- **Signposts:** What observable warning signs would indicate the assumption is breaking down?

Flag any load-bearing assumption that lacks supporting evidence as a Medium-severity finding.

**Reference:** Dewar, J.A. (2002). *Assumption-Based Planning*. RAND Corporation.

### 4. Separate facts from inference

Tag every statement in the analysis:

- **Fact:** directly observed, reproduced, or read from code/diff/logs
- **Inference:** derived from facts via reasoning
- **Speculation:** plausible but not grounded in evidence

If speculation has borrowed the confidence of a fact — if an inference reads like a fact — flag it. Name every assumption an inference depends on.

For incident and postmortem review, every finding should also carry:
- A scope tag: `in-window confirmed`, `out-of-window corroboration`, or `inference`
- A confidence tag per the evidence grading scale (see below)

Any number without a reproducible command or query is `unverified`. Any count derived from an unfiltered or wrong-window source is also `unverified` until rerun correctly.

### 5. Audit the reasoning

Review the artifact as if it were a code review from someone whose work you do not trust.

**Look for:**

- Unsupported jumps from symptom to mechanism
- Multiple variables collapsed into one hypothesis
- "Same version" claims that ignored env, permissions, temp paths, branch state, or service user
- Conclusions drawn from overwritten or mixed artifacts
- Findings that mix in-window facts with out-of-window corroboration
- Incomplete enumeration (searched for expected categories instead of listing all)
- Counts reported without the exact command that produced them
- Fixes proposed before causal mechanism isolation
- **Synthetic test results extended to production paths** — the most common overclaim
- **Universal quantifiers** ("all", "every", "only", "always", "never") that were not universally verified
- **Internal inconsistency** — counts that don't sum, summaries that contradict details, acceptance criteria that don't match steps, scope claims that don't match evidence

**State plainly which hypothesis is weakest and why.**

### 6. Check evidence grades (GRADE-enhanced)

Apply the evidence grading scale to every finding that makes a causal or behavioural claim:

| Grade | Label | Positive border | Negative border | Production path |
|-------|-------|----------------|-----------------|-----------------|
| **High** | **Demonstrated** | Mechanism triggers failure | Removing mechanism prevents failure | Both tested on actual production code path |
| **Moderate** | **Plausible** | Evidence points here; one border shown | Not yet shown removal prevents it | Production path inferred but not confirmed |
| **Low** | **Possible** | Mechanism triggers failure in synthetic test | Production path unconfirmed | Neither border on production path |
| **Very low** | **Speculative** | Hypothesis among several; untested | — | No border evidence |

Do not force omission, sequencing, or feasibility findings in design and implementation plans into this grading model unless the finding itself is a causal claim.

**For each graded finding, verify:**
- Does the language match the grade?
- Did the author write "demonstrated" for something that's only "plausible"?
- Did the author write "the mechanism is X" when they mean "mechanism X is plausible"?
- Did a synthetic test result get extended to a production path without bridging evidence?
- Were both borders tested for any "demonstrated" claim?

**GRADE downgrade criteria** (Guyatt et al., 2008). Apply these to any evidence claimed as High or Moderate:

| Factor | Question | Downgrade if |
|--------|----------|-------------|
| **Risk of bias** | Are there known limitations in how the data was collected? | Source is contaminated, partial, or from a different time window |
| **Inconsistency** | Do multiple sources agree? | Sources conflict and the analysis doesn't explain why |
| **Indirectness** | Does the evidence directly answer the hypothesis? | Evidence is proxy (e.g. synthetic test, different environment) |
| **Imprecision** | Sample size? Confidence? | Single observation, no repetition, anecdotal |
| **Reporting bias** | Were negative results included? | Analysis only cites confirming evidence |

If a finding fails any criterion, downgrade one level. If the analysis's language doesn't match the downgraded level, flag it.

### 7. Build the ACH matrix

Construct an Analysis of Competing Hypotheses matrix (Heuer, 1999).

- **Rows:** Each hypothesis the analysis considers (plus any it should have considered but didn't)
- **Columns:** Each discrete piece of evidence
- **Cells:** `+` (consistent), `−` (inconsistent), `?` (not diagnostic)

**Key operation:** Evaluate each piece of evidence *individually* against *all* hypotheses. Do not evaluate evidence narratively — narrative coherence is exactly the bias ACH is designed to break.

**Decision rule:** The hypothesis requiring the fewest contradictions survives. But: a single strong `−` can outweigh many weak `+` marks. State which contradictions are strong.

**Flag:** Any evidence the analysis treats as "supporting H1" that also fits H2 equally well (likelihood ratio ~1:1). Such evidence moves no needle and should not be cited as support.

**Reference:** Heuer, R.J. (1999). *Psychology of Intelligence Analysis*. CIA Center for the Study of Intelligence.

### 8. Verify citations

For every file:line reference in the analysis:
- Does the file exist at that path?
- Does the line contain what is claimed?
- Is the line number current (not from a stale read)?

For every count, total, percentage, timeline, or "zero results" claim:
- Can you reproduce it with the stated command?
- If not stated: flag as unverified

For plan review:
- Verify that referenced files, modules, directories, commands, and tests actually exist when the plan depends on them
- Verify that cited requirements, constraints, or earlier decisions are represented accurately

### 9. Re-rank hypotheses

Prefer narrow, mechanistic hypotheses over broad labels.

Bad:
- "the auth system is broken"
- "the plan seems risky"

Better:
- "the token validation at `auth.py:147` rejects valid tokens when `expires_at` falls within the refresh window"
- "Step 4 assumes a backfill can run after the schema change, but the migration removes the source column in Step 3"

Prefer maximally risky statements. The stronger the claim, the more useful the test. Then try to shatter the claim. If it survives a serious falsification attempt, it has earned attention.

For incidents, prefer contributing-factor chains over single "root cause" labels unless the evidence genuinely collapses to one mechanism.

### 10. Design the smallest discriminating test

For each finding that is below "demonstrated" grade, identify the single test that would buy the most certainty. State:

- Why this hypothesis has explanatory power
- Prediction if the hypothesis is true
- Prediction if it is false
- What result would actually change the grade

### 11. Pre-mortem the conclusion

After completing steps 1-10, assume the analysis's conclusion is **wrong**. Work backward:

- "If this root cause is incorrect, what would the next incident reveal?"
- List 3 alternative failure scenarios consistent with the available evidence
- For each alternative: is there *any* evidence in the data that would support it? If yes, the analysis needs hedging or a competing hypothesis section
- Check: did the analysis dismiss disconfirming evidence too quickly?

This step catches **narrative confidence bias** — where a coherent story feels right but rests on unspoken assumptions. Research shows pre-mortem analysis increases risk identification accuracy by ~30% (Klein, 2007).

**Reference:** Klein, G. (2007). Performing a Project Premortem. *Harvard Business Review*, 85(9), 18-19.

### 12. Diagnostic timeout

Final reflection before writing findings. Answer honestly:

- "Is this the most likely explanation, or just the most coherent one I've constructed?"
- "Am I anchored to the analysis's first hypothesis?"
- "What information would change my mind about my own review?"
- "What didn't I look for?"

If any answer unsettles you, go back and investigate before proceeding.

**Reference:** Croskerry, P. (2003). The Importance of Cognitive Errors in Diagnosis. *Academic Emergency Medicine*, 10(11), 1174-1185.

## Artifact-Specific Checks

### Debugging Analysis

Mandatory checks:

- Symptom-to-mechanism jump unsupported by evidence
- Production path claimed from synthetic test only
- Alternative hypotheses not ruled out
- Negative border not tested
- Code path or stack frame cited incorrectly
- Fix proposed before mechanism isolation

### Incident Analysis

Mandatory checks:

- Time-window contamination
- Timezone mismatch or silent timezone assumption
- Aggregation before filtering
- Contaminated provenance
- Deploy, restart, migration, or config-change boundaries not reconciled
- "Latest log" or "same run" claims without provenance proof
- Counts lacking exact query or command

### Design Plan

Mandatory checks:

- Requirement missing from the plan
- Contradiction with existing architecture or prior design decisions
- Unstated assumptions treated as facts
- Acceptance criteria too vague to verify
- Rollout, migration, or failure-mode handling omitted where required
- Feasibility claimed without concrete evidence
- Risks named without actionable mitigations

### Implementation Plan

Mandatory checks:

- File ownership or write scope unclear
- Sequence impossible or dependency order wrong
- Verification commands missing or non-specific
- Migration, backfill, rollback, or cleanup omitted where required
- Tests named vaguely instead of concretely
- Hidden blocking assumptions
- Steps too abstract to execute

### Generated Artifact

Mandatory checks:

- Artifact does not match its claimed generating inputs
- Provenance of the artifact is unclear
- Toolchain version or runtime context omitted
- Output compared against the wrong baseline
- Rendered or visual defect attributed to the wrong stage

## The Ripple Rule

**When issues are found, trace the ripples before reporting.**

A finding is rarely isolated. If a count is wrong in one place, every place that references or derives from that count may also be wrong. If a scope claim is too broad, every conclusion that depends on that scope is weakened. If a plan step is impossible, downstream steps built on it are also suspect.

**The protocol:**
1. Find an issue
2. **Before writing it up:** search the document for every reference to the affected claim, number, assumption, or step
3. List all downstream statements that depend on the incorrect claim
4. Report the issue AND its ripple effects as a single finding

**Example:** "Category 3 is described as 71 error-seconds, but the classifier output shows 48. This also affects: (a) the 216/550 total in the status line, (b) the percentage calculation in the summary, (c) the priority ranking in the recommendations section."

## The Pattern-Level Review Rule

When you find one defect, ask whether it is local or systemic.

- `local-only`: confined to one claim, one line, or one section
- `pattern-level`: reflects a repeated reasoning habit elsewhere in the artifact

If the issue is pattern-level:

- Say so explicitly
- Require a full sweep for the same defect class
- Do not accept a single-line correction as a complete fix

Examples of pattern-level defects:

- Repeated overclaiming from synthetic evidence
- Repeated missing citations
- Repeated vague plan steps with no verification hooks
- Repeated mismatch between detail sections and summary text

## The Editing Pass Rule

**When the author fixes issues, they must do a full editing pass — not piecemeal corrections.**

The failure mode: author fixes the flagged line, leaves three other places that reference the same wrong number. Next review round catches those. Author fixes those, introduces a new inconsistency. Five rounds later, everyone is frustrated.

**Require:** After any High-severity fix, the author must:
1. Search the entire document for every reference to the changed claim/number/finding
2. Update all references
3. Re-read the document from top to bottom for narrative coherence
4. Confirm "I have done a full editing pass" in their revision notes

**If the revision doesn't include "full editing pass" confirmation, send it back.**

## Output Contract

### Severity Levels

| Severity | Meaning | Action |
|----------|---------|--------|
| **High** | Evidence grade overclaimed, internal inconsistency, provenance failure, impossible step, critical omission, production path not demonstrated, load-bearing assumption unverified, ACH matrix shows favoured hypothesis is not best-supported | Must fix before presenting to human |
| **Medium** | Weak citation, incomplete enumeration, vague verification path, missing upgrade path, incomplete mitigation, unsupported but non-critical claim, GRADE downgrade not reflected in language, non-diagnostic evidence cited as support | Should fix; flag if not |
| **Low** | Language could be tighter, minor organisation issues, or small non-blocking precision problems | Fix if convenient |

### Output Format

```markdown
# Critical Peer Review: [artifact name]

Reviewer: [agent model]
Date: [YYYY-MM-DD]
Artifact type: [debugging-analysis | incident-analysis | design-plan | implementation-plan | generated-artifact | technical-reasoning]
Artifact reviewed: [file path or object reviewed]

## Source Inventory
- [artifact / log / diff / command / issue / screenshot checked]
- [artifact / log / diff / command / issue / screenshot checked]

## Hidden Assumptions
[Load-bearing assumptions extracted in step 3, with evidence status]

## ACH Matrix
[Hypothesis x evidence matrix from step 7, with decision rule applied]

## Findings

### High (count: N)
- **Issue**: [what is wrong]
  **Type**: [overclaim | contradiction | omission | unverifiable claim | provenance failure | citation failure | sequencing flaw | scope error]
  **Scope**: [in-window confirmed | out-of-window corroboration | inference | n/a]
  **Evidence grade**: [demonstrated | plausible | possible | speculative | n/a]
  **GRADE factors**: [which downgrade criteria triggered, if applicable]
  **Evidence**: [what the artifact says vs what the evidence supports]
  **Pattern level**: [local-only | pattern-level]
  **Ripple**: [downstream statements affected]
  **Corrected language**: [what it should say]
  **Location**: [file:line or section reference]
  **Next proof step**: [single best next test or verification action]

### Medium (count: N)
[Same format]

### Low (count: N)
[Same format, or brief list]

## Verification
- Files read: [...]
- Commands or queries checked: [...]
- Citations verified: [...]
- Provenance concerns: [...]

## Strongest Hypothesis
[Which finding has the most support and why — per ACH matrix]

## Weakest Hypothesis
[Which finding has the least support and why]

## Pre-Mortem
[Alternative failure scenarios from step 11]

## Fastest Next Test
[One test that would resolve the most uncertainty]

## Overall Assessment
[Ready to present / Needs revision — with specific requirements]
```

**Keep the tone direct. Be specific and critical. Do not soften weak logic.**

## Integration with Systematic Debugging

This skill is invoked automatically by Phase 3d of systematic-debugging. It can also be invoked independently for any technical analysis.

When invoked as Phase 3d self-audit:
- The debugging agent writes the analysis to file
- A clean subagent is dispatched with this skill's audit brief
- The subagent reviews the file and writes findings
- The debugging agent must resolve all High findings before presenting

When invoked independently:
- Point the reviewer at the file: "Review `docs/investigations/2026-03-20-slot-deletion.md` using critical-peer-review"
- The reviewer reads the file and all referenced artifacts
- Findings are written to the same directory or appended to the file's Peer Review section

## Methodological References

- Heuer, R.J. (1999). *Psychology of Intelligence Analysis*. CIA Center for the Study of Intelligence. [ACH]
- Guyatt, G.H. et al. (2008). GRADE: an emerging consensus on rating quality of evidence. *BMJ*, 336(7650), 924-926. [Evidence grading]
- Dewar, J.A. (2002). *Assumption-Based Planning*. RAND Corporation. [Hidden assumptions]
- Klein, G. (2007). Performing a Project Premortem. *Harvard Business Review*, 85(9), 18-19. [Pre-mortem]
- Croskerry, P. (2003). The Importance of Cognitive Errors in Diagnosis. *Academic Emergency Medicine*, 10(11), 1174-1185. [Diagnostic timeout]
- Popper, K.R. (1959). *The Logic of Scientific Discovery*. Hutchinson. [Falsification-first]
