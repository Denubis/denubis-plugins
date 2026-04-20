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
