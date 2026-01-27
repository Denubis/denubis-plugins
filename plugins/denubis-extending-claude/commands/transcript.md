---
description: Archive this conversation with research metadata (IDW2025 framework)
---

# Archive Transcript

**For Claude: REQUIRED SKILL**

Use the Skill tool to invoke the `transcript` skill from `denubis-extending-claude`:

<invoke name="Skill">
<parameter name="skill">denubis-extending-claude:transcript</parameter>
</invoke>

Follow the skill instructions to:
1. Analyze the conversation
2. Ask clarifying questions (REQUIRED - use AskUserQuestion)
3. Draft and confirm metadata
4. Execute archive with `claude-transcript-archive`
5. Generate SUMMARY.md file
