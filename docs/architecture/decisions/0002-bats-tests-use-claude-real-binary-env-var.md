# ADR 0002 — bats tests use `CLAUDE_REAL_BINARY` (not `REAL_CLAUDE`)

**Status:** Accepted (2026-05-20)

**Decision authors:** Phase 8 implementor

**Paired constraint:** `../constraints.md` § "Bats env-var contract (Phase 8)"

## Context

The Phase 8 implementation plan included a bats template for the wrapper
liveness lifecycle suite. The template repeatedly used `REAL_CLAUDE` as the
environment variable name for overriding the `claude` binary path:

```bash
REAL_CLAUDE="$CR_TEST_DIR/fake-claude.sh" "$WRAPPER" --print "test"
```

The phase file's commentary said this matched "the wrapper's existing
variable." The wrapper does have an internal local variable named
`REAL_CLAUDE`, but its external override knob is `CLAUDE_REAL_BINARY` (added
in commit `31e42d0`, 2026-04-29, predating the phase plan by approximately
ten days):

```bash
REAL_CLAUDE="${CLAUDE_REAL_BINARY:-$HOME/.local/bin/claude}"
```

Tests setting `REAL_CLAUDE` would not affect the wrapper at all — the
wrapper would read `CLAUDE_REAL_BINARY` (unset), fall back to
`$HOME/.local/bin/claude`, and either fail with "claude binary not found" or
worse, silently invoke the user's real claude binary.

Discovered during Phase 8 Subcomponent A when writing Task 2 (bats lifecycle
suite). The implementor inspected the wrapper to confirm the env-var name
and caught the mismatch before any test ran against the user's real claude
binary.

## Decision

All bats tests that invoke `claude-wrapper.sh` MUST set `CLAUDE_REAL_BINARY`
to override the binary path. The phase file's template was corrected in-line
during Subcomponent A; no test in `tests/test_claude_wrapper_liveness.bats`
references `REAL_CLAUDE`.

## Consequences

**Positive:**
- Tests actually exercise the stubbed binary they intend to exercise.
- Catches a class of plan-error where the plan author specified an
  identifier from memory rather than reading the code.

**Negative:**
- The plan template was wrong; without the in-line correction, the entire
  bats suite would have silently fallen through to the user's real claude
  binary, producing test results that say nothing about the wrapper's
  behaviour with a known-state stub.

**Pattern observation:**
This and ADR 0001 (the `set -e` interaction) together suggest that
implementation plans' "Codebase verified" assertions can be insufficiently
rigorous. Both defects were specifications written without reading the
actual implementation file. The Phase 8 Stage 2 design-conformance check
(task #9 of the orchestrator's plan) was extended to sweep all phase files
for similar plan-vs-code drift, not just verify the two known defects.

## Verification

- `grep -rn 'REAL_CLAUDE=' tests/` should never return matches inside test
  bodies (only inside the wrapper's local-variable assignment, if anything).
- `grep -rn 'CLAUDE_REAL_BINARY=' tests/test_claude_wrapper_liveness.bats`
  returns one match per test that overrides the binary (currently the
  `setup()` function plus several inline overrides for sleep-claude /
  jsonl-claude variants).
- All 13 tests in `tests/test_claude_wrapper_liveness.bats` pass against
  the patched wrapper, confirming the env-var routing works end-to-end.
