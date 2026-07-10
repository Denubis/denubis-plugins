---
name: writing-skills
description: Use when creating or editing skills - applies TDD with subagent testing to find rationalisation loopholes
user-invocable: false
---

# Writing Skills

Writing skills IS Test-Driven Development applied to process documentation. This cornerstone orchestrator sequences three sub-skills: `denubis-extending-claude:epistemic-humility` (should this skill exist?), `denubis-extending-claude:writing-claude-directives` (how should it be phrased?), `denubis-extending-claude:testing-skills-with-subagents` (does it survive pressure?). Iron Law: no skill without a failing test first.

## Core Principle

**Writing skills IS Test-Driven Development applied to process documentation.**

Write test cases (pressure scenarios), watch them fail (baseline behaviour), write the skill, watch tests pass, refactor (close loopholes).

**Iron Law:** No skill without a failing test first. Same as TDD for code.

## TDD Mapping

| TDD Concept | Skill Creation |
|-------------|----------------|
| Test case | Pressure scenario with subagent |
| Production code | SKILL.md document |
| RED | Agent violates rule without skill |
| GREEN | Agent complies with skill present |
| Refactor | Close loopholes, re-test |

## When to Create a Skill

**Create when:**
- Technique wasn't intuitively obvious
- You'd reference this across projects
- Pattern applies broadly
- Others would benefit

**Don't create for:**
- One-off solutions
- Standard practices documented elsewhere
- Project-specific conventions (use CLAUDE.md)

**Before committing to creation — or to an edit that changes a skill's scope — apply the rubric:** run the artefact-under-consideration through `denubis-extending-claude:epistemic-humility`. If it fails Scope (Jones's three conditions), Observability (three screens), Process (Schön's four questions), or the Failure-pattern screen, the right next step is to re-scope, not to author. Directive-writing is a protective belt around a scope decision, not a substitute for it.

## Skill Types

**Technique:** Concrete method with steps (condition-based-waiting, root-cause-tracing).

**Pattern:** Mental model for problems (flatten-with-flags, test-invariants).

**Reference:** API docs, syntax guides, tool documentation.

**Discipline:** Enforces a rule under pressure (TDD, verification). Tested with combined-stressor pressure scenarios; success is following the rule when the agent wants to break it. This is the type that most needs `denubis-extending-claude:testing-skills-with-subagents`.

## Directory Structure

```
skills/
  skill-name/
    SKILL.md              # Main reference (required)
    supporting-file.*     # Peer reference or tool, loaded on demand
    examples/             # Optional: worked examples
      worked-example.md
```

A skill directory holds `SKILL.md` plus optional peer supporting files and an optional `examples/` subdirectory. This shape follows obra/superpowers' `writing-skills` layout, which this skill imports from (see Supporting Files).

**Separate files for:** Heavy reference (100+ lines), reusable tools/scripts, worked examples.

**Keep inline:** Principles, code patterns (<50 lines), everything else.

## SKILL.md Template

```markdown
---
name: skill-name-with-hyphens
description: Use when [triggers/symptoms] - [what it does, third person]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Symptoms and use cases. When NOT to use.

## Core Pattern
Before/after comparison or key technique.

## Quick Reference
Table or bullets for scanning.

## Common Mistakes
What goes wrong + fixes.
```

## Workflow

Authoring a skill runs the three sub-skills in TDD order — the failing test comes before the skill body. Each owns a phase; this orchestrator sequences them.

1. **Scope check** — `denubis-extending-claude:epistemic-humility`. Apply the rubric before committing to a skill. A skill that fails Scope, Observability, Process, or the Failure-pattern screen wants re-scoping, not authoring.
2. **RED baseline** — `denubis-extending-claude:testing-skills-with-subagents`. Watch the agent fail the pressure scenario *without* the skill; source the baseline from an independent session. This is where the Iron Law's "failing test first" becomes operational — it precedes authoring.
3. **Write and phrase** — `denubis-extending-claude:writing-claude-directives`. Author the skill against the documented baseline failures: token efficiency, skill discovery optimisation, aggressive-language dial-back, and the per-model behavioural specifics.
4. **GREEN / REFACTOR** — `denubis-extending-claude:testing-skills-with-subagents`. Re-run the scenarios *with* the skill present; close loopholes and re-test until no new rationalisations surface (the "When Skill is Bulletproof" signs in that skill).

**Editing an existing skill re-enters this sequence, scoped to the change.** A scope-changing edit (new triggers, new verdict space, different audience) re-runs step 1. A phrasing edit runs step 3 on the touched sections. Any edit that could weaken compliance re-runs the pressure scenarios it could plausibly weaken (steps 2 and 4). "I'm only editing, not creating" is not an exit — an edit that skips re-testing ships an untested change to a tested skill.

## Supporting Files

Three files imported from obra/superpowers ship alongside this skill. See `README.md` for dependencies and invocation.

- `anthropic-best-practices.md` (obra verbatim, pinned `6fd4507`, imported 2026-06-11) — Anthropic-authored reference on skill structure, discovery optimisation, and anti-patterns. Reference material, not denubis-authored guidance.
- `render-graphs.js` (obra verbatim, pinned `6fd4507`, imported 2026-06-11) — Node + graphviz skill-author tool for rendering process-flow diagrams from `dot` blocks in a SKILL.md. Dev-only tooling, not runtime: run it by hand when a SKILL.md you are authoring has `dot` blocks you want rendered to SVG for review.
- `./examples/CLAUDE_MD_TESTING.md` (obra adapted, source pin `6fd4507`, imported 2026-06-11) — worked example of pressure-testing CLAUDE.md documentation.

## Anti-Patterns

- **Narrative example:** "In session 2025-10-03, we found..." (too specific, not reusable)
- **Multi-language dilution:** example-js.js, example-py.py (mediocre quality, maintenance burden)
- **Code in flowcharts:** Can't copy-paste, hard to read
- **Generic labels:** helper1, step3 (labels need semantic meaning)

## Skill Creation Checklist

Use TaskCreate to track each item, and mirror decisions and completion state to a checklist file on disk so the worklog survives session interruption. If TaskCreate is unavailable, the checklist file is the tracker.

**Editing instead of creating?** Run the items your change touches. The REFACTOR re-test items are never skippable: name which pressure scenarios the edit could weaken and re-run them.

**Scope:**
- [ ] Run the artefact through `denubis-extending-claude:epistemic-humility`
- [ ] If it fails any screen, re-scope rather than author

**RED Phase:**
- [ ] Source the RED baseline from an independent session (not invented by this executor)
- [ ] Run WITHOUT skill - document baseline failures verbatim
- [ ] Identify rationalisation patterns

**GREEN Phase:**
- [ ] Name uses letters, numbers, hyphens only
- [ ] Description starts with "Use when...", third person
- [ ] Address specific baseline failures
- [ ] One excellent example (not multi-language)
- [ ] Run WITH skill - verify compliance

**REFACTOR Phase:**
- [ ] Identify new rationalisations
- [ ] Add explicit counters
- [ ] Re-test until a pressure run surfaces no new rationalisations (the "When Skill is Bulletproof" signs in `denubis-extending-claude:testing-skills-with-subagents`)

**Deployment:**
- [ ] Present GREEN/REFACTOR evidence to your human partner; explicit acceptance required
- [ ] Commit and push (only after acceptance)
- [ ] Consider contributing via PR
