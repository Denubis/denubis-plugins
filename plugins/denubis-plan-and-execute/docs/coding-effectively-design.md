# coding-effectively Skill Design

Design decisions for the `coding-effectively` skill and its sub-skills.

## Background

The upstream `denubis-house-style` plugin contains a `coding-effectively` skill that our `code-reviewer` agent references. We removed that plugin (TypeScript/React focused) but need to fulfill the contract with Python-focused alternatives.

## Skill Structure

Main orchestrator skill references sub-skills:

```
skills/
  coding-effectively/SKILL.md        # Orchestrator, general principles
  coding-fcis/  # FCIS pattern
  defense-in-depth/                  # Validation at boundaries
  coding-good-tests/                # pytest patterns, mock strategy
  coding-property-testing/            # Hypothesis patterns
  howto-develop-with-postgres/       # SQL/transaction patterns
  coding-python-idioms/                     # Python 3.14+, t-strings, ty, security
```

## Key Decisions

### Python Version

- **Assume Python 3.14+** as baseline
- Document fallback patterns for older versions where relevant
- Use `f"{foo=}"` pattern for debug output (shows variable name and value)

### Type Checking (ty)

- Use `ty` with very strict settings
- Escape hatch: `# type: ignore[specific-error]` with:
  - Explanation comment
  - TODO commitment to revisit
  - Flag on `uv sync --upgrade` to check if still needed

### Transactions and SQL

- TX_ prefix for methods that START transactions
- Context managers (`with db.transaction():`) for scope visibility
- Transactions must be atomic - properly, not half-arsed
- Database is source of truth - treat it with respect
- ACID compliance is non-negotiable

### Documentation Lookup

Cascade for checking assumptions:
1. Context7 cached docs
2. WebSearch for current docs
3. Improve local cache with findings
4. Ask user if still unclear

### Logging

- Framework-agnostic principles (Logfire as preferred implementation)
- Never `print()` for anything that matters
- Always traceable to source (file:line or structured logger name)
- Web errors must appear in logs, not just browser console
- Structured logging preferred (JSON/key-value)

### Configuration

- **pydantic-settings** for typed, validated configuration
- Reads from `.env` but validates and types on startup
- Typos caught at startup, not runtime
- Defaults documented in code

### CLI

- **typer** preferred over click
- Type hints become validation
- Docstrings become help text
- Less boilerplate

### Docstrings

- **NumPy style** (Parameters/Returns with dashes)
- Include *why* this exists and its intention
- Reference development discussions (PR #, design doc)
- Examples are illustrative, pytest is the test suite
- Not using doctest as testing strategy

### Technical Debt

- Fold into coding-effectively as a section
- TODOs must have date or issue reference
- Lint rule for function length (~40 lines)
- Quarterly debt review (human process)

### Security

Inline critical prevention in coding-python-idioms:
- T-strings for SQL/HTML/shell (injection prevention)
- Never use dynamic code evaluation on untrusted input
- Never deserialize untrusted binary data (use JSON instead)
- Secrets in environment/config, never in code
- Validate at boundaries (API input, file input)

Reference Trail of Bits skills for deeper security audits.

## Testing Configuration

Standard pytest invocation:
```bash
uv run pytest --depper --depper-run-all-on-error -n auto --dist=loadfile -x --ff --durations=10 --tb=short
```

Plugins: xdist, asyncio, depper (dependency tracking)

## Research Sources

Patterns drawn from:
- Simon Willison's pytest writings (parametrize, fixtures, agent patterns)
- PyDev Tools Handbook (uv, ruff, ty, modern tooling)
- obra/superpowers (original upstream)
- Trail of Bits skills (security patterns)
- PEP 8 and Google Python Style Guide
- Hitchhiker's Guide to Python

## Sub-skill Content Notes

### coding-fcis

- Upstream already has Python examples
- Keep language-agnostic core
- Python notes: context managers are fine in shell, generators acceptable

### defense-in-depth

- Scope to system boundaries, not every function
- Four layers: Entry, Business, Environment, Debug
- EAFP is fine within validated boundaries

### coding-good-tests

- pytest with parametrize, fixtures
- `uv run pytest` not `python -m pytest`
- Mock strategy: don't mock what you don't own
- Condition-based waiting, not arbitrary sleeps

### coding-property-testing

- Hypothesis patterns
- Roundtrip, idempotence, invariants
- Conditional use - not for everything

### howto-develop-with-postgres

- TX_ prefix convention adopted
- Context managers for transaction scope
- ULID for user-visible PKs
- `numeric` for money, never float
- Type JSONB columns
- Proactive indexing

### coding-python-idioms

- T-strings for security-sensitive interpolation
- Deferred annotations (PEP 649)
- `X | None` not `Optional[X]`
- Never mutable default arguments
- `with` for all resources
- Avoid power features (metaclasses, import hooks)
- Security: no dynamic code evaluation, safe serialization only, secrets management, boundary validation
