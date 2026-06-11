# denubis-plugins

Claude Code plugins for design, implementation, and development workflows.

## Working Philosophy

### HALT When Things Feel Sideways

This repo spends most of its time mid-refactor — files renamed, skills reorganised, standards in flux. When something feels incorrect, contradictory, or inconsistent, **halt and discuss** rather than work around the anomaly.

Concrete triggers:

- Repo state looks mixed (old and new conventions coexisting, orphaned files, rename mid-flight).
- A design decision contradicts the active refactor direction.
- Tool results, skill contents, or documents conflict with each other.
- About to produce a large artifact (design doc, rewrite, plan) on assumptions that may be stale.
- A reviewer, auditor, or test-analyst returns substantial findings (Critical / Important / Multiple Minor / NEEDS_REVISION). Even if the top-level summary is "APPROVED" or "no strict gaps", interrogate every level before acting — a Minor finding or a "flagged but not a gap" note may hint at a false-world-model assumption the reviewer didn't escalate. See `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/feedback_review-all-levels.md`.
- A planning decision feels skeevy, even if a subagent or prior session approved it. Surface the concern ("Why are we grepping for that?", "Is this rubric-as-text?") and re-examine before writing more.
- A batch-fix pattern emerges (multiple findings queued for implementation). Batch-fixing skips the discussion step where embedded assumptions get surfaced. Work findings one by one, discussing what each fix reveals before moving to the next.

Default: **HALT and discuss, not HALT and decide unilaterally.** Raise the discrepancy in plain language and wait for direction. When a revision is substantial, a "halt and escalate to next session" is a valid choice — rushed revisions often miss the same structural issues the original work missed.

## Conventions

### Task Invocations Use XML Syntax

When documenting Task tool invocations in skills or agent prompts, use XML-style blocks:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Brief description of what the subagent does</parameter>
<parameter name="prompt">
The prompt content goes here.

Can be multiple lines.
</parameter>
</invoke>
```

This format keeps the model on-rails better than fenced code blocks with plain text descriptions.

**Do not** write Task invocations as prose like "Use the Task tool with subagent_type X and prompt Y". Use the XML block format.

### Schema Constants from Authoritative Source

When a subagent prompt references a schema-level value set (a CHECK constraint's allowed values, a StrEnum's members, a tuple defining valid states), derive the list by reading the authoritative implementation file at dispatch time — not from documentation, summaries, or memory. Documentation drifts; memory hallucinates; subagents inherit whatever the orchestrator passes in.

**Authoritative sources**: the implementation file (e.g., `db.py`'s `CLASSIFICATION_VALUES`), not the design plan or architecture doc that describes it.

**Why**: a Critical in Phase 1 review of denubis-crash-recovery traced to passing composite section-key strings (`borderline+ambiguous_match`) as if they were the DB column values that the rest of the plan used (bare `borderline` + separate reason column). The CHECK constraint was schema-locked to the wrong shape until caught on re-review. The slip happened because the value list was generated from memory rather than read from `db.py`.

### Conflicting Authoritative Sources Are Recorded, Not Resolved

When two authoritative sources disagree (platform API docs vs Claude Code docs, vendor table vs in-session observation), record both claims with citations and verification dates, attribute each as **observed** (empirical, reproduced in session) or **documented** (docs-only), and gate behaviour on the conservative reading. Do not pick a winner, silently drop the weaker source, or average the two.

**Why**: the Phase 2.6 advisor-pairing correction (2026-06-11) found the platform API compatibility table and the Claude Code advisor docs in direct conflict over whether Fable may advise Haiku/Sonnet mains. Recording both let the cost gate extend conservatively; resolving in either direction would have encoded a guess as doctrine. Phases 3/4 drift surveys follow this pattern when upstream sources disagree.

### Version Updates Require Marketplace and Changelog Sync

When updating a plugin's version in its `.claude-plugin/plugin.json`, you must also:

1. Update the corresponding version in `.claude-plugin/marketplace.json` at the repo root
2. Add a changelog entry to `CHANGELOG.md` at the repo root

Changelog entries go at the top (after the `# Changelog` heading) and follow the format:

```markdown
## [plugin-name] [version]

Brief description of the release.

**New:**
- New features or additions

**Changed:**
- Modifications to existing behavior

**Fixed:**
- Bug fixes
```

Only include sections that apply. Keep entries concise.
