# Phase 2.6 GREEN Verification

**Date:** 2026-06-10
**Phase:** 2.6 — Model-Tier Refresh (2026-06-10 amendment)
**Files touched:**
- `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` (pre-edit SHA `1b0ba8c5d6f3fd112a879efa9872c72ce4d4ded1`, 67 lines → 99 lines)
- `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md` (pre-edit SHA `4c4399a585d0c1305372a4c7ca344ab4226911d5`, 279 lines → 289 lines)

This is an append-only audit artefact (GREEN verification), exempt from the living-document rule per the rubric draft's R12 exception.

## AC verification

| AC | Result | Evidence |
|---|---|---|
| AC2.6.1 | PASS | `model-tier-notes.md` has `## Fable 5` (L11), `## Opus 4.8` (L29), `## Opus 4.7 (previous-generation Opus)` (L45); Sonnet 4.6 (L59) + Haiku 4.5 (L75) retained; header refreshed to 2026-06-10; Opus 4.7 marked previous-generation (same API surface as 4.8). Fable 5 section carries 5 `verified 2026-06-10` citation URLs; Opus 4.8 section carries 5. |
| AC2.6.2 | PASS | Opus 4.8 section records conservative tool/subagent/memory triggering with the prescriptive-trigger-condition fix (L31), literal severity-filter following with report-everything-filter-downstream (L33), and increased default narration / remove forced-progress scaffolding (L35). |
| AC2.6.3 | PASS | Fable 5 section records over-prescription degrades output with the verbatim vendor quote (L13), `reasoning_extraction` refusal risk (L15), longer turns by default (L17), parallel-subagent affinity (L19), memory-system affinity / one lesson per file (L21). |
| AC2.6.4 | PASS | Fable cost gate present verbatim in BOTH the Fable 5 section (model-tier-notes.md L25) AND the cross-model patterns section (L95): "Fable-tier invocations are human-triggered only. No directive, skill, plan, or agent prompt may auto-dispatch Fable-tier subagents or schedule unattended Fable runs — they burn real money." |
| AC2.6.5 | PASS | SKILL.md Compliance Techniques carries R3 trigger-explicitness (L98), positioned to extend (not replace) the rhetorical-emphasis vs true-boundary distinction at L96: under-triggering on Opus 4.8/Fable 5 is fixed with explicit when-to-use conditions, never stronger emphasis (which overtriggers Sonnet 4.6 / Opus 4.6 tier). |
| AC2.6.6 | PASS | SKILL.md carries R5 (no reasoning-echo; ask for evidence in output instead — L133/L135) and R7 (harness-tool fallback "if unavailable, ask inline"; `claudew` operator evidence; fully-qualified `Server:tool` form — L137/L139). |
| AC2.6.7 | PASS | See audits-doc closeout (commit refs recorded in `2026-06-10-rubric-for-rubrics-draft.md` pending items 1–2 and `2026-06-10-skill-audit-campaign.md` status). |
| AC2.6.8 | PASS | Grep audit (below) finds no bare-generation era-claims and no benchmark numbers in either touched file; every model-behaviour claim sits under a dated header or carries a verified-date citation. |

## Grep transcript

### AC2.6.8 — era-claim audit (both files)

```
$ grep -nE '\b(4\.x|4\.5\+|pre-4\.x|4\.1-era)\b' SKILL.md model-tier-notes.md
  CLEAN: none

$ grep -niE '[0-9]+(\.[0-9]+)?%[^)]*(SWE|MMLU|bench|eval|accuracy|score)|(SWE-bench|MMLU|GPQA|tau-bench)' SKILL.md model-tier-notes.md
  CLEAN: none
```

All residual "current models" / "Current Opus and Fable models" phrases are anchored: SKILL.md L69 and L96 name the tier inline `(Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5)` and L96 carries `(verified 2026-06-10)`; L103/L111 are illustrative code-comment slots inside the dated L96 subsection; L225 points to the dated `model-tier-notes.md`; L256 is a Common Mistakes table cell cross-referencing the anchored Compliance Techniques section.

### AC2.6.1 — model-tier-notes structure

```
$ grep -nE '^## (Fable 5|Opus 4\.8|Opus 4\.7 \(previous-generation Opus\)|Sonnet 4\.6|Haiku 4\.5|Cross-model patterns)' model-tier-notes.md
11:## Fable 5
29:## Opus 4.8
45:## Opus 4.7 (previous-generation Opus)
59:## Sonnet 4.6
75:## Haiku 4.5
87:## Cross-model patterns

Fable 5 section 2026-06-10 citations: 5
Opus 4.8 section 2026-06-10 citations: 5
```

### AC2.6.4 — Fable cost gate in BOTH locations

```
$ grep -n 'auto-dispatch Fable-tier subagents' model-tier-notes.md
25:**Cost gate (operator-empirical, 2026-06-10):** ... auto-dispatch Fable-tier subagents ...
95:- **Fable cost gate (operator-empirical, 2026-06-10):** ... auto-dispatch Fable-tier subagents ...
```

### AC2.6.5 / AC2.6.6 — SKILL.md additions

```
$ grep -n 'Trigger explicitness fixes under-triggering' SKILL.md
98:**Trigger explicitness fixes under-triggering — not stronger emphasis.** ...

$ grep -n 'Ask for Evidence, Not Reasoning-Echo' SKILL.md
133:### Ask for Evidence, Not Reasoning-Echo

$ grep -n 'Name a Fallback for Harness Tools' SKILL.md
137:### Name a Fallback for Harness Tools
```

### Cross-reference resolution

```
SKILL.md -> model-tier-notes.md refs: 3
model-tier-notes.md -> SKILL.md refs: 4
model-tier-notes.md exists: YES
```

Both files reference each other; `[`model-tier-notes.md`](model-tier-notes.md)` and `[`SKILL.md`](SKILL.md)` are sibling files in the same directory, so the relative links resolve.

### Line counts

```
SKILL.md: 289 (limit <300)  ✓
model-tier-notes.md: 99
```

## Full test suite

`uv run pytest -q` from the working directory — result recorded at commit time (see report). Skill-lint tests over SKILL.md description/frontmatter included; any failure treated as a real failure, not suppressed.

## Post-GREEN addendum — advisor-tool pairing constraint + cost levers (2026-06-10)

Operator-approved follow-up after GREEN (precedent: Phase 2's post-GREEN touch-ups). Touches `model-tier-notes.md` only; SKILL.md untouched (closed at 289/300 lines). Existing GREEN content above is unchanged.

**Added (all carry `verified 2026-06-10` citations; source: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool> and the effort page):**
- Fable 5 section — negative result protecting the cost gate: the advisor tool (beta `advisor-tool-2026-03-01`, type `advisor_20260301`) gives no cross-tier route to Fable judgement. Per the model-compatibility table, Fable 5 executor pairs only with Fable 5 advisor; no other executor may name Fable 5 as advisor; invalid pairs `400`. Recorded with the operator-empirical dated framing, including the verbatim in-session API error `400 tools.30.model: 'claude-opus-4-8' cannot be used as an advisor when the request model is 'claude-fable-5'`.
- Cross-model patterns — positive pattern (inside the cost gate): Haiku 4.5 / Sonnet 4.6 executor + Opus 4.8 advisor as a sanctioned automated-work quality lift (advisor reads transcript mid-generation, ~1,400–1,800 tokens, cap `max_tokens: 2048`; Claude Code `/advisor`).
- Cross-model patterns — task budgets (`output_config.task_budget`, beta `task-budgets-2026-03-13`, min 20,000 tokens, Fable 5 / Opus 4.7 / 4.8) and the effort parameter (`output_config.effort`; `xhigh` Claude Code default). Confirmed not already covered by the earlier Phase 2.6 cross-model edits before adding (no duplication).

**Verification:**
- AC2.6.8 grep on `model-tier-notes.md`: bare-generation era-claims → CLEAN none; benchmark numbers → CLEAN none; every new advisor/budget/effort claim under a dated header or with a verified-date citation.
- Haiku-no-judgement position and the Fable cost gate text unchanged (constraint honoured).
- Header unchanged (2026-06-10; additions share its date). File 99 → 104 lines.
- `uv run pytest -q` → 867 passed.

## Correction addendum — advisor pairing claim overturned by Claude Code docs (2026-06-11)

Operator-directed follow-up (proleptic counterarguments 1–2 disposition + advisor/subagent research). Existing content above is unchanged; the first bullet under the 2026-06-10 addendum ("no cross-tier route to Fable judgement... no other executor may name Fable 5 as advisor") is **superseded** — read it with this correction.

**What changed:** <https://code.claude.com/docs/en/advisor> (verified 2026-06-11, fetched directly) lists Fable as an accepted advisor for Haiku 4.5 and Sonnet 4.6 mains and recommends "Sonnet main + Fable advisor" as a pairing (v2.1.170+, Fable 5 access required). This conflicts with the platform API docs' compatibility table, which has no Fable-advisor row for non-Fable mains. There IS therefore a documented advisor-shaped path to Fable spend; because advisor calls are model-triggered, the cost gate now explicitly covers advisor configuration (no Fable advisor on automated/unattended runs).

**Edits to `model-tier-notes.md`:**
- Header paragraph: clarified that the header date marks the latest verification pass; previous-generation sections retain inline 2026-04-17 dates (proleptic counterargument 1).
- Fable 5 advisor note: rewritten as "Advisor pairing and the cost gate" — observed/documented attribution split (the in-session 400 proves only the Fable-main-rejects-Opus-advisor direction); doc-conflict recorded with both citations; beta-API caveat (changes without model releases, outside the header staleness tripwire) (proleptic counterargument 2 + correction).
- Cross-model advisor bullet: scope facts added — advisor is session main-loop only (`/advisor`, `advisorModel`, `--advisor`); no advisor attachment for subagent dispatches (closed frontmatter field set, no env var); subagent quality lift = `model`/`effort` choice. Source: <https://code.claude.com/docs/en/sub-agents> (verified 2026-06-11).
- Effort bullet: noted agent-definition `effort` frontmatter field.

**Verification:** AC2.6.8 re-grep on `model-tier-notes.md` — every new claim carries a verified-date citation; no bare era-claims; cost gate and Haiku-no-judgement text unchanged.

## Coherence-review closeout (2026-06-11)

Coherence reviewer (Opus, falsification framing, range `0f52233..eba4818`): **coheres — no revision required.** Both hard constraints verified by the reviewer: the Fable cost-gate sentence appears on no removed line in the range; GREEN artefact append-only with zero content lines removed. Operator disposition: "fix the things" — all actionable findings fixed in-session rather than deferred.

**Acknowledged nuance:** the Haiku-no-judgement passage is verbatim-preserved except its routing target advanced "Opus 4.7" → "Opus 4.8" (mechanical consequence of demoting 4.7 to previous-generation). Surfaced by the reviewer, acknowledged by the operator via the fix-the-things disposition; judged within the constraint's intent.

**Dispositions:**
- **M1 (architecture doc stale):** fixed in place rather than deferred to Phase 5 — `docs/architecture/plugins/denubis-extending-claude/0-context.md` updated to ten skills (epistemic-humility row + in-scope line) and skill-adjacent files now list `model-tier-notes.md` and the epistemic-humility supporting files. Root cause noted: the librarian/freshness pass did not fire at the Phase 1/2 boundaries; Phase 5 re-verification sweeps the tree again after Phases 3/4 reshape it.
- **M2 (doc-conflict pattern):** ratified as house style — repo `CLAUDE.md` gains "Conflicting Authoritative Sources Are Recorded, Not Resolved" (record both, attribute observed vs documented, gate conservatively), citing the advisor-pairing correction as precedent for Phases 3/4 drift surveys.
- **Flagged (operator claims lack falsifiers):** falsifier sentences added to the Fable cost gate (both copies, preserving the deliberate verbatim symmetry) and the Haiku-no-judgement note. Both are operator-owned: only a dated operator note or operator-run trial overturns them; vendor framing, doc changes, and model releases never do on their own. The `claudew` citation in SKILL.md deliberately receives no falsifier — it is evidence for rule R7, not a standing revisable position.
- **Suggestion (standing test):** AC2.6.8's mechanisable subset promoted to `tests/test_model_tier_freshness.py` (12 tests, TDD red-green: checker stubs failed first, negative cases prove detection). Invariants: parseable `last-verified` header; every `<URL>` citation carries a same-line `(verified YYYY-MM-DD)`; no bare `N.x` era-claims; "current models/tier" phrases anchored by a model-name enumeration. The new test immediately caught one floating "current models" (cross-model Prompting-responsiveness bullet), fixed to "these models" referring to the enumerated intro. Suite: 867 → 879 passed.

**Carry-forwards (for Phase 3/4 prep):**
- Phase 3 dispatch must read the `model-tier-notes.md` header date at execution time and halt if a model has shipped since (proleptic counterargument 3).
- Phase 4's true-up sweep must not mechanically bless beta-surface claims (advisor, task budgets) because the header reads current — the file deliberately mixes three freshness regimes (current 2026-06-10, previous-generation 2026-04-17 inline, beta surface outside the tripwire).
