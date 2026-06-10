---
name: merge-to-main
description: Use when merging a feature branch to main locally - runs all test gates before AND after merge, blocks on failure
user-invocable: true
disable-model-invocation: true
---

# Merge to Main

Merge the current feature branch to main after verifying all test gates pass, then re-verify on the merged result.

**Core principle:** Main must never be broken. Test before merge, test after merge, block on failure at either point.

**Announce at start:** "I'm using the merge-to-main skill to merge this branch."

## Step 1: Preflight Checks

### Merge policy opt-in (check first)

```bash
# Check for project-level merge policy
cat .ed3d/merge-policy 2>/dev/null
```

**If `.ed3d/merge-policy` does not exist:** Stop. Direct merge to main requires project-level opt-in. Use `/make-pr` instead to create a pull request. If the project intentionally uses direct merge (e.g. single-developer repo, no PR workflow), create `.ed3d/merge-policy` with a one-line explanation of why.

### Branch and state checks

```bash
# Must not already be on main/master
current=$(git branch --show-current)

# Must have commits ahead of base
git log main..HEAD --oneline

# Check for uncommitted changes
git status --porcelain
```

**If on main/master:** Stop. "You're already on main. Nothing to merge."

**If no commits ahead:** Stop. "No commits ahead of main. Nothing to merge."

**If uncommitted changes exist:** Stop. "Uncommitted changes detected. Commit or stash before merging."

## Step 2: Sync with Remote

Ensure main is up to date and the feature branch is rebased on top of it.

```bash
# Fetch latest from remote
git fetch origin

# Check if local main is ahead of remote (unusual — warn)
local_main=$(git rev-parse main)
remote_main=$(git rev-parse origin/main)
if [ "$(git merge-base "$local_main" "$remote_main")" = "$remote_main" ] && [ "$local_main" != "$remote_main" ]; then
  echo "WARNING: local main is ahead of origin/main"
fi
```

**If local main is ahead of remote:** Warn the user. "Local main has commits not on remote. Push main first, or confirm this is intentional."

```bash
# Update local main (without switching branches)
git fetch origin main:main

# Rebase feature branch onto updated main
git rebase main
```

**If rebase has conflicts:**
```
Rebase conflicts detected:

[list conflicting files]

Resolve conflicts with `git rebase --continue`, then run /merge-to-main again.
```

Stop. Do not auto-resolve.

**If rebase succeeds:** Continue to Step 3.

## Step 3: Discover Test Commands

Check sources in priority order. Use the **first source that provides test commands**:

### Priority 1: `.ed3d/testing-guidance.md`

Read `.ed3d/testing-guidance.md` if it exists. Parse all `### Heading (required)` sections under `## Test Suites` and extract fenced code blocks as commands.

See the `testing-guidance-format.md` in the `make-pr` skill directory for the format specification.

Also read any `## Pre-Merge Gate` section for additional constraints.

### Priority 2: CLAUDE.md test commands

Read the project's `CLAUDE.md`. Look for test commands in sections like `## Testing`, `## Commands`, `## Development`, or similar.

### Priority 3: `.ed3d/implementation-plan-guidance.md`

Read `.ed3d/implementation-plan-guidance.md` if it exists. Look for pre-merge gates or test commands.

### Priority 4: Fallback

```bash
pytest
```

**Report what was discovered:**
```
Test discovery: found [source]
Gates to run:
  1. [name]: [command]
  2. [name]: [command]
  ...
```

## Step 4: Run All Test Gates (Pre-Merge)

Run each discovered test command sequentially.

```
Running pre-merge gate 1/N: [name]...
  [command]
  → PASSED / FAILED (exit code X)
```

**If ANY gate fails:**
```
Pre-merge gate "[name]" failed (exit code X).

[Show relevant failure output]

Cannot merge with failing tests. Fix the failures and try again.
```

Stop. Do not merge.

**If ALL gates pass:** Continue to Step 5.

## Step 5: Merge

```bash
# Record feature branch name for cleanup
feature=$(git branch --show-current)

# Switch to main (already synced in Step 2)
git checkout main

# Merge feature branch (should be fast-forward after rebase)
git merge "$feature"
```

**If merge conflicts occur:**

```
Merge conflicts detected:

[list conflicting files]

Resolve conflicts, then run /merge-to-main again.
```

Stop. Do not auto-resolve conflicts.

## Step 6: Run All Test Gates (Post-Merge)

Re-run every test gate on the merged result. The merge may have introduced regressions even if both branches were individually clean.

```
Running post-merge gate 1/N: [name]...
  [command]
  → PASSED / FAILED (exit code X)
```

**If ANY gate fails:**

```
Post-merge gate "[name]" failed (exit code X).

[Show relevant failure output]

Main is currently in a merged-but-failing state.
Reverting the merge to restore main to a clean state.
```

```bash
git merge --abort 2>/dev/null || git reset --merge ORIG_HEAD
git checkout "$feature"
```

Report what failed and stop. The user needs to fix the issue on the feature branch.

**If ALL gates pass:** Continue to Step 7.

## Step 7: Clean Up

### Delete feature branch

```bash
git branch -d "$feature"
```

### Worktree cleanup

Check if the work was in a worktree:

```bash
git worktree list
```

If in a worktree, navigate out before removing:

```bash
# Get main repo path
main_repo=$(git worktree list | head -1 | awk '{print $1}')

# Navigate to main repo FIRST
cd "$main_repo"

# Remove worktree
git worktree remove <worktree-path>
```

**Why `cd` first:** The kernel cannot fully remove a directory that is any process's CWD. Modern git detects this and fails; older versions produce cryptic `getcwd` errors.

### Issue label cleanup

If a design plan in `docs/design-plans/` references a GitHub issue with `implementation-planned` label, remove it:

```bash
gh issue edit <number> --remove-label "implementation-planned"
```

Best-effort — warn and continue if this fails.

### Test plan reminder

If `docs/test-plans/` contains a test plan:

```
Human test plan available at: docs/test-plans/<name>.md
Review before considering this work fully complete.
```

## Quick Reference

| Step | Action | Blocks on failure |
|------|--------|-------------------|
| 1 | Preflight (branch, commits, clean) | Yes |
| 2 | Sync with remote, rebase on main | Yes (conflicts, local ahead) |
| 3 | Discover test commands | No (fallback to pytest) |
| 4 | Pre-merge test gates | Yes |
| 5 | Merge to main | Yes (conflicts) |
| 6 | Post-merge test gates | Yes (reverts merge) |
| 7 | Cleanup (branch, worktree, labels) | No (best-effort) |

## Common Mistakes

**Skipping post-merge tests**
- Problem: Both branches pass independently but merge introduces regressions
- Fix: Always re-run full suite after merge

**Leaving main broken after failed post-merge tests**
- Problem: Main has failing tests, blocks everyone
- Fix: Revert the merge immediately, report what failed

**Deleting branch before post-merge verification**
- Problem: Cannot recover if merge is bad
- Fix: Delete branch only after post-merge tests pass

**Removing worktree while CWD is inside it**
- Problem: `getcwd: cannot access parent directories` or `fatal: cannot remove worktree`
- Fix: `cd` to main repo root before `git worktree remove`

## Red Flags — STOP

If you find yourself reasoning any of these, you're rationalising:
- "Pre-merge tests passed, so post-merge will too" — merge introduces new interactions
- "I'll fix it on main" — fixing on main means main is broken while you fix
- "The conflict is trivial, I'll auto-resolve" — trivial conflicts can mask semantic bugs
- "Tests are slow, skip the second run" — speed ≠ correctness

All mean: run the tests, respect the results.

## Integration

**Pairs with:**
- **finishing-a-development-branch** — Option 1 delegates here
- **make-pr** — alternative path when review is needed
- **requesting-code-review** — run before merge-to-main for thorough review

**Test discovery convention:** See `testing-guidance-format.md` in the `make-pr` skill directory.
