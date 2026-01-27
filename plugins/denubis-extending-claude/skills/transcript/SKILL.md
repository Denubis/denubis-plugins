# Archive Transcript with Research Metadata

Archive this conversation with research metadata using the IDW2025 reproducibility framework (Three Ps: Prompt/Process/Provenance).

**IMPORTANT**: This is an INTERACTIVE process. You MUST use the AskUserQuestion tool to gather metadata before archiving. Do NOT skip straight to archiving.

## Your Task

### Step 1: Analyze the Conversation

Review the full conversation and identify:

1. A proposed **Title** (3-7 words)
2. Draft **Three Ps** (IDW2025 framework):
   - **Prompt**: What was the user trying to accomplish?
   - **Process**: How was Claude Code used?
   - **Provenance**: Role in broader research/project context
3. What context might be missing in 6 months?

### Step 2: REQUIRED - Ask Clarifying Questions

You MUST use the AskUserQuestion tool to gather input. Think proleptically - what context will be missing in 6 months?

Use AskUserQuestion with questions like:

```yaml
questions:
  - question: "What broader research or project goal does this session contribute to?"
    header: "Context"
    options:
      - label: "Standalone task"
        description: "This was a self-contained piece of work"
      - label: "Part of larger project"
        description: "Contributes to an ongoing research effort"
      - label: "Exploratory/learning"
        description: "Experimenting or learning something new"
    multiSelect: false
```

Also ask any conversation-specific questions about gaps you've identified. Do NOT ask generic checklists - only ask where the answer isn't already clear.

### Step 3: Draft and Confirm Metadata

After receiving the user's answers, present your draft metadata:

```text
**Title**: [Your proposed title]

**Three Ps (IDW2025 Framework)**:
- **Prompt**: [1-2 sentences on what was asked/needed]
- **Process**: [1-2 sentences on how the tool was used]
- **Provenance**: [1 sentence on role in research workflow, incorporating their answer]

**Tags**: [Suggested tags]
```

Use AskUserQuestion again to confirm:

```yaml
questions:
  - question: "Does this metadata look correct?"
    header: "Confirm"
    options:
      - label: "Yes, archive it"
        description: "Proceed with archiving"
      - label: "Edit title"
        description: "I want to change the title"
      - label: "Edit metadata"
        description: "I want to revise the Three Ps"
    multiSelect: false
```

### Step 4: Execute Archive

ONLY after the user confirms, run the archive command with all the gathered metadata:

```bash
claude-transcript-archive --retitle --local \
  --title "YOUR CONFIRMED TITLE" \
  --prompt "The Prompt summary you drafted" \
  --process "The Process summary you drafted" \
  --provenance "The Provenance summary you drafted"
```

**IMPORTANT**: You MUST pass all three `--prompt`, `--process`, and `--provenance` arguments. This marks the archive as fully reviewed (no `needs_review` flag).

### Step 5: Generate Markdown Summary

After archiving, create a `SUMMARY.md` file in the archive directory (`./ai_transcripts/[date]-[title]/`):

```markdown
# [Title]

**Date**: [YYYY-MM-DD]
**Duration**: [X minutes]
**Model**: [model used]

## Three Ps (IDW2025 Framework)

### Prompt
[What the user was trying to accomplish]

### Process
[How Claude Code was used]

### Provenance
[Role in broader research/project context]

## Key Artifacts

### Created
- [file1.py] - [brief description]
- [file2.md] - [brief description]

### Modified
- [file3.py] - [what changed]

## Session Statistics

- **Turns**: [N]
- **Tool calls**: [N total]
- **Estimated cost**: $[X.XX]

## Tags
[tag1], [tag2], [tag3]

---
*Archived with denubis-extending-claude:transcript*
```

Use the Write tool to create this SUMMARY.md file. Extract the statistics from `session.meta.json` to populate it accurately.

## After Archiving

Tell the user:

1. Where the archive was saved (always `./ai_transcripts/` in current project)
2. That they can view:
   - `SUMMARY.md` - Human-readable summary
   - `index.html` - Full HTML transcript
   - `session.meta.json` - Complete structured metadata
3. The archive follows the IDW2025 reproducibility framework
