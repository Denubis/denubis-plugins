# Critical Peer Review: SKILL.md

Reviewer: Codex (GPT-5)
Date: 2026-07-08
Document reviewed: context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md

## Hidden Assumptions

1. Load-bearing: a RED baseline can be screened by the executor without reopening self-licensing.
Evidence status: contradicted. The target says, “**Independent-session gate — RED baseline MUST come from a session that is NOT this executor, not from invention:**” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:83, but later permits process-adjacent evidence to be argued back in at line 94.

2. Load-bearing: named harness tools are available or have fallbacks.
Evidence status: partially unsupported. The target says, “use AskUserQuestion to ask” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:55 and “reconsider with AskUserQuestion” at line 71. The project protocol says, “A directive that names a harness tool (`AskUserQuestion`, `EnterPlanMode`, `Agent`/`Task`, MCP tools) must state the fallback when the tool is absent” at context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:129-131.

3. Load-bearing: current model-tier claims are stable enough to live inline.
Evidence status: weak. The target embeds Haiku-specific operator guidance at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:63. The model notes say, “Current tier (single source of truth)” at context/plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md:11 and “Other files in this skill — including its `SKILL.md` — reference this roster rather than naming versions inline” at line 13. The scoped applicability to this separate skill is inferred, not directly stated.

4. Load-bearing: the revised file effectively teaches pressure-testing.
Evidence status: supported for the current target. The target has RED/GREEN/REFACTOR mapping at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:38-49, pressure scenarios at lines 126-170, loophole closure at lines 172-259, pressure coverage at lines 261-312, and meta-testing at lines 313-339. Branch-delta effectiveness is [unverified — needs external check: base branch or git diff; `context` is not a git repository].

## ACH Matrix

Hypotheses:
- H1: The target is fit for purpose with only minor edits.
- H2: The target teaches the core method but has evidence-gate defects that can undermine RED.
- H3: The target fails the project’s skill-authoring protocols broadly.

| Evidence | H1 | H2 | H3 |
|---|---:|---:|---:|
| “Run scenario WITHOUT skill, watch agent fail” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:42 | + | + | − |
| “There is no third path.” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:96 | + | + | − |
| “If only process-adjacent evidence exists, state explicitly why it still counts” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:94 | − | + | + |
| “must state the fallback when the tool is absent” at context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:129-131 versus target AskUserQuestion lines 55 and 71 | − | + | + |
| “Pressure-Scenario Completeness Coverage” framing at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:261-304 | + | + | − |
| “Signs of bulletproof skill” / “Not bulletproof if” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:340-353 | + | + | − |

Decision rule: H2 requires the fewest contradictions. The target is substantially effective, but two protocol defects hit the evidence gate and tool fallback path.

## Findings

### High (count: 1)

- **Issue**: The RED-baseline gate reopens the self-licensing loophole it is supposed to close.
  **Evidence**: The target establishes a hard gate: “**Independent-session gate — RED baseline MUST come from a session that is NOT this executor, not from invention:**” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:83 and “**There is no third path.**” at line 96. But the qualifying checklist says: “If only process-adjacent evidence exists, state explicitly why it still counts, grade it as weaker, or prefer path 2.” at line 94. That creates a third path: executor-argued process-adjacent evidence.
  **GRADE factors**: Risk of bias and reporting bias. The exact evidence source being guarded against can be admitted by explanation.
  **Ripple**: The checklist later repeats the gate as “Sourced the RED baseline from an independent session” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:386, but the earlier escape clause means the check can pass on weakened evidence.
  **Corrected language**: Replace the line 94 escape with: “Process-adjacent evidence does not satisfy this gate by itself. If it is all you have, use path 2 or halt for human decision.”
  **Location**: context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:94

### Medium (count: 3)

- **Issue**: `AskUserQuestion` is named without the required absent-tool fallback.
  **Evidence**: The target says, “If you're unsure which model users will run, use AskUserQuestion to ask — recommend Sonnet as the default.” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:55 and “You chose the wrong test tier — reconsider with AskUserQuestion” at line 71. The directive-writing protocol says, “A directive that names a harness tool (`AskUserQuestion`, `EnterPlanMode`, `Agent`/`Task`, MCP tools) must state the fallback when the tool is absent — "if unavailable, ask inline".” at context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:129-131.
  **GRADE factors**: Direct evidence from target and sibling protocol.
  **Ripple**: A session without `AskUserQuestion` can stall at model-tier selection, which is a prerequisite for RED/GREEN testing.
  **Corrected language**: Add “If `AskUserQuestion` is unavailable, ask inline and wait for the answer.”
  **Location**: context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:55 and :71

- **Issue**: The rubric callback softens a failed-screen gate with “usually,” weakening the project’s own scope protocol.
  **Evidence**: The target says, “If the skill-under-test fails any screen, the right next step is usually to revise the skill's scope, not to invest in testing it” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:36. The orchestrator’s matching rule is harder: “If it fails Scope, Observability, Process, or the Failure-pattern screen, the right next step is to re-scope, not to author.” at context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:42.
  **GRADE factors**: Internal consistency gap across project protocols.
  **Ripple**: A failed `epistemic-humility` screen can be treated as a judgement call, which undermines the target’s RED evidence discipline.
  **Corrected language**: Remove “usually,” or name the exact exception and who must approve it.
  **Location**: context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:36

- **Issue**: Model-tier guidance duplicates dated model-specific claims inline instead of keeping model specifics in the model-tier note surface.
  **Evidence**: The target embeds: “Haiku 4.5 follows detailed mechanical instructions well, but operator experience (2026-04-22) is that Haiku 4.5 is unsuitable for any task requiring judgement” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:63. The model notes define “Current tier (single source of truth)” at context/plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md:11 and say “Per-model behavioural specifics are in the sections below.” at line 13.
  **GRADE factors**: Indirectness. The single-source rule is explicit inside `writing-claude-directives`; applying it to this separate skill is an inferred project-wide maintenance norm.
  **Ripple**: Model-release churn can leave this skill with stale behavioral guidance even when `model-tier-notes.md` is refreshed.
  **Corrected language**: Keep the structural rule in this file and point to `writing-claude-directives/model-tier-notes.md` for the dated Haiku judgement claim.
  **Location**: context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:63

### Low (count: 1)

- **Issue**: The target’s worked-example reference points to an example that explicitly says not to imitate its RED sourcing, so readers may over-copy the wrong artifact.
  **Evidence**: The target says, “imitate its variant-testing mechanics, not its RED sourcing” at context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:19. The example itself says, “A denubis-native worked example assembled from real campaign evidence is queued to replace this as the primary imitation target.” at context/plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md:11.
  **GRADE factors**: Low severity because the caveat is present, but the primary example remains a known caveated substitute.
  **Ripple**: Users can still cargo-cult author-invented scenarios from the example if they skim.
  **Corrected language**: Add a short inline “Do not copy the scenario sourcing; use only the comparison-table mechanics.”
  **Location**: context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:19

## Verification

Commands run and real output checked:

- `ls -R context`
  Output included `context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`, `context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`, `context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md`, and `context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md`.

- `nl -ba REVIEW-METHOD.md`
  Output included the required format at lines 235-283 and severity definitions at lines 227-233.

- `test -f context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md && nl -ba context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`
  Output showed target lines 1-460.

- `nl -ba context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`
  Output showed orchestration lines 97-105 and checklist lines 122-152.

- `nl -ba context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md`
  Output showed fallback rule lines 129-131 and testing-directives lines 265-269.

- `nl -ba context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md`
  Output showed rubric screens lines 23-88 and cross-references lines 90-98.

- `nl -ba context/plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md`
  Output showed the caveat at line 11 and test mechanics at lines 144-197.

- `git -C context status --short && git -C context diff -- context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`
  Output: `fatal: not a git repository (or any of the parent directories): .git`

- `rg -n "TaskCreate|TaskUpdate|TaskList|AskUserQuestion|cc-search-chats|Haiku 4.5|Sonnet 5|model-tier|usually|self-licensing|process-adjacent|bulletproof|maximum pressure|There is no third path|No third" context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`
  Output included matches at lines 36, 55, 63, 71, 85, 94, 96, 259, 342, 344, 349, 386, 404, and 429.

All shell commands emitted the same leading warning: `pyenv: cannot rehash: /home/brian/.pyenv/shims isn't writable`.

## Strongest Hypothesis

The strongest hypothesis is H2: the target teaches pressure-testing effectively, but its evidence-gate wording needs revision. The file has concrete RED/GREEN/REFACTOR mechanics, pressure scenarios, loophole closure, and meta-testing. The self-licensing finding is still load-bearing because line 94 weakens the RED baseline gate that lines 83 and 96 make central.

## Weakest Hypothesis

The weakest reported hypothesis is the model-tier duplication issue. It is a real maintenance risk, but the strongest “single source of truth” quote comes from `writing-claude-directives/model-tier-notes.md`, so applying it to this separate skill is an inference from project practice rather than a direct local rule.

## Pre-Mortem

If this review is wrong, the likely miss is over-weighting protocol purity against practical skill utility. The target may still perform well in actual use despite the line 94 escape because line 96 and the checklist strongly push independent evidence.

Alternative failure scenarios:
1. The biggest actual failure may be reader overload, not self-licensing; the file is 460 lines and may be too large for a “testing” skill.
2. The biggest actual failure may be operational: `cc-search-chats` fragility is documented in context/docs/issues.md:289-318, but the target does not include safe query construction.
3. The branch revisions may have improved this file substantially relative to baseline, but that delta is [unverified — needs external check: base branch or git diff].

## Fastest Next Test

Run a real fresh-session application of this target against a new discipline skill, then inspect whether the executor accepts “process-adjacent evidence” under line 94. If yes, the High finding is demonstrated. If no executor uses that escape across repeated runs, downgrade it to Medium wording-risk.

## Overall Assessment

Needs revision before presenting as fully protocol-compliant. The skill is fit enough in its main teaching arc: it explains RED/GREEN, pressure scenarios, loophole-hunting, adversarial rationalizations, and meta-testing. The branch’s effectiveness as a delta is [unverified — needs external check: base branch or git diff]. Required fixes: close the line 94 self-licensing escape, add `AskUserQuestion` fallbacks, harden the rubric-callback gate, and move or reference dated model-tier specifics.