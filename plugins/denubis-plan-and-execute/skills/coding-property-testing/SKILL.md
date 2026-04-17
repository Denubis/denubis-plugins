---
name: property-based-testing
description: Use when writing tests for serialisation, validation, normalisation, or pure functions - provides property catalog, Hypothesis patterns, and strategy guidance
---

# Property-Based Testing

## Overview

Property-based testing (PBT) generates random inputs and verifies that properties hold for all of them. Instead of testing specific examples, you test invariants.

**Use Hypothesis** for Python PBT.

## When to Use PBT

| Pattern | Example | Why PBT |
|---------|---------|---------|
| Serialisation pairs | `encode`/`decode`, `to_json`/`from_json` | Roundtrip catches edge cases |
| Normalisers | `sanitize`, `canonicalize`, `format` | Idempotence ensures stability |
| Validators | `is_valid`, `validate` | Valid-after-normalize property |
| Pure functions | Business logic, calculations | Properties verify contract |
| Sorting/ordering | `sort`, `rank`, `compare` | Ordering + idempotence |

## When NOT to Use PBT

- Simple CRUD without transformation
- UI/presentation logic
- Integration tests requiring external setup
- Prototyping with fluid requirements
- When specific examples suffice

## Property Catalog

| Property | Formula | When to Use |
|----------|---------|-------------|
| **Roundtrip** | `decode(encode(x)) == x` | Serialisation, conversion |
| **Idempotence** | `f(f(x)) == f(x)` | Normalisation, formatting |
| **Invariant** | Property holds before/after | Any transformation |
| **Commutativity** | `f(a, b) == f(b, a)` | Set operations |
| **Associativity** | `f(f(a,b), c) == f(a, f(b,c))` | Combining operations |
| **Identity** | `f(x, identity) == x` | Neutral element |
| **Inverse** | `f(g(x)) == x` | encrypt/decrypt |
| **Oracle** | `new_impl(x) == reference(x)` | Refactoring |
| **Easy to verify** | `is_sorted(sort(x))` | Complex algorithms |

**Strength hierarchy** (aim for strongest):
```
No Exception → Type Preservation → Invariant → Idempotence → Roundtrip
```

## Hypothesis Basics

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_roundtrip_encoding(text: str):
    """Encoding then decoding returns original."""
    encoded = encode(text)
    decoded = decode(encoded)
    assert decoded == text

@given(st.lists(st.integers()))
def test_sort_is_idempotent(items: list[int]):
    """Sorting twice equals sorting once."""
    once = sorted(items)
    twice = sorted(once)
    assert once == twice

@given(st.text())
def test_normalize_is_idempotent(text: str):
    """Normalizing twice equals normalizing once."""
    once = normalize(text)
    twice = normalize(once)
    assert once == twice
```

## Strategy Best Practices

### Constrain Early

Build constraints INTO the strategy, not via `assume()`:

```python
# GOOD: constraints in strategy
@given(st.integers(min_value=1, max_value=100))
def test_with_positive_int(n: int):
    ...

# BAD: high rejection rate
@given(st.integers())
def test_with_positive_int(n: int):
    assume(1 <= n <= 100)  # Most inputs rejected
    ...
```

### Size Limits

Prevent slow tests:

```python
@given(st.lists(st.integers(), max_size=100))
def test_list_processing(items: list[int]):
    ...

@given(st.text(max_size=1000))
def test_text_processing(text: str):
    ...
```

### Realistic Data

Match real-world constraints:

```python
# Realistic ages, not arbitrary ints
@given(st.integers(min_value=0, max_value=150))
def test_age_validation(age: int):
    ...

# Valid email-like strings
email_strategy = st.emails()

# Custom strategy for domain types
@st.composite
def user_strategy(draw):
    return User(
        name=draw(st.text(min_size=1, max_size=100)),
        age=draw(st.integers(min_value=0, max_value=150)),
        email=draw(st.emails()),
    )
```

### Reuse Strategies

```python
valid_amount = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000"),
    places=2,
)

@given(valid_amount)
def test_tax_calculation(amount: Decimal):
    ...

@given(valid_amount, valid_amount)
def test_addition(a: Decimal, b: Decimal):
    ...
```

## Explicit Examples

Always include edge cases:

```python
from hypothesis import given, example, strategies as st

@given(st.lists(st.integers()))
@example([])           # Empty list
@example([1])          # Single element
@example([1, 1, 1])    # All same
def test_sort_properties(items: list[int]):
    result = sorted(items)
    assert len(result) == len(items)
    assert all(result[i] <= result[i+1] for i in range(len(result)-1))
```

## Settings

```python
from hypothesis import given, settings, strategies as st

# Development: fast feedback
@settings(max_examples=10)
@given(st.text())
def test_quick(text: str):
    ...

# CI: thorough
@settings(max_examples=200)
@given(st.text())
def test_thorough(text: str):
    ...

# Nightly: exhaustive
@settings(max_examples=1000, deadline=None)
@given(st.text())
def test_exhaustive(text: str):
    ...
```

## Quality Checklist

Before committing PBT tests:

- [ ] **Not tautological:** Assertion doesn't compare same expression
- [ ] **Strong property:** Not just "no crash"
- [ ] **Not vacuous:** `assume()` doesn't filter most inputs
- [ ] **Edge cases explicit:** `@example` for empty, single, boundary
- [ ] **No reimplementation:** Don't restate function logic in assertion
- [ ] **Realistic constraints:** Strategy matches real-world input

## Red Flags

| Red Flag | Problem | Fix |
|----------|---------|-----|
| `assert f(x) == f(x)` | Tautological | Find real property |
| Only "no exception" | Too weak | Find stronger property |
| Many `assume()` calls | Vacuous | Redesign strategy |
| `assert add(a,b) == a+b` | Reimplementation | Use algebraic property |
| No `@example` decorators | Missing edge cases | Add explicit examples |

## Common Patterns

### Roundtrip

```python
@given(st.binary())
def test_compression_roundtrip(data: bytes):
    compressed = compress(data)
    decompressed = decompress(compressed)
    assert decompressed == data
```

### Idempotence

```python
@given(st.text())
def test_whitespace_normalization(text: str):
    once = normalize_whitespace(text)
    twice = normalize_whitespace(once)
    assert once == twice
```

### Invariants

```python
@given(st.lists(st.integers()))
def test_sort_preserves_length(items: list[int]):
    result = sorted(items)
    assert len(result) == len(items)

@given(st.lists(st.integers()))
def test_sort_preserves_elements(items: list[int]):
    result = sorted(items)
    assert sorted(result) == sorted(items)  # Same multiset
```

### Oracle (Reference Implementation)

```python
@given(st.lists(st.integers()))
def test_optimized_matches_reference(items: list[int]):
    reference = slow_but_correct_sort(items)
    optimized = fast_sort(items)
    assert optimized == reference
```

## Integration with pytest

Hypothesis works with pytest fixtures:

```python
@pytest.fixture
def db_session():
    ...

@given(st.text(min_size=1))
def test_user_creation(db_session, name: str):
    user = create_user(db_session, name=name)
    assert user.name == name
```

## Summary

1. **Find properties** - roundtrip, idempotence, invariants
2. **Constrain strategies** - realistic, bounded, no `assume()`
3. **Add explicit examples** - edge cases with `@example`
4. **Avoid tautologies** - test real behaviour
