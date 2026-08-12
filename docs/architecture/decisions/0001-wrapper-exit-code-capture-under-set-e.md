# ADR 0001 — Wrapper exit-code capture under `set -e`

**Status:** Accepted

## Authority evidence

- Human invocation:
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-crash-recovery/0df390b7-41f5-4e92-a69d-bce7548f00ce.jsonl:9`
- Exact resolver:
  `cc-search-chats context 899dd8df-1a41-49f1-bbfb-ba77ddcc0691 --json`

The invocation directs the post-acceptance promotion of this ADR. The resolver supplies
the human message; this ADR does not reproduce it.

## Context

`claude-wrapper.sh` runs with `set -euo pipefail`. Its liveness-marker cleanup and final
exit must still execute when the child Claude process exits non-zero. A bare command
followed by `EXIT_CODE=$?` cannot provide that boundary: `set -e` exits before the
assignment.

## Decision

Run the child command as `... || EXIT_CODE=$?`, then set
`EXIT_CODE=${EXIT_CODE:-0}`. Keep the transcript-archive prompt behind an explicit
exit-zero condition. The liveness cleanup removes the marker only for exit 0 or 130 and
retains it for other failures.

## Consequences

- The cleanup branch executes for every child exit status.
- Exit 130 follows the intentional clean-interrupt path instead of being retained only
  because the wrapper aborted early.
- Other non-zero exits retain crash evidence through the intended branch.
- Transcript archiving remains a clean-exit action.

## Verification

- Implementation: `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`.
- Boundary tests: `tests/test_claude_wrapper_liveness.bats`.
- Paired current constraint: `../constraints.md`, “Wrapper exit-code capture +
  transcript-archive gate”.
