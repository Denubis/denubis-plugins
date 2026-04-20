---
name: coding-fcis
family: coding-effectively
description: Use when writing or refactoring code - enforces separation of pure business logic (Functional Core) from side effects (Imperative Shell) for testability and clarity
---

# Functional Core, Imperative Shell (FCIS)

## Overview

**Core principle:** Separate pure business logic (Functional Core) from side effects (Imperative Shell). Pure functions are trivial to test. I/O is isolated to thin shells.

## When to Use

**Use FCIS when:**
- Writing any new code
- Refactoring existing code
- Deciding where logic belongs
- Tests require complex mocking (signal to refactor)

**Question to ask:** "Can I test this business logic without mocking the database?"

## The Pattern

```
1. GATHER (Shell):  Collect data from external sources
2. PROCESS (Core):  Transform input to output (pure)
3. PERSIST (Shell): Save results externally
```

## File Classification

**Add pattern comment to application code files:**

```python
# pattern: Functional Core
# pattern: Imperative Shell
# pattern: Mixed (needs refactoring)
```

**Exceptions (no classification needed):**
- Configuration files
- Scripts and task runners
- Data files
- Documentation

## Functional Core Files

**Contains ONLY:**
- Pure functions (same input → same output, always)
- Business logic, validations, calculations
- Data transformations
- Logging (exception: loggers are permitted)

**NEVER contains:**
- File I/O
- Database operations
- HTTP requests
- Environment variable access
- `datetime.now()`, `random()`, or other non-deterministic calls

**Test signature:** Simple assertions, no mocks except logger.

### Example

```python
# pattern: Functional Core

from decimal import Decimal
import structlog

def calculate_order_total(
    items: list[OrderItem],
    tax_rate: Decimal,
    logger: structlog.BoundLogger | None = None,
) -> OrderTotal:
    """Calculate order total with tax.

    Pure function - same inputs always produce same outputs.
    """
    if logger:
        logger.debug("calculating_total", item_count=len(items))

    subtotal = sum(item.price * item.quantity for item in items)
    tax = subtotal * tax_rate

    return OrderTotal(
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
    )
```

## Imperative Shell Files

**Contains ONLY:**
- I/O operations: files, database, HTTP, environment
- Orchestration: gather → call Core → persist
- Error handling for I/O failures
- Minimal logic (coordination only)

**NEVER contains:**
- Complex calculations
- Business rule validations
- Data transformations beyond format conversion

**Test signature:** Integration tests with real dependencies or mocks.

### Example

```python
# pattern: Imperative Shell

import structlog
from .core import calculate_order_total
from .repository import OrderRepository

logger = structlog.get_logger(__name__)

async def process_order(order_id: str, repo: OrderRepository) -> OrderTotal:
    """Process an order: gather, calculate, persist."""

    # GATHER
    items = await repo.get_order_items(order_id)
    tax_rate = await repo.get_tax_rate(order_id)

    # PROCESS (call Functional Core)
    result = calculate_order_total(items, tax_rate, logger)

    # PERSIST
    await repo.update_order_total(order_id, result.total)

    return result
```

## Decision Flow

Before writing a function, ask:

1. **Can it run without external dependencies?**
   - YES → Functional Core
   - NO → Continue...

2. **Does it coordinate I/O?**
   - YES → Imperative Shell
   - NO → **STOP. Refactor.** Business logic + I/O mixed.

## Python-Specific Notes

### Context Managers Are Fine in Shell

```python
# pattern: Imperative Shell

async def export_report(report_id: str) -> Path:
    """Export report to file."""
    # Context manager in shell is fine
    async with aiofiles.open(output_path, 'w') as f:
        data = await generate_report_data(report_id)  # Shell: I/O
        content = format_report(data)  # Core: pure transformation
        await f.write(content)
    return output_path
```

### Generators Can Be Impure

Generators that read lazily are I/O - they belong in shell:

```python
# pattern: Imperative Shell

def read_records(path: Path) -> Iterator[Record]:
    """Lazily read records from file."""
    with open(path) as f:
        for line in f:
            yield parse_record(line)  # parse_record is Core
```

### Pass Time as Parameter

```python
# pattern: Functional Core

def is_expired(expiry: datetime, now: datetime) -> bool:
    """Check if something is expired. Pure - time is passed in."""
    return now > expiry

# pattern: Imperative Shell

def check_session(session_id: str) -> bool:
    """Check if session is expired."""
    session = get_session(session_id)
    return is_expired(session.expiry, datetime.now())  # Shell provides time
```

## Common Rationalizations

| Excuse | Reality | Fix |
|--------|---------|-----|
| "Just one file read" | File I/O = side effect | Shell reads, Core processes |
| "Database is passed as parameter" | DB operations are I/O | Shell queries, Core transforms |
| "Need to check if file exists" | File system = I/O | Shell checks, passes bool to Core |
| "Small HTTP call" | HTTP = side effect | Shell fetches, Core processes |
| "Need current time" | Non-deterministic | Shell passes time to Core |
| "Logging is a side effect" | **Exception.** Logging permitted. | Keep logger in Core |
| "Simpler to combine" | Mixed = untestable without mocks | Split now, test simply |

## Red Flags

**STOP and refactor if you see:**

- File I/O in a "pure" function
- Database connection passed to Core
- HTTP requests in business logic
- `os.environ` in calculations
- `datetime.now()` or `random()` in Core
- Tests requiring complex mocking

## Refactoring Patterns

### Extract Pure Core

```python
# BEFORE: mixed
def process_order(order_id: str) -> None:
    order = db.fetch(order_id)           # I/O
    discount = calculate_discount(order)  # Pure
    total = apply_discount(order, discount)  # Pure
    db.save(order_id, total)             # I/O

# AFTER: separated
def calculate_order_total(order: Order, rules: DiscountRules) -> Decimal:
    """Pure function - easy to test."""
    discount = calculate_discount(order, rules)
    return apply_discount(order, discount)

def process_order(order_id: str) -> None:
    """Thin shell."""
    order = db.fetch(order_id)
    total = calculate_order_total(order, get_discount_rules())
    db.save(order_id, total)
```

### Return Instead of Mutate

```python
# BEFORE: mutation
def sort_tasks(tasks: list[Task]) -> None:
    tasks.sort(key=lambda t: t.priority)

# AFTER: pure
def sorted_tasks(tasks: list[Task]) -> list[Task]:
    return sorted(tasks, key=lambda t: t.priority)
```

### Inject Dependencies

```python
# BEFORE: uses global
def validate_input(data: str) -> bool:
    return len(data) <= CONFIG.max_length

# AFTER: injected
def validate_input(data: str, max_length: int) -> bool:
    return len(data) <= max_length
```

## Summary

1. **Functional Core:** Pure functions. No I/O except logging.
2. **Imperative Shell:** I/O coordination. Minimal logic.
3. **Classify files.** Know what each file is.

**Test:** Can you test the business logic with simple assertions and no mocks? If not, refactor.
