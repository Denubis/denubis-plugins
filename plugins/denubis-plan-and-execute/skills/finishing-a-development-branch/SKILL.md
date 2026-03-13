---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
user-invocable: false
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Update project context → Present options → Delegate to the right skill.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Update Project Context

Before presenting options, invoke `denubis-extending-claude:project-claude-librarian` to update CLAUDE.md files if contracts or structure changed.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-extending-claude:project-claude-librarian</parameter>
<parameter name="description">Updating project context for <branch-name></parameter>
<parameter name="prompt">
  Review what changed in this branch and update CLAUDE.md files if contracts or structure changed.

  Base branch: <base-branch>
  Feature branch: <feature-branch>
  Working directory: <directory>

  Follow the denubis-extending-claude:maintaining-project-context skill to:
  1. Diff against base branch to see what changed
  2. Identify contract/API/structure changes
  3. Update affected CLAUDE.md files
  4. Commit documentation updates with message: "docs: update project context for <branch-name>"

  Report back with what was updated (or that no updates were needed).
</parameter>
</invoke>
```

**If librarian commits updates:** Include those commits in the subsequent merge/PR.
**If librarian reports no updates needed:** Proceed.
**If librarian subagent is not available:** Skip this step, saying aloud that you're skipping it because the `denubis-extending-claude` plugin is not available.

### Step 2: Present Options

Present exactly these 4 options in `AskUserQuestion`.

```
Implementation complete. What would you like to do?

1. Merge back to main locally (/merge-to-main)
2. Push and create a Pull Request (/make-pr)
3. Keep the branch as-is (I'll handle it later, or I have more work to do)
4. Discard this work

Which option?
```

**Don't add explanation** — keep options concise.

### Step 3: Execute Choice

#### Option 1: Merge Locally

Activate the `merge-to-main` skill. It handles:
- Syncing with remote and rebasing
- Test discovery and pre-merge verification
- Merging to main
- Post-merge test verification
- Branch and worktree cleanup

#### Option 2: Push and Create PR

Activate the `make-pr` skill. It handles:
- Syncing with remote and rebasing
- Test discovery and verification
- Pushing and creating the PR
- Post-PR cleanup

#### Option 3: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

**Don't cleanup worktree.**

#### Option 4: Discard

**Confirm first:**
```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```

Wait for exact confirmation.

If confirmed:
```bash
git checkout main
git branch -D <feature-branch>
```

Then cleanup worktree if applicable (see Worktree Cleanup below).

### Worktree Cleanup

**For Options 1, 4** (Option 2 preserves worktree for review feedback):

Check if in worktree:
```bash
git worktree list | grep $(git branch --show-current)
```

If yes, **navigate out before removing:**

```bash
# Get the main repo path (first entry in worktree list)
main_repo=$(git worktree list | head -1 | awk '{print $1}')

# Navigate to main repo FIRST
cd "$main_repo"

# NOW remove the worktree
git worktree remove <worktree-path>
```

**Why `cd` first:** Claude Code's Bash tool persists CWD between calls. The kernel cannot fully remove a directory that is any process's CWD.

### Step 4: Remind About Test Plan

**For Options 1, 2, and 3:**

If a human test plan was generated (check `docs/test-plans/`), remind the user:

```
Human test plan available at: docs/test-plans/<plan-name>.md

This documents:
- What automated tests cover
- What requires human verification
- End-to-end scenarios to manually test

Review before considering this work fully complete.
```

**Skip for Option 4 (Discard).**

## Quick Reference

| Option | Delegates to | Update Context | Keep Worktree | Test Plan Reminder |
|--------|-------------|----------------|---------------|-------------------|
| 1. Merge locally | merge-to-main | ✓ | - | ✓ |
| 2. Create PR | make-pr | ✓ | ✓ | ✓ |
| 3. Keep as-is | — | - | ✓ | ✓ |
| 4. Discard | — | - | - | - |

## Common Mistakes

**Open-ended questions**
- Problem: "What should I do next?" — ambiguous
- Fix: Present exactly 4 structured options

**Removing worktree while CWD is inside it**
- Problem: `getcwd: cannot access parent directories` or `fatal: cannot remove worktree`
- Fix: Always `cd` to the main repo root before removing

**No confirmation for discard**
- Problem: Accidentally delete work
- Fix: Require typed "discard" confirmation

## Red Flags

**Never:**
- Delete work without confirmation
- Force-push without explicit request
- Skip project context update before merge/PR

**Always:**
- Update project context before offering options
- Present exactly 4 options
- Get typed confirmation for Option 4
- Remind about human test plan for Options 1, 2 & 3 (if exists)

## Integration

**Called by:**
- **executing-an-implementation-plan** — After all tasks complete

**Delegates to:**
- **merge-to-main** — Option 1 (handles testing, merge, cleanup)
- **make-pr** — Option 2 (handles testing, push, PR creation)

**Pairs with:**
- **using-git-worktrees** — Cleans up worktree created by that skill
