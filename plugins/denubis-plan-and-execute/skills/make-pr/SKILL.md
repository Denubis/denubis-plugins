---
name: make-pr
description: Use when creating a pull request from a feature branch - discovers project test commands, runs all gates, pushes branch, and creates PR via gh; blocks on test failure to prevent broken PRs
user-invocable: true
disable-model-invocation: true
---

# Make PR

Create a pull request from the current branch after verifying all test gates pass.

**Core principle:** Never push a broken branch. Discover what tests exist, run them all, block on failure.

**Announce at start:** "I'm using the make-pr skill to create a pull request."

## Step 1: Preflight Checks

Verify the branch is ready for a PR:

```bash
# Must not be on main/master
current=$(git branch --show-current)

# Must have commits ahead of base
git log main..HEAD --oneline
```

**If on main/master:** Stop. "You're on the main branch. Switch to a feature branch first."

**If no commits ahead:** Stop. "No commits ahead of main. Nothing to PR."

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

Resolve conflicts with `git rebase --continue`, then run /make-pr again.
```

Stop. Do not auto-resolve.

**If rebase succeeds:** Continue to Step 3.

## Step 3: Discover Test Commands

Check sources in priority order. Use the **first source that provides test commands**:

### Priority 1: `.ed3d/testing-guidance.md`

Read `.ed3d/testing-guidance.md` if it exists. Parse all `### Heading (required)` sections under `## Test Suites` and extract fenced code blocks as commands.

See `testing-guidance-format.md` in this skill directory for the format specification.

Also read any `## Pre-PR Gate` section for additional constraints.

### Priority 2: CLAUDE.md test commands

Read the project's `CLAUDE.md`. Look for test commands in sections like `## Testing`, `## Commands`, `## Development`, or similar. Extract any commands that run tests, linters, or type-checkers.

### Priority 3: `.ed3d/implementation-plan-guidance.md`

Read `.ed3d/implementation-plan-guidance.md` if it exists. Look for pre-PR gates or test commands.

### Priority 4: Fallback

If none of the above exist or provide test commands:

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

## Step 4: Run All Test Gates

Run each discovered test command sequentially. Capture the output and exit code.

```
Running gate 1/N: [name]...
  [command]
  → PASSED / FAILED (exit code X)

Running gate 2/N: [name]...
  [command]
  → PASSED / FAILED (exit code X)
```

**If ANY gate fails:**

```
Gate "[name]" failed (exit code X).

[Show relevant failure output]

Cannot create PR with failing tests. Fix the failures and try again.
```

Stop. Do not proceed to push or PR creation.

**If ALL gates pass:** Continue to Step 5.

## Step 5: Determine Base Branch and PR Details

```bash
# Find base branch
git merge-base HEAD main 2>/dev/null && echo "main" || echo "master"
```

Analyse the branch commits to draft PR title and body:

```bash
git log main..HEAD --oneline
git diff main..HEAD --stat
```

**Draft a PR title:** Under 70 characters. Focus on what changed, not how.

**Draft a PR body:** Use this structure:

```markdown
## Summary
- [2-3 bullets of what changed and why]

## Test Plan
- [What was verified]
- [How to test manually if applicable]
```

## Step 6: Push and Create PR

```bash
# Push branch
git push -u origin $(git branch --show-current)

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<bullets>

## Test Plan
<verification steps>
EOF
)"
```

**Report the PR URL when done.**

## Step 7: Post-PR Checks

After PR creation:

1. **Worktree cleanup check:** If in a worktree, report the worktree path but do NOT clean it up — the user may need it for review feedback.

2. **Issue label cleanup:** If a design plan in `docs/design-plans/` references a GitHub issue with `implementation-planned` label, remove it:
   ```bash
   gh issue edit <number> --remove-label "implementation-planned"
   ```
   Best-effort — warn and continue if this fails.

3. **Test plan reminder:** If `docs/test-plans/` contains a test plan, remind:
   ```
   Human test plan available at: docs/test-plans/<name>.md
   Review before considering this work fully complete.
   ```

## Quick Reference

| Step | Action | Blocks on failure |
|------|--------|-------------------|
| 1 | Preflight (branch, commits) | Yes |
| 2 | Sync with remote, rebase on main | Yes (conflicts, local ahead) |
| 3 | Discover test commands | No (fallback to pytest) |
| 4 | Run all test gates | Yes |
| 5 | Draft PR title/body | No |
| 6 | Push and create PR | Yes (push/gh failure) |
| 7 | Post-PR cleanup | No (best-effort) |

## Common Mistakes

**Skipping test discovery**
- Problem: Running only `pytest` when project has additional gates (e2e, docs build, linting)
- Fix: Always check `.ed3d/testing-guidance.md` first

**Creating PR with failing tests**
- Problem: "Tests mostly pass" or "that failure is unrelated"
- Fix: ALL gates must pass. No exceptions. If a failure is genuinely unrelated, the user can tell you to skip it explicitly.

**Pushing to wrong remote**
- Problem: Fork vs upstream confusion
- Fix: Use `origin` and let the gh-fork-guard hook catch mistakes

## Red Flags — STOP

If you find yourself reasoning any of these, you're rationalising:
- "That test failure is pre-existing" — verify with `git stash && pytest && git stash pop`
- "Tests mostly pass" — mostly ≠ all
- "I'll create the PR and fix it after" — broken PRs waste reviewer time
- "The test is flaky" — run it again to confirm; if it passes on retry, it passes

All mean: run the tests, respect the results.

## Integration

**Pairs with:**
- **finishing-a-development-branch** — Option 2 delegates here
- **merge-to-main** — alternative path when PR isn't needed
- **requesting-code-review** — run before make-pr for thorough review

**Test discovery convention:** See `testing-guidance-format.md` in this skill directory.
