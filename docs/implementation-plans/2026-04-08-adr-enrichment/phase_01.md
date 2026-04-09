# ADR Enrichment Implementation Plan

**Goal:** Add Architecture Decision Record (ADR) vocabulary to the design plan template and database architecture template.

**Architecture:** Template-only changes to two existing skill files. No runtime code, no new files, no new directories. Decision Record sections are inserted into existing document structure templates and writer guidance sections.

**Tech Stack:** Markdown templates for Claude Code skill files.

**Scope:** 3 phases from original design (phases 1-3)

**Codebase verified:** 2026-04-08

---

## Acceptance Criteria Coverage

This phase implements:

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

### adr-enrichment.AC4: Integration flow updated
- **adr-enrichment.AC4.1 Success:** "Integration with Workflow" section in `writing-design-plans/SKILL.md` lists Decision Record in the append sequence

---

<!-- START_TASK_1 -->
### Task 1: Add Decision Record section and writer guidance to writing-design-plans/SKILL.md

**Verifies:** adr-enrichment.AC1.1, adr-enrichment.AC1.2, adr-enrichment.AC1.3, adr-enrichment.AC1.4, adr-enrichment.AC1.5, adr-enrichment.AC2.1, adr-enrichment.AC2.2, adr-enrichment.AC2.3, adr-enrichment.AC2.4, adr-enrichment.AC4.1

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`

This task makes three insertions into a single file. All three must be consistent.

**Note:** Line numbers below refer to the file *before* any edits in this task. After Step 1 inserts ~18 lines, all subsequent line numbers shift. Search by content (headings, keywords), not by line number.

**Step 1: Insert Decision Record section into document structure template**

In the "Document Structure" section, find the template code block (starts around line 106). Between the `## Architecture` block (ends at line 113) and `## Existing Patterns` (starts at line 114), insert:

```markdown

## Decision Record

### DR[N]: [Decision title - what was chosen over what]
**Status:** Proposed | Accepted | Superseded by [link] | Deprecated
**Confidence:** High | Medium | Low
**Reevaluation triggers:** [Conditions under which to revisit]

**Decision:** [Active voice: "We chose X over Y."]

**Consequences:**
- **Enables:** [What this unlocks]
- **Prevents:** [What this forecloses]

**Alternatives considered:**
- **[Alternative]:** Rejected because [reason]

[Repeat DR[N+1], DR[N+2], ... for each significant decision]
```

**Step 2: Insert Decision Record Section writer guidance**

After the "Existing Patterns Section" guidance (ends around line 393) and before the "Additional Considerations" guidance (starts at line 395), insert a new `## Decision Record Section` heading with this content:

```markdown
## Decision Record Section

**Purpose:** Capture significant design decisions with enough context to understand why they were made, what they enable, and when to revisit them.

**Placement:** After Architecture, before Existing Patterns. Decisions emerge from the architecture discussion, so readers have context before encountering the formal records.

**What warrants a decision record:**
- If brainstorming Phase 2 explored it as a named approach, it's a decision record
- Technology choices (library X over Y) warrant a record
- Architectural patterns (event-driven vs synchronous) warrant a record
- Scope trade-offs explicitly discussed with the user warrant a record
- If only one option was ever considered, it's not a decision — it's just the design

**Mapping brainstorming output to Decision Record fields:**
- The approach selected in Phase 2 becomes the **Decision** field
- Rejected approaches become **Alternatives considered** with rejection reasons from the discussion
- Trade-offs discussed during exploration inform **Consequences** (Enables/Prevents)
- User's certainty during selection maps to **Confidence** (High if clear preference, Medium if close call, Low if "let's try this")
- Concerns raised during brainstorming become **Reevaluation triggers**

**Status values:**
- **Proposed:** Decision under discussion, not yet approved.
- **Accepted:** Decision is active and governs current implementation.
- **Superseded by [new plan/section]:** A new decision replaces this one. The old record stays immutable; the new record references what it supersedes.
- **Deprecated:** Decision is no longer relevant (e.g., feature removed) but was never formally replaced.

**Fowler's superseding rule:** Accepted decisions are never reopened or edited. To change a decision, create a new record marked as superseding the old one. This preserves the audit trail — future readers see what governed work during each period.

**Confidence levels:**
- **High:** Strong evidence, well-understood domain, clear consensus.
- **Medium:** Reasonable choice but alternatives were close, or domain has unknowns.
- **Low:** Best guess given constraints; expect to revisit.

**Style:**
- Use the inverted pyramid: lead with what was decided, then why, then consequences
- Active voice for Decision field: "We chose X over Y" not "X was selected"
- Keep each record concise — if the explanation exceeds a paragraph, the decision may need splitting
- Number records sequentially per document: DR1, DR2, DR3

**Example:**
```markdown
## Decision Record

### DR1: Enrich existing templates rather than create new ADR artefact type
**Status:** Accepted
**Confidence:** High
**Reevaluation triggers:** If standalone decisions (not tied to a design plan) exceed what architecture docs can capture; if a separate docs/adr/ directory becomes needed.

**Decision:** We chose to add ADR fields to existing design plan and architecture doc templates rather than creating a docs/adr/ directory or standalone ADR skill.

**Consequences:**
- **Enables:** ADR vocabulary in all future design plans with zero workflow change. Brainstorming output feeds directly into Decision Records.
- **Prevents:** Capturing standalone architectural decisions not tied to a design plan or database doc.

**Alternatives considered:**
- **Standalone docs/adr/ directory:** Rejected because it creates a parallel system that would drift from design plans.
- **New ADR skill:** Rejected because existing workflows already handle decision documentation.
```
```

**Step 3: Update Integration with Workflow append sequence**

In the "Integration with Workflow" section (around line 787), find the line:

```
  -> Append body: Architecture, Existing Patterns, Implementation Phases, Additional Considerations
```

Replace with:

```
  -> Append body: Architecture, Decision Record, Existing Patterns, Implementation Phases, Additional Considerations
```

**Verification:**

Run these grep commands to verify all insertions:

```bash
# AC1.1: Decision Record section exists in template between Architecture and Existing Patterns
grep -n "## Decision Record" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md

# AC1.2: DR[N] format with all required fields
grep -c "DR\[N\]" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md
grep "Reevaluation triggers" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md | head -3

# AC1.3: Four status values documented
grep "Proposed.*Accepted.*Superseded.*Deprecated" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md

# AC1.4: Superseding rule mentioned (human review needed for semantic correctness)
grep -i "supersed" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md | head -3

# AC1.5: Confidence levels
grep -A1 "High.*Medium.*Low" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md | head -3

# AC2.1: Writer guidance heading
grep "## Decision Record Section" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md

# AC2.2: Identification heuristics
grep "brainstorming Phase 2" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md

# AC2.3: Negative heuristic
grep "only one option" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md

# AC2.4: Brainstorming mapping
grep "Mapping brainstorming" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md

# AC4.1: Integration flow updated (verify Decision Record appears in append sequence)
grep "Append body" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md | grep "Decision Record"
```

Expected: All grep commands return matches.

**Commit:**

```bash
git add plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md
git commit -m "feat: add Decision Record section to design plan template

Enrich writing-design-plans skill with ADR vocabulary:
- Decision Record section in document structure template (after Architecture, before Existing Patterns)
- Writer guidance for decision identification with heuristics and brainstorming mapping
- Integration with Workflow updated to include Decision Record in append sequence"
```
<!-- END_TASK_1 -->
