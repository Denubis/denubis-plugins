# Code Review Findings — phase-7

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification

```
Tests: uv run pytest -q → 782 passed in 3.24s
Bats (repo root): bats tests/test_crash_recovery_smoke.bats → 6/6 ok
Bats (/tmp): bats /path/to/tests/test_crash_recovery_smoke.bats → 6/6 ok (off-root confirmed)
```

## Prior Findings Verification

All three findings from the initial Phase 7 review (commit 2c49027) have been addressed in commit d0b5a8e.

### Important #1 — "every session will be classified `concluded`" overclaim

**Status: Resolved**

The fix routes all three overclaim sites to Phase 8's honesty pass via an extended instruction in `phase_08.md:550–556`. The extension now enumerates:

- `README.md:25-27` — both the "degrades to JSONL-tail-only heuristics" half and the "every session will be classified `concluded`" half, with the correct behaviour described
- `SKILL.md:99 (Integration section)` — the identical false claim, flagged separately
- The honest replacement text (what Phase 8 should write instead), including the empirical evidence from the dogfood

The design seed (`docs/design-plans/2026-05-19-post-mortem-crash-detection.md`) is updated to be the authoritative list of all three overclaim sites with the same honest replacement, so Phase 8 has two corroborating references. The README and SKILL.md themselves are unchanged in Phase 7 as intended — Phase 7 stays scoped to ship-what's-there.

The fix is complete and correctly scoped. The Phase 8 implementor has unambiguous, file:line-anchored instructions for all three corrections.

### Minor #1 — bats `CR` uses cwd-relative path

**Status: Resolved**

`tests/test_crash_recovery_smoke.bats:21` is now:

```bash
CR="uv run --project ${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"
```

The marketplace.json `open()` call (line 67) is also anchored:

```python
m = json.load(open('${BATS_TEST_DIRNAME}/../.claude-plugin/marketplace.json'))
```

The `open()` call is inside a double-quoted `-c` string, so the shell expands `${BATS_TEST_DIRNAME}` before Python receives the path — correct. Verified: 6/6 pass from /tmp, which was the failure condition the finding identified.

### Minor #2 — SKILL.md annotation iteration order undocumented

**Status: Resolved**

`plugins/denubis-crash-recovery/skills/triage/SKILL.md:39` now reads:

> **Ambiguous correlation**, then **Needs investigation**, then **Idle-live killed** rows. (Iterate in this order — higher-confidence borderlines first, regardless of report render order.)

The parenthetical exactly matches the suggested fix from the prior review.

## Plan Alignment

Unchanged from initial review — all tasks implemented and verified. No plan-alignment regressions introduced by the fix commit.

## Issues

None.

## Decision: APPROVED FOR MERGE

All three prior findings are resolved. No new issues were introduced in the fix commit. The five changed files are: the design seed (overclaim documentation extended), the prior findings file (written by the initial review), phase_08.md (honesty-pass instruction extended to cover all three sites), SKILL.md (parenthetical added), and the bats suite (BATS_TEST_DIRNAME anchoring applied to both path references). All changes are targeted and correct.
