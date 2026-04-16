# Skill Coherence Review — Working Notes

**Date:** 2026-04-16
**Scope:** Full review of 47 skills, 20 agents across 4 plugins
**Method:** 3 parallel critical-peer-review agents (workflow spine, coding standards, meta/architecture), then cross-cutting synthesis. Frustration signals from conversation history used as empirical test cases.

## Agreed Decisions

### H1: requesting-code-review trigger contradiction

**Problem:** Line 16 says "after each task" but executing-an-implementation-plan says "once per phase." Direct contradiction.

**Agreed fix:**
1. Two mandatory triggers: per-phase (phase-diff scope), pre-merge (full-branch-diff scope)
2. "Major feature" dropped as a separate trigger — it's a phase by another name
3. BASE_SHA guidance must distinguish phase scope (`commit before phase started`) vs full-branch scope (`git merge-base HEAD main`)
4. Line 338-339 "Called by" updated to match reality
5. Description (line 3) keeps "before merging" for discoverability

**Discovery during discussion:** `finishing-a-development-branch` never calls `requesting-code-review` despite line 339 claiming it does. No full-branch review exists before merge/PR. New task H13 created.

**Blocked by:** H13 (wire in full-branch review)

---

### H2: Duplicate DoD ownership

**Problem:** `asking-clarifying-questions` section 5 (lines 177-211) has a "Required Final Step" DoD section that duplicates `starting-a-design-plan` Phase 3. Integration diagram at line 326 also references wrong phase number.

**Agreed fix:**
1. Rip section 5 out of `asking-clarifying-questions` — DoD is Phase 3's job, not clarification's
2. Fix integration diagram phase number (brainstorming is Phase 4 not Phase 3)
3. Phase 3 needs a proper quality rubric for DoD — current "2-4 sentences covering deliverables, success criteria, exclusions" is a format, not a rubric

**Decomposed into:**
- H2a (task 54): Research and build a proper DoD rubric with cited sources
- H2b (task 55): Remove duplicate from asking-clarifying-questions (blocked by H2a)

---

### H3: No guard against premature closure

**Problem:** No phase-count verification before final review. Task list doesn't persist across `/clear` — skill wrongly assumes it does (lines 759, 763). Caused: "fuck, we never did the rest of it. FUCK."

**Agreed fix — structural change to executing-an-implementation-plan:**
1. Per-phase task creation instead of all-phases-upfront
2. Each phase creates its own task list; final task is "prepare /clear and resume for Phase N+1"
3. Last phase's final task is "invoke final review" instead of "invoke next phase"
4. Plan file on disk = source of truth for overall progress
5. Task list = source of truth for current phase only
6. Resume prompt = bridge between phases
7. Remove all claims that task list persists across `/clear`
8. User sees only current phase's tasks (acceptable — otherwise impossible to get actual sense of state)

---

### H12: Popper system redesign (pipeline, quality rubric, template, persistence)

**Problem — three stacked failures:**
1. **Broken pipeline** — Popper entries generated during three-lens analysis then explicitly discarded (line 825: "Plan document contains ONLY the implementation tasks"). human-uat-gate tries to find them, gets nothing, improvises from acceptance criteria. The three-lens analysis is ceremonial.
2. **No quality rubric** — 53% of existing Human Verification entries are tautological ("read template, confirm keywords present"). No principle distinguishing good entries from bad.
3. **Bad template** — decisions are implicit, undeclared, buried inside fake UATs.

**Audit evidence:** Subagent rated every Popper/HV entry across all accessible plans. Zero Popper entries persisted in any plan file. Of HV entries: 26% Good, 53% Tautological, 5% Buried decision.

**Agreed fix — four parts:**

**Part 1: Persistence.** Create `uat-requirements.md` parallel to `test-requirements.md`. Human-judgment falsification entries persist here. Automatable entries go to test-requirements.md. Different consumers, same directory.

**Part 2: Quality rubric (Carnap's Mark I eyeball).** The developer is the instrument. A good UAT entry requires:
1. What the human **does** — an action pursuing the design objective, not a verification procedure
2. What they're **judging** — a subjective quality only a human can evaluate
3. What **failure** looks like — a concrete experience proving the decision wrong

Ruled out: "read X and confirm Y present" (inspection, not use), "run X see Y" (a test), "check that Z works" (unfalsifiable).

**Part 3: Falsification template (Popper as risky statement).** Make the strongest claim the decision implies, then try to shatter it:

```
**This decision assumes:** [the assumption baked into the implementation]
**To shatter it:** [use the built thing for its intended purpose and judge whether the assumption holds]
**It's wrong if:** [the specific experience that shows the assumption failed your intent]
```

The developer uses the system for its purpose and asks: does this match what I meant? The gap between intent and result is the falsification.

**Part 4: Decision record template.** Title declares the recommended decision. Options → Counterarguments → Recommendation → Philosophers comment on the whole:

```
### DR1: Use grouped-by-category prompt vocabulary (recommended)

**Options considered:**
- Grouped by category with descriptions
- Flat sorted list
- Hierarchical with collapsible sections

**Counterarguments:**
- Grouped: may impose taxonomy that doesn't match how the archive works
- Flat: loses semantic structure at 48 labels
- Hierarchical: adds complexity model may not respect

**Recommendation:** Grouped by category — semantic structure helps model understand category boundaries.

**This decision assumes:** the grouping matches how the developer thinks about the source material
**To shatter it:** process a batch of mixed-content pages and judge whether the labels match your understanding of the material
**It's wrong if:** the categories don't map to how you actually think about this archive, or you can't find the right label without fighting the structure

**Haraway:** [only if interesting]
**Lakatos:** [only if interesting]
```

**Sources:** Popper (1959), Carnap's operationalism. Audit data from plan review subagent.

---

### H13: No full-branch code review before merge/PR

**Problem:** finishing-a-development-branch skips straight to "merge or PR?" without reviewing the full branch. requesting-code-review line 339 falsely claims "Called by: finishing-a-development-branch (final review)."

**Agreed fix:** Either finishing-a-development-branch invokes requesting-code-review with full-branch scope before presenting options, or executing-an-implementation-plan schedules it as the final step. Blocks H1 completion.

---

### H4: PEP audit for python-idioms (3.12, 3.13, 3.14)

**Problem:** Skill claims "Python 3.14+" but only covers t-strings and PEP 649. PEP 758 directly caused "3.14 syntax, mate." Full audit reveals 7+ PEPs missing. Also: agents drift to `.venv/bin/ruff` and `python -m ruff` instead of `uv run ruff`.

**Agreed fix:**
1. Version compatibility table — each PEP tagged with minimum version (3.12/3.13/3.14). Key syntax PEPs: 701, 695 (3.12), 696 (3.13), 750, 758, 649, 765 (3.14)
2. Agents must check `python --version` before assuming 3.14 features available
3. Explicit rule: "Use `uv run` for all tooling unless project CLAUDE.md says otherwise. Never `.venv/bin/X` or `python -m X`."
4. 3.12 matters as fallback (vllm requires it)

**Sources:** PEP documents, Python What's New pages for 3.12/3.13/3.14.

---

### H5: Tool/environment verification via `.ed3d/tools.md`

**Problem:** No skill checks tool availability. Caused: "you have pandoc, mate." Agents assume tools missing without checking.

**Agreed fix — lazy discovery persisted to `.ed3d/tools.md`:**
1. Markdown file, each tool is a `##` heading with invocation, version, path, notes/workarounds
2. Rule: before using any external tool, check `.ed3d/tools.md`. If not listed, run `which X` / `X --version`, append, use discovered invocation
3. Never claim unavailable without checking both file and system
4. Instruction in both `coding-effectively` and `systematic-debugging` (different purposes)
5. Absorbs M14 (environment verification guidance)

---

### H6: Fix systematic-debugging deflection failure mode

**Problem:** Phase 3 human-checkpoint protocol says "stop and ask." Missing the inverse: when you have strong evidence, present your analysis as a defended argument. Caused: "you tell me, mate" (agent had telemetry data but asked the human to interpret it).

**Agreed fix:** Add anti-deflection instruction to Phase 3. Toulmin structure: claim, evidence, warrant, anticipated critique. "If you have diagnostic evidence, present it as a defended argument. Do not ask questions you can answer from available data." Complements (not replaces) the "stop and ask when uncertain" protocol — different situations, different responses.

---

### H7: Citation requirement for architecture docs

**Problem:** Architecture docs updated from design plans before implementation, documenting things that don't exist as if they do. Caused: "oh for fuck's sake, mate" (Permission.can_edit documented as existing).

**Agreed fix — citation requirement, not status field:**
1. Every claim must cite its source: file + symbol name (e.g. `src/models/permission.py::Permission`)
2. No line numbers — they shift. File + class/function is durable, greppable
3. Citation determines status implicitly: cites code/migration = exists, cites design plan = planned, cites nothing = must add or remove
4. Prospective content is fine — it just must cite the design plan, making its status visible
5. Fix `update-architecture-docs` to enforce citations on all content

---

### H8-H11: Reference and frontmatter fixes

Quick fixes, no design decisions needed:
- **H8:** `testing-skills-with-subagents:17` — change `superpowers:test-driven-development` → `denubis-plan-and-execute:test-driven-development`
- **H9:** `testing-skills-with-subagents:170` — remove dead `persuasion-principles.md` reference (file doesn't exist)
- **H10:** `syncing-with-upstream:107` — change `Claude Opus 4.5` → `Claude` (generic form, matches commit skill)
- **H11:** `syncing-with-upstream` frontmatter — add `user-invocable: true`

---

### M1: Gate merge-to-main behind project-level opt-in

**Problem:** merge-to-main lacks `disable-model-invocation` and can be auto-invoked. Frustration was about ceremony not being followed.

**Agreed fix:**
1. Add `disable-model-invocation: true`
2. Require project-level opt-in (e.g. `.ed3d/merge-policy`) that says "this project uses direct merge, not PRs"
3. Without that file, refuse and direct to `make-pr`
4. Default workflow is PR; merge-to-main is the exception for tiny projects

---

### M2: CWD re-verification after /clear resume

**Problem:** After /clear, Claude resets to repo root. Agent may edit wrong directory. Caused: "what the fuck is going on?"

**Agreed fix — three checks, non-negotiable, before any work:**
1. If resume prompt indicates worktree, verify it exists via `git worktree list`
2. Verify current branch is NOT main/master
3. Verify current branch matches resume prompt's claim

---

### M3: Orchestrator acceptance rubric for task-implementor output (absorbs M4)

**Problem:** verification-before-completion is passive. TDD doesn't specify full suite. No enforcement mechanism.

**Agreed fix — orchestrator rubric:** When task-implementor reports "done," check:
1. Tests ran per CLAUDE.md command (full suite, not subset)
2. Verification-before-completion evidence present
3. Relevant skills ran and reported (coding-effectively sub-skills, TDD RED-GREEN-REFACTOR, type-check/build)
4. Code review passed (per-phase)
5. Coherence review or UAT (depending on phase type)
6. Refactoring pass if applicable (smell-assessor)
Missing evidence = reject, send back. Also add verification-before-completion to coding-effectively's required sub-skills.

---

### M5: Track critical-peer-review invocation as explicit task

**Problem:** starting-an-implementation-plan:258 mentions invoking critical-peer-review but it's buried prose, not task-tracked. Skipped after compaction.

**Agreed fix:** Track it as a task in the planning phase's task list.

---

### M6: Reconcile mocking rules across TDD and writing-good-tests

**Agreed fix:** Never mock internal code — build scaffolding for isolation. Always mock external boundaries — network, shell, filesystem, third-party APIs. Tests must be isolated. TDD's "no mocks unless unavoidable" replaced with this sharper rule.

---

### M7: Fix datetime.now in howto-develop-with-postgres

**Agreed fix:** Replace Python-side `default_factory=datetime.now` with Postgres-side `sa_column_kwargs={"server_default": text("now()")}`. Database generates tz-aware timestamps. No FCIS tension.

---

### M8: Two mandatory stages for cleanup/docs in implementation plan

**Problem:** Librarian invoked in two places, runs in neither. Documentation/cleanup is treated as optional and gets skipped.

**Agreed fix — two mandatory stages outside normal phase count:**

**Stage 1: Post-implementation cleanup** (after all phases, before final review):
- Librarian updates CLAUDE.md/AGENTS.md
- Architecture docs updated with citations to actual code (file + symbol)
- Implementation-time ADRs created for decisions not in design plan (status: Proposed)

**Stage 2: Post-acceptance** (after final review/UAT passes):
- ADRs move Proposed → Accepted with timestamp
- Architecture docs get final citation pass (now citing accepted code)
- Record of "reviewed, trade-offs acknowledged"

Both mandatory. Not skippable. Remove librarian from executing-an-implementation-plan section 4 and finishing-a-development-branch step 1.

**Sources:** Fowler (bliki), Nygard (2011), Spotify Engineering, AWS Prescriptive Guidance on ADR process.

---

### Frustration check (this session)

One signal: "what the fuck do you mean by task and phase, exactly?" — I used terminology imprecisely while discussing a terminology contradiction fix. Reinforces L13/L14 (glossary needed). Pattern: define terms before using them in discussion.

---

### M9: Deduplicate agent creation guidance

creating-a-plugin cross-references creating-an-agent instead of duplicating.

---

### M11: Fix proleptic-challenge trigger table

Says "During UAT" but fires before UAT/coherence routing. Fix description. Once M25 (rename convention) is done, trigger timing belongs to orchestrator, not worker.

---

### M12: Add TDD and verification-before-completion to coding-effectively

Both more fundamental than currently listed skills. Straightforward.

---

### M13: Anti-tautology guards

Two additions: (1) coherence-review: "don't restate automated test results as coherence findings." (2) code-reviewer: "every verification command must be capable of non-zero exit code. `echo OK` is not verification."

---

### M15: Add scale/capacity to clarifying-questions

"How many users/records/requests? Current limits? Expected growth?"

---

### M16: Cascading-failure rule in systematic-debugging

"If problems appearing in new locations after each fix, blast radius is expanding. STOP. Revert to last known good across ALL affected branches."

---

### M17: Create using-research-agents skill

Covers: (1) when to use which agent, (2) academic research protocol — build bibliography with full citations and DOI URLs, provide curl commands for open-access, note institutional access. Human fetches via DOIs. PDFs in docs/papers/ (gitignored). Agent reads FULL paper, writes discussion in docs/papers/{slug}.md. (3) Anti-pattern: never cite a paper you haven't read in full. Users are academics — proper journal citations and DOIs. Absorbs M23.

---

### M18: Add Test Requirements task to writing-implementation-plans Step 0

Already in example and checklist, missing from spec. Straightforward.

---

### M19: Replace rtk git with plain git in maintain-architecture

RTK hook rewrites transparently. Skills shouldn't reference rtk.

---

### M20: Research agents tools: frontmatter — non-issue

Research agents need broad tool access for M17 bibliography/writing workflow. No restriction needed.

---

### M21: Expand maintaining-project-context skill

Three simple maintenance tasks (CLAUDE.md, test pseudocode, permissions cleanup) go into expanded skill. Dependency rationale stays separate — uses restate-our-assumptions with Popper/Lakatos/Haraway, warrants subagent dispatch.

---

### M22: Fix systematic-debugging "Phase 4.5" reference

Line 629: "Phase 4.5" → "Phase 4, step 5".

---

### M24: Split critical-peer-review with progressive disclosure

SKILL.md keeps core protocol, process rules, output contract, frustration-signal search, advanced analysis (ACH, pre-mortem). Artifact-specific checklists move to checklists/{artifact-type}.md — loaded on-demand. One level deep per Anthropic guidance.

---

### M25: Rename worker skills to {parent}-{action} convention

Worker skills include parent orchestrator name. `family:` frontmatter field. Multi-parent skills keep current names with family metadata. Do LAST.

---

### H14: Frustration-signal search as mandatory step in critical-peer-review

Search conversation history for swearing/"mate" (Australian frustration signal). Each incident = empirical evidence of skill failure. Also check during review — user frustration during findings discussion is data about the review process itself.

---

### Mocking rule (M6)

Never mock internal code — build scaffolding. Always mock external boundaries — network, shell, filesystem, third-party APIs. Tests must be isolated.

---

### datetime.now in postgres examples (M7)

Replace Python-side `default_factory=datetime.now` with Postgres-side `sa_column_kwargs={"server_default": text("now()")}`. Database generates tz-aware timestamps.

---

### Double librarian invocation → two mandatory stages (M8)

Stage 1 post-implementation: update CLAUDE.md, architecture docs with code citations, create implementation-time ADRs (Proposed).
Stage 2 post-acceptance: ADRs → Accepted with timestamp, final citation pass.
Both mandatory. Sources: Fowler, Nygard (2011).

---

### merge-to-main gating (M1)

disable-model-invocation: true. Require .ed3d/merge-policy opt-in. Default is PR.

---

### CWD re-verification after /clear (M2)

Three checks before any work: worktree exists, not on main, branch matches resume prompt.

---

### Orchestrator acceptance rubric (M3, absorbs M4)

Rubric for accepting task-implementor output: tests ran (full suite), verification evidence, relevant skills ran and reported, code review passed, coherence/UAT passed.

---

### Session-naming on resume (L15)

Resume prompt after /clear must include session-naming invocation.

---

### Evidence grading scales (L5) — non-issue

3-level correct for refactoring (no speculative refactoring). 4-level correct for debugging.

---

### Session-naming triple invocation (L4) — non-issue

Each invocation is after /clear. Correct behaviour.

---

### property-based-testing f(x)==f(x) (L6) — reviewer was wrong

Correctly flagged as tautological.

---

### L7-L14: Straightforward fixes

- L7: Typo "ith" → "with"
- L8: Arrow character inconsistency
- L9: Checklist formatting standardisation
- L10: DOI format
- L11: Co-Authored-By format
- L12: TaskCreate optionality note
- L13: "Phase" glossary
- L14: Disambiguate "plan" references

### M10: maintain-architecture vs update-architecture-docs boundary — non-issue

Orchestrator/worker relationship is clear. Inner skill's HALT is a valid safety net.

---

## Implementation Progress

### Completed (8 commits, 2026-04-16)

| Commit | Tasks | Change |
|--------|-------|--------|
| `a893468` | H8 | Fix `superpowers:` → `denubis-plan-and-execute:` in testing-skills-with-subagents |
| `33c173d` | H9, L7 | Remove dead persuasion-principles.md ref, fix "ith" typo |
| `7bee729` | H10, H11 | Fix stale Co-Authored-By, add user-invocable to syncing-with-upstream |
| `021d2a2` | H6, M16, M22 | Anti-deflection (Toulmin), cascading-failure rule, fix "Phase 4.5" ref in systematic-debugging |
| `65efb4e` | M12 | Add TDD and verification-before-completion to coding-effectively required sub-skills |
| `ef8d3e1` | M19 | Replace `rtk git` with plain `git` in maintain-architecture |
| `221f41f` | M7 | Replace datetime.now with server_default in postgres examples |
| `c16e4b9` | M11 | Fix proleptic-challenge trigger table timing descriptions |

### Dismissed as non-issues

M10, M14 (absorbed by H5), M20, M23 (absorbed by M17), L3 (merged with M11), L4, L5, L6

### Remaining — needs implementation

- ~~**H12**: Popper system redesign~~ DONE — uat-requirements.md persistence, Carnap quality rubric, falsification template ("assumes/shatter/wrong if"), decision record template (DR format with options+counterarguments), three anti-smuggling tests (decomposition, reduction, disagreement). Touched: writing-implementation-plans, human-uat-gate, executing-an-implementation-plan
- **M25**: Rename worker skills to {parent}-{action} (do LAST)

### Completed — structural changes (sessions 3-4)

- **H1** + **H13**: Full-branch code review wired into finishing-a-development-branch; requesting-code-review triggers fixed (per-phase + pre-merge scopes with distinct BASE_SHA)
- **H3**: Per-phase task lists, false /clear persistence claim removed, "Prepare for next phase" task defined
- **H4**: PEP version compatibility table (695, 701, 696, 649, 750, 758, 765), tooling rule (uv run), version check
- **H5**: .ed3d/tools.md lazy discovery in coding-effectively + systematic-debugging
- **H14**: Frustration-signal search as step 0 in critical-peer-review
- **M1**: Gate merge-to-main behind .ed3d/merge-policy opt-in
- **M2**: CWD re-verification after /clear (3 checks: worktree exists, not main, branch matches)
- **M3**: Orchestrator acceptance rubric (tests ran, verification evidence, commit hash)
- **M8**: Two mandatory stages (post-implementation cleanup + post-acceptance ADR promotion)
- **M24**: Split critical-peer-review checklists into progressive disclosure (5 checklist files)

- **H7**: Citation requirement — `(file::symbol, commit_hash)` parenthetical citations in DFD, database, state templates + SKILL.md enforcement
- **H2a**: DoD quality rubric — three tests (observable, falsifiable, scoped) + anti-patterns + downstream consumption
- **H2b**: Removed duplicate DoD section from asking-clarifying-questions, fixed phase number references (Phase 3 -> Phase 4)

### Completed — smaller edits (this session, uncommitted)

- **M5**: Track critical-peer-review as task in starting-an-implementation-plan
- **M6**: Reconcile mocking rules (TDD + writing-good-tests) — "never mock internal, always mock external"
- **M9**: Deduplicate agent creation guidance — creating-a-plugin cross-refs creating-an-agent
- **M13**: Anti-tautology guards — coherence-reviewer + code-reviewer both patched
- **M15**: Add scale/capacity to clarifying-questions (new section 4)
- **M18**: Add Test Requirements to writing-implementation-plans Step 0 formal spec
- **M21**: Expand maintaining-project-context — added test pseudocode + permissions cleanup sections
- **L1**: Fix brainstorming diagram numbering (4.1-4.4 -> Phase 1-3)
- **L2**: Fix make-pr branch detection (merge-base -> rev-parse --verify)
- **L8**: Fix arrow characters in creating-a-plugin (replacement chars -> `->`)
- **L9**: Standardise checklists to `[ ]` (was `☐`) across agents and skills
- **L10**: DOI format in restate-our-assumptions (bare DOI -> URL)
- **L11**: Already fixed by H10
- **L12**: TaskCreate optionality in controlled-dependency-upgrade
- **L13**: Phase/task/stage glossary in executing-an-implementation-plan
- **L14**: Disambiguated via glossary (same change as L13)
- **L15**: Session-naming added to resume prompt template
- **Unicode cleanup**: Standardised `→` to `->`, `◻` to `[ ]`, `›` to `-` in modified files

### Remaining — smaller edits

- **M17**: Create using-research-agents skill (new file needed)
- **M25**: Rename convention (LAST)

### Session 5 — Audit + Real-Plan Testing

**Audit of other session's work:** 4 parallel subagents read actual files. All implementations match agreed designs except:
- H1 frontmatter still said "major features" — fixed (commit a27a023)
- M8 Stage 2 positioned before Section 5 (Final Review) despite prose saying "after" — fixed (commit 5f2bf29)
- H2a missing citations and rejection mechanism — fixed (commit bc4e691)
- M3 acceptance rubric missing TDD evidence row — fixed (commit 6ac00fd)

**Real-plan testing against PGT corpus:**

DoD rubric (5 plans, 34 entries): 53% correctly accepted, 24% correctly flagged, 9% over-rejected, 15% under-flagged. Three carve-outs needed: test baselines with specific counts, migration DoDs naming mechanisms, performance/regression claims.

Popper sort (4 plans): Works. Most valuable for weak plans. Export Queue 402 independently invented uat-requirements.md. Three things currently lost: file-upload rendering quality, multi-doc-tabs usability, ban-user suspension experience.

Acceptance rubric (3 plans): 40% false rejection rate. Rubric assumes every task is TDD-able. Real plans have test-only, config, migration, documentation, diagnostic tasks. Needs task-type-aware gating.

**New issues from melica session analysis (three contributing causes):**
- H15: Consumer-tracing requirement — every new function/class/field must state its call site. No call site = no function. Would have killed the orphaned derive_content_types() at planning time.
- H16: Proleptic dismissal requires cited evidence — "I think it's fine" is not dismissal. Must cite specific code, design plan line, or test. The challenger correctly found the doc_type tension; the agent dismissed it with reasoning that was wrong.
- H17: Design conformance check — does the implementation match what the design plan specified? If it deviates, is the deviation recorded as a decision? The design plan said derive_content_types() maps doc_type:*, the implementation plan ignored doc_type:* entirely, nobody compared the two.

**New issues from real-plan testing:**
- H18: DoD rubric carve-outs — 9% over-rejection (test baselines with specific counts, migration DoDs naming mechanisms, performance/regression claims)
- H19: Task-type-aware acceptance rubric gating — 40% false rejection rate. Rubric assumes every task is TDD-able. Needs to read task-type signals and apply appropriate checks.

### Remaining tasks

| Task | Description | Status |
|------|-------------|--------|
| H12 | Popper system redesign (pipeline, persistence, template, rubric) | In progress (separate session) |
| H15 | Consumer-tracing in writing-implementation-plans | Done |
| H16 | Proleptic dismissal requires cited evidence | Done |
| H17 | Design conformance check — impl matches design plan | Done |
| H18 | DoD rubric carve-outs from real-plan testing | Done |
| H19 | Task-type-aware acceptance rubric gating | Done |
| M25 | Rename worker skills to {parent}-{action} | Pending (LAST) |
| L8, L12 | Minor fixes not yet verified | Pending |

## Cross-Cutting Themes Identified

1. **Verification is opt-in, not enforced** — verification-before-completion exists but nothing in the orchestrator enforces it. PARTIALLY FIXED: M12 added it to coding-effectively.
2. **Coding orchestrator is incomplete** — coding-effectively didn't include TDD or verification-before-completion. FIXED by M12.
3. **No skill checks the physical environment** — 47 skills, zero environment verification. DESIGN AGREED (H5: .ed3d/tools.md).
4. **Architecture docs actively document aspirational state as reality** — by design, but caused real frustration. DESIGN AGREED (H7: citation requirement).
5. **Worker skills don't indicate their parent orchestrator** — DESIGN AGREED (M25: {parent}-{action} naming + family metadata). Do LAST.
6. **No full-branch review before merge** — DESIGN AGREED (H13). Blocks H1.
