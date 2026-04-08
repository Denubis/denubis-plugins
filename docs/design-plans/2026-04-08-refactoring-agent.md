# Refactoring Agent Design

**GitHub Issue:** None

## Summary

This design builds a three-subagent refactoring pipeline for the `denubis-plan-and-execute` plugin. Currently, post-phase refactoring in the execution skill is either absent or reduced to a thin prompt. The new pipeline replaces that with a structured sequence: a `smell-assessor` agent detects code quality problems using static measurement tools and a new `refactoring-rubric` skill grounded in established software engineering literature; a `critical-peer-review` agent (already in the plugin) scrutinises those findings and rejects overclaiming; and a `refactoring-executor` agent applies Fowler refactoring patterns to the findings that survive review. The orchestrator runs concrete measurements before dispatching any agent and short-circuits the pipeline at each gate, so no code is changed unless there is evidence worth acting on.

A secondary capability is added to the planning stage: the `writing-implementation-plans` skill will ask the codebase investigator whether existing files are structurally ready for upcoming changes, and insert an explicit "preparatory-refactor" phase when they are not. This encodes Beck's "make the change easy, then make the easy change" principle into the plan itself, rather than leaving structural impediments to be discovered mid-implementation.

## Definition of Done

1. A refactoring agent exists that performs smell-driven, literature-grounded refactoring of code that has already passed review. It loads the code quality skills (FCIS, coding-effectively, python-idioms) as its evaluation rubric, uses concrete tooling (complexipy via uvx, ruff) for measurable smell detection, and applies Fowler's catalog of refactoring patterns. It enforces the "two hats" discipline — no behaviour changes, tests stay green, revert if they break.

2. The `executing-an-implementation-plan` skill dispatches the refactoring agent with proper context (phase files, working directory, invocation mode) instead of the current thin "simplify code" prompt. It handles both post-phase and preparatory invocation modes.

3. The `writing-implementation-plans` skill can insert preparatory refactoring phases — explicit plan phases where existing code is restructured before an implementation phase, following Beck's "make the change easy, then make the easy change" pattern.

## Acceptance Criteria

### refactoring-agent.AC1: Smell Assessor Produces Structured Report
- **refactoring-agent.AC1.1 Success:** Assessor loads refactoring-rubric and coding-effectively skills, reads complexipy/wc-l/ast-grep measurement data, and produces a smell-report.md with findings structured by Mantyla category, each with location, evidence grade, and suggested Fowler refactoring pattern
- **refactoring-agent.AC1.2 Success:** Assessor writes checkpoint file (smell-report.md) to scratchpad directory, surviving turn exhaustion
- **refactoring-agent.AC1.3 Edge:** When no smells are detected, assessor produces report with empty Findings section and populated "No Action Needed" list proving all categories were assessed

### refactoring-agent.AC2: Critical Review Gates Execution
- **refactoring-agent.AC2.1 Success:** Critical-peer-review receives smell report and phase code, produces reviewed-smell-report.md with per-finding verdicts (proceed/downgrade/reject)
- **refactoring-agent.AC2.2 Failure:** When all findings are rejected by critical review, pipeline skips refactoring execution entirely and announces the result
- **refactoring-agent.AC2.3 Success:** Critical review checks Speculative Generality findings against design plan — findings for abstractions the design calls for are rejected

### refactoring-agent.AC3: Refactoring Executor Applies Patterns Safely
- **refactoring-agent.AC3.1 Success:** Executor works through reviewed findings one at a time, preferring ast-grep for structural transformations, with tests green after each transformation
- **refactoring-agent.AC3.2 Failure:** When a refactoring breaks tests, executor reverts that transformation immediately (does not fix the test) and moves to next finding
- **refactoring-agent.AC3.3 Success:** Executor produces report with Transformations Applied, Transformations Reverted, Complexity Delta (before/after complexipy), and Verification evidence

### refactoring-agent.AC4: Orchestrator Runs Measurement Before Dispatch
- **refactoring-agent.AC4.1 Success:** Orchestrator runs wc -l, uvx complexipy, and ast-grep structural smell rules on phase files before dispatching smell-assessor, writing results to scratchpad
- **refactoring-agent.AC4.2 Success:** Orchestrator dispatches all three subagents in sequence with absolute paths to scratchpad artefacts, phase files, and design plan
- **refactoring-agent.AC4.3 Success:** Gate checks short-circuit the pipeline: no findings after assessment skips critical review and execution; all findings rejected after critical review skips execution
- **refactoring-agent.AC4.4 Failure:** When an agent exhausts its turn budget, orchestrator checks for checkpoint files and reports partial state to human (same recovery pattern as existing agents)

### refactoring-agent.AC5: Preparatory Refactoring Detected by Planner
- **refactoring-agent.AC5.1 Success:** During writing-implementation-plans, codebase-investigator is asked about structural readiness for phases that modify existing files, and impediments are reported
- **refactoring-agent.AC5.2 Success:** When impediments are found, planner inserts a "preparatory-refactor" phase before the implementation phase, with goal referencing the upcoming phase it enables
- **refactoring-agent.AC5.3 Edge:** Planner does NOT insert preparatory refactoring for phases that only create new files (nothing to restructure)
- **refactoring-agent.AC5.4 Success:** Execution skill recognises "preparatory-refactor" phase type and dispatches the three-subagent pipeline with "structural readiness" framing

## Glossary

- **Fowler's refactoring catalog**: A reference catalog of 72 named refactoring patterns (e.g., Extract Method, Inline Variable) from Martin Fowler's *Refactoring* (2018). Provides a shared vocabulary for prescribing specific transformations.
- **Two Hats discipline**: Fowler's metaphor for separating behaviour-preserving refactoring from feature work. When refactoring, no observable behaviour changes; when adding features, no structural tidying. The executor enforces this by reverting any transformation that breaks tests.
- **Mantyla taxonomy**: A five-category classification of code smells (Bloaters, Object-Orientation Abusers, Change Preventers, Dispensables, Couplers) from Mantyla, Vanhanen & Lassenius (2003), "A Taxonomy and an Initial Empirical Study of Bad Smells in Code," ICSM 2003. Used here to organise smell findings into tiers.
- **Tier 1 / Tier 2 / Tier 3 smells**: A prioritisation applied on top of Mantyla's taxonomy in this design. Tier 1 smells are metrics-grounded (detectable by static tools); Tier 2 are design-level (require reasoning); Tier 3 are deferred (require cross-file or historical analysis not feasible in a single-phase run).
- **complexipy**: A Python cognitive complexity analyser, invoked via `uvx` (no install required). Produces a numeric complexity score per function. The pipeline uses a threshold of 15.
- **ast-grep**: A structural code search and transformation tool that matches syntax tree patterns rather than text. Used here both for smell detection (YAML rules) and for applying refactoring transformations.
- **uvx**: The `uv` tool's `run` sub-command, which executes a Python package in an ephemeral environment without requiring a persistent install. Used to run `complexipy` without modifying the project environment.
- **FCIS (Functional Core, Imperative Shell)**: An architecture pattern separating pure computation (no I/O, no side effects) from imperative coordination code. Violations are one of the named smells detected by the pipeline. Also the name of an existing skill in the plugin.
- **Evidence grading (Demonstrated / Plausible / Possible)**: A three-level scale applied to each smell finding by the assessor, indicating how strongly the evidence supports the claim. Grades below a threshold are downgraded or rejected by critical review.
- **Rule of Three**: A heuristic from Fowler: duplication is only a smell worth addressing when it appears three or more times. Applied as a gate before the assessor reports a duplication finding.
- **Speculative Generality**: A specific code smell (Fowler / Mantyla) describing abstractions added in anticipation of future requirements that do not yet exist. Critical review is instructed to reject findings of this smell when the design plan actually calls for the abstraction.
- **Preparatory refactoring**: Beck's pattern of restructuring existing code before implementing a feature, so the feature is easier to add cleanly. This design introduces it as a first-class phase type in implementation plans.
- **Scratchpad directory**: A per-session temporary directory used by agents to write intermediate artefacts (smell reports, reviewed reports, measurement outputs) that persist across turn boundaries and survive agent exhaustion.
- **Checkpoint protocol**: A convention in this plugin where analysis agents write progress files to disk at intervals, so partial work is recoverable if an agent exhausts its turn budget before finishing.
- **Marinescu detection strategies**: Logical combinations of metrics with statistically-derived thresholds for detecting design flaws, from Marinescu (2004). E.g., God Class = (access to foreign data > few) AND (weighted method count >= very high) AND (tight class cohesion < 1/3).
- **iSMELL**: "Assembling LLMs with Expert Toolsets for Code Smell Detection and Refactoring," ASE 2024 (IEEE/ACM). Found hybrid LLM + specialist tools achieves +35% F1 over LLM-only approaches. Motivates the measurement-first pipeline.
- **ICSE 2025 IDE track**: "LLM-Driven Code Refactoring: Opportunities and Limitations." Found 65% of LLM refactoring failures stem from missing context. Motivates providing measurement data to agents.
- **2025 Systematic Review**: "Using LLMs to Enhance Code Quality," ScienceDirect. Found "refactored code by LLMs is not reliable." Motivates the critical review gate between detection and execution.

## Architecture

Three-subagent pipeline for post-phase refactoring, replacing the code-simplifier dispatch (which references a non-existent agent, falling back to orchestrator self-refactoring with a thin "simplify code" prompt). The pipeline separates concerns: detection, review, and execution are distinct agents with distinct models and responsibilities.

### Agent Decomposition

| Agent | Model | Role | Analogy |
|-------|-------|------|---------|
| `smell-assessor` | Sonnet | Structured smell detection against Mantyla taxonomy + skill rubrics. Read-only — no file edits. | Like code-reviewer: structured checklist, analysis-only, writes findings to disk |
| `critical-peer-review` (existing) | Opus | Reviews smell report for overclaiming, downgrades weak findings, gates execution | Already exists — reused with scoped dispatch (evidence grading and overclaiming detection apply; ACH matrix, pre-mortem, and timeline verification are suppressed as inapplicable to smell reports) |
| `refactoring-executor` | Opus | Applies Fowler refactoring patterns to reviewed findings. Prefers ast-grep for structural transformations. | Like task-implementor: makes code changes, checkpoint commits |

### New Skill

| Skill | Purpose |
|-------|---------|
| `refactoring-rubric` | Mantyla taxonomy checklist, Fowler smell-to-refactoring mapping, evidence grading criteria, ast-grep structural detection rules, stopping criteria, Two Hats discipline. Loaded by smell-assessor at startup. |

### Post-Phase Refactoring Pipeline (Mandatory)

Invoked after UAT confirmation, replacing the current section 3d of `executing-an-implementation-plan`:

```
Orchestrator (executing-an-impl-plan)
  |
  +- 1. Measure (orchestrator runs directly, before any agent dispatch)
  |     - wc -l on all phase files -> line-counts.txt
  |     - uvx complexipy <phase-files> --max-complexity-allowed 15 -> complexipy-output.txt
  |     - ast-grep scan with structural smell rules -> structural-smells.json
  |
  +- 2. Dispatch smell-assessor
  |     Input: phase files, measurement outputs, design plan ref
  |     Output: smell-report.md in scratchpad
  |
  +- 3. Gate: if no findings, skip remaining steps
  |     Announce: "No smells detected in phase files. Skipping refactoring."
  |
  +- 4. Dispatch critical-peer-review
  |     Input: smell-report.md, phase code, design plan
  |     Output: reviewed-smell-report.md
  |     Gate: if all findings rejected, skip execution
  |     Announce: "Critical review rejected all N findings. Reasons: [summary].
  |               No refactoring will be performed. Review the rejected findings
  |               above if you disagree."
  |
  +- 5. Dispatch refactoring-executor
  |     Input: reviewed-smell-report.md, phase files, test commands
  |     Output: refactored code, committed separately
  |
  +- 6. Verify green (orchestrator runs tests as final safety net)
```

### Preparatory Refactoring (Optional, Planner-Inserted)

During `writing-implementation-plans`, the codebase-investigator already runs per-phase. For phases that modify existing files, the investigator gets an additional structural readiness question. If impediments are found, the planner inserts a "preparatory-refactor" phase before the implementation phase.

Preparatory refactoring uses the same three-subagent pipeline but with a different framing: the assessor evaluates "structural readiness for upcoming phase goal" rather than "quality of completed phase."

**Detection heuristic:** The structural readiness question asked during codebase investigation is intentionally open-ended rather than threshold-based. The investigator assesses whether the target files' current structure would make the upcoming phase unnecessarily difficult — mixed concerns that need splitting, hardcoded assumptions that need generalising, missing seams. This is a judgment call, not a metric gate. The heuristic is expected to iterate as we gain experience with what impediments look like across codebases.

**Subagent boundaries are deliberate context isolation.** Each agent in the pipeline gets a clean context window. The assessor reads code without the orchestrator's accumulated execution context. The critical reviewer evaluates findings without the assessor's reasoning biases. The executor acts on reviewed prescriptions without detection context bleeding in. This is the same principle that motivates `/clear` between design and implementation planning.

### Relationship to Code Reviewer

The code-reviewer and refactoring pipeline serve different purposes:

| Concern | Code Reviewer | Refactoring Pipeline |
|---------|--------------|---------------------|
| Question asked | "Did it do the job?" | "Is this good code that does the job?" |
| Scope | Diff (BASE_SHA..HEAD_SHA) | Phase files holistically |
| Standards | Compliance checklist (type safety, error handling, test coverage, security) | Design quality rubric (complexity, coupling, FCIS, duplication, abstraction) |
| Output | Issue list (Critical/Important/Minor) | Smell report with evidence grades and refactoring prescriptions |
| Runs when | After implementation, before fixes | After UAT confirmation, after review is clean |

## Existing Patterns

### Agent Structure

All agents in `plugins/denubis-plan-and-execute/agents/` follow a consistent structure:

- YAML front matter: `name`, `description`, `model`, `color` (optional `tools` when restricted)
- Mandatory First Actions section (load skills, read input)
- Checkpoint Protocol (code agents: WIP commits; analysis agents: write-to-disk progress files)
- Process steps
- Report template with evidence requirements
- MUST/MUST NOT Do sections

The smell-assessor follows the code-reviewer pattern (analysis agent, checkpoint to disk). The refactoring-executor follows the task-implementor pattern (code agent, WIP commits).

### Dispatch Pattern

All agents dispatched via `<invoke name="Task">` XML blocks with:
- `subagent_type`: `denubis-plan-and-execute:[agent-name]`
- `max_turns`: 150 (calibrated minimum, do not reduce)
- Absolute paths for all file references
- `SCRATCHPAD_DIR` for session isolation

### Skill Loading

Agents load skills dynamically based on task content. The refactoring-rubric skill is loaded by the smell-assessor; coding-effectively and using-ast-grep are loaded by the refactoring-executor. This follows the existing pattern where task-implementor loads test-driven-development, verification-before-completion, and language-specific skills.

### Separate Rules Directory

ast-grep YAML rules for structural smell detection live in a `rules/` directory alongside the refactoring-rubric skill, with individual `.yaml` files per smell. This follows the pattern of keeping testable artefacts separate from prose documentation.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Refactoring Rubric Skill

**Goal:** Create the knowledge base that grounds all smell detection and refactoring decisions.

**Components:**
- `skills/refactoring-rubric/SKILL.md` — Mantyla taxonomy checklist (Bloaters, OO Abusers, Change Preventers, Dispensables, Couplers), Fowler smell-to-refactoring mapping table, evidence grading criteria (Demonstrated/Plausible/Possible), Rule of Three gate, Two Hats discipline rules, Tier 3 deferred smells registry
- `skills/refactoring-rubric/rules/` — ast-grep YAML rules for structural smell detection (Tier 1 only — smells requiring counting or comparison are Tier 2, assessed by the LLM):
  - `nesting-depth.yaml` — functions with >3 levels of nested control flow
  - `fcis-violation.yaml` — functions containing I/O calls (open, requests.*, pathlib write/read, db.* — enumerated list, inherently brittle but useful as a signal)
  - `long-parameter-list.yaml` — functions with >=4 parameters
  - `global-mutable-state.yaml` — module-level non-constant assignments

**Dependencies:** None (first phase)

**Done when:** Skill file loads correctly. ast-grep rules match expected patterns in test fixtures. Taxonomy covers all Tier 1 and Tier 2 smells from Mantyla's categories.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Smell Assessor Agent

**Goal:** Create the read-only analysis agent that produces structured smell reports.

**Components:**
- `agents/smell-assessor.md` — Agent definition following code-reviewer pattern. Loads refactoring-rubric and coding-effectively skills. Two-pass assessment: metrics-grounded (Tier 1) then design-level (Tier 2). Writes smell-report.md to scratchpad with checkpoint protocol.

**Dependencies:** Phase 1 (rubric skill must exist for agent to load)

**Done when:** Agent definition follows established agent patterns. Loads correct skills. Output format matches the smell-report.md structure (Complexity Measurements, Findings with evidence grades, No Action Needed section, Deferred Tier 3 section).
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Refactoring Executor Agent

**Goal:** Create the code-changing agent that applies reviewed refactoring prescriptions.

**Components:**
- `agents/refactoring-executor.md` — Agent definition following task-implementor pattern. Loads refactoring-rubric, coding-effectively, and using-ast-grep skills. One-finding-at-a-time execution. Prefers ast-grep for structural transformations, manual edit as fallback. Revert-on-red discipline. Complexity delta reporting.

**Dependencies:** Phase 1 (rubric skill must exist for agent to load)

**Done when:** Agent definition follows established agent patterns. Loads correct skills. Includes ast-grep usage patterns for common refactorings. Report format includes Transformations Applied, Transformations Reverted, Complexity Delta, and Verification sections.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Orchestrator Integration (executing-an-implementation-plan)

**Goal:** Replace the thin code-simplifier dispatch with the three-subagent pipeline.

**Components:**
- `skills/executing-an-implementation-plan/SKILL.md` — Modify section `#### 3d. Phase Refactor` with: measurement step (wc -l, complexipy, ast-grep rules), smell-assessor dispatch, gate check, critical-peer-review dispatch (scoped: evidence grading and overclaiming detection only, suppress ACH/pre-mortem/timeline), gate check, refactoring-executor dispatch, final verification. Update turn budget table to include smell-assessor (150) and refactoring-executor (150). Note: this increases the maximum per-phase refactoring cost from 150 turns (current code-simplifier) to 450 turns (three agents at 150 each), mitigated by gate short-circuits. Update null/empty response handling for new agents. Update phase completion flow diagram.

**Dependencies:** Phases 1, 2, 3 (all agents and skill must exist)

**Done when:** Section 3d dispatches the full pipeline. Measurement commands run before agent dispatch. Gate checks short-circuit when no findings or all findings rejected. Scratchpad directory used for all intermediate artefacts. Transparency rules followed (print each subagent response).
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Preparatory Refactoring (writing-implementation-plans)

**Goal:** Enable the implementation planner to insert preparatory refactoring phases.

**Components:**
- `skills/writing-implementation-plans/SKILL.md` — Modify per-phase codebase investigation to include structural readiness question for phases modifying existing files. Add "preparatory-refactor" as a recognised phase type alongside "infrastructure" and "functionality". Document the phase template for preparatory refactoring (Goal references upcoming phase, Verifies: None, success = tests green after restructuring).
- `skills/executing-an-implementation-plan/SKILL.md` — Add handling for "preparatory-refactor" phase type: dispatches the three-subagent pipeline with "structural readiness" framing instead of "post-phase quality" framing.

**Dependencies:** Phase 4 (orchestrator must already have the pipeline)

**Done when:** Planner can insert preparatory refactoring phases based on investigator findings. Execution skill recognises the phase type and dispatches the pipeline with appropriate framing. Template for preparatory refactoring phases documented.
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Documentation and Deferred Scope

**Goal:** Document the Tier 3 deferred smells and future codebase-level refactoring requirements.

**Components:**
- Within `skills/refactoring-rubric/SKILL.md` Part 6 (Tier 3 Registry) — detailed documentation of each deferred smell (Shotgun Surgery, Divergent Change, Insider Trading, Mysterious Name, cross-file duplication, God Module), detection approaches (git history analysis, import graph, similarity analysis), and what a future codebase-level refactoring skill would need
- Version bump for `denubis-plan-and-execute` in `plugin.json`, `marketplace.json`, and `CHANGELOG.md`

**Dependencies:** Phases 1-5 (all implementation complete)

**Done when:** Tier 3 registry is comprehensive with detection approaches for each deferred smell. Version bumped and changelog updated. All files committed.
<!-- END_PHASE_6 -->

## Additional Considerations

### Literature Grounding

This design is grounded in:
- **Fowler (2018):** Refactoring catalog (72 patterns), Two Hats metaphor, six refactoring workflows
- **Beck (2003):** Red-Green-Refactor cycle, "make the change easy, then make the easy change"
- **Mantyla, Vanhanen & Lassenius (2003):** Five-category smell taxonomy (Bloaters, OO Abusers, Change Preventers, Dispensables, Couplers), ICSM 2003
- **Marinescu (2004):** Detection strategies — logical combinations of metrics with thresholds
- **Lanza & Marinescu (2006):** Operationalised detection for ~15 smells via composite metric rules
- **DECOR/Moha et al. (2010):** Formal smell specification via DSL
- **iSMELL (ASE 2024):** "Assembling LLMs with Expert Toolsets for Code Smell Detection and Refactoring," IEEE/ACM ASE 2024 — hybrid LLM + specialist tools achieves +35% F1 over LLM-only approaches
- **ICSE 2025 IDE track:** "LLM-Driven Code Refactoring: Opportunities and Limitations" — 65% of LLM refactoring failures stem from missing context
- **2025 Systematic Review:** "Using LLMs to Enhance Code Quality," ScienceDirect — "Refactored code by LLMs is not reliable," validates the critical review gate

### Complexity Thresholds

Following PromptGrimoireTool's established configuration:
- Cognitive complexity: <=15 (complexipy, enforced at commit in PGT)
- Function length: <=40 lines (coding-effectively signal)
- File length: <=400 lines (coding-effectively signal)
- Nesting depth: <=3 levels (ast-grep rule)
- Parameter count: <4 preferred (ast-grep rule, Long Parameter List smell)

### What This Design Does NOT Do

- **Codebase-level refactoring (Mode C):** Deferred. Requires git history analysis, cross-module scope, and its own design plan. The Tier 3 registry documents requirements for future work.
- **Replace the code reviewer:** The reviewer checks compliance; the refactoring pipeline improves design quality. Different concerns, different agents, different timing.
- **Run ruff or ty:** Those are infrastructure hooks that already run on every file save and commit. The refactoring pipeline operates above the linting layer.
- **Refactor JavaScript:** Python-primary. JS files may be touched incidentally but the rubric, ast-grep rules, and skill references are Python-focused.
