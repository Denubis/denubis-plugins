# Phase 2 RED Evidence — Static Code-Smell Inventory

**Source:** Phase 2B investigator file-read findings (2026-04-17) + 2026-04-22 independent-session search confirming no in-chat RED candidates exist.
**Restructure framing:** PREVENTIVE (not corrective). No prior session has been observed failing at the listed deficiencies.
**Pre-restructure SKILL.md SHA:** `ec7c88757a59ce21b86d7fa05f3981e3ce52c640`
**Pre-restructure long-running-state-patterns.md SHA:** `0d380227af400bfc94d9644899fd9b485fc6a124`
**Pre-restructure graphviz-conventions.dot SHA:** `3509e2f028cacaa8118cbc8c80025efb089ec28e` (recorded for completeness; attribution-only reconciliation in Task 4)

## Code-smell inventory

Line numbers verified against the pre-restructure SHAs above via `Read` at evidence-capture time (2026-04-22 plan-amendment pass). Numbers will drift once Task 2 / Task 3.5 apply edits.

### `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md`

| File | Line | Current text (quoted) | Deficiency |
|------|------|-----------------------|------------|
| SKILL.md | 69 | `Claude 4.x models are highly responsive to instructions. Lead with context and motivation; reserve imperatives for critical boundaries.` | Generic `Claude 4.x` anchor — AC3.7 requires per-model (`Opus 4.7 / Sonnet 4.6 / Haiku 4.5`) with pointer to `model-tier-notes.md`. |
| SKILL.md | 96 | `For Claude 4.x, aggressive language ("YOU MUST", "CRITICAL") can cause overtriggering. Use normal language first:` | Generic `Claude 4.x` anchor; also missing the current Anthropic prompting-best-practices URL and the concrete before/after example required by design DR3. |
| SKILL.md | 99 | `# Often sufficient for 4.x` (in-example comment) | Undifferentiated `4.x` anchor in a code-comment slot — must become per-model or drop the version marker. |
| SKILL.md | 215-220 | H3 subsection `### Opus 4.5: "Think" Sensitivity` plus its body (three `think`-variant replacement bullets) | Stale model-version anchor. Opus 4.5 is superseded by Opus 4.7 (2026-04). The entire subsection is the target deletion per AC3.1; no known Opus 4.7 equivalent to the "think-word sensitivity" claim has surfaced in the current Anthropic prompting docs, so it goes rather than getting rewritten. |
| SKILL.md | 237 | `Aggressive language for 4.x` (Common Mistakes table cell) | Generic `4.x` anchor in a table cell — update to "current models" with back-pointer to the primary aggressive-language discussion. |

### `plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md`

| File | Line | Current text (quoted) | Deficiency |
|------|------|-----------------------|------------|
| long-running-state-patterns.md | 15 | `**Token Budget Awareness**: Claude 4.5+ receives updates on remaining context after tool calls. Enables better task persistence and strategy adjustment.` | `Claude 4.5+` floor anchor — Opus/Sonnet 4.5 are superseded; needs per-model anchoring to Opus 4.7 / Sonnet 4.6 / Haiku 4.5. |
| long-running-state-patterns.md | 114 | `Orchestrator (Opus 4.5)` inside ASCII diagram | `Opus 4.5` superseded; update to `Opus 4.7`. |
| long-running-state-patterns.md | 119 | `Subagents (Sonnet/Haiku 4.5)` inside ASCII diagram | `Sonnet 4.5` superseded; update to `Sonnet 4.6 / Haiku 4.5` (Haiku 4.5 preserved — current 2026-04 shipping model). |
| long-running-state-patterns.md | 132 | `\| Opus 4.5 \| Orchestration, complex planning \| $15/M output \|` (Model Selection table) | `Opus 4.5` superseded; update to `Opus 4.7`. |
| long-running-state-patterns.md | 133 | `\| Sonnet 4.5 \| Focused implementation \| $15/M output \|` (Model Selection table) | `Sonnet 4.5` superseded; update to `Sonnet 4.6`. |
| long-running-state-patterns.md | 134 / 136 | `\| Haiku 4.5 \| Simple tasks (90% of Sonnet capability) \| $5/M output \|` and `Haiku 4.5 makes multi-agent orchestration economically viable.` | **Not a deficiency** — Haiku 4.5 is the current shipping Haiku as of 2026-04 and stays. Recorded here so a future reader can see the line was considered and deliberately preserved. |

### `plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot`

| File | Line | Current text (quoted) | Deficiency |
|------|------|-----------------------|------------|
| graphviz-conventions.dot | — | No comment anywhere in the file identifies upstream provenance (obra/superpowers). | Byte-identical to `/tmp/superpowers-obra/skills/writing-skills/graphviz-conventions.dot` (verified 2026-04-17 in Phase 2C). Content reconciliation is a no-op; AC3.5 requires attribution so future diffs against upstream are legible. Task 4 adds a `//`-comment block only. |

## Independent-session search (2026-04-22)

**Queries run (FTS5-safe single-term):** `directive`, `Opus`, `Sonnet`, `Haiku`, `judgement`, `aggressive`, `overtriggering`, `CRITICAL`, `rationalize`, `rationalise`, `bypass`, `loophole`, `YOU`, `MUST`, `Sensitivity`, `think`, `mate`, `fuck`.

The last two (`mate`, `fuck`) are frustration-signal proxies per `feedback_haiku-no-judgement.md` and the project-wide auto-memory note that Australian-English `mate` is an escalation signal — a session where the operator used these while directive-writing would be a plausible RED candidate even if the failure itself was not explicitly model-anchored.

**Projects searched (chat-index paths):**

- `brian-ed3d-plugins` — `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`
- `PromptGrimoireTool` — `~/.claude/projects/-home-brian-people-Brian-PromptGrimoireTool/`
- `marketplaces/denubis-plugins` — `~/.claude/projects/-home-brian-marketplaces-denubis-plugins/`
- `pretix` — `~/.claude/projects/-home-brian-people-Brian-pretix/`
- `INTS1301` — `~/.claude/projects/-home-brian-people-Brian-INTS1301/`
- `LLM-History-Paper` — `~/.claude/projects/-home-brian-people-Brian-LLM-History-Paper/`

**Qualifying transcripts:** 0 across 30+ FTS5-safe single-term queries in 6 projects.

**Interpretation:** deficiencies are preemptive hygiene; restructure is preventive. Phase 2 restructures a skill whose deficiencies have not measurably misled authors in-the-wild. Recorded explicitly so a future reader is not surprised that this file contains static evidence rather than a transcript quote.

## How Phase 2 addresses the deficiencies

- Task 2 drops the stale `Opus 4.5: "Think" Sensitivity` subsection and updates per-model anchors in SKILL.md (lines 69, 96, 99, 237).
- Task 3 creates `model-tier-notes.md` as the per-model companion file (refresh-cycles decouple per design DR4).
- Task 3.5 updates `long-running-state-patterns.md` anchors (Opus 4.5 / Sonnet 4.5 → Opus 4.7 / Sonnet 4.6; Haiku 4.5 preserved; dated header + source URL added).
- Task 4 adds obra attribution to `graphviz-conventions.dot` (content byte-identical).

**Reviewer reproduction path:** clone the worktree at commit tip `575dd6b` (merge-base `4d5c952`), re-run the 18 FTS5-safe single-term queries listed above against the 6 project chat-index paths, and confirm 0 qualifying transcripts. Then diff-audit the line numbers above against the pre-restructure SHAs recorded at the top of this file.
