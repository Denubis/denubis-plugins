# Test Requirements: ADR Enrichment

All commands use the worktree root as working directory:
```
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/adr-enrichment
```

Shorthand used below:
- `SKILL` = `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`
- `DBTEMPL` = `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md`
- `PLUGIN` = `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json`
- `MARKET` = `.claude-plugin/marketplace.json`
- `CHANGE` = `CHANGELOG.md`

## Automated Verification

| Criterion | Command | Expected |
|-----------|---------|----------|
| adr-enrichment.AC1.1 | `grep -n "## Architecture\|## Decision Record\|## Existing Patterns" $SKILL \| head -6` | Output must show Architecture, then Decision Record, then Existing Patterns in ascending line order. |
| adr-enrichment.AC1.2 | `grep -c "DR\[N\]" $SKILL` and `grep -c "Reevaluation triggers" $SKILL` and `grep -c "\*\*Enables:\*\*" $SKILL` and `grep -c "\*\*Prevents:\*\*" $SKILL` and `grep -c "\*\*Alternatives considered:\*\*" $SKILL` | All counts >= 1. |
| adr-enrichment.AC1.3 | `grep "Proposed.*Accepted.*Superseded.*Deprecated" $SKILL` | At least one match showing all four status values on a single line. |
| adr-enrichment.AC1.5 | `grep "High.*Medium.*Low" $SKILL` | At least one match showing all three confidence levels on a single line. |
| adr-enrichment.AC2.1 | `grep "## Decision Record Section" $SKILL` | Exactly one match (the writer guidance heading, distinct from the `## Decision Record` template heading). |
| adr-enrichment.AC2.2 | `grep "brainstorming Phase 2" $SKILL` and `grep -c "Technology choices\|Architectural patterns\|Scope trade-offs" $SKILL` | At least one match each. |
| adr-enrichment.AC2.3 | `grep "only one option" $SKILL` | At least one match containing the negative heuristic. |
| adr-enrichment.AC2.4 | `grep -i "mapping brainstorming\|brainstorming output" $SKILL` | At least one match explaining how brainstorming maps to Decision Record fields. |
| adr-enrichment.AC3.1 | `grep "Status:" $DBTEMPL && grep "Confidence:" $DBTEMPL && grep "Reevaluation triggers:" $DBTEMPL && grep "Enables:" $DBTEMPL && grep "Prevents:" $DBTEMPL` | All five commands return matches. |
| adr-enrichment.AC3.2 | `grep "Date:" $DBTEMPL && grep "Context:" $DBTEMPL && grep "Decision:" $DBTEMPL && grep "Alternatives rejected:" $DBTEMPL` | All four commands return matches (existing fields preserved). |
| adr-enrichment.AC3.3 | `grep -n "Date:\|Status:\|Confidence:\|Reevaluation triggers:\|Context:" $DBTEMPL` | Line numbers must appear in order: Date, Status, Confidence, Reevaluation triggers, then Context. |
| adr-enrichment.AC4.1 | `grep "Append body" $SKILL \| grep "Decision Record"` | At least one match showing "Decision Record" in the append sequence. |
| adr-enrichment.AC5.1 | `grep '"version"' $PLUGIN` | Shows version `"2.23.0"` (bumped from `"2.22.0"`). |
| adr-enrichment.AC5.2 | `grep '"version"' $PLUGIN` and `grep -A2 'denubis-plan-and-execute' $MARKET \| grep '"version"'` | Both commands return the same version string (`"2.23.0"`). |
| adr-enrichment.AC5.3 | `grep "denubis-plan-and-execute.*2.23.0\|ADR enrichment\|Decision Record" $CHANGE \| head -5` | At least one match in the changelog referencing the ADR enrichment release. |

## Human Verification

| Criterion | Why not automated | Verification approach |
|-----------|-------------------|----------------------|
| adr-enrichment.AC1.4 | Superseding rule is a semantic concept expressed in prose. A grep can confirm the word "supersed" appears, but cannot verify the rule is correctly and completely documented. | Read the "Decision Record Section" writer guidance in `SKILL.md`. Confirm it contains a paragraph explaining Fowler's superseding rule with both halves: (1) accepted decisions are never reopened or edited, and (2) to change a decision, create a new record that references the old one. Check that the Status field's "Superseded by [link]" value is consistent with this rule. |
| adr-enrichment.AC2.4 (semantic completeness) | The automated check confirms a brainstorming mapping section exists, but cannot verify the mapping is complete and correct. | Read the brainstorming-to-Decision-Record mapping in the writer guidance. Verify it maps: (1) selected approach to Decision, (2) rejected approaches to Alternatives considered, (3) trade-offs to Consequences (Enables/Prevents), (4) certainty to Confidence, (5) concerns to Reevaluation triggers. Each mapping should name the brainstorming source and the Decision Record target field. |
