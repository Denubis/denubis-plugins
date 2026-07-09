# Code Review Findings — phase-2.6

# Code Review: Phase 2.6 — Minor-Finding Fixes (writing-claude-directives)

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

Re-review of commit `43778b9` against base `93d572d`. Scope: markdown skill files + audit
docs only (no runtime code). FCIS, type-safety, error-handling, injection, and
test-coverage gates are N/A. This cycle verifies the two prior Minor findings are
resolved and surfaces any new issues introduced by the fixes.

## Verification
```
Tests: uv run pytest -q → 867 passed in 3.12s (includes skill-lint over SKILL.md)
Lint:  skill-lint is part of the pytest suite → passed
SKILL.md line count: 289 (limit < 300) ✓
model-tier-notes.md line count: 105
Phase 2 artefacts (phase_02_red_evidence.md, phase_02_green_verification.md): NOT modified ✓
Era-claim / benchmark scan (4.x, 4.1-era, SWE-bench, %-on, benchmark): no hits ✓ (AC2.6.8)
Fable cost gate: verbatim at model-tier-notes.md:25 and :97 ✓
Haiku-no-judgement: intact at model-tier-notes.md:85, routes to Sonnet 4.6 / Opus 4.8 ✓
```

## Prior Findings Verification

- **Prior Minor 1 (undated/uncited overengineering claim + dangling cross-reference)** — **Resolved.**
  - `SKILL.md:225` now reads: "Current Opus 4.8 and Fable 5 models tend to overengineer — adding files, abstractions, or unrequested tidying, especially at higher effort (verified 2026-06-10; per-model specifics in `model-tier-notes.md` → Cross-model patterns)". The claim now names the models explicitly, carries an inline `verified 2026-06-10`, and the cross-ref targets a named subsection.
  - `model-tier-notes.md:101` adds an overengineering bullet under the dated `## Cross-model patterns` header (L89) with a verbatim vendor quote and Source URL (`prompting-claude-fable-5`, verified 2026-06-10). The L225 cross-ref now resolves to real content — the reviewer's preferred Option (a). Both directions of the cross-reference resolve: SKILL.md:225 → model-tier-notes.md:89 heading; model-tier-notes.md:101 → SKILL.md:223 `## Overengineering Prevention`.

- **Prior Minor 2 (advisor-tool + effort URLs missing from phase file Sources)** — **Resolved.**
  - `phase_02_6.md:21-22` appends both URLs to the Sources section, each annotated "added by 2026-06-10 post-GREEN addendum" with the relevant rationale (advisor pairing / cost-gate protection; effort parameter / task budgets). The Sources list now matches the citations the implementation relies on.

## Plan Alignment
- AC2.6.8 (no era-claims; every model-behaviour claim under a dated header or with a verified date): ✓ now fully met. The previously-flagged L225 claim carries a verified date and resolves to a dated-header bullet. Scan for bare-generation references and benchmark numbers → none.
- AC2.6.1 / AC2.6.4 intent (post-GREEN addendum citations sanctioned and recorded): ✓ the addendum's two source URLs are now reflected in the phase file's Sources list.
- All other ACs (AC2.6.2, 2.6.3, 2.6.5, 2.6.6, 2.6.7) were fully met in the prior cycle and are untouched by this diff.

## Issues
None. Both prior Minor findings are resolved and the fixes introduce no new issues.

Note (informational, not a finding): the new `model-tier-notes.md:101` bullet states the
descriptive lead-in "Both models may add extra files, abstractions, or defensive error
handling beyond what was asked" and then quotes the identical sentence verbatim as the
vendor source. The word-for-word repetition is harmless and arguably tightens the
attribution, but reads slightly redundantly. Not worth a fix.

## Consolidation Opportunities
None visible in the diff. The fix added one bullet and edited one line; no superseded
content remains. The SKILL.md edit replaced the generic claim in place rather than
duplicating it.

## Decision: APPROVED FOR MERGE

Both prior Minor findings are resolved with evidence. AC2.6.1–2.6.8 are now fully met
(AC2.6.8 was the last open gap and is closed). Verification is green: 867 tests pass,
SKILL.md is 289 lines, the Fable cost gate and Haiku-no-judgement note are intact and
verbatim, no era-claims or benchmark numbers are present, and Phase 2 artefacts are
untouched. No new issues introduced.
