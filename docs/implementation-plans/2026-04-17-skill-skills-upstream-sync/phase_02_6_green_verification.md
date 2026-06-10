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
