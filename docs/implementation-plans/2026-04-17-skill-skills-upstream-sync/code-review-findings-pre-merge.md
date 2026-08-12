# Code Review Findings — pre-merge

# Code Review: Sonnet-5 Model Floor Propagation (Re-Review After Fix Cycle)

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification
```
Tests: uv run pytest -q → 1131 passed
Lint: uv run ruff check . → ruff binary not found in this environment; no Python files
       are touched by this diff (fix cycle is markdown/JSON/lock only), so this is
       non-blocking. Confirmed via `git diff --name-only` that no *.py file appears
       in c25c1ad..5b66e0e.
```

Scope note: verified against the whole branch (`c25c1ad5371fc80e6d0e3bf9ff8432f94a908e76..5b66e0e`,
30 files changed), not only the three fix commits (`cd839f8`, `412857f`, `5b66e0e`), per the
caller's instruction that several fixes edit files first touched earlier in the branch.

## Prior Findings Verification

### Critical

**C1 — unsourced operator attribution ("no carve-out for cosmetic work").**
**Resolved.** The current dispatch contract and its raw human authority records live in
`plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md`.
Dependent skills point to that owner rather than restating the decision.

**C2 — `long-running-state-patterns.md` contradicted the floor one directory from where it was declared.**
**Resolved.** Commit `412857f` rewrote the header disclaimer, the ASCII orchestration diagram,
the tier table, and the "economically viable" sentence:
- Header (line 3): *"Tiers here follow this project's model floor, so they are Opus and Sonnet
  only ... the tier assignments below are not [model-independent]"* — closes the loophole the
  prior review identified (the old disclaimer scoped only to version numbers).
- Diagram (line 121): `Subagents (Sonnet / Haiku tier)` → `Subagents (Sonnet tier)`.
- Table (lines 134-136): the `Haiku | Simple tasks | Lowest` row is deleted outright, not just
  reworded.
- Economics sentence (line 137): *"Sonnet is the cheapest sanctioned tier, so it carries the
  fan-out ... Haiku is cheaper again and is not available for this, because an operator ruling
  on 2026-07-25 made Sonnet the floor"* — replaces the old "The Haiku tier makes multi-agent
  orchestration economically viable" claim and cites the note.
`grep -n -i haiku` on the file now returns exactly one line (the economics sentence explaining
why Haiku is *excluded*), confirming no residual prescriptive Haiku guidance survives.

### Important

**I1 — "the cost is real and was accepted deliberately" overclaimed operator deliberation.**
**Resolved.** `testing-skills-with-subagents` now states the current Sonnet test floor and
points to the model-routing owner; it does not reconstruct operator deliberation.

**I2 — `docs/architecture/plugins/denubis-research-agents/0-context.md` stale (all four agents listed as haiku, stale commit citation).**
**Resolved.** Commit `5b66e0e` updates the Model column to `sonnet` for all four agents and
repoints each per-claim commit citation from `5bfcd99` to `ebfc608`. Verified `ebfc608` by
`git show`: it is exactly `feat(research-agents): move all four research agents to sonnet`,
touching all four agent files' `model:` frontmatter plus `using-research-agents/SKILL.md` — the
citation is accurate, not just plausible-looking. The doc also gained a summary line: *"All four
ran on `haiku` until 2026-07-25, when an operator ruling made Sonnet the floor"* with a
`.notes/` citation.

**I3 — `docs/architecture/plugins/denubis-basic-agents/0-context.md` purpose text drifted from the new frontmatter description.**
**Resolved.** Commit `5b66e0e` rewrites the purpose cell to track the new
`haiku-general-purpose.md` description almost verbatim ("no currently sanctioned use," "kept
callable," "positive justification naming a bounded mechanical task") and repoints the commit
citation from `3918fe9` to `3e28e44`. Verified `3e28e44` by `git show`: it is
`fix(basic-agents): stop advertising a tier with no sanctioned use` and does edit
`haiku-general-purpose.md`'s description to the text the architecture doc now paraphrases — the
citation is accurate.

### Minor

**m1 — `writing-claude-directives/SKILL.md:233` pre-escalation framing ("route away from Haiku").**
**Resolved.** Commit `cd839f8` changes "deciding whether to route judgement-heavy work away from
the Haiku tier" to "checking a dispatch against the Sonnet model floor," which reflects the
blanket-floor doctrine rather than the superseded judgement-only framing.

**m2 — `anthropic-best-practices.md` still references Haiku (FYI only, not counted as a finding previously).**
**No change made, and this is correct.** `git diff` confirms this file is untouched by the fix
cycle. I agree with leaving it alone: its frontmatter declares it verbatim-imported content from
`obra/superpowers` with a source-repo/source-commit/imported-date provenance contract, and
editing vendor-attributed text to match local doctrine would falsify that provenance without
actually changing what the upstream project says. This was correctly logged as "no action
required" in the prior review and remains so.

## New Issues (Priority Sweep)

Per the caller's instruction, I widened the search past `plugins/**/*.md` and
`docs/architecture/**/*.md` — the two locations the author's own greps evidently covered (per
the `5b66e0e` commit message: *"The earlier sweep missed these because it was scoped to
plugins/**/*.md and never looked at docs/"*) — into file types and directories a markdown-scoped
sweep would skip:

- **Hooks** (`plugins/*/hooks/*.py`): `git grep -il haiku` across all `.py` files in the repo
  returns only `tests/test_model_tier_freshness.py`. No hook references Haiku dispatch.
- **Scripts, JSON, TOML, YAML, shell**: `git grep -il haiku -- '*.py' '*.json' '*.sh' '*.toml'
  '*.yaml' '*.yml' '*.js' '*.ts'` returns only the same test file. No JSON config (including
  `hooks.json` in five plugins, all four `plugin.json` files, and `marketplace.json`) references
  a model tier by name at all — model selection lives entirely in agent frontmatter and
  skill prose, both already covered by the doctrine sync.
- **Test fixtures**: `tests/test_model_tier_freshness.py` mentions Haiku twice, both as sample
  text for a regex-anchor test (`MODEL_NAME_PATTERN` matching "Sonnet 4.6, Haiku 4.5" style
  strings) — this is fixture data exercising the freshness-checker itself, not a dispatch site
  or a doctrine claim. Not a finding.
- **READMEs**: `README.md` and `docs/architecture/README.md` both list "haiku/sonnet/opus
  general-purpose" as the three agents this plugin provides — a factual enumeration of files
  that exist (all three files still exist; `haiku-general-purpose` is the documented kept-callable
  exception), not a dispatch recommendation or a currency claim. Not a finding.
- **Directories outside `plugins/` and `docs/architecture/`**: checked `docs/audits/2026-07-02-*.md`
  (two files, newly added earlier in the branch) and the three `RESUME-PROMPT-fable*.md` files.
  The audit docs mention Haiku only inside dated 2026-07-02 findings tables describing the
  pre-floor state — correctly frozen historical snapshots, same category as the `docs/design-plans/`
  exemption the caller flagged as deliberate. `docs/design-plans/2026-03-21-statusline-v2.md` and
  `docs/implementation-plans/2026-04-17-.../phase_02*.md` likewise reference Haiku only in
  dated historical description of decisions already made at the time — not live doctrine, not
  touched by this diff, not in scope. The three RESUME-PROMPT files contain no Haiku references
  at all.
- **JSON validity**: all four `plugin.json` files and `marketplace.json` parse as valid JSON
  after the version bumps (checked with `python3 -m json.load`).
- **Version/marketplace sync**: all four bumped versions (`2.1.0`, `1.3.0`, `1.10.0`, `2.39.0`)
  match between each plugin's `plugin.json` and `marketplace.json` exactly. The 2.37.0/2.38.0
  skip is the caller's known-deliberate exception.
- **New-citation spot check**: grepped every remaining "operator ruled / operator ruling /
  operator statement" claim added or touched by this diff (7 locations across
  `CHANGELOG.md`, `haiku-general-purpose.md`, `using-generic-agents/SKILL.md`,
  `creating-an-agent/SKILL.md`, `testing-skills-with-subagents/SKILL.md`,
  `model-tier-notes.md`, `using-research-agents/SKILL.md`). All seven cite the 2026-07-25 floor
  date, which matches the note's "Escalated 2026-07-25" paragraph verbatim-adjacent language
  ("haiku is unacceptable for internet research ... sonnet 5 the floor for almost everything").
  None of these seven independently asserts the 2026-07-26 carve-out without a citation — the two
  live-dispatch-site files that do state the carve-out (`exec-session-naming`,
  `testing-skills-with-subagents`) both point to the model-routing owner. No recurrence of the
  unsourced-attribution defect class.

**Result: zero new issues.** The fix cycle's own stated blind spot (markdown-only sweep scope)
is exactly what this pass targeted, and it did not reproduce in non-markdown surfaces.

## Consolidation Opportunities
None visible in the diff.

## Decision: APPROVED FOR MERGE
