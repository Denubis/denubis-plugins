# ADR 0002 — Wrapper tests use `CLAUDE_REAL_BINARY`

**Status:** Accepted

## Context

`REAL_CLAUDE` is a local variable inside `claude-wrapper.sh`. The wrapper's external
binary override is `CLAUDE_REAL_BINARY`. A test that exports the local-variable name does
not replace the child executable and can accidentally invoke the real Claude binary.

## Decision

Tests and controlled invocations set `CLAUDE_REAL_BINARY` when replacing the child
binary. `REAL_CLAUDE` is not an external configuration key.

## Consequences

- Wrapper tests exercise their declared stub.
- A wrong override name fails at the test boundary instead of silently falling through
  to the user's installation.

## Verification

- Implementation: `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`.
- Boundary tests: `tests/test_claude_wrapper_liveness.bats`.
- Paired current constraint: `../constraints.md`, “Bats env-var contract”.
