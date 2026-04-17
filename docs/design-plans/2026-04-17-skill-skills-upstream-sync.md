# Skill-Skills Upstream Sync Design

**GitHub Issue:** None

## Summary

This design syncs four skill-authoring skills in the `denubis-extending-claude` plugin against upstream improvements in the obra/superpowers skill library. The work has two moving parts: adopting obra's architectural shape (thin orchestrators that delegate dense material to peer supporting files) and correcting stale or unverifiable content accumulated in earlier sessions (outdated model-specific claims, fabricated taxonomy codes misattributed to an academic paper).

The approach is hybrid. `writing-skills` gets a full cornerstone rewrite as a thin orchestrator that sequences the other two skills. `testing-skills-with-subagents` and `writing-claude-directives` are restructured in place, preserving verified denubis-specific material verbatim while grafting on obra improvements. A new fourth skill, `epistemic-humility`, is authored from scratch as a reference-type skill providing a rubric for whether any proposed skill earns its existence — sourced exclusively from verifiable content in `AbsenceJudgement.tex`. Each orchestrator cross-references this rubric on demand rather than inlining it. Progressive disclosure operates at two levels: across the four skills (orchestrators reference the rubric rather than embedding it) and within each skill (a thin SKILL.md delegates heavy material to peer files that load only when needed).

## Definition of Done

Four skill artifacts in `plugins/denubis-extending-claude/skills/` are brought up to date and tuned for Opus 4.7 / Sonnet 4.6 / Haiku 4.5:

- `writing-skills/` — **cornerstone orchestrator rewrite** aligned with obra/superpowers upstream. Thin orchestrator SKILL.md that sequences the other two skills. Adopts obra supporting files (`anthropic-best-practices.md`, `persuasion-principles.md`, `render-graphs.js`, `graphviz-conventions.dot`, `examples/CLAUDE_MD_TESTING.md`) adapted to our repo's conventions.
- `testing-skills-with-subagents/` — **restructure-in-place**. Absorb obra improvements (multi-factor pressure-scenario format, letter-vs-spirit bulletproofing, meta-testing) while preserving denubis-specific strengths verbatim (model-tier guidance, "no blaming the model", flaky-result discipline).
- `writing-claude-directives/` — **restructure-in-place**. Add Cialdini/Meincke persuasion section. Update model-specific notes for Opus 4.7 / Sonnet 4.6 / Haiku 4.5 (sourced from current Anthropic system cards and published guidance). Retire Opus-4.5-specific claims that no longer apply.
- **NEW:** `epistemic-humility/` — **reference-type skill** sourced from `AbsenceJudgement.tex`. Provides a rubric/checklist for when a skill (or any agent-scaffolded task) is structurally in-scope vs over-reaching. Invoked on demand by the three orchestrators when scope/epistemics questions arise. Cites only what is verifiably in the paper: technoscholasticism; Schön's four reflective-practitioner questions; Jones's scope-lever discipline (90%+ unrescued / bounded-reversible failure / fast-surface human rollback); failure patterns (temporality blindness, scope-confabulation, vibes-based operation, evidence accumulation without evaluation); success conditions (mechanical bounded tasks, heavy scaffolding, human-reserved synthesis).

**Theoretical spine (load-bearing, verified against sources):** Popper / Lakatos / Haraway / Carnap philosophy of science; proleptic reasoning (Kudina / Ballsun-Stanton / Alfano 2025); technoscholasticism + Schön's four questions + Jones's scope-lever (all from `AbsenceJudgement.tex` verbatim); Cialdini / Meincke persuasion research (from obra's `persuasion-principles.md`). **Prior handoff cited TEMP/RAND/SCOP/VIBE/FABR and MECH/MTCH/SCAF/BOUN codes — these are not in the paper and are not used.**

Success is observable as: all four skills pass a RED-GREEN-REFACTOR test with subagents per the `testing-skills-with-subagents` methodology; each orchestrator passes the `epistemic-humility` rubric applied to itself (see "rubric self-application is a coherence check, not a mechanical pass" in Additional Considerations); per-skill size targets are distinct — `writing-skills` is a thin orchestrator (≤250 lines; cornerstone rewrite from a 163-line stub), `testing-skills-with-subagents` grows modestly from absorbing obra additions and the conversation-precedent protocol (≤550 lines, up from current 421), `writing-claude-directives` shifts content from stale sections into new supporting files with a modest net delta (≤350 lines, from current 270); supporting files sit at peer level within each skill's directory; model-specific guidance references current (2026-04) Anthropic documentation.

**Explicitly out of scope for Part 1:**
- Other skill-skills (`writing-claude-md-files`, `maintaining-project-context`, `creating-a-plugin`, `creating-an-agent`) — touch only if a cross-reference change forces it.
- The critique skills / agents (Part 3).
- PromptGrimoireTool / MELICA tuning (Part 4).
- A standalone research-synthesis artifact — the research informs the rewrite; it is not itself a deliverable.
- Non-sync refactoring of the three incumbent skills unrelated to upstream alignment.

**Handoff:** The design-plan Phase 6 points at **Part 2's design session**, not an implementation plan. Part 2's design will scope which *other* upstream innovations (beyond skill-skills) to fold into the repo.

## Acceptance Criteria

### skill-skills-upstream-sync.AC1: `writing-skills` cornerstone rewrite
- **skill-skills-upstream-sync.AC1.1 Success:** `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md` exists with valid YAML frontmatter (`name`, `description` fields present)
- **skill-skills-upstream-sync.AC1.2 Success:** SKILL.md line count is ≤ 250 (thin-orchestrator target; small margin over the 200-line target in DR5)
- **skill-skills-upstream-sync.AC1.3 Success:** SKILL.md cross-references `testing-skills-with-subagents`, `writing-claude-directives`, and `epistemic-humility`; each reference resolves to an existing skill directory
- **skill-skills-upstream-sync.AC1.4 Success:** Supporting files exist: `anthropic-best-practices.md`, `render-graphs.js`, `examples/CLAUDE_MD_TESTING.md`
- **skill-skills-upstream-sync.AC1.5 Success:** Obra-imported files preserve attribution (Source line in frontmatter or top of file citing obra/superpowers origin)
- **skill-skills-upstream-sync.AC1.6 Failure:** Commit rejected if any obra-imported file lacks attribution or any cross-reference points at a non-existent skill or file
- **skill-skills-upstream-sync.AC1.7 Edge:** `test-requirements.md` for Phase 4 documents the RED precedent (prior transcript reference via `cc-search-chats:search-chat`, or explicit by-hand capture)

### skill-skills-upstream-sync.AC2: `testing-skills-with-subagents` restructure
- **skill-skills-upstream-sync.AC2.1 Success:** SKILL.md's RED phase section begins with the conversation-precedent protocol, cross-referencing `cc-search-chats:search-chat` and specifying the by-hand fallback
- **skill-skills-upstream-sync.AC2.2 Success:** Synthetic multi-stressor pressure scenarios are positioned as REFACTOR-phase completeness checks, not primary RED baseline (DR3)
- **skill-skills-upstream-sync.AC2.3 Success:** Model-tier guidance ("RED at production tier, GREEN one tier down"), "No Blaming the Model" principle, and flaky-result discipline all retained (grep-audit against current SKILL.md confirms presence)
- **skill-skills-upstream-sync.AC2.4 Success:** Obra's multi-factor pressure-scenario format absorbed (3+ combined stressors, A/B/C forced choice, concrete options)
- **skill-skills-upstream-sync.AC2.5 Success:** Rubric callback section present, references `epistemic-humility`
- **skill-skills-upstream-sync.AC2.6 Failure:** The specific claim "Haiku follows detailed instructions well but struggles with judgement calls" does not appear verbatim; if the tier-test principle appears, it's framed structurally (weakest tier = strongest clarity test) without the Haiku-specific assertion that contradicts current Anthropic docs
- **skill-skills-upstream-sync.AC2.7 Edge:** `test-requirements.md` for Phase 3 documents the RED precedent

### skill-skills-upstream-sync.AC3: `writing-claude-directives` restructure
- **skill-skills-upstream-sync.AC3.1 Success:** SKILL.md does not contain a section titled "Opus 4.5: 'Think' Sensitivity" (or equivalent) — stale claim fully removed
- **skill-skills-upstream-sync.AC3.2 Success:** `model-tier-notes.md` exists with separate sections for Opus 4.7, Sonnet 4.6, and Haiku 4.5; each section contains at least one citation URL to 2026 Anthropic documentation
- **skill-skills-upstream-sync.AC3.3 Success:** `persuasion-principles.md` imported from obra and adapted to denubis voice; obra attribution preserved
- **skill-skills-upstream-sync.AC3.4 Success:** SKILL.md has a Cialdini/Meincke persuasion section citing the 33%→72% compliance evidence
- **skill-skills-upstream-sync.AC3.5 Success:** `graphviz-conventions.dot` reconciled against obra's version; reconciliation result documented in the commit message or phase notes
- **skill-skills-upstream-sync.AC3.6 Success:** Rubric callback section present, references `epistemic-humility`
- **skill-skills-upstream-sync.AC3.7 Failure:** No claim cites Opus 4.5 as the current frontier model; every model-specific claim has an explicit model-version anchor (e.g. "Opus 4.7:")
- **skill-skills-upstream-sync.AC3.8 Edge:** `test-requirements.md` for Phase 2 documents the RED precedent and the Anthropic PDF consumption (system card content incorporated into `model-tier-notes.md`)

### skill-skills-upstream-sync.AC4: `epistemic-humility` reference skill
- **skill-skills-upstream-sync.AC4.1 Success:** `plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md` exists with reference-type frontmatter (description keyed to scope-assessment triggers)
- **skill-skills-upstream-sync.AC4.2 Success:** Rubric has four sections: Scope (Jones's three conditions), Observability, Process (Schön's four questions), Failure-pattern screen
- **skill-skills-upstream-sync.AC4.3 Success:** Every cited claim is attributable to `AbsenceJudgement.tex` with a page or section ref, or to a named secondary source (Schön 1994 p.132, Jones — citation located and verified)
- **skill-skills-upstream-sync.AC4.4 Failure:** No mention of TEMP, RAND, SCOP, VIBE, FABR, MECH, MTCH, SCAF, or BOUN as defined codes (grep-audit); if any of these strings appear, it must be in a rejection context explicitly citing DR4
- **skill-skills-upstream-sync.AC4.5 Edge:** Rubric self-application is a **coherence check, not a mechanical pass**. The rubric is a judgment aid — Schön's questions are reflective by design, not algorithmic. Self-application passes when the rubric demonstrably probes the same question categories it asks of other skills (i.e. the rubric's sections map back onto itself without contradiction), *not* when every checkbox is mechanically satisfied. A documented demonstration of this coherence (a written walk-through applying each rubric section to the rubric itself, noting where reflection is required and why) lives in the skill's body or a supporting file.

### skill-skills-upstream-sync.AC5: cross-cutting — version sync, cross-reference audit, commit discipline
- **skill-skills-upstream-sync.AC5.1 Success:** `plugins/denubis-extending-claude/.claude-plugin/plugin.json` version incremented from its pre-Phase-1 value
- **skill-skills-upstream-sync.AC5.2 Success:** `.claude-plugin/marketplace.json` at repo root contains a matching version for `denubis-extending-claude`
- **skill-skills-upstream-sync.AC5.3 Success:** `CHANGELOG.md` at repo root contains a new entry under the `[denubis-extending-claude]` heading at the appropriate version, following the project's New/Changed/Fixed format
- **skill-skills-upstream-sync.AC5.4 Success:** Cross-reference audit: every `denubis-extending-claude:<skill>` invocation in the four skills resolves to an existing skill directory; every supporting-file reference resolves to an existing file (grep-audit verified)
- **skill-skills-upstream-sync.AC5.5 Failure:** No commit uses `--no-verify`, `--amend` of a prior commit in this plan, or any forced operation (global CLAUDE.md git safety protocol)
- **skill-skills-upstream-sync.AC5.6 Edge:** Commits split per user's global preference (3+ files → 2+ commits, split by natural concern); tests and implementation for a given phase live in the same commit

## Glossary

- **obra/superpowers**: Upstream Claude Code plugin repository from which denubis-extending-claude is forked. Referred to as "obra" throughout; the source for supporting files (`anthropic-best-practices.md`, `persuasion-principles.md`, `render-graphs.js`, `graphviz-conventions.dot`, `examples/CLAUDE_MD_TESTING.md`) imported in this sync.
- **RED-GREEN-REFACTOR**: Adaptation of TDD's test lifecycle to skill validation. RED: establish a real failure baseline (broken behaviour observed in a prior conversation). GREEN: write the skill and confirm it fixes the observed failure. REFACTOR: tighten with synthetic pressure scenarios.
- **RED precedent**: The real prior-conversation transcript evidence that grounds the RED phase. Required before authoring or restructuring a skill; sourced via `cc-search-chats:search-chat` or a by-hand commissioned run.
- **progressive disclosure**: Architectural principle where an orchestrator's main surface stays terse by delegating dense material (model notes, persuasion data, worked examples) to peer supporting files loaded only when that section is relevant.
- **orchestrator (skill sense)**: A skill whose primary job is to sequence or cross-reference other skills rather than to contain all guidance inline. Distinguished from reference-type and technique-type skills.
- **reference-type skill**: A skill serving as on-demand documentation or a rubric — loaded when needed, not discipline-enforcing at invocation. The `epistemic-humility` skill is the first reference-type skill in `denubis-extending-claude`.
- **thin orchestrator**: An orchestrator that stays within a ~200-line target by delegating everything except sequencing logic to peer files or sub-skills.
- **rubric callback**: A section within an orchestrator skill that instructs the model to invoke `epistemic-humility` at scope-assessment decision points, rather than inlining scope-assessment criteria.
- **conversation-precedent methodology**: The practice of sourcing a skill's RED baseline from a real prior conversation transcript (retrieved via `cc-search-chats:search-chat`) rather than from scenarios the skill author invents.
- **technoscholasticism**: Term from `AbsenceJudgement.tex` for the failure pattern of treating textual authority (documentation, prior outputs, model outputs) as a substitute for empirical verification — manufacturing the appearance of evidence through citation rather than observation.
- **Schön's four reflective-practitioner questions**: Four questions from Donald Schön (1994, p.132) cited in `AbsenceJudgement.tex` for evaluating whether a practitioner (or skill) is operating within reflective competence. Used as the Process section of the `epistemic-humility` rubric.
- **Jones's scope-lever discipline**: A three-condition test from `AbsenceJudgement.tex` (attributed to Jones) for whether a task is safe to delegate: 90%+ of failures are unrescued without intervention, failures are bounded and reversible, and human rollback is fast-surface. Used as the Scope section of the `epistemic-humility` rubric.
- **AbsenceJudgement**: Academic paper (`AbsenceJudgement.tex`) co-authored by Brian Ballsun-Stanton, whose verifiable content grounds the `epistemic-humility` skill. The design explicitly restricts citations to content present in the file.
- **hybrid rewrite**: This design's strategy of applying a full cornerstone rewrite to `writing-skills` while applying restructure-in-place to the other two orchestrators.
- **restructure-in-place**: Editing an existing skill to absorb improvements and drop stale content while preserving verified denubis-specific material verbatim — as opposed to rewriting from a blank slate.
- **cornerstone rewrite**: A from-scratch rewrite that establishes the architectural shape other components depend on. Used for `writing-skills` because the current version is an effectively empty stub.
- **cc-search-chats:search-chat**: MCP tool providing search access to prior Claude Code conversation transcripts. Used in this design as the mechanism for sourcing RED precedent.
- **epistemic humility (the virtue)**: The intellectual disposition of accurately representing the limits of one's knowledge and evidence — the named virtue underlying the `epistemic-humility` reference skill and its rubric.
- **Cialdini/Meincke persuasion research**: Cialdini's seven principles of influence combined with Meincke et al. 2025 compliance data (showing structured requests improve compliance from 33% to 72%). Source material for the `persuasion-principles.md` supporting file imported from obra.
- **proleptic reasoning**: Anticipatory reasoning about potential objections or failure modes before they occur. Cited from Kudina/Ballsun-Stanton/Alfano 2025; already present in `denubis-plan-and-execute` skills and carried forward here.

## Architecture

Four skill artifacts compose a layered meta-skill stack for skill authoring. Three are orchestrators (discipline-enforcing, user-invoked or loaded-when-relevant) and one is a reference (loaded on demand). The architecture applies **progressive disclosure at two levels**: (a) across the four skills — the orchestrators cross-reference the reference skill rather than inlining its rubric; (b) within each skill — a thin SKILL.md delegates to peer supporting files that load only when their section is needed.

**Component map:**

- `plugins/denubis-extending-claude/skills/writing-skills/` — cornerstone orchestrator. Entry point for skill authoring. Thin SKILL.md (~150–200 lines target) sequencing `testing-skills-with-subagents` and `writing-claude-directives` as required sub-skills, with a rubric callback to `epistemic-humility`.
  - `SKILL.md` (rewritten)
  - `anthropic-best-practices.md` (obra import, adapted) — progressive disclosure, context-window-as-public-good, evaluation-driven development, paired-instance refinement
  - `render-graphs.js` (obra import verbatim) — Node.js CLI rendering Graphviz diagrams from SKILL.md to SVG
  - `examples/CLAUDE_MD_TESTING.md` (obra import, adapted) — worked test-campaign example

- `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/` — restructure-in-place orchestrator. Pressure-test methodology for skill validation.
  - `SKILL.md` (restructured) — absorbs obra's multi-factor pressure-scenario format and letter-vs-spirit bulletproofing; adopts conversation-precedent as primary RED baseline; preserves denubis model-tier guidance, "no blaming the model", flaky-result discipline; softens unverified Haiku-judgement claim; adds rubric callback section
  - Cross-reference dependency on `cc-search-chats:search-chat` for precedent sourcing

- `plugins/denubis-extending-claude/skills/writing-claude-directives/` — restructure-in-place orchestrator. Instruction-writing guidance (skills, CLAUDE.md, agent prompts, system prompts).
  - `SKILL.md` (restructured) — drops stale Opus 4.5 "think sensitivity" section; adds Cialdini/Meincke persuasion section; splits model-specific guidance into `model-tier-notes.md`; retires overtriggering claims superseded by 2026-04 Anthropic documentation for Opus 4.7 / Sonnet 4.6 / Haiku 4.5; adds rubric callback section
  - `persuasion-principles.md` (obra import, adapted) — Cialdini 7 principles + Meincke et al. 2025 compliance data (33%→72%)
  - `graphviz-conventions.dot` (verify vs obra; merge/replace) — flowchart style guide
  - `model-tier-notes.md` (new, denubis-authored) — Opus 4.7 / Sonnet 4.6 / Haiku 4.5 specifics, updatable without touching SKILL.md
  - `long-running-state-patterns.md` (unchanged unless implementation-phase research surfaces updates)

- `plugins/denubis-extending-claude/skills/epistemic-humility/` — **new** reference-type skill. Rubric for assessing whether a proposed skill (or agent-scaffolded task) earns its existence. Loaded on demand by the three orchestrators.
  - `SKILL.md` — rubric checklist: Scope (Jones's three conditions), Observability (not vibes), Process (Schön's four questions), Failure-pattern screen (AbsenceJudgement-named patterns)
  - `absencejudgement-citations.md` (optional, if token cost earned) — paragraph-level source quotations

**Data flow — meta-skill invocation pattern:**

```mermaid
flowchart LR
    User([User])
    WS[writing-skills]
    TSWS[testing-skills-with-subagents]
    WCD[writing-claude-directives]
    EH[epistemic-humility]
    Chats[(Prior conversations<br/>via search-chat)]

    User -->|"I want to write/edit a skill"| WS
    WS -->|"scope check"| EH
    WS -->|"validate via"| TSWS
    WS -->|"phrase directives via"| WCD
    TSWS -->|"source RED from"| Chats
    TSWS -->|"scope check"| EH
    WCD -->|"scope check"| EH
    WCD -->|"model specifics"| WCD
    EH -->|"pass/fail"| WS
    EH -->|"pass/fail"| TSWS
    EH -->|"pass/fail"| WCD
```

**System boundaries:** The stack consumes prior conversation transcripts (via existing `cc-search-chats:search-chat` plumbing) and produces/updates SKILL.md + supporting files. No runtime dependencies outside the skill tree; `render-graphs.js` requires Node.js but is dev-only (skill-author tool, not invoked at skill-use time).

## Decision Record

### DR1: Hybrid rewrite depth — cornerstone rewrite + restructure-in-place
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If implementation reveals `writing-skills` cornerstone rewrite duplicates content better kept in sub-skills (indicating the three-skill split itself needs revisiting); if `testing-skills-with-subagents` or `writing-claude-directives` absorb so much obra material that restructure-in-place becomes indistinguishable from rewrite.

**Decision:** We chose a hybrid rewrite strategy: `writing-skills` is rewritten from scratch as a thin cornerstone orchestrator, while `testing-skills-with-subagents` and `writing-claude-directives` are restructured in place — preserving denubis-specific content verbatim where it earns its place and grafting obra improvements onto the existing structure.

**Consequences:**
- **Enables:** Lowest-risk preservation of hard-won denubis-specific material (model-tier test calibration, "no blaming the model", flaky-result discipline, action-bias/overengineering-prevention templates); targets rewrite effort at the leanest and most outdated skill (`writing-skills`, currently 163 lines); lets the cornerstone adopt obra's architectural shape without dragging the other two through parallel rewrites.
- **Prevents:** Full voice-consistency across the three orchestrators (rewritten vs restructured skills will read slightly differently); parallel-rewrite-style parallelism with obra's one-skill structure.

**Alternatives considered:**
- **Restructure-in-place all three:** Rejected because `writing-skills` is effectively a 163-line stub that points at the other two; it needs a real orchestrator rewrite, not in-place edits.
- **Full-rewrite all three from obra base:** Rejected because it risks losing denubis-specific strengths the user flagged as preserved (model-tier guidance, "no blaming the model"); higher effort, lower reward.

### DR2: Four-artifact scope — add `epistemic-humility` as reference skill
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If the rubric proves not to generalise beyond skill authoring (i.e. is only ever invoked from these three orchestrators) and belongs as a supporting file inside one of them rather than a first-class skill; if implementation reveals the rubric is too short to earn skill-shaped status.

**Decision:** We chose to add a fourth artifact — a new reference-type skill `epistemic-humility` sourced from `AbsenceJudgement.tex` — rather than embedding the rubric as a supporting file inside one of the three orchestrators.

**Consequences:**
- **Enables:** Single authoritative locus for the rubric (not scattered across three sections in three skills); discoverability via skill description ("Use when assessing whether a proposed skill earns its existence"); future agents and skill-authors outside this three-skill loop can invoke it; cleaner progressive disclosure (the rubric loads only when scope questions arise).
- **Prevents:** Treating the rubric as an internal implementation detail of skill authoring; keeping DoD scope at three artifacts.

**Alternatives considered:**
- **Supporting file inside `writing-skills/`:** Rejected because weaker discoverability — agents looking up "is this skill well-scoped?" won't find a skill-shaped answer.
- **Embedded section in `writing-claude-directives`:** Rejected because it conflates directive-writing with scope-assessment; the rubric applies to more than directives.
- **Sibling skill named `assessing-skill-scope` (or similar):** Rejected in favour of `epistemic-humility` because the broader framing names the underlying virtue, not only the narrow application.

### DR3: Conversation-precedent methodology replaces synthetic scenarios as primary RED baseline
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If implementation reveals that conversation-precedent sourcing is consistently unavailable (no prior chats + no by-hand fallback practical) for common skill categories; if real transcripts prove too noisy to yield usable failure patterns.

**Decision:** We chose to revise `testing-skills-with-subagents` so the RED phase sources its baseline evidence from real prior conversations (via `cc-search-chats:search-chat`) or an explicit user-commissioned by-hand run, not from synthetic pressure scenarios invented by the skill author. Synthetic multi-stressor scenarios (obra's format) are demoted to REFACTOR-phase completeness checks.

**Consequences:**
- **Enables:** Falsifiable skill justification — every skill points at a real transcript where the failure manifested; alignment with the `epistemic-humility` rubric's observability principle (real evidence vs invented scenarios); skills defend against failures that actually occurred.
- **Prevents:** Writing skills that defend against failures the author imagined but did not observe (an instance of the vibes-based-operation failure pattern the rubric itself screens against); fast skill-spinning with no evidence base.

**Alternatives considered:**
- **Keep synthetic-scenarios-first (current methodology, obra's methodology):** Rejected because it risks writing skills from imagined rather than observed failures.
- **Conversation-precedent only, no synthetic scenarios at all:** Rejected because synthetic scenarios remain valuable in REFACTOR for exercising failure modes that precedent transcripts may not cover.

### DR4: `AbsenceJudgement.tex` citations restricted to verifiable content
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If the paper's author (Brian) surfaces a different source document that does define the TEMP/RAND/SCOP/VIBE/FABR failure codes and MECH/MTCH/SCAF/BOUN success codes; if a later revision of the paper introduces these codes officially.

**Decision:** We chose to cite `AbsenceJudgement.tex` only for content verifiable in the file: technoscholasticism; Schön's four reflective-practitioner questions (verbatim, attributed to Schön 1994 p.132); Jones's scope-lever three-condition test (90%+ unrescued / bounded-reversible / fast-surface); named failure patterns (temporality blindness, scope-confabulation, vibes-based operation, evidence-accumulation-without-evaluation); named success conditions (mechanical bounded tasks, heavy scaffolding, human-reserved synthesis).

**Consequences:**
- **Enables:** Honest attribution; avoidance of propagating fabricated acronyms through the repo; preservation of the paper's actual discipline (which is more general than a five/four-code taxonomy); agents and human readers can verify citations by opening the file.
- **Prevents:** Citing TEMP/RAND/SCOP/VIBE/FABR (failure codes) or MECH/MTCH/SCAF/BOUN (success codes) — these acronyms were fabricated by a prior Claude session and propagated through a session-resumption handoff as "load-bearing theoretical spine, NOT up for revision." They are not in the paper.

**Alternatives considered:**
- **Treat the fabricated codes as established vocabulary (accept the handoff):** Rejected because it misattributes content to a real academic paper Brian is an author on and builds skill-skills on a fake spine.
- **Coin our own four/five-code taxonomy for the paper's patterns:** Rejected because (a) not needed — the prose descriptions are already usable; (b) inventing taxonomies after fabrication is suspect; (c) the paper critiques exactly this kind of textual-authority manufacture (technoscholasticism).

### DR5: Progressive disclosure at two architectural levels
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If implementation reveals orchestrators cannot stay within the ~200-line target without losing load-bearing content (indicating the target is wrong or the content needs further decomposition); if supporting-file proliferation makes navigation harder than monolithic SKILL.md would have.

**Decision:** We chose to apply progressive disclosure at two levels: across the four skills (orchestrators reference the `epistemic-humility` rubric on demand, not inline); and within each skill (thin SKILL.md delegates to peer supporting files that load only when their section is needed).

**Consequences:**
- **Enables:** Every orchestrator stays terse and scannable; dense material (persuasion data, model-tier notes, graphviz conventions, worked examples) stays accessible via supporting files but doesn't bloat the main surface; refresh cycles decouple (model notes updatable without touching SKILL.md orchestrator).
- **Prevents:** Fat monolithic SKILL.md files that degrade Claude's discovery and compliance under token pressure; tight coupling between orchestration and reference content.

**Alternatives considered:**
- **Single-file orchestrators (no supporting files within a skill):** Rejected because dense reference material (persuasion, model notes, examples) belongs outside the skim path.
- **Progressive disclosure only within skills, with an internal rubric section:** Rejected because it violates the cross-skill discoverability rationale from DR2.

## Existing Patterns

Investigation surfaced several patterns this design follows and one it establishes.

**Orchestrator + sub-skill pattern (denubis, established).** Already used in `denubis-plan-and-execute:starting-a-design-plan` (orchestrates `brainstorming`, `asking-clarifying-questions`, `writing-design-plans`, `proleptic-challenge`) and in the plan-and-execute skill tree generally. The four-skill stack adopts this pattern at both the three-skill level (writing-skills orchestrates the other two) and, internally, each restructured skill delegates dense material to peer supporting files.

**Progressive disclosure (obra, adopted).** Obra/superpowers' `writing-skills/` already ships a thin SKILL.md delegating to peer supporting files (`anthropic-best-practices.md`, `persuasion-principles.md`, `render-graphs.js`, `graphviz-conventions.dot`, `examples/CLAUDE_MD_TESTING.md`). This design imports that architectural pattern.

**Reference-type skills (obra taxonomy, applied).** Obra's `writing-skills/SKILL.md` documents three skill types: Technique, Pattern, and Reference. Reference skills are API docs, syntax guides, tool documentation — loaded when needed, not discipline-enforcing. The new `epistemic-humility` skill is the first reference-type skill added under `denubis-extending-claude/`.

**Graphviz conventions (existing, to verify against obra).** We already ship `writing-claude-directives/graphviz-conventions.dot` (5.8K). Obra ships a file of the same name in `writing-skills/`. Implementation Phase 2 performs a diff and either merges to superset or replaces with obra's version where strictly better — decision deferred to that phase because it requires seeing both files side-by-side.

**Plugin version discipline (repo convention, CLAUDE.md).** This repo's CLAUDE.md mandates that plugin version bumps sync across `plugins/denubis-extending-claude/.claude-plugin/plugin.json`, repo-root `.claude-plugin/marketplace.json`, and `CHANGELOG.md`. A substantial edit to this plugin's skill tree qualifies for a version bump; Phase 5 handles it.

**Theoretical spine (existing, verified).** Popper/Lakatos/Haraway/Carnap philosophy of science and proleptic reasoning (Kudina/Ballsun-Stanton/Alfano 2025) are already referenced across `denubis-plan-and-execute` skills. This design adds three further well-sourced references: technoscholasticism, Schön's four questions, and Jones's scope-lever — all from `AbsenceJudgement.tex`. No taxonomic codes (TEMP/RAND/SCOP/VIBE/FABR or MECH/MTCH/SCAF/BOUN) are introduced; DR4 documents why.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Author `epistemic-humility` reference skill

**Goal:** Establish the rubric as a first-class skill before any orchestrator invokes it. This is the cornerstone dependency for Phases 2–4.

**Components:**
- `plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md` (new, reference-type) — rubric checklist with four sections (Scope, Observability, Process, Failure-pattern screen); frontmatter description keyed to scope/epistemics triggers; paragraph-level citations into `/home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex` with page/section refs
- `plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md` (optional — author only if rubric SKILL.md cannot include enough source quotation without bloating past the reference-skill form)
- A written demonstration of rubric self-application (per AC4.5) — the walk-through lives in the SKILL.md body or a small supporting file called `self-application.md`
- Cross-reference stanza written but invocations in the other three skills are deferred to Phases 2–4

**Source artefact:** `/home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex` (outside this repo). Read locally during Phase 1 implementation. All rubric claims must be verifiable against this file (DR4 gate). Per DR4, the codes TEMP/RAND/SCOP/VIBE/FABR and MECH/MTCH/SCAF/BOUN are not in the file and are explicitly rejected.

**Dependencies:** None (first phase). External dependency on the AbsenceJudgement.tex file path above being accessible at implementation time.

**Done when:**
- The skill exists at its path with valid frontmatter
- Rubric sections read against `AbsenceJudgement.tex` — no claim cites something not in the file (DR4 compliance check)
- Rubric applied to itself passes: scope is mechanical/bounded (rubric is a checklist), triggers are observable (discrete skill-assessment moments), Schön's four questions answer in the affirmative for the rubric itself, Jones's three conditions hold
- No cross-references to other three skills yet (they're rewritten in later phases)
- Acceptance criteria covered: `skill-skills-upstream-sync.AC4.*`
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Restructure `writing-claude-directives`

**Goal:** Current (2026-04) model-tier guidance, persuasion-principles adoption, drop stale Opus-4.5 content, add rubric callback.

**Components:**
- `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md` (restructured) — drop "Opus 4.5: 'Think' Sensitivity" section entirely; replace with pointer to `model-tier-notes.md`; retire any claim superseded by 2026-04 Anthropic documentation (e.g. "aggressive language causes overtriggering" for Claude 4.x — validate against docs); add short rubric callback section referencing `epistemic-humility`; add Cialdini/Meincke persuasion section with 33%→72% compliance evidence pointing into `persuasion-principles.md`
- `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` (new) — Opus 4.7 (literal, strict effort levels, fewer tools + more reasoning, steerable adaptive thinking); Sonnet 4.6 (proactive default, adaptive thinking, dial-back aggressive language); Haiku 4.5 (strong instruction-following, 128k extended thinking, no documented judgment weakness — soften any denubis claims to the contrary); sourced from today's research pass + the Anthropic system card PDF at `/tmp/anthropic-system-card.pdf` (consume in this phase)
- `plugins/denubis-extending-claude/skills/writing-claude-directives/persuasion-principles.md` (obra import, adapted) — Cialdini 7 + Meincke et al. 2025 data
- `plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot` (verify vs obra's version — diff, merge to superset, or replace if obra's is strictly better)
- `plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md` (unchanged unless research surfaces updates)

**Dependencies:** Phase 1 (epistemic-humility exists to be invoked).

**Done when:**
- SKILL.md is restructured per above; no residual Opus 4.5 claims
- `model-tier-notes.md` cites 2026-04 Anthropic documentation + system card; every model claim has a source URL
- `persuasion-principles.md` imported and adapted (denubis voice, attribution to obra preserved)
- `graphviz-conventions.dot` reconciled against obra
- Rubric callback section references `epistemic-humility`
- **RED precedent transcript exists, one way or the other:** either the author locates prior transcripts via `cc-search-chats:search-chat`, OR the user runs a by-hand session against the skill's problem space and that transcript is made available. This is a binary gate — the phase does not proceed to GREEN without a transcript on file.
- GREEN verified against pressure scenarios absorbed from obra; REFACTOR closes all loopholes surfaced
- Rubric self-application passes (coherence check per Additional Considerations)
- Acceptance criteria covered: `skill-skills-upstream-sync.AC3.*`
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Restructure `testing-skills-with-subagents`

**Goal:** Conversation-precedent methodology (DR3), obra additions (multi-factor pressure scenarios, letter-vs-spirit bulletproofing, meta-testing), preservation of denubis strengths (model-tier, no blaming, flaky-result), soften Haiku judgment-call claim.

**Components:**
- `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` (restructured) — prepend conversation-precedent protocol at the top of the RED phase (DR3); demote synthetic pressure scenarios to REFACTOR-phase completeness checks; absorb obra's multi-factor pressure-scenario format (3+ combined stressors, A/B/C forced choice, realistic constraints); add letter-vs-spirit bulletproofing principle; add meta-testing pattern from obra; soften the "Haiku struggles with judgement calls" claim (keep the tier-test principle, drop the unverified specific); add rubric callback section referencing `epistemic-humility`; cross-reference dependency on `cc-search-chats:search-chat` for precedent sourcing documented in frontmatter or a Dependencies section

**Dependencies:** Phase 1 (rubric exists); Phase 2 is not a strict dependency but implementation Phase 2's RED precedent-finding activity may surface patterns worth documenting in this phase's revised RED protocol.

**Done when:**
- SKILL.md is restructured per above
- Conversation-precedent protocol explicitly cross-references `cc-search-chats:search-chat` and specifies the by-hand fallback as the binary alternative (not an optional fallback)
- All denubis-specific strengths are preserved verbatim: model-tier guidance (RED at production, GREEN one tier down), "No Blaming the Model", flaky-result discipline
- Haiku judgement-call claim softened (specifics dropped; structural principle kept)
- Rubric callback section references `epistemic-humility`
- **RED precedent transcript exists, one way or the other:** either prior skill-testing session transcripts via `cc-search-chats:search-chat`, OR a user-commissioned by-hand run against the skill's own problem space whose transcript is made available. Binary gate — phase does not proceed to GREEN without a transcript on file.
- GREEN verified; REFACTOR closed loopholes
- Rubric self-application passes (coherence check)
- Acceptance criteria covered: `skill-skills-upstream-sync.AC2.*`
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Rewrite `writing-skills` as cornerstone orchestrator

**Goal:** Replace the current 163-line stub with a thin cornerstone orchestrator that sequences the other two skills and cross-references the rubric. Adopt obra's supporting-file shape.

**Components:**
- `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md` (rewritten) — thin orchestrator (~150–200 lines target); entry-point description keyed to skill-authoring triggers; sections: Core Principle (TDD-for-process-documentation, Iron Law), When to Create a Skill (with rubric callback), Skill Types, Directory Structure, Workflow (calls `testing-skills-with-subagents` for RED/GREEN/REFACTOR, `writing-claude-directives` for phrasing/compliance, `epistemic-humility` for scope), Anti-Patterns, Checklist
- `plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md` (obra import, adapted) — progressive disclosure, context-as-public-good, evaluation-driven development, paired-instance refinement
- `plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js` (obra import verbatim) — Node.js CLI tool; add README note calling out Node dependency
- `plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md` (obra import, adapted) — worked test-campaign example; denubis-voice adaptation minimal (example content is illustrative, not discipline-enforcing)

**Dependencies:** Phases 1, 2, 3 (orchestrator invokes all three).

**Done when:**
- SKILL.md rewritten; line count within target (≤250)
- Cross-references to the other three skills all resolve (verified by reading the target skills)
- Supporting files imported with attribution
- **RED precedent transcript exists, one way or the other:** skill-authoring session transcripts via `cc-search-chats:search-chat`, OR a user-commissioned by-hand session on "write a new skill from scratch" whose transcript is made available. Binary gate.
- GREEN verified; REFACTOR closed loopholes
- This phase's production is the integration evidence called out in the Definition of Done — the cornerstone was authored using precedent-based RED + rubric self-application
- Rubric self-application passes (coherence check)
- Acceptance criteria covered: `skill-skills-upstream-sync.AC1.*`
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Cross-reference audit, version bump, commit

**Goal:** Verify all cross-references resolve end-to-end; apply repo's version-sync convention; commit as a coherent set.

**Components:**
- Cross-reference audit: every `denubis-extending-claude:X` invocation in the four skills points at a skill that exists; every supporting-file reference (`anthropic-best-practices.md`, `persuasion-principles.md`, etc.) points at a file that exists
- Plugin version bump: `plugins/denubis-extending-claude/.claude-plugin/plugin.json` version increment per repo convention
- `.claude-plugin/marketplace.json` version sync at repo root
- `CHANGELOG.md` entry at repo root under `[denubis-extending-claude]` heading per the project CLAUDE.md format (New / Changed / Fixed sections)
- Commit(s): per user's global commit preference (3+ files → 2+ commits), split by natural concern (one commit per skill-phase, or grouped by skill, with cross-ref/version-sync as its own commit)

**Dependencies:** Phases 1, 2, 3, 4.

**Done when:**
- All cross-references resolve (audit verified by grepping invocations against file paths)
- `plugin.json`, `marketplace.json`, and `CHANGELOG.md` versions match
- Git commits exist with conventional-commit-style messages; no amends; no forced operations
- Design doc's exit criteria all check: four artifacts exist, each has documented RED precedent, each passed GREEN, each passed rubric self-application, writing-skills + epistemic-humility production are documented as integration evidence
- Acceptance criteria covered: `skill-skills-upstream-sync.AC5.*`
<!-- END_PHASE_5 -->

## Additional Considerations

**Rubric self-application is a coherence check, not a mechanical pass.** The `epistemic-humility` rubric is a judgment aid — Schön's four questions are reflective by design, not algorithmic. Applying the rubric to itself is a demonstration that the rubric's question categories coherently probe the artefact they are applied to. It is *not* a mechanical checkbox exercise, and claiming otherwise would smuggle in exactly the vibes-vs-observable confusion the rubric screens against. AC4.5 codifies this. Phase 1 produces a written walk-through of the self-application in the skill's body or a small supporting file, so the coherence claim is inspectable rather than merely asserted.

**Conversation-precedent is a binary gate, not an optional fallback.** Every phase that authors or restructures a skill (Phases 2, 3, 4) requires a RED transcript before proceeding to GREEN. The transcript comes from one of two sources — prior transcripts retrieved via `cc-search-chats:search-chat`, or a user-commissioned by-hand run whose transcript is captured and made available. There is no "skip the precedent" path. If neither source produces a transcript on implementation day, the phase blocks for human decision (commission a run, or re-scope). The design treats this as a feature, not a friction: skills authored without transcripts would violate DR3's rationale.

**Model-note staleness.** `writing-claude-directives/model-tier-notes.md` will age as Anthropic releases new models. The structural decision (DR5) to split model notes into a supporting file lets them be refreshed without touching the orchestrator. Add a dated header (`_Last verified: 2026-04-17_`) so staleness is observable.

**Anthropic documentation sourcing for Phase 2.** Primary sources for `model-tier-notes.md` are URLs from current (2026-04) Anthropic web documentation (platform.claude.com, anthropic.com, docs.claude.com) — AC3.2 specifies URLs. The system card PDF at `/tmp/anthropic-system-card.pdf` (downloaded, 13.6MB, PDF 1.4) is a supplementary source to be consumed during Phase 2 implementation via `pdftotext` or Read tool (selective pages) for cross-verification, not the primary citation.

**Obra upstream drift.** This is a one-time sync, not an ongoing automation. Future drift handled by Part 2's programme (upstream innovations beyond skill-skills). Supporting files imported from obra preserve attribution so future-us can compare against a point-in-time origin.

**Fabricated-codes propagation.** DR4 records that prior-session handoffs contained fabricated AbsenceJudgement codes. A feedback memory has been saved at `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/feedback_absencejudgement-codes-fabricated.md` to prevent re-introduction. Implementation Phases 1 and 4 should grep-audit all four skills for `TEMP\|RAND\|SCOP\|VIBE\|FABR\|MECH\|MTCH\|SCAF\|BOUN` and fail the phase if any are found outside quoted-rejection contexts.

**Render-graphs.js dependency.** `render-graphs.js` requires Node.js. This is skill-author tooling (invoked manually when visualising Graphviz diagrams in SKILL.md), not runtime. Phase 4 adds a `README.md` note in `writing-skills/` calling out the dependency. No `package.json` needed — the tool is a standalone CLI.

**Integration evidence, not integration test.** Per user clarification during brainstorming: today is a refactoring day, not integration-test day. The two from-scratch artifacts (`writing-skills` cornerstone rewrite, `epistemic-humility` new skill) are *themselves* integration evidence because they were produced using the methodology they describe. No separate integration test is authored.
