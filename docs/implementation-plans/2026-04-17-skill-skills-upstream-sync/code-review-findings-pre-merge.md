# Code Review Findings — pre-merge

# Code Review: Sonnet-5 Model Floor Propagation

## Status: CHANGES REQUIRED

**Critical: 2 | Important: 3 | Minor: 2**

## Verification
```
Tests: uv run pytest -q → 1131 passed
Tests (scoped): uv run pytest tests/test_model_tier_freshness.py tests/test_marketplace_sync.py -q → 30 passed
Lint: not run — no lint findings requested and diff is prose/config-only (no Python touched except uv.lock metadata)
```
`test_model_tier_freshness.py` is a genuine mechanical gate (checks `last-verified` frontmatter, per-URL `(verified YYYY-MM-DD)` markers, bans bare `N.x` era-claims, requires model-name anchors near "current models" phrases) — not a tautology, and it passed against the new `model-tier-notes.md` content.

## Plan Alignment
(No implementation plan exists; the requirement is the operator ruling in `.notes/feedback_haiku-no-judgement.md`.)

- ✓ Four `denubis-research-agents` agents (`codebase-investigator`, `combined-researcher`, `internet-researcher`, `remote-code-researcher`) moved `haiku` → `sonnet`. Verified these were the *only* remaining `model: haiku` agents besides `haiku-general-purpose` at BASE_SHA (`git grep` at `c25c1ad`), matching the CHANGELOG's "last agents in the suite still on haiku" claim.
- ✓ `haiku-general-purpose` kept callable, description rewritten to drop research/summarisation.
- ✓ `exec-session-naming` and `design-clarify` dispatch `sonnet-general-purpose`.
- ✓ `testing-skills-with-subagents` GREEN phase moved off "one tier below production."
- ✓ Doctrine recorded in `model-tier-notes.md`, synced in `using-research-agents`, `using-generic-agents`, `creating-an-agent`.
- ✓ Version bumps and marketplace/CHANGELOG sync — all four `plugin.json` versions match `marketplace.json` and the new CHANGELOG heading exactly; the 2.37.0/2.38.0 skip is explained and matches the known-deliberate exception.
- ~ **Deviated (problematic):** the claim "the operator ruled no carve-out for cosmetic work" (repeated in a shipped skill file and the CHANGELOG) has no traceable source in the authoritative note. See Critical finding below.

## Issues

### Critical (count: 2)

- **Issue**: An operator-ruling claim is shipped into durable doctrine with no traceable source. `exec-session-naming/SKILL.md` and `CHANGELOG.md` both state "the operator ruled ... no carve-out for cosmetic work," attributing a specific scope decision to the operator. The designated authority, `.notes/feedback_haiku-no-judgement.md`, contains only the general 2026-07-25 quote ("haiku is unacceptable for internet research... unacceptable for most things... sonnet 5 the floor for almost everything... hallucination rate is unacceptable") and never mentions carve-outs, cosmetic work, or dispatch-site scope at all. I also checked every other file touched by this diff, plus the in-diff audit docs (`docs/audits/2026-07-02-*.md`) and the untracked `RESUME-2026-07-25.md` sitting in the worktree, for any record of this — none exists. This is exactly the failure mode Priority Focus #2 was commissioned to catch: a paraphrase of a dated ruling that goes beyond what the note actually says, now baked into a shipped skill file that a future session will treat as settled fact it can't re-verify.
  - **Location**: `plugins/denubis-plan-and-execute/skills/exec-session-naming/SKILL.md:184`; `CHANGELOG.md:13`
  - **Fix**: Either (a) get the operator to state the cosmetic-work/dispatch-site scope explicitly and add a dated addendum to `.notes/feedback_haiku-no-judgement.md` recording it verbatim, the same way the 2026-07-25 escalation was recorded, then cite that addendum from both locations — or (b) rewrite both sentences to own the inference as the author's own reasoning ("we read 'almost everything' as reaching cosmetic dispatch sites like slug generation; the operator has not separately ruled on this") rather than asserting it as a distinct operator ruling.

- **Issue**: `long-running-state-patterns.md`, a live reference file in the same skill directory as the just-edited `model-tier-notes.md`, still tells directive authors to dispatch Haiku for cost reasons — the exact contradiction this review was commissioned to hunt for, sitting one file away from the fix. It says "Subagents (Sonnet / Haiku tier)," lists `Haiku | Simple tasks | Lowest [cost]` in a model-selection table, and states "The Haiku tier makes multi-agent orchestration economically viable." The file's own header disclaimer ("current versions, IDs, and per-model specifics live in model-tier-notes.md") does not cover this — the disclaimer is about version numbers, but the sentence being contradicted is prescriptive dispatch advice, not a version number. This diff edited three sibling skills' model-tier guidance (`using-generic-agents`, `creating-an-agent`, `testing-skills-with-subagents`) but missed this one, despite it living in `writing-claude-directives/` itself, the very skill whose `model-tier-notes.md` got the floor doctrine added.
  - **Location**: `plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md:121,136,138`
  - **Fix**: Update the model-selection table and the "economically viable" sentence to reflect Sonnet as the floor, consistent with the other three skills edited in this diff. At minimum, add a floor pointer matching the pattern used in `using-generic-agents/SKILL.md`.

### Important (count: 3)

- **Issue**: `testing-skills-with-subagents/SKILL.md` asserts operator-level deliberation over a tradeoff the note gives no evidence the operator considered. "The cost is real and was accepted deliberately" frames the loss of GREEN-phase tier-differentiation (the specific diagnostic value of testing one tier below production) as something the operator weighed and accepted. The note's actual 2026-07-25 statement is a general hallucination-rate ruling; nothing indicates the operator was informed of, or ruled on, this skill's specific testing-methodology tradeoff. This reads as the author's own editorial judgement dressed in the operator's authority.
  - **Location**: `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:65`
  - **Fix**: Rephrase to attribute the acceptance to the author/maintainer applying the ruling's consequence, not to the operator directly — e.g., "This diff accepts that cost as a consequence of the floor ruling" rather than "was accepted deliberately."

- **Issue**: `docs/architecture/plugins/denubis-research-agents/0-context.md` is a living architecture doc (the kind `architecture-update`/`maintaining-project-context` exist to keep synced) that cites a specific commit hash (`5bfcd99`) as the source of truth for each agent's frontmatter model, and states all four research agents are `haiku`. This diff changed all four to `sonnet` without touching this doc, so the doc now contradicts the code it describes, on the exact question this review exists to police.
  - **Location**: `docs/architecture/plugins/denubis-research-agents/0-context.md:54-57`
  - **Fix**: Update the "Model" column to `sonnet` and refresh the commit-hash citation to a commit in this change.

- **Issue**: `docs/architecture/plugins/denubis-basic-agents/0-context.md` describes `haiku-general-purpose`'s purpose as "tool-heavy, low-judgement work," which the same diff's new agent-file description directly contradicts ("No currently sanctioned use... Not for research, summarisation of anything that will be relied on, or any judgement"). The model tier is correctly unchanged (deliberate), but the purpose text drifted.
  - **Location**: `docs/architecture/plugins/denubis-basic-agents/0-context.md:50`
  - **Fix**: Update the purpose cell to match the new frontmatter description, or note explicitly that the architecture doc's purpose text is pending a decision.

### Minor (count: 2)

- **Issue**: `writing-claude-directives/SKILL.md` still frames the model-tier consultation trigger as "deciding whether to route judgement-heavy work away from the Haiku tier" — pre-escalation framing (judgement-heavy work only) that undersells the new blanket floor. Not a live dispatch instruction, so low risk, but inconsistent with the doctrine this same diff wrote into `model-tier-notes.md` one directory down.
  - **Location**: `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md:233`
  - **Fix**: Reword to reference the floor generally, not just judgement-heavy work.

- **Issue**: `writing-skills/anthropic-best-practices.md` (explicitly imported verbatim from `obra/superpowers`, per its own frontmatter and preface) still tells authors to test skills "with Haiku" and includes "Tested with Haiku, Sonnet, and Opus" as a checklist item. This is out of scope by the file's own declared status (vendor reference, not denubis doctrine — same category as the `creating-a-plugin` known exception), so I am not counting it as a finding, but flagging it for awareness since a careless read of the checklist could reintroduce a Haiku dispatch.
  - **Location**: `plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md:153,1147`
  - **Fix**: No action required under current conventions; mentioned for visibility only.

## Consolidation Opportunities
None visible in the diff — the doctrine-sync edits are appropriately distributed (one clause per file) rather than duplicated.

## Additional Sweep Notes (Priority Focus #1, #3, #4 — no findings beyond the above)

- **Residual `model: haiku` in agent frontmatter**: swept all `plugins/**/agents/*.md` — only `haiku-general-purpose.md` remains, which is the documented known exception.
- **`creating-a-plugin/SKILL.md`**: still lists `haiku` as an allowed `model` value — confirmed this is the platform's accepted-values list per the known exception, not a recommendation.
- **`model-tier-notes-log.md`**: mentions Haiku 4.5 only inside dated, already-superseded historical entries (the advisor-pairing convergence log) — correctly framed as history, not live guidance.
- **Priority #3 (testing-skills-with-subagents coherence)**: verified the GREEN-phase rewrite is internally consistent. GREEN is now pinned to "weakest sanctioned tier" (Sonnet) independent of RED's tier, and the lost weaker-tier signal is explicitly redirected to "harder adversarial scenarios" — a mechanism ("pressure scenarios") already fully specified elsewhere in the same file (lines 100, 122-263, 399-412), not a dangling reference. Grepped every other skill that references `testing-skills-with-subagents` (`writing-skills/SKILL.md`, `epistemic-humility/SKILL.md`, `writing-claude-directives/SKILL.md`, `systematic-debugging/CREATION-LOG.md`, `writing-skills/examples/CLAUDE_MD_TESTING.md`) — none hard-codes the retired "one tier below" framing or a specific Haiku GREEN-phase claim, so none is stranded. No remaining "one tier below/down" phrase exists anywhere in `plugins/` (confirmed by grep).
- **Priority #4 (false propagation in the Fable cost gate)**: diffed `model-tier-notes.md` with `--unified=0` to isolate exact changed lines. Exactly three hunks changed, all identical in kind: "Automated work routes to Haiku/Sonnet/Opus" → "Automated work routes to Sonnet/Opus (Haiku was dropped from this list by the 2026-07-25 floor ruling...)". The adjacent advisor-pairing paragraph, which records the deliberately-conflicting platform-API-vs-Claude-Code-docs sources and the Sonnet-as-advisor prohibition, was not touched at all. No corruption of that record.
- **uv.lock**: diff is metadata only (`exclude-newer` / `exclude-newer-span` bump), no dependency changes.

## Decision: BLOCKED - CHANGES REQUIRED
