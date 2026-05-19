# Code Review Findings — phase-7

## Status: APPROVED — minor issues noted

**Critical: 0 | Important: 1 | Minor: 2**

## Verification

```
Tests: uv run pytest -q → 782 passed in 3.24s
Bats:  bats tests/test_crash_recovery_smoke.bats → 6/6 ok
Lint:  ruff not resolvable in this environment (rtk proxy and python module both failed); no Python changed in this diff — not a blocker
```

## Plan Alignment

- Task 1 (SKILL.md): ✓ implemented. Frontmatter, all required sections, `last-reviewed`, `user-invocable`, description ≤200 chars (163), leads with "Use when".
- Task 1 deviation (description text): ✓ justified. Plan's example description contained a three-item parenthetical (`crashed, killed, idle-disconnected`) that would have failed `test_no_parenthetical_enumeration`. Implementor wrote a compliant alternative preserving intent. 7 QA tests pass.
- Task 2 (README): ✓ implemented. All six required sections present. 104 lines, within ≤120 cap. `denubis-plan-and-execute` dependency documented. `<PHASE-8-VERSION>` placeholder present. AC5.6 and AC6.4 UAT runbooks present.
- Task 2 deviation (dependency text): ~ deviated, partially problematic — see Important finding below.
- Task 3 (bats smoke test): ✓ implemented verbatim from plan spec. All 6 tests pass.
- Interlude commit (6639b76): ✓ justified. Captures a real structural gap (classifier cannot produce `hard_crash` without liveness files) surfaced during dogfood. Defers implementation appropriately. Phase 8 amendment is correctly scoped — it adds an honesty-pass instruction and a "do not implement this in Phase 8" guard without expanding Phase 8 scope.
- AC1.2: ✓ verified by marketplace.json bats test.
- AC8.1: ✓ dependency documented with version placeholder.

## Issues

### Important (count: 1)

- **Issue**: The README Dependency section (and the SKILL.md Integration section) both state "every session will be classified `concluded`" when the liveness wrapper is absent. This is false. Without liveness files, `liveness_present=False` rules produce `CONCLUDED` for `TailKind.CONCLUDED` and `BORDERLINE` for dangling tool-use, dangling ask-question, and dangling agent-dispatch tails (`classify.py:173–195`). `BORDERLINE` maps to "Needs investigation" and "Ambiguous correlation" render sections, not to "Recently concluded". Users reading the README will believe the tool is useless without the wrapper; the real picture is that it degrades to borderline-only signal (which the dogfood proved has value — five crashed sessions appeared in "Needs investigation" as `unknown_tail_kind`).
- **Location**: `plugins/denubis-crash-recovery/README.md:25–27` (diff hunk +25 to +27); `plugins/denubis-crash-recovery/skills/triage/SKILL.md:99` (Integration section).
- **Fix**: This is flagged for Phase 8's honesty pass (phase_08.md:550). The Phase 8 amendment correctly identifies the problem and instructs Phase 8 to correct it. No fix needed in Phase 7 — the design seed and the phase_08.md amendment are the right mechanism. However, the Phase 8 instruction (line 550) quotes only the old "degrades to JSONL-tail-only heuristics" wording as the thing to fix; it should also call out the "every session will be classified `concluded`" claim as incorrect, since that wording appears in both the Phase 7 README diff and the SKILL.md Integration section. The Phase 8 implementor needs to know about both instances.

  Suggested amendment to phase_08.md line 550: add "The Phase 7 README also adds 'every session will be classified `concluded`' — this is wrong; BORDERLINE classifications still fire. Fix both claims and update SKILL.md Integration section in the same pass."

### Minor (count: 2)

- **Issue**: The bats `CR` variable uses a relative path (`plugins/denubis-crash-recovery/scripts/crash_recovery`). Bats runs each test from the directory where `bats` is invoked. If the suite is ever run as `bats tests/test_crash_recovery_smoke.bats` from a directory other than the repo root, `CR` will fail with "No such file or directory". Other bats tests in this repo (`test_dispatcher.bats`, `test_rtk_rewrite.bats`) do not exhibit this pattern — they don't use `uv run --project` at all. The plan spec shows the same relative path, so this is faithfully implemented, but it introduces a latent fragility.
- **Location**: `tests/test_crash_recovery_smoke.bats:21`
- **Fix**: Use `BATS_TEST_DIRNAME` to anchor the project path: `CR="uv run --project ${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"`. This is robust regardless of invocation directory. Low urgency — tests currently pass from repo root, which is the documented invocation.

---

- **Issue**: The SKILL.md Step 2 annotation loop iterates "Ambiguous correlation, then Needs investigation, then Idle-live killed" rows, but SKILL.md Step 1 notes the report renders sections in the fixed order: "Currently unfinished, Idle-live killed, Ambiguous correlation, Needs investigation, Recently concluded, Irrecoverable". The annotation iteration order (Ambiguous → Needs investigation → Idle-live killed) is different from the render order (Idle-live killed → Ambiguous → Needs investigation). This is intentional per the plan (plan line 62: "Ambiguous correlation, then Needs investigation, then Idle-live killed"), but it is undocumented and could confuse an implementor who assumes the annotation loop mirrors the render order. The rationale (surfacing higher-confidence borderlines first) is implicit.
- **Location**: `plugins/denubis-crash-recovery/skills/triage/SKILL.md:39–42`
- **Fix**: Add a parenthetical: "Iterate in this order — higher-confidence borderlines first, regardless of render section order." Prevents future implementors from silently reordering to match the render.

## Decision: APPROVED FOR MERGE

All three planned tasks are implemented and verified. The interlude commit is well-reasoned and correctly scoped. The Important finding is a documentation accuracy issue already flagged and routed to Phase 8 — the phase_08.md amendment needs one additional sentence to ensure Phase 8 catches both instances. The two Minor findings are low urgency and do not block merge.

**Action required before Phase 8 merge:** extend phase_08.md line 550's honesty-pass instruction to explicitly cover (a) the "every session will be classified `concluded`" claim in the README and (b) the same claim in SKILL.md Integration section.
