# Coherence Review: Phase 1 — Stage-1 cwd forward-scan + dedup-safe scan

Reviewer: claude-opus-4-8 (coherence-reviewer)
Date: 2026-06-14
Phase file: `docs/implementation-plans/2026-06-12-crash-detection/phase_01.md`
Design plan: `docs/design-plans/2026-06-12-crash-detection.md`
Diff range: `0b1642e..49bd184`

Inputs read: design plan (incl. DR1-DR9, ACs, DoD), phase_01.md, the full source diff (`jsonl.py`, `scan.py`, `correlate.py`), the test diff (`jsonl_builder.py`, `test_jsonl_tail.py`, `test_scan.py`, `test_correlate.py`), `test-requirements.md`, `proleptic-challenge-phase-1.md`, `db.py` (schema), and both arch docs (`0-context.md`, `database.md`). Suite run once: 194 passed.

The range `0b1642e..49bd184` is consistent with the proleptic file's challenged range (`0b1642e..a00bfa7`): `49bd184` adds only the proleptic-disposition doc on top of `a00bfa7`. No source changed between them.

---

## Conformance

The implementation conforms to the design's architectural intent. Specific positives, stated explicitly because they are the strongest conformance evidence:

- **FCIS split preserved (DR3, Existing Patterns).** `first_record_field` in `jsonl.py` is a pure, side-effect-free reader (opens a file, returns a value or `None`, never raises, never writes). `scan._first_entry_cwd` and both `correlate` helpers now delegate to it. No DB I/O moved into the pure layer. The shared helper is the single cwd/timestamp extraction point the design called for — the two prior line-1 reads are gone, eliminating the drift risk DR3 named.
- **The correlation join is the fix, not the classifier (DR1).** `classify.py` is untouched in the diff (diff stat shows no `classify.py` change). The forward scan changes classifier *inputs* (`cwd_present`, the correlation result), exactly as DR6 specified — RULES table unchanged, no `CLASSIFIER_VERSION` bump. This is the central architectural claim of the design and the implementation honours it precisely.
- **Dedup confined to `_walk_sessions` (Phase 1 plan, DR5).** `run_scan` and `scan_db` are unchanged; `live_pids` (run_scan.py:418) derives from the already-deduped `facts` list, so `seen_uuids`, `classifications`, and `live_pids` all consume the deduped output. The change is exactly where the plan said to put it.

No erosion found. No drift between design naming and code naming (the helper is named and located as DR3 specified).

## Traceability

Decision → code → test → doc chain for the Phase 1 ACs:

| AC | Code | Test (guards reversal?) | Doc |
|----|------|--------------------------|-----|
| AC2.1 (later-line cwd extracted) | `jsonl.first_record_field`; `scan._first_entry_cwd` | `test_first_record_field_cwd_on_line2_snapshot_prefixed`, `test_scan_classifies_snapshot_prefixed_jsonl_not_missing_cwd` — yes, asserts not-`missing_cwd` + real cwd | `0-context.md` line 40 (present-tense, accurate post-Phase-1) |
| AC2.2 (later-line `.live` correlates) | `correlate._cwd_matches_any_jsonl_in`, `_jsonl_first_entry_ts_meets_threshold` | `test_correlate_direct_match_when_cwd_on_later_line`, `test_correlate_mtime_match_when_timestamp_on_later_line`, `test_project_dir_for_cwd_finds_match_when_cwd_on_later_line` — yes | `0-context.md` line 56 (labelled "planned" — see Arch Doc Updates) |
| AC2.3 (genuine no-cwd preserved) | `first_record_field` returns `None` → `_first_entry_cwd` returns `""` | `test_first_record_field_returns_none_when_no_cwd_anywhere`, `test_scan_genuine_no_cwd_jsonl_still_classifies_missing_cwd` — yes | n/a |
| AC3.1 (two markers → one UUID, no IntegrityError) | `_walk_sessions` dedup dict | `test_scan_dedup_two_markers_same_uuid_no_integrity_error` — yes, asserts exactly 1 sessions row + 1 history row | **gap — see below** |
| AC3.2 (direct-match beats ambiguous) | `_RANK` ordering + `_consider` | `test_scan_dedup_direct_match_wins_over_ambiguous` — yes, asserts `classification=="hard_crash"` and the exact reason | as AC3.1 |
| AC1.1 (capstone: snapshot-prefixed victim → hard_crash) | full chain | `test_snapshot_prefixed_crash_victim_surfaces_as_hard_crash` — yes | n/a |

Every Phase 1 AC has code and a test that would break if the decision were reversed. One doc gap (DR5's dedup invariant — below).

**Candidate fitness function / test requirement (not a recurring review item):** The same-rank tie-break correctness property (F1 below) is automatable and *should be a test*, not a standing review concern. `test-requirements.md` already maps AC3.x; if the human chooses to make the tie-break liveness-aware, add a row asserting "alive DIRECT marker wins over dead DIRECT marker for the same UUID." The existing CA3 test asserts order-independence only and must not be mistaken for that guard.

## Baked-In Assumptions

**BA1 — `_FIRST_FIELD_SCAN_LIMIT = 50` (rating: notable).**
- **Design said:** "bounded forward scan" with no numeric bound (DR3, glossary). Silent on the value.
- **Implementation chose:** 50, calibrated against the operator's 7683 real transcripts (p99 first-cwd index = 4, max = 9). Comment upgraded from assertion to measured evidence (proleptic CA2, commit `a00bfa7`).
- **Forward impact:** Bounds the scan to the operator's observed transcript shape. DR3's own reevaluation trigger names the failure mode ("transcripts grow a deep prefix of non-`cwd` records beyond the scan bound"). On a deeper-prefix transcript, `first_record_field` silently returns `None` → `missing_cwd` reintroduced silently. ~5x headroom over the measured max makes this low-likelihood for this operator; the assumption is the operator's machine is representative. Surfaced for the human to confirm; not a defect.

**BA2 — dedup precedence rank and same-rank tie-break key (rating: concerning — see F1).**
- **Design said:** "exact > window > ambiguous-candidate; tie-broken by sorted liveness path" (Architecture / Phase 1 plan).
- **Implementation chose:** `_RANK = {DIRECT:0, MTIME:1, AMBIGUOUS:2}`, tie-break on `(rank, liveness_path_str)`. Faithful to the literal design text.
- **Forward impact:** the tie-break is liveness-blind. The design *itself* specified "sorted liveness path" as the tie-break, so the implementation conforms — but the design's choice bakes in "path order decides the winner among same-rank facts," which is wrong when same-rank facts disagree on liveness. This is the F1 finding: the assumption is in the design and was implemented faithfully, which is exactly why it needs surfacing now rather than being treated as an implementation slip.

**BA3 — `errors="replace"` on the forward read (rating: benign).**
- **Design said:** silent on decode-error handling.
- **Implementation chose:** `open(..., errors="replace")`, consistent with the existing lossy-encoding rationale already documented in `_cwd_matches_any_jsonl_in`. Reasonable default; no downstream impact.

## Forward Fitness

**Supports Phases 2-5 as a floor, with one carried risk.**

- **Phase 2 (session_id + start_time stamps, exact-id correlation).** The shared `first_record_field` and the dedup dict are the substrate Phase 2 extends. **Carried risk:** Phase 2 makes *fresh* sessions' markers DIRECT (via `session_id`), so a resumed session and its origin marker become a rank-0 DIRECT tie *without* needing chain-resume. Phase 2 **widens** the F1 same-rank-tie surface. The right time to decide the tie-break policy is before Phase 2 builds on it.
- **Phase 3 (tight-window correlation).** `_jsonl_first_entry_ts_meets_threshold` now reads the first *real* timestamp via the forward scan, not line 1. This is the correct input for Phase 3's `[started, started+Δ]` band — a snapshot-record line-1 read would have fed Phase 3 a wrong or missing first-entry-ts. Forward-cwd sets up Phase 3's tight-window correlation correctly.
- **Phase 4 (render + byte-identical).** **Be precise:** Phase 1's order-independent dedup delivers *identical filesystem state → identical DB content* (the dedup is path-deterministic, verified by the CA3 order-independence test). AC5.3's guarantee is *identical DB → identical render output*, owned by Phase 4's pure `render()`. Phase 1 is a **necessary precondition** for the end-to-end byte-identical property, not the guarantee itself. The dedup's order-independence does underwrite the DB-determinism half; it does not by itself "underwrite byte-identical render."
- **Phase 5 (reaping).** Out of scope for Phase 1, but note: reaping does not exist until Phase 5, so dead markers **accumulate** through Phases 1-4. That accumulation is what makes F1's same-rank dead+alive collision a normal state, not an edge case, during the interim.

**What a hostile reviewer would flag:** the CA3 regression test (`test_scan_dedup_same_rank_tie_break_order_independent`) constructs the exact dead-marker + alive-marker same-UUID collision and asserts only `results[0] == results[1]` — order-stability. It is green whether the persisted classification is `hard_crash` (dead path sorts first) or `live` (alive path sorts first). It locks in "winner = path lexicography, liveness ignored" as the contract. That is the gap below.

## Situated Accountability

This check applies: Phase 1 encodes a domain assumption about transcript shape (the snapshot-prefix model) and a tie-break policy that decides which of two conflicting facts about a session "wins."

- **Whose perspective shaped these decisions:** the single operator's own machine. `_FIRST_FIELD_SCAN_LIMIT=50` is calibrated to *this operator's* 7683 transcripts (p99=4, max=9) — one configuration's notion of a normal prefix depth. The dedup precedence ("direct beats ambiguous") is correct for the operator's goal of surfacing crash victims. For a single-operator, single-machine tool this is appropriate and the design says so (Additional Considerations: "live fixtures," operator binding).
- **Who benefits:** the operator, who gets victims surfaced and 1013 false `missing_cwd` cleared.
- **Who bears costs / what's absent:** future format drift (DR3's reevaluation trigger) and any other machine whose transcripts carry a deeper non-cwd prefix — the limit was set from one machine's distribution, and the failure mode (silent `missing_cwd`) is invisible. The same-rank tie-break's liveness-blindness means a *live* session can be reported as a crash victim — the cost lands on the operator's trust in the "## Probable system-crash victims" section the moment a chain-resumed live session appears there. No perspective in the design weighs "false-positive crash victim" against "order-independence"; the design optimised for the latter and did not name the former.

## Architecture Doc Updates

Both arch docs were refreshed on 2026-06-12 (design time), pre-staging the forward-scan description ahead of implementation. They are now mostly accurate, with two items:

1. **`0-context.md` line 40 — already accurate, leave as-is.** "the `cwd` (via a bounded forward scan to the first record carrying it — transcripts now open with a snapshot record, so line 1 alone is insufficient...)" — this is present-tense and is now true after Phase 1. No change needed.

2. **`0-context.md` line 56 — "(planned)" qualifier, partial update warranted (Medium).** The line bundles Stage-1 and Stage-2 under "(planned)" and says the join "Repairs the line-1-only cwd read." After Phase 1 the *forward-cwd read itself* is shipped (the literal repair of the line-1 read is done); Stage-1 *exact-id* correlation is Phase 2 and Stage-2 is Phase 3. Recommend splitting the status so the shipped forward-scan repair is not labelled "planned" alongside the genuinely-future exact-id/Stage-2 work. Defer to the human; this is a precision nit, not erosion.

3. **`database.md` — DR5 dedup invariant is undocumented (Medium, traceability gap).** `database.md` documents the `(uuid, scan_id)` PRIMARY KEY (lines 50, 108) but not the new scan-level invariant DR5 introduced: *a single scan never writes two facts for one UUID*. This is the one Phase 1 structural decision the pre-staged docs did not cover. By the traceability rubric (code + test, no doc → erodes silently), recommend adding a short note to `database.md` (near the `classification_history` PK or the write-flow section) stating that `scan._walk_sessions` deduplicates facts by UUID before the write loop so the composite PK is never violated within one scan, with the precedence rule. Draft target: `database.md` § "classification_history" or § write-flow. Recommend; do not write it for them.

Note for accuracy: `database.md`'s "Phase 4 `_write_scan_run`" and "Phase 6 `prune`" references use the **parent** crash-recovery plan's phase numbering, not this crash-detection plan's. Not Phase 1 drift; do not mis-attribute.

## Findings Summary

### High (count: 0)

None that hard-block. F1 (below) is rated Medium-leaning-High; it does not block because Phase 1 meets its stated ACs (AC3.2 = direct-beats-ambiguous works), but it must be a human decision before Phase 2.

### Medium (count: 3)

- **F1 — same-rank dedup tie-break is liveness-blind; a live session can persist as `hard_crash`.** `_consider` compares `(rank, liveness_path_str)` with no liveness term. Two rank-0 DIRECT_MATCH facts for one UUID with conflicting liveness (a dead crash marker + a live resumed-session marker, both `--resume <same-uuid>`, both boot-current) are decided by path lexicography, not by which is alive. Reachable now: chain-resume leaves the prior crash marker in `run/`, and reaping is Phase 5, so dead markers accumulate through Phases 1-4. Phase 2's `session_id` stamping widens this (fresh markers become DIRECT too). The CA3 regression test constructs exactly this collision but asserts only order-stability, so "dead-wins-if-path-sorts-first" is locked in green. The design *specified* "tie-broken by sorted liveness path," so the implementation conforms — the assumption lives in the design. **Action:** present to the human. Options: (a) accept and document that same-rank ties are path-decided (the operator must know a chain-resumed live session can show under "Probable system-crash victims"); or (b) add a liveness/recency-preferring term to the tie-break key before `liveness_path_str`, and strengthen the CA3 test to assert the alive marker wins. Surfacing and rating only — not fixing.
- **F2 — DR5 dedup invariant has code + test but no architecture-doc reflection.** See Arch Doc Updates item 3. Recommend a `database.md` note.
- **F3 — `0-context.md` line 56 labels the shipped forward-scan repair "(planned)".** See Arch Doc Updates item 2. Recommend splitting shipped-vs-future status.

### Low (count: 2)

- **F4 — PRIMARY KEY described as "UNIQUE constraint" throughout the design, phase plan, and test docstrings.** The schema (`db.py:80`) is `PRIMARY KEY (uuid, scan_id)`, not a named `UNIQUE` constraint. Functionally identical in SQLite (composite PK enforces uniqueness, duplicate insert raises `IntegrityError`), so the dedup rationale is sound — but the terminology names a constraint type the schema does not literally declare, and the drift propagated into test docstrings (`test_scan_dedup_two_markers_same_uuid_no_integrity_error` says "UNIQUE constraint"). Cosmetic; note for completeness.
- **F5 — `_FIRST_FIELD_SCAN_LIMIT=50` calibrated to one machine (BA1).** Surfaced under Baked-In Assumptions and Situated Accountability. Low because the headroom is ~5x the measured max and DR3 already names the reevaluation trigger; recorded so a future format-drift regression has a paper trail.

## Overall Assessment

**Coheres, with one noted assumption requiring a human decision before Phase 2.**

Phase 1's implementation faithfully realises the design's central architectural intent: it repairs the `.live`→JSONL correlation join at the root (the line-1 cwd read), via one shared pure helper, leaving `classify.py`'s RULES table untouched (DR1, DR3, DR6), and it closes the dedup-triggered `triage` crash (DR5) confined to `_walk_sessions`. Every Phase 1 AC traces to code and to a test that would break if the decision reversed. The suite is 194 green.

The one finding that must not be filed away is **F1**: the same-rank dedup tie-break is liveness-blind, the gap is reachable in the current (pre-reaping) state, Phase 2 widens it, and the existing regression test masks it by asserting order-independence rather than correct-winner. The verdict is "Coheres" **only if** the human, going into Phase 2, either accepts the path-decided same-rank tie-break (and the chance of a live session appearing as a crash victim) or chooses to make the tie-break liveness-aware first. F2/F3 are doc-reflection recommendations; F4/F5 are noted for completeness.
