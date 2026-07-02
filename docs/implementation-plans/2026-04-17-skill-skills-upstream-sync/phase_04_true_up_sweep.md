# Phase 4 True-Up Sweep — 2026-06-12

This is a designated append-only audit artefact (R12 exception): later corrections append dated entries below rather than editing the entries above. Every count, SHA, and quotation here was recomputed from files and git at write time (CA3 rule).

## Pinned upstream and clone verification

- Pinned obra clone: `/tmp/superpowers-obra`
- Verified HEAD: `6fd4507659784c351abbd2bc264c7162cfd386dc` (obra/superpowers, 2026-05-29), matches the plan pin. Confirmed with `git -C /tmp/superpowers-obra log -1 --format='%H'`.
- Working branch: `skill-skills-upstream-sync` (worktree). No edits were made to any skill file in this task; this artefact is the only file written.

## Scope

Amendment item 3 (operator-approved 2026-06-10), phase_04.md line 72: inventory the denubis-extending-claude files descending from obra/ed3d, true them up against the pinned obra hash, and record per file: identical / diverged-deliberately (cite the decision) / diverged-stale (true up). Plus carry-forward 1: independent re-verification of the beta advisor/task-budget claims in `model-tier-notes.md`.

## Part 1 — Obra-descent inventory and classification

Method: located each candidate's obra counterpart with `find /tmp/superpowers-obra -name '<basename>'`; ran `diff`/`sha256sum`; used `git log --follow` on our side to source each divergence. Name-match scan intersected basenames and skill-directory names (Part 1c).

| File (denubis path, repo-relative) | Obra counterpart at 6fd4507 | Classification | Evidence |
|---|---|---|---|
| `plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot` | `skills/writing-skills/graphviz-conventions.dot` | **diverged-deliberately** | Seed body (`cf17c55`, pre-attribution) SHA `e2890a5…` == obra@6fd4507 SHA `e2890a5…` — byte-identical, corroborating the April 2026 claim. Current divergence = (1) 3-line attribution comment header + blank line added in `bb2f87f` then relocated above `digraph` in `8230047`; (2) one cosmetic blank line left after `digraph STYLE_GUIDE {` by the `8230047` header move. `diff -B` (ignore blank lines) of body vs obra is silent. No contradiction of any recorded audit claim. |
| `plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md` | none | **no obra counterpart at 6fd4507 — denubis/ed3d-original** | `find` finds no obra file of this basename or near-name; the only obra "long-running" hit is `using-superpowers/references/copilot-tools.md` (unrelated, copilot tools). Present at our seed `cf17c55`; history (`76faf34`, `0a2d607`) is denubis-side model-anchor/header maintenance only. Nothing to true up against obra. |
| `plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md` | `skills/writing-skills/anthropic-best-practices.md` | **verbatim-body (verified this phase)** | Commit `8e342f8`. 2 diff hunks, both pure additions on our side: frontmatter+preface (our lines 1-15) and dated appendix (our lines 1166-1184). Our body lines 16-1165 SHA `20914c2…` == obra SHA `20914c2…`. Frontmatter's own `adaptation: verbatim (… body obra-authored, byte-identical)` matches observation. |
| `plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js` | `skills/writing-skills/render-graphs.js` | **byte-identical (verified this phase)** | Commit `8d807a4`. `diff -q` silent (exit 0); SHA `ccda971…` both sides. |
| `plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md` | `skills/writing-skills/examples/CLAUDE_MD_TESTING.md` | **light-touch-adapted (verified this phase)** | Commit `25af075`. 2 diff hunks, both pure additions on our side: frontmatter (our lines 1-8) and one denubis cross-reference note (our lines 10-11). No mid-body `<`/`>` changes; obra scenario content unchanged. Frontmatter's `adaptation: light-touch` matches observation. |
| `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md` | `skills/writing-skills/SKILL.md` (same skill-dir name) | **diverged-deliberately** | Phase 4 cornerstone rewrite, commit `472ba3d` ("cornerstone rewrite as thin orchestrator sequencing three sub-skills"), ancestor of HEAD `25af075`. Deliberate per plan; content diff is not the classifier. |
| `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` | ed3d→obra ancestor (renamed; no same-named obra dir) | **diverged-deliberately** | Traces to seed `cf17c55` under `plugins/ed3d-extending-claude/…`, renamed R100 at the denubis rename `1cd3c82`; shares obra heritage (sibling `CLAUDE_MD_TESTING.md` example). Rewritten across Phase 3 of this plan — series of refactors, largest `598ef7a` (119 lines), reframing `7d727b8`/`2412bba`, and the explicit phase-3 review commit `6b2dc70` (`docs(phase-03): address phase-3 review findings…`). All ancestors of HEAD. Deliberate per plan. |
| `plugins/denubis-extending-claude/skills/writing-skills/README.md` | none (obra has no README.md under `skills/`) | **denubis-authored, not obra-descended** | Commit `8d807a4` ("…+ README for supporting files"). `find /tmp/superpowers-obra/skills -name README.md` returns nothing. Documents the imported supporting files; no obra ancestor. |

### Part 1c name-match scan detail

- Basename intersection (obra `skills/` tree vs denubis-extending-claude `*.md`/`*.js`/`*.dot`): `anthropic-best-practices.md`, `CLAUDE_MD_TESTING.md`, `graphviz-conventions.dot`, `render-graphs.js` (all classified above), plus generic `SKILL.md`.
- Skill-directory-name intersection: only `writing-skills` matches by directory name (classified above). `testing-skills-with-subagents` has no same-named obra dir but descends from an obra ancestor via ed3d (classified above as the prompt directed).
- No other genuine obra-descended file was found beyond those tabled.

### Note on the April byte-identity claim (graphviz-conventions.dot)

The HALT condition "evidence contradicting the April byte-identity claim … in a way that implicates other recorded artefacts" was checked and **not triggered**. The April claim ("Verified byte-identical 2026-04-17 during skill-skills upstream sync (Phase 2)") is corroborated, not contradicted: the seed body predating our attribution edits is byte-identical to obra@6fd4507 (matching SHA). The present file-level difference is entirely self-inflicted (attribution header + one cosmetic blank line from the header relocation in `8230047`) and post-dates the verification. The header comment still asserting "byte-identical" sits four lines above a body that now carries one extra blank line versus obra; this is a cosmetic drift in the file the comment annotates, not a falsified audit record. It is listed under Flags as a low-severity tidy-up candidate (operator decision; no edit made here).

## Part 2 — Beta advisor / task-budget claim re-verification (carry-forward 1)

Target file: `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md`. These claims concern beta APIs and sit outside the header-date staleness tripwire, so the `last-verified: 2026-06-10` header does not bless them. Re-verified independently against live docs on **2026-06-12**. Source attribution per claim marks each as **observed** (empirical, reproduced in session) or **documented** (docs-only).

### Claim A — Advisor pairing and the Fable-advisor live-doc conflict (line 27)

Verbatim claim (excerpt): *"The advisor tool (beta `advisor-tool-2026-03-01`, tool type `advisor_20260301`) lets a cheaper main model consult a stronger advisor mid-task. Observed (operator-empirical, 2026-06-10, in session): a Fable 5 main model rejects an Opus 4.8 advisor — verbatim API error: `400 tools.30.model: 'claude-opus-4-8' cannot be used as an advisor when the request model is 'claude-fable-5'`. … The converse direction is open, not closed: Claude Code's advisor docs list Fable as an accepted advisor for Haiku 4.5 and Sonnet 4.6 mains and recommend "Sonnet main + Fable advisor" as a pairing, while the platform API docs' compatibility table omits any Fable-advisor row for non-Fable mains — a live doc conflict (noted 2026-06-11 …)."*

**Verdict: CURRENT, and the recorded live-doc conflict is CONFIRMED STILL LIVE (2026-06-12).**

- Beta header `advisor-tool-2026-03-01` and tool type `advisor_20260301`: **documented**, confirmed verbatim on the platform API advisor-tool page (beta note and every code sample) — `https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool` (fetched 2026-06-12).
- Fable-main-rejects-non-Fable-advisor: **observed** (the 400 the file records, 2026-06-10) and additionally **documented** on both pages. Claude Code advisor doc: Fable 5 main → accepted advisors "Fable", note "An Opus or Sonnet advisor is rejected" — `https://code.claude.com/docs/en/advisor` (fetched 2026-06-12). Platform API compat table: Fable 5 executor → "Claude Fable 5" advisor only.
- The conflict over **Fable-as-advisor for Haiku/Sonnet mains** persists across the two live sources as of 2026-06-12:
  - Claude Code advisor doc, "Choose an advisor model" table (**documented**, fetched 2026-06-12): `Haiku 4.5 → Fable, Opus, Sonnet`; `Sonnet 4.6 → Fable, Opus, Sonnet`; and "Common model pairings" recommends "Sonnet main + Fable advisor."
  - Platform API advisor-tool "Model compatibility" table (**documented**, fetched 2026-06-12): `Haiku 4.5 → Opus 4.8, Opus 4.7`; `Sonnet 4.6 → Opus 4.8, Opus 4.7`. No Fable advisor row for any non-Fable executor.
- Per the repo convention "Conflicting Authoritative Sources Are Recorded, Not Resolved," both readings stand recorded; the file already gates conservatively (route automated-run advisors to Opus 4.8, never Fable), which the conflict does not disturb. No edit made.

### Claim B — Advisor is a session main-loop feature only; closed subagent frontmatter (line 98)

Verbatim claim (excerpt): *"**Scope (Claude Code, verified 2026-06-11): the advisor is a session main-loop feature only.** It is set via `/advisor`, the `advisorModel` setting, or the `--advisor` launch flag, and there is no way to attach an advisor to a subagent dispatch — the agent-definition frontmatter field set is closed (`model`, `effort`, `maxTurns`, `tools`, … — no advisor field) and no subagent-advisor env var exists. A subagent runs on its `model` with no advisor, regardless of the parent session's advisor."*

**Verdict: CURRENT.**

- Advisor configured via `/advisor`, `advisorModel` setting, `--advisor` flag, session main-loop only: **documented**, confirmed on `https://code.claude.com/docs/en/advisor` ("Enable the advisor": three configuration methods; "Supported main model: Opus 4.6 or later, Sonnet 4.6, or Haiku 4.5 … Fable 5 also qualifies on … v2.1.170+") (fetched 2026-06-12).
- Closed subagent frontmatter with no advisor field: **documented**, confirmed on `https://code.claude.com/docs/en/sub-agents` (fetched 2026-06-12). The page enumerates the full supported field set — `description`, `prompt`, `tools`, `disallowedTools`, `model`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills`, `initialPrompt`, `memory`, `effort`, `background`, `isolation`, `color`. The string "advisor" does not appear anywhere on the page. The file's parenthetical "(`model`, `effort`, `maxTurns`, `tools`, …)" is a faithful (elided) subset; no conflict.
- The 1,400–1,800-token typical advisor usage and the `max_tokens: 2048` cap recommendation in this bullet are also **documented** on the platform advisor-tool page (Usage and billing: "typically … 1,400 to 1,800 tokens total including thinking"; Capping advisor output: "Recommended starting point: `max_tokens: 2048`").

### Claim C — Task budgets (line 99)

Verbatim claim: *"**Task budgets (cumulative cost bound):** for long agentic runs, `output_config.task_budget` (beta `task-budgets-2026-03-13`, minimum 20,000 tokens; Fable 5 / Opus 4.7 / Opus 4.8 only) gives the model a running token countdown it self-moderates against — a model-aware cumulative bound, distinct from `max_tokens` (an enforced per-response ceiling the model does not see). Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8> (verified 2026-06-10)."*

**Verdict: CURRENT on substance; two minor doc-precision discrepancies (no material conflict).**

All substantive sub-claims are **documented** and confirmed on the dedicated task-budgets page `https://platform.claude.com/docs/en/build-with-claude/task-budgets` (fetched 2026-06-12):

- Beta header `task-budgets-2026-03-13`: confirmed verbatim.
- Minimum 20,000 tokens: confirmed verbatim — "The minimum accepted `task_budget.total` is **20,000 tokens**; values below the minimum return a 400 error."
- Advisory cumulative bound vs `max_tokens` per-response ceiling: confirmed — "Task budgets are a **soft hint, not a hard cap** … The enforced limit on total output tokens is still `max_tokens`"; "The countdown is visible only to the model. API responses do not include a remaining-budget field."

Two minor discrepancies, recorded but not material to the claim's usefulness (no edit made):

1. **Citation-target imprecision.** The file cites the claim to `…/prompting-claude-opus-4-8` (fetched 2026-06-12). That page covers effort, verbosity, subagents, etc., but says **nothing** about `task_budget`. The authoritative spec lives at `…/build-with-claude/task-budgets`. The cited URL does not substantiate the claim; the correct one does.
2. **Model-list incompleteness.** The file says "Fable 5 / Opus 4.7 / Opus 4.8 only." The live "Feature support" table also lists **Claude Mythos 5** as Beta (and confirms Opus 4.6 / Sonnet 4.6 / Haiku 4.5 are Not supported). The file omits Mythos 5. Whether Mythos 5 belongs in this repo's tier notes is an editorial call, not a correctness defect in the "only these tiers support it" exclusion of Sonnet/Haiku.

## Flags for operator

Nothing rises to a HALT (no diverged-stale skill file found; no convention-uncovered source conflict). Items below are advisory; no edits were made to any skill file in this task.

1. **(Low, tidy-up) graphviz-conventions.dot cosmetic drift.** The file's top comment asserts "Verified byte-identical 2026-04-17" while the body now carries one extra blank line (after `digraph STYLE_GUIDE {`) versus obra@6fd4507, introduced by the denubis header relocation in `8230047`. The April claim itself is sound (seed body SHA matches obra). Operator may choose to delete that one blank line to restore exact body byte-identity, or to soften the comment wording to "body verified byte-identical apart from the denubis attribution header." No correctness impact either way.
2. **(Recorded conflict, conservative gate already in place) Fable-advisor pairing.** The Claude Code vs platform API live-doc conflict over whether Fable may advise Haiku 4.5 / Sonnet 4.6 mains is confirmed still live as of 2026-06-12. `model-tier-notes.md` already records both sources and gates conservatively (automated-run advisors → Opus 4.8, never Fable). Left as-is per "Conflicting Authoritative Sources Are Recorded, Not Resolved."
3. **(Minor, citation) task-budget claim cites the wrong URL** (`prompting-claude-opus-4-8`, which does not mention `task_budget`) and **omits Mythos 5** from the supporting tier list. The claim's substance (beta header, 20,000 minimum, advisory-vs-enforced distinction) is correct and verifiable at `…/build-with-claude/task-budgets`. Operator may wish to repoint the citation and decide whether Mythos 5 belongs in the list.

---

## 2026-07-02 dated append — Sonnet 5 release pass (supersedes parts of the above)

The dispatch-time staleness tripwire (RESUME-PROMPT carry-forward #4) fired on Phase 4 Task 6 resume: **Claude Sonnet 5 shipped 2026-06-30** (`claude-sonnet-5`; announcement <https://www.anthropic.com/news/claude-sonnet-5>), after this sweep's 2026-06-12 verification. A re-verification pass was run 2026-07-02 against live vendor pages and committed to `model-tier-notes.md`. Effects on this record:

- **Flag #2 (Fable-advisor conflict) is superseded — dissolved by upstream convergence.** The platform API compatibility table (fetched 2026-07-02) now lists Fable 5 and Mythos 5 as accepted advisors for Haiku 4.5, Sonnet 4.6, Sonnet 5, and Opus 4.6+ executors, matching the Claude Code docs. A new recorded-not-resolved discrepancy replaces it: Claude Code accepts a Sonnet 5 advisor for Sonnet 5 / Sonnet 4.6 / Opus 4.6 mains; the platform table lists no Sonnet 5 advisor row for any executor.
- **Flag #3 (task-budget citation) is actioned.** Citation repointed to `…/build-with-claude/task-budgets`; Mythos 5 added to the beta list; Sonnet 5 recorded as explicitly not supported (live feature table now rows out Sonnet 5 and rows in Mythos 5); "not supported on Claude Code or Cowork surfaces" added.
- **Claim B ("advisor is a session main-loop feature only") is superseded by doc change.** Claude Code's advisor page (fetched 2026-07-02) states "Subagents inherit the configured advisor and apply the same pairing check against their own model." The closed frontmatter field set (no per-agent advisor field) remains true per the 2026-06-12 sub-agents fetch. `model-tier-notes.md` line-level claim updated with cost-gate consequence (advisor spend propagates to subagent fan-out).
- Flag #1 (graphviz-conventions.dot cosmetic drift) remains open, awaiting operator disposition.

Operator notes recorded 2026-07-02 in `model-tier-notes.md`: Sonnet 5 hallucination caution (operator-directed); Fable-tier availability is intermittent ("briefly back").
