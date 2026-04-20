---
name: defense-in-depth
family: coding-effectively
description: Use when fixing bugs caused by invalid data or designing validation - enforces validation at system boundaries to make bugs structurally impossible rather than temporarily fixed
---

# Defense-in-Depth Validation

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or tests that mock intermediate layers.

**Core principle:** Validate at system boundaries. Make the bug structurally impossible.

## When to Use

**Use when:**
- Invalid data caused a bug
- Data crosses system boundaries (API → service → database)
- Multiple code paths reach the same code
- Tests mock intermediate layers

**Don't overuse:**
- Pure internal functions with validated callers (FCIS handles this)
- Data already validated by framework (pydantic, etc.)
- Adjacent layers doing identical checks

## System Boundaries

Validation happens at boundaries, not everywhere:

```
┌─────────────────────────────────────────┐
│  External World (untrusted)             │
└─────────────────┬───────────────────────┘
                  │ ← VALIDATE HERE (Entry)
┌─────────────────▼───────────────────────┐
│  API Layer                              │
└─────────────────┬───────────────────────┘
                  │ ← Trust within app
┌─────────────────▼───────────────────────┐
│  Business Logic (Functional Core)       │
└─────────────────┬───────────────────────┘
                  │ ← VALIDATE HERE (Before persist)
┌─────────────────▼───────────────────────┐
│  Database / External Services           │
└─────────────────────────────────────────┘
```

## The Four Layers

### Layer 1: Entry Point Validation

**Purpose:** Reject invalid input at API/system boundary.

```python
from pydantic import BaseModel, field_validator

class CreateProjectRequest(BaseModel):
    name: str
    working_directory: str

    @field_validator('working_directory')
    @classmethod
    def validate_directory(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('working_directory cannot be empty')
        path = Path(v)
        if not path.exists():
            raise ValueError(f'working_directory does not exist: {v}')
        return v
```

**When needed:** Always at API boundaries. Pydantic does this naturally.

### Layer 2: Business Logic Preconditions

**Purpose:** Ensure data makes sense for this specific operation.

```python
def initialize_workspace(project_dir: Path, session_id: str) -> Workspace:
    """Initialize workspace for a project.

    Parameters
    ----------
    project_dir : Path
        Must be an existing directory.
    session_id : str
        Must be non-empty.

    Raises
    ------
    ValueError
        If preconditions not met.
    """
    if not project_dir.is_dir():
        raise ValueError(f"project_dir must be directory: {project_dir}")
    if not session_id:
        raise ValueError("session_id required")
    # ... proceed
```

**When needed:** When mocks might bypass Layer 1, or when business rules differ from entry validation.

### Layer 3: Environment Guards

**Purpose:** Prevent dangerous operations in specific contexts.

```python
import tempfile
from pathlib import Path

def git_init(directory: Path) -> None:
    """Initialize git repository.

    In test environment, refuses to init outside temp directory.
    """
    if os.environ.get('TESTING'):
        temp_root = Path(tempfile.gettempdir())
        if not directory.is_relative_to(temp_root):
            raise RuntimeError(
                f"Refusing git init outside temp dir in tests: {directory}"
            )
    # ... proceed with git init
```

**When needed:** Destructive or irreversible operations, especially in tests.

### Layer 4: Debug Instrumentation

**Purpose:** Capture context for forensics when other layers fail.

```python
import structlog

logger = structlog.get_logger(__name__)

def git_init(directory: Path) -> None:
    """Initialize git repository."""
    logger.debug(
        "git_init",
        directory=str(directory),
        cwd=str(Path.cwd()),
        exists=directory.exists(),
    )
    # ... proceed
```

**When needed:** When debugging is difficult, or tracing how bad data arrived.

## Decision Heuristic

| Situation | Layers Needed |
|-----------|---------------|
| Public API, simple validation | 1 only |
| Data crosses multiple services | 1 + 2 |
| Destructive operations | 1 + 2 + 3 |
| Chasing hard-to-reproduce bug | 1 + 2 + 3 + 4 |
| Tests mock intermediate layers | At minimum: 1 + 3 |

## Python's EAFP and Defense-in-Depth

Python's "Easier to Ask Forgiveness than Permission" (EAFP) is fine **within validated boundaries**.

```python
# EAFP is fine here - we've validated at boundary
def process_config(config: ValidatedConfig) -> Result:
    try:
        value = config.settings['key']  # EAFP: try to access
    except KeyError:
        value = default
    return process(value)
```

Defense-in-depth is about **boundaries**, not abandoning EAFP internally.

## Applying the Pattern

When you find a bug caused by invalid data:

1. **Trace the data flow** - Where does the bad value originate? Where is it used?
2. **Map boundaries** - List every boundary the data crosses
3. **Decide which layers** - Use heuristic above
4. **Add validation** - Entry → business → environment → debug
5. **Test each layer** - Verify Layer 2 catches what bypasses Layer 1

## Error Messages

Include the bad value and expected format:

```python
# Good: actionable
raise ValueError(f"working_directory must exist, got: {path}")

# Bad: no context
raise ValueError("invalid directory")
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| One validation point | Add at entry + before persist |
| Identical checks at adjacent layers | Make each layer check something different |
| Environment guards only in prod | Add them in tests too |
| Swallowing validation errors | Let them propagate with context |
| Validation without useful message | Include the bad value |

## Quick Reference

| Layer | Question It Answers | Typical Check |
|-------|---------------------|---------------|
| Entry | Is input valid? | Non-empty, exists, correct type |
| Business | Does it make sense here? | Required for this operation |
| Environment | Is this safe in this context? | Not in tests, inside temp dir |
| Debug | How did we get here? | Log inputs, cwd, stack |

## Key Insight

During testing, each layer catches bugs the others miss:
- Different code paths bypass entry validation
- Mocks bypass business logic checks
- Edge cases need environment guards
- Debug logging identifies structural misuse

**The bug isn't fixed until it's impossible.**
