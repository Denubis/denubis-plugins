# Fable-pass skill 3 findings — writing-skills (2026-07-09/10)

Review of `plugins/denubis-extending-claude/skills/writing-skills/` on the four
axes (job-in-plugin, branch-delta, protocol-conformance, scar tissue). The
report was produced by an Opus subagent (agent `a430696656f5aaaed`, dispatch
operator-approved 2026-07-09); every quote was verified in the main session
with `grep -nF` against the worktree files or `git diff main...HEAD` before
discussion. Findings were discussed with the operator one at a time and
dispositioned 2026-07-10. No Critical or Important findings; the reviewer's
per-axis verdicts were positive on all four axes.

The same dispatch doubled as round 1 of the epistemic-humility announce-trigger
test; that outcome is recorded separately in
`phase_05_announce_trigger_red_evidence.md` (round 1 invalid, round 2 valid
RED).

## Dispositions

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| 1 | Minor | SKILL.md:125 named TaskCreate with no harness-tool fallback, under an `IMPORTANT:` marker | Fixed `7299e79` — TaskCreate primary, checklist file as durable mirror and fallback (operator ruling) |
| 2 | Minor | Consolidation narration, date stamps, and a promissory "queued to replace" in `examples/CLAUDE_MD_TESTING.md:6,11` + SKILL.md:114 | Fixed `9a7d8a4` — scar cut; import pin and doctrinal caveat kept; intent moved to ISSUE-13 with state |
| 3 | Minor | Intro sub-skill list ordered exist → phrase → test, contradicting the Iron Law and the d5a0f5b Workflow order | Fixed `96c757b` — reordered to scope → pressure-test → phrase |
| 4 | Flagged | Dropped "Testing is overkill / Too simple / No time" anti-rationalisation rows lost their only home | Fixed `87e7401` — one counter line in the checklist preamble |
| 5 | Flagged | SKILL.md template frontmatter omitted `user-invocable`, which every skill in the plugin sets | Fixed `5c135a7` — field added to the template, default false, inline note |
| 6 | Flagged | Description does not advertise the new scope gate | **Won't-fix** (operator, 2026-07-10) — the trigger set is unchanged and already routes; the gate is workflow step 1 and the first checklist section, so the addition would be content preview, not discovery |

## Re-test note

All five fixes strengthen or are cosmetic to the directives under test (a
fallback added, scar removed, an ordering corrected, a counter restored, a
template field added). No fix loosens a rule a pressure scenario exercises, so
no pressure-scenario re-run was performed for them; the REFACTOR re-test rule
is about edits that could weaken compliance.

## Ride-along (same session, outside the six findings)

- `24b9d1b` fix(epistemic-humility): description shortened 349 → 196 chars —
  caught by `test_skill_descriptions.py` at the 1.9.0 release gate; trigger
  clause preserved verbatim.
- `561f069` fix(maintaining-project-context): stale Called-by step pointers —
  by-product of the round-2 trigger-test audit.
- `7103b88` feat(exec-session-naming): user-invocable (operator request).
- Queued, not yet done: epistemic-humility announce-cadence wording (operator
  2026-07-10: announce once per load, not per presentation) and the
  announcement-enforcement design task (see the RED-evidence record).
