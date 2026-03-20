---
name: critical-peer-review
description: Use when reviewing debugging analyses, postmortems, incident investigations, or another agent's technical reasoning for overclaiming, internal inconsistency, and evidence-grade violations - falsification-first audit that treats prior output as untrusted
user-invocable: true
---

# Critical Peer Review

Evidence-led review of technical analyses, debugging reports, postmortems, and incident investigations. Treats prior reasoning as something to audit, not trust. (Adapted from Codex critical-crash-review protocol.)

## Core Principle

**The analysis you are reviewing was produced by a system that is incentivised to sound confident.** Your job is to find where that confidence outstrips the evidence. Every claim must earn its grade.

## When to Use

- Reviewing a debugging analysis (Phase 3d self-audit in systematic-debugging)
- Reviewing a postmortem or incident report
- Reviewing another agent's technical reasoning
- Reviewing your own prior analysis after being told you overclaimed
- Any time a technical document makes causal claims that affect decisions

## Workflow

### 1. Establish the evidence universe

Read the exact artifacts first:

- The analysis document being reviewed
- Failing logs, test output, stack traces it references
- Source files and diffs it cites
- Prior reviewer notes if any exist

**Call out missing evidence immediately.** If the analysis references artifacts you cannot access, flag this — you cannot verify claims about evidence you haven't seen.

When the evidence includes logs, timelines, or counts:
- Note file path, line count, timestamp range, timezone
- Choose one reference timezone for cross-source comparison
- Never assume all sources share the same timezone

**Positive control:** Before trusting any filter or query result, verify it against one event you already know must appear. If a query returns zero, re-run the positive control before reporting "no evidence."

### 2. Protect provenance

Assume tmp directories, logs, and generated outputs may be contaminated.

Check:
- Whether local reruns may have overwritten server artifacts
- Whether copied files still point at the original context
- Whether "latest" files may actually be from a different run

Treat provenance failure as a first-class finding. A contaminated log weakens every downstream claim.

### 3. Separate facts from inference

Tag every statement in the analysis:

- **Fact:** directly observed, reproduced, or read from code/diff/logs
- **Inference:** derived from facts via reasoning
- **Speculation:** plausible but not grounded in evidence

If speculation has borrowed the confidence of a fact — if an inference reads like a fact — flag it. Name every assumption an inference depends on.

For incident and postmortem review, every finding should also carry:
- A scope tag: `in-window confirmed`, `out-of-window corroboration`, or `inference`
- A confidence tag per the evidence grading scale (see below)

Any number without a reproducible command or query is `unverified`. Any count derived from an unfiltered or wrong-window source is also `unverified` until rerun correctly.

### 4. Audit the reasoning

Review the analysis as if it were a code review from someone whose work you do not trust.

**Look for:**

- Unsupported jumps from symptom to mechanism
- Multiple variables collapsed into one hypothesis
- "Same version" claims that ignored env, permissions, or temp paths
- Conclusions drawn from overwritten or mixed artifacts
- Findings that mix in-window facts with out-of-window corroboration
- Incomplete enumeration (searched for expected categories instead of listing all)
- Counts reported without the exact command that produced them
- Fixes proposed before causal mechanism isolation
- **Synthetic test results extended to production paths** — the most common overclaim
- **Universal quantifiers** ("all", "every", "only") that were not universally verified
- **Internal inconsistency** — counts that don't sum, summaries that contradict details, scope claims that don't match evidence

**State plainly which hypothesis is weakest and why.**

### 5. Check evidence grades

Apply the evidence grading scale to every finding in the analysis:

| Grade | Label | Positive border | Negative border | Production path |
|-------|-------|----------------|-----------------|-----------------|
| **High** | **Demonstrated** | Mechanism triggers failure | Removing mechanism prevents failure | Both tested on actual production code path |
| **Moderate** | **Plausible** | Evidence points here; one border shown | Not yet shown removal prevents it | Production path inferred but not confirmed |
| **Low** | **Possible** | Mechanism triggers failure in synthetic test | Production path unconfirmed | Neither border on production path |
| **Very low** | **Speculative** | Hypothesis among several; untested | — | No border evidence |

**For each finding, verify:**
- Does the language match the grade?
- Did the author write "demonstrated" for something that's only "plausible"?
- Did the author write "the mechanism is X" when they mean "mechanism X is plausible"?
- Did a synthetic test result get extended to a production path without bridging evidence?
- Were both borders tested for any "demonstrated" claim?

### 6. Verify citations

For every file:line reference in the analysis:
- Does the file exist at that path?
- Does the line contain what is claimed?
- Is the line number current (not from a stale read)?

For every count or number:
- Can you reproduce it with the stated command?
- If not stated: flag as unverified

### 7. Re-rank hypotheses

Prefer narrow, mechanistic hypotheses over broad labels.

Bad: "the auth system is broken"
Better: "the token validation at `auth.py:147` rejects valid tokens when `expires_at` falls within the refresh window"

Prefer maximally risky statements. The stronger the claim, the more useful the test. Then try to shatter the claim. If it survives a serious falsification attempt, it has earned attention.

For incidents, prefer contributing-factor chains over single "root cause" labels unless the evidence genuinely collapses to one mechanism.

### 8. Design the smallest discriminating test

For each finding that is below "demonstrated" grade, identify the single test that would buy the most certainty. State:

- Why this hypothesis has explanatory power
- Prediction if the hypothesis is true
- Prediction if it is false
- What result would actually change the grade

## The Ripple Rule

**When issues are found, trace the ripples before reporting.**

A finding is rarely isolated. If a count is wrong in one place, every place that references or derives from that count may also be wrong. If a scope claim is too broad, every conclusion that depends on that scope is weakened.

**The protocol:**
1. Find an issue
2. **Before writing it up:** search the document for every reference to the affected claim, number, or finding
3. List all downstream statements that depend on the incorrect claim
4. Report the issue AND its ripple effects as a single finding

**Example:** "Category 3 is described as 71 error-seconds, but the classifier output shows 48. This also affects: (a) the 216/550 total in the status line, (b) the percentage calculation in the summary, (c) the priority ranking in the recommendations section."

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
| **High** | Evidence grade overclaimed, internal inconsistency, production path not demonstrated | Must fix before presenting to human |
| **Medium** | Missing upgrade path, weak citations, incomplete enumeration | Should fix; flag if not |
| **Low** | Language could be tighter, minor style | Fix if convenient |

### Output Format

```markdown
# Critical Peer Review: [document name]

Reviewer: [agent model]
Date: [YYYY-MM-DD]
Document reviewed: [file path]

## Findings

### High (count: N)
- **Issue**: [what is overclaimed or inconsistent]
  **Evidence**: [what the analysis says vs what the evidence supports]
  **Ripple**: [downstream statements affected]
  **Corrected language**: [what it should say]
  **Location**: [file:line or section reference]

### Medium (count: N)
[Same format]

### Low (count: N)
[Same format, or brief list]

## Verification
[What you checked independently — commands run, files read, citations verified]

## Strongest Hypothesis
[Which finding has the most support and why]

## Weakest Hypothesis
[Which finding has the least support and why]

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
