# ADR Enrichment Implementation Plan

**Goal:** Add Architecture Decision Record (ADR) vocabulary to the design plan template and database architecture template.

**Architecture:** Template-only changes to two existing skill files. No runtime code, no new files, no new directories. Decision Record sections are inserted into existing document structure templates and writer guidance sections.

**Tech Stack:** Markdown templates for Claude Code skill files.

**Scope:** 3 phases from original design (phases 1-3)

**Codebase verified:** 2026-04-08

---

## Acceptance Criteria Coverage

This phase implements:

### adr-enrichment.AC3: Database template enriched
- **adr-enrichment.AC3.1 Success:** `template-database.md` Design Decisions section includes Status, Confidence, Reevaluation triggers, and structured Consequences fields
- **adr-enrichment.AC3.2 Success:** Existing fields (Date, Context, Decision, Alternatives rejected) are preserved
- **adr-enrichment.AC3.3 Success:** Status/Confidence/Reevaluation triggers appear in metadata cluster after Date, before Context

---

<!-- START_TASK_1 -->
### Task 1: Enrich Design Decisions section in template-database.md

**Verifies:** adr-enrichment.AC3.1, adr-enrichment.AC3.2, adr-enrichment.AC3.3

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md:49-53`

**Step 1: Replace the Design Decisions entry template**

In `template-database.md`, find the current Design Decisions entry (lines 49-53):

```markdown
### [Decision Title]
**Date:** YYYY-MM-DD
**Context:** [Why this decision was needed]
**Decision:** [What was decided]
**Alternatives rejected:** [What else was considered and why it was rejected]
```

Replace with:

```markdown
### [Decision Title]
**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded by [link] | Deprecated
**Confidence:** High | Medium | Low
**Reevaluation triggers:** [Conditions under which to revisit]

**Context:** [Why this decision was needed]
**Decision:** [What was decided]
**Consequences:**
- **Enables:** [What this unlocks]
- **Prevents:** [What this forecloses]
**Alternatives rejected:** [What else was considered and why it was rejected]
```

Note: The blank line after Reevaluation triggers separates the metadata cluster (Date, Status, Confidence, Reevaluation triggers) from the narrative body (Context, Decision, Consequences, Alternatives rejected). This matches the design plan's specification that "Status/Confidence/Reevaluation triggers are placed after Date to form a metadata block that a reader can scan before committing to the narrative."

**Step 2: Verify the enrichment**

Run these grep commands:

```bash
# AC3.1: New fields present
grep "Status:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Confidence:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Reevaluation triggers:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Enables:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Prevents:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md

# AC3.2: Existing fields preserved
grep "Date:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Context:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Decision:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
grep "Alternatives rejected:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md

# AC3.3: Metadata cluster order (Date before Status before Confidence before Reevaluation)
grep -n "Date:\|Status:\|Confidence:\|Reevaluation\|Context:" plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
```

Expected: All grep commands return matches. The `-n` output for AC3.3 should show Date, Status, Confidence, Reevaluation triggers on consecutive lines before Context.

**Step 3: Commit**

```bash
git add plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md
git commit -m "feat: add ADR fields to database template Design Decisions section

Enrich template-database.md with Status, Confidence, Reevaluation triggers,
and structured Consequences (Enables/Prevents) alongside existing
Date/Context/Decision/Alternatives rejected fields."
```
<!-- END_TASK_1 -->
