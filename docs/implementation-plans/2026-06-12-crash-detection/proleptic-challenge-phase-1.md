# Proleptic Challenge — Phase 1 (crash-detection)

**Trigger:** Phase transition — code review passed (APPROVED, 0C/0I/3 Minor, all fixed at `60629aa`), entering the coherence gate.
**Range challenged:** `0b1642e..a00bfa7` (branch `crash-detection`).
**Disposition decided with the operator:** "Close both [actionable gaps] now."

The challenger raised four counterarguments. Two were closed with code/tests; two are honest deferrals already owned by later phases / the design.

## CA1 — "complete and correct" overclaims the backlog payoff *(accepted; reframed)*

The capstone test (`test_snapshot_prefixed_crash_victim_surfaces_as_hard_crash`) drives a `--resume <uuid>` marker — the **DIRECT_MATCH** path. The measured backlog (33/36 `.live` → `no_match`) is **id-less** and takes the mtime path; in a busy directory it now resolves to `borderline/ambiguous_match`, not `hard_crash`.

**Disposition:** Not a Phase 1 defect — Phase 1 meets its ACs (AC1.1 is the DIRECT path; Stage-2 disambiguation is Phase 3). What Phase 1 *does* deliver to the backlog: the 1013 false `irrecoverable/missing_cwd` mislabels are fixed; the `triage` dedup crash is closed; victims surface as `hard_crash` for direct-match and *unambiguous* id-less markers. Busy-dir ambiguous victims need Phase 3 (tmux-resurrect corroboration). The design's Additional Considerations already hedges this ("does not promise a victim count"). Recorded here so the framing is honest going into the gate.

## CA2 — `_FIRST_FIELD_SCAN_LIMIT=50` was asserted, not measured *(closed)*

Risk: if any real transcript carries 50+ parseable records before the first `cwd`, `first_record_field` returns `None` → `missing_cwd` silently reintroduced.

**Settled empirically (read-only pass over real `~/.claude/projects`):** 7767 files, 7683 with a cwd; first-cwd record index min=1, median=1, p95=2, p99=4, **max=9**; **0 files** with first-cwd index > 50. 50 is ~5× the observed worst case. Comment upgraded from assertion to measured evidence (`a00bfa7`). No code/limit change needed.

## CA3 — same-rank dedup tie-break was untested; order-independence unverified *(closed)*

The AC3.1/AC3.2 tests only collide DIRECT_MATCH (rank 0) vs AMBIGUOUS (rank 2), so `(rank, path) < existing[:2]` never executed on equal ranks. Order-independence is load-bearing for Phase 4's byte-identical render.

**Closed (`4638c37`):** new `test_scan_dedup_same_rank_tie_break_order_independent` collides two DIRECT_MATCH markers on one UUID (rank-0 vs rank-0) with different standalone outcomes, runs both `list_liveness_files` iteration orders on fresh DBs, and asserts identical persisted classification. Passes — the tie-break is path-deterministic, not insertion-order-dependent.

## CA4 — some previously-`concluded` id-less sessions now flip to `borderline` *(accepted; deferred to Phase 3)*

Before Phase 1 an id-less marker whose cwd was unread returned `NO_MATCH`; its UUID then classified via the JSONL-only walk (e.g. `concluded`). After the cwd fix the marker correlates to a multi-candidate set → `AMBIGUOUS` → `borderline/ambiguous_match`. No UUID is dropped; the losing fact's classification accuracy degrades until Phase 3 corroborates (design-acknowledged, AC6.3).

**Disposition:** deferral by design, not a Phase 1 gap. Named here so the coherence review and the Phase 4 UAT judge it with eyes open.

---

**Outcome:** CA2 + CA3 closed in-branch; CA1 + CA4 recorded as design-owned deferrals. Suite 194 green. Proleptic gate satisfied → coherence review.
