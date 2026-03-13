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

### Step 3: Run Fast Tests

Before committing, run lightweight test gates to catch obvious breakage.

**Discover fast test commands** using the same priority as make-pr/merge-to-main, but only `fast`-marked suites:

**Priority 1:** Read `.ed3d/testing-guidance.md` if it exists. Run only suites marked `(fast)` — e.g. `### Unit Tests (required, fast)`.

**Priority 2:** Read CLAUDE.md for test commands. If found, run only unit test commands (not e2e, not integration, not docs build).

**Priority 3:** Read `.ed3d/implementation-plan-guidance.md` for fast/unit test commands.

**Priority 4:** Fallback: `pytest tests/unit/` if a `tests/unit/` directory exists, otherwise `pytest` with a short timeout.

```
Running fast tests before commit...
  [command]
  → PASSED / FAILED
```

**If fast tests fail:**
```
Fast tests failed. Fix before committing:

[failure output]
```

Stop. Do not proceed to commit.

**If no fast test suites are discovered and no test directory exists:** Skip this step. Not every project has tests.

**If fast tests pass:** Continue to Step 4.

### Step 4: Plan Commits

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

### Step 5: Match Commit Style

From `git log` output, detect the repository's convention:

- Semantic prefixes (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
- Plain descriptions
- Other patterns

Match whatever the repo uses.

### Step 6: Draft and Confirm

**If `-m` was provided:** Use that message. Skip to Step 7.

**Otherwise:** Draft a concise commit message (1-2 sentences) focusing on the **why** not the **what**.

Present the plan to the user:

```
Commit plan:

1. [files] — "message"
2. [files] — "message"

Proceed?
```

Wait for confirmation. If the user adjusts, incorporate their feedback.

### Step 7: Execute Commits

For each commit:

```bash
# Stage specific files (never git add -A or git add .)
git add file1.py file2.py
```

Then use the **Write tool** (not Bash) to write the commit message:

```
Write .commit-msg.tmp with content:

Commit message here.

Co-Authored-By: Claude <noreply@anthropic.com>
```

Then commit with a **fixed** Bash command (allowable once, reusable forever):

```bash
git commit -F .commit-msg.tmp && rm -f .commit-msg.tmp
```

**Why Write tool + fixed Bash:**
- Write tool handles varying message content — no shell quoting, no injection, no `$()`.
- The Bash command is identical every time regardless of message content. Users can add `Bash(git commit -F .commit-msg.tmp && rm -f .commit-msg.tmp)` to their allow list once.
- `.commit-msg.tmp` in the working directory is visible, auditable, and cleaned up after commit.
- If `.commit-msg.tmp` already exists when Write is called, Write will show the user the overwrite — providing natural lockfile protection.

**Never use Bash to write commit messages** — no `printf`, `echo`, `cat`, or heredoc. The Write tool is the only safe path.

After all commits:

```bash
git status
```

Verify clean working tree (or expected remaining changes).

### Step 8: Report

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
- Use `printf`, `echo`, or `$()` command substitution for commit messages — shell injection risk

**ALWAYS:**
- Use Write tool for `.commit-msg.tmp`, then `git commit -F .commit-msg.tmp && rm -f .commit-msg.tmp` — no shell involvement in message content
- Include `Co-Authored-By: Claude <noreply@anthropic.com>`
- Stage files by name, not by wildcard
- Run fast tests before committing
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

**Shell injection in commit messages**
- Problem: `printf`, `echo`, `cat`, or heredoc in Bash with unescaped special characters
- Fix: Always use the Write tool for `.commit-msg.tmp`, never Bash
