# Test Requirements — crash-detection

Maps every acceptance criterion to its automated test(s). The test-analyst validates this coverage during execution. Human-judgment items are in `uat-requirements.md`. Every AC maps to an automated test below OR a UAT entry; none are unmapped.

Package tests: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/`. Bats: `tests/test_claude_wrapper_liveness.bats`. Run: `uv run pytest` (worktree root) and `bats tests/test_claude_wrapper_liveness.bats`.

| AC | Type | Test file | Verifies |
|----|------|-----------|----------|
| AC1.1 | integration | test_scan.py | snapshot-prefixed JSONL + dead-PID/boot-current marker → `run_scan` → `hard_crash` (Phase 1 Task 6) |
| AC1.2 | unit | test_render.py | `hard_crash` row renders under `## Probable system-crash victims` with full UUID + `claudew --resume <full-uuid>` |
| AC1.3 | unit | test_classify.py (existing) + test_scan.py | present + PID-alive (start-time matched) → `live`, not `hard_crash` |
| AC2.1 | unit/integration | test_jsonl_tail.py, test_scan.py | later-line `cwd` extracted (not `""`); session not `irrecoverable/missing_cwd` |
| AC2.2 | unit | test_correlate.py | later-line-cwd `.live` correlates (DIRECT/MTIME), not `no_match`; `_project_dir_for_cwd` finds the dir |
| AC2.3 | unit/integration | test_jsonl_tail.py, test_scan.py | no `cwd` anywhere in window → still `irrecoverable/missing_cwd` |
| AC3.1 | integration | test_scan.py | two markers → one UUID: `run_scan` completes, no `IntegrityError`, one `sessions` row |
| AC3.2 | integration | test_scan.py | UUID both direct-match and ambiguous-candidate → direct-match fact wins |
| AC4.1 | bats | test_claude_wrapper_liveness.bats | wrapper writes `session_id` + `start_time` for fresh and resumed sessions |
| AC4.2 | bats + unit | test_claude_wrapper_liveness.bats, test_liveness.py, test_scan.py | written `start_time` matches comm-safe `/proc` parse; `pid_alive_checked` True on match, False on mismatch; scan rejects reuse |
| AC4.3 | unit | test_correlate.py | `session_id`-bearing marker direct-matches `<session_id>.jsonl` |
| AC4.4 | unit | test_liveness.py, test_correlate.py | no `start_time` → bare `kill -0`; no `session_id` → Stage-2 fallthrough |
| AC4.5 | bats (existing) | test_claude_wrapper_liveness.bats | clean exit 0/130 removes `.live`; abnormal 137/139/non-zero preserves |
| AC5.1 | unit | test_render.py | every in-scope session renders; crash highlight adds a section, drops no roster row |
| AC5.2 | unit | test_render.py | full UUID in resume line (never only `uuid[:8]`); pane-title/last-substantive/`jsonl_last_ts` shown when present |
| AC5.3 | unit | test_render.py | render byte-identical for identical DB state |
| AC6.1 | unit | test_correlate.py | single in-tight-window JSONL → `MTIME_MATCH` |
| AC6.2 | unit + integration | test_correlate.py, test_scan.py | multi-cwd candidates corroborated by one resurrect pane → resolves to it |
| AC6.3 | unit | test_correlate.py | uncorroborated multi-candidate → `borderline/ambiguous_match`, all candidates listed |
| AC6.4 | unit | test_resurrect.py | parse pane fields (title=6, `:path`=7, shell=9); `snapshot_near`; `label_for_cwd` prefers `✳` |
| AC7.1 | unit | test_init.py | `init()` on pre-existing DB adds columns, no data loss, idempotent; `open_db()` refuses un-migrated DB (RuntimeError → run `crash-recovery init`), schema left untouched; `run_scan()` against un-migrated DB raises clean RuntimeError, no partial write |
| AC7.2 | unit | test_init.py | fresh `init()` creates columns from DDL |
| AC7.3 | unit | test_render.py | `render()` on un-migrated DB does not raise `no such column` |
| AC8.1 | unit | test_prune.py | `survey_markers` / `--dry-run` lists dead start-time-checked markers (session concluded/hard_crash), no delete |
| AC8.2 | unit | test_prune.py | `--confirm` reaps markers |
| AC8.3 | unit | test_prune.py | alive markers + uncorrelated markers never reaped |
| AC9.1 | regression | full `uv run pytest` | existing 179 + new tests green |
| AC9.2 | regression | `bats tests/test_claude_wrapper_liveness.bats` | existing 13 + new bats green |

**Human-judgment (not automatable):** whether the surfaced crash victims match what the operator actually lost, and whether the resume commands recover the right sessions — see `uat-requirements.md` (Phase 4).
