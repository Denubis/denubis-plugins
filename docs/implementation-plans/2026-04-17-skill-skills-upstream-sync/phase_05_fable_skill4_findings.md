# Fable-pass skill 4 findings — testing-skills-with-subagents (2026-07-10)

Review of `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/`
on the four axes (job-in-plugin, branch-delta, protocol-conformance, scar
tissue), conducted in the main session per the standing operator ruling (no
subagent dispatch). Every quote was verified with `grep -nF` against the
worktree file before presentation. The branch delta was reconstructed against
the pre-branch baseline `33c173d` (2026-04-16), since `main...HEAD` is
near-empty after the 1.9.0/2.36.0 merge; twelve commits (`b9bed28`..`b4c87e0`)
form the delta.

Per-axis verdicts: (1) the skill does its job as the testing leg of the
writing-skills triad, and its cross-references resolve (the
`../writing-skills/examples/CLAUDE_MD_TESTING.md` pointer was confirmed on
disk); (2) the branch delta made it substantially more effective —
conversation-precedent RED gate with qualifying-criteria checklist,
letter-vs-spirit promoted to foundational, synthetic scenarios demoted to
REFACTOR completeness, tool fallbacks named, narrative tail deleted; (3)
protocol conformance is good — description shape passes, model anchors are
date-stamped; (4) scar tissue was present and is now removed (below).

Operator ruling 2026-07-10 ("it is imperative we remove all scar tissue")
authorised fixing the scar-class findings in one pass; the non-scar findings
remain open for finding-by-finding discussion.

## Dispositions

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| 1 | Important | SKILL.md:303 pointed at "the design plan's *Persuasion principles do not belong in denubis skills*" — plan-vocabulary in a shipped skill; the design plan does not ship with the installed plugin, so the pointer cannot resolve for consumers | Fixed `9fa95e0` — parenthetical cut; the positive "NOT Cialdini persuasion principles" sentence carries the guard |
| 2 | Important | Pre-protocol RED framing survives at lines 42, 77, 107 ("Run scenario WITHOUT skill, watch agent fail"; "give agents the realistic task drawn from that baseline") and sits in tension with the independence gate ("NOT this session, NOT a subagent of this session"; "A subagent of the author's own session does not count") — a first-time executor gets two readings of what a RED run is | **OPEN** — coherence question on the core gate; needs operator discussion (is a subagent reproduction of an independently sourced baseline permitted, or is the run language a leftover to reword?) |
| 3 | Moderate | Three checklists (qualifying criteria, Basic Baseline, Testing Checklist) carry no TaskCreate/disk-mirror preamble; the 2026-07-10 ruling says reuse the writing-skills pattern where the question recurs | **OPEN** — apply the TaskCreate-primary + durable-mirror preamble, pending operator wording |
| 4 | Minor (scar) | "Structural principle retained: weakest-model-tier-that-follows = strongest-clarity-test" (line 63 tail) — consolidation narration duplicating the paragraph's opening claim | Fixed `9fa95e0` — deleted |
| 5 | Minor (scar) | "The catalogue ... now live in the REFACTOR phase's ... subsection — pressure scenarios are a completeness tool, so their reference material sits with the REFACTOR work that uses it" (lines 155–159) — supersession narration | Fixed `9fa95e0` — rewritten as a plain cross-reference |
| 6 | Minor | Near-duplicate example (VERIFY GREEN "Great scenario" vs REFACTOR completeness example) plus a dedup-apology paragraph acknowledging the duplication (line 265) | Scar half fixed `9fa95e0` — apology paragraph deleted. **OPEN** — whether to differentiate the completeness example (e.g. authority+economic+social pressures, which would better demonstrate "modes real transcripts may not exercise") |
| 7 | Flagged | "The skill is always the problem" / "Never conclude 'the model is the problem'" (line 73) — hyperbole contradicted by the same paragraph's minimum-model-requirement carve-out | **OPEN** — defer to the parked systematic-debugging hyperbole ruling; the two should be decided together |

Non-findings weighed and set aside: imperative density (licensed by
writing-claude-directives' discipline-skill row); the Haiku 4.5 dual-source
recording (follows the conflicting-sources convention); the line-36 "usually"
softener (codex won't-fix, not reopened); the obra caveat at line 19
(load-bearing usage instruction, not scar); the
`denubis-basic-agents:sonnet-general-purpose` reference lacking an
absent-plugin fallback (weak — an executor adapts to a generic subagent with a
model override; raise only if the fallback rule is later extended from harness
tools to agent rosters).

## Re-test note

All four fixes delete narration or a dead pointer; none loosens a rule a
pressure scenario exercises, so no pressure-scenario re-run was performed
(the REFACTOR re-test rule targets edits that could weaken compliance).

## Ride-along (same session, outside the seven findings)

- `1b7e618` fix(epistemic-humility): announce-and-temper cadence — once per
  session at skill load, not per presentation (the queued wording fix from the
  skill-3 session, operator-directed this session). This changes the announce
  observable; the enforcement-over-prose design task recorded in
  `phase_05_announce_trigger_red_evidence.md` remains the follow-on, since the
  round-2 RED showed prose levers exhausted for unreinforced subagents.
