---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes - six-phase framework (root cause investigation, pattern analysis, hypothesis testing, full execution path audit, Toulmin claim verification with falsification, implementation with hardening) that ensures understanding before attempting solutions
user-invocable: true
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Laws

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

```
NO CHANGES WITHOUT WRITTEN PREDICTIONS
```

Every change you make — every single one — must have a written prediction BEFORE you make it: "I expect this change to produce [specific observable result] because [specific reasoning]." If you cannot write that sentence, you do not understand the problem well enough to touch the code. And after every failed attempt: "I predicted X. I observed Y instead. This tells me Z about my model of the system." No second attempt without that written update. This is not optional reflection — it is a mandatory checkpoint.

## Anti-Pattern: "I Think This Should Work"

You try a fix. It fails. You try another. It fails. You try a third. Each attempt starts with "I think this should work" but you never investigated *why the previous attempt failed*. This is cut-and-try — experiments without predictions, without reading, without understanding. It wastes time, introduces new bugs, and digs the hole deeper.

**The pattern:**
1. Something breaks
2. "I think X should fix it" → change X → still broken
3. "OK, maybe Y" → change Y → still broken
4. "Let me also try Z" → change Z → now broken differently

**What went wrong:** You never stopped to read the error, check the docs, or form a falsifiable hypothesis. Each "fix" was a guess. After the first failure, the correct action is: STOP. Read the error. Read the source. Understand *why* it failed. Then form a hypothesis with a prediction you can test.

**If you catch yourself on attempt #2 without having investigated attempt #1's failure: you are doing this anti-pattern. Return to Phase 1.**

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Manager wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - They often contain the exact solution
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Read the Documentation**
   - Before forming any hypothesis, read the official documentation for the component that's failing
   - What does the API/library/tool claim to do? What are its constraints? What version are you on?
   - Read the source as necessary — but docs first. The docs tell you what the system is *supposed* to do; the source tells you what it *actually* does. You need both, but start with intent before implementation
   - Check changelogs and migration guides if you recently upgraded
   - This is your "literature review" — what is already known about this system before you start experimenting?

3. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If not reproducible → gather more data, don't guess

4. **Establish Differential Baseline**

   **MANDATORY.** Before any hypothesis can be formed, establish the concrete difference between the reference state and the current state. Every subsequent claim about root cause must trace back to this differential.

   - **Identify the reference branch:** `main` if working directly, or the base branch if in a worktree/feature branch. Run `git merge-base HEAD <reference>` to find the divergence point.
   - **Run the full differential:** `rtk git diff <merge-base>...HEAD` for all changes since divergence. This is your **evidence universe**.
   - **Review recent commits:** `rtk git log <merge-base>..HEAD --oneline` for the change narrative.
   - **Check non-code changes:** New dependencies, config changes, environmental differences.
   - **Search past sessions:** Use `cc-search-chats search "error message or topic"` to find if this issue was encountered and resolved before.

   **If the differential is empty** (bug exists on the reference branch too): State this explicitly. The contradiction is between the code's behaviour and its specification. Cite the specification, documentation, or test that describes expected behaviour. The evidence universe shifts from "what changed" to "what the code does vs what it should do."

   **This differential gates all subsequent phases.** No claim about root cause is valid unless it references specific lines from this diff (or, for pre-existing bugs, specific lines that contradict the specification).

5. **Gather Evidence in Multi-Component Systems**

   **WHEN system has multiple components (CI → build → signing, API → service → database):**

   **BEFORE proposing fixes, add diagnostic instrumentation:**
   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

   **Example (multi-layer system):**
   ```bash
   # Layer 1: Workflow
   echo "=== Secrets available in workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Layer 2: Build script
   echo "=== Env vars in build script: ==="
   env | grep IDENTITY || echo "IDENTITY not in environment"

   # Layer 3: Signing script
   echo "=== Keychain state: ==="
   security list-keychains
   security find-identity -v

   # Layer 4: Actual signing
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   **This reveals:** Which layer fails (secrets → workflow ✓, workflow → build ✗)

6. **Trace Data Flow**

   **WHEN error is deep in call stack**, trace backward:
   - Where does bad value originate?
   - What called this with bad value?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

### Phase 2: Pattern Analysis

**Find the pattern before fixing:**

1. **Find Working Examples**
   - Locate similar working code in same codebase
   - What works that's similar to what's broken?
   - For structural patterns (function signatures, class hierarchies, decorator usage), use ast-grep — see `using-ast-grep` skill

2. **Compare Against References**
   - If implementing pattern, read reference implementation COMPLETELY
   - Don't skim - read every line
   - Understand the pattern fully before applying

3. **Identify Differences**
   - What's different between working and broken?
   - List every difference, however small
   - Don't assume "that can't matter"

4. **Understand Dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

### Phase 3: Hypothesis and Testing

**No cut-and-try.** Experiments without predictions are just flailing. Every experiment must have a falsifiable prediction stated BEFORE you run it.

**The protocol:**

1. **Do the Reading First**
   - Read error messages, docs, source code for the relevant component
   - Check similar issues in the codebase (git log, grep for past fixes)
   - Understand the system's intended behaviour before hypothesising about its failure
   - This is the "lit review" — what does the system claim to do?

2. **Form Single Falsifiable Hypothesis**
   - State clearly: "I predict that X is the root cause because Y"
   - State the falsification: "If I do Z, I expect to see W. If I see V instead, this hypothesis is wrong."
   - Write both down before touching any code
   - Be specific, not vague
   - **Ground in the differential.** Your hypothesis must cite specific changes from the Phase 1 differential baseline. "I predict X is the root cause because the diff shows [old code] was changed to [new code] at [file:line]." A hypothesis that cannot point to a specific diff (or specification contradiction for pre-existing bugs) is not ready for testing — return to Phase 1.

3. **Test Minimally**
   - Make the SMALLEST possible change to test hypothesis
   - One variable at a time
   - Don't fix multiple things at once

4. **Evaluate Against Prediction (Mandatory Bayesian Update)**
   - Did the result match your prediction? Yes → Phase 3b
   - Did it contradict your prediction? **STOP. Do not attempt another fix. Write the update and present it to the human:**
     - "I predicted [X]. I observed [Y]. This tells me [Z] about my model of the system."
     - "My prior belief was [A]. Given this evidence, I now believe [B]."
     - "This rules out [C] and makes [D] more likely because [E]."
     - "My proposed next hypothesis is [H]. Does this reasoning make sense to you?"
   - **Wait for human feedback before proceeding.** The human may see something you missed. They may redirect you. They may tell you to investigate a different angle entirely. The Bayesian update is a checkpoint, not a formality.
   - DON'T form a new hypothesis and keep going autonomously. DON'T add more fixes on top of a falsified hypothesis.
   - **If you cannot articulate what you learned from the failure, you did not learn anything.** Return to Phase 1 and read more

5. **When You Don't Know**
   - Say "I don't understand X"
   - Don't pretend to know
   - Ask for help
   - Research more

### Phase 3b: FULL EXECUTION PATH AUDIT

**Your hypothesis survived testing. Now PROVE you understand the full picture.**

FULL, COMPREHENSIVE, GRANULAR code audit of the ENTIRE EXECUTION PATH — not just the function where the bug lives, but everything it calls, everything that calls IT, every branch, every edge case, to the boundaries of the project. You are not done until you can account for every line of code the data touches.

**The protocol:**

1. **Trace the call graph OUT from the bug site**
   - Start at the line where the bug manifests
   - Read EVERY function it calls. Read EVERY function THOSE call. Follow the chain to the edges — framework boundaries, I/O, external APIs
   - Then trace BACK: what calls the buggy function? What calls THAT? Trace callers up to the entry point

2. **READ EACH LINE. Not skim. READ.**
   - For every function in the execution path: read it line by line
   - Check: does this line do what you think it does?
   - Check: does your hypothesis account for this line's behaviour?
   - Check: are there other callers of this function that your fix might break?

3. **Verify ALL intended functionality along the path**
   - Not just the failing case. EVERY case that traverses this code path
   - What happens with null? With empty? With maximum? With concurrent access?
   - Does your hypothesis explain ALL observed behaviour, or just the triggering case?

4. **If the audit reveals your hypothesis is INCOMPLETE**
   - STOP. Do not implement a partial fix
   - Return to Phase 3 with the new information
   - A fix that doesn't account for the full path is a fix that creates new bugs

**Loop until the execution path would satisfy a skeptical reviewer who thinks it's impossible to debug with prompting. That reviewer is your human partner. Don't disappoint them.**

### Phase 3c: CLAIM VERIFICATION (Toulmin Analysis)

**You've read the code. You've formed your analysis. Now PROVE every sentence of it.**

Reading code and making claims about what it does are two different cognitive acts. Phase 3b ensures you read the code. Phase 3c ensures the claims you derive from that reading are individually verified, not confabulated.

**The failure mode this prevents:** You read 200 lines of code. You write a bug report with 8 factual claims. 6 are correct. 2 are subtly wrong — you misread a condition, assumed a default, or conflated two similar-looking code paths. Those 2 wrong claims lead to a wrong fix. Your human partner catches it and rightly loses confidence.

**The protocol:**

1. **Write your analysis BEFORE this step** — whatever you would have reported to the user about the root cause, write it out in full.

2. **Decompose into atomic claims.** Go through your analysis sentence by sentence. Every factual assertion is a claim. Extract each one. Be ruthless — "the function returns early when X" is a claim. "The config defaults to Y" is a claim. "Z is called before W" is a claim. If a sentence contains two facts, that's two claims.

3. **For each claim, complete the Toulmin structure:**

   | Field | What it is | Example |
   |-------|-----------|---------|
   | **Claim** | The assertion | "Session token expires because middleware calls `invalidateToken()` on line 147" |
   | **Data** | Differential evidence — what changed or what contradicts spec | "Line 147 was changed from `token_store.refresh(request.token)` to `token_store.invalidate(request.token)` in commit abc123" or "Line 147 is unchanged from main; it contradicts the spec which states tokens should persist" |
   | **Warrant** | Why the data supports the claim | "The `invalidate` method marks the token as expired in the store, per its docstring on line 23 of `token_store.py`" |
   | **Qualifier** | Confidence level | "Certainly" / "Probably" / "Possibly — haven't verified X" |
   | **Rebuttal** | What would make this claim false | "If `invalidate()` is a no-op in test mode, or if a different code path re-validates before this runs" |

   **Narrow claims only.** Each claim must be as narrow as possible — tied to a specific diff line or specification contradiction. No broad characterisations ("the module is broken"). No assertions without differential evidence ("line 50 is wrong" without showing what it was changed from or what specification it violates).

4. **For each claim: design and run a falsification experiment.** The experiment must be the fastest possible test that could disprove the claim. Priorities:
   - Grep/read to verify the specific line says what you claim it says
   - Run a targeted test with a diagnostic assertion
   - Add a temporary log line and trigger the code path
   - Check configuration/environment values

   **Every claim gets tested.** No exceptions. No "this one is obvious." Obvious claims are the ones most likely to be wrong because you didn't bother checking.

5. **Interrogate the experiment (Quine-Duhem).** A falsification experiment never tests a claim in isolation. It tests the claim AND every auxiliary hypothesis the experiment depends on: your test setup, your input data, your measurement method, your environment. When results contradict your prediction, the claim might be wrong — or the experiment might be. (Quine-Duhem problem; cf. Ben Recht, "Devezer's Urn".)

   **Before concluding from ANY experiment result, ask:**
   - **Did I test what I think I tested?** Am I running the actual code from the codebase, or a copy I transcribed into a REPL? Did I import the right module? Am I testing the right code path?
   - **Is my test input what the system actually receives?** Did I verify the real input, or am I guessing what it looks like?
   - **Is my measurement correct?** Am I checking the right output? Could there be a stdout/stderr confusion, a format difference, or a timing issue?

   **Corroborate.** No claim is settled by one experiment from one method. If you tested in a REPL, also verify in situ. If you read a config file, also check what the runtime actually loaded. Two independent paths to the same conclusion.

   **When results surprise you:** Your first move is to question the experiment, not the hypothesis. Identify the weakest auxiliary (the assumption you're least certain about) and test IT before updating your beliefs about the claim.

   **When you can't resolve ambiguity:** If experiment and corroboration disagree, or you've tested auxiliaries and still can't determine which is wrong — STOP. Present both results to the human with your analysis of what might explain the disagreement. This is a mandatory human checkpoint: genuine Quine-Duhem ambiguity requires human judgment, not more autonomous guessing.

6. **Record results.** For each claim:
   - **Confirmed:** Data matches, experiment corroborated via second method. State what you observed and how you corroborated.
   - **Falsified:** Claim is wrong AND you verified the experiment itself was sound. State what you found instead. Return to Phase 3 with corrected understanding.
   - **Indeterminate:** Couldn't conclusively test, or experiment and corroboration disagree. Downgrade qualifier to "Possibly" and flag for the user.
   - **Auxiliary failure:** Experiment was unsound — the test itself was wrong. Discard result, fix the test, re-run. Do NOT count this as evidence for or against the claim.

7. **Find the epistemic boundary.** After all claims are tested, explicitly state:
   - What you know with high confidence (confirmed claims)
   - What you believe but haven't fully verified (indeterminate claims)
   - What you initially believed but found to be wrong (falsified claims)

   **Present this boundary to the user.** "I'm confident about X and Y. I believe but haven't fully verified Z. I initially thought W but found it's actually V."

**Output format when reporting to the user:**

```
## Root Cause Analysis

[Your narrative analysis here]

### Claim Verification

| # | Claim | Evidence | Falsification | Result |
|---|-------|----------|---------------|--------|
| 1 | [claim] | [file:line] | [experiment] | Confirmed/Falsified/Indeterminate |
| 2 | ... | ... | ... | ... |

### Epistemic Boundary
- **High confidence:** [claims 1, 3, 5]
- **Moderate confidence:** [claim 4 — couldn't test X]
- **Corrected:** [claim 2 — initially thought X, actually Y]
```

**Delegating experiments to subagents:** Subagents don't have this skill loaded. When delegating a falsification experiment, you MUST include the differential protocol and the interrogation protocol in the prompt:

```
DIFFERENTIAL BASELINE:
Reference branch: [branch name]
Merge base: [commit hash]

You MUST ground every claim in the differential between the reference and current state.
Run `rtk git diff [merge-base]...HEAD -- [relevant files]` to see what changed.
Every claim about root cause must cite a specific line from this diff.
If the bug exists on the reference branch too, state this explicitly and cite the
specification instead.
No broad claims. Each assertion must be as narrow as possible and tied to a specific diff.

EXPERIMENT:
Run this experiment: [describe experiment]
I predict: [expected result]

AFTER getting results, BEFORE reporting back:
1. Verify you tested the actual production code, not a transcription or mock
2. Verify your test input matches what the system really receives (check, don't assume)
3. Verify your measurement — right output stream, right format, right assertion
4. Corroborate via one different method (if you grepped, also run the code; if you ran a test, also read the source)
5. If experiment and corroboration disagree, report BOTH — do not pick one

Report: what you observed, how you corroborated, the differential evidence you found,
and any auxiliary assumption you're uncertain about.
```

**The main agent must still verify subagent reports.** Subagent says "confirmed"? Spot-check the corroboration. Subagent says "falsified"? Verify the experiment was sound before updating your beliefs. Delegation does not transfer epistemic responsibility.

**If ANY claim is falsified:** STOP. Do not proceed to Phase 4. Your analysis contains at least one error. Return to Phase 3 with the corrected understanding and re-derive your analysis.

**If claims are indeterminate:** Flag them prominently for the user. They may accept the risk or ask for deeper investigation.

**Why every sentence matters:** A bug report that's 75% correct is worse than no report at all — it gives false confidence. The wrong 25% poisons the fix. You must know exactly which parts of your analysis are proven and which are assumptions.

### Phase 4: Implementation

**Fix the root cause, not the symptom:**

1. **Create Failing Test Case**
   - Simplest possible reproduction
   - Automated test if possible
   - One-off test script if no framework
   - MUST have before fixing
   - **REQUIRED SUB-SKILL:** Use denubis-plan-and-execute:test-driven-development for writing proper failing tests

2. **Implement Single Fix**
   - Address the root cause identified
   - ONE change at a time
   - No "while I'm here" improvements
   - No bundled refactoring

3. **Verify Fix — POST-FIX AUDIT**
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved?
   - **RE-READ your changes AND the surrounding execution path line by line.** Does the fix handle every case you found in Phase 3b? Did you introduce new assumptions? Would a skeptical reviewer accept this as COMPLETE?

4. **If Fix Doesn't Work**
   - STOP
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If ≥ 3: STOP and question the architecture (step 5 below)**
   - DON'T attempt Fix #4 without architectural discussion

5. **If 3+ Fixes Failed: Question Architecture**

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **STOP and question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Should we refactor architecture vs. continue fixing symptoms?

   **Discuss with your human partner before attempting more fixes**

   This is NOT a failed hypothesis - this is a wrong architecture.

### Phase 5: Hardening Suggestion

**The bug is fixed. The tests pass. You audited the execution path. Now make the code RESIST bugs of this nature.**

You have full context from the path audit — you know the execution path, the callers, the edge cases. Use that knowledge.

**Suggest ONE small, focused refactor** that would make this class of bug structurally harder to introduce. Present it to the user for approval. Do NOT implement without asking.

Examples:
- Extract a validation at the boundary that would catch bad data before it propagates
- Add a type constraint that makes the invalid state unrepresentable
- Rename a misleading variable that contributed to the confusion
- Add an assertion that would have caught this immediately

**Rules:**
- ONE suggestion. Not a wishlist. Not "while we're here"
- It must be SMALL — a single function, a type change, a guard clause
- It must be directly motivated by THIS bug and THIS execution path
- The working tests from Phase 4 are your safety net — use them
- If the user says no, move on. This is a suggestion, not a mandate

## Red Flags - STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals new problem in different place**
- **"This claim is obvious, I don't need to verify it"** — obvious claims are the ones most likely to be wrong
- **"I read the code, so my analysis is correct"** — reading and correctly interpreting are different acts
- **Writing a bug report without running falsification experiments on each claim**
- **Proposing a root cause without citing the differential** — no diff evidence, no claim
- **Making broad assertions** ("the module is broken", "the logic is wrong") **without narrow differential evidence**
- **"Flaky upstream, we can disregard"** — almost always a symptom of something real. Investigate it.

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (see Phase 4.5)

## your human partner's Signals You're Doing It Wrong

**Watch for these redirections:**
- "Is that not happening?" - You assumed without verifying
- "Will it show us...?" - You should have added evidence gathering
- "Stop guessing" - You're proposing fixes without understanding
- "Ultrathink this" - Question fundamentals, not just symptoms
- "We're stuck?" (frustrated) - Your approach isn't working

**When you see these:** STOP. Return to Phase 1.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |
| "I read the code, my analysis is correct" | Reading ≠ correctly interpreting. Verify each claim independently. |
| "This claim doesn't need verification" | The claim you skip verifying is the one that's wrong. Every claim. |
| "The root cause is obvious from reading the code" | Show the diff. Point to the specific change. No diff, no claim. |
| "The whole module/system is broken" | Too broad. Which specific line changed? What specifically contradicts what? |
| "Flaky upstream, we can disregard" | Almost always a symptom of something real. Intermittent failures have root causes. Investigate. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, establish differential baseline, gather evidence | Understand WHAT and WHY; diff gates all claims |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **3b. Path Audit** | FULL execution path audit, line by line, to project edges | Every line accounted for |
| **3c. Claim Verification** | Toulmin analysis of every claim, falsification experiments | Every claim confirmed or flagged |
| **4. Implementation** | Create test, fix, post-fix audit, verify | Bug resolved, tests pass, path clean |
| **5. Hardening** | Suggest ONE small refactor to resist this bug class | User-approved or declined |

## When Investigation Reveals a Preexisting Bug

You investigated thoroughly. The bug exists on `main`. It predates your work. **This is a finding, not a dismissal.**

"Preexisting" and "flaky" are never exit ramps. They are diagnoses that require action:

1. **Document what you found.** Root cause, affected code paths, reproduction steps.
2. **Offer a path to the human.** Do not silently move on. Present options:
   - "This is preexisting. Want me to set up a worktree and give you a prompt to fix this in a separate session?"
   - "This is intermittent. Want me to create an issue with the reproduction steps?"
   - "This is upstream. Want me to file a bug report?"
3. **Get explicit acknowledgement.** The human decides whether to fix now, defer, or accept. You do not get to decide that a bug is someone else's problem.

**No silent flaky.** If a test passes sometimes and fails sometimes, that is a real bug with a real root cause. Intermittent failures have deterministic causes — race conditions, state leakage, ordering dependencies, resource exhaustion. "Flaky" is a description of the symptom, not a diagnosis. Investigate it like any other bug, or refer it to a separate session. Never silently ignore it.

## When Process Reveals "No Root Cause"

If systematic investigation reveals issue is truly environmental, timing-dependent, or external:

1. You've completed the process
2. Document what you investigated
3. Implement appropriate handling (retry, timeout, error message)
4. Add monitoring/logging for future investigation

**But:** 95% of "no root cause" cases are incomplete investigation.

## Integration with Other Skills

**This skill requires using:**
- **test-driven-development** - REQUIRED for creating failing test case (see Phase 4, Step 1)

**Complementary skills:**
- **coding-effectively** - Includes `defense-in-depth` for adding validation at multiple layers
- **verification-before-completion** - Verify fix worked before claiming success

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common
