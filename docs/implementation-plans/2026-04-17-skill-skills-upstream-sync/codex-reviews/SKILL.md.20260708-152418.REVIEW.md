# Critical Peer Review: SKILL.md

Reviewer: Codex (GPT-5)
Date: 2026-07-08
Document reviewed: context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md

## Hidden Assumptions

1. **The orchestrator’s phase order preserves the Iron Law.** Evidence status: contradicted. The target says: “Iron Law: no skill without a failing test first” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:9), but then sequences testing after phrasing: “1. **Scope check**”, “2. **Phrasing and compliance**”, “3. **RED/GREEN/REFACTOR**” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:101-103).

2. **Vendored support files are integrated enough to justify shipping in this skill directory.** Evidence status: partially supported for `anthropic-best-practices.md`, weak for `render-graphs.js`. The target says all three files “ship alongside this skill” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:109), but the workflow never tells the reader when to consult `anthropic-best-practices.md` or run `render-graphs.js`.

3. **Cross-referencing sub-skills is sufficient orchestration.** Evidence status: weakened. The target says: “this orchestrator only points” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:99). That does not supply enough sequencing glue where the sub-skills conflict with the target’s own phase order.

## ACH Matrix

| Hypothesis | E1: Iron Law stated | E2: workflow puts RED/GREEN/REFACTOR at step 3 | E3: testing sub-skill says RED before writing | E4: vendored best practices say evaluations before extensive docs | E5: README labels vendored files as reference/dev-only | E6: project audit says Iron Law held in 1 of 4 sessions |
|---|---:|---:|---:|---:|---:|---:|
| H1: Target is an effective cornerstone orchestrator as written | + | − | − | − | ? | − |
| H2: Target has the right components but wrong gate ordering | + | + | + | + | ? | + |
| H3: Main problem is vendored dead weight, not orchestration | ? | ? | ? | ? | + | ? |

Decision rule: H2 survives with the fewest contradictions. The strongest contradiction against H1 is that the target operationalizes the failing-test-first rule only at step 3 while the testing sub-skill requires watching failure before writing the skill.

## Findings

### High (count: 1)

- **Issue**: The workflow violates its own Iron Law by placing directive phrasing before RED baseline testing.
  **Evidence**: The target states: “**Iron Law:** No skill without a failing test first. Same as TDD for code.” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:17). But the actual workflow says: “1. **Scope check**”, “2. **Phrasing and compliance**”, then “3. **RED/GREEN/REFACTOR**” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:101-103). The testing sub-skill requires the opposite order: “You MUST see what agents naturally do before writing the skill.” (context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:79), and “Write skill addressing the specific baseline failures you documented.” (context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:114). The vendored Anthropic reference aligns with RED-before-docs: “Create evaluations BEFORE writing extensive documentation.” (context/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md:740).
  **GRADE factors**: High. Internal inconsistency and production-path overclaim: the target claims failing-test-first discipline but its own ordered workflow delays the failing test until after phrasing work. Reporting bias also applies because the target repeats the Iron Law without confronting this sequencing exception.
  **Ripple**: Affects the opening claim (line 9), Core Principle (lines 15-17), Workflow (lines 97-105), and Checklist (lines 132-147). It also matches the project audit’s observed failure: “the Iron Law held in 1 of 4 authoring sessions” (context/docs/audits/2026-07-02-skill-engagement-audit.md:231).
  **Corrected language**: Make the sequence: scope viability screen → RED baseline sourcing and failing run → write minimal skill body against observed failures → directive phrasing pass → GREEN/REFACTOR pressure testing → UAT/acceptance. Do not say phrasing happens before RED.
  **Location**: context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:97-105

### Medium (count: 2)

- **Issue**: The checklist omits load-bearing evaluation requirements from the vendored best-practices file it ships as an authoring reference.
  **Evidence**: The target says `anthropic-best-practices.md` is “Anthropic-authored reference on skill structure, discovery optimisation, and anti-patterns” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:111). That reference requires: “At least three evaluations created”, “Tested with Haiku, Sonnet, and Opus”, and “Tested with real usage scenarios” (context/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md:1146-1148). The target checklist only says “Run WITHOUT skill”, “Run WITH skill”, and “Re-test until a pressure run surfaces no new rationalisations” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:134,142,147). It does not preserve the count, model matrix, or real-usage requirement.
  **GRADE factors**: Moderate. Indirectness and incompleteness: the target imports the reference but weakens its operational checklist.
  **Ripple**: Affects Supporting Files (line 111) and Skill Creation Checklist (lines 132-147). It also weakens the target’s claim to follow project skill-authoring standards.
  **Corrected language**: Add checklist items for at least three evaluations, real usage scenarios, and the intended model-tier matrix or an explicit denubis-specific replacement for the Anthropic Haiku/Sonnet/Opus matrix.
  **Location**: context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:132-147

- **Issue**: `render-graphs.js` is described as shipped tooling but remains unintegrated with the skill’s workflow.
  **Evidence**: The target says: “`render-graphs.js` ... Node + graphviz skill-author tool for rendering process-flow diagrams from `dot` blocks in a SKILL.md. Dev-only tooling, not runtime.” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:112). The README says it “Extracts all ` ```dot ` code blocks from the target `SKILL.md` and renders them to SVG files alongside” (context/plugins/denubis-extending-claude/skills/writing-skills/README.md:19), and “Claude Code does not invoke it” (context/plugins/denubis-extending-claude/skills/writing-skills/README.md:21). The target workflow and checklist do not mention diagrams, `dot` blocks, or any condition under which this tool should be run (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:97-152).
  **GRADE factors**: Moderate. Non-diagnostic support-file citation: the file exists and is documented, but the target does not integrate it into an authoring decision or verification step.
  **Ripple**: Affects Supporting Files (lines 109-113) and the review focus question about whether vendored files cohere with the skill. `anthropic-best-practices.md` is at least conceptually relevant; `render-graphs.js` is dead weight unless the skill adds a graph-authoring branch or moves the tool to the directive/graphviz skill where graph guidance actually lives.
  **Corrected language**: Either remove `render-graphs.js` from this skill, or add a narrow branch: use only when a skill contains `dot` blocks and a human wants rendered process-flow diagrams; otherwise ignore it.
  **Location**: context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:112

### Low (count: 1)

- **Issue**: “This orchestrator only points” is too weak for a cornerstone orchestrator.
  **Evidence**: The target says: “Authoring a skill sequences the three sub-skills in order. Each owns a phase of the work; this orchestrator only points.” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:99). But the same file calls itself “This cornerstone orchestrator” (context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:9). A cornerstone orchestrator must resolve phase boundaries, not merely list component skills.
  **GRADE factors**: Low. Language and role clarity.
  **Ripple**: This wording makes the High finding easier to miss because it frames sequencing as pass-through rather than load-bearing design.
  **Corrected language**: Replace with: “This orchestrator owns phase order and handoffs; sub-skills own their internal checks.”
  **Location**: context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:99

## Verification

Commands actually run and relevant real output:

```text
ls -R context
```

Output began with:

```text
context:
CHANGELOG.md
CLAUDE.md
README.md
docs
plugins
pyproject.toml
scripts
tests
uv.lock
```

```text
wc -l REVIEW-METHOD.md context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md context/plugins/denubis-extending-claude/skills/writing-skills/README.md context/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md context/plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js context/plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md
```

Output:

```text
   320 REVIEW-METHOD.md
   152 context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md
    29 context/plugins/denubis-extending-claude/skills/writing-skills/README.md
  1184 context/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md
   168 context/plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js
   198 context/plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md
   108 context/plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md
   281 context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md
   460 context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md
  2900 total
```

```text
nl -ba context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md | sed -n '1,220p'
```

Verified target lines 1-152.

```text
nl -ba context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md | sed -n '1,520p'
```

Verified RED-before-writing requirements at lines 75-119 and checklist at lines 381-405.

```text
nl -ba context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md | sed -n '1,340p'
```

Verified directive-writing rubric callback and task-tracking guidance.

```text
nl -ba context/plugins/denubis-extending-claude/skills/writing-skills/README.md | sed -n '1,120p'
```

Verified support-file descriptions.

```text
nl -ba context/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md | sed -n '730,775p'
```

Verified evaluation-first guidance at lines 738-748.

```text
nl -ba context/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md | sed -n '1,120p;1120,1205p'
```

Verified frontmatter/preface and checklist lines 1146-1148.

```text
nl -ba context/docs/audits/2026-07-02-skill-engagement-audit.md | sed -n '220,270p'
```

Verified observed writing-skills audit claim at lines 230-231.

```text
rg -n '```dot|render-graphs|graphviz-conventions|\.dot' context/plugins/denubis-extending-claude/skills/writing-skills context/plugins/denubis-extending-claude/skills/writing-claude-directives context/plugins/denubis-extending-claude/skills/testing-skills-with-subagents context/plugins/denubis-extending-claude/skills/epistemic-humility
```

Output included only references to the graph tool/style guide, not actual `dot` code blocks in the checked skill bodies:

```text
context/plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:277:See graphviz-conventions.dot for flowchart style guide.
context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:112:- `render-graphs.js` ...
context/plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js:22:  const regex = /```dot\n([\s\S]*?)```/g;
```

One attempted `rg` command with unescaped backticks failed as:

```text
/usr/bin/bash: -c: line 1: unexpected EOF while looking for matching ``'
```

## Strongest Hypothesis

The strongest hypothesis is H2: the skill has the right sub-skills but the orchestration order is wrong. The decisive evidence is the direct contradiction between the target’s ordered workflow and the testing sub-skill’s “before writing the skill” requirement.

## Weakest Hypothesis

The weakest hypothesis is H3: vendored dead weight is the main defect. `render-graphs.js` is weakly integrated, but `anthropic-best-practices.md` and the example file are explicitly caveated and relevant. The ordering failure is more load-bearing.

## Pre-Mortem

If this review is wrong and the skill is fit as written, the next failure would likely show that agents interpret “Phrasing and compliance” as only a pre-writing planning pass, not as authoring. The target does not say that.

Alternative failure scenarios consistent with the evidence:

1. Agents keep skipping RED because the checklist permits them to treat testing as a late verification phase.
2. Agents over-consult vendored Anthropic guidance and bypass denubis-specific RED sourcing rules.
3. Agents ignore `render-graphs.js` entirely, leaving it harmless but still unnecessary context and maintenance surface.

## Fastest Next Test

Run one fresh skill-authoring session using this target exactly as written and require transcript evidence for phase order. Prediction if the High finding is true: the agent will do scope/phrasing before sourcing a failing RED baseline, or will treat RED as a late pressure-test step. Prediction if false: the agent will source and run a failing baseline before drafting substantive skill prose.

## Overall Assessment

Needs revision. The target is close in components, but not fit as the cornerstone orchestrator until it makes RED baseline sourcing happen before directive phrasing and skill-body authorship, and until the supporting files are either integrated into the workflow or explicitly demoted/removed.