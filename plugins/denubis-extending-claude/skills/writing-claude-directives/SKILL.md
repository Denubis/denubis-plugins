---
name: writing-claude-directives
description: Use when writing instructions that guide Claude behavior - skills, CLAUDE.md files, agent prompts, system prompts. Covers token efficiency, compliance techniques, and discovery optimization.
user-invocable: false
---

# Writing Claude Directives

## Core Principles

**1. Claude is smart.** Only write what it doesn't already know. Challenge each line: does this justify its token cost?

**2. Positive > Negative framing.** "Don't do X" triggers thinking about X (pink elephant problem). Say what TO do, not what to avoid.

```markdown
# Bad: triggers the behavior
Don't create duplicate files

# Good: directs to correct behavior
Update existing files in place
```

**3. Context motivates compliance.** Explain WHY, not just WHAT. Claude generalizes from motivation.

```markdown
# Less effective
NEVER use ellipses

# More effective
Your response will be read aloud by a text-to-speech engine, so never use ellipses since the TTS engine cannot pronounce them.
```

**4. Placement matters.** Instructions at prompt start and end receive higher attention. Critical rules go at boundaries.

**5. ~150 instruction limit.** More instructions = uniform degradation across ALL rules. Prune ruthlessly.

**6. Repetition enforces critical rules.** For high-stakes requirements, repeat with different framings.

## Token Efficiency

**Targets:**
- Frequently-loaded directives: <200 words
- Skills/CLAUDE.md: <500 lines total
- Reference --help instead of documenting flags
- Cross-reference other skills instead of repeating

**Progressive disclosure:** Main file is overview + links. Reference files load on-demand.

## Discovery (for Skills)

The `description` field determines if Claude finds your skill.

**Format:** Start with "Use when..." + specific triggers + what it does.

**Write in third person.** Injected into system prompt.

```yaml
# Bad: vague, first person
description: I help with async testing

# Good: triggers + action, third person
description: Use when tests have race conditions or timing dependencies - replaces arbitrary timeouts with condition polling
```

**Keywords:** Include error messages, symptoms, tool names Claude might search for.

## Compliance Techniques

Current Claude models (Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5) are highly responsive to instructions, with per-model specifics in [`model-tier-notes.md`](model-tier-notes.md). Lead with context and motivation; reserve imperatives for critical boundaries.

### Primary: Context + Motivation

Explain WHY the rule exists. Claude generalizes from the explanation:

```markdown
# Instead of raw authority
You MUST run tests before committing.

# Provide motivation
Run tests before committing. Untested commits break CI for the whole team and block other developers from merging their work.
```

### Secondary: Structural Enforcement

Use structure to make compliance the path of least resistance:

| Pattern | Example |
|---------|---------|
| Workflow steps | Numbered steps with verification gates |
| Task tracking (TaskCreate/TaskUpdate) | Checklists without tracking = skipped steps |
| Forced commitment | "Announce: I'm using [skill]" |
| Explicit blocking | "If X happens, stop and do Y instead" |

### Escalation: Imperatives (Use Sparingly)

Imperatives divide into two cases, and the distinction is load-bearing. **Rhetorical emphasis** — stacking `CRITICAL` / `YOU MUST` / `NEVER` onto ordinary instructions to signal importance — should be dialled back. Current Claude models (Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5) overtrigger on these markers, reading urgency as content-signal rather than emphasis. **True boundaries** — irreversibility, safety-critical operations, unconditional prohibitions — retain the imperative; they earn it. The cost of misfire differs between the two cases: rhetorical overtrigger degrades instruction-following in nearby unrelated contexts, while a missed true-boundary gate destroys work, rewrites shared history, or leaks secrets. Rather than `CRITICAL: You MUST use this tool when X`, prefer `Use this tool when X`; but leave `Never commit secrets to version control` alone. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices> (verified 2026-06-10).

**Trigger explicitness fixes under-triggering — not stronger emphasis.** The dial-back above answers overtriggering; the opposite failure (a tool or skill that should fire and doesn't) has a different fix. On Opus 4.8 and Fable 5 the remedy for under-triggering is a plain, specific when-to-use condition in the description — `Use when X`, `Call this when the user asks about Y` — placed in the capability's own description, not just surrounding prose. This gives measurable should-call lift. Reaching for louder language instead is the trap: it does not raise the should-call rate and it overtriggers Sonnet 4.6 and the Opus 4.6 tier. Explicit trigger conditions, not emphasis, are the lever in both directions. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10).

Concrete before/after (the dial-back transformation itself is shown under Primary: Context + Motivation above):

```markdown
# Often sufficient for current models
Use this tool when searching for files.

# Reserve imperatives for true boundaries
Never commit secrets to version control.
```

Close loopholes when needed, but prefer context over authority:

```markdown
# Good: context + loophole closure
Write the test first. Code written before its test tends to test the implementation rather than the behavior, making refactoring harder later. If you find yourself with untested code, delete it and start with the test.
```

### By Skill Type

| Type | Approach |
|------|----------|
| Discipline (TDD, verification) | Context + structural enforcement + loophole closure |
| Technique (patterns, how-to) | Clear steps, "we want quality" framing |
| Reference (documentation) | Clarity only, no persuasion needed |

### Ask for Evidence, Not Reasoning-Echo

Do not instruct the model to echo, transcribe, or explain its internal reasoning as response text. On Fable 5, show-your-thinking phrasing can trigger the `reasoning_extraction` refusal category and cause fallbacks. Ask for evidence and justification *in the output* — "cite the line you changed", "state which check you ran" — rather than asking the model to reproduce the thinking that produced it. If reasoning visibility is genuinely needed, read the structured `thinking` blocks instead of prompting for a transcript. Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5> (verified 2026-06-10).

### Name a Fallback for Harness Tools

A directive that names a harness tool (`AskUserQuestion`, `EnterPlanMode`, `Agent`/`Task`, MCP tools) must state the fallback when the tool is absent — "if unavailable, ask inline". Tool rosters vary per session (operator evidence: the `claudew` alias disables specific tools), so a directive that assumes a tool is present misfires wherever it is not. Reference MCP tools by the fully qualified `Server:tool` form so the model can locate them.

## Rubric Callback

Before writing a new directive, check whether the underlying agent-task-or-skill passes the `denubis-extending-claude:epistemic-humility` rubric. The rubric screens Scope (Jones's three conditions), Observability (form-gate + tautology-screen + named-falsifier), Process (Schön's four questions), and Failure-pattern (four named patterns from AbsenceJudgement); full citations for Jones, Schön, and AbsenceJudgement are in that skill's `absencejudgement-citations.md`. If the artefact under review fails any screen, the right next step is usually to revise the scope, not to write stronger directives — directive-writing is a protective belt around a scope decision, not a substitute for it.

## Structure Patterns

### XML for Directives and Format Control

Claude parses XML effectively. Use for multi-part directives:

```xml
<task>What to accomplish</task>
<constraints>Hard requirements</constraints>
<output_format>Expected structure</output_format>
<examples>Input/output pairs</examples>
```

XML also works as format indicators:

```xml
<smoothly_flowing_prose>Write report sections here</smoothly_flowing_prose>
<structured_data>JSON or tables here</structured_data>
```

XML outperforms markdown, JSON, or YAML for rule preservation in long prompts.

### Match Prompt Style to Desired Output

The formatting style in your prompt influences Claude's response. Include markdown formatting in your prompts when you want markdown output. Remove markdown from prompts if you want plain text output.

### Workflows

Break complex tasks into checkable steps:

```markdown
## Workflow
- [ ] Step 1: Analyze inputs
- [ ] Step 2: Generate plan
- [ ] Step 3: Validate plan
- [ ] Step 4: Execute
- [ ] Step 5: Verify output
```

### Feedback Loops

Validate → fix → repeat:

```markdown
1. Generate output
2. Run validator
3. If errors: fix and go to step 2
4. Only proceed when validation passes
```

### Degrees of Freedom

Match specificity to fragility:

| Task Type | Freedom | Style |
|-----------|---------|-------|
| Fragile operations | Low | Exact scripts, no modifications |
| Preferred patterns | Medium | Templates with parameters |
| Context-dependent | High | Principles and heuristics |

## Action Bias Templates

### Proactive (Default to Action)

```xml
<default_to_action>
By default, implement changes rather than only suggesting them. If the user's intent is unclear, infer the most useful likely action and proceed, using tools to discover any missing details instead of guessing. Try to infer the user's intent about whether a tool call is intended or not, and act accordingly.
</default_to_action>
```

### Conservative (Research First)

```xml
<do_not_act_before_instructions>
Do not jump into implementation or change files unless clearly instructed. When the user's intent is ambiguous, default to providing information, doing research, and providing recommendations rather than taking action. Only proceed with edits when the user explicitly requests them.
</do_not_act_before_instructions>
```

## Overengineering Prevention

Current Opus 4.8 and Fable 5 models tend to overengineer — adding files, abstractions, or unrequested tidying, especially at higher effort (verified 2026-06-10; per-model specifics in [`model-tier-notes.md`](model-tier-notes.md) → Cross-model patterns):

```markdown
Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused.

Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up. A simple feature doesn't need extra configurability.

Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs). Don't use backwards-compatibility shims when you can just change the code.

Don't create helpers, utilities, or abstractions for one-time operations. Don't design for hypothetical future requirements. The right amount of complexity is the minimum needed for the current task. Reuse existing abstractions where possible and follow DRY.
```

## Model-Specific Notes

Per-model behavioural specifics (effort levels, steerability, instruction-following characteristics, extended-thinking budgets) live in [`model-tier-notes.md`](model-tier-notes.md) as a supporting file so they can be refreshed without touching this orchestrator. Consult that file when a directive's target model matters — e.g. choosing effort level, calibrating aggressive-language dial-back, or deciding whether to route judgement-heavy work away from Haiku 4.5.

## Naming (for Skills)

**Gerund form (verb + -ing):** `writing-skills`, `testing-code`, `debugging-errors`

**Name by action or insight:** `condition-based-waiting` not `async-helpers`

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Verbose explanations | Claude knows basics - omit |
| Multiple valid approaches | Pick one default, escape hatch for edge cases |
| Vague triggers | Specific symptoms: "tests flaky", "race condition" |
| Deeply nested references | Keep one level deep from main file |
| Windows paths | Always forward slashes |
| Aggressive language for current models | Lead with context, reserve imperatives for boundaries (see Compliance Techniques section) |

## Anti-Rationalization

For discipline-enforcing directives, anticipate excuses:

```markdown
## Red Flags - STOP
If you find yourself reasoning any of these, you're rationalizing:
- "This is simple enough to skip"
- "I already tested manually"
- "The spirit not the letter"
- "This case is different"

All mean: Follow the process.
```

## Testing Directives

1. **Baseline:** Run scenario WITHOUT directive, document failures
2. **Apply:** Add directive, verify compliance
3. **Iterate:** Find new loopholes → add counters → re-test

## Long-Running Tasks

For multi-context-window workflows and state management across sessions, see long-running-state-patterns.md in this directory.

## Graphviz (for Process Flows)

See graphviz-conventions.dot for flowchart style guide.

**Use flowcharts for:** Non-obvious decisions, process loops, "when to use A vs B"

**Don't use for:** Reference material (use tables), linear steps (use lists)
