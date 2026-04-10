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

These smells require cross-file, cross-module, or temporal analysis not feasible in single-phase assessment. Each entry documents the detection approach a future codebase-level tool would need.

#### Shotgun Surgery (Tier 3)

**Category:** Change Preventers

**What it is:** A single conceptual change requires coordinated edits across many files. The change cannot be localised because the responsibility is scattered. This makes changes expensive and error-prone — missing one file breaks the system.

**Detection approach:**
- Required data: `git log --name-only` history, change coupling analysis
- Detection heuristic: Group commits by logical change (branch or linked issue), measure file-set scope per change. Flag when change scope > threshold files consistently.
- Reference: Marinescu (2004) detection strategy: change frequency > threshold AND change coupling > threshold

**Why deferred:** Requires temporal git history analysis across multiple files — not available in single-phase static assessment.

**What a future skill would need:**
- Git log parsing with change coupling computation
- Configurable thresholds for file-set scope

#### Divergent Change (Tier 3)

**Category:** Change Preventers

**What it is:** A single file is modified for many different, unrelated reasons across commits. The file has accumulated multiple responsibilities, making it a bottleneck for unrelated changes.

**Detection approach:**
- Required data: Commit message classification, file change frequency analysis
- Detection heuristic: Classify commit reasons per file. Flag when a file's change reasons span > 3 unrelated categories with high frequency.
- Reference: Lanza & Marinescu (2006): WMC >= very high AND TCC < 1/3

**Why deferred:** Requires temporal analysis of commit patterns and commit-reason classification, not static structure.

**What a future skill would need:**
- Commit message topic classification (LLM or keyword-based)
- Per-file change frequency and reason diversity metrics

#### Parallel Inheritance (Tier 3)

**Category:** Change Preventers

**What it is:** Adding a subclass in one hierarchy forces a matching subclass in another. The two hierarchies are coupled — every extension in one requires a mirrored extension in the other.

**Detection approach:**
- Required data: Cross-hierarchy class pairing analysis across multiple files
- Detection heuristic: Identify class hierarchies with 1:1 subclass correspondence. Flag when creating a subclass in hierarchy A consistently requires a new subclass in hierarchy B.
- Reference: Fowler (1999) — often a sign of missing delegation or Strategy pattern

**Why deferred:** Requires simultaneous structural comparison of two or more inheritance trees across file boundaries.

**What a future skill would need:**
- Multi-file inheritance tree extraction
- Cross-hierarchy correspondence detection

#### Insider Trading (Tier 3)

**Category:** Couplers

**What it is:** Modules sharing too much internal knowledge across boundaries. Excessive imports of private/internal symbols, or modules that depend on each other's implementation details rather than public interfaces.

**Detection approach:**
- Required data: Import graph analysis, symbol visibility classification
- Detection heuristic: Build module dependency graph. Flag modules with bidirectional dependencies or imports of conventionally-private symbols (prefixed `_`, not in `__all__`).
- Reference: Moha et al. (2010) DECOR specification

**Why deferred:** Requires module boundary awareness and import graph analysis not available in single-file assessment.

**What a future skill would need:**
- Full-project import graph construction
- Symbol visibility classification (public vs internal)

#### Mysterious Name (Tier 3)

**Category:** Dispensables

**What it is:** Variable, function, or class names that require cross-file context to understand. A name may be clear within its own module but ambiguous or misleading when referenced from another module.

**Detection approach:**
- Required data: Cross-file reference analysis, naming convention consistency check
- Detection heuristic: For each exported symbol, measure "name informativeness" relative to usage context. Flag symbols whose name does not convey their purpose at call sites.
- Reference: No formal detection metric in literature. Fowler (1999) identifies naming as critical for revealing intent; Kerievsky (2004) on naming as the most impactful low-cost refactoring.

**Why deferred:** Name quality is contextual — a name clear in one module may be mysterious when referenced from another. Requires cross-file usage analysis.

**What a future skill would need:**
- Cross-file symbol reference tracking
- Naming informativeness heuristic (possibly LLM-based)

#### Cross-file Duplication (Tier 3)

**Category:** Dispensables

**What it is:** Similar logic repeated across different modules. Unlike within-file duplication (detectable by ast-grep), this spans file boundaries and may use slightly different variable names or structures.

**Detection approach:**
- Required data: AST similarity analysis across files (token-level or tree-level), clone detection tools
- Detection heuristic: Pairwise structural comparison of function bodies across files. Flag pairs with > 80% AST node similarity.
- Reference: Fowler's Rule of Three applies, but detection must span files

**Why deferred:** Single-file ast-grep rules cannot compare across files. Requires a clone detection pass over the full file set.

**What a future skill would need:**
- Multi-file AST comparison (e.g., jscpd, PMD CPD, or custom ast-grep orchestration)
- Configurable similarity threshold

#### God Module (Tier 3)

**Category:** Bloaters

**What it is:** A module that accumulates unrelated responsibilities over time. High fan-in (many importers depend on it) combined with low internal cohesion. Often grows organically as convenience functions get added.

**Detection approach:**
- Required data: Import dependency graph, cohesion metrics (LCOM), responsibility classification
- Detection heuristic: Compute fan-in (number of importing modules) and internal cohesion (TCC or LCOM4). Flag modules with fan-in > threshold AND TCC < 1/3.
- Reference: Marinescu God Class detection adapted to module level: ATFD > few AND WMC >= very high AND TCC < 1/3

**Why deferred:** Requires full-module semantic analysis and import graph construction beyond individual smell detection.

**What a future skill would need:**
- Module-level cohesion metrics (TCC, LCOM4)
- Import fan-in computation across the project
