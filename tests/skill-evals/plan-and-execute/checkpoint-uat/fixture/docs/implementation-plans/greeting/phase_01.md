# Phase 1: Uppercase greeting is usable and documented

**Goal:** The public function supports an optional uppercase result without changing its
default.

<!-- START_TASK_1 -->
### Task 1: Establish and implement uppercase behavior

**Files:** `greeting_tests.py`, `greeting.py`, `README.md`

**Verifies:** `greeting.AC1`

Add the missing behavioral test first, observe the intended failure, implement the
keyword-only option minimally, and update README usage.

**Run:** `python -m unittest discover -p '*_tests.py' -q`
**Expected evidence:** both default and uppercase cases pass; removing the option makes
the uppercase case fail.
<!-- END_TASK_1 -->
