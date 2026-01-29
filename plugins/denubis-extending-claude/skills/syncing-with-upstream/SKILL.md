---
name: syncing-with-upstream
description: Use when integrating changes from upstream ed3d-plugins into this fork - handles the ed3d->denubis rename, conflict resolution, and selective cherry-picking
---

# Syncing with Upstream

## Overview

This fork (denubis-plugins) diverged from upstream (ed3d-plugins) with:
- Renamed plugins: `ed3d-*` → `denubis-*`
- Different philosophy: Opus for implementation, halt-on-failure, block on all severities
- Additional plugins: shortcut-detection hook, transcript archiving
- Removed plugins: house-style, playwright (wrong ecosystem)

Upstream continues development. This skill guides selective integration of useful changes.

## When to Use

- Periodically check upstream for new features
- When upstream fixes bugs you also have
- When upstream improves skills you use

## Prerequisites

Ensure upstream remote is configured:

```bash
git remote -v | grep upstream
# Should show: upstream https://github.com/ed3dai/ed3d-plugins.git
```

If not:
```bash
git remote add upstream https://github.com/ed3dai/ed3d-plugins.git
```

## The Process

### 1. Fetch and Review Upstream Changes

```bash
git fetch upstream
git log --oneline main..upstream/main
```

Review each commit. Categorise:
- **Content changes**: New features, bug fixes, skill improvements
- **Infrastructure changes**: Version bumps, changelog updates (usually skip)
- **Rename-only changes**: File moves within ed3d-* structure (skip)

### 2. Cherry-Pick Content Changes

Cherry-pick one commit at a time for review:

```bash
git cherry-pick --no-commit <commit-hash>
```

**Why --no-commit:** Allows reviewing and resolving conflicts before committing.

### 3. Resolve Conflicts

Common conflict patterns:

| File | Resolution |
|------|------------|
| `CHANGELOG.md` | Keep HEAD (your changelog is authoritative) |
| `README.md` | Merge both: keep your philosophy + add new content |
| `marketplace.json` | Keep HEAD (your plugin list is correct) |
| `how-to-customize.md` | Usually keep HEAD wording if better |
| `plugins/ed3d-*/...` | Delete orphaned ed3d-* files |

**For content files (skills, agents):**
- If change applies to your denubis-* version, apply manually
- Check if you already have the change (may have diverged earlier)

### 4. Run Rename Script (if needed)

If cherry-pick created ed3d-* files or references:

```bash
./scripts/rename-upstream.sh
```

This script:
- Renames `plugins/ed3d-*` → `plugins/denubis-*`
- Replaces `ed3d` with `denubis` in file contents
- Updates author info

### 5. Commit with Upstream Reference

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat: merge upstream [feature name] (<commit-hash>)

[Brief description of what changed]

Upstream commit: <full-hash>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

**Always reference the upstream commit hash** for traceability.

### 6. Repeat for Each Commit

Process commits in order. Small commits = easier conflict resolution.

## Automation Script

The `scripts/rename-upstream.sh` script handles bulk renaming. Run it after cherry-picks that introduce ed3d-* content.

## What NOT to Merge

- **Version bumps**: Your versions diverge intentionally
- **Changelog entries**: Maintain your own changelog
- **Plugins you removed**: house-style, playwright
- **Philosophy changes**: If upstream changes model tiers, review carefully

## Example Session

```bash
# 1. Fetch
git fetch upstream

# 2. Review
git log --oneline main..upstream/main
# 4b0ef81 feat(plan-and-execute): pass implementation guidance to per-phase code reviews
# 7b54ef9 doc: how-to-customize further assistance from the model

# 3. Cherry-pick first commit
git cherry-pick --no-commit 7b54ef9

# 4. Check status, resolve conflicts
git status
# Edit conflicted files...

# 5. Commit
git add -A
git commit -m "doc: how-to-customize suggest CLAUDE.md reading (7b54ef9)..."

# 6. Repeat for next commit
git cherry-pick --no-commit 4b0ef81
# ...
```

## After Syncing

1. Run tests if any exist
2. Test affected skills manually
3. Push to origin when satisfied

## Tracking Sync State

After syncing, note the last upstream commit you integrated:

```bash
git log --oneline upstream/main -1
# Record this in your commit message or a tracking file
```

This helps identify what's new on next sync.
