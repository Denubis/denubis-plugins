# Code Review Findings — plan-validation

**Review type:** Plan validation (design alignment + technical correctness)
**Design doc:** `docs/design-plans/2026-06-12-crash-detection.md`
**Plans reviewed:** `phase_01.md` through `phase_05.md`
**Review date:** 2026-06-12
**Baseline confirmed:** 179 pytest tests collected (matches plan's stated baseline)

---

## Status: APPROVED WITH NOTES

**Critical: 0 | Important: 3 | Minor: 3**

---

## Verification

```
Baseline count: uv run pytest --collect-only -q → 179 tests collected
Resurrect field indices: verified against real ~/.byobu-sessions/tmux_resurrect_20260612T182057.txt
/proc/stat field-22 parse: verified by field mapping (field 3 → index 0; field 22 → index 19 Python / $20 bash)
```

---

## AC Coverage

| AC | Covered by | Status |
|----|-----------|--------|
| AC1.1 hard_crash classification | Existing test_classify.py + Phase 1-2 fixes that let rules fire | ✓ (hand-wave; see Important-1) |
| AC1.2 render shows all means | Phase 4 | ✓ |
| AC1.3 prune defers concluded | Existing prune tests + Phase 1-2 fixes | ✓ (hand-wave; see Important-1) |
| AC2 forward cwd scan | Phase 1 | ✓ |
| AC3 dedup-safe scan | Phase 1 | ✓ |
| AC4 wrapper stamps | Phase 2 | ✓ |
| AC5 render overhaul | Phase 4 | ✓ |
| AC6 resurrect disambiguation | Phase 3 | ✓ |
| AC7 schema migration | Phase 4 | ✓ |
| AC8 marker reaping | Phase 5 | ✓ |
| AC9 regression baseline | Every phase | ✓ |

---

## Plan Alignment

- Phase 1: ✓ Implements AC2 (forward cwd scan), AC3 (dedup). Symbols planned (`first_record_field`, `_first_entry_cwd`, `_cwd_matches_any_jsonl_in`, `_jsonl_first_entry_ts_meets_threshold`, `_walk_sessions` dedup) all confirmed absent/present as expected.
- Phase 2: ~ AC header incorrectly lists AC3 as a Phase 2 deliverable. AC3 is Phase 1's deliverable. Phase 2 delivers AC4. (See Important-2.)
- Phase 3: ~ "Done when" and AC header claim AC5 ("all-means-all" render). AC5 is Phase 4's deliverable. Phase 3 provides the `label_for_cwd` prerequisite but not the render overhaul. (See Important-3.)
- Phase 4: ✓ Covers AC1.2, AC5, AC7. Fixture functions (`DbFixtureRow`, `make_db_with_sessions`) confirmed present in `jsonl_builder.py` but lack `pane_title`/`last_substantive` fields — Phase 4 must extend them. The plan explicitly covers this.
- Phase 5: ✓ Covers AC8. `open_db` read-write concern noted (see Minor-1).

---

## Issues

### Important (count: 3)

**Important-1: AC1.1 and AC1.3 integration coverage is asserted, not demonstrated**
- **Issue:** Phase 5's final note says AC1.1 (`hard_crash` classification) and AC1.3 (prune defers concluded) are "already covered by existing `test_classify.py` rules plus the Phase 1-2 correlation/liveness fixes that let those rules fire." This is correct in principle — the classifier rules fire on the scan output — but no plan task creates an end-to-end integration test exercising: snapshot-prefixed JSONL → `run_scan` → `hard_crash` classification → DB row. The plans produce the individual unit tests (Phase 1 tests `first_record_field`, Phase 2 tests `pid_alive_checked`) but no task explicitly wires them together into an integration test for the headline crash-detection scenario. If the wiring has a bug (e.g. `_first_entry_cwd` still falls through to the old path on some input shape), no test will catch it before merge.
- **Location:** `phase_05.md` lines 126-127 (final phase note); `phase_01.md` Task 5 (does not include an integration test for crash classification)
- **Fix:** Add one integration test in Phase 1 Task 5 or Phase 2 that: builds a snapshot-prefixed JSONL fixture via `make_full_fixture` (with `has_liveness=True, pid_alive=False, boot_id_current=True`) whose first line is a snapshot record and whose cwd appears on line 2+, runs `run_scan`, and asserts the session is classified `hard_crash`. This is the AC1.1 success path with a snapshot-prefix transcript.

**Important-2: Phase 2 AC header incorrectly claims AC3**
- **Issue:** `phase_02.md` "Acceptance Criteria Coverage" section lists `crash-detection.AC3: Dedup-safe scan`. AC3 is fully delivered by Phase 1 (`_walk_sessions` dedup logic). Phase 2 delivers AC4 (wrapper stamps). The mislabel will cause an implementer who reads Phase 2's done-when to believe dedup belongs in Phase 2 and may duplicate or skip Phase 1 work.
- **Location:** `phase_02.md` AC coverage section (AC3 entry)
- **Fix:** Remove the AC3 entry from Phase 2's AC coverage; it belongs exclusively to Phase 1.

**Important-3: Phase 3 "Done when" and AC header claim AC5**
- **Issue:** `phase_03.md` line 141: "all-means-all" and `label_for_cwd` are presented as AC5 deliverables. AC5 ("render shows all means") requires the Phase 4 render overhaul (`PROBABLE_CRASH_VICTIMS` section, PRAGMA graceful-degradation, full UUID, pane_title). Phase 3 creates `label_for_cwd` as a prerequisite for Phase 4's render, but Phase 3 alone does not deliver AC5.
- **Location:** `phase_03.md` AC coverage section (AC5.2 entry); "Phase 3 done when" (line 141)
- **Fix:** Remove AC5 from Phase 3's AC coverage and done-when. Clarify that `label_for_cwd` is a prerequisite consumed by Phase 4, which delivers AC5.

### Minor (count: 3)

**Minor-1: Phase 5 Task 1 comment says `open_db` "does not mutate"**
- **Issue:** `phase_05.md` line 70: "Open the DB read-only for `survey_markers` (`db.open_db` is fine — it does not mutate; or use the same read pattern as `survey`)." `db.open_db()` opens a read-write connection and asserts WAL mode — it is not a read-only URI. The comment is misleading. `survey()` in `prune.py` uses `db.open_db()` already (same pattern), so this is consistent — but the parenthetical claim that it "does not mutate" is technically wrong: WAL assertion writes the journal mode if not already set, and a `PRAGMA` call can modify journal state.
- **Location:** `phase_05.md` line 70
- **Fix:** Replace with: "Open the DB with `db.open_db(db_path)` (same as `survey`; the connection is not used for writes)." Do not assert it is read-only.

**Minor-2: Phase 3 `ScanContext` frozen dataclass change burden not flagged**
- **Issue:** `phase_03.md` Task 3 adds `resurrect_dir: Path` to `ScanContext` (frozen dataclass). The implementation note says to "update all constructions in tests via the fixture/`make_full_fixture` default to a non-existent temp dir". However, `make_full_fixture` does not construct `ScanContext` — it returns `(db_dir, run_dir, projects_root)`. Test files that construct `ScanContext` directly (e.g. `test_scan.py`) must all be updated. The plan's mitigation language ("via the fixture") is imprecise and may mislead an implementer into thinking no test edits are needed.
- **Location:** `phase_03.md` Task 3, implementation note for ScanContext
- **Fix:** Restate as: "Update every `ScanContext(...)` construction in `test_scan.py` to add `resurrect_dir=tmp_path / 'empty-resurrect'` (a non-existent dir). Count the constructions and confirm each is updated before committing."

**Minor-3: Phase 4 header UUID placement ambiguity vs AC5.2**
- **Issue:** Phase 4's render overhaul changes the entry header to `**{pane_title or cwd_basename}**` followed by `\`claudew --resume {uuid_full}\`` on the next line. AC5.2 states "Row header uses full UUID." Under the new format, the UUID appears in the resume command line, not in the bold header label. Whether this satisfies "row header uses full UUID" depends on interpretation of "header." The UUID is visually prominent and present, but the bold label no longer contains it.
- **Location:** `phase_04.md` Task 4 render entry format; design AC5.2
- **Fix:** Clarify in Phase 4 Task 4 that AC5.2 is satisfied by the UUID appearing in the `claudew --resume` line (the primary action line of the entry), not necessarily in the bold display label.

---

## Technical Correctness Verified

- **/proc/stat field-22 parse:** `rpartition(')')` in Python yields `after.split()[19]` for `start_time`. Bash `${stat##*) }` + `set -- $rest` yields `${20}`. Both correct. ✓
- **Resurrect pane field indices:** Verified against real `~/.byobu-sessions/tmux_resurrect_20260612T182057.txt`. [6]=window_title, [7]=`:path` (strip `:`), [9]=shell command. Matches plan exactly. ✓
- **Glyph volatility confirmed:** Real snapshot shows braille spinner glyphs (`:##`) in field [4] and spinner glyphs in field [6] titles, not `✳`. The `✳` prefix is the idle/saved state; active panes show spinners. Plan's warning is accurate. `label_for_cwd`'s `✳`-preference heuristic will return any matching-cwd title when none has `✳` (fallback is correct). ✓
- **Phase 4 graceful-degradation SELECT:** Current `render()` hard-codes a 7-column query with no PRAGMA defense. Plan's addition of PRAGMA table_info guard is necessary and correct. ✓
- **IDLE_LIVE_KILLED rename:** Verified in `render.py` `SectionKey` enum and `_section_for_row`. Reason-partition test in `test_render.py` keys on `reason` strings (not `SectionKey`), so the rename does not break it. `_EXPECTED_SECTIONS` dict hardcodes `SectionKey.IDLE_LIVE_KILLED` — Phase 4 must update this dict entry to `SectionKey.PROBABLE_CRASH_VICTIMS`, or the `test_section_assignment_for_every_phase_2_reason` parametrised test will fail. The plan does not explicitly call this out.
- **Fixture signatures:** `make_full_fixture` and `make_db_with_sessions` confirmed present in `jsonl_builder.py`. `make_liveness_file` lacks `session_id`/`start_time` params (Phase 2 adds them). `DbFixtureRow` lacks `pane_title`/`last_substantive` fields (Phase 4 adds them). All absences are expected and planned. ✓

---

## Additional Note: test_render.py _EXPECTED_SECTIONS dict

`test_render.py` line 428 hardcodes `SectionKey.IDLE_LIVE_KILLED` as the expected section for `hard_crash` rows. Phase 4's rename to `PROBABLE_CRASH_VICTIMS` will break this test unless Phase 4 Task 4 explicitly updates `_EXPECTED_SECTIONS`. The snapshot fixtures (`expected_mixed.md`) will also break because the section heading changes from `## Idle-live killed` to `## Probable crash victims`. Phase 4 plans to update render tests and snapshot files — but the plan should explicitly call out `_EXPECTED_SECTIONS` and the `assert "## Recently concluded" in actual` style assertions that pin section names.

This is not a gap in functionality but a predictable test-break if the implementer misses it. Recommend adding to Phase 4 Task 4: "Update `_EXPECTED_SECTIONS` in `test_render.py` and regenerate/rewrite snapshot files under `tests/fixtures/snapshots/`."

---

## Decision: APPROVED FOR MERGE (with Important notes requiring attention before Phase 2 and 3 implementation starts)

The five plans cover all nine acceptance criteria. Symbol names, field indices, and algorithmic claims are technically correct. The three Important findings are documentation misalignments that will cause implementer confusion if unaddressed; they do not block plan approval but should be corrected before the affected phases are handed to an implementer.
