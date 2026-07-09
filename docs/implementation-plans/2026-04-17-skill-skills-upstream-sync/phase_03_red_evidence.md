# Phase 3 — RED Evidence (independent-session gate)

**Task:** phase_03.md Task 1 (Verifies AC2.7).
**Gate:** Phase 3 does not proceed to Task 2 without this file, sourced from a
session that is NOT the Phase 3 executor. Source 1 (cc-search-chats prior
transcript) produced a qualifying hit; the commissioned fresh-session run
(Source 2) was therefore not needed.

---

## Source

- **Method:** Source 1 — `cc-search-chats:search-chat` over all Claude Code
  project indices. FTS5-safe single-term queries (ISSUE-10), unioned in Python.
- **Search driver:** queried the global FTS index
  (`~/.cc-search-chats/index.db`) once per term across all 102 projects that
  hold session data, then filtered to plugin-development projects and ranked by
  rare-term richness. (A per-project `cc-search-chats search --project … --json`
  sweep is the equivalent reviewer-reproducible form; the direct index query is
  a faithful union of the same rows.)
- **Queries run (19 single-term):** `rationalize`, `rationalise`,
  `rationalisation`, `bypass`, `skipped`, `loophole`, `CRITICAL`,
  `overtriggering`, `aggressive`, `tautology`, `tautological`, `synthetic`,
  `pressure`, `ambiguous`, `subagent`, `defeated`, `defeat`, `mate`, `fuck`.
- **Raw per-term hit counts (pre-union, all projects):** rationalize 4 ·
  rationalise 8 · rationalisation 33 · bypass 359 · skipped 738 · loophole 7 ·
  CRITICAL 2315 · overtriggering 11 · aggressive 89 · tautology 33 ·
  tautological 45 · synthetic 327 · pressure 201 · ambiguous 168 · subagent 882 ·
  defeated 7 · defeat 12 · mate 411 · fuck 216. Union: 5172 unique messages
  across 102 projects; 810 in plugin-development projects.

## Session reference (qualifying hit)

- **Session ID:** `e94bf167-23b4-443d-be14-05fefa3f35df`
- **Project:** `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync`
  (index dir `-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync`)
- **Span:** 2026-04-23T00:33:54Z → 2026-04-24T01:45:44Z (374 records)
- **What the session was doing:** executing **Phase 2** of this same
  upstream-sync plan — GREEN-verifying the restructured `writing-claude-directives`
  skill by dispatching a Sonnet subagent against a pressure scenario, then
  self-applying the `epistemic-humility` rubric before committing the GREEN
  artefact.
- **Independence:** this is a distinct prior session, not the Phase 3 executor
  and not a subagent of it. The failure was surfaced by the session's own rubric
  walk-through and then independently confirmed by an external reviewer (codex),
  so it is not author self-attestation.

Key message UUIDs (reviewer can re-pull with
`cc-search-chats context <uuid> --json --depth 10 --verbose`):
- `57a3d76b-98df-4a2a-b259-38fafcd56370` — the four-check GREEN table, all PASS
  on first run ("All four pass on first run. No REFACTOR iteration needed.").
- `21a7ff8c-19d2-4ddd-a91d-0b88dc312d77` — rubric self-application, vulnerability
  V6 (scenario favourability) named.
- `fc2fee1f-e154-4405-9489-4d5de9d4bf26` — the seven-vulnerability brief handed
  to an external reviewer.
- `2dfb7283-8baf-4748-a3e3-264fe4ca6004` — external reviewer (codex) verdict:
  V6 is a pre-GREEN blocker.

## SKILL.md SHA tested against

The failure is a deficiency of the **current, pre-Phase-3**
`testing-skills-with-subagents/SKILL.md`. Identity recorded at Task 1 dispatch:

- Last commit touching the file:
  `cdc98114985388871af19fcf7377feff8630d030`
- `git hash-object` of the working file:
  `be15d216edd1dab2d6962ac710ef0d3f2abfc591`
- File length: 425 lines.

(The session under observation tested `writing-claude-directives`, but it did so
**following the methodology that `testing-skills-with-subagents` prescribes**.
The deficiency identified below is in that prescribed methodology, not in
`writing-claude-directives`.)

## Observed failure

A GREEN-phase pressure test was run with a **single self-authored pressure
scenario**. All four structural checks passed on the first run, and the
orchestrator initially read this as GREEN ("All four pass on first run. No
REFACTOR iteration needed."). The orchestrator's subsequent rubric
self-application surfaced that the scenario was **exactly what the skill under
test was already optimised to pass** — the scenario was charitable, and no
scenario was run that the skill was *not* tuned for. An external reviewer
independently confirmed this as a pre-GREEN blocker and prescribed running a
contrasting scenario.

This is the **synthetic-scenario over-fitting** failure mode: a scenario invented
by the tester optimises for the path the tester (and the skill author) already
imagined the skill would handle, producing misleading GREEN confidence. The
current SKILL.md instructs the tester to *invent* pressure scenarios and offers
no precedent-sourcing step and no anti-favourability guard — so a charitable,
self-confirming scenario satisfies the prescribed cycle.

## Direct quotes

Orchestrator rubric self-application (`21a7ff8c-…`):

> **V6 — Scenario favourability.** "Aggressive instructions that Claude will
> definitely follow" is exactly what Compliance Techniques is optimised for. I
> didn't test scenarios the skill is *not* tuned for (e.g., reserved-imperatives
> judgement calls). The scenario was charitable.

The same vulnerability, restated in the external-reviewer brief (`fc2fee1f-…`):

> **The one pressure scenario was exactly what the skill's Compliance Techniques
> section is optimised for** ("aggressive instructions"). I didn't test scenarios
> the skill is *not* tuned for — e.g., directives where a genuine hard imperative
> is warranted and the skill should recognise it.

External reviewer (codex) verdict, relayed verbatim by the operator
(`2dfb7283-…`):

> Fix V6. The planned GREEN run is singular … and the chosen scenario only tests
> the "dial back aggressive language" path … even though the skill explicitly
> preserves true hard boundaries … Run one contrasting scenario where a real
> imperative is warranted.

The first-run GREEN table that the favourable scenario produced (`57a3d76b-…`):

> All four pass on first run. No REFACTOR iteration needed.

## Deficiency in the current SKILL.md

- **Location:** `## RED Phase: Baseline Testing (Watch It Fail)` and its
  `### Synthetic Pressure-Scenario Example` (current lines 71–112); plus
  `## VERIFY GREEN: Pressure Testing` → `### Writing Pressure Scenarios`,
  `### Pressure Types`, `### Key Elements of Good Scenarios` (current lines
  122–181).
- **Current text (RED baseline sourcing):** the RED phase tells the tester to
  "**Create pressure scenarios** (3+ combined pressures)" (line 81) and provides
  an invented worked example ("You spent 4 hours implementing a feature… It's
  6pm, dinner at 6:30pm…", lines 91–104). The scenario is *authored by the
  tester*; there is no step that sources the baseline from a real prior failure,
  and no step instructing the tester to include a scenario the skill is **not**
  tuned for.
- **Why it is a deficiency:** the prescribed cycle is satisfiable by a charitable,
  self-confirming scenario. Because the tester invents the scenario, the natural
  scenario to reach for is one the skill (and its author) already anticipated —
  the exact pattern observed in session `e94bf167`. The skill's own VERIFY-GREEN
  guidance ("Make agent believe it's real work, not a quiz", lines 184–191)
  raises *realism* but not *representativeness*: a vivid, realistic scenario can
  still be the one the skill is already optimised to pass. Nothing in RED or
  VERIFY-GREEN grounds the baseline in observed failures or guards against
  favourability. The miss was caught only by an out-of-band rubric and an
  external reviewer — i.e., by machinery outside this skill.

## How Phase 3 addresses it

- **Task 2** prepends a **Conversation-Precedent Protocol** to the RED phase: the
  RED baseline MUST come from an independent session (a `cc-search-chats`
  transcript of a real failure, or a user-run fresh-session scenario), not from
  the tester's invention. Its "why" paragraph names exactly this failure:
  synthetic scenarios "optimise for the scenarios the author imagined the skill
  would face, not the scenarios the skill actually encountered." This directly
  removes the favourability trap: a baseline drawn from a real prior failure
  cannot be charitably tuned to the skill, because it predates the skill.
- **Task 3** demotes the synthetic pressure-scenario content from the RED
  baseline to a REFACTOR-phase **completeness coverage** tool, with a lead
  paragraph stating that synthetic scenarios *supplement* conversation-precedent
  evidence and do not replace it — the precise distinction that V6 collapsed.
- Together these make the favourable-scenario GREEN that session `e94bf167`
  produced structurally non-conforming under the restructured skill: the RED
  baseline would have had to come from a real independent failure first, and the
  synthetic scenario would be labelled as supplementary completeness coverage
  rather than primary GREEN evidence.

Note for reviewers (added after phase-3 code review, 2026-06-11): the qualifying session tested `writing-claude-directives` while following the methodology `testing-skills-with-subagents` prescribes — the observed failure is of the prescribed methodology, locatable in this skill's RED-phase instructions, not of the skill that happened to be under test. A direct in-use failure of this specific skill would be stronger evidence; the session satisfies the gate because the deficiency it exhibits is the one this skill's RED phase encodes.

---

## Near-misses considered and rejected (gate honesty)

The strict qualifying criteria (session was TESTING a skill; exhibited a failure
the current SKILL.md addresses; failure is quotable; responsible SKILL.md section
nameable) excluded several otherwise-tempting hits:

- **Session `3bd05a93` (2026-04-18) — design/planning session for this plan.**
  Contains the cleanest articulation of the deficiency ("synthetic scenarios
  optimise for imagined, not encountered"; the executor-in-critical-path fix).
  Rejected as the RED source: it is *meta-discussion about* the deficiency
  authored by the plan designers, not an *observed failure of the skill in use*.
  Using it would be circular — it is the framing the independent-session gate
  exists to exclude.
- **Sessions `1e0345ae` / `60e09787` (2026-04-17) — Phase 1/plan-authoring.**
  Discuss synthetic-to-REFACTOR demotion and aggressive-imperative
  overtriggering in the abstract. No observed in-use failure; same circularity
  problem.
- **Session `24ef9bc1` (2026-06-02/03).** "I wrote it strong, but I didn't run
  the rationalisation-loophole loop" — an admission of *skipping* testing, not a
  testing run that *failed* in a way this skill addresses. Does not exhibit the
  synthetic-over-fitting / rationalisation-under-pressure / ambiguous-clarity
  failure modes.
- **Frustration-only hits (`mate`, `fuck`).** e.g. `5d509d40` "please actually
  not test with test data in prod, mate?" and `24ef9bc1` "I've run UATs, mate? I'm
  very tired." Operator-frustration markers without a skill-testing-failure
  context. Excluded per the criteria.

The qualifying hit (`e94bf167`, V6) was retained because it is, uniquely among
the candidates, an *observed* in-use failure of the prescribed testing
methodology, *quotable*, *independently confirmed* (codex), and locatable to a
named SKILL.md region.

---

## Appendix — Task 0 dual-upstream refetch + drift survey (verbatim)

Incorporated per phase_03.md 2026-06-10 Amendment item 1. Source:
`/tmp/exec-2026-04-17-skill-skills-upstream-sync-564e1be7/task0-drift-survey.md`.

> # Phase 3 Task 0 — Dual-Upstream Refetch + Drift Survey (2026-06-11)
>
> Per phase_03.md 2026-06-10 Amendment item 1.
>
> ## Pinned upstream hashes
>
> - obra/superpowers (clone: /tmp/superpowers-obra): `6fd4507659784c351abbd2bc264c7162cfd386dc 2026-05-29 Require contributors to disclose authoring environment and target dev`
> - ed3dai/ed3d-plugins (clone: /tmp/ed3d-plugins-upstream): `47257b5ead52972de667f8922f6cc4ec3af1d8cd 2026-04-28 feat(house-style): add howto-code-in-rust skill, generalize commit hygiene`
>
> ## Drift survey result: NO MATERIAL DRIFT — no HALT
>
> - obra `skills/writing-skills/testing-skills-with-subagents.md`: 384 lines (matches April 2026-04-17 anchor). Last commit touching the file: `a08f088 2026-01-14`. Anchors re-verified verbatim:
>   - `### Pressure Types` + 7-pressure table at lines 128–140; "**Best tests combine 3+ pressures.**" at 142.
>   - Letter-vs-spirit rationalization strings at 169 and 216 ("I'm following the spirit not the letter").
>   - Meta-testing three response categories at 240–265.
> - ed3d upstream `plugins/ed3d-extending-claude/skills/`: no commits since 2026-04-17. testing-skills-with-subagents last touched `3e7e26e 2026-02-13`; writing-skills `611bfd1 2026-02-03`; writing-claude-directives `b0d6d88 2026-03-19`. Repo tip 2026-04-28 commit touched house-style only.
>
> April line anchors remain valid; re-anchoring not required. Obra's "Why this works" persuasion-principles.md cross-reference (line ~144) remains excluded per the design plan ("Persuasion principles do not belong in denubis skills").
