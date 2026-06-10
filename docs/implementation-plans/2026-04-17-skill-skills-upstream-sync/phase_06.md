# Skill-Skills Upstream Sync — Phase 6: Harden `impl-plan-write` Against UAT Smuggling (Cross-Plugin)

**⚠️ EXECUTION ORDER (L3 revision):** Despite sorting lexically AFTER `phase_05.md`, this phase executes **BEFORE** Phase 5. Phase 5 is the terminal coherent-set commit phase; Phase 6's cross-plugin changes (denubis-plan-and-execute impl-plan-write hardening) must land first so Phase 5's version bump + marketplace + CHANGELOG sync can capture them. Execution order: `phase_01 → phase_02 → phase_02_5 → phase_02_6 → phase_03 → phase_04 → phase_06 → phase_05`.

**2026-06-10 Amendment:** Line anchors in this file (e.g. SKILL.md 728–734, 1285) were verified against `impl-plan-write` at 1,337 lines; main's copy is now 1,348. Re-verify every anchor after the step-0 main merge before editing — the "exact boundaries determined at execution time" rule applies to all edit points, not just smell-assessor targets. Sequencing rule: this phase lands BEFORE the 2026-06-10 audit campaign's planned impl-plan-write restructure (`docs/audits/2026-06-10-skill-audit-campaign.md` tier 5), which would otherwise re-invalidate these anchors.

**Goal:** Close the rubric-vs-gate gap in `denubis-plan-and-execute:impl-plan-write`. The three anti-smuggling tests (Decomposition / Reduction / Disagreement) documented at SKILL.md lines 728-734 are rubric-as-text without forcing function — a planner can emit UAT entries whose falsification is actually automatable, and nothing blocks them. Phase 6 converts the rubric into a gate via (a) template change mandating `**What's automatable:**` / `**What's NOT automatable:**` lines before every UAT entry's falsification template, (b) three-lens-table amendment making "no UAT entry" first-class, (c) per-phase ND rejection gate firing before user approval, (d) Finalization existence gate on `uat-requirements.md`, (e) one-time collation audit via dedicated Sonnet subagent at the `## UAT Requirements Collation` section (SKILL.md line 1285), and (f) retroactive audit of this plan's accumulated entries.

**Architecture:** Cross-plugin edit. Phase 6 modifies `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (1337 lines, multiple scattered edit points) and produces one new audit artefact (`uat-audit-2026-04-17.md`) for this plan. No new skills authored. No runtime behaviour added to Claude Code — changes are to the skill's documentation that guides planner behaviour during design-decisions-mode sessions.

**Tech Stack:** Markdown edits. Python for verification scripts. No new dependencies.

**Scope:** 6 of 6 phases from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md`. Added mid-Part-1 as cross-plugin hardening surfaced by applying impl-plan-write to plan its sibling skills.

**Codebase verified:** 2026-04-17 (Phase 6B direct inspection: impl-plan-write SKILL.md outline captured; all target edit points identified).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### skill-skills-upstream-sync.AC6: `impl-plan-write` anti-smuggling hardening (cross-plugin)
- **skill-skills-upstream-sync.AC6.1 Success:** `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` design-decisions-mode template requires every UAT entry emitted at step 8 (per-phase) to contain `**What's automatable:**` and `**What's NOT automatable:**` lines immediately preceding the `This decision assumes / To shatter it / It's wrong if` falsification block
- **skill-skills-upstream-sync.AC6.2 Success:** `impl-plan-write` `## UAT Requirements Collation` section (SKILL.md line 1285; tracked task "UAT Requirements: Collate uat-requirements.md from phase decisions") gains a one-time audit step: every entry in `uat-requirements.md` is scored against the three anti-smuggling tests (Decomposition / Reduction / Disagreement) by a dedicated subagent before the file is written; failures block collation and are surfaced to the human
- **skill-skills-upstream-sync.AC6.3 Success:** The template change is accompanied in-skill by a worked example: a smuggled-automatable UAT entry is refused (named failing test), and the adapted genuine-surface entry that replaces it is shown
- **skill-skills-upstream-sync.AC6.4 — CUT during M2 revision (2026-04-18).** Earlier drafts specified a `audit-uat-template-compliance.sh` forward-enforcement script embedded inside `impl-plan-write/SKILL.md`. The script was rubric-as-text (never extracted, never run; AC6.4 "coverage" was `grep -q` for the script's name). Cut entirely. Forward-template compliance rests on the in-loop gates: AC6.1 (template mandate) + AC6.2 (collation audit) + AC6.8 (Finalization existence). Future plans that use impl-plan-write inherit these gates.
- **skill-skills-upstream-sync.AC6.5 Edge:** The `uat-requirements.md` in *this* implementation plan is retroactively audited against the three tests as part of Phase 6 (a one-time catch-up audit for Phase 1's entries, plus any added during Phases 2-5 execution); findings are recorded in the plan directory and any smuggled entries are rewritten or deleted with provenance
- **skill-skills-upstream-sync.AC6.6 Success** (M6 revision 2026-04-18: reframed from "rejection gate" to "pre-presentation self-audit"): `impl-plan-write/SKILL.md` Task ND (per-phase file write) is preceded by a pre-presentation self-audit at step 6.5 — before AskUserQuestion at step 7, the planner scores each proposed UAT entry against the three anti-smuggling tests (Decomposition / Reduction / Disagreement) and surfaces pass/fail with suggested re-routing (to test-requirement, deferred-to-future-phase, or "no UAT entry for this decision") so the step-7 conversation is informed. Self-audit does NOT structurally prevent reaching the user; the user CAN approve a surfaced entry. Structural anti-smuggling enforcement is the Task 4 Collation audit (AC6.2) — an independent subagent runs every entry through the three tests before `uat-requirements.md` is written.
- **skill-skills-upstream-sync.AC6.7 Success:** The three-lens table in `impl-plan-write/SKILL.md` at approximately lines 681-686 (Popper row at line 683) is amended so "no UAT entry for this decision" is a **first-class output**, not a failure to find one
- **skill-skills-upstream-sync.AC6.8 Success:** `impl-plan-write/SKILL.md` Finalization-task definition-of-done requires `uat-requirements.md` to exist at PLAN_DIR before Finalization can complete — even if contents are the minimal "No human-judgment UAT entries" form

---

## Dependencies and Sources

**Phase dependencies (execution order):**
- **Phase 1 complete.** Provides the first `uat-requirements.md` entries for retroactive audit (AC6.5).
- Phase 6 executes BEFORE Phase 5 so Phase 5's coherent-set commit captures Phase 6's impl-plan-write deltas (per design plan update).
- No direct dependency on Phases 2, 3, 4 for content — Phase 6 is an impl-plan-write refactor. However, additional UAT entries accumulated during Phases 2-5's planning sessions must be included in the retroactive audit.

**Target file (pre-Phase-6 state, Phase 6B captured outline):**
- `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` — 1337 lines, named-section offsets:
  - Three-lens table: line 681-686 (Popper row at line 683)
  - Design-decisions-mode workflow: line 675-905
  - DR template (step 6 output format): line 838-884
  - Step 7 (AskUserQuestion): line 886-895
  - Step 8 (Task ND + UAT persistence): line 897-904
  - Plan Validation / Finalization: line 1136-1233
  - UAT Requirements Collation: line 1285-1330

**No external dependencies.** Internal skill refactor + one-time audit against this plan's accumulated UAT entries.

**Current state of this plan's `uat-requirements.md` (as of 2026-04-18, post-H3 revision):**
- Phase 1: 4 entries (one direct + three deferred back-references to Phase 4)
- Phase 2: 2 entries (DR-P2-DR8 rubric-callback timing back-ref; DR-P2-DR3 aggressive-language behaviour change)
  - Note: DR-P2-DR2 was removed when persuasion-principles.md import was dropped mid-plan
- Phase 3: 1 entry (DR-P3-DR7 rubric-callback timing back-ref)
- Phase 4: 0 native entries — DR-P4-INT-1 (integration-evidence coherence) was DELETED in H3 revision as unauditable-by-design; the back-referenced entries from Phase 2 DR8 and Phase 3 DR7 still manifest in Phase 4's section
- Phase 5: 1 entry (DR-P5-FRUST-1 frustration-signal audit categorisation — added in H3 revision; replaces DR-P4-INT-1)

Total: 8 entries across the plan (net unchanged: -DR-P4-INT-1, +DR-P5-FRUST-1). Retroactive audit (Task 5) runs the three tests on each.

---

<!-- START_TASK_1 -->
### Task 1: Amend three-lens table — make "no UAT entry" first-class

**Verifies:** skill-skills-upstream-sync.AC6.7

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (three-lens table only, approximately line 681-686)

**Step 1: Locate the three-lens table**

Current text (approximately line 683):
```
| **Popper (falsification)** | What would prove this decision wrong? | **Always.** Every decision gets a falsification test — but the output depends on whether a human can judge it or a machine can (see Popper discipline below). |
```

**Step 2: Replace the Popper row**

Amended text:
```
| **Popper (falsification)** | What would prove this decision wrong? | **Always analyse; output depends on decomposition.** Every decision gets a falsifiability analysis (see Popper discipline below). The UAT entry is the subset of decisions where falsification genuinely requires human judgment. Zero UAT entries is a first-class valid outcome for infrastructure / preparatory-refactor phases and for any phase whose decisions all decompose to automatable checks — "no UAT entry" is NOT a failure to find one. |
```

**Step 3: Verify edit landed**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md') as f:
    content = f.read()
assert 'Zero UAT entries is a first-class valid outcome' in content, 'three-lens table amendment missing'
assert 'no UAT entry' in content, 'zero-UAT framing missing'
print('three-lens table amendment verified')
"
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
git commit -m "refactor(impl-plan-write): amend three-lens table — 'no UAT entry' is first-class

Popper row reframed from 'Always — every decision gets a falsification
test' to 'Every decision gets a falsifiability ANALYSIS; the UAT entry
is the subset where falsification genuinely requires human judgment.
Zero UAT entries is a first-class valid outcome.'

Addresses false-positive pattern: infrastructure phases were producing
mechanistically-automatable Popper entries because the old framing
pushed for them. 'No UAT entry' is now explicitly permitted as an
output, not treated as a failure to find one.

Part of skill-skills upstream sync (Phase 6 AC6.7).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add What's-automatable / What's-NOT-automatable template lines; add worked example

**Verifies:** skill-skills-upstream-sync.AC6.1, skill-skills-upstream-sync.AC6.3

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (DR template at approximately line 838-884; worked-example section near template)

**Step 1: Amend the DR template**

Current DR1 template (approximately line 838-856):
```markdown
### DR1: [Recommended decision statement] (recommended)

**Options considered:**
- [Option A — the recommended choice]
- [Option B]
- [Option C, if applicable]

**Counterarguments:**
- [Option A]: [strongest argument against it]
- [Option B]: [strongest argument against it]

**Recommendation:** [Option A] — [why, in one sentence].

**This decision assumes:** [the assumption baked into the implementation]
**To shatter it:** [use the built thing for its intended purpose and judge whether the assumption holds]
**It's wrong if:** [the specific experience that shows the assumption failed your intent]

**Haraway:** [only if someone bears an invisible cost — vendor lock-in, accessibility, data residency, etc.]
**Lakatos:** [only if DEGENERATING — cite specific evidence of workaround/scope-leak]
```

Amended template (insert new lines between Recommendation and "This decision assumes"):
```markdown
### DR1: [Recommended decision statement] (recommended)

**Options considered:**
- [Option A — the recommended choice]
- [Option B]
- [Option C, if applicable]

**Counterarguments:**
- [Option A]: [strongest argument against it]
- [Option B]: [strongest argument against it]

**Recommendation:** [Option A] — [why, in one sentence].

**What's automatable:** [name the mechanism that CAN be verified by a named command or operational check. If nothing is automatable here, this UAT entry is probably a disguised test-requirement — flag and re-route.]
**What's NOT automatable:** [name the surface judgment that requires a human who has used the built thing. If nothing is NOT automatable, the entry is smuggled — reject.]

**This decision assumes:** [the assumption baked into the implementation]
**To shatter it:** [use the built thing for its intended purpose and judge whether the assumption holds]
**It's wrong if:** [the specific experience that shows the assumption failed your intent]

**Haraway:** [only if someone bears an invisible cost — vendor lock-in, accessibility, data residency, etc.]
**Lakatos:** [only if DEGENERATING — cite specific evidence of workaround/scope-leak]
```

Apply the SAME amendment to the **DR3** template in the same section (M4 revision 2026-04-19 — precise scope). DR3 carries a full UAT entry (`This decision assumes` / `To shatter it` / `It's wrong if`) that persists to `uat-requirements.md`, so it MUST gain the `What's automatable` / `What's NOT automatable` lines between `Recommendation` and `This decision assumes`.

**Do NOT amend DR2 or DR4.** In `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (~lines 858-882) both route entirely to test-requirement via `**Popper:** -> **test-requirement** — write [test type] test: \`test_[name]\` …` and have no falsification block. The `What's automatable` / `What's NOT automatable` lines belong only to UAT entries; adding them to DR2/DR4 templates would teach authors to attach UAT scaffolding to decisions that have no UAT entry, which is the exact smuggling pattern Phase 6 is hardening against.

Scope summary: **DR1 and DR3 get the amendment; DR2 and DR4 do not.**

**Step 2: Add worked example immediately after the DR templates**

Append a new subsection `#### Worked Examples — smuggled entry, genuine entry, zero-UAT phase`:

```markdown
#### Worked Examples — smuggled entry, genuine entry, zero-UAT phase

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
```

**Step 3: Verify edits**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md') as f:
    content = f.read()
# AC6.1: template lines present
assert \"What's automatable\" in content and \"What's NOT automatable\" in content, \
    'what-automatable template lines missing'
# AC6.1 + M4 scope (2026-04-19): DR1 and DR3 carry the What-automatable lines; DR2 and DR4 must NOT
idx_dr1 = content.find('### DR1:')
idx_dr2 = content.find('### DR2:')
idx_dr3 = content.find('### DR3:')
idx_dr4 = content.find('### DR4:')
assert -1 not in (idx_dr1, idx_dr2, idx_dr3, idx_dr4), 'one or more DR template headers missing'
assert idx_dr1 < idx_dr2 < idx_dr3 < idx_dr4, 'DR template ordering broken'
dr4_end = content.find('\\n### ', idx_dr4 + 1)
if dr4_end == -1:
    dr4_end = len(content)
dr1_block = content[idx_dr1:idx_dr2]
dr2_block = content[idx_dr2:idx_dr3]
dr3_block = content[idx_dr3:idx_dr4]
dr4_block = content[idx_dr4:dr4_end]
assert \"What's automatable\" in dr1_block and \"What's NOT automatable\" in dr1_block, \
    'DR1 template missing What-automatable lines (AC6.1)'
assert \"What's automatable\" in dr3_block and \"What's NOT automatable\" in dr3_block, \
    'DR3 template missing What-automatable lines (AC6.1 / M4)'
assert \"What's automatable\" not in dr2_block, \
    'DR2 template incorrectly carries What-automatable line (M4: DR2 routes to test-requirement; must not have UAT scaffolding)'
assert \"What's automatable\" not in dr4_block, \
    'DR4 template incorrectly carries What-automatable line (M4: DR4 routes to test-requirement; must not have UAT scaffolding)'
# AC6.3: worked examples
assert 'Smuggled entry (REJECT)' in content, 'smuggled worked example missing'
assert 'Genuine UAT entry (ACCEPT)' in content, 'genuine worked example missing'
assert 'Zero-UAT output' in content, 'zero-UAT worked example missing'
print('Task 2 structural checks passed')
"
```

**Step 4 (AC6.4) — CUT during M2 revision (2026-04-18).** Earlier drafts specified an `audit-uat-template-compliance.sh` script documented inside `impl-plan-write/SKILL.md` as a fenced bash block. The critical peer review (M2) flagged this as rubric-as-text: the script was never extracted or run, and AC6.4 "coverage" was just `grep -q 'audit-uat-template-compliance'` against the SKILL.md (i.e., the script's *name* being mentioned, not the script executing). The whole mechanism was cut rather than promoted to real enforcement. Forward-template compliance now rests on the in-loop gates: AC6.1 (template change mandates the template in impl-plan-write's DR workflow) + AC6.2 (collation audit runs every entry through the three tests before `uat-requirements.md` is written) + AC6.8 (Finalization existence gate). Future plans that use impl-plan-write inherit these gates; a hypothetical future plan that bypasses impl-plan-write entirely is out of scope for this design.

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
git commit -m "feat(impl-plan-write): mandate What's-automatable/What's-NOT-automatable template lines + worked examples

- Every UAT entry in design-decisions mode must now include two explicit
  header lines before the falsification template:
    **What's automatable:** (mechanism verifiable by named command)
    **What's NOT automatable:** (surface judgment needing human use)
  Missing-or-blank = fail the three anti-smuggling tests at authoring time
  (Decomposition / Reduction / Disagreement enforced structurally).
- Added worked examples section immediately after DR templates:
    Example 1: smuggled entry (REJECT) with named failing test
    Example 2: genuine surface UAT (ACCEPT) with decomposed format
    Example 3: zero-UAT infrastructure phase (first-class valid outcome)
- Addresses the false-positive pattern identified by the parallel-session
  audit: infrastructure phases producing mechanistically-automatable
  Popper entries because the template didn't force decomposition.

Part of skill-skills upstream sync (Phase 6 AC6.1, AC6.3).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Insert per-phase ND pre-presentation self-audit (before step 7; M6 revision: reframed from "rejection gate")

**Verifies:** skill-skills-upstream-sync.AC6.6

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (new step 6.5 between current step 6 and step 7, approximately line 884-886)

**Step 1: Insert the pre-presentation self-audit step (M6 revision: reframed from "rejection gate")**

Between the current step 6 ("Present to user") and step 7 ("Use AskUserQuestion"), insert a new step 6.5:

```markdown
6.5. **Pre-presentation self-audit — apply the three anti-smuggling tests before AskUserQuestion**

This is a pre-presentation self-audit, NOT the structural anti-smuggling gate. The structural gate is the collation audit in Task 4 (UAT Requirements Collation section, SKILL.md line 1285), which dispatches a dedicated subagent to run every entry through the three tests independently of the planner. Step 6.5 is planner-side hygiene that surfaces obvious smuggling BEFORE the user approval in step 7 — making the conversation better. The user CAN still approve a smuggled entry; the collation audit at Task 4 is what actually prevents smuggled entries from reaching `uat-requirements.md`.

Before presenting the DR set to the user for approval (step 7), run each proposed UAT entry (entries with `**What's automatable:**` and `**What's NOT automatable:**` lines) through the three anti-smuggling tests:

1. **Decomposition test** — Is the What's-automatable genuinely separate from the What's-NOT-automatable, or does the What's-automatable already cover what the falsification claims to test?
2. **Reduction test** — Would each step in the "To shatter it" scenario be automatable in isolation? If yes, the entry is a multi-step integration test a human is running by hand — automate it.
3. **Disagreement test** — Would two reasonable people, after using the thing, plausibly disagree about whether "It's wrong if" was met? If every observer would reach the same verdict, the entry is an automated check, not a UAT.

**Self-audit behaviour:**
- If an entry passes all three tests → retain and present to user.
- If an entry fails the Decomposition test → re-route to test-requirements.md (mechanism was automatable; no surface judgment exists).
- If an entry fails the Reduction test → decompose into automatable test-requirements (the scenario is an integration test).
- If an entry fails the Disagreement test → either rewrite the "It's wrong if" clause to describe something genuinely subjective, or re-route to test-requirements.md.
- If all entries fail → **zero UAT entries is the correct output for this phase** (this is the first-class output from AC6.7).

**Why this is a self-audit, not a structural gate (M6 revision):** The user in step 7 CAN approve a smuggled entry if presented with one — the planner-side self-audit does not structurally prevent reaching the user. The structural gate is the collation audit in Task 4, which runs an independent subagent over every entry in the final `uat-requirements.md` before writing. Step 6.5 improves the conversation; Task 4 is the backstop. Present self-audited entries to the user honestly (including any that were self-flagged and re-routed), so step 7's approval is informed.

**Self-audit log:** Record pass/fail for each proposed entry in a brief comment (in-memory; does not need to be persisted). If re-routing to test-requirements, note the target test name.
```

**Step 2: Renumber downstream steps if needed**

Verify the new step 6.5 inserts cleanly between step 6 and step 7 without breaking the existing numbering. The rest of the workflow (steps 7, 8, 9) is unchanged.

**Step 3: Verify edit**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md') as f:
    content = f.read()
# AC6.6: per-phase ND pre-presentation self-audit present (M6 revision: reframed from "gate" to "self-audit" — the structural gate is Task 4 collation audit)
assert 'Pre-presentation self-audit' in content, 'pre-presentation self-audit step missing'
assert 'Decomposition test' in content and 'Reduction test' in content and 'Disagreement test' in content, \
    'three anti-smuggling tests not named in self-audit step'
# Verify it's placed before step 7 (AskUserQuestion)
audit_pos = content.find('Pre-presentation self-audit')
step7_pos = content.find('Use AskUserQuestion', audit_pos)
assert step7_pos != -1, 'step 7 AskUserQuestion not found after self-audit'
assert audit_pos < step7_pos, 'self-audit must precede step 7'
# Verify the self-audit names Task 4 collation audit as the structural backstop
assert 'collation audit' in content.lower() or 'UAT Requirements Collation' in content, \
    'self-audit must reference Task 4 collation audit as the structural gate'
print('Task 3 structural checks passed')
"
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
git commit -m "feat(impl-plan-write): per-phase ND pre-presentation self-audit (step 6.5)

- Insert step 6.5 between 'Present to user' (step 6) and AskUserQuestion
  approval (step 7) that scores each proposed UAT entry against the
  three anti-smuggling tests (Decomposition / Reduction / Disagreement)
  as planner-side hygiene before step 7.
- Explicitly NOT a structural gate (M6 revision 2026-04-18): the user
  CAN still approve a surfaced smuggled entry at step 7. The structural
  anti-smuggling gate is the Task 4 Collation audit — an independent
  subagent runs every entry through the three tests before
  uat-requirements.md is written. Step 6.5 improves the step-7
  conversation; Task 4 is the backstop.
- Four routing outcomes per entry: pass all three (retain and present),
  fail Decomposition (route to test-requirements), fail Reduction
  (decompose into tests), fail Disagreement (rewrite or route). All
  fail → zero UAT entries, the first-class output per AC6.7.

Part of skill-skills upstream sync (Phase 6 AC6.6).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Add Finalization existence gate on uat-requirements.md + UAT Requirements Collation audit

**Verifies:** skill-skills-upstream-sync.AC6.2, skill-skills-upstream-sync.AC6.8

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (Finalization task around line 1136-1233 and UAT Requirements Collation around line 1285-1330)

**Step 1: Amend Finalization task — add uat-requirements.md existence gate**

Within the Finalization section, add a new Step 4 (after existing Step 3 "Complete finalization"):

```markdown
### Step 4: Existence gate — verify `uat-requirements.md` exists at PLAN_DIR

Finalization cannot complete until `uat-requirements.md` exists at `[PLAN_DIR]/uat-requirements.md`. If the file is missing:
- Halt Finalization
- Dispatch the UAT Requirements Collation section (SKILL.md line 1285) now — do not proceed without it
- If the collation produces zero entries (all decisions routed to test-requirements per AC6.7), still write the file in its minimal form:
  ```
  # UAT Requirements — [Plan Name]

  No human-judgment UAT entries. All verification routes to automated tests or operational checks. Phases route to `exec-coherence-review`, not the UAT gate.
  ```

The file must exist regardless. Silent-skip is the failure mode this gate closes — sessions that compact or interrupt during planning can drop the collation step entirely, leaving no record that UAT was considered. Explicit minimal-file output distinguishes "considered and found empty" from "never ran."

Run:
\`\`\`bash
test -f "$PLAN_DIR/uat-requirements.md" || { echo "FAIL: uat-requirements.md missing"; exit 1; }
\`\`\`
Exit 0 → Finalization proceeds. Exit 1 → halt, dispatch collation.
```

**Step 2: Amend UAT Requirements Collation task — add collation audit**

Within the UAT Requirements Collation section (approximately line 1285-1330), add a new step between the current collation step and the write step:

```markdown
**Collation audit — dispatch Sonnet subagent to run three-test rubric on each entry**

Before writing `uat-requirements.md` to disk, dispatch a subagent (`denubis-basic-agents:sonnet-general-purpose`) with each proposed entry, the three anti-smuggling tests (Decomposition / Reduction / Disagreement), and a prompt instructing:

> For each UAT entry provided below, score:
> 1. Decomposition pass/fail — is What's-automatable genuinely separate from What's-NOT-automatable? If no separation, FAIL.
> 2. Reduction pass/fail — is the "To shatter it" scenario a single integrated experience or a multi-step integration test? If multi-step with each step automatable, FAIL.
> 3. Disagreement pass/fail — would two reasonable people plausibly disagree on "It's wrong if"? If every observer would reach the same verdict, FAIL.
>
> For each entry, output: PASS / FAIL with the failing test named; or PASS with short rationale. If FAIL, propose how to re-route (test-requirement? rewrite? delete?).

Pass the subagent's structured output back. For any FAIL, block the collation write and surface to the human:
- Display the entry text
- Display the failing test
- Propose the rewrite or re-route
- Accept human decision: retain-with-rewrite, retain-with-override-acknowledgement, delete, re-route

Only after all entries either pass OR have human-acknowledged overrides does `uat-requirements.md` get written.

**Why a Sonnet subagent, not critical-peer-review:** The three-test check is narrow. critical-peer-review has a broader scope (evidence-grading, internal inconsistency) and would do more than needed. A Sonnet agent with the three-test rubric as its sole prompt is cheaper and more focused.

**Why a collation audit when step 6.5 self-audit already runs (M6 revision):** Step 6.5 is planner-side pre-presentation self-audit — hygienic but NOT structural (the user can still approve a smuggled entry presented to them). This Task 4 collation audit IS the structural gate: the **Second defensive layer**, where an independent subagent runs every entry in the final `uat-requirements.md` through the three tests before the file is written, catching anything the self-audit missed, anything added outside the design-decisions-mode flow, anything from earlier sessions that pre-date the self-audit, and anything the user approved at step 7 that shouldn't have been. The two layers together close the rubric-vs-gate gap identified as the core finding from the 497-min parallel-session audit.
```

**Step 3: Verify edits**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md') as f:
    content = f.read()
# AC6.8: Finalization existence gate
assert 'Finalization cannot complete until' in content, 'Finalization existence gate missing'
assert 'uat-requirements.md' in content, 'uat-requirements.md reference missing'
assert 'No human-judgment UAT entries' in content, 'minimal-form template missing'
# AC6.2: Collation audit
assert 'Collation audit' in content, 'collation audit step missing'
assert 'denubis-basic-agents:sonnet-general-purpose' in content, 'Sonnet subagent not specified'
assert 'Second defensive layer' in content, 'two-layer framing missing'
print('Task 4 structural checks passed')
"
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
git commit -m "feat(impl-plan-write): Finalization existence gate on uat-requirements.md + UAT Requirements Collation audit

- Finalization task gains Step 4: verify uat-requirements.md exists at
  PLAN_DIR before Finalization can complete. If missing, halt and
  dispatch collation. Minimal-form file (stating 'no human-judgment
  UAT entries' explicitly) is a valid output; silence is not.
- Closes the silent-skip hole identified in the 497-min parallel session
  where uat-requirements.md was never written at all (compaction may
  have dropped the collation step).
- UAT Requirements Collation gains a dedicated Sonnet-subagent audit
  step: every entry runs through three-test rubric before the file is
  written. Second defensive layer behind the Task 3 per-ND gate.

Part of skill-skills upstream sync (Phase 6 AC6.2, AC6.8).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Retroactive audit of this plan's uat-requirements.md

**Verifies:** skill-skills-upstream-sync.AC6.5

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-audit-2026-04-17.md`
- Possibly modify: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-requirements.md` (if any entry is smuggled, rewrite in place with provenance)

**Step 1: Dispatch Sonnet subagent with the three-test rubric**

Execute via the Agent tool (example invocation — actual agent call happens at Phase 6 execution time):

> **Agent type:** `denubis-basic-agents:sonnet-general-purpose`
> **Prompt:**
> Read `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-requirements.md`. For each UAT entry (identified by `### DR-` or `### DR-P*` headings), score against the three anti-smuggling tests:
>
> 1. **Decomposition test** — Is "What's automatable" genuinely separate from "What's NOT automatable"? If one is blank or repeats the other, FAIL.
> 2. **Reduction test** — Is the "To shatter it" a single human-integrated experience, or a multi-step integration test each step of which could automate? FAIL if multi-step integration.
> 3. **Disagreement test** — Would two reasonable people plausibly disagree on "It's wrong if"? FAIL if every observer would reach the same verdict.
>
> For each entry, output:
> - Entry heading
> - Decomposition: PASS / FAIL with rationale
> - Reduction: PASS / FAIL with rationale
> - Disagreement: PASS / FAIL with rationale
> - Overall: PASS (retain) / FAIL (recommend rewrite or removal)
>
> Be concise. Evidence-led. If an entry lacks the What's-automatable/What's-NOT-automatable lines, note it and apply the decomposition test to the falsification block alone.

**Step 2: Capture subagent output into audit file**

Write `uat-audit-2026-04-17.md` with structure:

```markdown
# UAT Retroactive Audit — 2026-04-17

Audit of `uat-requirements.md` for skill-skills upstream sync implementation plan.

**Audit trigger:** Phase 6 AC6.5 — retroactive audit of entries accumulated through Phases 1-5 against the three anti-smuggling tests (Decomposition / Reduction / Disagreement), now enforced at authoring time via the Phase 6 template and gate changes.

**Audit method:** `denubis-basic-agents:sonnet-general-purpose` subagent, prompt captured in Phase 6 implementation plan Task 5.

**Audit date:** 2026-04-17

---

## Findings

[subagent output, structured per entry]

---

## Remediation actions

[For each FAIL, note:
- Entry heading
- Failing test
- Action taken: rewrite in place / removed / re-routed to test-requirements.md
- Provenance: commit SHA or "N/A — pre-Phase-6 smuggled entry"]

---

## Audit summary

- Entries audited: N
- PASS: N
- FAIL: N
- Remediated: N
- Retained with override: N (with human-acknowledgement)

```

**Template note:** The audit file must contain ONLY the Sonnet subagent's findings + remediation actions + audit summary. The planner's pre-audit predictions live in this phase file (see "Planner's pre-audit notes" below), NOT in the audit template, so the Sonnet subagent scores independently without reading the planner's expectations first.

**Step 3: Rewrite smuggled entries in place**

For any FAIL entry, edit `uat-requirements.md` directly:
- Add a `<!-- PROVENANCE: rewritten 2026-04-17 per Phase 6 retroactive audit; original failed [test] -->` HTML comment above the rewritten entry
- Apply the rewrite the subagent recommended, or (if no rewrite is possible) delete the entry and note its removal in the audit file

Commit the uat-requirements.md edits separately.

**Step 4: Commit audit file + any remediation edits**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
# First commit: audit file
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-audit-2026-04-17.md
git commit -m "docs(phase-06): retroactive UAT audit for skill-skills upstream sync plan

Sonnet subagent applied three-test rubric (Decomposition / Reduction /
Disagreement) to all 8 UAT entries accumulated through Phases 1-5.

Findings: [summary of PASS / FAIL counts; filled in at execution time]

Per-entry findings, remediation actions, and audit summary in the file.

Part of skill-skills upstream sync (Phase 6 AC6.5).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"

# Second commit (only if remediation edits applied)
# git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-requirements.md
# git commit -m "docs(phase-06): remediate smuggled UAT entries per retroactive audit [N entries rewritten]"
```
<!-- END_TASK_5 -->

---

<!-- START_TASK_6 -->
### Task 6: Rewrite illustrative inline paths in `impl-plan-write/SKILL.md` to angle-bracket placeholder form

**Verifies:** skill-skills-upstream-sync.AC5.4 (supporting — eliminates false-positive FAILs from teaching-material paths when Phase 5's cross-reference audit runs over `impl-plan-write/SKILL.md`)

**Context (H1 revision 2026-04-19):** Phase 5's cross-reference audit uses a path-form regex that matches any backticked string containing `/` and ending in a known extension. `impl-plan-write/SKILL.md` contains illustrative teaching examples (e.g., `` `src/auth.py` ``, `` `tests/services/test_auth.py` ``) that match the regex but do not resolve to real files — they're placeholders showing plan-authors what task descriptions should look like. Under the path-form convention, teaching placeholders use angle-bracket prefix (`` `<src>/auth.py` ``, `` `<tests>/...` ``) so the `<` character fails the path-form regex character class and the placeholder is not audited. This task applies the convention to the existing illustrative paths.

**Files:**

- Modify: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`

**Step 1: Apply the rewrites**

Rewrite the following illustrative backticked paths. Each is a teaching example that currently matches the path-form regex; the angle-bracket prefix opts them out.

| Location (approximate line) | Old | New |
|---|---|---|
| ~113 | `` `src/auth.py` `` | `` `<src>/auth.py` `` |
| ~114 | `` `src/main.py:45-67` `` | `` `<src>/main.py:45-67` `` |
| ~578 | `` `src/services/auth.py` `` | `` `<src>/services/auth.py` `` |
| ~579 | `` `src/services/existing.py:123-145` `` (or similar) | `` `<src>/services/existing.py:123-145` `` |
| ~580 | `` `tests/services/test_auth.py` `` | `` `<tests>/services/test_auth.py` `` |
| ~604 | `` `src/auth/middleware.py` `` | `` `<src>/auth/middleware.py` `` |
| ~604 | `` `src/auth/tokens.py` `` | `` `<src>/auth/tokens.py` `` |
| ~920 | `` `src/__init__.py` `` | `` `<src>/__init__.py` `` |
| ~952 | `` `src/services/feature.py` `` | `` `<src>/services/feature.py` `` |
| ~953 | `` `src/services/existing.py` `` | `` `<src>/services/existing.py` `` |
| ~954 | `` `tests/services/test_feature.py` `` | `` `<tests>/services/test_feature.py` `` |

Line numbers are approximate; use the text content as the source of truth. The actual list may shift slightly after Phase 6 Tasks 1-5 land. Re-run Step 2 below to discover any illustrative paths not on this list.

**Step 1a: Add a convention note in the skill**

Insert a brief note near the top of `impl-plan-write/SKILL.md` (e.g., near the "Task description conventions" section or, if no such section exists, in the "Files:" discussion) documenting the convention so future edits continue it:

> **Teaching-material placeholder convention:** Illustrative file paths in this skill use angle-bracket prefixes — `` `<src>/auth.py` ``, `` `<tests>/services/test_auth.py` `` — so they are not audited by the cross-reference tool (see `docs/issues.md` ISSUE-01 and Phase 5 of the 2026-04-17 skill-skills upstream sync plan). Real file references use path-form without angle brackets.

**Step 2: Verify no illustrative path-form backticks remain**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
# Hunt for any remaining backticked illustrative paths that would match
# the path-form regex. Expect zero hits after the rewrites above land.
python3 -c "
import re
path_re = re.compile(
    r'\`([a-zA-Z0-9_.][a-zA-Z0-9_./-]*/[a-zA-Z0-9_.-]+\.(?:md|js|dot|py|sh|txt))(?::\d+(?:-\d+)?)?\`'
)
text = open('plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md').read()
matches = [(i+1, m.group(1)) for i, line in enumerate(text.splitlines()) for m in path_re.finditer(line)]
# Expected: only real references (not illustrative src/ or tests/ paths).
for line, ref in matches:
    if ref.startswith(('src/', 'tests/')):
        print(f'LEFTOVER ILLUSTRATIVE at line {line}: {ref}')
assert not any(ref.startswith(('src/', 'tests/')) for _, ref in matches), \
    'illustrative src/ or tests/ paths still present — Task 6 rewrite incomplete'
print(f'PASS: {len(matches)} path-form references remain; none are illustrative src/ or tests/')
"
```

Expected: `PASS: N path-form references remain; none are illustrative src/ or tests/` where N is the count of legitimate path-form references (real cross-refs to repo-existing files).

**Step 3: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
git commit -m "feat(impl-plan-write): angle-bracket placeholder convention for illustrative paths

Existing teaching examples in impl-plan-write/SKILL.md used backticked
'src/...' and 'tests/...' paths as concrete illustrations ('Create
\`src/auth.py\`'). Under the Phase 5 cross-reference audit's path-form
convention (H1 revision 2026-04-19), any backticked string containing
'/' and ending in a known extension is treated as a real reference and
must resolve. Illustrative placeholders would fail spuriously.

This commit rewrites 11 illustrative inline paths to angle-bracket form
(e.g., \`src/auth.py\` -> \`<src>/auth.py\`, \`tests/services/test_auth.py\`
-> \`<tests>/services/test_auth.py\`). The '<' character falls outside
the path-form regex character class, so placeholders are skipped by
the audit. A convention note near the top of the skill documents the
pattern for future edits.

No semantic change to the skill's teaching — placeholders remain
concrete enough that plan-authors can see 'oh, a path goes here' while
being syntactically distinct from real repo references.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (AC5.4 support)
      docs/issues.md ISSUE-01 (tool promotion — path-form convention origin)
      docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05.md (Task 1 audit)"
```
<!-- END_TASK_6 -->

---

## Done when (phase-level)

- [ ] Three-lens table amended in impl-plan-write/SKILL.md; "no UAT entry" framed as first-class output (Task 1)
- [ ] DR templates mandate `**What's automatable:**` / `**What's NOT automatable:**` lines; three worked examples present (smuggled REJECT, genuine ACCEPT, zero-UAT phase) (Task 2)
- [ ] Step 6.5 per-phase ND pre-presentation self-audit inserted before AskUserQuestion step 7, with reference to Task 4 collation audit as the structural backstop (Task 3; M6 revision)
- [ ] Finalization Step 4 existence gate on uat-requirements.md present; UAT Collation gains Sonnet-subagent audit step (Task 4)
- [ ] `uat-audit-2026-04-17.md` exists with per-entry findings; any FAIL entries remediated in `uat-requirements.md` with provenance comments (Task 5)
- [ ] Illustrative `` `src/...` `` and `` `tests/...` `` inline paths in `impl-plan-write/SKILL.md` rewritten to angle-bracket placeholder form (`` `<src>/...` ``, `` `<tests>/...` ``); convention note added (Task 6 — H1 revision 2026-04-19 support for Phase 5 audit)
- [ ] Commits land (6+ — one per Task 1-4 plus audit file; Task 5 may produce a second commit for remediations; Task 6 adds one commit)
- [ ] All AC6.* criteria verifiable (AC6.1/6.2/6.3/6.5/6.6/6.7/6.8): grep impl-plan-write/SKILL.md for the mandated strings (template lines, three tests, existence gate, worked examples). AC6.4 was CUT during M2 revision 2026-04-18 — no `audit-uat-template-compliance.sh` or forward-enforcement script lives in the skill.

**Not in scope for Phase 6:**
- Phase 5's version-sync commits (covered by Phase 5 with extended-scope AC5.7)
- Broader impl-plan-write refactoring unrelated to UAT-smuggling hardening
- The stratified-sampling follow-up (flagged as out-of-scope in design plan Additional Considerations — lives in a separate future design)
- Writing the Phase 6 entries into `uat-requirements.md` — Phase 6 has no native UAT entries; all DRs routed to test-requirements

---

## Planner's pre-audit notes (NOT for inclusion in the audit file)

These are the planner's expectations for the Task 5 retroactive audit. They live here so the Sonnet subagent can score `uat-requirements.md` independently against the three tests without reading the planner's predictions first. Task 5's audit file template contains only the subagent's findings + remediation + summary.

**Phase 1's four entries** (one direct AC4.5 coherence + three deferred back-refs for DR-P1-DR1/DR2/DR4) were self-audited mid-planning during the Phase 1 DR approval round and passed all three tests by framing luck, not structural constraint — the planner happened to be thinking decomposition-first while writing them. The retroactive audit should confirm or challenge that pre-assessment; a FAIL on any Phase 1 entry is meaningful evidence that the framing-luck hypothesis was correct.

**Phase 2's two entries** (DR-P2-DR8 rubric-callback timing back-ref; DR-P2-DR3 aggressive-language behaviour) use the post-Phase-6-template gate-form — `**What's automatable:**` / `**What's NOT automatable:**` lines before the falsification template. These were authored after the user surfaced the form-gate observation mid-Phase-2 discussion; they should pass cleanly. (Note: DR-P2-DR2 was removed when the persuasion-principles import was dropped.)

**Phase 3's one entry** (DR-P3-DR7 rubric-callback timing back-ref) uses the gate-form template. Should pass cleanly.

**Phase 4 has no native entries post-H3 revision.** DR-P4-INT-1 (integration-evidence coherence) was flagged by critical peer review (H3 + H7) as unauditable-by-design — the entry's "To shatter it" procedure (audit commit history against GREEN narrative) was a self-attested test because the commits and the narrative share an author; the Sonnet subagent dispatched by this task had access to neither the lived authoring process nor the commit history. The entry was DELETED during H3 revision. Its replacement is DR-P5-FRUST-1 in Phase 5's section (the frustration-signal audit categorisation — see below). The retroactive audit should skip any historical reference to DR-P4-INT-1 and apply the three tests to DR-P5-FRUST-1 in its place.

**Phase 5's one entry** (DR-P5-FRUST-1 frustration-signal audit categorisation — added H3 revision) uses the gate-form template. The Decomposition test should pass (automatable: cc-search-chats queries + match collection; non-automatable: human categorisation of each match); Reduction test should pass (the "To shatter it" names single human judgement calls per match, not a multi-step integration test); Disagreement test should pass ("It's wrong if" names a specific failure mode — zero-frustration verdict despite user recall of unflagged frustration — that reasonable people could dispute).
