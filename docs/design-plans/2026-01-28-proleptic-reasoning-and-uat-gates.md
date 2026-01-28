# Proleptic Reasoning and UAT Gates Design

## Summary

This design introduces two mechanisms to improve decision-making quality in Claude Code workflows: proleptic reasoning and human UAT gates. Proleptic reasoning operationalises a philosophical practice from argumentation theory—anticipating and articulating counterarguments before settling on a decision—by dispatching a specialised "proleptic challenger" subagent at key workflow decision points. This challenger generates 2-4 counterarguments against proposals (design options, code review conclusions, acceptance criteria) and presents them to the human alongside a "drunk tutor" framing: both the original proposal and the counterarguments may be flawed, requiring human judgement to evaluate which concerns are legitimate. The value lies not in the quality of the counterarguments but in forcing deliberate evaluation of alternatives before committing.

The second mechanism introduces explicit human User Acceptance Testing (UAT) gates into implementation workflows. After code review passes and proleptic counterarguments are presented, the workflow stops and displays the Definition of Done criteria from earlier in the process, waiting for explicit human verification that the work satisfies requirements. This prevents premature completion declarations and ensures humans validate that implementations meet their actual needs rather than just passing automated checks. The design also adds support for loading project-specific guidance files from `.claude/design-plan-guidance.md` and `.claude/implementation-plan-guidance.md` to inject domain constraints and coding standards at appropriate workflow stages.

## Definition of Done

1. **Proleptic challenger subagent exists** - A subagent that generates counterarguments to proposed approaches, triggered at decision points
2. **Human UAT gate in workflows** - After code review passes, workflow stops and presents acceptance criteria for human verification before proceeding
3. **Project guidance files in `.claude/`** - Design and implementation guidance loaded from `.claude/design-plan-guidance.md` and `.claude/implementation-plan-guidance.md`
4. **Proleptic challenges at decision points**:
   - After options are presented (before human chooses)
   - After code review completes (challenge the review's conclusions)
   - After UAT criteria are defined (challenge the acceptance criteria)
   - After substantive human input that settles direction
5. **"Drunk tutor" framing** - Both proposals AND counterarguments are presented as potentially flawed, requiring human judgement
6. **Academic citation** - Plugin references the source paper (DOI: 10.1007/s44204-025-00247-1)

## Glossary

- **Proleptic reasoning**: A practice from argumentation theory where an arguer anticipates objections to their position, articulates them charitably, and responds to them preemptively. Here, operationalised as dispatching a subagent to generate counterarguments at decision points.
- **UAT (User Acceptance Testing)**: A testing phase where the end user verifies that delivered work meets their requirements and acceptance criteria. Here, a workflow gate requiring explicit human verification before proceeding.
- **Subagent**: An isolated instance of Claude invoked via the Task tool to perform a specific, bounded task (like generating counterarguments or reviewing code) without polluting the main conversation context.
- **Task tool**: Claude Code's mechanism for spawning isolated subagent instances with dedicated prompts and context, used here to dispatch the proleptic challenger agent.
- **Workflow gate**: A point in an automated process that requires explicit approval or input before proceeding to the next step (e.g., code review, UAT verification).
- **"Drunk tutor" framing**: A metaphor from the source paper indicating that LLM outputs sound authoritative but may be incorrect, requiring human judgement rather than blind trust. Applied here to both proposals and counterarguments.
- **Definition of Done**: Explicit acceptance criteria defined early in a design or implementation process that specify what conditions must be met for work to be considered complete.
- **DOI (Digital Object Identifier)**: A persistent identifier for academic publications. The cited DOI (10.1007/s44204-025-00247-1) references Kudina, Ballsun-Stanton & Alfano (2025) on proleptic reasoning with LLMs.

## Architecture

### Core Concept: Proleptic Reasoning as Workflow Discipline

Proleptic reasoning - the anticipation, charitable articulation, and response to potential objections - is operationalised as a mandatory workflow step at decision points. The value is not in the LLM's counterarguments being correct; it's in forcing the human to evaluate them. Even wrong counterarguments stimulate better reasoning.

The "drunk tutor" framing applies: the proleptic challenger sounds authoritative but may be wrong. The human must judge both the original proposal AND the counterarguments.

### Components

**Proleptic Challenger Agent** (`plugins/denubis-plan-and-execute/agents/proleptic-challenger.md`)
- Receives: The proposal/decision being challenged, context about what triggered the challenge
- Generates: 2-4 counterarguments of varying strength
- Returns: Structured output with counterarguments and explicit reminder that both proposal and counterarguments require human judgement
- References: DOI 10.1007/s44204-025-00247-1 (Kudina, Ballsun-Stanton & Alfano, 2025)

**Proleptic Challenge Skill** (`plugins/denubis-plan-and-execute/skills/proleptic-challenge/SKILL.md`)
- Documents when to invoke the proleptic challenger
- Provides templates for presenting counterarguments to users
- Includes the "drunk tutor" framing instructions

**Human UAT Gate Skill** (`plugins/denubis-plan-and-execute/skills/human-uat-gate/SKILL.md`)
- Invoked after code review passes
- Presents Definition of Done / acceptance criteria from earlier in workflow
- Explicitly stops and waits for human verification
- Does not proceed until human confirms

**Updated Skills** (modifications to existing files):
- `executing-an-implementation-plan/SKILL.md` - Add UAT gate after code review, invoke proleptic challenger after phase completion
- `starting-a-design-plan/SKILL.md` - Invoke proleptic challenger after Definition of Done is drafted
- `requesting-code-review/SKILL.md` - Invoke proleptic challenger after review completes
- `brainstorming/SKILL.md` - Invoke proleptic challenger when options are presented

**Guidance Files** (user-created, not plugin files):
- `.claude/design-plan-guidance.md` - Project-specific design constraints, loaded before clarification
- `.claude/implementation-plan-guidance.md` - Project-specific coding standards, loaded during implementation and review

### Trigger Points for Proleptic Challenge

| Trigger | What Gets Challenged | Expected Outcome |
|---------|---------------------|------------------|
| Options presented | The options themselves | Human chooses with awareness of tradeoffs |
| Code review completes | The review's conclusions | Human judges if review is persuasive |
| UAT criteria defined | The acceptance criteria | Human confirms criteria are sufficient |
| Substantive human input | The direction being settled | Human confirms or revises based on counterarguments |

### Flow: Code Review → Proleptic Challenge → UAT Gate

```
Code review passes
    ↓
Proleptic challenger invoked
    → "Is this review persuasive? Arguments against:"
    → [Counterarguments presented]
    → "Both the review and these counterarguments may be flawed. Your judgement is required."
    ↓
Human judges counterarguments
    ↓
UAT gate invoked
    → "Definition of Done from Phase 3:"
    → [Acceptance criteria listed]
    → "Please verify these are met. I'll wait for your confirmation."
    ↓
Human confirms (or identifies gaps)
    ↓
Workflow proceeds (or loops back to fix)
```

## Existing Patterns

**Subagent dispatch pattern** - Existing skills dispatch subagents via Task tool with structured prompts. Proleptic challenger follows this pattern.

**Skill invocation pattern** - Existing skills announce usage and follow documented steps. Proleptic challenge skill follows this pattern.

**Workflow gates** - Code review already acts as a gate. UAT gate extends this pattern with explicit human verification requirement.

**Guidance file loading** - Upstream ed3d-plugins introduced `.ed3d/` guidance files. This design adapts to `.claude/` for semantic consistency with Claude Code's existing `.claude/` settings directory.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Proleptic Challenger Agent

**Goal:** Create the core agent that generates counterarguments

**Components:**
- `plugins/denubis-plan-and-execute/agents/proleptic-challenger.md` - Agent definition with model selection, description, and prompt
- Agent prompt includes DOI reference, "drunk tutor" framing, structured output format

**Dependencies:** None

**Done when:** Agent can be invoked via Task tool and returns structured counterarguments with appropriate framing
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Proleptic Challenge Skill

**Goal:** Document when and how to invoke the proleptic challenger

**Components:**
- `plugins/denubis-plan-and-execute/skills/proleptic-challenge/SKILL.md` - Skill definition with trigger points, invocation templates, presentation format

**Dependencies:** Phase 1 (agent exists)

**Done when:** Skill documents all trigger points and provides clear templates for invoking challenger
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Human UAT Gate Skill

**Goal:** Create explicit human verification gate after code review

**Components:**
- `plugins/denubis-plan-and-execute/skills/human-uat-gate/SKILL.md` - Skill that presents acceptance criteria and waits for human confirmation

**Dependencies:** None (can be developed in parallel with Phases 1-2)

**Done when:** Skill provides clear template for presenting acceptance criteria and waiting for human response
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Integrate Proleptic Challenge into Existing Skills

**Goal:** Update existing skills to invoke proleptic challenger at decision points

**Components:**
- `plugins/denubis-plan-and-execute/skills/brainstorming/SKILL.md` - Add proleptic challenge when options presented
- `plugins/denubis-plan-and-execute/skills/starting-a-design-plan/SKILL.md` - Add proleptic challenge after Definition of Done
- `plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md` - Add proleptic challenge after review completes

**Dependencies:** Phases 1, 2 (challenger and skill exist)

**Done when:** Each skill invokes proleptic challenger at appropriate decision points
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Integrate UAT Gate into Execution Workflow

**Goal:** Add mandatory human verification after code review in implementation execution

**Components:**
- `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md` - Add UAT gate after phase code review passes

**Dependencies:** Phase 3 (UAT gate skill exists)

**Done when:** Execution workflow stops after code review and waits for human UAT verification
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Guidance File Support

**Goal:** Load project-specific guidance from `.claude/` directory

**Components:**
- `plugins/denubis-plan-and-execute/skills/starting-a-design-plan/SKILL.md` - Load `.claude/design-plan-guidance.md` before clarification
- `plugins/denubis-plan-and-execute/skills/starting-an-implementation-plan/SKILL.md` - Load `.claude/implementation-plan-guidance.md` at plan start
- `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md` - Pass guidance to code reviewers
- `plugins/denubis-plan-and-execute/commands/how-to-customize.md` - Document the feature with examples

**Dependencies:** None (can be developed in parallel)

**Done when:** Guidance files are loaded at appropriate points and `/how-to-customize` command documents the feature
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Version and Documentation Updates

**Goal:** Update plugin version, marketplace, changelog, and README

**Components:**
- `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` - Version bump
- `.claude-plugin/marketplace.json` - Sync version
- `CHANGELOG.md` - Add release notes
- `plugins/denubis-plan-and-execute/README.md` - Document new features

**Dependencies:** Phases 1-6 complete

**Done when:** Version updated, changelog entry added, README documents proleptic reasoning and UAT gates
<!-- END_PHASE_7 -->

## Additional Considerations

**Proleptic challenge is not adversarial** - The goal is not to defeat proposals but to surface considerations the human should evaluate. Counterarguments should be charitable and substantive, not strawmen.

**Frequency calibration** - Proleptic challenges fire at decision points, not every turn. "Substantive human input" means direction-setting input, not routine confirmations like "yes, proceed."

**Escape hatch** - Humans can dismiss counterarguments quickly if they've already considered them. The gate doesn't require lengthy engagement, just acknowledgement.

**Academic grounding** - The DOI reference (10.1007/s44204-025-00247-1) provides theoretical foundation and signals that this is a principled approach, not arbitrary process.
