# Handover: ADR Enrichment of Existing Templates

## Goal

Add Architecture Decision Record (ADR) fields to our existing design plan and architecture doc templates. We already capture decisions with rationale — we just don't use ADR vocabulary or structure for it. No new directory, no new skill, no new artefact type.

## Context

Martin Fowler's ADR concept (https://martinfowler.com/bliki/ArchitectureDecisionRecord.html, based on Michael Nygard's 2011 work) describes short documents capturing a single decision with its context and consequences. Our design plans and architecture doc templates already function as ADRs for major decisions — the brainstorming skill explores alternatives, the proleptic challenge surfaces disagreements, and design plans document what was chosen and why.

The gap is four specific fields that ADRs formalise and we currently lack:

### Fields to Add

| Field | What it captures | Why it matters |
|-------|-----------------|----------------|
| **Status** | Proposed → Accepted → Superseded | Prevents reopening settled decisions; superseding creates a new record rather than editing the old one |
| **Consequences** | What this decision enables AND what it prevents | Forces explicit acknowledgment of tradeoffs, not just "we chose X because Y" |
| **Confidence level** | How sure we are (High / Medium / Low) | Signals which decisions are load-bearing vs provisional |
| **Reevaluation triggers** | Conditions under which this decision should be revisited | Prevents both premature revisiting and stale-forever decisions |

## Files to Modify

### 1. Design Plan Template

**File:** `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`

The design plan template (look for the markdown template section) needs the four fields added. The "Additional Considerations" section already captures some rationale — the new fields should sit alongside it, not replace it.

Suggested placement: after the Summary/before Implementation Phases, as a "Decision Record" section within the design plan.

### 2. Architecture Doc Templates

**File:** `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

The `template-database.md` already has a "Design Decisions" section with Date/Context/Decision/Alternatives Rejected columns. This needs the four new fields added to match.

Check ALL templates in this skill — any template that captures decisions should get the enrichment.

### 3. Brainstorming Skill (read-only reference)

**File:** `plugins/denubis-plan-and-execute/skills/brainstorming/SKILL.md`

The brainstorming skill already explores alternatives and rejects options. The design plan template changes should ensure that brainstorming output naturally feeds the Consequences and Confidence fields. You may not need to change this file, but read it to understand what upstream output looks like.

## Design Constraints

- **No new artefact type.** We enrich existing templates, not create `docs/adr/`.
- **No new skill.** The existing design-plan and architecture-doc workflows handle ADR creation.
- **Fowler's key rule:** Accepted decisions are never reopened. Superseding creates a NEW record that references the old one. Build this into the status field documentation.
- **Brevity principle:** Fowler emphasises inverted pyramid — most important material first. The new fields should be concise, not essayistic.
- **Version bump required.** Changes to `denubis-plan-and-execute` skills require updating `plugin.json`, `marketplace.json`, and `CHANGELOG.md` per project CLAUDE.md conventions.

## What Success Looks Like

After this work, a design plan's decision section should read something like:

```markdown
## Decision Record

**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If X library drops Python 3.14 support; if upstream adds native Y

### Decision
We chose A over B and C.

### Consequences
- **Enables:** [what this unlocks]
- **Prevents:** [what this forecloses]

### Alternatives Considered
- **B:** Rejected because [reason]
- **C:** Rejected because [reason]
```

## Out of Scope

- Retroactively adding ADR fields to the 5 existing design plans in `docs/design-plans/`
- Creating a standalone ADR skill for smaller decisions
- Creating a `docs/adr/` directory
- Changing the brainstorming or proleptic challenge skills
