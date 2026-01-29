#!/usr/bin/env bash
# Rename ed3d-* to denubis-* after cherry-picking or merging from upstream
# Usage: ./scripts/rename-upstream.sh [--dry-run]
#
# This script:
# 1. Renames directories: plugins/ed3d-* -> plugins/denubis-*
# 2. Replaces "ed3d" with "denubis" in file contents
# 3. Updates author info from Ed to Brian
#
# Run this AFTER merging/cherry-picking upstream commits, BEFORE committing.
# Always use --dry-run first to review what will change.

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE - No changes will be made ==="
    echo ""
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "=== Renaming upstream ed3d-* to denubis-* ==="
echo ""

# 1. Check for plugin directories to rename
echo "## Directory renames:"
found_dirs=false
for dir in plugins/ed3d-*; do
    if [[ -d "$dir" ]]; then
        found_dirs=true
        newdir="${dir/ed3d-/denubis-}"
        if [[ -d "$newdir" ]]; then
            echo "  MERGE: $dir -> $newdir (target exists, will merge contents)"
        else
            echo "  RENAME: $dir -> $newdir"
        fi

        if [[ "$DRY_RUN" == "false" ]]; then
            if [[ -d "$newdir" ]]; then
                # Copy files that don't exist in target, skip conflicts
                cp -rn "$dir"/* "$newdir"/ 2>/dev/null || true
                rm -rf "$dir"
            else
                git mv "$dir" "$newdir" 2>/dev/null || mv "$dir" "$newdir"
            fi
        fi
    fi
done
if [[ "$found_dirs" == "false" ]]; then
    echo "  (none found)"
fi
echo ""

# 2. Find files with ed3d references
echo "## Files with 'ed3d' references to update:"
files_to_update=()

while IFS= read -r -d '' file; do
    if file "$file" | grep -q 'text'; then
        if grep -q 'ed3d' "$file" 2>/dev/null; then
            files_to_update+=("$file")
            echo "  $file"
        fi
    fi
done < <(find . -type f \
    -not -path './.git/*' \
    -not -path './scripts/rename-upstream.sh' \
    -not -name '*.pyc' \
    -not -name '*.png' \
    -not -name '*.jpg' \
    -not -name '*.gif' \
    -print0)

if [[ ${#files_to_update[@]} -eq 0 ]]; then
    echo "  (none found)"
fi
echo ""

# Show what replacements will happen
if [[ ${#files_to_update[@]} -gt 0 ]]; then
    echo "## Replacements that will be applied:"
    echo "  ed3d-plugins -> denubis-plugins"
    echo "  ed3d-plan-and-execute -> denubis-plan-and-execute"
    echo "  ed3d-basic-agents -> denubis-basic-agents"
    echo "  ed3d-research-agents -> denubis-research-agents"
    echo "  ed3d-extending-claude -> denubis-extending-claude"
    echo "  ed3d-00-getting-started -> denubis-00-getting-started"
    echo "  ed3d-hook-* -> denubis-hook-*"
    echo "  ed3d-house-style -> denubis-house-style"
    echo "  ed3d-playwright -> denubis-playwright"
    echo "  @ed3d- -> @denubis-"
    echo ""
fi

# Apply replacements if not dry run
if [[ "$DRY_RUN" == "false" && ${#files_to_update[@]} -gt 0 ]]; then
    echo "Applying replacements..."
    for file in "${files_to_update[@]}"; do
        sed -i 's/ed3d-plugins/denubis-plugins/g' "$file"
        sed -i 's/ed3d-plan-and-execute/denubis-plan-and-execute/g' "$file"
        sed -i 's/ed3d-basic-agents/denubis-basic-agents/g' "$file"
        sed -i 's/ed3d-research-agents/denubis-research-agents/g' "$file"
        sed -i 's/ed3d-extending-claude/denubis-extending-claude/g' "$file"
        sed -i 's/ed3d-00-getting-started/denubis-00-getting-started/g' "$file"
        sed -i 's/ed3d-hook-/denubis-hook-/g' "$file"
        sed -i 's/ed3d-house-style/denubis-house-style/g' "$file"
        sed -i 's/ed3d-playwright/denubis-playwright/g' "$file"
        sed -i 's/@ed3d-/@denubis-/g' "$file"
    done
    echo ""
fi

# 3. Check for author info to update
echo "## Author info updates in plugin.json files:"
author_files=()
while IFS= read -r -d '' file; do
    if grep -q '"name": "Ed"' "$file" 2>/dev/null; then
        author_files+=("$file")
        echo "  $file"
    fi
done < <(find . -name 'plugin.json' -type f -print0)

if [[ ${#author_files[@]} -eq 0 ]]; then
    echo "  (none found)"
fi
echo ""

# Apply author updates if not dry run
if [[ "$DRY_RUN" == "false" && ${#author_files[@]} -gt 0 ]]; then
    echo "Updating author info..."
    for file in "${author_files[@]}"; do
        sed -i 's/"name": "Ed"/"name": "Brian Ballsun-Stanton"/g' "$file"
        sed -i 's/"email": "ed@ed3d.net"/"github": "denubis"/g' "$file"
    done
    echo ""
fi

echo "=== $(if [[ "$DRY_RUN" == "true" ]]; then echo "DRY RUN COMPLETE"; else echo "DONE"; fi) ==="

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "Run without --dry-run to apply these changes."
    echo "Then review with: git diff"
else
    echo ""
    echo "Review changes with: git diff"
    echo "Stage changes with: git add -A"
    echo "Then commit or continue resolving conflicts."
fi
