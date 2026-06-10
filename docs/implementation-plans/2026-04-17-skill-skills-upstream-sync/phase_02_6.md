# Skill-Skills Upstream Sync — Phase 2.6: Model-Tier Refresh (2026-06-10 Amendment)

**⚠️ EXECUTION ORDER:** Inserted by the 2026-06-10 amendment pass. Runs after Phase 2.5, before Phase 3. Full order: `phase_01 → phase_02 → phase_02_5 → phase_02_6 → phase_03 → phase_04 → phase_06 → phase_05`.

**Goal:** Refresh `writing-claude-directives`' model-tier guidance from the 2026-04 tier (Opus 4.7 / Sonnet 4.6 / Haiku 4.5) to the 2026-06 tier (Fable 5 / Opus 4.8 / Sonnet 4.6 / Haiku 4.5), and reconcile the rubric-for-rubrics items that target this skill. Phase 2's work is NOT reopened — its audit trail stands; this phase is a corrective refresh of one Phase 2 deliverable that has tripped its own staleness rule.

**Why now:** `model-tier-notes.md` carries the rule "if the dated header is more than one model release behind current, treat every claim below as unverified". Its header reads 2026-04-17; Opus 4.8 and Fable 5 have shipped since. The file is, by its own standard, unverified.

**Architecture:** Edit-in-place of `model-tier-notes.md` (add sections, refresh header, keep the per-model + cross-model + operator-empirical structure Phase 2 established) plus three surgical additions to `SKILL.md`. No new files.

**Phase Type:** functionality (preventive-restructure RED framing per the 2026-04-22 amendment precedent).

**Depends on:** Step-0 merge of current `main` (see RESUME-PROMPT) — requires `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` and `docs/audits/2026-06-10-skill-audit-campaign.md` in-tree.

**Sources (all verified 2026-06-10):**
- <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>
- <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5>
- <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8>
- <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>
- Rubric-for-rubrics draft: `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` (R3, R5, R7, R10 cost-gate)
- <https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool> (added by 2026-06-10 post-GREEN addendum: advisor pairing pattern and cost-gate protection)
- <https://platform.claude.com/docs/en/build-with-claude/effort> (added by 2026-06-10 post-GREEN addendum: effort parameter, task budgets)
- <https://code.claude.com/docs/en/advisor> (added by 2026-06-11 correction addendum: Claude Code advisor pairing table — conflicts with the API-docs table; Fable accepted as advisor for Haiku/Sonnet mains; advisor is session main-loop only)
- <https://code.claude.com/docs/en/sub-agents> (added by 2026-06-11 correction addendum: closed agent-frontmatter field set — no advisor attachment for subagents; per-agent `effort` field)

---

## Acceptance Criteria

- **AC2.6.1 Success:** `model-tier-notes.md` contains Opus 4.8 and Fable 5 sections, each with at least one citation URL to 2026-06 Anthropic documentation; the dated header is refreshed; the Opus 4.7 section is retained, marked previous-generation (same API surface as 4.8).
- **AC2.6.2 Success:** The Opus 4.8 section records: conservative tool/subagent/memory triggering with the prescriptive trigger-condition fix; literal severity-filter following (report-everything-filter-downstream for review harnesses); increased default narration.
- **AC2.6.3 Success:** The Fable 5 section records: over-prescription degrades output (vendor quotation: "Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality"); `reasoning_extraction` refusal risk for reasoning-echo instructions; longer turns by default; parallel-subagent affinity; memory-system affinity.
- **AC2.6.4 Success (operator-empirical, 2026-06-10):** The Fable cost gate is recorded in the Fable 5 section AND the cross-model patterns section: **Fable-tier invocations are human-triggered only. No directive, skill, plan, or agent prompt may auto-dispatch Fable-tier subagents or schedule unattended Fable runs — they burn real money.** Automated work routes to Haiku/Sonnet/Opus.
- **AC2.6.5 Success:** `SKILL.md` Compliance Techniques carries the trigger-explicitness rule (rubric R3): under-triggering on current Opus/Fable tiers is fixed with explicit when-to-use conditions in descriptions, never with stronger emphasis (which overtriggers).
- **AC2.6.6 Success:** `SKILL.md` carries rubric R5 (directives must not instruct models to echo or transcribe internal reasoning; ask for evidence in output instead) and R7 (directives naming harness tools state an if-unavailable fallback; tool rosters vary per session — operator evidence: the `claudew` alias).
- **AC2.6.7 Success:** `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` pending-reconciliation items 1–2 are marked done with commit refs; the campaign doc status table is updated.
- **AC2.6.8 Failure:** No era-claims introduced ("current models" without a dated anchor, bare "4.x"-style generation claims, benchmark numbers). Grep-audit: every model-behaviour claim in the touched files sits under a dated header or carries a verified-date citation.

## Tasks (single implementor session)

1. **Read sources + rubric draft.** Confirm the four cited URLs still say what the rubric draft summarises; note any drift in the RED-evidence artefact.
2. **Edit `model-tier-notes.md`.** Add Opus 4.8 + Fable 5 sections (vendor-guidance provenance convention); mark Opus 4.7 previous-generation; refresh dated header and the cross-model patterns section (add: trigger-explicitness, Fable cost gate).
3. **Edit `SKILL.md`.** R3 into Compliance Techniques (extends, does not replace, Phase 2's rhetorical-emphasis vs true-boundary distinction); add R5 and R7 entries where they fit the existing section structure; keep total length < 300 lines.
4. **Verify.** Grep checks per ACs; line counts; cross-reference resolution (`model-tier-notes.md` ↔ `SKILL.md`).
5. **Close the loop.** Update the two `docs/audits/` files (in-tree post-merge); commit per repo convention (separate commits: model-tier-notes, SKILL.md, audits-doc closeout).

## RED evidence (static, preventive)

The staleness tripwire itself: `model-tier-notes.md` header dated 2026-04-17 vs current tier 2026-06 (Opus 4.8 released; Fable 5 released; vendor guidance pages for both exist and postdate every claim in the file). Record the tripwire text and the two new model names in `phase_02_6_red_evidence.md`. No transcript search required — preventive framing per the 2026-04-22 amendment precedent.

## Done when

- [ ] AC2.6.1–AC2.6.8 verified (grep transcript in GREEN artefact)
- [ ] `phase_02_6_red_evidence.md` and `phase_02_6_green_verification.md` committed
- [ ] Audits docs updated in-tree
