---
name: impl-plan-write
family: starting-an-implementation-plan
description: Use when design is complete and you need detailed implementation tasks - produces plans with exact file paths, code examples, and verification steps
user-invocable: false
---

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to verify it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the impl-plan-write skill to create the implementation plan."

**Save plans to:** `docs/implementation-plans/YYYY-MM-DD-<feature-name>/phase_##.md`

## Critical: Design Plans Provide Direction, Not Code

**Design plans are intentionally high-level.** They describe components, modules, and contracts — not implementation code. This is by design.

**You MUST generate code fresh based on codebase investigation.** Do NOT copy code from the design document. Even if a design plan contains code examples (it shouldn't, but some might), treat them as illustrative only.

**Why this matters:**
- Design plans may be days or weeks old
- Codebase state changes between design and implementation
- Investigation reveals actual patterns, dependencies, and constraints
- Your code must work with the codebase as it exists NOW

**The design plan tells you WHERE you're going. Codebase investigation tells you HOW to get there from where you are.**

## Before Starting

**REQUIRED: Verify scope and codebase state**

### 1. Scope Validation

Count the phases/tasks in the design plan.

**If design plan has >8 phases:** STOP. Refuse to proceed.

Tell the user:
"This design has [N] phases, which exceeds the 8-phase limit for implementation plans. Please rerun this skill with a scope of no more than 8 phases. You can:
1. Select the first 8 phases for this implementation plan
2. Break the design into multiple implementation plans
3. Simplify the design to fit within 8 phases"

**If already implementing phases 9+:** The user should provide the previous implementation plan as context when scoping the next batch.

### 2. Codebase Verification

**You MUST verify current codebase state before EACH AND EVERY PHASE. Use `codebase-investigator` to prove out your hypotheses and to ensure that current state aligns with what you want to write out.**

**YOU MUST verify current codebase state before writing ANY task.**

**DO NOT verify codebase yourself. Use codebase-investigator agent.**

**Provide the agent with design assumptions so it can report discrepancies:**

Dispatch one subagent codebase-investigator to understand testing behavior for this project.
- **DO NOT prescribe new requirements around testing. Follow how the codebase does it.**
   - For example: do NOT stipulate TDD unless you understand the scope of the problem to be a predominantly functional one OR you receive direction from a human otherwise and do not assume that mocking databases or other external dependencies is acceptable. 
- If you find problems that are difficult to test in isolation with mocks, you should surface questions to the human operator as to how they want to proceed.
- Instruct the subagent to seek out CLAUDE.md or AGENTS.md files that include details on testing behavior, logic, and methodology, and include file references for you to provide in your plan for the executor to pass to its subagents.

Dispatch a second subagent codebase-investigator (simultaneously) with:
- "The design assumes these files exist: [list with expected paths/structure from design]"
- "Verify each file exists and report any differences from these assumptions"
- "The design says [feature] is implemented in [location]. Verify this is accurate"
- "Design expects [dependency] version [X]. Check actual version installed"
- For verifying API surfaces, class hierarchies, or usage patterns, instruct the investigator to use ast-grep for structural searches (see `using-ast-grep` skill)

**Example query to agent:**
```
Design assumptions from docs/plans/YYYY-MM-DD-feature-design.md:
- Auth service in src/services/auth.py with login() and logout() functions
- User model in src/models/user.py with email and password fields
- Test file at tests/services/test_auth.py
- Uses argon2-cffi dependency for password hashing

Verify these assumptions and report:
1. What exists vs what design expects
2. Any structural differences (different paths, functions, signatures)
3. Any missing or additional components
4. Current dependency versions (check pyproject.toml / uv.lock)
```

Review investigator findings and note any differences from design assumptions.

**Based on investigator report, NEVER write:**
- "Update `main.py` if exists"
- "Modify `config.py` (if present)"
- "Create or update `types.py`"

**Based on investigator report, ALWAYS write:**
- "Create `<src>/auth.py`" (investigator confirmed doesn't exist)
- "Modify `<src>/main.py:45-67`" (investigator confirmed exists, checked line numbers)
- "No changes needed to `config.py`" (investigator confirmed already correct)

**Teaching-material placeholder convention:** Illustrative file paths in this skill use angle-bracket prefixes — `<src>/auth.py`, `<tests>/services/test_auth.py` — so they are not audited by the cross-reference tool (see `docs/issues.md` ISSUE-01 and Phase 5 of the 2026-04-17 skill-skills upstream sync plan). Real file references use path-form without angle brackets.

**If codebase state differs from design assumptions:** Document the difference and adjust the implementation plan accordingly.

### 3. External Dependency Research

**When phases involve external libraries or dependencies, research them before writing tasks.**

Use a tiered approach—start with documentation, escalate to source code only when needed.

#### Tier 1: Internet Researcher (default)

Use `internet-researcher` for:
- Official documentation and API references
- Common usage patterns and examples
- Standard specifications (OAuth2, JWT, HTTP, etc.)
- Best practices and known gotchas

**This handles ~80% of external dependency questions.** Most integration work follows documented patterns.

#### Tier 2: Remote Code Researcher (escalation)

Use `remote-code-researcher` when:
- Documentation doesn't cover your edge case
- You need to understand internal implementation for extension/customization
- Docs describe *what* but you need to know *how*
- Behavior differs from docs and you need ground truth
- You're extending or hooking into library internals

#### Decision Framework

```
Phase involves external dependency?
├─ No → codebase-investigator only
└─ Yes → What do we need to know?
    ├─ API usage, standard patterns → internet-researcher
    ├─ Standard/spec implementation → internet-researcher
    ├─ Implementation internals, extension points → remote-code-researcher
    └─ Both local state + external info → combined-researcher
```

#### When to Dispatch

**Dispatch internet-researcher when phase mentions:**
- External packages/libraries to integrate
- Third-party APIs to call
- Standards to implement (OAuth, JWT, OpenAPI, etc.)

**Escalate to remote-code-researcher when:**
- Internet-researcher returns "docs don't cover this"
- Task requires extending library behavior
- Task requires matching internal patterns not in docs
- You need to understand error handling, edge cases, or internals

#### Reporting Findings

Include external research findings alongside codebase verification:

```markdown
**External dependency investigation findings:**
- ✓ Stripe SDK uses `stripe.customers.create()` with params: {email, name, metadata}
- ✓ OAuth2 refresh flow per RFC 6749 Section 6
- ✗ Design assumed sync API, but library is async-only
- + Error handling uses typed exception hierarchy (StripeError subclasses)
- 📖 Source: [Official docs | RFC spec | Source code @ commit]
```

**Standards vs Implementation:** Standards questions (e.g., "how does OAuth2 work") are internet-researcher territory. Implementation questions (e.g., "how does auth0-js store tokens") may require remote-code-researcher.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes).**

For functionality tasks:
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

For infrastructure tasks:
- "Create the config file" - step
- "Verify it works (install, build, run)" - step
- "Commit" - step

**Task dependencies MUST be explicit and sequential:**
- Task N requires helper function? Task N-1 creates it.
- Task N requires bootstrap credentials? Prior task provisions them.
- Never write code that assumes "this will exist somehow."

**Consumer-tracing requirement:** Every new function, class, or field in a task must name its call site — what existing or planned code will invoke it and in which task. No call site = no function. This catches orphaned code at planning time. If a function's only consumer is "will be used later," it doesn't belong in this task.

## Task Types: Infrastructure vs Functionality

**Match task structure to what the design phase specifies.**

The design plan distinguishes between infrastructure phases (verified operationally) and functionality phases (verified by tests). Your implementation tasks must honor this distinction.

| Phase Type | Task Structure | Verification |
|------------|----------------|--------------|
| Infrastructure | Create files, configure, verify operationally | Commands succeed (install, build, run) |
| Functionality | Write tests, implement, verify tests pass | Tests pass for the behavior |
| Preparatory-refactor | Restructure existing code for upcoming phase | Tests stay green after restructuring |

**Preparatory-refactor phases** (Beck's "make the change easy"):
- Inserted by the planner when codebase investigation reveals structural impediments in files an upcoming phase will modify
- Goal always references the upcoming phase it enables (e.g., "Restructure auth middleware to enable Phase 3's OAuth2 integration")
- **Verifies: None** — verification is that tests stay green after restructuring
- Uses the three-subagent refactoring pipeline (smell-assessor → critical-peer-review → refactoring-executor) with "structural readiness" framing
- No new tests written (refactoring preserves behaviour, Two Hats discipline)
- Do NOT insert for phases that only create new files — there is nothing to restructure

**Infrastructure tasks** (project setup, config files, dependencies):
- Don't force TDD on scaffolding
- Verification = operational success (`uv sync`, `uv run ruff check`)
- **Verifies: None** — explicitly state this, don't invent ACs for setup phases

**Functionality tasks** (code that does something):
- Tests are deliverables alongside code
- Each task lists which ACs it verifies (e.g., "Verifies: AC1.1, AC1.3")
- Tests must verify those specific AC cases, not just "test the code"
- Phase ends with passing tests for all ACs listed in the phase's AC Coverage

**Test behavior, not implementation.**
- Test that your function produces the right output, not that it called dependencies a certain way
- If you refactored internals but behaviour stayed the same, would the test still pass? If no, you're testing implementation details.
- The AC is the spec: "Invalid password returns 401" means test the response, not verify that `argon2.verify()` was called

**What doesn't need tests:**
- Type annotations (type checker verifies these — use `ty` or `mypy`)
- Dependencies that have their own tests (don't re-test them through your code)
- How you call things (test the result, not the wiring)
- Infrastructure/setup (verify operationally)

**Subcomponent task grouping.** Design plans structure phases as subcomponents: types → implementation → tests. When writing tasks for a subcomponent, wrap them in subcomponent markers (see "Task and Subcomponent Markers" section):

```markdown
<!-- START_SUBCOMPONENT_A (tasks 1-3) -->
<!-- START_TASK_1 -->
### Task 1: TokenPayload model and TokenConfig
...
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: TokenService implementation
...
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: TokenService tests
...
<!-- END_TASK_3 -->
<!-- END_SUBCOMPONENT_A -->
```

The execution agent uses these markers to identify related tasks. The tests task proves the subcomponent works.

**Read the design plan's "Done when" section.** If it says "build succeeds," don't invent unit tests. If it says "tests pass for X," ensure tasks produce those tests.

## Plan Document Header

**Every plan phase document MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Scope:** [N] phases from original design (phases [X-Y] if partial implementation)

**Codebase verified:** [Date/time of verification]

**Phase Type:** infrastructure | functionality | preparatory-refactor

---

## Acceptance Criteria Coverage

This phase implements and tests:

### {slug}.AC1: [Criterion heading from design plan]
- **{slug}.AC1.1 Success:** [Copied literally from design plan]
- **{slug}.AC1.3 Failure:** [Copied literally from design plan]

### {slug}.AC2: [Criterion heading from design plan]
- **{slug}.AC2.1 Success:** [Copied literally from design plan]

---
```

**AC Coverage rules:**
- Copy AC text literally from the design plan—do not paraphrase
- Use the full scoped AC identifier (e.g., `oauth2-svc-authn-42.AC1.1`), not bare `AC1.1`
- Include ONLY the ACs this phase implements and tests
- Include both the criterion heading (`{slug}.AC1`) and the specific cases (`{slug}.AC1.1`, `{slug}.AC1.3`)
- Tasks in this phase must produce tests that verify these specific cases
- An AC case may appear in multiple phases if partially addressed, but final phase must complete it

Phase Type is required for all new plans. The execution skill uses this field to determine dispatch behaviour. If omitted, the executor defaults to functionality.

**Preparatory-refactor header example:**

```markdown
# [Feature Name] Implementation Plan — Preparatory Refactoring for Phase [N]

**Goal:** Restructure [target files] to enable Phase [N]: [Phase Name]

**Architecture:** [What structural changes are needed and why they enable the upcoming phase]

**Tech Stack:** [Same as the phase it enables]

**Scope:** Preparatory phase inserted before Phase [N] of [total] from original design

**Codebase verified:** [Date/time]

**Phase Type:** preparatory-refactor

**Target Files:**
- `[absolute/path/to/file1.py]`
- `[absolute/path/to/file2.py]`

---

## Acceptance Criteria Coverage

This phase is preparatory refactoring. It restructures existing code to enable the upcoming implementation phase.

**Verifies: None** — success = tests green after restructuring.

**Enables:** Phase [N]: [Phase Name] — [what structural readiness this provides]

---
```

## Task and Subcomponent Markers

**Wrap every task and subcomponent in HTML comment markers** to enable efficient parsing during execution.

### Task Markers

Every task MUST be wrapped:

```markdown
<!-- START_TASK_1 -->
### Task 1: [Task Name]
...task content...
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: [Task Name]
...task content...
<!-- END_TASK_2 -->
```

### Subcomponent Markers

When tasks form a logical subcomponent (e.g., types → implementation → tests), wrap the group:

```markdown
<!-- START_SUBCOMPONENT_A (tasks 3-5) -->
<!-- START_TASK_3 -->
### Task 3: TokenService types
...
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: TokenService implementation
...
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: TokenService tests
...
<!-- END_TASK_5 -->
<!-- END_SUBCOMPONENT_A -->
```

**Key rules:**
- Tasks are numbered: `START_TASK_1`, `START_TASK_2`, etc.
- Subcomponents use letters: `START_SUBCOMPONENT_A`, `START_SUBCOMPONENT_B`, etc.
- Subcomponent markers MUST include which tasks they contain: `(tasks 3-5)`
- Tasks inside subcomponents still have their own markers
- Standalone tasks (not in a subcomponent) just have task markers

**Why markers:**
- Execution can grep for `START_TASK_` to list all tasks without reading full content
- Execution can extract just the relevant section to pass to task-implementor
- Reduces context usage during execution (especially with experimental workflow)

## Phase-by-Phase Implementation

**Step 0: Create granular task tracker with dependencies**

After verifying scope (≤8 phases), use TaskCreate to create granular sub-tasks for EACH phase. This structure survives context compaction.

**CRITICAL: Include absolute paths and set up dependencies.**

Before creating tasks, capture absolute paths:
- `DESIGN_PATH`: Absolute path to design plan (e.g., `/home/user/project/docs/design-plans/2025-01-24-feature.md`)
- `PLAN_DIR`: Absolute path to implementation plan directory (e.g., `/home/user/project/docs/implementation-plans/2025-01-24-feature/`)

**Read the Acceptance Criteria section from the design plan.** Acceptance criteria are numbered (AC1, AC1.1, AC1.2, etc.) and define what "done" means. When writing each phase:
1. Identify which ACs this phase implements (look at design phase's "Done when" + component responsibilities)
2. Copy those AC entries literally into the phase's "Acceptance Criteria Coverage" header section
3. Ensure tasks produce tests that verify each listed AC case

**For each phase N, create these tasks with dependencies:**

```markdown
- [ ] Phase NA: Read [Phase Name] from {DESIGN_PATH}
      → blocked by: Phase (N-1)D (or nothing if N=1)
- [ ] Phase NB: Investigate codebase for Phase N and activate relevant skills
      → blocked by: Phase NA
- [ ] Phase NC: Research external deps (Phase N)
      → blocked by: Phase NB
- [ ] Phase ND: Write {PLAN_DIR}/phase_0N.md
      → blocked by: Phase NC
```

**VERBATIM TASK NAMES — DO NOT PARAPHRASE.** Copy task names exactly as shown above. "Investigate codebase for Phase N and activate relevant skills" must include "and activate relevant skills" — that phrase triggers skill activation after compaction. Paraphrasing loses critical instructions.

**After all phase tasks, create Test Requirements, UAT Requirements, then the Finalization task — in that order.** Finalization runs LAST so its plan-validation review also covers the generated `test-requirements.md` / `uat-requirements.md`, and its existence gate verifies an already-written, stamped `uat-requirements.md` instead of racing the task that produces it:

```markdown
- [ ] Test Requirements: Generate test-requirements.md from Acceptance Criteria
      → blocked by: all Phase *D tasks
- [ ] UAT Requirements: Collate uat-requirements.md from phase decisions
      → blocked by: Test Requirements
```

Then create the Finalization task. Before creating it, check if `.ed3d/implementation-plan-guidance.md` exists. If it does, include its absolute path in the task description:

```markdown
# If .ed3d/implementation-plan-guidance.md exists:
- [ ] Finalization: Run code-reviewer over all phase files (guidance: [absolute path to .ed3d/implementation-plan-guidance.md]), fix ALL issues including minor ones
      → blocked by: UAT Requirements

# If .ed3d/implementation-plan-guidance.md does NOT exist:
- [ ] Finalization: Run code-reviewer over all phase files, fix ALL issues including minor ones
      → blocked by: UAT Requirements
```

**Example for a 3-phase design at `/home/user/project/docs/design-plans/2025-01-24-oauth-99.md`:**

```
TaskCreate: "Phase 1A: Read Token Types from /home/user/project/docs/design-plans/2025-01-24-oauth-99.md"
TaskCreate: "Phase 1B: Investigate codebase for Phase 1 and activate relevant skills"
  → TaskUpdate: addBlockedBy: [1A]
TaskCreate: "Phase 1C: Research external deps (Phase 1)"
  → TaskUpdate: addBlockedBy: [1B]
TaskCreate: "Phase 1D: Write /home/user/project/docs/implementation-plans/2025-01-24-oauth-99/phase_01.md"
  → TaskUpdate: addBlockedBy: [1C]

TaskCreate: "Phase 2A: Read Token Service from /home/user/project/docs/design-plans/2025-01-24-oauth-99.md"
  → TaskUpdate: addBlockedBy: [1D]
TaskCreate: "Phase 2B: Investigate codebase for Phase 2 and activate relevant skills"
  → TaskUpdate: addBlockedBy: [2A]
TaskCreate: "Phase 2C: Research external deps (Phase 2)"
  → TaskUpdate: addBlockedBy: [2B]
TaskCreate: "Phase 2D: Write /home/user/project/docs/implementation-plans/2025-01-24-oauth-99/phase_02.md"
  → TaskUpdate: addBlockedBy: [2C]

TaskCreate: "Phase 3A: Read Session Manager from /home/user/project/docs/design-plans/2025-01-24-oauth-99.md"
  → TaskUpdate: addBlockedBy: [2D]
TaskCreate: "Phase 3B: Investigate codebase for Phase 3 and activate relevant skills"
  → TaskUpdate: addBlockedBy: [3A]
TaskCreate: "Phase 3C: Research external deps (Phase 3)"
  → TaskUpdate: addBlockedBy: [3B]
TaskCreate: "Phase 3D: Write /home/user/project/docs/implementation-plans/2025-01-24-oauth-99/phase_03.md"
  → TaskUpdate: addBlockedBy: [3C]

TaskCreate: "Test Requirements: Generate test-requirements.md from Acceptance Criteria"
  → TaskUpdate: addBlockedBy: [1D, 2D, 3D]

TaskCreate: "UAT Requirements: Collate uat-requirements.md from phase decisions"
  → TaskUpdate: addBlockedBy: [Test Requirements]

TaskCreate: "Finalization: Run code-reviewer over all phase files, fix ALL issues including minor ones"
  → TaskUpdate: addBlockedBy: [UAT Requirements]
```

**Why absolute paths in task descriptions:** After compaction, the task list is all that remains. Absolute paths ensure you know exactly which files to read/write without relying on context.

**Why dependencies:** Tasks show `[blocked by #X, #Y]` in the task list, making execution order explicit and preventing out-of-order work.

Use TaskUpdate to mark each sub-task as in_progress when starting, completed when done.

---

### Per-phase workflow

**Separate WHAT (decisions needing human judgement) from HOW (implementation details for subagents).** You surface genuine decisions with lens analysis for approval. The implementation tasks get written to disk after approval, and the lens analysis is ephemeral and does not appear in the phase file.

There is one route. Do not offer the human a choice of review style, and do not write phases to disk unreviewed to save tokens: the decisions that reach a human are chosen by the filters in step 5, not by a mode selected up front.

**Three lenses applied to each design decision:**

| Lens | Question | When to include |
|------|----------|----------------|
| **Popper (falsification)** | What would prove this decision wrong? | **Always analyse; output depends on decomposition.** Every decision gets a falsifiability analysis (see Popper discipline below). The UAT entry is the subset of decisions where falsification genuinely requires human judgment. Zero UAT entries is a first-class valid outcome for infrastructure / preparatory-refactor phases and for any phase whose decisions all decompose to automatable checks — "no UAT entry" is NOT a failure to find one. |
| **Lakatos (research programmes)** | Is this decision extending the architecture or working around a prior commitment? | **Only when interesting.** Omit for routine choices. Its presence signals "pay attention." |
| **Haraway (situated knowledge)** | Whose perspective shaped this? Who benefits, who bears cost, what's absent? | **Only when interesting.** Include for: vendor/platform lock-in, data residency, accessibility, security model, cost distribution, technology that constrains future options. Omit for routine structural decisions. Its presence signals "someone bears an invisible cost." |

Full citations for the three lenses (Popper 1963, Lakatos 1978, Haraway 1988) are in the References section of the `restate-our-assumptions` skill.

**Popper discipline — falsification tests must earn their format:**

Every design decision gets a falsification test. But the *output* of that test depends on whether a human or a machine should verify it.

**The sorting question:** "Can this prediction be proven wrong by automated test, or does it require human judgment?"

| Answer | What to write | Where it goes |
|--------|--------------|---------------|
| **Automatable** — the prediction reduces to "run X, compare output to Y" | Write it as a test requirement | `test-requirements.md` — the test-analyst validates coverage during execution |
| **Human judgment required** — the prediction requires interacting with the system and forming an opinion (usability, domain correctness, workflow fit) | Write it as a **Popper (your UAT)** entry using the falsification template below | `uat-requirements.md` — the `exec-uat-gate` skill uses it during execution. **These entries MUST be persisted.** |
| **Judgment required, but not in this phase** — the user-facing experience doesn't exist yet | Note which future phase it belongs to | `uat-requirements.md` under the future phase's section, with a back-reference to the decision (DR[N]) made here |

**Quality rubric — Carnap's "Mark I eyeball" test** (after Carnap, R. 1936. "Testability and Meaning." *Philosophy of Science* 3(4): 419–471; "Mark I eyeball" is operator slang for the human-as-instrument, not Carnap's phrase)**:**

The developer is the instrument. A good UAT entry requires ALL THREE:

1. **What the human does** — an action pursuing the design objective, not a verification procedure. The human *uses* the thing for its purpose.
2. **What they're judging** — a subjective quality only a human can evaluate (usability, domain correctness, workflow fit, clarity, discoverability).
3. **What failure looks like** — a concrete experience proving the decision wrong. Not "it doesn't work" but what the human would see, feel, or be unable to do.

**Ruled out by this rubric:**
- "Read X and confirm Y is present" — inspection, not use
- "Run X and see Y" — that's a test, automate it
- "Check that Z works" — unfalsifiable (what does "works" look like?)
- "Verify the output matches the spec" — comparison, not judgment
- "Curl the endpoint and check the response" — integration test the human is running by hand

**Audit evidence:** 76% of Popper entries in real plans were tautological — manual re-runs of what automated tests already verify. The rubric exists to prevent this.

**Falsification template (Popper as risky statement):**

Make the strongest claim the decision implies, then try to shatter it:

```
**This decision assumes:** [the assumption baked into the implementation]
**To shatter it:** [use the built thing for its intended purpose and judge whether the assumption holds]
**It's wrong if:** [the specific experience that shows the assumption failed your intent]
```

The developer uses the system for its purpose and asks: does this match what I meant? The gap between intent and result is the falsification.

**Three anti-smuggling tests — apply to EVERY proposed UAT entry:**

1. **Decomposition test:** Separate the mechanism from the surface. If the mechanism ("Stytch prevents re-auth") can be proven wrong by automated test, the UAT entry must be about the surface alone ("the rejection experience makes sense to a student") — not the mechanism wearing a UX hat. If the surface judgment is trivial once the mechanism is verified, there is no UAT entry.

2. **Reduction test:** If each step in a multi-step scenario could be verified by an automated test in isolation, the scenario is an integration test the human is running by hand. Automate it. "Run the CLI, then switch to the browser, then watch the tabs" looks complex but each step is an assertion.

3. **Disagreement test:** The "It's wrong if" must describe something two reasonable people could disagree about. If every observer would reach the same verdict ("the page shows an error" / "the row is missing"), it's an automated check, not a judgment. This kills "feels" padding — "timing feels unreliable" is either measurable (automate it) or genuinely subjective (keep it, but say what "unreliable" looks like).

   **Disclosed-oracle check (sharpens Decomposition + Disagreement; added after adversarial rounds 1–2, 2026-07-06; refined for mixed-signal entries round 4, 2026-07-07):** Experiential wording in "It's wrong if" is not enough to pass. If **This decision assumes** discloses a scalar, a boundary, OR a relational comparison — a number, count, rate, latency, threshold, status code, resolves/404 line, or a parity-to-baseline comparison ("no larger a share than the model it replaces", "≤ the current rate", "no worse than the incumbent") — whose value would settle the verdict **on its own, leaving no irreducible human judgment**, the entry FAILS however experientially "It's wrong if" is phrased. The boundary need not be a literal number: a disclosed relation to an unnamed baseline still pre-computes the verdict. Test it directly: write an automated check using ONLY the facts stated in **This decision assumes**; if that check's output would determine "It's wrong if", the sensory wording ("feels sluggish", "reads as complete", "a step backward in trust") is laundering a deterministic check → FAIL, route to test-requirements. A genuine entry's assumes-clause names the human construct ("users evaluate responsiveness holistically"), not a constant or a parity-to-baseline comparison that pre-computes the boundary.

   **Mixed-signal exception — split, do not over-reject:** A disclosed boundary that is *necessary but not sufficient* does not fail the entry wholesale. **The operative test is textual and lives in "It's wrong if" — not in the mood of "What's NOT automatable".** Route the disclosed boundary to a test-requirement, then read what remains of "It's wrong if": if a nonempty wrongness condition survives — one a human could trigger *while every routed check passes*, drawn from the entry's own "It's wrong if" rather than newly invented — the entry is mixed-signal: **SPLIT it.** Keep that surviving condition as the UAT entry and remove the settled boundary from **This decision assumes**. If nothing falsifiable survives in "It's wrong if" once the boundary is routed — the only residual is a judgment asserted in **This decision assumes** or **What's NOT automatable**, with no wrongness condition a human could trip — it is decorative: **FAIL the whole entry**, do not split. Two anchors: "latency > 100ms AND users feel it is sluggish" leaves an *empty* "It's wrong if" once latency is routed (the stutter IS the latency) → FAIL; "text falls below 4.5:1 contrast anywhere, or a low-vision user still cannot parse the visual hierarchy where contrast passes" leaves "a low-vision user cannot parse the hierarchy" after the ratio is routed → SPLIT. Every UAT entry has a nonempty "What's NOT automatable" because the template demands one; a vibe asserted there is not a surviving wrongness condition, and an entry whose "It's wrong if" enumerates only automatable conditions FAILs even if it invokes a coherence or gestalt judgment elsewhere.

**Rubric maintenance — this rubric is LLM-judged and wording-sensitive:** adversarial testing (rounds 1–3, 2026-07-06; rounds 4–5 mixed-signal refinement, 2026-07-07) showed the gate's catch rate changes with exact rubric phrasing — repeatedly, including a round-4 laundering hole in which a smuggle whose "It's wrong if" enumerated only automatable conditions was wrongly SPLIT by invoking a coherence gestalt asserted elsewhere. Any edit to these three tests, the disclosed-oracle check, or the mixed-signal exception must be re-validated against the E1–E12 adversarial fixture before shipping; inspection-equivalence ("the new wording obviously covers it") is not sufficient evidence. Fixture roles: E9 (decorative human read bolted onto a fully-settling oracle → FAIL), E7 (automatable-only "It's wrong if" with a gestalt vibe attached elsewhere → FAIL, not SPLIT), and E12 (an in-clause decorative twin whose second "It's wrong if" disjunct is derivable from already-automatable facts → FAIL, not SPLIT) guard the fail side; E10 (already-decomposed, boundary carved into "What's automatable" → PASS) and E11 (genuine mixed-signal — a human-triggerable residual surviving in "It's wrong if" after the boundary is routed → SPLIT) guard that the exception neither over-rejects nor becomes a laundering hole. The fixture, all rounds, and the residual-risk record live in the Phase 6 adversarial-test record of the 2026-04-17 skill-skills-upstream-sync implementation plan. Known ceiling: every fixture smuggle discloses its oracle in-text; the gate has not been tested against a smuggler who scrubs the tell entirely.

**A bad Popper entry restates what automated tests verify:**
- "Run the validator and see it validates" — that's a unit test
- "Call the endpoint and see 200 OK" — that's an integration test
- "Run `uv sync` and see no errors" — that's a build check
- "Check the database for the new row" — that's an assertion
- "Verify the button appears when sharing is enabled" — if a boolean controls visibility, test the boolean
- "Run the ban command and observe the full workflow" — multi-step integration test (fails reduction test)
- "Attempt to log in as a banned user and evaluate the rejection experience" — automatable core with UX wrapper (fails decomposition test: "Stytch prevents re-auth" is a test; "experience makes sense" is only genuine if the automated test can't cover it)

**A good Popper entry describes something only a human can judge:**
- "Use the extraction workflow on chapter 3 and assess whether the entries match your understanding of the source material" — domain judgment (fails no anti-smuggling test: no automated test can verify domain accuracy)
- "Navigate the auth flow as a new user and evaluate whether the steps are discoverable without documentation" — usability judgment (reasonable people would disagree about "discoverable")
- "Read the generated report and assess whether the relationship between X and Y is accurately represented" — interpretation judgment
- "Use the incident timeline tool against the 2026-03-16 data and judge whether the correlated events tell a coherent story" — analytical judgment
- "Read the generated guide as a new instructor and assess whether you could complete the setup without asking for help" — completeness judgment (the mechanism "headings exist" is automatable; the surface "I could follow this without help" is genuinely subjective)

**For phases with no user-facing surface** (most foundational phases): there are typically no Popper UAT entries. Instead, the decision's falsification test is either an automated test requirement or a note that human verification is deferred to the phase where the experience exists. The `exec-coherence-review` skill handles the human touchpoint for these phases — checking whether the foundations support the future UAT, not re-running tests by hand.

**Worked example — sorting a phase's decisions across the three buckets:**

Phase 2 (Token Service, functionality, no UI) has 4 design decisions:

1. "Token validation rejects expired tokens" → **Automatable.** Write integration test: `test_expired_token_returns_401`. Goes to test-requirements.md.
2. "Token refresh uses sliding window expiry" → **Automatable.** Write test: `test_sliding_window_extends_on_activity`. Goes to test-requirements.md.
3. "The auth flow feels discoverable to a new user without documentation" → **Human judgment, but not in this phase.** The UI doesn't exist until Phase 4. Persisted to `uat-requirements.md` under Phase 4, back-reference DR2 from Phase 2.
4. "Concurrent refresh requests don't create duplicate tokens" → **Automatable.** Write test: `test_concurrent_refresh_deduplicates`. Goes to test-requirements.md.

Result: Phase 2 has zero Popper UAT entries. The execution routing rubric sends it to exec-coherence-review, not the UAT gate. The one human-judgment item lands in Phase 4's UAT where it belongs.

**Lakatos discipline:**
- The hard core = design plan's architectural commitments (inherited, not questioned here)
- The protective belt = implementation decisions being made NOW (under review)
- **DEGENERATING** = decision requires workarounds, modifies code outside this phase's scope, conflicts with later phases, duplicates existing capability because the existing one doesn't quite fit
- **PROGRESSIVE** = decision makes a downstream phase simpler (cite which), removes special cases from existing code, extends an existing pattern rather than creating a parallel one — **must cite specific evidence**
- If you cannot cite evidence of progression or degeneration, **omit Lakatos entirely.** Do not invent a "stable" or "neutral" classification. The absence of the lens IS the signal that the decision is routine.
- If the agent rates most decisions PROGRESSIVE without specific evidence, the analysis is performative. Most decisions are routine protective belt adjustments.

**Workflow for EACH phase (using granular task tracking):**

1. **Task NA: Read design phase**
   - Mark task NA as in_progress
   - Extract the `<!-- START_PHASE_N -->` section from design plan
   - Mark task NA as completed

2. **Task NB: Verify codebase state**
   - Mark task NB as in_progress
   - Dispatch codebase-investigator with design assumptions for this phase
   - Review investigator findings for discrepancies
   - **Activate relevant skills** based on findings (if not already active):
     - Python code? Activate coding-python-idioms/coding-effectively skills
     - Database work? Activate howto-develop-with-postgres skill
     - Match skills to the technologies this phase involves
   - **Structural readiness check (for phases modifying existing files):**
     If this phase modifies existing files (not just creating new ones), add to the investigator query:
     "The upcoming phase will modify these existing files: [list]. Assess their structural readiness:
     - Are there mixed concerns that should be separated before the phase changes arrive?
     - Are there hardcoded assumptions that need generalising?
     - Are there missing seams (no clear extension points for the new functionality)?
     - Would the phase's changes be significantly easier if any structural prep work was done first?"
     **If the investigator reports impediments:** Surface them to the planner. The planner should consider inserting a "preparatory-refactor" phase before this phase. Use AskUserQuestion:
     Question: "Codebase investigation found structural impediments in files Phase [N] will modify: [summary]. Insert a preparatory-refactor phase before Phase [N]?"
     Options: "Yes — insert preparatory-refactor phase" | "No — proceed without (implementation may be harder)"
     **If the user approves:** Insert a preparatory-refactor phase with goal referencing the upcoming phase, Phase Type: preparatory-refactor, and tasks empty (the refactoring pipeline determines what to do at execution time based on smell assessment). Number as Phase [N-1.5] or renumber subsequent phases.
     **If the phase only creates new files:** Skip the structural readiness check entirely.
   - Mark task NB as completed

3. **Task NC: Research external dependencies** (if phase involves them)
   - Mark task NC as in_progress
   - Dispatch internet-researcher for docs/standards/API patterns
   - Escalate to remote-code-researcher if docs are insufficient
   - Document findings for inclusion in phase output
   - Mark task NC as completed
   - (Skip if no external deps - still mark completed with note "N/A")

4. **Write implementation tasks** for this phase (in memory, not to file):
   - Identify which ACs this phase covers based on design phase's scope
   - Include the "Acceptance Criteria Coverage" section with literal AC copies
   - Write tasks that implement and test each listed AC case

5. **Find the genuine decisions — and only those.** Most phases surface none. Zero is the normal, good outcome; a phase that lists four "decisions" is almost always manufacturing them.

   A genuine decision is a fork the design leaves open that you cannot settle on plain technical grounds. If the design plan, an acceptance criterion, or an obvious best practice already settles the choice, it is an implementation detail: write it to the plan and move on. It is not something to present.

   Apply all three filters before presenting any candidate. Each one, on its own, disqualifies it:
   - **Restatement.** If it restates what the design or an AC already says in other words, it is not a decision.
   - **Invented alternative.** If you had to invent an alternative so you would have something to "consider", the alternative is not real and neither is the decision.
   - **Obvious default.** If two competent engineers would pick the same option without discussion, that is a default. Write the default; do not present it.

   A real decision survives all three: the design is silent, the alternatives are real, and a competent engineer could reasonably go either way. These live in structural choices later phases depend on, library selections with real trade-offs, and error-handling strategies the design left open. The lens analysis is for these survivors — it is not a form to fill in for every task.

6. **Present to user** - Output the design decisions with lens analysis:

```markdown
**Phase [N]: [Phase Name]**

**Codebase verification findings:**
- ✓ Design assumption confirmed: [what matched]
- ✗ Design assumption incorrect: [what design said] - ACTUALLY: [reality]
- + Found additional: [unexpected things discovered]
- ✓ Dependency confirmed: [library@version]

**External dependency findings:** (if applicable)
- ✓ [Library] API: [what docs/source revealed]
- ✗ Design assumption incorrect: [what design said] - ACTUALLY: [reality per docs/source]
- 📖 Source: [Official docs | RFC spec | Source code @ commit]

**Design decisions in this phase:**

*Most phases surface none. If step 5's filters leave nothing, write "No open decisions — the design settles this phase" and list what the phase delivers. Do not manufacture decisions to fill the section.*

*Each decision is plain language. The three lens lines below carry the substance — they are kept, not performed: the Popper line always routes a falsification to a test or a UAT check; the Lakatos and Haraway lines appear only when they genuinely fire.*

### DR1: [the decision, one plain sentence a non-specialist follows]

**What it implies:** [what each direction commits you to downstream — which later phases, data, or interfaces depend on this choice. This is the part the human is actually judging.]

**What's automatable:** [name the mechanism that CAN be verified by a named command or operational check. If nothing is automatable here, this UAT entry is probably a disguised test-requirement — flag and re-route.]
**What's NOT automatable:** [name the surface judgment that requires a human who has used the built thing. If nothing is NOT automatable, the entry is smuggled — reject.]

**This decision assumes:** [the assumption baked into the implementation]
**To shatter it:** [use the built thing for its intended purpose and judge whether the assumption holds]
**It's wrong if:** [the specific experience that shows the assumption failed your intent]

**How we'd know it's wrong (Popper):** [the falsification, routed to where it gets checked:
- A test can catch it → name it, `test_[name]`, added to test-requirements.md.
- Only a human can judge it, and the experience exists now → write **This decision assumes / To shatter it / It's wrong if**, persisted to uat-requirements.md.
- Only a human can judge it, but the experience doesn't exist yet → note the future phase and persist to uat-requirements.md under it, back-referencing DR[N].]

**Works around / leaks into (Lakatos):** [only if the decision genuinely degenerates — cite the specific workaround, scope-leak, or conflict with a later phase. Omit otherwise.]

**Who bears the cost (Haraway):** [only if someone genuinely does — vendor lock-in, accessibility, data residency, security model. Omit otherwise.]

**Recommendation:** [...]

**Popper:** -> **test-requirement** — write [test type] test: `test_[name]` that [specific automated verification]. Added to test-requirements.md.
**Lakatos: DEGENERATING** — [only if applicable, with specific evidence]

### DR3: [Foundational choice — no user experience in this phase]

**Options considered:**
- [...]

**Recommendation:** [...]

**What's automatable:** [name the mechanism that CAN be verified by a named command or operational check. If nothing is automatable here, this UAT entry is probably a disguised test-requirement — flag and re-route.]
**What's NOT automatable:** [name the surface judgment that requires a human who has used the built thing. If nothing is NOT automatable, the entry is smuggled — reject.]

**This decision assumes:** [assumption]
**To shatter it:** Deferred to Phase [M] — the user-facing experience doesn't exist yet.
**It's wrong if:** [what you'd see in Phase M that proves this foundation was wrong]
*(Persisted to uat-requirements.md under Phase [M], back-reference DR3 from Phase [N])*

### DR4: [Routine choice — no alternatives worth reviewing]
**Popper:** -> **test-requirement** — `test_[name]`. Added to test-requirements.md.

[Continue for all non-trivial decisions in this phase...]
```

6.5. **Pre-presentation self-audit — apply the three anti-smuggling tests before AskUserQuestion**

This is a pre-presentation self-audit, NOT the structural anti-smuggling gate. The structural gate is the collation audit in the UAT Requirements Collation section, which dispatches a dedicated subagent to run every entry through the three tests independently of the planner. Step 6.5 is planner-side hygiene that surfaces obvious smuggling BEFORE the user approval in step 7 — making the conversation better. The user CAN still approve a smuggled entry; the collation audit is the structural gate that rejects disclosed-oracle smuggles before they reach `uat-requirements.md` — a calibrated, evidence-bounded property, not a guarantee that "structurally prevents" all smuggling (the catch rate is LLM-judged and wording-sensitive; see the calibrated claim and residual risk in the rubric-maintenance note under the Disagreement test).

Before presenting the DR set to the user for approval (step 7), run each proposed UAT entry (entries with `**What's automatable:**` and `**What's NOT automatable:**` lines) through the three anti-smuggling tests:

1. **Decomposition test** — Is the What's-automatable genuinely separate from the What's-NOT-automatable, or does the What's-automatable already cover what the falsification claims to test?
2. **Reduction test** — Would each step in the "To shatter it" scenario be automatable in isolation? If yes, the entry is a multi-step integration test a human is running by hand — automate it.
3. **Disagreement test** — Would two reasonable people, after using the thing, plausibly disagree about whether "It's wrong if" was met? If every observer would reach the same verdict, the entry is an automated check, not a UAT.
   - **Disclosed-oracle sub-check:** if "This decision assumes" discloses a scalar/threshold/count/rate/status-code/resolves-404 boundary OR a parity-to-baseline comparison ("no worse than the incumbent", "≤ the current rate") whose value would settle "It's wrong if" **on its own**, FAIL however experientially "It's wrong if" is phrased — the boundary need not be a literal number; an automated check built from only the assumes-clause facts deciding the verdict means the sensory wording is laundering a deterministic check. **Mixed-signal exception:** route the boundary to a test-requirement, then read what remains of "It's wrong if". If a nonempty wrongness condition survives — one a human could trigger while every routed check passes, drawn from the entry's own "It's wrong if" — **SPLIT** and keep that condition as the UAT entry. If nothing falsifiable survives in "It's wrong if" once the boundary is routed (only a vibe in **This decision assumes** / **What's NOT automatable**) it is decorative → FAIL, not SPLIT. Every entry has a nonempty **What's NOT automatable**; a judgment asserted only there is not a surviving wrongness condition, and an "It's wrong if" that enumerates only automatable conditions FAILs even if a coherence or gestalt judgment is invoked elsewhere.

**Self-audit behaviour:**
- If an entry passes all three tests → retain and present to user.
- If an entry fails the Decomposition test → re-route to test-requirements.md (mechanism was automatable; no surface judgment exists).
- If an entry fails the Reduction test → decompose into automatable test-requirements (the scenario is an integration test).
- If an entry fails the Disagreement test → either rewrite the "It's wrong if" clause to describe something genuinely subjective, or re-route to test-requirements.md.
- If an entry is mixed-signal — after routing the disclosed boundary to test-requirements.md, a nonempty wrongness condition still survives in **It's wrong if** that a human could trigger while the routed check passes → **SPLIT**: keep that surviving condition as the UAT entry, remove the settled boundary from **This decision assumes**. If routing the boundary leaves an empty **It's wrong if** (the only residual is a judgment in **This decision assumes** / **What's NOT automatable**), it is decorative → FAIL, not SPLIT. Do not reject a genuine remainder wholesale; do not retain a decorative one.
- If all entries fail → **zero UAT entries is the correct output for this phase** (this is the first-class output from AC6.7).

**Why this is a self-audit, not a structural gate (M6 revision):** The user in step 7 CAN approve a smuggled entry if presented with one — the planner-side self-audit does not structurally prevent reaching the user. The structural gate is the collation audit in the UAT Requirements Collation section, which runs an independent subagent over every entry in the final `uat-requirements.md` before writing. Step 6.5 improves the conversation; the collation audit is the backstop. Present self-audited entries to the user honestly (including any that were self-flagged and re-routed), so step 7's approval is informed.

**Self-audit log:** Record pass/fail for each proposed entry in a brief comment (in-memory; does not need to be persisted). If re-routing to test-requirements, note the target test name.

7. **Use AskUserQuestion:**

**The question MUST summarise what's being approved.** State what the phase delivers, how many genuine decisions it surfaced (often zero), and any degeneration or cost flag raised.

Example (no open decisions): "Phase 2: creates auth middleware and token service, covers AC2.1-AC2.3. No open decisions — the design settles this phase."
Example (one decision): "Phase 3: comment store and import (AC1.6-AC1.7). One open decision — where comment ratings live (JSONB column vs separate table)."

**Options:**
- "Approved - proceed to write phase and continue"
- "Needs revision - [describe changes]"
- "Other"

8. **Task ND: Write phase file and persist UAT entries (if approved)**
   - Mark task ND as in_progress
   - Write phase to `docs/implementation-plans/YYYY-MM-DD-<feature-name>/phase_##.md`
   - Phase file contains ONLY the implementation tasks (no lens analysis, no verification findings)
   - **Persist Popper UAT entries:** Append all human-judgment falsification entries from this phase's decisions to `uat-requirements.md` as an unstamped working accumulation (the UAT Requirements Collation step below audits every entry and re-writes the file with its provenance stamp — do not stamp it here). Automatable entries go to test-requirements.md as before.
   - Mark task ND as completed, continue to next phase

9. **If needs revision:** Revise implementation tasks based on decision feedback, re-identify decisions, present again (do NOT mark ND as in_progress until approved)

---

### Worked Examples — smuggled entry, genuine entry, zero-UAT phase

**Example 1: Smuggled entry (REJECT)**

Proposed:
> **DR3: Token validation rejects expired tokens**
> **What's automatable:** (left blank or filled with something like "the rejection logic works")
> **What's NOT automatable:** (left blank or filled with "the user experience of seeing the rejection")
> **This decision assumes:** ...
> **To shatter it:** Run the test suite and verify expired tokens return 401.
> **It's wrong if:** Expired tokens don't return 401.

**Why this is smuggled:** "To shatter it: Run the test suite" is a test-requirement. The three anti-smuggling tests would flag:
- Decomposition test FAILS: the mechanism ("tokens return 401 on expiry") IS automatable and there is no distinct surface judgment.
- Disagreement test FAILS: "401 vs 200" is not something two reasonable people can disagree about.

**Re-routing:** Add to test-requirements.md as `test_expired_token_returns_401`. Do NOT create a UAT entry.

**Example 2: Genuine UAT entry (ACCEPT)**

Proposed:
> **DR5: Error messages guide users to the fix**
> **What's automatable:** The error message format (e.g., "includes a link to documentation") can be grep-checked. The text itself is present or absent.
> **What's NOT automatable:** Whether the message's wording actually helps a new user form the next action. "Helpful" is a subjective quality of the language, not a mechanical property.
> **This decision assumes:** Users will understand the next step after reading the error.
> **To shatter it:** Use the feature with a deliberately-wrong input as a first-time user and assess whether the error's wording guides you to the fix.
> **It's wrong if:** You read the error and reach for documentation to understand what to do next, meaning the error names the fault without scaffolding the next action.

**Why this is genuine:** The Decomposition test separates mechanism (format) from surface (helpfulness). The Disagreement test is satisfied — reasonable people could disagree whether an error message is "guiding" vs "naming." The Reduction test passes — it's a single integrated human experience, not a multi-step integration test.

**Example 3: Zero-UAT output (infrastructure phase)**

A preparatory-refactor phase whose Done-when is "tests stay green after restructuring" has:
- All verification automatable (tests pass or don't)
- No surface-judgment experience (the restructure is inspectable via diff)
- Every proposed UAT decomposes to test-requirement or test-of-behaviour-preservation

**Correct output:** Zero UAT entries in this phase's section of `uat-requirements.md`. The phase writes `## Phase N: [Name]` and a one-line "No native UAT entries; all verification routes to test-requirement" marker. This is a first-class valid outcome — NOT a failure to find UAT entries.

## Task Structure

**Use the appropriate template based on task type (see Task Types section above).**

### Infrastructure Task Template

````markdown
<!-- START_TASK_N -->
### Task N: [Infrastructure Component]

**Files:**
- Create: `pyproject.toml`
- Create: `<src>/__init__.py`

**Step 1: Create the files**

[Complete file contents - no placeholders]

**Step 2: Verify operationally**

Run: `uv sync`
Expected: Dependencies install without errors

Run: `uv run ruff check .`
Expected: No lint errors

**Step 3: Commit**

```bash
git add pyproject.toml src/__init__.py
git commit -m "chore: initialize project structure"
```
<!-- END_TASK_N -->
````

### Functionality Task Template

```markdown
<!-- START_TASK_N -->
### Task N: [Component Name]

**Verifies:** {slug}.AC1.1, {slug}.AC1.3 (list specific AC cases this task tests)

**Files:**
- Create: `<src>/services/feature.py`
- Modify: `<src>/services/existing.py:123-145`
- Test: `<tests>/services/test_feature.py` (unit|integration|e2e)

**Implementation:**
[Describe what to implement - contracts, behavior, key logic. Include code for complex/non-obvious implementations.]

**Testing:**
Tests must verify each AC listed above:
- {slug}.AC1.1: [brief description of what test should verify]
- {slug}.AC1.3: [brief description of what test should verify]

Follow project testing patterns. Task-implementor generates actual test code at execution time.

**Verification:**
Run: `[test command]`
Expected: All tests pass

**Commit:** `feat: [description]`
<!-- END_TASK_N -->
```

**Key principles for functionality tasks:**

1. **List ACs explicitly.** Every functionality task specifies which AC cases it verifies in the "Verifies" field.

2. **Describe tests, don't write test code.** The AC text is the spec (e.g., "AC1.3: Invalid password returns 401"). Task-implementor generates test code at execution time with fresh codebase context.

3. **Include implementation code when non-obvious.** If implementation is complex or project-specific patterns apply, include the code. If it's straightforward given the AC description, describe it.

4. **Specify test type and location.** Unit, integration, or e2e? Which file? This ensures consistency across phases.

**Why no test code in plans:**
- Test code needs actual function signatures from the implementation
- Project testing patterns discovered at execution time
- AC text like "Invalid password returns 401" is already a clear test spec
- Task-implementor has fresher context than implementation planner

**If you find yourself writing "this won't compile until Phase N+1":**
STOP. You are describing something that belongs in the current phase. _Every phase must be executable with all tests passing when the phase completes._

## Common Rationalizations - STOP

These are violations of the skill requirements:

| Excuse | Reality |
|--------|---------|
| "File probably exists, I'll say 'update if exists'" | Use codebase-investigator. Write definitive instruction. |
| "Design mentioned this file, must be there" | Codebase changes. Use investigator to verify current state. |
| "I can quickly verify files myself" | Use codebase-investigator. Saves context and prevents hallucination. |
| "Design plan has code, I'll use that" | No. Design provides direction. Generate code fresh from codebase investigation. |
| "Design plan is recent, code should still work" | Codebase may have changed. Investigation is the source of truth, not the design. |
| "User can figure out if file exists during execution" | Your job is exact instructions. No ambiguity. |
| "Testing Phase 3 will fail but that's OK because it'll be fixed in Phase 4" | All phases must compile and pass tests before they conclude. |
| "Phase validation slows me down" | Going off track wastes far more time. Validate each phase. |
| "I'll batch all phases then validate at end" | No. Validate incrementally. There is no mode that defers it. |
| "I'll just ask for approval, user can see the plan" | Output complete plan in message BEFORE AskUserQuestion. User must see it. |
| "Plan looks complete enough to ask" | Show ALL tasks with ALL steps and code. Then ask. |
| "This plan has 12 phases but they're small" | Limit is 8 phases. No exceptions. Refuse and redirect. |
| "I can combine phases to fit in 8" | That's the user's decision, not yours. Refuse and explain options. |
| "Comment explains what needs to be done next" | Code comments aren't instructions. Code must run as-written. Create prior task for dependencies. |
| "Engineer will figure out the bootstrap approach" | No implementation questions in code. Resolve it now or create prerequisite task. |
| "Infrastructure tasks need TDD structure too" | No. Use infrastructure template. Verify operationally per design plan. |
| "I'll add tests to this config file task" | If design says "Done when: builds," don't invent tests. Honor the design. |
| "Functionality phase but design forgot tests" | Surface to user. Functionality needs tests. Design gap, not your call to skip. |
| "Plan looks complete, skip validation" | Always validate. Gaps found now are cheaper than gaps found during execution. |
| "Validation is overkill for simple plans" | Simple plans validate quickly. Complex plans need it more. Always validate. |
| "Finalization task is done, minor issues can wait" | NO. Fix ALL issues — including Minor ones — in the first cycle. Finalization completes only when the bounded review reaches a terminal outcome (zero issues or a user-chosen resolution path), never by silently skipping the bug-fixer's first pass. |
| "I'll skip creating granular tasks, one per phase is enough" | Granular tasks survive compaction. Create NA, NB, NC, ND per phase + Finalization. |
| "Dependencies are obvious, don't need addBlockedBy" | Task list shows blocked status. Set dependencies explicitly with TaskUpdate. |
| "Relative paths are fine in task descriptions" | After compaction, context is lost. Use absolute paths so tasks are self-contained. |
| "The consumer is obvious" / "It'll be used in a later phase" | Name the call site now. If you can't, the function doesn't belong in this task. "Used later" is how orphaned code gets planned. |
| "I'll paraphrase the task name, same meaning" | NO. Task names are VERBATIM. "and activate relevant skills" triggers behavior post-compaction. |
| "I know how this library works from training" | Research it. APIs change. Use internet-researcher for docs, remote-code-researcher for internals. |
| "Docs are probably accurate enough" | Usually yes. But if extending/customizing library behavior, verify with source code. |
| "I'll clone the repo to check the docs" | No. Use internet-researcher for docs. Only clone (remote-code-researcher) for source code investigation. |
| "Phase has external deps but I'll skip research" | Research is mandatory when phase involves external dependencies. Surface unknowns now. |
| "Test requirements can be generated during execution" | No. Test requirements must exist before execution starts. Code reviewer uses them. |
| "This type needs unit tests" | No. The type checker (`ty`/`mypy`) verifies types. Don't test what the checker catches. |
| "Should test that this calls the dependency correctly" | No. Test behavior (the result), not wiring (how you called things). |
| "Dependency is used here, should verify it works" | No. Dependencies have their own tests. Test YOUR code's behavior. |
| "More tests = better coverage" | Wrong tests = noise. Test the ACs, nothing more. |
| "Phase doesn't have ACs but I'll add some tests anyway" | No. Explicitly state "Verifies: None" for infrastructure phases. Don't invent work. |
| "Acceptance Criteria are clear, don't need test requirements" | Test requirements map criteria to specific tests. Execution needs this mapping. |
| "I'll skip test requirements, the user seemed in a hurry" | No. Test requirements are always generated and written. |
| "Test requirements task is optional" | No. It's a tracked task with dependencies. Must complete before execution handoff. |
| "All decisions in this phase are PROGRESSIVE" | Unlikely. Most decisions are routine. PROGRESSIVE requires citing a specific downstream phase that gets simpler. Omit Lakatos for routine choices. |
| "Lakatos doesn't apply to any decisions here" | Possible for simple phases. But if you're adding workarounds, shims, or code that a later phase will undo — that's degeneration. Flag it. |
| "I'll show the implementation tasks to the human too" | No. Show decisions and lens analysis only. Implementation tasks go to disk for subagents, not to the human. |
| "The human would probably rather just review the phases himself" | That is the mode selection this skill deliberately removed. Surface decisions, not a choice of review style. |
| "This decision has no perspective worth naming" | Most routine decisions don't. But vendor lock-in, data residency, accessibility, security, and cost distribution always have invisible costs. Include Haraway when someone bears a cost the decision-maker doesn't see. |

**All of these mean: STOP. Follow the requirements exactly.**

## When You Don't Know How to Proceed

**If you cannot write executable code without unresolved questions:** STOP immediately.

Do NOT write hand-waving comments. Do NOT leave TODOs. Do NOT proceed.

**Instead, use AskUserQuestion with:**

1. **Exact description of the blocking issue:**
   - What specific implementation decision you cannot make
   - What information is missing from the design
   - What dependencies are undefined

2. **Context about why this blocks you:**
   - Which task/phase this affects
   - What you've already verified via codebase-investigator
   - What the design document says (or doesn't say)

3. **Possible solutions you can see:**
   - Option A: [specific approach with tradeoffs]
   - Option B: [alternative approach with tradeoffs]
   - Option C: [if applicable]

**Example:**
```
I'm blocked on Phase 2, Task 3 (Bootstrap Logto M2M application).

Issue: The code needs Management API credentials to create resources, but those credentials don't exist yet (chicken-egg problem).

Design document says: "Bootstrap Logto with applications and roles" but doesn't specify how to get initial credentials.

Codebase verification: No existing bootstrap credentials or manual setup documented.

Possible solutions:
A. Add Phase 0: Manual setup - document steps for user to manually create initial M2M app via Logto UI, save credentials to .env
B. Use Logto admin API if available - requires admin credentials in different format
C. Modify Logto docker-compose to inject initial M2M app via environment variables

Which approach should I take?
```

**Never proceed with uncertain implementation. Surface the decision to the user.**

## Requirements Checklist

**Before starting:**
- [ ] Count phases - refuse if >8
- [ ] Capture absolute paths: DESIGN_PATH and PLAN_DIR
- [ ] Read Acceptance Criteria section from design plan
- [ ] Create granular task list with TaskCreate (NA, NB, NC, ND per phase + Test Requirements + UAT Requirements + Finalization)
- [ ] Set up dependencies with TaskUpdate addBlockedBy (see Step 0)
- [ ] Task descriptions include absolute paths (not relative)

**For each phase (tasks NA through ND):**
- [ ] **Task NA:** Mark in_progress, read `<!-- START_PHASE_N -->` from design, mark completed
- [ ] **Task NB:** Mark in_progress, dispatch codebase-investigator, review findings, mark completed
- [ ] **Task NC:** Mark in_progress, research external deps if needed (or mark completed with "N/A"), mark completed
- [ ] Write complete tasks with exact paths and code based on investigator and research findings
- [ ] Find the genuine decisions using step 5's three filters. Zero is the normal outcome
- [ ] Apply lenses to any survivors (Popper always, Lakatos only when interesting, Haraway only when someone bears invisible cost), present for approval
- [ ] **Task ND:** Mark in_progress, write to absolute path in task description, mark completed

**For each task in the plan:**
- [ ] Exact file paths with line numbers for modifications
- [ ] Complete code - zero TODOs, zero unresolved questions in comments
- [ ] Every code example runs immediately without implementation decisions
- [ ] If code references helpers/utilities, prior task creates them
- [ ] Exact commands with expected output
- [ ] No conditional instructions ("if exists", "if needed")

**Test Requirements + UAT Requirements (after all phase ND tasks completed):**
- [ ] Mark Test Requirements task as in_progress
- [ ] Dispatch Opus subagent to generate test requirements from Acceptance Criteria
- [ ] Present to user, use AskUserQuestion for approval
- [ ] Write test-requirements.md to PLAN_DIR
- [ ] Mark Test Requirements task as completed
- [ ] Collate uat-requirements.md from the entries phases accumulated, plus any acceptance criterion needing human judgement that no phase decision covered
- [ ] Dispatch the collation audit subagent — it scores every entry independently of the planner
- [ ] Resolve any FAIL or SPLIT with the human before writing
- [ ] Write uat-requirements.md to PLAN_DIR (first line = collation-audit stamp)
- [ ] Mark UAT Requirements task as completed
- [ ] Proceed to Finalization

**Finalization (after Test Requirements + UAT Requirements completed):**
- [ ] Mark Finalization task as in_progress
- [ ] Dispatch code-reviewer to validate plan against design (SCOPE: `plan-validation`)
- [ ] Fix ALL issues including Minor ones from the initial review
- [ ] Re-run code-reviewer once to verify fixes (one cycle only — same SCOPE, PRIOR_FINDINGS_FILE pointing at `code-review-findings-plan-validation.md`)
- [ ] If re-review finds anything unresolved or new, **HALT and present to the user** (options: fix now / accept remaining / halt for discussion). Do NOT auto-loop.
- [ ] Existence gate: `uat-requirements.md` present AND first-line-stamped (else halt, dispatch collation now)
- [ ] Mark Finalization task as completed when zero issues or user-chosen resolution path is taken
- [ ] Proceed to execution handoff

## Plan Validation (Finalization Task)

**This is a tracked task: "Finalization: Run code-reviewer over all phase files, fix ALL issues including minor ones"**

Finalization runs LAST — after Test Requirements Generation and UAT Requirements Collation (both below) have written `test-requirements.md` and the stamped `uat-requirements.md`. Its plan-validation review therefore also covers those artefacts, and the existence gate below verifies the already-written stamp. When the UAT Requirements task is complete, mark the Finalization task as in_progress.

### Step 1: Dispatch code-reviewer

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:code-reviewer</parameter>
<parameter name="description">Validating implementation plan against design</parameter>
<parameter name="prompt">
  Review the implementation plan for completeness and alignment with the design.

  DESIGN_PLAN: [path to design plan, e.g., docs/design-plans/YYYY-MM-DD-feature.md]

  IMPLEMENTATION_GUIDANCE: [absolute path to .ed3d/implementation-plan-guidance.md, or "None" if file does not exist]

  IMPLEMENTATION_PHASES:
  - [path to phase_01.md]
  - [path to phase_02.md]
  - [... all phase files]

  If IMPLEMENTATION_GUIDANCE is not "None", read it first and apply any project-specific
  review criteria, coding standards, or quality gates it specifies in addition to the
  standard review checklist.

  Evaluate:
  1. **Coverage**: Does the implementation plan cover ALL requirements from the design?
     - Check each design phase maps to implementation tasks
     - Check each "Done when" criteria has corresponding verification
     - Check each component mentioned in design has implementation tasks

  2. **Gaps**: Are there any missing pieces?
     - Functionality mentioned in design but not in implementation
     - Tests specified in design but missing from implementation tasks
     - Dependencies or setup steps not accounted for

  3. **Alignment**: Does the implementation approach match the design?
     - Architecture decisions followed
     - File paths consistent with design
     - Subcomponent structure matches design phases

  4. **Executability**: Can each phase be executed independently?
     - Dependencies between tasks are explicit
     - No forward references to code that doesn't exist yet
     - Each phase ends with verifiable state

  Report:
  - GAPS: [list any missing coverage]
  - MISALIGNMENTS: [list any divergence from design]
  - ISSUES: [Critical/Important/Minor issues in the plan itself]
  - ASSESSMENT: APPROVED / NEEDS_REVISION

  SCOPE: plan-validation

  Per the agent's standard protocol, write your full findings to
  `code-review-findings-plan-validation.md` in the plan directory. Re-review
  cycles will read this file rather than re-deriving issues.
</parameter>
</invoke>
```

### Step 2: Fix ALL issues (including minor ones) — first cycle

**CRITICAL: In the first fix cycle, you MUST fix ALL issues including Minor ones.** The HALT introduced after re-review is not licence to silently skip Minor issues from the initial review — those still get fixed in the bug-fixer pass.

Do NOT rationalize skipping minor issues during the first fix cycle. Mark Finalization complete only when the review reaches a terminal outcome: zero issues after the one re-review, or a user-chosen resolution path (fix-now / accept / halt-for-discussion).

**If reviewer returns NEEDS_REVISION or reports ANY issues:**

1. **Create a task for EACH issue** (survives compaction):
   ```
   TaskCreate: "Finalization fix [Critical]: <VERBATIM issue description from reviewer>"
   TaskCreate: "Finalization fix [Important]: <VERBATIM issue description from reviewer>"
   TaskCreate: "Finalization fix [Minor]: <VERBATIM issue description from reviewer>"
   ...one task per issue...
   TaskCreate: "Finalization: Re-review after fixes"
   TaskUpdate: set "Re-review" blocked by all fix tasks
   ```

   **Copy issue descriptions VERBATIM**, even if long. After compaction, the task description is all that remains — it must contain the full issue details to understand what to fix.

2. Review the gaps, misalignments, and issues identified
3. Fix ALL of them - Critical, Important, AND Minor
4. Update the relevant phase files
5. Mark each fix task complete as you address it
6. Re-run code-reviewer validation **once** — pass `SCOPE: plan-validation` and `PRIOR_FINDINGS_FILE: <path to code-review-findings-plan-validation.md>` so it verifies against the recorded findings rather than starting fresh
7. **HALT after the re-review.** If anything is unresolved or new, present the updated findings file to the user and ask which option they want: (a) another fix cycle (user-authorised), (b) accept the remaining issues as out-of-scope, or (c) halt for discussion. Do NOT auto-dispatch a third reviewer pass.
8. Mark "Re-review" complete when the user-chosen resolution path concludes (zero issues, accepted, or explicit halt)

**Common rationalizations to REJECT:**
- "Minor issues can be fixed during execution" - NO. Fix them now.
- "This minor issue is just a style preference" - NO. Fix it.
- "We can address this later" - NO. The task says "fix ALL issues including minor ones."

### Step 3: Complete finalization

**When the bounded review reaches a terminal outcome:**

- Zero issues on initial review, OR
- Zero issues on the one re-review, OR
- User-chosen resolution path resolved (fix-now cycle completed, issues accepted, or halt-for-discussion concluded with explicit direction).

**Existence gate (must pass BEFORE marking complete):**

Finalization cannot complete until `uat-requirements.md` exists at `[PLAN_DIR]/uat-requirements.md` **and carries the collation-audit provenance stamp** (the marker the UAT Requirements Collation audit writes as the file's first line — see that section). If the file is missing, or present but unstamped:
- Halt Finalization
- Dispatch the UAT Requirements Collation section now — do not proceed without it
- If the collation produces zero entries (all decisions routed to test-requirements per AC6.7), still write the file in its minimal form (stamp included):
  ```
  <!-- collation-audit: PASS | 0 entries (all routed to test-requirements) | [YYYY-MM-DD] -->
  # UAT Requirements — [Plan Name]

  No human-judgment UAT entries. All verification routes to automated tests or operational checks. Phases route to `exec-coherence-review`, not the UAT gate.
  ```

The file must exist **and be stamped** regardless. Silent-skip is the failure mode this gate closes — sessions that compact or interrupt during planning can drop the collation step entirely, leaving no record that UAT was considered. What the stamp gives is **attestation that the collation step ran**, not proof it scored every current entry: it is planner-written and its template appears in this skill, and nothing compares the stamp's count/date to the file's actual entries. So it closes the observed failure (the whole collation section dropped → no stamp) and legacy or hand-written files (unstamped); it does **not** close "a stamp older than entries appended beneath it." An unstamped file fails the gate; a stamped one is trusted as-is. Explicit minimal-file output distinguishes "considered and found empty" from "never ran."

Run:
```bash
test -f "$PLAN_DIR/uat-requirements.md" || { echo "FAIL: uat-requirements.md missing"; exit 1; }
head -1 "$PLAN_DIR/uat-requirements.md" | grep -q '^<!-- collation-audit:' || { echo "FAIL: uat-requirements.md present but unstamped — the collation step did not run"; exit 1; }
```
The grep is anchored to the **first line** so a UAT entry that merely mentions the collation audit in its body cannot self-stamp the file. Exit 0 (present AND first-line-stamped) → gate passes. Exit 1 → halt, dispatch the UAT Requirements Collation audit (which re-scores every entry and writes a fresh stamp).

**Only after the existence gate passes:** Mark the Finalization task as completed, then proceed to execution handoff.

## Test Requirements Generation

**Tracked task: "Test Requirements: Generate test-requirements.md from Acceptance Criteria"**

Mark in_progress after all phase D tasks complete.

Test requirements map acceptance criteria to specific automated tests, and identify criteria requiring human verification. The test-analyst agent uses this during execution to validate coverage.

**Step 1: Generate via subagent**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:opus-general-purpose</parameter>
<parameter name="description">Generating test requirements from Acceptance Criteria</parameter>
<parameter name="prompt">
Read the design at [DESIGN_PATH] and implementation phases in [PLAN_DIR].

Generate test-requirements.md mapping each acceptance criterion to automated tests:
- Criterion, test type (unit/integration/e2e), expected test file path

Human-judgment verification is tracked separately, in uat-requirements.md, which the UAT Requirements Collation step writes AFTER this one. Do not read it or assume it exists. Instead, list every acceptance criterion you did NOT map to an automated test, with a one-line reason. Collation consumes that list and must account for each entry.
</parameter>
</invoke>
```

**Step 2: Present for approval**

Present to the user and use AskUserQuestion. If AskUserQuestion is unavailable, ask inline and wait for an answer before writing.

**If the user requests revisions:**

1. **Create a task for EACH revision** (survives compaction):
   ```
   TaskCreate: "Test requirements fix: <VERBATIM revision request from user>"
   ...one task per revision...
   TaskCreate: "Test requirements: Re-present for approval"
   TaskUpdate: set "Re-present" blocked by all fix tasks
   ```

   **Copy revision requests VERBATIM**, even if long. After compaction, the task description must contain the full details.

2. Address each revision, marking tasks complete as you go
3. Re-present for approval
4. Repeat until approved

**Step 3: Write and complete**

Write to `[PLAN_DIR]/test-requirements.md`. Mark task completed. Proceed to UAT requirements collation.

## UAT Requirements Collation

**Tracked task: "UAT Requirements: Collate uat-requirements.md from phase decisions"**

Mark in_progress after Test Requirements completes.

UAT requirements collect every human-judgment Popper entry the plan produced. The `exec-uat-gate` skill reads this file during execution.

There is one generation route, and it has two inputs.

**Input 1, the accumulated entries.** Phases appended their human-judgment falsification entries to `uat-requirements.md` during step 8 (Task ND), unstamped. Read that accumulated file.

**Input 2, the acceptance criteria no decision covered.** Take the list of unmapped acceptance criteria that Test Requirements Generation produced. For each, judge with the Carnap quality rubric whether it needs human judgement, and construct a falsification entry for any that does. An AC that needs neither an automated test nor a UAT entry must be named with its reason, not silently dropped.

Both inputs then go through the same collation audit below, which scores every entry and re-writes the file with the provenance stamp. **A phase that produced zero entries is normal, and a plan that produces zero entries is valid** — see the minimal form at the end of this section.

**Format:**

```markdown
# UAT Requirements

Human-judgment falsification entries. Each requires a human to USE the built thing
and exercise judgment that automated tests cannot capture.

Quality gate: every entry must have (1) what the human DOES (an action, not inspection),
(2) what they're JUDGING (subjective quality), (3) what FAILURE looks like (concrete experience).

## Phase [N]: [Phase Name]

### DR[X]: [Decision title]

**This decision assumes:** [assumption]
**To shatter it:** [human interaction pursuing the design objective]
**It's wrong if:** [concrete failure experience]

### DR[Y]: [Decision title] (back-reference from Phase [M] DR[Z])

**This decision assumes:** [assumption]
**To shatter it:** [human interaction — deferred from earlier phase]
**It's wrong if:** [concrete failure experience]

## Phase [N+1]: [Phase Name]
...
```

**If no phases produced human-judgment entries:** Write a minimal `uat-requirements.md` whose first line is the collation-audit stamp (`<!-- collation-audit: PASS | 0 entries (all routed to test-requirements) | [YYYY-MM-DD] -->`), followed by "No human-judgment UAT entries. All verification is automated — phases route to exec-coherence-review, not UAT gate." This is a valid outcome for infrastructure-only plans.

**Collation audit — dispatch Sonnet subagent to run three-test rubric on each entry**

Before the stamped `uat-requirements.md` is written, dispatch a subagent (`denubis-basic-agents:sonnet-general-purpose`) with each entry, the three anti-smuggling tests (Decomposition / Reduction / Disagreement), and a prompt instructing:

> For each UAT entry provided below, score:
> 1. Decomposition pass/fail — is What's-automatable genuinely separate from What's-NOT-automatable? If no separation, FAIL.
> 2. Reduction pass/fail — is the "To shatter it" scenario a single integrated experience or a multi-step integration test? If multi-step with each step automatable, FAIL.
> 3. Disagreement pass/fail — would two reasonable people plausibly disagree on "It's wrong if"? If every observer would reach the same verdict, FAIL. **Disclosed-oracle sub-check:** if "This decision assumes" discloses a scalar/threshold/count/rate/status-code/resolves-404 boundary OR a parity-to-baseline comparison ("no worse than the incumbent", "≤ the current rate") whose value would settle "It's wrong if" **on its own**, FAIL however experientially "It's wrong if" is phrased — the boundary need not be a literal number; write an automated check from only the assumes-clause facts; if its output decides the verdict, the sensory wording is laundering a deterministic check. **Mixed-signal exception:** route the disclosed boundary to a test-requirement, then read what remains of "It's wrong if". If a nonempty wrongness condition survives — one a human could trigger while every routed check passes, drawn from the entry's own "It's wrong if" — return SPLIT (keep that condition as the UAT entry). If nothing falsifiable survives in "It's wrong if" once the boundary is routed — the only residual is a judgment asserted in "This decision assumes" or "What's NOT automatable", with no wrongness condition a human could trip — it is decorative → FAIL, not SPLIT. Every entry has a nonempty "What's NOT automatable"; a vibe there is not a surviving wrongness condition, and an entry whose "It's wrong if" enumerates only automatable conditions FAILs even if it invokes a coherence/gestalt judgment elsewhere.
>
> For each entry, output: PASS / FAIL / SPLIT with the deciding test named; or PASS with short rationale. If FAIL, propose how to re-route (test-requirement? rewrite? delete?). If SPLIT, name the automatable boundary to route to a test-requirement and state the residual human judgment that remains the UAT entry.

Pass the subagent's structured output back. For any FAIL or SPLIT, block the collation write and surface to the human:
- Display the entry text
- Display the deciding test (failing test for FAIL; the necessary-but-not-sufficient boundary for SPLIT)
- Propose the rewrite or re-route (for SPLIT: the test-requirement to add AND the trimmed UAT entry that remains)
- Accept human decision: retain-with-rewrite, retain-with-override-acknowledgement, delete, re-route, or accept-split (write the test-requirement, keep the trimmed UAT entry)

Only after all entries either pass, split with human acknowledgement, OR have human-acknowledged overrides does the stamped `uat-requirements.md` get written.

**Why a Sonnet subagent, not critical-peer-review:** The three-test check is narrow. critical-peer-review has a broader scope (evidence-grading, internal inconsistency) and would do more than needed. A Sonnet agent with the three-test rubric as its sole prompt is cheaper and more focused.

**Why a collation audit when step 6.5 self-audit already runs (M6 revision):** Step 6.5 is planner-side pre-presentation self-audit — hygienic but NOT structural (the user can still approve a smuggled entry presented to them). This UAT Requirements Collation audit IS the structural gate: the **Second defensive layer**, where an independent subagent runs every entry in the final `uat-requirements.md` through the three tests before the file is written, scoring every entry the self-audit missed, added outside the design-decisions-mode flow, carried over from earlier sessions that pre-date the self-audit, or approved by the user at step 7 — catching smuggles in the tested disclosed-oracle categories among them, subject to the documented wording-sensitive catch-rate limits (not a catch-all; see the known ceiling under the Disagreement test). The two layers together close the rubric-vs-gate gap identified as the core finding from the 497-min parallel-session audit — "close" in the architectural sense that an independent enforcing layer now exists; the gate's *catch rate* is a calibrated, wording-sensitive property, not a structural guarantee (see the rubric-maintenance note under the Disagreement test).

**Step: Write and complete**

Write to `[PLAN_DIR]/uat-requirements.md`. The **first line** must be the collation-audit provenance stamp — an HTML comment written when this collation step runs, which the Finalization existence gate greps for on the first line (it attests the collation step ran; it is not proof a subagent scored every entry):

```
<!-- collation-audit: PASS | [N] entries scored against Decomposition/Reduction/Disagreement (any FAIL/SPLIT resolved with human acknowledgement) | [YYYY-MM-DD] -->
```

Fill `[N]` (entry count; 0 for the minimal form) and the date at write time. The stamp is the marker the Finalization gate checks for; a `uat-requirements.md` without it (a stale file from a prior session, or a hand-written one) fails the gate. It attests the collation step ran — it is not proof, since a stale or hand-copied marker also passes (the honest bound at the existence gate above). Mark task completed. Proceed to Finalization (the Plan Validation (Finalization Task) section above).

## Execution Handoff

After Finalization completes (existence gate passed), announce:

**"Implementation plan complete and validated. Saved to [count] phase files + test-requirements.md + uat-requirements.md in `docs/implementation-plans/YYYY-MM-DD-<feature-name>/`. The first phase file is `<full-path>`."**

