# ADR 0001 — Wrapper exit-code capture under `set -e`

**Status:** Proposed (2026-05-20)

**Decision authors:** Phase 8 implementor + orchestrator + user (authorisation
2026-05-19)

**Paired constraint:** `../constraints.md` § "Wrapper exit-code capture +
transcript-archive gate (Phase 8)"

## Context

`plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` runs with
`set -euo pipefail` at the top of the script (`claude-wrapper.sh:33`). The
Phase 8 implementation plan added two new blocks to the wrapper:

- **Block A:** atomic write of `~/.claude/run/$$.live` before the `claude`
  invocation.
- **Block B:** conditional cleanup (`rm -f` iff exit code is 0 or 130)
  immediately before the final `exit $EXIT_CODE`.

The plan asserted in its "Codebase verified" section: *"Wrapper is structurally
ready (already uses foreground invocation with `EXIT_CODE=$?` capture at line
89-90; no `exec` to replace). No preparatory-refactor needed."* This assertion
was wrong. Under `set -e`, a non-zero exit from `claude` on line 89 aborts the
wrapper immediately, before line 90's `EXIT_CODE=$?` can capture the code and
before the cleanup block at the end of the script can run. Empirically
verified with a minimal reproduction during Phase 8 Subcomponent A:

- `claude` exits 0 → `set -e` doesn't trip → cleanup runs → file removed ✓
- `claude` exits 130 → `set -e` aborts at line 89 → cleanup never runs → file
  retained ✗ (AC5.2 requires the file removed on Ctrl-C)
- `claude` exits 1 / 137 / 139 → `set -e` aborts at line 89 → cleanup never
  runs → file retained ✓ (AC5.5 expects retention, but the path through which
  retention happens is "Block B never executes", not "Block B branches false"
  — a structural failure mode passing for the wrong reason)

The AC5.2 case (exit 130 must remove the file) cannot be satisfied without
making the cleanup block actually reachable on non-zero exits.

## Options considered

1. **Add `|| EXIT_CODE=$?` to the `claude` invocation line + default
   `EXIT_CODE=${EXIT_CODE:-0}` on the next line.** The canonical bash idiom
   for "capture non-zero exit while preserving `set -e` elsewhere". Two lines
   modified in existing wrapper code.

2. **Bracket the `claude` invocation with `set +e` / `set -e`.** More
   intrusive (three additional lines) and breaks the script's invariant of
   uniform `set -e` discipline.

3. **Wrap the `claude` invocation in `if ! ...; then EXIT_CODE=$?; fi`.**
   Semantically equivalent to option 1 but more verbose.

4. **Defer Phase 8 to brainstorm wrapper exit-handling more broadly.** The
   existing transcript-archive block at the time also had the same `set -e`
   blocker — it only ran on clean exits because non-zero exits aborted the
   wrapper before reaching it. Treating this as a wider design problem was
   considered. Rejected because the post-Phase-8 ADR can capture the
   transcript-archive-on-non-zero design question separately; the wrapper
   exit-code capture itself is small and well-bounded.

## Decision

Option 1: change the `claude` invocation line from

```bash
"$REAL_CLAUDE" --disallowedTools "$DISALLOWED_TOOLS" --teammate-mode=auto "${EXTRA_ARGS[@]}" "$@"
EXIT_CODE=$?
```

to

```bash
"$REAL_CLAUDE" --disallowedTools "$DISALLOWED_TOOLS" --teammate-mode=auto "${EXTRA_ARGS[@]}" "$@" || EXIT_CODE=$?
EXIT_CODE=${EXIT_CODE:-0}
```

The `|| EXIT_CODE=$?` defers `set -e` for the single `claude` invocation;
`${EXIT_CODE:-0}` handles the case where `claude` exits 0 and the `||` branch
never fires (leaving `EXIT_CODE` unset under `set -u`).

## Consequences

**Positive:**
- AC5.2 (Ctrl-C exit 130 removes the liveness file) now passes for the right
  reason — Block B actually runs and the conditional matches.
- AC5.5 (×3, codes 1/137/139 preserve the file) now passes for the right
  reason — Block B runs and the conditional doesn't match.
- The wrapper's existing transcript-archive block at lines 92-119 also
  becomes reachable on non-zero exits — see "Spillover consequence" below.

**Negative:**
- The plan's "Codebase verified" guarantee turned out to be insufficient
  rigour. Future "Codebase verified" assertions should mean: *the plan author
  ran the wrapper with the specific exit codes the new test cases will
  exercise and observed the relevant lines execute*. Not just: *I read the
  code and it looks fine.*

**Spillover consequence (handled in commits a9e778e and 0909322):**
The transcript-archive block (`Press Enter to archive transcript...`)
previously fired only on clean exits because `set -e` aborted the wrapper
before reaching it on non-zero exits. After this ADR's fix, it would fire on
all exits. To preserve the pre-Phase-8 effective behaviour, the transcript-
archive block has been wrapped in `if [[ "$EXIT_CODE" -eq 0 ]]; then ... fi`
(commit `a9e778e`). The gate is locked by a bats fitness test (commit
`0909322`) and documented in `CHANGELOG.md` 2.32.2.

## Verification

- `tests/test_claude_wrapper_liveness.bats::AC5.5` (×3) confirms the wrapper
  exits non-zero, captures the exit code, and reaches the cleanup block
  which retains the file.
- `tests/test_claude_wrapper_liveness.bats::AC5.2 — Ctrl-C exit (130)
  removes the liveness file` confirms the 130 case reaches cleanup and
  removes the file.
- `tests/test_claude_wrapper_liveness.bats::M1 fitness — abnormal claude
  exit skips transcript-archive prompt` locks the paired transcript-archive
  gate.
