<!-- Provenance: Fable fan-out, workflow run wf_2288cbc8-d9b, one agent per plugin.
Run started 2026-07-02, completed 2026-07-03 after quota-limit resume. Findings only. -->

# Model-Anchor Sweep — 2026-07-02

Post-Sonnet-5-release sweep (Sonnet 5 shipped 2026-06-30) of every file in all 14 plugins for
Claude model references, classified against rubric R6 (model-specific claims belong in dated
supporting files — `docs/audits/2026-06-10-rubric-for-rubrics-draft.md`, pending item 4) and
for staleness (Sonnet 4.6 is now previous-generation).

**Classifications:** `stale` = treats a superseded model as current; `r6-violation` = inline
model anchor in a SKILL.md body or agent prompt; `uncertain` = agent could not classify
confidently. Correctly-dated references (model-tier-notes.md, changelogs, historical records)
are aggregated as counts, not enumerated.

**Operator-judgement caveat (orchestrating session, 2026-07-03):** several `r6-violation`
findings flag agent-frontmatter *descriptions* ("Uses Sonnet for structured checklist
evaluation"). Model pins in agent definitions are deliberate routing choices, not staleness;
whether their descriptions' model rationale belongs in dated files is an R6 interpretation
question for the operator, not a settled defect. Treat those four plan-and-execute findings
as candidates, not convictions.

**Relationship to the upstream-sync plan:** the `writing-claude-directives/SKILL.md` findings
(lines 69, 96 — "Current Claude models (… Sonnet 4.6 …)") are in this plan's own Phase 2
deliverable and pair with the V5 carry-forward (inline model anchors in
`testing-skills-with-subagents`). Reconcile at the Phase 4/5 boundary alongside
`model-tier-notes.md`, which was re-verified 2026-07-02 and is the sanctioned home.

## Findings by plugin


### denubis-basic-agents — 10 files scanned, 32 model refs, 5 findings

| Class | File:line | Reference | Note |
|---|---|---|---|
| stale | `denubis-basic-agents/skills/using-generic-agents/SKILL.md:29` | ## Model Characteristics (Sonnet 4.6 era) | Section header anchors the skill's current-guidance section to Sonnet 4.6; Sonnet 5 shipped 2026-06-30, so the 4.6 era framing is previous-generation. |
| stale | `denubis-basic-agents/skills/using-generic-agents/SKILL.md:35` | **Sonnet 4.6:** The daily driver. Near-parity with Opus on SWE-bench (79.6% vs 80.8%) ...  | Presents Sonnet 4.6 as the current daily driver with 4.6-era SWE-bench numbers and pricing; superseded by Sonnet 5. |
| r6-violation | `denubis-basic-agents/skills/using-generic-agents/SKILL.md:17` | Near Opus-level on software engineering tasks at 1/5 the cost. | Benchmark/pricing claim inline in the SKILL.md routing table; belongs in a dated supporting file, and the 1/5-cost figure is 4.6-era. |
| r6-violation | `denubis-basic-agents/skills/using-generic-agents/SKILL.md:33` | **Haiku:** Excels at following specific, detailed instructions with tool calls... | Model-specific capability characterization inline in a SKILL.md body (part of the 4.6-era section); R6 says this lives in a dated supporting file. |
| r6-violation | `denubis-basic-agents/skills/using-generic-agents/SKILL.md:37` | **Opus:** Strongest at deep reasoning (17-point lead over Sonnet on GPQA Diamond)... | Inline benchmark claim in SKILL.md body; comparison is against Sonnet 4.6, so the 'gap has narrowed' guidance is also previous-generation vs Sonnet 5. |

Dated/OK references (not violations): `denubis-basic-agents/agents/haiku-general-purpose.md` (3), `denubis-basic-agents/agents/sonnet-general-purpose.md` (3), `denubis-basic-agents/agents/opus-general-purpose.md` (3), `denubis-basic-agents/agents/python-developer.md` (2), `denubis-basic-agents/agents/academic-researcher.md` (2), `denubis-basic-agents/skills/using-generic-agents/SKILL.md` (7)

### denubis-extending-claude — 24 files scanned, 95 model refs, 8 findings

| Class | File:line | Reference | Note |
|---|---|---|---|
| stale | `denubis-extending-claude/skills/writing-claude-directives/SKILL.md:69` | Current Claude models (Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5) | Lists Sonnet 4.6 as current; Sonnet 5 shipped 2026-06-30. Also an inline model list in SKILL.md body (R6) despite pointing at model-tier-notes.md. |
| stale | `denubis-extending-claude/skills/writing-claude-directives/SKILL.md:96` | Current Claude models (Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5) overtrigger on these mark | Same now-wrong 'current' list, plus an inline per-model behavioral claim (verified 2026-06-10) that R6 says belongs in model-tier-notes.md. |
| r6-violation | `denubis-extending-claude/skills/writing-claude-directives/SKILL.md:98` | On Opus 4.8 and Fable 5 ... it overtriggers Sonnet 4.6 and the Opus 4.6 tier | Inline model-specific triggering claims in SKILL.md body; Sonnet 4.6 anchor is now previous-generation, so guidance needs Sonnet 5 re-verification too. |
| r6-violation | `denubis-extending-claude/skills/writing-claude-directives/SKILL.md:127` | On Fable 5, show-your-thinking phrasing can trigger the reasoning_extraction refusal categ | Fable 5 is still current (not stale), but this dated per-model behavioral claim sits inline in the SKILL.md body instead of model-tier-notes.md. |
| r6-violation | `denubis-extending-claude/skills/writing-claude-directives/SKILL.md:217` | Current Opus 4.8 and Fable 5 models tend to overengineer | Inline 'current' model anchor + behavioral claim in SKILL.md body; it cross-references model-tier-notes.md where the claim already lives. |
| r6-violation | `denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md:63` | Haiku 4.5 ... Sonnet 4.6 and Opus 4.8 will follow them easily | Version-anchored model claims (incl. operator-experience 2026-04-22) inline in SKILL.md body; Sonnet 4.6 used as the operative Sonnet tier, now superseded by Sonnet 5. |
| uncertain | `denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md:3` | Last verified: 2026-04-23. Model anchors: Opus 4.7 / Sonnet 4.6 / Haiku 4.5 | Dated supporting file, so R6-compliant in form (8 refs incl. Opus 4.7 orchestration/pricing tables). But anchors now trail Opus 4.8 and Sonnet 5; model-tier-notes' own rule says treat as unverified and re-verify. |
| uncertain | `denubis-extending-claude/agents/project-claude-librarian.md:44` | other AI agents (Codex, Copilot) can also use it | Third-party name inline in an agent prompt, but it is an AGENTS.md-ecosystem mention, not a model-tier or currency claim; likely fine, flagged only because 'codex' was in scope. |

Dated/OK references (not violations): `denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` (58), `denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md` (5), `denubis-extending-claude/skills/creating-an-agent/SKILL.md` (8), `denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` (6), `denubis-extending-claude/skills/syncing-with-upstream/SKILL.md` (1), `denubis-extending-claude/agents/project-claude-librarian.md` (1), `denubis-extending-claude/skills/writing-claude-directives/SKILL.md` (1)

### denubis-plan-and-execute — 101 files scanned, 36 model refs, 6 findings

| Class | File:line | Reference | Note |
|---|---|---|---|
| r6-violation | `denubis-plan-and-execute/agents/task-bug-fixer.md:3` | Uses Sonnet for root cause understanding. | Tier-capability rationale inline in agent description. The frontmatter pin (model: sonnet) is deliberate and fine; the undated capability claim should live in a dated supporting file. Borderline: tier alias, no version. |
| r6-violation | `denubis-plan-and-execute/agents/test-analyst.md:3` | Uses Sonnet for structured coverage analysis. | Same pattern: inline tier-capability rationale in agent description duplicating the deliberate frontmatter pin. Not stale (alias-level), but the model-specific claim belongs in a dated file per R6. |
| r6-violation | `denubis-plan-and-execute/agents/task-implementor.md:3` | Uses Opus for reliable implementation with halt-on-failure policy. | Inline tier-capability rationale ('Opus for reliable implementation') in agent description. Pin itself is deliberate; the reliability claim is undated model-specific reasoning that ages silently. |
| r6-violation | `denubis-plan-and-execute/agents/code-reviewer.md:3` | Uses Sonnet for structured checklist evaluation. | Same pattern: inline tier-capability rationale in agent description. Frontmatter pin OK; the capability claim belongs in the dated model-tier-notes home. |
| uncertain | `denubis-plan-and-execute/skills/critical-peer-review/SKILL.md:9` | (Adapted from Codex critical-crash-review protocol, enhanced with ACH, GRADE, ABP, and pre | Third-party model name (Codex) inline in SKILL.md body, but as undated provenance attribution, not a capability/era claim. R6 targets model claims; this reads more as R12 scar tissue (provenance belongs in git history). |
| uncertain | `denubis-plan-and-execute/skills/systematic-debugging/SKILL.md:421` | (Adapted from Codex critical-crash-review protocol.) | Same Codex provenance attribution inline in a SKILL.md body. Not a model capability claim, so not clearly R6; undated attribution arguably belongs in commit history per R12. |

Dated/OK references (not violations): `denubis-plan-and-execute/agents/task-bug-fixer.md` (1), `denubis-plan-and-execute/agents/test-analyst.md` (1), `denubis-plan-and-execute/agents/task-implementor.md` (1), `denubis-plan-and-execute/agents/code-reviewer.md` (1), `denubis-plan-and-execute/agents/proleptic-challenger.md` (1), `denubis-plan-and-execute/agents/smell-assessor.md` (1), `denubis-plan-and-execute/agents/dba-reviewer.md` (1), `denubis-plan-and-execute/agents/critical-peer-review.md` (1), `denubis-plan-and-execute/agents/refactoring-executor.md` (1), `denubis-plan-and-execute/agents/coherence-reviewer.md` (1), `denubis-plan-and-execute/skills/maintain-architecture/SKILL.md` (3), `denubis-plan-and-execute/skills/exec-session-naming/SKILL.md` (9), `denubis-plan-and-execute/skills/design-write/SKILL.md` (1), `denubis-plan-and-execute/skills/design-clarify/SKILL.md` (1), `denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (2), `denubis-plan-and-execute/docs/workflow-status-line.md` (1), `denubis-plan-and-execute/scripts/workflow_statusline/tests/test_bar.py` (1), `denubis-plan-and-execute/scripts/workflow_statusline/tests/test_main.py` (2)

### denubis-research-agents — 9 files scanned, 8 model refs, 1 findings

| Class | File:line | Reference | Note |
|---|---|---|---|
| r6-violation | `denubis-research-agents/skills/using-research-agents/SKILL.md:13` | Agent Selection table, Model column: 'Haiku' on lines 13-16 | Inline model anchor in SKILL.md body. Not stale (mirrors deliberate haiku frontmatter pins, no currency/tier claim), but the column duplicates frontmatter and drifts silently if an agent is re-pinned; R6 puts model claims in dated files. |

Dated/OK references (not violations): `denubis-research-agents/agents/codebase-investigator.md` (1), `denubis-research-agents/agents/internet-researcher.md` (1), `denubis-research-agents/agents/combined-researcher.md` (1), `denubis-research-agents/agents/remote-code-researcher.md` (1)

## Clean plugins (zero model references or all correctly dated)

`denubis-00-getting-started` (4 files), `denubis-bibliography` (8 files), `denubis-crash-recovery` (39 files), `denubis-git-commit` (2 files), `denubis-hook-branch-bg` (3 files), `denubis-hook-claudemd-reminder` (5 files), `denubis-hook-gh-fork-guard` (4 files), `denubis-hook-pretooluse-dispatcher` (4 files), `denubis-hook-shortcut-detection` (6 files), `denubis-hook-skill-reinforcement` (5 files)


**Totals:** 20 enumerated findings across 4 plugins; 10 plugins clean.
