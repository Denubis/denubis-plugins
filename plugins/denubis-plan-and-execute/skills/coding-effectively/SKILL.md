---
name: coding-effectively
description: Use when writing or reviewing code - orchestrates sub-skills for FCIS patterns, testing, database access, and Python idioms. Load this skill to get the full coding standards framework.
---

# Coding Effectively

## Required Sub-Skills

**ALWAYS load when coding:**
- `test-driven-development` - RED-GREEN-REFACTOR: write tests first, always
- `verification-before-completion` - Evidence before assertions: run and show output before claiming done
- `functional-core-imperative-shell` - Separate pure logic from I/O
- `defense-in-depth` - Validate at system boundaries
- `python-idioms` - Python 3.14+ patterns, security, tooling

**CONDITIONAL - load when applicable:**
- `writing-good-tests` - When writing or reviewing tests
- `property-based-testing` - For serialisation, validation, pure functions
- `howto-develop-with-postgres` - When working with PostgreSQL

## Property-Driven Design

When designing features, think about properties upfront. This surfaces design gaps early.

| Question | Property Type | Example |
|----------|---------------|---------|
| Does it have an inverse? | Roundtrip | `decode(encode(x)) == x` |
| Is applying it twice the same as once? | Idempotence | `f(f(x)) == f(x)` |
| What quantities are preserved? | Invariants | Length, sum, count unchanged |
| Is there a reference implementation? | Oracle | `new(x) == old(x)` |
| Can output be easily verified? | Easy to verify | `is_sorted(sort(x))` |

Surface these during design, not during debugging.

## Tool Verification

**Before using any external tool, check `.ed3d/tools.md`.** Never claim a tool is unavailable without checking.

**Protocol:**
1. Check `.ed3d/tools.md` -- if the tool is listed, use the documented invocation
2. If not listed, run `which <tool>` and `<tool> --version`
3. If found, append to `.ed3d/tools.md` with invocation, version, path, and any notes
4. If genuinely not found after both checks, then report unavailable

**`.ed3d/tools.md` format:**

```markdown
## pandoc
- Invocation: `pandoc`
- Version: 3.1.9
- Path: /usr/bin/pandoc
- Notes: supports --pdf-engine=xelatex

## ruff
- Invocation: `uv run ruff`
- Version: 0.8.2
- Notes: always via uv run, never .venv/bin/ruff
```

**Why:** Agents repeatedly claim tools are missing without checking. This caused "you have pandoc, mate." The file persists across sessions -- once discovered, a tool stays discovered.

## Core Principles

### Correctness Over Convenience

Model the full error space. No shortcuts.

- Handle edge cases: race conditions, timing issues, partial failures
- Use the type system to encode constraints
- Prefer compile-time guarantees over runtime checks
- When uncertain, investigate rather than assume

**Don't:**
- Simplify error handling to save time
- Ignore edge cases because "they probably won't happen"
- Use `Any` or `# type: ignore` to bypass checking

### Virtuous Laziness

Code is a liability, not an asset. Every line requires reading, testing, debugging, and maintaining. Optimise for the smallest system that solves the problem.

**Before adding code, complete this checklist:**

1. Can an existing function/module be extended instead of creating a new one?
2. Can existing code be *removed* to make this unnecessary?
3. Does this addition consolidate or duplicate what's already here?
4. Will a future reader understand why this exists without asking?

If the answer to #1 is yes, extend. If #2 is yes, delete. If #3 is "duplicate," stop and refactor first.

**The deletion test:** When you finish a change, check whether any existing code is now dead, redundant, or superseded by what you wrote. Remove it in the same change. New code that *could* replace old code but doesn't should be rare — if the system keeps growing without anything being removed, something is wrong.

**Don't:**
- Add a new module when an existing one covers 80% of the need
- Stack a workaround on top of a workaround (the "layercake")
- Generate a file you cannot explain the necessity of in one sentence
- Solve a problem by adding an abstraction layer instead of simplifying the layer that has the problem

### Pragmatic Incrementalism

- Prefer specific, composable logic over abstract frameworks
- Evolve design incrementally rather than perfect upfront
- Don't build for hypothetical future requirements

**The rule of three:** Don't abstract until you've seen the pattern three times. Three similar lines is better than a premature abstraction.

## File Organisation

### Descriptive Names Over Catch-Alls

Name files by what they contain, not generic categories.

**Don't create:**
- `utils.py` - Becomes a dumping ground
- `helpers.py` - Same problem
- `common.py` - What isn't common?
- `misc.py` - Actively unhelpful

**Do create:**
- `string_formatting.py` - String manipulation
- `date_arithmetic.py` - Date calculations
- `api_error_handling.py` - API error utilities

**When tempted to create utils.py:** Stop. Ask what the functions have in common. Name the file after that.

### Module Organisation

- Keep module boundaries strict
- Platform-specific code in separate files
- Test helpers in dedicated modules, not mixed with production

## Technical Debt Management

### TODO Discipline

TODOs must have context:

```python
# TODO(2026-02): Refactor when async client ships - issue #42
# TODO(brian): Revisit after ty supports this pattern
```

Naked `# TODO: fix this` is not acceptable.

### Complexity Signals

**Stop and refactor when:**
- Function exceeds ~40 lines
- File exceeds ~400 lines
- Nesting exceeds 3 levels
- You can't explain what it does in one sentence

### Quarterly Review

Schedule human review of:
- Open TODOs older than 90 days
- Files with highest churn
- Test files that frequently break

## Error Handling

### Two-Tier Model

1. **User-facing errors**: Semantic, actionable messages
2. **Internal errors**: Programming errors that may raise

### Message Format

Lowercase sentence fragments for composability:

```python
# Good: composes naturally
raise ValueError(f"failed to connect to database: {reason}")

# Bad: awkward composition
raise ValueError(f"Failed to Connect to Database: {Reason}")
```

## Documentation

### Docstring Requirements

NumPy style with intention:

```python
def calculate_tax(amount: Decimal, rate: Decimal) -> Decimal:
    """Calculate tax on an amount.

    Extracted from order processing to enable property-based testing.
    See: design-docs/tax-calculation.md, PR #42

    Parameters
    ----------
    amount : Decimal
        The base amount before tax.
    rate : Decimal
        Tax rate as a decimal (0.1 = 10%).

    Returns
    -------
    Decimal
        The calculated tax amount.

    Examples
    --------
    >>> calculate_tax(Decimal("100"), Decimal("0.1"))
    Decimal("10.00")
    """
```

**Include:**
- *Why* this exists
- Reference to design doc or PR
- Example showing usage

## Common Mistakes

| Mistake | Reality | Fix |
|---------|---------|-----|
| "Just put it in utils" | utils.py becomes 2000 lines | Name files by purpose |
| "Edge cases are rare" | Edge cases cause incidents | Handle them |
| "We might need this later" | Premature abstraction is costly | Wait for third use |
| "The type system is too strict" | Strictness catches bugs early | Fix the error |
| "I'll refactor later" | Later never comes | Do it now or don't |
| "I'll add a new module for this" | Existing module probably handles it | Extend, don't proliferate |

## Red Flags

**Stop and reconsider when you see:**

- A `utils.py` growing beyond 200 lines
- Error handling that swallows errors
- Abstractions created for single use cases
- Type assertions to bypass the checker
- Functions you can't explain simply
- TODOs without context
- New files added without any files removed or simplified
- Multiple implementations of similar functionality coexisting (the "layercake" — new solution added, old solution not removed)
- System growing monotonically across tasks without consolidation
