# ADR Enrichment Implementation Plan

**Goal:** Add Architecture Decision Record (ADR) vocabulary to the design plan template and database architecture template.

**Architecture:** Template-only changes to two existing skill files. No runtime code, no new files, no new directories. Decision Record sections are inserted into existing document structure templates and writer guidance sections.

**Tech Stack:** Markdown templates for Claude Code skill files.

**Scope:** 3 phases from original design (phases 1-3)

**Codebase verified:** 2026-04-08

---

## Acceptance Criteria Coverage

This phase implements:

### adr-enrichment.AC5: Version and changelog
- **adr-enrichment.AC5.1 Success:** `plugin.json` version bumped
- **adr-enrichment.AC5.2 Success:** `marketplace.json` version matches `plugin.json`
- **adr-enrichment.AC5.3 Success:** `CHANGELOG.md` has entry describing ADR enrichment

---

<!-- START_TASK_1 -->
### Task 1: Bump version in plugin.json and marketplace.json

**Verifies:** adr-enrichment.AC5.1, adr-enrichment.AC5.2

**Files:**
- Modify: `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json:4` (version field)
- Modify: `.claude-plugin/marketplace.json` (denubis-plan-and-execute version field, around line 25)

**Step 1: Update plugin.json version**

In `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json`, change:

```json
"version": "2.22.0",
```

to:

```json
"version": "2.23.0",
```

**Step 2: Update marketplace.json version**

In `.claude-plugin/marketplace.json`, find the `denubis-plan-and-execute` entry and change:

```json
"version": "2.22.0",
```

to:

```json
"version": "2.23.0",
```

**Step 3: Verify versions match**

```bash
grep '"version"' plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
grep -A2 'denubis-plan-and-execute' .claude-plugin/marketplace.json | grep '"version"'
```

Expected: Both show `"version": "2.23.0"`.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add changelog entry

**Verifies:** adr-enrichment.AC5.3

**Files:**
- Modify: `CHANGELOG.md:2` (insert after `# Changelog` heading)

**Step 1: Add changelog entry**

Insert the following after the `# Changelog` heading (line 1) and before the existing `## [denubis-plan-and-execute] 2.22.0` entry:

```markdown

## [denubis-plan-and-execute] 2.23.0

ADR enrichment of design plan and database architecture templates.

**New:**
- Decision Record section in `writing-design-plans` skill template (DR[N] subsections with Status, Confidence, Reevaluation triggers, Consequences, Alternatives)
- Writer guidance for decision identification with brainstorming mapping and Fowler's superseding rule
- ADR fields (Status, Confidence, Reevaluation triggers, structured Consequences) in `template-database.md` Design Decisions section
```

**Step 2: Verify changelog entry**

```bash
head -15 CHANGELOG.md
```

Expected: New entry appears at top, followed by existing 2.22.0 entry.

**Step 3: Commit**

```bash
git add plugins/denubis-plan-and-execute/.claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore: bump denubis-plan-and-execute to 2.23.0

Version bump and changelog for ADR enrichment release:
- Decision Record section added to design plan template
- ADR fields added to database architecture template"
```
<!-- END_TASK_2 -->
