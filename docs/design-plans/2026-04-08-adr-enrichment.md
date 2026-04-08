# ADR Enrichment of Existing Templates Design

**GitHub Issue:** None

## Summary

This work enriches two existing skill templates within the `denubis-plan-and-execute` plugin with Architecture Decision Record (ADR) vocabulary. Rather than creating a separate ADR system, the change embeds decision-tracking fields directly into the design artifacts writers already produce: the design plan template and the database architecture template. Each decision is recorded as a numbered entry (DR1, DR2, ...) capturing what was chosen, why alternatives were rejected, what the choice enables and forecloses, how confident the team was, and under what conditions the decision should be revisited.

The implementation is template-only — no new files, no runtime code, no new directories. The enriched templates are activated the moment a writer follows the updated skill guidance. Brainstorming output maps directly into the new Decision Record fields, so the added structure costs writers no additional research: the exploration work is already done by the time they reach this section. The superseding rule (from Fowler's ADR pattern) is documented explicitly — accepted decisions are never edited; to reverse a decision, a new record is created that references the old one, preserving the full audit trail.

## Definition of Done

1. **Design plan template enriched.** The `writing-design-plans/SKILL.md` template includes a "Decision Record" section after Architecture and before Existing Patterns, with Status, Consequences, Confidence, and Reevaluation triggers fields. The skill instructions guide writers on how to populate these fields.
2. **Database architecture template enriched.** The `template-database.md` "Design Decisions" section includes the same four ADR fields alongside the existing Date/Context/Decision/Alternatives rejected columns.
3. **Fowler's superseding rule documented.** Status field documentation makes clear that accepted decisions are never reopened — superseding creates a new record referencing the old one.
4. **Version bump and changelog.** `denubis-plan-and-execute` plugin.json, marketplace.json, and CHANGELOG.md updated per project conventions.

**Out of scope:** Retroactive enrichment of existing design plans, new ADR skill, `docs/adr/` directory, changes to brainstorming or proleptic challenge skills.

## Acceptance Criteria

### adr-enrichment.AC1: Design plan template includes Decision Record section
- **adr-enrichment.AC1.1 Success:** `writing-design-plans/SKILL.md` document structure template contains `## Decision Record` after `## Architecture` and before `## Existing Patterns`
- **adr-enrichment.AC1.2 Success:** Decision Record template shows DR[N] subsection format with Status, Confidence, Reevaluation triggers, Decision, Consequences (Enables/Prevents), and Alternatives considered fields
- **adr-enrichment.AC1.3 Success:** Status field documents four values: Proposed, Accepted, Superseded by [link], Deprecated
- **adr-enrichment.AC1.4 Success:** Superseding rule documented: accepted records are never edited; superseding creates a new record referencing the old one
- **adr-enrichment.AC1.5 Success:** Confidence level definitions documented: High, Medium, Low with clear semantics

### adr-enrichment.AC2: Writer guidance for decision identification
- **adr-enrichment.AC2.1 Success:** Skill contains a "Decision Record Section" guidance heading parallel to existing "Existing Patterns Section" and "Additional Considerations" headings
- **adr-enrichment.AC2.2 Success:** Identification heuristics present: brainstorming Phase 2 approaches, technology choices, architectural patterns, scope trade-offs
- **adr-enrichment.AC2.3 Success:** Negative heuristic present: "if only one option was considered, it's not a decision"
- **adr-enrichment.AC2.4 Success:** Guidance explains how brainstorming output maps to Decision Record fields

### adr-enrichment.AC3: Database template enriched
- **adr-enrichment.AC3.1 Success:** `template-database.md` Design Decisions section includes Status, Confidence, Reevaluation triggers, and structured Consequences fields
- **adr-enrichment.AC3.2 Success:** Existing fields (Date, Context, Decision, Alternatives rejected) are preserved
- **adr-enrichment.AC3.3 Success:** Status/Confidence/Reevaluation triggers appear in metadata cluster after Date, before Context

### adr-enrichment.AC4: Integration flow updated
- **adr-enrichment.AC4.1 Success:** "Integration with Workflow" section in `writing-design-plans/SKILL.md` lists Decision Record in the append sequence

### adr-enrichment.AC5: Version and changelog
- **adr-enrichment.AC5.1 Success:** `plugin.json` version bumped
- **adr-enrichment.AC5.2 Success:** `marketplace.json` version matches `plugin.json`
- **adr-enrichment.AC5.3 Success:** `CHANGELOG.md` has entry describing ADR enrichment

## Glossary

- **ADR (Architecture Decision Record):** A short structured document capturing a significant architectural or design decision, the context that motivated it, and its consequences. Popularised by Michael Nygard (2011); the format referenced here follows Fowler's presentation of Nygard's pattern.
- **Fowler's superseding rule:** The constraint that accepted decisions are never edited or reopened. To change a decision, a new record is created that explicitly supersedes the old one, keeping the historical record intact.
- **DR[N]:** Shorthand for a numbered Decision Record within a design plan (e.g., DR1, DR2). Numbering is per-document and sequential.
- **Status (ADR field):** Lifecycle marker: Proposed (under discussion), Accepted (active), Superseded by [link] (replaced), or Deprecated (no longer relevant, never formally replaced).
- **Confidence level:** Three-point scale (High/Medium/Low) indicating certainty at decision time. Deliberately coarse to avoid false precision.
- **Reevaluation triggers:** Explicit conditions under which a decision should be revisited, recorded at decision time rather than recovered from memory later.
- **Consequences (Enables/Prevents):** Structured field pair recording what a decision makes possible and what it forecloses.
- **Inverted pyramid principle:** Fowler's recommendation that ADRs be concise and front-loaded with the conclusion.
- **Brainstorming Phase 2 (Exploration):** The brainstorming skill stage where 2-3 named approaches are generated with trade-offs before user selection. Its output maps directly to Decision Record fields.

## Architecture

Template-only change. No runtime code, no new files, no new directories.

Two existing skill files are modified to add ADR vocabulary to their templates:

1. **`plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`** — gains a `## Decision Record` section in the design plan document structure (after Architecture, before Existing Patterns) and writer guidance on populating it. The section contains one or more numbered decision records (DR1, DR2, ...), each with Status, Confidence, Reevaluation triggers, Decision, Consequences (Enables/Prevents), and Alternatives considered.

2. **`plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md`** — the existing "Design Decisions" section gains Status, Confidence, Reevaluation triggers, and a structured Consequences field alongside its existing Date/Context/Decision/Alternatives rejected fields.

### Decision Record Format (Design Plans)

Each decision record within a design plan follows this structure:

```markdown
### DR[N]: [Decision title — what was chosen over what]
**Status:** Proposed | Accepted | Superseded by [link] | Deprecated
**Confidence:** High | Medium | Low
**Reevaluation triggers:** [Conditions under which to revisit]

**Decision:** [Active voice: "We chose X over Y."]

**Consequences:**
- **Enables:** [What this unlocks]
- **Prevents:** [What this forecloses]

**Alternatives considered:**
- **[Alternative]:** Rejected because [reason]
```

### Decision Record Format (Database Template)

Each database design decision follows this enriched structure:

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
**Alternatives rejected:** [What else was considered and why]
```

### Status Semantics

- **Proposed:** Decision under discussion, not yet approved.
- **Accepted:** Decision is active and governs current implementation. Never edit an accepted record.
- **Superseded by [new plan/section]:** A new decision replaces this one. The old record stays immutable; the new record references what it supersedes.
- **Deprecated:** Decision is no longer relevant (e.g., feature removed) but was never formally replaced.

Fowler's rule: accepted decisions are never reopened. To change a decision, create a new record marked as superseding the old one. This preserves the audit trail — future readers see what governed work during each period.

### Confidence Levels

- **High:** Strong evidence, well-understood domain, clear consensus.
- **Medium:** Reasonable choice but alternatives were close, or domain has unknowns.
- **Low:** Best guess given constraints; expect to revisit.

### Decision Identification Heuristics

Writers populate the Decision Record section during design documentation, drawing from brainstorming context. Heuristics for what warrants a record:

- If brainstorming Phase 2 explored it as a named approach, it's a decision record
- Technology choices (library X over Y) warrant a record
- Architectural patterns (event-driven vs synchronous) warrant a record
- Scope trade-offs explicitly discussed with the user warrant a record
- If only one option was ever considered, it's not a decision — it's just the design

## Decision Record

### DR1: Enrich existing templates rather than create new ADR artefact type
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If the number of standalone decisions (not tied to a design plan) exceeds what can be captured in architecture docs; if a separate `docs/adr/` directory becomes needed for decisions that don't fit design plans or database docs.

**Decision:** We chose to add ADR fields to existing design plan and architecture doc templates rather than creating a `docs/adr/` directory or standalone ADR skill.

**Consequences:**
- **Enables:** ADR vocabulary in all future design plans and database docs with zero workflow change. Brainstorming output feeds directly into Decision Records.
- **Prevents:** Capturing standalone architectural decisions that aren't tied to a design plan or database doc. Small decisions (e.g., "we use ruff not flake8") have no home.

**Alternatives considered:**
- **Standalone `docs/adr/` directory:** Rejected because it creates a parallel decision-tracking system that would drift from design plans. Fowler's ADRs are short documents — our design plans already serve that purpose for major decisions.
- **New ADR skill:** Rejected because the existing design-plan and architecture-doc workflows already handle decision documentation. A separate skill would duplicate orchestration.

### DR2: Multiple decision records per design plan
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If design plans consistently have only one decision, making multiple records feel like overhead.

**Decision:** We chose multiple numbered decision records (DR1, DR2, ...) per design plan rather than a single top-level record.

**Consequences:**
- **Enables:** Granular tracking of sub-decisions within a design (e.g., "chose Redis" and "chose workspace affinity" tracked separately with independent confidence and reevaluation triggers).
- **Prevents:** Nothing significant. Slightly more template bulk, but each record is concise (Fowler's inverted pyramid principle).

**Alternatives considered:**
- **One record per plan:** Rejected because design plans often contain multiple significant sub-decisions with different confidence levels and different reevaluation triggers. Collapsing them into one record loses granularity.

## Existing Patterns

**Design plan template** (`writing-design-plans/SKILL.md`): The existing document structure appends body sections (Architecture, Existing Patterns, Implementation Phases, Additional Considerations) in sequence. The Decision Record section follows the same pattern — a new body section with its own heading and writer guidance section, parallel to the existing "Existing Patterns Section" and "Additional Considerations" guidance headings.

**Database template** (`template-database.md`): The existing "Design Decisions" section already captures per-decision records with Date, Context, Decision, and Alternatives rejected. The enrichment adds fields to this existing per-decision structure rather than replacing it.

**Brainstorming skill** (`brainstorming/SKILL.md`): Phase 2 (Exploration) already generates 2-3 named approaches with trade-offs, and the user selects one. This output maps directly to Decision Record entries — the selected approach becomes the Decision, rejected approaches become Alternatives considered, and the trade-off discussion informs Consequences. No changes to brainstorming are needed; the mapping is documented in the writer guidance.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Design Plan Template Enrichment
**Goal:** Add Decision Record section and writer guidance to `writing-design-plans/SKILL.md`

**Components:**
- `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md` — add `## Decision Record` to the document structure template (after `## Architecture`, before `## Existing Patterns`), add "Decision Record Section" writer guidance heading with identification heuristics, status semantics, confidence levels, consequences format, and superseding rule. Update the "Integration with Workflow" section to include Decision Record in the append sequence.

**Dependencies:** None

**Done when:** The skill file contains the Decision Record template, writer guidance, and updated integration flow. The template matches the format validated in brainstorming (DR[N] subsections with Status, Confidence, Reevaluation triggers, Decision, Consequences, Alternatives considered).
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Database Template Enrichment
**Goal:** Add ADR fields to `template-database.md` Design Decisions section

**Components:**
- `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md` — enrich the "Design Decisions" section template with Status, Confidence, Reevaluation triggers, and structured Consequences (Enables/Prevents) alongside existing Date/Context/Decision/Alternatives rejected fields.

**Dependencies:** None (can be built in parallel with Phase 1)

**Done when:** The template's Design Decisions section includes all four ADR fields in the format validated in brainstorming.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Version Bump and Changelog
**Goal:** Update plugin version and changelog per project conventions

**Components:**
- `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — matching version bump
- `CHANGELOG.md` — entry for ADR enrichment release

**Dependencies:** Phases 1-2 (template changes complete)

**Done when:** plugin.json, marketplace.json, and CHANGELOG.md are updated with consistent version and descriptive changelog entry.
<!-- END_PHASE_3 -->

## Additional Considerations

**Retrospective enrichment agent.** This design deliberately excludes retroactive ADR annotation of existing design plans. A separate design will address an agent that can read existing plans (e.g., the ~80+ in PromptGrimoireTool), identify implicit decisions from Architecture/Additional Considerations prose, and propose Decision Record entries. The template format established here becomes the target specification for that agent.

**Confidence calibration.** The three-level confidence scale (High/Medium/Low) is deliberately coarse. Finer granularity (numeric scores, percentage ranges) would create false precision — the value is in signalling "we're sure" vs "we're guessing," not in distinguishing 70% from 80% confidence.
