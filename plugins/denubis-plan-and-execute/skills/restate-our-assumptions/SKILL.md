---
name: restate-our-assumptions
description: Use for periodic review of dependency assumptions, when dependency-rationale.md may be stale, or before major releases - applies Popper (falsification), Lakatos (research programmes), and Haraway (situated knowledge) to each dependency with codebase evidence
user-invocable: true
---

# Restate Our Assumptions

> "Restate our assumptions." — Max Cohen, *Pi* (1998)

## Overview

Periodically audit the project's dependency assumptions by applying three philosophical lenses. The goal is not philosophical exercise — it's finding dependencies whose justifications no longer hold, whose role has shifted, or whose beneficiaries have changed.

Every claim in `docs/dependency-rationale.md` was true when written. This skill tests whether it's still true today.

## Theoretical Framework

Three lenses, each asking a different question:

| Lens | Question | Method |
|------|----------|--------|
| **Popper** | Can we break this claim? | Search the codebase for evidence that contradicts or outgrows the stated justification |
| **Lakatos** | Is this dependency's role progressing or degenerating? | Classify as hard core vs protective belt; check if we're patching around it |
| **Haraway** | For whom does this dependency exist? | Identify who benefits, who bears the cost, and whose perspective justified the choice |

### References

- Popper, K. (1963). *Conjectures and Refutations*. Routledge. — Falsifiability as demarcation; a claim that cannot be tested is not a useful claim.
- Lakatos, I. (1978). *The Methodology of Scientific Research Programmes*. Cambridge University Press. — Hard core (protected assumptions) vs protective belt (adjustable auxiliaries); progressive programmes predict new facts, degenerating ones only accommodate old ones.
- Haraway, D. (1988). Situated Knowledges. *Feminist Studies*, 14(3), 575–599. — All knowledge is partial and situated; objectivity requires naming the perspective, not claiming none.
- See also: Kudina, O., Ballsun-Stanton, B., & Alfano, M. (2025). The use of large language models as scaffolds for proleptic reasoning. *Asian Journal of Philosophy*, 4, 24. https://doi.org/10.1007/s44204-025-00247-1

## When to Use

- Quarterly dependency review
- Before major releases
- When `docs/dependency-rationale.md` hasn't been reviewed in >3 months
- When someone questions whether a dependency is still needed
- After significant refactoring that may have changed dependency usage patterns

## Prerequisites

`docs/dependency-rationale.md` must exist. If it doesn't, run the controlled-dependency-upgrade skill first — its audit phase creates the rationale file.

## Workflow

### Step 1: Read the Rationale

Read `docs/dependency-rationale.md`. For each dependency, note:
- The stated claim
- The listed evidence (file paths)
- When it was last reviewed
- Who it serves

Create a task per dependency using TaskCreate.

### Step 2: Apply Three Lenses Per Dependency

For **each** dependency, search the codebase and apply all three lenses. The analysis must cite specific files and line numbers — philosophy without evidence is speculation.

#### Popper: Falsification

Take the stated claim and try to break it.

1. **Test the claim's boundaries.** If the claim says "used for HTTP calls to weather API," search for all uses of the package. Are there uses beyond weather? The claim is falsified if scope has grown.
2. **Test the evidence.** Do the listed evidence files still exist? Do they still import the package? If not, the evidence trail is broken.
3. **Test for replaceability.** Could the claimed function be served by something already in the dependency tree? If `httpx` is already a transitive dep and the claim is "HTTP client," the justification for a separate `requests` dependency weakens.

**Output per dependency:**

```markdown
### Popper: requests
- **Claim tested:** "HTTP client for external API calls to weather service"
- **Evidence found:** `import requests` in src/api/client.py:12, src/fetcher.py:34, src/health_check.py:5
- **Verdict:** FALSIFIED — usage extends beyond weather service (health_check.py). Claim needs broadening.
```

Verdicts: **CORROBORATED** (evidence supports claim), **FALSIFIED** (evidence contradicts claim), **UNFALSIFIABLE** (claim too vague to test), **STALE** (evidence files no longer exist).

#### Lakatos: Research Programmes

Classify the dependency's role and assess whether it's progressing or degenerating.

1. **Hard core or protective belt?** A hard core dependency is foundational — replacing it means rearchitecting. A protective belt dependency is auxiliary — it could be swapped for an alternative without structural change.
2. **Progressive or degenerating?** Check git history. Has the dependency been involved in workarounds, compatibility shims, or pinned versions? That's degeneration — we're making ad hoc adjustments to preserve the dependency rather than the dependency enabling new capabilities.

**Output per dependency:**

```markdown
### Lakatos: boto3
- **Classification:** Protective belt (S3 is the auxiliary choice; cloud storage is the hard core commitment)
- **Programme status:** DEGENERATING — pinned to <1.29 due to breaking change in S3 event notifications (commit abc123). Two workarounds in s3_handler.py since 2024-10.
- **Implication:** Consider whether the workarounds protect a productive programme or sustain a commitment we should revisit.
```

Statuses: **PROGRESSIVE** (enabling new capabilities, clean integration), **STABLE** (working as expected, no pressure), **DEGENERATING** (workarounds accumulating, pinned versions, compatibility issues).

#### Haraway: Situated Knowledge

Name the perspective that justified this dependency and ask who's missing.

1. **Whose perspective?** Who chose this dependency? What was their role? A backend developer choosing `requests` reflects a synchronous-HTTP worldview. An ops engineer might have chosen differently.
2. **Who benefits?** Runtime users, developers, CI, type system? Be specific.
3. **Who bears the cost?** Vendor lock-in falls on future maintainers. Performance overhead falls on users. Build complexity falls on CI.
4. **Whose perspective is absent?** Who wasn't consulted? Security auditors? Performance engineers? The person who'll maintain this in two years?

**Output per dependency:**

```markdown
### Haraway: boto3
- **Perspective:** Backend developer with AWS access and familiarity
- **Benefits:** Runtime users (document storage works), developers (familiar SDK)
- **Costs borne by:** Future maintainers (AWS vendor lock-in), finance (S3 egress costs at scale), compliance (data residency tied to AWS regions)
- **Absent perspectives:** Cost modelling at scale, multi-cloud contingency, data sovereignty review
```

### Step 3: Synthesise Findings

After analysing all dependencies, produce a structured report:

```markdown
# Dependency Assumptions Review — YYYY-MM-DD

## Summary
[2-3 sentence overview of findings]

## Findings

### <package-name>
**Current claim:** [from rationale file]
**Popper:** [verdict + one-line summary]
**Lakatos:** [classification + status + one-line summary]
**Haraway:** [perspective + key absent voice]
**Recommendation:** [RETAIN / UPDATE CLAIM / INVESTIGATE REPLACEMENT / REMOVE]

### <next-package>
[Same structure]

## Patterns Observed
[Cross-cutting observations: are most programmes progressive or degenerating? Is one perspective dominating all choices? Are claims getting vaguer over time?]

## Actions
- [ ] [Specific, actionable items arising from the review]
```

### Step 4: Present to User and Wait

Present the full report. **Do not update `docs/dependency-rationale.md` or any other file.** The findings are inputs to the user's judgement, not autonomous verdicts.

The user decides:
- Which claims to update and how
- Which dependencies to investigate further
- Which absent perspectives matter for this project
- Whether a degenerating programme warrants action or is acceptable technical debt

**Wait for the user to direct changes.** Only update files when the user tells you what to change and how.

## Key Principles

| Principle | Rationale |
|-----------|-----------|
| Evidence from the codebase, not speculation | Cite files and line numbers. Philosophy without evidence is unfounded. |
| Popper and Lakatos on every dependency; Haraway when someone bears invisible cost | Popper catches stale claims. Lakatos catches degenerating commitments. Haraway catches invisible costs — include it for vendor lock-in, data residency, accessibility, security, cost distribution. Omit for stdlib or single-purpose utilities where the perspective analysis adds no insight. |
| Present findings, don't make changes | The review produces analysis for human judgement. The human decides what to act on. |
| The human decides | Findings are inputs to judgement, not verdicts. Present and wait. |

## Red Flags — STOP

If you find yourself reasoning any of these, you're rationalising:
- "The philosophy is overkill for a small project" → Small projects accumulate debt fastest. Review anyway.
- "I already know these packages are fine" → The point is to test that assumption. Review anyway.
- "I'll just check imports, skip the Lakatos analysis" → Lakatos catches degenerating commitments. Always include it. Haraway when someone bears invisible cost.
- "I can do this analysis without searching the codebase" → Philosophy without evidence is speculation. Search.
- "The rationale file is up to date, no review needed" → Rationale files describe intent; the codebase describes reality. They drift. Review.
- "I'll update the rationale file based on my findings" → Present findings to the user. They decide what changes.
- "This claim is obviously wrong, I'll just fix it" → Obvious to you. The user may have context you lack. Present, don't fix.
