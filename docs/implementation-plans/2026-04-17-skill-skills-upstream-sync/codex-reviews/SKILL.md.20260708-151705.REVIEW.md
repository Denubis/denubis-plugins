# Critical Peer Review: SKILL.md

Reviewer: Codex (GPT-5)
Date: 2026-07-08
Document reviewed: context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md

## Hidden Assumptions

- The model-tier split is complete enough that `SKILL.md` no longer carries stale-prone model claims. Evidence status: contradicted by target line 96 and supporting file line 17.
- Directive authors will consult `model-tier-notes.md` whenever a target model matters. Evidence status: partially supported by `SKILL.md:231`, but weakened by current-model claims remaining inline.
- The short “Testing Directives” section is sufficient to satisfy the project’s TDD-for-skills protocol. Evidence status: weak; `writing-skills/SKILL.md:105` requires edit-scoped re-entry and re-testing, while target lines 265-269 only give a three-step baseline/apply/iterate loop.
- Broad prompt-engineering claims in the target are either generally known or externally sourced. Evidence status: unverified in staged context; no internet is available.

## ACH Matrix

| Hypothesis | E1: target points to model notes | E2: target has inline “Current Claude models” source claim | E3: long-running reference has “Current Claude models” claim | E4: model notes define staleness guard | E5: tests enforce only model-tier-notes | E6: writing-skills requires edit-scoped TDD |
|---|---:|---:|---:|---:|---:|---:|
| H1: Model-anchor move fully succeeded | + | - | - | + | - | ? |
| H2: Move improved the skill but left stale-prone gaps outside the source of truth | + | + | + | + | + | + |
| H3: Main defect is general skill-authoring protocol noncompliance, not model notes | ? | ? | ? | ? | ? | + |

Decision rule: H2 survives with the fewest contradictions. The strongest contradiction against H1 is that the target still says, “Current Claude models overtrigger on these markers” in `SKILL.md:96`, outside the staleness-controlled model note file.

## Findings

### High (count: 1)

- **Issue**: The model-version-anchor extraction is incomplete: current-model behavioural claims remain outside the declared single source of truth and outside the standing freshness test.
  **Evidence**: Target `SKILL.md:96` says, “Current Claude models overtrigger on these markers, reading urgency as content-signal rather than emphasis.” The supporting file explicitly says, `model-tier-notes.md:13`, “Other files in this skill — including its `SKILL.md` — reference this roster rather than naming versions inline, so a model release is a one-place update.” But `long-running-state-patterns.md:17` also says, “Current Claude models receive updates on remaining context after tool calls.”
  **GRADE factors**: Risk of bias and reporting bias. The freshness enforcement is scoped to `model-tier-notes.md`: `test_model_tier_freshness.py:33` names only `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md`.
  **Ripple**: A future model release can make `SKILL.md:69`, `SKILL.md:96`, `SKILL.md:103`, `SKILL.md:217`, `SKILL.md:248`, and `long-running-state-patterns.md:17` stale without tripping the freshness test.
  **Corrected language**: Move current-model behavioural claims into `model-tier-notes.md`; in `SKILL.md`, say only “See `model-tier-notes.md` for current model-specific responsiveness, overtriggering, and overengineering notes.”
  **Location**: context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:96

### Medium (count: 3)

- **Issue**: The rubric callback covers “new directive” creation but not scope-changing edits, which conflicts with the project’s own skill-authoring protocol.
  **Evidence**: Target `SKILL.md:135` says, “Before writing a new directive, check whether the underlying agent-task-or-skill passes the `denubis-extending-claude:epistemic-humility` rubric.” The governing protocol says, `writing-skills/SKILL.md:42`, “Before committing to creation — or to an edit that changes a skill's scope — apply the rubric”.
  **GRADE factors**: Indirectness: this is a protocol conformance finding, not a runtime failure.
  **Ripple**: Authors editing triggers, audience, or model routing can skip the rubric because the local callback names only new directive writing.
  **Corrected language**: “Before writing a new directive or editing one in a way that changes scope, triggers, audience, or failure consequences, apply `denubis-extending-claude:epistemic-humility`.”
  **Location**: context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:135

- **Issue**: “Testing Directives” is too weak for project skill-authoring TDD; it omits independent RED evidence, edit-scoped re-testing, and subagent pressure testing.
  **Evidence**: Target `SKILL.md:267-269` says, “Baseline: Run scenario WITHOUT directive, document failures”; “Apply: Add directive, verify compliance”; “Iterate: Find new loopholes → add counters → re-test”. The project protocol says, `writing-skills/SKILL.md:9`, “Iron Law: no skill without a failing test first,” and `writing-skills/SKILL.md:105`, “Any edit that could weaken compliance re-runs the pressure scenarios it could plausibly weaken”.
  **GRADE factors**: Imprecision: no run evidence shows authors actually misapply it, but the local instruction is structurally weaker than the invoked protocol.
  **Ripple**: A skill author can satisfy the target’s testing section using an invented scenario or a one-pass “verify compliance” check while still violating the stronger RED/GREEN/REFACTOR method.
  **Corrected language**: Add a pointer to `testing-skills-with-subagents` and require independent RED baseline evidence plus edit-scoped pressure re-runs for compliance-affecting edits.
  **Location**: context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:265

- **Issue**: Several load-bearing prompt-engineering claims are asserted without provenance in the staged context.
  **Evidence**: Target `SKILL.md:35` says, “More instructions = uniform degradation across ALL rules.” Target `SKILL.md:157` says, “XML outperforms markdown, JSON, or YAML for rule preservation in long prompts.” Search found those claims only in the target: `rg` output included `SKILL.md:35` and `SKILL.md:157`, with no supporting hit in `anthropic-best-practices.md` or `context/docs`.
  **GRADE factors**: Indirectness and reporting bias. Confirming or refuting needs external prompt-engineering evidence, which is unavailable here.
  **Ripple**: Because the target is itself an authoring guide, unsupported universal claims can propagate into new directives as hard rules.
  **Corrected language**: Hedge or cite: “Long prompts can dilute instruction adherence; keep critical rules concise and tested.” For XML: “Use XML for multi-part prompt structure when it improves parseability; test against markdown/JSON/YAML when the distinction is load-bearing.” [unverified — needs external check: current Anthropic prompt-structure evidence for XML superiority and instruction-count degradation]
  **Location**: context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:35

### Low (count: 0)

## Verification

- `ls -R context` ran successfully and listed the target path under `context/plugins/denubis-extending-claude/skills/writing-claude-directives/`.
- `test -f context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md && echo TARGET_FOUND` output: `TARGET_FOUND`
- `wc -l ...` output included: `281 .../writing-claude-directives/SKILL.md`, `138 .../model-tier-notes.md`, `205 .../long-running-state-patterns.md`, `175 .../graphviz-conventions.dot`.
- `rg -n "Current Claude models|current models|current tier|current versions|single source of truth|verified 2026|Source: <https|model-tier-notes\.md" context/plugins/denubis-extending-claude/skills/writing-claude-directives` output included `SKILL.md:69`, `SKILL.md:96`, `SKILL.md:217`, `long-running-state-patterns.md:17`, and `model-tier-notes.md:11`.
- `rg -n "Before writing a new directive|Testing Directives|Baseline|Iron Law|Editing an existing skill|scope-changing edit|Before committing to creation" ...` output included `SKILL.md:135`, `SKILL.md:265`, `writing-skills/SKILL.md:9`, `writing-skills/SKILL.md:42`, and `writing-skills/SKILL.md:105`.
- `rg -n "XML outperforms|150 instruction|uniform degradation|Placement matters|higher attention" ...` output included only target hits for the challenged claims.

## Strongest Hypothesis

The strongest hypothesis is H2: moving model-version anchors into `model-tier-notes.md` improved maintainability but left stale-prone current-model claims in `SKILL.md` and `long-running-state-patterns.md`. The target itself points to the source of truth, while still carrying current-model assertions outside it.

## Weakest Hypothesis

The weakest hypothesis is H1: the split fully succeeded. It fails against direct target evidence at `SKILL.md:96` and supporting-file evidence at `long-running-state-patterns.md:17`.

## Pre-Mortem

If this review is wrong, the next failure would likely show that the project intentionally permits generic “Current Claude models” claims in orchestrators while only version IDs live in `model-tier-notes.md`. I found no such exception in the staged files.

Alternative failure scenario 1: the freshness test is intentionally narrow and human review catches all other current-model claims. Evidence against: `model-tier-notes.md:13` says model release becomes “a one-place update.”

Alternative failure scenario 2: target brevity intentionally omits full TDD details because `writing-skills` orchestrates them. Evidence for: `writing-skills/SKILL.md:99` says the orchestrator sequences the sub-skills. Evidence against: target has its own `## Testing Directives` section, so readers can treat it as complete.

Alternative failure scenario 3: XML and 150-instruction claims are supported by external Anthropic docs not staged here. Status: [unverified — needs external check: current Anthropic prompt-engineering documentation or experiment records]

## Fastest Next Test

Add a grep-based freshness check over the whole `writing-claude-directives/` directory for `Current Claude models`, `current models`, and same-line external citations outside `model-tier-notes.md`. If it flags the current target/supporting-file lines, either move those claims into `model-tier-notes.md` or explicitly document why they are model-independent.

## Overall Assessment

Needs revision. The skill is broadly useful and mostly coherent, but it is not ready as a whole-skill authoring guide until the remaining current-model claims are either centralized in `model-tier-notes.md` or covered by the same freshness discipline, and the local testing/rubric sections are brought into line with `writing-skills` for edits as well as new directives.