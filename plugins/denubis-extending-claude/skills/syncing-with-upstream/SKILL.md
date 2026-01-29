---
name: syncing-with-upstream
description: Use when integrating changes from upstream ed3d-plugins into this fork - handles the ed3d->denubis rename, conflict resolution, and merge workflow
---

# Syncing with Upstream

## Overview

This fork (denubis-plugins) diverged from upstream (ed3d-plugins) with:
- Renamed plugins: `ed3d-*` → `denubis-*`
- Different philosophy: Opus for implementation, halt-on-failure, block on all severities
- Additional plugins: shortcut-detection hook, transcript archiving
- Removed plugins: house-style, playwright (wrong ecosystem)

When the user asks to sync, do it. This skill documents how.

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

Present the commits to the user. Let them identify which changes they want.

### 2. Merge or Cherry-Pick

**Prefer merge** for multiple commits (preserves history, easier future syncs):

```bash
git merge --no-commit upstream/main
```

**Use cherry-pick** for selective single commits:

```bash
git cherry-pick --no-commit <commit-hash>
```

**Why --no-commit:** Review and resolve before committing.

### 3. Resolve Conflicts

**Read every conflict.** Don't apply mechanical rules blindly.

Common patterns (as starting points, not rules):

| File | Typical Resolution | But Check For... |
|------|-------------------|------------------|
| `CHANGELOG.md` | Keep HEAD | Bug fixes to tooling |
| `README.md` | Merge both sections | Structural changes |
| `marketplace.json` | Keep HEAD | Schema changes |
| `plugins/ed3d-*/...` | Delete orphaned files | New plugins you might want |

**For skill/agent content:**
1. Read both versions
2. Check if you already have the change
3. If upstream improves something, apply the improvement to your version
4. If it conflicts with your philosophy, keep yours

### 4. Run Rename Script (with review)

If merge/cherry-pick created ed3d-* files or references:

```bash
# Dry run first - see what would change
./scripts/rename-upstream.sh --dry-run

# Review the output, then apply
./scripts/rename-upstream.sh
```

**Review the diff before committing.** The script does bulk replacement which may have edge cases:
- URLs containing `ed3d` that shouldn't change
- Comments referencing upstream that should stay as-is
- New plugins you might want to keep as `ed3d-*`

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

## Automation Script

The `scripts/rename-upstream.sh` script:
- Renames `plugins/ed3d-*` → `plugins/denubis-*`
- Replaces `ed3d` with `denubis` in file contents
- Updates author info

**Always run with `--dry-run` first** to review changes before applying.

## What NOT to Merge

- **Version bumps**: Your versions diverge intentionally
- **Changelog entries**: Maintain your own changelog
- **Plugins you removed**: house-style, playwright

## Example Session

```bash
# 1. Fetch and show user
git fetch upstream
git log --oneline main..upstream/main

# 2. User says "merge those"
git merge --no-commit upstream/main

# 3. Check conflicts
git status --short
# UU .claude-plugin/marketplace.json
# UU CHANGELOG.md
# ...

# 4. Resolve each conflict (read both sides!)
# Edit files...

# 5. Check rename script impact
./scripts/rename-upstream.sh --dry-run

# 6. Apply renames if appropriate
./scripts/rename-upstream.sh

# 7. Review full diff
git diff --cached

# 8. Commit
git add -A
git commit -m "feat: merge upstream guidance improvements..."
```

## After Syncing

1. Run tests if any exist
2. Test affected skills manually
3. Push to origin when satisfied
