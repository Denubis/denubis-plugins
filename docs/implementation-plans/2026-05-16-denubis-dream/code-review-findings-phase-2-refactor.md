# Code Review Findings — phase-2-refactor

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 1**

## Verification

```
Tests: uv run pytest tests/ → 492 passed in 0.82s
Lint: N/A (no lint config for shell/markdown content)
```

All 492 tests pass. The prior findings file (code-review-findings-phase-2.md) claimed "490 passed, 2 failed" — that was the pre-fix state at `8aa897f`. The HEAD commit `c2b12ac` (and `1e85c46` which fixed the description tests) together yield a clean 492.

## Plan Alignment

- DR1 amendment (co-located `_lib.sh` permitted): ✓ present in design plan, correctly scoped to "POSIX Bash, no test runner, no Python interpreter"
- `_lib.sh` helper file added at correct path: ✓ `plugins/denubis-dream/skills/dreaming/_lib.sh`
- Five helper functions per spec: ✓ `dream_main_slug`, `dream_main_dir`, `dream_today`, `dream_dated_dir`, `dream_discovered_slugs`
- SKILL.md `## Helper resolution` section added: ✓ at line 12, before all Bash blocks
- SKILL.md `## Bash-block convention` updated: ✓ sourced-helper pattern described
- Every Bash block opens with `source "$DREAM_LIB"`: ✓ all six blocks verified (lines 44, 71, 99, 111, 122, 138)
- Phase 3–6 plan notes added: ✓ consistent wording across all four plans
- AC2.5 (clean exit outside git repo): ✓ `|| exit 0` on SKILL.md line 46
- AC9.3 (autonomous no-op): ✓ autonomous block at SKILL.md lines 111–117

## Issues

### Minor (count: 1)

- **Issue**: In the `## Project slug resolution` Bash block, `dream_main_slug` is invoked twice per block execution: once explicitly on line 46 (`MAIN_SLUG=$(dream_main_slug)`), and a second time implicitly on line 47 via `dream_main_dir` (which calls `dream_main_slug` internally). Each call runs `git rev-parse --show-toplevel`. This is idempotent and correct; it is a minor efficiency redundancy, not a bug. A caller-supplies-slug variant of `dream_main_dir` (e.g. `dream_main_dir "$slug"`) would eliminate the double invocation, but that requires changing the helper's interface.
- **Location**: `_lib.sh` line 26 + SKILL.md lines 46–47
- **Fix**: Accept as-is (correct behaviour, negligible cost in practice). Alternatively, restructure SKILL.md line 47 to derive from `$MAIN_SLUG` directly: `MAIN_DIR="$HOME/.claude/projects/$MAIN_SLUG"`. This avoids the extra git call without changing `_lib.sh`.

## Bash Quality Findings (per review brief)

**Quoting:** All variable expansions in `_lib.sh` are correctly quoted. `$HOME`, `$slug`, `$main_dir`, `$today`, and `$git_top` are in double-quoted or single-argument `printf` contexts throughout. `$DREAM_LIB` in SKILL.md is a template placeholder, not a live variable — its substitution instruction is unambiguous.

**Local declarations:** All function-local variables use `local` (`git_top`, `main_path`, `slug`, `main_dir`, `today`). No scope leakage.

**Error propagation:** `dream_main_slug` returns 1 when `git rev-parse` returns empty. `dream_main_dir` and `dream_dated_dir` both propagate via `|| return 1`. `dream_discovered_slugs` propagates via `|| return 1`. The `|| exit 0` in SKILL.md line 46 was verified by execution: when `dream_main_slug` returns 1, the command substitution completes with exit code 1, the `||` fires, and the shell exits 0. Line 47 is not reached. AC2.5 is correctly implemented.

**Idempotency:** Each function re-derives from `git rev-parse` and `date` on every call. No cached state. The `dream_dated_dir` inline calls in the autonomous-mode and manual-mode no-op blocks (SKILL.md lines 113, 114, 124) produce the same path as the prelude block's `DATED_DIR=$(dream_dated_dir)` (line 101) — verified by the double-call idempotency test.

**`sed -E` portability:** `sed -E` is GNU sed and BSD sed (macOS). The design targets "Bash + standard tools" (not strict POSIX sh), and the project's existing shell code uses bash-specific constructs. This is consistent with design intent. Not flagged.

**No `set -e`:** The helper is sourced, not executed as a script, so a `set -e` at top level would affect the calling shell. The `|| return 1` chains handle propagation explicitly. No missing-`set -e` risk.

**Unquoted command substitutions:** None found. All `$(...)` results are assigned to variables or passed as single-argument `printf`; no word-splitting or glob-expansion risk.

**`$DREAM_LIB` template model:** The `## Helper resolution` section clearly labels `$DREAM_LIB` as a template placeholder (not an env var), provides two worked path examples, and instructs substitution before each Bash tool call. The model is unambiguous.

## Decision: APPROVED FOR MERGE
