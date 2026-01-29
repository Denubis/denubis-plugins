#!/usr/bin/env bash
# Rename ed3d-* to denubis-* after cherry-picking or merging from upstream
# Usage: ./scripts/rename-upstream.sh
#
# This script:
# 1. Renames directories: plugins/ed3d-* -> plugins/denubis-*
# 2. Replaces "ed3d" with "denubis" in file contents
# 3. Updates author info from Ed to Brian
#
# Run this AFTER cherry-picking upstream commits, BEFORE committing.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "=== Renaming upstream ed3d-* to denubis-* ==="

# 1. Rename plugin directories
for dir in plugins/ed3d-*; do
    if [[ -d "$dir" ]]; then
        newdir="${dir/ed3d-/denubis-}"
        if [[ -d "$newdir" ]]; then
            echo "Target $newdir already exists - merging contents..."
            # Copy files that don't exist in target, skip conflicts
            cp -rn "$dir"/* "$newdir"/ 2>/dev/null || true
            rm -rf "$dir"
        else
            echo "Renaming $dir -> $newdir"
            git mv "$dir" "$newdir" 2>/dev/null || mv "$dir" "$newdir"
        fi
    fi
done

# 2. Replace ed3d with denubis in file contents
echo "Replacing 'ed3d' with 'denubis' in file contents..."

# Find all text files (exclude .git and binary files)
find . -type f \
    -not -path './.git/*' \
    -not -path './scripts/rename-upstream.sh' \
    -not -name '*.pyc' \
    -not -name '*.png' \
    -not -name '*.jpg' \
    -not -name '*.gif' \
    -print0 | while IFS= read -r -d '' file; do
    if file "$file" | grep -q 'text'; then
        if grep -q 'ed3d' "$file" 2>/dev/null; then
            echo "  Updating: $file"
            sed -i 's/ed3d-plugins/denubis-plugins/g' "$file"
            sed -i 's/ed3d-plan-and-execute/denubis-plan-and-execute/g' "$file"
            sed -i 's/ed3d-basic-agents/denubis-basic-agents/g' "$file"
            sed -i 's/ed3d-research-agents/denubis-research-agents/g' "$file"
            sed -i 's/ed3d-extending-claude/denubis-extending-claude/g' "$file"
            sed -i 's/ed3d-00-getting-started/denubis-00-getting-started/g' "$file"
            sed -i 's/ed3d-hook-/denubis-hook-/g' "$file"
            sed -i 's/ed3d-house-style/denubis-house-style/g' "$file"
            sed -i 's/ed3d-playwright/denubis-playwright/g' "$file"
            # Generic fallback for any remaining ed3d references
            sed -i 's/@ed3d-/@denubis-/g' "$file"
        fi
    fi
done

# 3. Update author info in plugin.json files
echo "Updating author info..."
find . -name 'plugin.json' -type f -print0 | while IFS= read -r -d '' file; do
    if grep -q '"name": "Ed"' "$file" 2>/dev/null; then
        echo "  Updating author in: $file"
        sed -i 's/"name": "Ed"/"name": "Brian Ballsun-Stanton"/g' "$file"
        sed -i 's/"email": "ed@ed3d.net"/"github": "denubis"/g' "$file"
    fi
done

echo ""
echo "=== Done ==="
echo "Review changes with: git diff"
echo "Stage changes with: git add -A"
echo "Then commit or continue resolving conflicts."
