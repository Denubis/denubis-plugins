# .ed3d/testing-guidance.md Format

Projects can create `.ed3d/testing-guidance.md` to specify test commands and gates for commits, PRs, and merges.

## Example

```markdown
# Testing Guidance

## Test Suites

### Unit Tests (required, fast)
```bash
pytest tests/unit/
```

### Linting (required, fast)
```bash
ruff check .
```

### End-to-End Tests (required)
```bash
pytest tests/e2e/ --browser chromium
pytest tests/e2e/ --browser firefox
```

### Documentation Build (required)
```bash
cd docs && make html
```

## Pre-PR Gate

All required suites must pass before creating a PR.

## Pre-Merge Gate

All required suites must pass before merging to main.
All required suites must pass again after merge (on the merged result).
```

## Format Rules

- Each `### Heading (markers)` under `## Test Suites` is a gate
- Fenced code blocks under each heading are the commands to run
- Markers in parentheses control when the suite runs:

| Marker | Meaning |
|--------|---------|
| `required` | Must pass for PR and merge gates |
| `fast` | Also runs before commits (lightweight, quick) |
| `optional` | Advisory only — failure is reported but does not block |

- A suite can have multiple markers: `(required, fast)` means it runs at commit time AND at PR/merge time
- `fast` suites should complete in seconds, not minutes — unit tests, linters, type-checkers
- `## Pre-PR Gate` and `## Pre-Merge Gate` sections can add additional prose constraints
- If the file is absent, skills fall back to CLAUDE.md test commands, then `pytest`

## Which skills use which gates

| Skill | Suites run |
|-------|-----------|
| `/commit` | `fast` only |
| `/make-pr` | All `required` (includes `fast`) |
| `/merge-to-main` | All `required` (includes `fast`), twice (pre and post merge) |
