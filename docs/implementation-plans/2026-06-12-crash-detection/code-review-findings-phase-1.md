# Code Review Findings — phase-1

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 3**

## Verification

```
Tests: uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q → 193 passed in 2.24s
Lint: skipped (no linter in project; not a finding)
```

## Plan Alignment

- crash-detection.AC1.1: `test_snapshot_prefixed_crash_victim_surfaces_as_hard_crash` — end-to-end: snapshot-prefixed JSONL + dead-PID + boot-current + TOOL_USE_NO_RESULT tail → `hard_crash`. ✓ implemented
- crash-detection.AC2.1: `test_first_record_field_cwd_on_line2_snapshot_prefixed` (helper level) + `test_scan_classifies_snapshot_prefixed_jsonl_not_missing_cwd` (scan level). ✓ implemented
- crash-detection.AC2.2: three correlate tests cover project-dir lookup, DIRECT_MATCH, and MTIME_MATCH on snapshot-prefixed JSONLs. ✓ implemented
- crash-detection.AC2.3: `test_first_record_field_returns_none_when_no_cwd_anywhere` (helper) + `test_scan_genuine_no_cwd_jsonl_still_classifies_missing_cwd` (scan). ✓ implemented
- crash-detection.AC3.1: `test_scan_dedup_two_markers_same_uuid_no_integrity_error` — two markers, same UUID, no IntegrityError, one sessions row + one history row. ✓ implemented (see note below on test genuineness)
- crash-detection.AC3.2: `test_scan_dedup_direct_match_wins_over_ambiguous` — DIRECT_MATCH wins over AMBIGUOUS for same UUID. ✓ implemented

### AC3 test genuineness (load-bearing check)

The dedup tests work by writing two in-window same-cwd JSONLs (uuid_x, uuid_y) in one project directory, then marker B with no `--resume`. The correlate logic for marker B: `_project_dir_for_cwd` finds the directory (both JSONLs share the same cwd), both JSONLs pass the mtime + `_jsonl_first_entry_ts_meets_threshold` filter → `len(candidates) == 2` → `AMBIGUOUS` with candidates `(uuid_x, uuid_y)`. This means `_build_ambiguous_facts` emits a fact for `uuid_x` from marker B, which would collide with marker A's DIRECT_MATCH fact for the same UUID. The collision is genuine — not vacuous. Pre-fix code would have raised `sqlite3.IntegrityError` here.

## Issues

### Minor (count: 3)

- **Issue**: `first_record_field` has no return type annotation. Every other helper in `jsonl.py` carries a return annotation (`-> str | None`, `-> int | None`, etc.).
- **Location**: `jsonl.py` line 357 in the diff (`def first_record_field(path: Path, field: str, limit: int = _FIRST_FIELD_SCAN_LIMIT):`)
- **Fix**: Add `-> str | None` to the signature.

---

- **Issue**: Mangled docstring sentence in `first_record_field`: "Blank lines and lines that fail to JSON-decode are skipped (they do not consume the record budget is a design choice — count only parseable dict records toward `limit`)."
- **Location**: `jsonl.py` lines 363-364 in the diff (the `first_record_field` docstring)
- **Fix**: Rewrite as two sentences: "Blank lines and lines that fail to JSON-decode are skipped and do not consume the record budget — only parseable dict records count toward `limit`."

---

- **Issue**: The module-level comment (line 353 in the diff) says the limit "caps cost on pathological files." The `count` variable increments only on parseable dict records; blank lines and non-JSON lines do not consume the budget and are iterated unconditionally. A file with a million blank lines or a million unparseable lines would be read in full. The comment implies a bound that the code does not fully provide for degenerate inputs.
- **Location**: `jsonl.py` lines 351-353 in the diff (the `_FIRST_FIELD_SCAN_LIMIT` comment block)
- **Fix**: Qualify the comment: "caps cost on pathological but parseable files." Alternatively, note that line-count is not bounded, only parseable-dict-record count. The behaviour is correct for all realistic transcripts; this is a comment accuracy issue only.

## Consolidation Opportunities

None visible in the diff context.

## Assessment

The implementation is correct. The forward-scan helper is sound: the bound is honoured (the `count >= limit` check fires before the loop continues after the limit-th parseable dict record), the non-empty-str filter is correct for both `cwd` and `timestamp`, `None` is returned on absence, `OSError` is caught at open time. The contract at each call site is preserved: `_first_entry_cwd` returns `""` not `None` via the `or ""` idiom; `_cwd_matches_any_jsonl_in` treats a `None` return from the helper as non-matching (correct, since `None == cwd` is always `False`); `_jsonl_first_entry_ts_meets_threshold` checks `raw_ts is None` explicitly before further parsing.

The dedup rank logic is correct. The tuple comparison `(rank, liveness_path_str) < existing[:2]` is a standard Python lexicographic comparison — lower rank wins, and path string breaks ties deterministically regardless of filesystem iteration order. The `seen` set derived from `deduped` is correct and feeds `_walk_jsonl_only` cleanly.

The AC3 dedup tests are genuine: two markers producing a real UUID collision have been verified by tracing the correlate path.

## Decision: APPROVED FOR MERGE
