# ADR 0002 — Wrapper tests use `CLAUDE_REAL_BINARY`

**Status:** Accepted

## Authority evidence

- Human invocation:
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-crash-recovery/0df390b7-41f5-4e92-a69d-bce7548f00ce.jsonl:9`
- Exact resolver:
  `cc-search-chats context 899dd8df-1a41-49f1-bbfb-ba77ddcc0691 --json`

The invocation directs the post-acceptance promotion of this ADR. The resolver supplies
the human message; this ADR does not reproduce it.

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
