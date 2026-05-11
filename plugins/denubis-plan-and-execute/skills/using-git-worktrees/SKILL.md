---
name: using-git-worktrees
description: Use when starting isolated feature work or when the user asks for a worktree - sets up worktrees with project-specific config and LFS handling
user-invocable: true
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository. Claude Code has built-in worktree support via `claude -w` (which uses `.claude/worktrees/`). This skill layers project-specific setup on top: LFS handling, dependency installation, `.ed3d/worktree-setup.md` instructions, and baseline test verification.

**Two worktree locations exist:**
- **`.worktrees/`** — our convention for mid-session worktrees (project-local, gitignored)
- **`.claude/worktrees/`** — Claude Code's built-in location (used by `claude -w`)

Both are valid. The skill handles either.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## How Worktrees Are Created

### Starting a new session in a worktree

Recommend the user launch a new session with `claude -w`:

```bash
claude -w feature-auth                  # Named worktree
claude -w 42-add-oauth-support          # Named after issue (see Naming section)
claude -w feature-auth --tmux           # With tmux session
```

The user runs this from their terminal, not from within Claude. After launching, this skill runs setup steps in the new session.

### Creating a worktree mid-session

When isolation is needed during an existing session (e.g., brainstorming approved a design, implementation plan starting), use `.worktrees/`:

```bash
git worktree add .worktrees/<name> -b <branch-name>
cd .worktrees/<name>
```

**MUST verify `.worktrees/` is gitignored before creating:**

```bash
git check-ignore -q .worktrees/test 2>/dev/null
```

If `.worktrees/` is not ignored, add it to `.gitignore` immediately, commit, then proceed.

### Detecting an existing worktree

If the session is already inside a worktree (user launched with `claude -w`), detect it and skip creation:

```bash
# Returns the .git dir — if it's a file pointing elsewhere, we're in a worktree
git rev-parse --git-common-dir
# If this differs from $(git rev-parse --git-dir), we're in a worktree
```

If already in a worktree, proceed directly to setup steps.

## Naming Worktrees

### From a git issue

When the user references an issue number, construct a descriptive name:

```bash
# Fetch issue title for a meaningful branch name
gh issue view 42 --json title,number --jq '"\(.number)-\(.title)"' | \
  tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-' | head -c 50
# Result: 42-add-oauth-support
```

Use this as the worktree name: `claude -w 42-add-oauth-support` or `git worktree add .worktrees/42-add-oauth-support -b 42-add-oauth-support`.

### From a description

When the user describes the work without an issue number, derive a short kebab-case name from the description. Keep it under 30 characters. Ask if ambiguous.

### Quick reference

| Source | Example name |
|--------|-------------|
| Issue #42 "Add OAuth support" | `42-add-oauth-support` |
| User says "fix the login bug" | `fix-login-bug` |
| Design plan approved | `implement-<plan-slug>` |
| No context given | Ask the user |

## Setup Steps

After the worktree exists and you're inside it, run these steps in order.

### 1. Handle LFS Files

**Git LFS and worktrees have a known bad interaction.** LFS-tracked files can appear as modified due to pointer/content mismatch. This causes pre-commit's stash mechanism to fail — hooks pass, but the stash restore fails and the commit is aborted.

```bash
if git lfs env >/dev/null 2>&1; then
  git diff --name-only | while IFS= read -r f; do
    [ -n "$f" ] && \
      git check-attr filter -- "$f" 2>/dev/null | grep -q 'filter: lfs' && \
      git update-index --assume-unchanged -- "$f"
  done
fi
```

**Why:** The files aren't actually changed — the filter driver transforms content differently in the worktree context. `assume-unchanged` stops git from reporting them as modified, preventing pre-commit stash failures.

This is automatic. No project configuration needed.

### 2. Ensure `.worktreeinclude` Exists

Claude Code's `.worktreeinclude` file (in the project root, `.gitignore` syntax) tells it which gitignored files to copy into new worktrees. If the project has `.env` files but no `.worktreeinclude`, suggest creating one:

```bash
main_repo=$(git worktree list | head -1 | awk '{print $1}')
if [ ! -f "$main_repo/.worktreeinclude" ]; then
  ls "$main_repo"/.env* 2>/dev/null
fi
```

If `.env` files exist but `.worktreeinclude` doesn't, tell the user:

> This project has `.env` files but no `.worktreeinclude`. Creating one ensures worktrees automatically get these files. Shall I create it?

A typical `.worktreeinclude`:
```
.env
.env.local
.env.test
.env.development
```

For the current worktree, if `.worktreeinclude` didn't exist at creation time, copy the files manually:

```bash
for env_file in .env .env.local .env.test .env.development; do
  if [ -f "$main_repo/$env_file" ] && [ ! -f "$env_file" ]; then
    cp "$main_repo/$env_file" "$env_file"
  fi
done
```

### 3. Install Dependencies and Run Project Setup

This step has two parts, always in this order: **auto-detect first, then custom instructions.**

**Part A: Auto-detect and install dependencies:**

```bash
# Python
if [ -f pyproject.toml ]; then uv sync; fi

# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

**Part B: Check `.ed3d/worktree-setup.md` for additional instructions:**

```bash
main_repo=$(git worktree list | head -1 | awk '{print $1}')
if [ -f "$main_repo/.ed3d/worktree-setup.md" ]; then
  cat "$main_repo/.ed3d/worktree-setup.md"
fi
```

This file contains plain instructions for post-install worktree setup — migrations to run, databases to create, config files to copy. Execute these **after** dependency installation (Part A). If any step is destructive or unclear, confirm with the user before executing.

### 4. Verify Clean Baseline

**Find the test command** in CLAUDE.md or project config. Run it to ensure the worktree starts clean.

**If tests fail:** Report failures, ask whether to proceed or investigate.

**If tests pass:** Report ready.

### 5. Report

```
Worktree ready at <full-path>
Branch: <branch-name>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| New session needed | Recommend `claude -w <name>` |
| Mid-session isolation | `git worktree add .worktrees/<name>` (verify .gitignore) |
| Already in a worktree | Skip creation, run setup steps |
| Issue number given | Fetch title with `gh issue view`, build descriptive name |
| LFS configured | Auto-apply `assume-unchanged` to dirty LFS files |
| No `.worktreeinclude` but `.env` files exist | Suggest creating `.worktreeinclude` |
| `.ed3d/worktree-setup.md` exists | Read from main checkout, follow its instructions |
| No pyproject.toml/package.json | Skip dependency install |
| Tests fail during baseline | Report failures + ask |
| Removing a worktree | `cd` to main repo first, then `git worktree remove` |

## `.ed3d/worktree-setup.md` Format

This file lives in the project's `.ed3d/` directory alongside `design-plan-guidance.md` and `implementation-plan-guidance.md`. It contains plain instructions for worktree-specific setup — things that go beyond dependency installation.

Example:

```markdown
# Worktree Setup

## Database
Create a separate test database for the worktree:
    createdb myproject_test
    uv run alembic upgrade head

## Services
Docker services are shared — do not run `docker compose up` in the worktree.
The main checkout's services at localhost:5432 and localhost:6379 are used by all worktrees.

## Additional config
Copy `config/local.example.py` to `config/local.py` and set DEBUG = True.
```

## Removing Worktrees Safely

**For worktrees created with `claude -w`:** Claude handles cleanup automatically on session exit. Worktrees with no changes are removed; worktrees with changes prompt to keep or discard.

**For worktrees created mid-session (`.worktrees/`):** You must remove them manually. Ensure your CWD is outside the worktree first — the kernel cannot remove a directory that is any process's CWD.

```bash
main_repo=$(git worktree list | head -1 | awk '{print $1}')
cd "$main_repo"
git worktree remove <worktree-path>
```

**Failure modes if you skip `cd`:**
- Modern git: `fatal: cannot remove worktree '<path>': '<path>' is the current working directory`
- Older git: `pwd: error retrieving current directory: getcwd: cannot access parent directories`

**Note:** The `finishing-a-development-branch` skill handles this automatically.

## Common Mistakes

**Skipping LFS handling**
- **Problem:** Pre-commit stash fails on dirty LFS files, aborting commits even though all hooks pass
- **Fix:** Always check for LFS after entering the worktree and `assume-unchanged` any dirty LFS-tracked files

**Ignoring `.ed3d/worktree-setup.md`**
- **Problem:** Project-specific setup steps are skipped, leading to broken state (missing databases, unmigrated schemas)
- **Fix:** Always check for `.ed3d/worktree-setup.md` in the main checkout

**Skipping .gitignore verification for `.worktrees/`**
- **Problem:** Worktree contents get tracked, pollute git status
- **Fix:** Always verify `.worktrees/` is in `.gitignore` before creating mid-session worktrees

**Proceeding with failing tests**
- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

**Removing worktree while CWD is inside it**
- **Problem:** Shell can't resolve `getcwd()`, every subsequent Bash call may fail
- **Fix:** Always `cd "$main_repo"` before `git worktree remove`

**Skipping environment file setup**
- **Problem:** Tests fail with missing config or secrets
- **Fix:** Ensure `.worktreeinclude` exists or copy `.env*` files manually

## Example Workflows

### User invokes `/using-git-worktrees` for a new issue

```
User: /using-git-worktrees 42

You: I'm using the using-git-worktrees skill to set up an isolated workspace.

[Fetch issue #42: "Add OAuth support for SAML providers"]
[Recommend: claude -w 42-add-oauth-support --tmux]
[User launches new session]
```

### Mid-session worktree (from brainstorming)

```
You: I'm using the using-git-worktrees skill to set up an isolated workspace.

[Verify .gitignore contains .worktrees/]
[Create: git worktree add .worktrees/implement-oauth -b implement-oauth]
[Check LFS - configured, 38 dirty files → assume-unchanged applied]
[Check .worktreeinclude - exists, .env files already copied]
[Read .ed3d/worktree-setup.md - found, creating test database]
[Run uv sync]
[Run alembic upgrade head per worktree-setup.md]
[Run uv run pytest - 47 passing]

Worktree ready at /home/user/myproject/.worktrees/implement-oauth
Branch: implement-oauth
Tests passing (47 tests, 0 failures)
Ready to implement OAuth support
```

### Already in a worktree (launched with `claude -w`)

```
You: I'm using the using-git-worktrees skill to set up an isolated workspace.

[Detected: already in worktree at .claude/worktrees/feature-auth]
[Check LFS - not configured, skipping]
[Check .worktreeinclude - missing, but .env exists in main → suggesting creation]
[Read .ed3d/worktree-setup.md - not found, using auto-detection]
[Run npm install]
[Run npm test - 122 passing]

Worktree ready (already created by claude -w)
Tests passing (122 tests, 0 failures)
Ready to work
```

## Red Flags

**Never:**
- Skip `.gitignore` verification for `.worktrees/`
- Skip baseline test verification
- Proceed with failing tests without asking
- Run `git worktree remove` while CWD is inside the worktree
- Ignore `.ed3d/worktree-setup.md` when it exists

**Always:**
- Handle LFS files after entering the worktree
- Check for `.worktreeinclude` and suggest creating it if needed
- Check `.ed3d/worktree-setup.md` before falling back to auto-detection
- Auto-detect and run project setup
- Verify clean test baseline
- `cd` to main repo root before removing a worktree

## Integration

**Called by:**
- **starting-an-implementation-plan** - sets up workspace before implementation
- User invocation via `/using-git-worktrees`

**Pairs with:**
- **finishing-a-development-branch** - REQUIRED for cleanup after work complete
- **executing-an-implementation-plan** - work happens in this worktree
