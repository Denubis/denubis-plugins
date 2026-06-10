# Code Review Findings — phase-1

Third review pass. Verifying fixes from commit 2f8fb1f against prior findings from the re-review cycle.
BASE_SHA: ee5d8e2b92b5e00229ff7ade7e2847bba6d66232
HEAD_SHA: 2f8fb1f542b3b3db6d19284cca06bbcb4c58049c

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Prior Findings Verification

Three findings carried over from the re-review cycle (recorded in the prior code-review-findings-phase-1.md). Each checked against the diff and the current file state.

**Critical-1 (DBA): CLASSIFICATION_VALUES contained composite values `borderline+ambiguous_match` and `borderline+malformed_tail` inconsistent with Phase 2's StrEnum**

RESOLVED. `db.py:30–36` is now the bare 5-value tuple:

```python
CLASSIFICATION_VALUES: tuple[str, ...] = (
    "live",
    "hard_crash",
    "borderline",
    "concluded",
    "irrecoverable",
)
```

No literal `borderline+` string survives anywhere in `db.py`. `grep -n "borderline+" db.py` returns only line 33 (`"borderline",`), which is the bare value — not a composite.

**Minor-1: three `conn.commit()` calls inside `pytest.raises` blocks were unreachable dead code**

RESOLVED. All three removed. Evidence from diff: three `-conn.commit()` hunks at `test_init.py:243`, `test_init.py:282`, `test_init.py:321` (pre-fix numbering). Current file has zero `conn.commit()` inside any `pytest.raises` block. The setup commit at line 315 (the `conn.commit()` before the RESTRICT `pytest.raises` block in `test_classification_history_scan_id_fk_is_restrict`) is intact and correct — it commits the prerequisite rows before testing the FK constraint.

**Minor-2: Task 2 "Files:" list still included `tests/__init__.py`**

RESOLVED. The line `Create: plugins/denubis-crash-recovery/scripts/crash_recovery/tests/__init__.py` is removed from `phase_01.md:120`. The Task 2 Files list now reads `tests/conftest.py` only, consistent with Step 4's prohibition at `phase_01.md:169`.

---

## Verification

```
Tests: uv run pytest -q plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ → 21 passed in 0.42s
Lint: not re-run (no new Python code in this diff; 3-line removal from test_init.py, 2-line removal from db.py)
```

21 tests pass. No tests were lost or skipped relative to the prior passing count.

---

## Doc Sync Verification

Four documents updated in this commit — all consistent with each other and with `db.py`:

| Document | Change | Status |
|----------|--------|--------|
| `db.py:30–36` | Bare 5-value tuple | Authoritative source |
| `docs/architecture/database.md:70–76` | Bare 5-value list in code fence + render-section explanation note | Consistent |
| `docs/design-plans/2026-05-08-crash-recovery.md:150` | Comment updated to `live \| hard_crash \| borderline \| concluded \| irrecoverable` | Consistent |
| `docs/implementation-plans/.../phase_01.md:310–316` | Spec code block updated to bare 5-value tuple | Consistent |

The render-section explanation note at `database.md:76` is present and clear: "These compound section keys are a rendering concept only — they are derived at render time from `(classification, reason)` tuples stored in separate columns. The DB stores only the bare classification value; the `reason` column holds the distinguishing reason string."

---

## Issues

None.

---

## Decision: APPROVED FOR MERGE

All prior findings resolved. No new issues introduced by the fix commit. Implementation is correct and internally consistent across code, tests, and documentation.
