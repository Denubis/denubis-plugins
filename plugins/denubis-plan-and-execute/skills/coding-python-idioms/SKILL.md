---
name: coding-python-idioms
family: coding-effectively
description: Use when writing Python code - covers Python 3.14+ patterns, t-strings, ty, uv, ruff, typer, pydantic-settings, and security practices
---

# Python Idioms

**Assumes Python 3.14+** unless project CLAUDE.md says otherwise. **Check `python --version` before assuming 3.14 features are available** -- some projects (e.g. vllm) require 3.12.

## Version Compatibility

| PEP | Feature | Min Version | Syntax change? |
|-----|---------|-------------|----------------|
| 695 | Type parameter syntax (`def f[T]()`) | 3.12 | Yes |
| 701 | F-string nesting, backslashes, comments | 3.12 | Relaxation |
| 696 | Type parameter defaults (`class Foo[T = str]`) | 3.13 | Yes |
| 649 | Deferred annotation evaluation | 3.14 | No |
| 750 | Template strings (`t"..."`) | 3.14 | Yes |
| 758 | Except without parentheses | 3.14 | Yes |
| 765 | SyntaxWarning for return/break/continue in finally | 3.14 | Restriction |

## Tooling

**Use `uv run` for all tooling** unless project CLAUDE.md says otherwise. Never `.venv/bin/X` or `python -m X`.

```bash
# Good
uv run ruff check .
uv run pytest
uv run ty check

# Bad
.venv/bin/ruff check .
python -m ruff check .
python -m pytest
```

## Type Annotations

### Modern Syntax

```python
# Good: Python 3.10+ union syntax
def process(value: str | None) -> list[str]:
    ...

# Avoid: typing module for basic types
from typing import Optional, List
def process(value: Optional[str]) -> List[str]:  # outdated
    ...
```

### Type Checking with ty

Use `ty` with strict settings. When ty rejects code:

```python
# Escape hatch with commitment
result = some_library_call()  # type: ignore[no-untyped-call]
# TODO(2026-Q2): Revisit when library adds type stubs
# Flag on: uv sync --upgrade
```

**Rules:**
- Never bare `# type: ignore` - always specify the error code
- Always add explanation comment
- Always add TODO with timeline
- Check on every `uv sync --upgrade` if still needed

### Type Parameter Syntax (PEP 695, 3.12+)

```python
# Good: inline type parameters
def first[T](items: list[T]) -> T:
    return items[0]

class Stack[T]:
    def push(self, item: T) -> None: ...
    def pop(self) -> T: ...

# Type alias with the type statement
type Vector[T] = list[T]

# Old style (avoid in 3.12+)
from typing import TypeVar
T = TypeVar("T")
def first(items: list[T]) -> T: ...
```

### Type Parameter Defaults (PEP 696, 3.13+)

```python
# Default type parameter
class Response[T = dict]:
    data: T

r = Response()       # T defaults to dict
r2 = Response[str]()  # T is str
```

### Deferred Annotations (PEP 649, 3.14+)

Forward references work without quotes in 3.14+:

```python
# Good: no quotes needed
class Node:
    def add_child(self, child: Node) -> None:
        ...

# Unnecessary in 3.14+
class Node:
    def add_child(self, child: "Node") -> None:  # quotes not needed
        ...
```

## String Formatting

### T-Strings for Security

Use t-strings (template strings) for any string that will be:
- Passed to a SQL driver
- Rendered as HTML
- Passed to a shell command
- Used in any security-sensitive context

```python
# Good: t-string prevents injection
from string.templatelib import Template
query = t"SELECT * FROM users WHERE id = {user_id}"
# Template object, not a string - must be processed by SQL driver

# Dangerous: f-string allows injection
query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection risk
```

### Debug Output

Use `=` specifier for debugging:

```python
# Good: shows variable name and value
print(f"{user_id=}, {status=}")
# Output: user_id=42, status='active'

# Verbose equivalent
print(f"user_id={user_id}, status={status}")
```

### Fallback for Pre-3.14

When t-strings unavailable, use parameterised queries:

```python
# Fallback: parameterised query (safe)
cursor.run_query("SELECT * FROM users WHERE id = %s", (user_id,))

# Never: string formatting for SQL
cursor.run_query(f"SELECT * FROM users WHERE id = {user_id}")  # injection
```

## Security

### Never Trust Untrusted Input

**Dynamic code interpretation on untrusted input = arbitrary code running:**

- Never pass user input to functions that interpret code dynamically
- Never deserialize untrusted binary data (use JSON instead)
- Never load serialized objects from untrusted sources

```python
# Safe: JSON parsing
import json
data = json.loads(user_input)  # data, not code

# Unsafe: binary deserialization from untrusted source
# (can execute arbitrary code during deserialization)
```

### Secrets Management

```python
# Good: from environment via pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str

    model_config = {"env_file": ".env"}

# Never: hardcoded secrets
API_KEY = "sk-1234567890"  # exposed in version control
```

### Validate at Boundaries

Validate all external input at entry points:

```python
# Good: validate on receipt
@app.post("/users")
def create_user(request: CreateUserRequest) -> User:
    # pydantic validates request automatically
    ...

# Bad: trust and forward
@app.post("/users")
def create_user(data: dict) -> User:
    # No validation - anything could be in there
    db.insert(data)
```

## Function Arguments

**Prefer explicit over flexible** (in order of preference):

1. **Positional** for essential parameters where order is natural
2. **Keyword with defaults** for optional parameters
3. **`*args`** only for truly variable-length input
4. **`**kwargs`** sparingly, only when undetermined names needed

```python
# Good: clear interface
def create_user(name: str, email: str, *, admin: bool = False) -> User:
    ...

# Avoid: unclear interface
def create_user(*args, **kwargs) -> User:  # what goes in?
    ...
```

## Default Arguments

**Never mutable defaults:**

```python
# Bad: shared mutable default
def append_to(item, target=[]):  # list shared across calls!
    target.append(item)
    return target

# Good: None sentinel
def append_to(item, target: list | None = None) -> list:
    if target is None:
        target = []
    target.append(item)
    return target
```

## Resource Management

**Always use context managers:**

```python
# Good: cleanup guaranteed
with open(path) as f:
    data = f.read()

# Bad: cleanup not guaranteed
f = open(path)
data = f.read()
f.close()  # may not run on exception
```

Never rely on `__del__` for cleanup - garbage collection timing is unpredictable.

## Exception Handling

### Except Without Parentheses (PEP 758, 3.14+)

```python
# Good (3.14+): no parentheses needed without as
except KeyError, ValueError:
    handle_error()

# Required: parentheses WITH as binding
except (KeyError, ValueError) as e:
    handle_error(e)

# Still valid: parentheses always work
except (KeyError, ValueError):
    handle_error()

# Pre-3.14: parentheses always required
except (KeyError, ValueError):
    handle_error()
```

### Finally Block Restrictions (PEP 765, 3.14+)

```python
# Bad (3.14 SyntaxWarning): return/break/continue exiting finally
def risky():
    try:
        return compute()
    finally:
        return default  # silently swallows exceptions -- now warns

# Good: let finally clean up, don't exit from it
def safe():
    try:
        return compute()
    finally:
        cleanup()  # runs, then original return proceeds
```

## Iteration Patterns

### Generators Over Lists

```python
# Good: memory efficient
total = sum(item.price for item in items)

# Wasteful: allocates full list
total = sum([item.price for item in items])
```

### Never Modify While Iterating

```python
# Bad: modifying during iteration
for item in items:
    if item.expired:
        items.remove(item)  # undefined behavior

# Good: build new collection
items = [item for item in items if not item.expired]

# Good: iterate over copy
for item in items[:]:
    if item.expired:
        items.remove(item)
```

## Logging

**Never `print()` for anything that matters:**

```python
# Good: structured, traceable
import structlog
logger = structlog.get_logger(__name__)

logger.info("user_created", user_id=user.id, email=user.email)

# Bad: unstructured, untraceable
print(f"Created user {user.id}")
```

**Principles:**
- Always include source location (logger name or file:line)
- Structured logging preferred (JSON/key-value)
- Web errors must appear in logs, not just browser console

## CLI with typer

**Preferred over click** - type hints become validation:

```python
import typer

app = typer.Typer()

@app.command()
def greet(name: str, count: int = 1, loud: bool = False):
    """Greet someone COUNT times."""
    greeting = f"Hello, {name}!"
    if loud:
        greeting = greeting.upper()
    for _ in range(count):
        print(greeting)

if __name__ == "__main__":
    app()
```

## Configuration with pydantic-settings

**Preferred over raw `.env`** - typed, validated, documented:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    debug: bool = False
    max_connections: int = 10
    api_timeout: float = 30.0

    model_config = {"env_file": ".env"}

settings = Settings()  # validates on import, fails fast
```

## Testing

Standard invocation:

```bash
uv run pytest --depper --depper-run-all-on-error -n auto --dist=loadfile -x --ff --durations=10 --tb=short
```

See `coding-good-tests` skill for patterns.

## Avoid Power Features

These obscure intent and break tools:

- Metaclasses (use dataclasses, protocols, or plain classes)
- `__del__` methods (use context managers)
- Import hooks (use standard imports)
- Dynamic inheritance (use composition)
- Bytecode manipulation

**When tempted:** There's almost always a simpler way.

## Quick Reference

| Pattern | Good | Avoid |
|---------|------|-------|
| Union types | `str \| None` | `Optional[str]` |
| Generic types | `list[str]` | `List[str]` |
| SQL/HTML/shell | t-strings | f-strings |
| Debug output | `f"{x=}"` | `f"x={x}"` |
| Optional params | `None` sentinel | mutable default |
| Resources | `with` statement | manual close |
| Iteration | generators | list comprehensions (unless needed) |
| Output | logging | print |
| CLI | typer | argparse |
| Config | pydantic-settings | raw os.environ |
