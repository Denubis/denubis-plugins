---
name: exec-session-naming
family: executing-an-implementation-plan,starting-an-implementation-plan,starting-a-design-plan,systematic-debugging
description: Generate domain-specific session name via Haiku subagent, rename tmux window, write lock file
user-invocable: false
---

# Session Naming

Generate a short, domain-specific slug for the current session. Rename the tmux window and write a lock file so the statusline can display it.

## 1. Gather Context

Collect the following before spawning the subagent:

- **User prompt summary:** Summarise the user's initial prompt from conversation context (one sentence).
- **Invoking skill name:** The skill that triggered exec-session-naming.
- **Repo name:** Basename of `git rev-parse --show-toplevel`.
- **Branch name:** Output of `git branch --show-current`.
- **Tmux pane ID:** Read `$TMUX_PANE` from the environment and strip the `%` prefix.

## 2. Tmux Guard

If `$TMUX` or `$TMUX_PANE` is not set, the session is not running inside tmux. In that case:

- Still spawn the Haiku subagent and generate the slug (useful for `/rename`).
- Skip the tmux rename and lock file steps.
- Log: "Not in a tmux session -- skipping window rename and lock file."

## 3. Generate Slug via Haiku Subagent

Substitute the gathered values into the placeholders below, then invoke:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:haiku-general-purpose</parameter>
<parameter name="description">Generate session name slug</parameter>
<parameter name="prompt">
Generate a 2-4 word lowercase hyphenated slug that summarises this Claude Code session.

Context:
- User's initial prompt: {user_prompt_summary}
- Active skill: {skill_name}
- Repository: {repo_name}
- Branch: {branch_name}

Rules:
- 2-4 words, lowercase, hyphen-separated
- Domain-specific (use terms from the prompt, not generic words)
- No repo name or branch name in the slug (that's already shown elsewhere)
- Examples: "fix-auth-timeout", "add-rate-limits", "refactor-cache-layer"

Output ONLY the slug, nothing else.
</parameter>
</invoke>
```

Capture the returned slug. Trim any whitespace.

## 4. Apply the Slug

After receiving the slug from the subagent:

1. **Rename tmux window** (only if both `$TMUX` and `$TMUX_PANE` are set):
   Run via Bash: `tmux rename-window "Cl:{slug}"` (substitute the actual slug)

2. **Write lock file** (only if both `$TMUX` and `$TMUX_PANE` are set):
   Run via Bash: `echo "{slug}" > /tmp/claude-statusline-tmux-lock-$(echo $TMUX_PANE | tr -d '%')` (substitute the actual slug)

3. **Tell the user** (substitute the actual slug):
   "To also rename this session, run: `/rename <slug>`"
