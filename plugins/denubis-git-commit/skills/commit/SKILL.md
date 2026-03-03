---
name: commit
description: Create git commits with proper analysis, message drafting, and project conventions. Use when asked to commit, or when /commit is invoked.
user-invocable: true
---

# Git Commit

Create well-structured git commits by analysing changes, drafting messages, and following project conventions.

**Announce at start:** "I'm using the commit skill to create a git commit."

## Arguments

- No args: analyse all changes, draft message, confirm with user
- `-m "message"`: use provided message directly (skip drafting)

## The Process

### Step 1: Gather State (parallel)

Run all three in parallel via Bash:

```bash
# 1. Untracked and modified files (NEVER use -uall)
git status

# 2. Staged and unstaged diffs
git diff HEAD

# 3. Recent commit messages for style matching
git log --oneline -15
```

### Step 2: Analyse Changes

From the gathered state:

1. **Check for sensitive files** (.env, credentials, keys, tokens). If found, warn the user and exclude them.
2. **Check for anything to commit.** If no untracked files and no modifications, say so and stop.
3. **Identify the nature of changes:** new feature, enhancement, bug fix, refactor, test, docs, etc.
4. **Group changes by concern** for potential multi-commit splitting.

### Step 3: Plan Commits

Follow the project's commit splitting rules:

| Changed files | Minimum commits |
|--------------|----------------|
| 1-2 files | 1 commit |
| 3-4 files | 2 commits |
| 5+ files | 3+ commits |

**Splitting rules:**
- Split by directory/module, then by concern
- Test files go with their implementation in the same commit
- Never separate a test from the code it tests

### Step 4: Match Commit Style

From `git log` output, detect the repository's convention:

- Semantic prefixes (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
- Plain descriptions
- Other patterns

Match whatever the repo uses.

### Step 5: Draft and Confirm

**If `-m` was provided:** Use that message. Skip to Step 6.

**Otherwise:** Draft a concise commit message (1-2 sentences) focusing on the **why** not the **what**.

Present the plan to the user:

```
Commit plan:

1. [files] — "message"
2. [files] — "message"

Proceed?
```

Wait for confirmation. If the user adjusts, incorporate their feedback.

### Step 6: Execute Commits

For each commit:

```bash
# Stage specific files (never git add -A or git add .)
git add file1.py file2.py

# Write message to temp file, commit with -F, clean up
# This avoids $() command substitution which triggers injection warnings.
printf '%s\n' 'Commit message here.' '' 'Co-Authored-By: Claude <noreply@anthropic.com>' > /tmp/commit-msg.txt && git commit -F /tmp/commit-msg.txt && rm -f /tmp/commit-msg.txt
```

After all commits:

```bash
git status
```

Verify clean working tree (or expected remaining changes).

### Step 7: Report

State what was committed. If there are remaining uncommitted changes, mention them.

## Safety Rules

**NEVER:**
- `git add -A` or `git add .` (can include secrets or binaries)
- `git push` (unless user explicitly asks)
- `--no-verify` or `--no-gpg-sign` (unless user explicitly asks)
- `--amend` (unless user explicitly asks — amending after hook failure destroys the previous commit)
- Force push to main/master
- Commit files that look like secrets (.env, credentials.json, \*.key, \*.pem)
- Use `-i` flag (interactive mode not supported)

**ALWAYS:**
- Use `printf > /tmp/commit-msg.txt && git commit -F /tmp/commit-msg.txt && rm -f /tmp/commit-msg.txt` for commit messages (avoids `$()` injection warnings)
- Include `Co-Authored-By: Claude <noreply@anthropic.com>`
- Stage files by name, not by wildcard
- Run `git status` after committing to verify
- Create NEW commits after hook failures (not amend)

## Pre-commit Hook Failures

If a commit is rejected by pre-commit hooks:

1. Read the hook output
2. Fix the issues
3. Re-stage the fixed files
4. Create a **NEW** commit (the failed commit never happened — amending would modify the previous commit)

## Common Mistakes

**Giant commits**
- Problem: Dumping everything into one commit
- Fix: Follow the splitting rules above

**Amending after hook failure**
- Problem: `--amend` modifies the PREVIOUS commit, not the failed one
- Fix: Always create a new commit after fixing hook issues

**Vague messages**
- Problem: "update code", "fix stuff"
- Fix: Focus on why the change was made

**Pushing without asking**
- Problem: User didn't want to push yet
- Fix: Never push unless explicitly asked
