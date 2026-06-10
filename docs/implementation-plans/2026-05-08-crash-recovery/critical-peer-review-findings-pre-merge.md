# Critical Peer Review Findings — pre-merge

**Reviewer:** critical-peer-review (claude-opus-4-7[1m])
**Date:** 2026-05-21
**SHA range:** `deaf92a..2b8e6a7` (pre-fix), `cd2d8d7` (post-fix)
**Artifact classification:** implementation-plan (with code, architecture docs, audit trail)
**Verdict:** APPROVED-FOR-MERGE

This is a separate review from `critical-peer-review-findings.md` (2026-05-14, design-plan critical review). The 2026-05-14 review audited the implementation plan before execution. This 2026-05-21 review audits the completed 8-phase artifact at pre-merge time.

## Scope reviewed

- Design plan + 8 phase files + test-requirements + uat-requirements
- All audit-trail review files (per-phase × 8 + coherence × 2 + stage-2 + design-phase critical review)
- Architecture docs: constraints.md, database.md, glossary.md, 0-context.md, ADRs 0001 + 0002
- Post-mortem report: `docs/design-plans/post-mortem-crash-report-2026-05-20.md`
- Test plan: `docs/test-plans/2026-05-08-crash-recovery.md`
- Source code: `plugins/denubis-crash-recovery/` + `plugins/denubis-plan-and-execute/hooks/`

## Hidden assumptions audit (8 assumptions, all Verified or low-risk)

A1–A8 reviewed. Key verifications:
- A4/A5 (`set -e` exit-code capture per ADR 0001): verified via direct shell probes (`/tmp/setexp.sh`, `/tmp/setexp2.sh`). ADR 0001 fix is correct.
- A7 (5-file fsync cluster causally tied to crash): rated **Plausible**, not Demonstrated — the post-mortem report's discriminating evidence is actually E5 (PID cross-check), not the cluster signature. See Minor-5.

## ACH matrix — post-mortem report's HIGH conclusion

Built a 4-hypothesis × 5-evidence matrix testing whether H1 (15:14:38 crash killed 4+ sessions) is the only hypothesis without strong contradicting evidence. Confirmed: H1 is the only one with no strong `−` marks. H2 (scheduled syncfs, sessions idle) is falsified by E4 (mid_tool_call tails — idle processes wouldn't be writing tool_uses) and E5 (no post-reboot PIDs — sessions would still be running). H3/H4 (graceful shutdown variants) falsified by E1.

**Critical analytic finding (informs Minor-5):** The report frames the cluster signature as load-bearing in "Why HIGH" rationales, but E2 (cluster) has likelihood ratio ~1:1 between H1 and H2. The actually-diagnostic evidence is E4 + E5.

## Findings

### High / Important: 0

### Minor: 5 (all doc-hygiene, all fixed in `cd2d8d7`)

| # | Finding | Resolution |
|---|---------|-----------|
| Minor-1 | "11 tests" stale claim in 4 docs after M3+M4 brought count to 13 (bats `@test` count verified). Affected: constraints.md:70, ADR 0002:75, stage-2-conformance:130 + :290 | Fixed (`cd2d8d7`): constraints.md changed to "Every test"; other three sites updated to "13 tests". `grep -rn "11 tests"` returns 0 matches. |
| Minor-2 | Post-mortem `5.4–6.0 s before boundary` doesn't match cited data (actual: 5.030–5.041 s). Conclusion unaffected, label internally inconsistent | Fixed (`cd2d8d7`): "5.4–6.0 s" → "approximately 5.0 s". |
| Minor-3 | `_REAL_TYPES = frozenset({"assistant", "user"})` is structurally an allow-list but described as a "deny-list" in jsonl.py:36-58 comment, jsonl.py:57 warning, and constraints.md row. The "Do NOT revert to an allow-list" warning is backwards. Future-maintainer trap | Fixed (`cd2d8d7`): allow-list framing propagated through jsonl.py comment + line-58 warning + constraints.md row. |
| Minor-4 | Stale "bookkeeping deny-list" name in constraints.md historical row (line 88) after Stage 2 M4 renamed the constraint | Fixed (`cd2d8d7`): historical row title aligned with renamed constraint ("JSONL-type allow-list"). User explicitly authorised overriding historical-row-immutability policy for this case. |
| Minor-5 | Post-mortem "Why HIGH" rationales lead with cluster signature (non-diagnostic; LR~1:1) instead of mid_tool_call tail + PID cross-check (diagnostic; falsifies H2). Conclusion correct; framing would mislead future falsification attempts | Fixed (`cd2d8d7`): all four HIGH entries reframed to lead with diagnostic evidence; cluster signature retained as "discovery anchor" framing. Bug-fixer made one judgement call: used "confirmed dead in post-reboot ps cross-check" rather than template's per-UUID phrasing because the actual check is a single global cross-check, not per-UUID lookup — preserves accuracy over template fidelity. |

## Flagged (reviewer interrogated, found no false-world-model issues)

- **"All phases passed first or second review" pattern:** spot-checked phase-1 and phase-8 findings against actual diffs. Both substantive. Plan-validation review + 2026-05-14 critical-peer-review caught 5 Critical + 6 Medium + 5 Low pre-implementation — review topology was working, not rubber-stamping.
- **UAT reframing (Phase 8 routing AC5.6 + AC6.4 to coherence + live-operation):** honest. The original AC acceptance thresholds are literal-output-match (mechanical, not judgement). Constraint row "AC5.6 / AC6.4 UAT deferral to live operation" makes the deferral explicit; two real-crash empirical events (2026-05-18 + 2026-05-20) provide non-tautological evidence. Phase 7 prune-prompt clarity UAT (genuinely subjective) remained on UAT track.

## What the prior reviews appear to have missed

All five Minor findings above were missed by the prior review chain (per-phase × 8 + coherence × 2 + stage-2 + DBA + pre-merge code review + test-analyst). Likely causes:
1. Minor-1: reviewers checked content, not numeric labels
2. Minor-3: terminology vs operational-meaning mismatch requires reading code-comment + constraint-row + implementation together
3. Minor-2 + Minor-5: post-mortem report committed without going through any review pass before merge

The pattern is not a defect in the review topology — it's the natural ceiling of agent-based review at this scope (84 files, +17K LOC). The fixes are documentation hygiene, not code defects.

## What could not be verified

1. Two simultaneous wrappers from different worktrees under all init systems (only bash setup exercised)
2. `last -F` output authenticity in post-mortem report (no access to original)
3. 2026-05-18 design-seed cluster timestamps (no access to original)
4. `boot_id=unknown` fallback path reachability (no /proc-unreadable test environment)
5. Every per-phase reviewer's actual falsification rigor (2 of 8 spot-checked; 6 of 8 not exhaustively audited — audit-trail file sizes consistent with substantive engagement)

## Pre-mortem (3 alternative failure scenarios examined)

1. Bats test passes but verifies wrong thing — falsified by reading `claude-wrapper.sh:94-101` (file written BEFORE claude invocation; test verifies pre-kill existence)
2. 8 phase reviews approve a structural defect that no cross-cutting reviewer catches — Stage 2's M3 finding (which now has a fitness test) and the M3 bats test added in `6f9ada0` close the most likely candidate (write-side / read-side format-skew)
3. Post-mortem HIGH attributions wrong because benign cause also produces cluster at boundary − 5s — falsified by E5 (no post-reboot PIDs)

## Overall verdict

**APPROVED-FOR-MERGE.** Implementation honors every DR (1-10) and AC (1.1-8.3) with code + test + doc traceability. All test suites pass (800 pytest + 94 bats). Two known plan defects captured as ADRs 0001 + 0002 with paired constraint rows. Post-mortem HIGH conclusion supported by diagnostic evidence even with framing defect (fixed). Structural gap in `classify.py::RULES` honestly disclosed in README + SKILL + design seed + constraint row. Retroactive recovery explicitly out of scope and verified not accidentally implemented. CHANGELOG honestly calls out transcript-archive gate as behaviour change.

**No findings block merge.** The 5 Minor doc-hygiene findings are resolved in `cd2d8d7`.
