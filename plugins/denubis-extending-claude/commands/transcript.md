---
description: Archive a conversation with research metadata (IDW2025 framework). Optionally pass a session UUID to archive a prior session.
---

# Archive Transcript

**For Claude: REQUIRED SKILL**

Use the Skill tool to invoke the `transcript` skill from `denubis-extending-claude`, passing any arguments through:

<invoke name="Skill">
<parameter name="skill">denubis-extending-claude:transcript</parameter>
<parameter name="args">{any arguments the user provided, e.g. a session UUID}</parameter>
</invoke>

Follow the skill instructions to:
1. Resolve the transcript source (current session or prior session by UUID)
2. Analyze the conversation
3. Ask clarifying questions (REQUIRED - use AskUserQuestion)
4. Draft and confirm metadata
5. Execute archive with `claude-transcript-archive`
6. Generate SUMMARY.md file
