---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
user-invocable: false
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Directory Selection Process

Follow this priority order:

### 1. Check Existing Directories

```bash
# Check in priority order
ls -d .worktrees 2>/dev/null     # Preferred (hidden)
ls -d worktrees 2>/dev/null      # Alternative
```

**If found:** Use that directory. If both exist, `.worktrees` wins.

### 2. Check CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

**If preference specified:** Use it without asking.

### 3. Ask User

If no directory exists and no CLAUDE.md preference:

```
No worktree directory found. Where should I create worktrees?

1. .worktrees/ (project-local, hidden)
2. ~/.claude/worktrees/<project-name>/ (global location)

Which would you prefer?
```

## Safety Verification

### For Project-Local Directories (.worktrees or worktrees)

**MUST verify .gitignore before creating worktree:**

```bash
# Check if directory pattern in .gitignore
grep -q "^\.worktrees/$" .gitignore || grep -q "^worktrees/$" .gitignore
```

**If NOT in .gitignore:**

Per Jesse's rule "Fix broken things immediately":
1. Add appropriate line to .gitignore
2. Commit the change
3. Proceed with worktree creation

**Why critical:** Prevents accidentally committing worktree contents to repository.

### For Global Directory (~/.claude/worktrees)

No .gitignore verification needed - outside project entirely.

## Creation Steps

### 1. Detect Project Name

```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. Create Worktree

```bash
# Determine full path
case $LOCATION in
  .worktrees|worktrees)
    path="$LOCATION/$BRANCH_NAME"
    ;;
  ~/.claude/worktrees/*)
    path="~/.claude/worktrees/$project/$BRANCH_NAME"
    ;;
esac

# Create worktree with new branch
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. Copy Environment Files

**Worktrees share the git repo but NOT untracked files like `.env`, database configs, or local settings.** These must be copied from the main checkout.

```bash
# Get main repo path
main_repo=$(git worktree list | head -1 | awk '{print $1}')

# Check for .env files in the main checkout and copy them
for env_file in .env .env.local .env.test .env.development; do
  if [ -f "$main_repo/$env_file" ] && [ ! -f "$env_file" ]; then
    cp "$main_repo/$env_file" "$env_file"
  fi
done
```

**Also check CLAUDE.md** for project-specific environment setup (database creation, service configuration, etc.). Common needs:
- **Database:** The project may need its own test database. Check if the test config references a specific database name or uses the same one as the main checkout.
- **Docker/services:** If the project uses `docker compose`, the worktree may need its own compose override or the services may already be shared.
- **Local config files:** Some projects have `config/local.py`, `settings.local.json`, or similar that are gitignored.

**If the project uses a database:** Ask the user whether the worktree should share the main checkout's database or create a separate one. Shared databases can cause test conflicts if both checkouts run tests simultaneously.

### 4. Run Project Setup

**Check CLAUDE.md** for project-specific setup instructions first. If none found, auto-detect:

```bash
# Python (preferred)
if [ -f pyproject.toml ]; then uv sync; fi

# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

### 5. Verify Clean Baseline

**Find the test command in CLAUDE.md** (or project config). Run it to ensure worktree starts clean.

**If tests fail:** Report failures, ask whether to proceed or investigate.

**If tests pass:** Report ready.

### 6. Report Location

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify .gitignore) |
| `worktrees/` exists | Use it (verify .gitignore) |
| Both exist | Use `.worktrees/` |
| Neither exists | Check CLAUDE.md → Ask user |
| Directory not in .gitignore | Add it immediately + commit |
| Tests fail during baseline | Report failures + ask |
| No pyproject.toml/package.json | Skip dependency install |
| Project has .env files | Copy from main checkout |
| Project uses a database | Ask user: share or create separate |
| Removing a worktree | `cd` to main repo first, then `git worktree remove` |

## Removing Worktrees Safely

When removing a worktree, **you MUST ensure your CWD is outside the worktree first.** This is a POSIX limitation: the kernel cannot remove a directory that is any process's CWD. Claude Code's Bash tool persists CWD between calls, so after working in a worktree your CWD is almost certainly inside it.

```bash
# Get the main repo path
main_repo=$(git worktree list | head -1 | awk '{print $1}')

# Navigate out FIRST
cd "$main_repo"

# THEN remove
git worktree remove <worktree-path>
```

**Failure modes if you skip `cd`:**
- Modern git: `fatal: cannot remove worktree '<path>': '<path>' is the current working directory`
- Older git: `pwd: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory`
- Both are unrecoverable without navigating to a valid directory first

**Note:** The `finishing-a-development-branch` skill handles this automatically. This section documents the principle for any other context where worktree removal is needed.

## Common Mistakes

**Skipping .gitignore verification**
- **Problem:** Worktree contents get tracked, pollute git status
- **Fix:** Always grep .gitignore before creating project-local worktree

**Assuming directory location**
- **Problem:** Creates inconsistency, violates project conventions
- **Fix:** Follow priority: existing > CLAUDE.md > ask

**Proceeding with failing tests**
- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

**Removing worktree while CWD is inside it**
- **Problem:** Shell can't resolve `getcwd()`, git can't remove the directory, every subsequent Bash call may fail
- **Fix:** Always `cd "$main_repo"` before `git worktree remove`. See "Removing Worktrees Safely" above.

**Skipping environment file setup**
- **Problem:** Tests fail with missing config, wrong database, or missing secrets because `.env` files are gitignored and not present in the new worktree
- **Fix:** Copy `.env*` files from main checkout before running setup. Check CLAUDE.md for database/service configuration needs.

**Hardcoding setup commands**
- **Problem:** Breaks on projects using different tools
- **Fix:** Auto-detect from project files (package.json, etc.)

## Example Workflow

```
You: I'm using the using-git-worktrees skill to set up an isolated workspace.

[Check .worktrees/ - exists]
[Verify .gitignore - contains .worktrees/]
[Create worktree: git worktree add .worktrees/auth -b feature/auth]
[Run uv sync]
[Find test command in CLAUDE.md → uv run pytest]
[Run uv run pytest - 47 passing]

Worktree ready at /home/user/myproject/.worktrees/auth
Tests passing (47 tests, 0 failures)
Ready to implement auth feature
```

## Red Flags

**Never:**
- Create worktree without .gitignore verification (project-local)
- Skip baseline test verification
- Proceed with failing tests without asking
- Assume directory location when ambiguous
- Skip CLAUDE.md check
- Run `git worktree remove` while CWD is inside the worktree

**Always:**
- Follow directory priority: existing > CLAUDE.md > ask
- Verify .gitignore for project-local
- Auto-detect and run project setup
- Verify clean test baseline
- `cd` to main repo root before removing a worktree

## Integration

**Called by:**
- **brainstorming** (Phase 4) - REQUIRED when design is approved and implementation follows
- Any skill needing isolated workspace

**Pairs with:**
- **finishing-a-development-branch** - REQUIRED for cleanup after work complete
- **executing-an-implementation-plan** - Work happens in this worktree
