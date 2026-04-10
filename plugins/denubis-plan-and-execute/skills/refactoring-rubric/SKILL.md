---
name: refactoring-rubric
description: Use when assessing code for refactoring opportunities — provides Mantyla smell taxonomy, Fowler refactoring patterns, evidence grading criteria, and structural detection rules. Loaded by smell-assessor agent as its evaluation rubric.
user-invocable: false
---

# Refactoring Rubric

Grounding reference for code smell detection and refactoring decisions. Combines Mantyla's smell taxonomy, Fowler's refactoring catalogue, evidence grading, and structural detection rules.

## Part 1: Mantyla Taxonomy Checklist

### Bloaters

| Smell | Tier | Detection Signal | Refactoring |
|-------|------|-----------------|-------------|
| Long Method | T1 | complexipy >15 or wc -l >40 | Extract Method, Replace Temp with Query |
| Long Parameter List | T1 | >=4 parameters | Introduce Parameter Object, Preserve Whole Object |
| Large Class | T1 | wc -l >400 | Extract Class, Extract Superclass |
| Primitive Obsession | T2 | LLM-assessed: raw types where value objects fit | Replace Primitive with Object, Introduce Parameter Object |
| Data Clumps | T2 | LLM-assessed: same group of fields/params repeated | Extract Class, Introduce Parameter Object |

### Object-Orientation Abusers

| Smell | Tier | Detection Signal | Refactoring |
|-------|------|-----------------|-------------|
| Switch Statements | T2 | LLM-assessed: repeated type-checking conditionals | Replace Conditional with Polymorphism, Introduce Special Case |
| Refused Bequest | T2 | LLM-assessed: subclass ignores inherited behaviour | Push Down Method, Replace Inheritance with Delegation |
| Alternative Classes with Different Interfaces | T2 | LLM-assessed: classes doing same thing with different APIs | Rename Method, Extract Superclass |
| Temporary Field | T2 | LLM-assessed: fields only set in some paths | Extract Class, Introduce Special Case |

### Change Preventers

| Smell | Tier | Detection Signal | Refactoring |
|-------|------|-----------------|-------------|
| Divergent Change | T3 | Cross-file analysis required | Extract Class |
| Shotgun Surgery | T3 | Cross-file analysis required | Move Function, Inline Class |
| Parallel Inheritance | T3 | Cross-file analysis required | Move Function, Collapse Hierarchy |

### Dispensables

| Smell | Tier | Detection Signal | Refactoring |
|-------|------|-----------------|-------------|
| Duplicate Code | T2 | Rule of Three gate (see Part 4) | Extract Method, Pull Up Method, Form Template Method |
| Lazy Class | T2 | LLM-assessed: class does too little to justify existence | Inline Class, Collapse Hierarchy |
| Data Class | T2 | LLM-assessed: class with only fields and getters/setters | Move Function (into the class), Encapsulate Record |
| Dead Code | T2 | LLM-assessed: unreachable or unused code | Remove Dead Code |
| Speculative Generality | T2 | LLM-assessed: abstractions with single implementation; check against design plan | Inline Class, Collapse Hierarchy, Remove Dead Code |

### Couplers

| Smell | Tier | Detection Signal | Refactoring |
|-------|------|-----------------|-------------|
| Feature Envy | T2 | LLM-assessed: method uses another class's data more than its own | Move Function, Extract Method + Move Function |
| Inappropriate Intimacy | T2 | LLM-assessed: classes access each other's internals | Move Function, Extract Class, Hide Delegate |
| Message Chains | T2 | LLM-assessed: a.b().c().d() chains | Hide Delegate, Extract Method |
| Middle Man | T2 | LLM-assessed: class delegates almost everything | Remove Middle Man, Inline Function |
| Insider Trading | T3 | Cross-module analysis required | Move Function, Hide Delegate |

### Additional Structural Smells

These are not in Mantyla's original taxonomy but are detectable at Tier 1 with structural rules.

| Smell | Tier | Detection Signal | Refactoring |
|-------|------|-----------------|-------------|
| Deep Nesting | T1 | >3 levels nested control flow (ast-grep rule) | Replace Nested Conditional with Guard Clauses, Decompose Conditional, Extract Method |
| FCIS Violation | T1 | I/O calls in functions that should be pure (ast-grep rule) | Extract Method (separate I/O from logic), Move Function |
| Global Mutable State | T1 | Module-level non-constant assignments (ast-grep rule) | Encapsulate Variable, Replace Global with Module-Level Function |

## Part 2: Fowler Smell-to-Refactoring Mapping

Primary lookup table for smell-to-refactoring decisions.

| Smell | Primary Refactoring | Secondary |
|-------|-------------------|-----------|
| Long Method | Extract Method | Replace Temp with Query, Decompose Conditional |
| Long Parameter List | Introduce Parameter Object | Replace Parameter with Query, Preserve Whole Object |
| Large Class | Extract Class | Extract Superclass |
| Deep Nesting | Replace Nested Conditional with Guard Clauses | Decompose Conditional, Extract Method |
| FCIS Violation | Extract Method (separate I/O from logic) | Move Function |
| Global Mutable State | Encapsulate Variable | Replace Global with Module-Level Function |
| Duplicate Code | Extract Method | Pull Up Method, Form Template Method |
| Feature Envy | Move Function | Extract Method + Move Function |
| Data Class | Move Function (into the class) | Encapsulate Record |
| Speculative Generality | Inline Class | Collapse Hierarchy, Remove Dead Code |
| Dead Code | Remove Dead Code | -- |
| Switch Statements | Replace Conditional with Polymorphism | Introduce Special Case |
| Message Chains | Hide Delegate | Extract Method |
| Middle Man | Remove Middle Man | Inline Function |

## Part 3: Evidence Grading Criteria

Three-level scale for each finding.

| Grade | Definition | Action |
|-------|-----------|--------|
| **Demonstrated** | Metric exceeds threshold OR structural rule fires with exact match. Evidence is reproducible by running the same tool. | Proceed to refactoring. |
| **Plausible** | Code exhibits the pattern but metric is borderline or detection is LLM-assessed. A competent reviewer would likely agree. | Proceed, but note the grade in report. Critical review may downgrade. |
| **Possible** | Assessor suspects the smell but evidence is indirect or contextual. Reasonable people could disagree. | Report but flag for review. Critical review will likely reject unless corroborated. |

### Grading Rules

- Tier 1 findings with tool output are always **Demonstrated**.
- Tier 2 findings start at **Plausible**; upgrade to Demonstrated only if multiple independent signals converge.
- Never report a finding below **Possible** -- if evidence is weaker than "reasonable people could disagree," it is not a finding.

## Part 4: Rule of Three Gate

Before reporting a Duplicate Code finding, verify all three conditions:

1. The duplicated pattern appears **at least three times**.
2. The instances are not trivially different (e.g., different variable names in boilerplate).
3. Extracting the duplication would produce a **meaningful abstraction**, not just a wrapper.

If fewer than three instances, do not report. Log it in the "Below Threshold" section of the report.

## Part 5: Two Hats Discipline

When refactoring (applying patterns from this rubric):

- **Hat: Refactoring** -- Change structure, preserve behaviour. Tests must stay green after every transformation. If a test breaks, revert immediately. Do not fix the test -- that is changing behaviour.
- **Hat: Adding features** -- Not worn during refactoring. No new functionality, no new tests for new behaviour, no "while I'm here" improvements.

Switching hats requires an explicit decision and a clean commit boundary.

## Part 6: Tier 3 Deferred Smells Registry

These smells require cross-file or cross-module analysis not feasible in single-phase assessment. Full documentation added in Phase 6.

### Shotgun Surgery
One-line: A single logical change requires edits across many files.
Detection requires: Cross-file change frequency analysis (git history or dependency graph).
Deferred because: Requires multi-file context window exceeding single-phase scope.

### Divergent Change
One-line: A single file is changed for many different, unrelated reasons.
Detection requires: Change-reason classification across git history for each file.
Deferred because: Requires temporal analysis of commit patterns, not static structure.

### Parallel Inheritance
One-line: Adding a subclass in one hierarchy forces a matching subclass in another.
Detection requires: Cross-hierarchy class pairing analysis across multiple files.
Deferred because: Requires simultaneous structural comparison of two or more inheritance trees, not feasible in single-file scope.

### Insider Trading
One-line: Modules sharing too much internal knowledge across boundaries.
Detection requires: Cross-module dependency analysis and boundary definition.
Deferred because: Requires module boundary awareness not available in single-file assessment.

### Mysterious Name
One-line: Unclear naming requiring cross-file context to understand.
Detection requires: Cross-file usage analysis to determine if naming is locally or globally ambiguous.
Deferred because: Name clarity depends on broader project conventions and usage context.

### Cross-file Duplication
One-line: Similar logic repeated across different modules.
Detection requires: Cross-file structural comparison with semantic equivalence checking.
Deferred because: Single-file ast-grep rules cannot compare across files.

### God Module
One-line: A module that accumulates unrelated responsibilities over time.
Detection requires: Cohesion analysis across all functions/classes in a module.
Deferred because: Requires full-module semantic analysis beyond individual smell detection.
