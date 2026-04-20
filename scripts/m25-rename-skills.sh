#!/usr/bin/env bash
# M25: Rename worker skills to {parent}-{action} convention
#
# Usage: ./scripts/m25-rename-skills.sh [--dry-run]
#
# This script:
# 1. Renames skill directories via git mv
# 2. Two-pass replacement of all references (old->placeholder->new)
# 3. Adds family: field to frontmatter (renamed + multi-parent skills)
# 4. Verifies no stale references or leftover placeholders remain
#
# Replacement runs BEFORE frontmatter family: addition. This prevents
# substring corruption (e.g. session-naming matching inside exec-session-naming)
# because the frontmatter still contains the old name when replacements run.
#
# Only replaces references in plugins/ and root CLAUDE.md/AGENTS.md.
# Historical docs (docs/) are NOT modified -- they are records of past work.
#
# Run --dry-run first to see what would change.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILLS_DIR="$REPO_ROOT/plugins/denubis-plan-and-execute/skills"
PLUGIN_PREFIX="denubis-plan-and-execute"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE ==="
fi

# --- Renames: old_name|new_name|parent_name ---
# brainstorming and defense-in-depth are common English words;
# renaming them corrupts prose. They get family: only (in MULTI_PARENT).
ACTUAL_RENAMES=(
    "functional-core-imperative-shell|coding-fcis|coding-effectively"
    "writing-implementation-plans|impl-plan-write|starting-an-implementation-plan"
    "asking-clarifying-questions|design-clarify|starting-a-design-plan"
    "verification-before-completion|coding-verify|coding-effectively"
    "property-based-testing|coding-property-testing|coding-effectively"
    "test-driven-development|coding-tdd|coding-effectively"
    "writing-design-plans|design-write|starting-a-design-plan"
    "update-architecture-docs|architecture-update|maintain-architecture"
    "writing-good-tests|coding-good-tests|coding-effectively"
    "refactoring-rubric|exec-refactoring-rubric|executing-an-implementation-plan"
    "python-idioms|coding-python-idioms|coding-effectively"
    "coherence-review|exec-coherence-review|executing-an-implementation-plan"
    "session-naming|exec-session-naming|executing-an-implementation-plan"
    "human-uat-gate|exec-uat-gate|executing-an-implementation-plan"
)

# --- Multi-parent / common-word skills: add family: metadata only ---
MULTI_PARENT=(
    "finishing-a-development-branch|executing-an-implementation-plan,make-pr,merge-to-main"
    "requesting-code-review|executing-an-implementation-plan,finishing-a-development-branch,make-pr,merge-to-main"
    "proleptic-challenge|executing-an-implementation-plan,design-write"
    "brainstorming|starting-a-design-plan"
    "defense-in-depth|coding-effectively"
)

# Sort by old name length descending (longest first for replacement safety)
IFS=$'\n' SORTED_RENAMES=($(for r in "${ACTUAL_RENAMES[@]}"; do
    old="${r%%|*}"
    echo "${#old} $r"
done | sort -rn | sed 's/^[0-9]* //'))
unset IFS

echo ""
echo "=== Phase 1: Directory renames (git mv) ==="

for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"
    old_dir="$SKILLS_DIR/$old"
    new_dir="$SKILLS_DIR/$new"

    if [[ -d "$old_dir" ]]; then
        echo "  git mv $old -> $new"
        if [[ "$DRY_RUN" == false ]]; then
            git mv "$old_dir" "$new_dir"
        fi
    elif [[ -d "$new_dir" ]]; then
        echo "  SKIP $old -> $new (already renamed)"
    else
        echo "  ERROR: $old_dir does not exist!"
        exit 1
    fi
done

echo ""
echo "=== Phase 2: Two-pass reference replacement ==="
echo "  Scope: plugins/ *.md and *.py, root CLAUDE.md/AGENTS.md"
echo "  Excludes: docs/ (historical records)"
echo ""
echo "  Frontmatter still contains old names at this point."
echo "  Replacements update everything including frontmatter name: fields."

# Collect .md and .py files in plugins/ (active code, not historical docs)
mapfile -t TARGET_FILES < <(find "$REPO_ROOT/plugins" \( -name '*.md' -o -name '*.py' \) -type f 2>/dev/null)

# Also include root CLAUDE.md or AGENTS.md
for f in "$REPO_ROOT/CLAUDE.md" "$REPO_ROOT/AGENTS.md"; do
    [[ -f "$f" ]] && TARGET_FILES+=("$f")
done

# Generate deterministic placeholders
declare -A PLACEHOLDERS
for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"
    PLACEHOLDERS["$old"]="__RENAME_${old//-/_}__"
done

echo "  Pass 1: old names -> placeholders (longest-first to avoid partial matches)"

for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"
    placeholder="${PLACEHOLDERS[$old]}"
    qualified_old="$PLUGIN_PREFIX:$old"
    qualified_placeholder="$PLUGIN_PREFIX:$placeholder"

    match_count=0
    for f in "${TARGET_FILES[@]}"; do
        if grep -qP "\b\Q$old\E\b" "$f" 2>/dev/null; then
            ((match_count++)) || true
        fi
    done

    if [[ $match_count -gt 0 ]]; then
        echo "    $old -> $placeholder ($match_count files)"
        if [[ "$DRY_RUN" == false ]]; then
            for f in "${TARGET_FILES[@]}"; do
                # Replace qualified form first (plugin:skill-name)
                perl -i -pe "s/\b\Q$qualified_old\E\b/$qualified_placeholder/g" "$f"
                # Then bare form (not preceded by colon -- qualified already handled)
                perl -i -pe "s/(?<!:)\b\Q$old\E\b/$placeholder/g" "$f"
            done
        fi
    else
        echo "    $old -> $placeholder (0 files)"
    fi
done

echo ""
echo "  Pass 2: placeholders -> new names"

for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"
    placeholder="${PLACEHOLDERS[$old]}"
    qualified_placeholder="$PLUGIN_PREFIX:$placeholder"
    qualified_new="$PLUGIN_PREFIX:$new"

    echo "    $placeholder -> $new"
    if [[ "$DRY_RUN" == false ]]; then
        for f in "${TARGET_FILES[@]}"; do
            perl -i -pe "s/\Q$qualified_placeholder\E/$qualified_new/g" "$f"
            perl -i -pe "s/\Q$placeholder\E/$new/g" "$f"
        done
    fi
done

echo ""
echo "=== Phase 3: Add family: to all renamed and multi-parent skills ==="

# Add family: to renamed skills (name: already correct from Phase 2 replacement)
for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"
    if [[ "$DRY_RUN" == true ]]; then
        skill_file="$SKILLS_DIR/$old/SKILL.md"
    else
        skill_file="$SKILLS_DIR/$new/SKILL.md"
    fi

    if [[ ! -f "$skill_file" ]]; then
        echo "  ERROR: $skill_file not found!"
        exit 1
    fi

    echo "  $new/SKILL.md: family: $parent"
    if [[ "$DRY_RUN" == false ]]; then
        if ! grep -q "^family:" "$skill_file"; then
            perl -i -pe "s/^(name: \Q$new\E)\$/\$1\nfamily: $parent/" "$skill_file"
        fi
    fi
done

# Add family: to multi-parent / common-word skills (no rename, name unchanged)
for entry in "${MULTI_PARENT[@]}"; do
    IFS='|' read -r name parents <<< "$entry"
    skill_file="$SKILLS_DIR/$name/SKILL.md"

    if [[ ! -f "$skill_file" ]]; then
        echo "  ERROR: $skill_file not found!"
        exit 1
    fi

    echo "  $name/SKILL.md: family: $parents"
    if [[ "$DRY_RUN" == false ]]; then
        if ! grep -q "^family:" "$skill_file"; then
            perl -i -pe "s/^(name: \Q$name\E)\$/\$1\nfamily: $parents/" "$skill_file"
        fi
    fi
done

echo ""
echo "=== Phase 4: Verification ==="
echo "  Checking plugins/ for stale old names and leftover placeholders"

STALE_FOUND=false
for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"

    stale=$(grep -rlP "\b\Q$old\E\b" "$REPO_ROOT/plugins" 2>/dev/null || true)
    if [[ -n "$stale" ]]; then
        echo "  STALE: '$old' still found in:"
        echo "$stale" | sed 's/^/    /'
        STALE_FOUND=true
    fi
done

PLACEHOLDER_FOUND=false
for entry in "${SORTED_RENAMES[@]}"; do
    IFS='|' read -r old new parent <<< "$entry"
    placeholder="${PLACEHOLDERS[$old]}"

    leftover=$(grep -rl "$placeholder" "$REPO_ROOT/plugins" 2>/dev/null || true)
    if [[ -n "$leftover" ]]; then
        echo "  LEFTOVER PLACEHOLDER: '$placeholder' still found in:"
        echo "$leftover" | sed 's/^/    /'
        PLACEHOLDER_FOUND=true
    fi
done

# Check for double-prefixed corruption (the bug this script was designed to avoid)
DOUBLE_FOUND=false
for pattern in "exec-exec-" "coding-coding-" "design-design-" "impl-plan-impl-plan-" "architecture-architecture-"; do
    doubles=$(grep -rl "$pattern" "$REPO_ROOT/plugins" 2>/dev/null || true)
    if [[ -n "$doubles" ]]; then
        echo "  DOUBLE PREFIX: '$pattern' found in:"
        echo "$doubles" | sed 's/^/    /'
        DOUBLE_FOUND=true
    fi
done

if [[ "$PLACEHOLDER_FOUND" == true ]]; then
    echo ""
    echo "ERROR: Leftover placeholders found. Pass 2 incomplete."
elif [[ "$DOUBLE_FOUND" == true ]]; then
    echo ""
    echo "ERROR: Double-prefixed names found. Replacement order bug."
elif [[ "$STALE_FOUND" == true ]]; then
    echo ""
    echo "WARNING: Stale references found in plugins/. Review the files above."
else
    echo "  All clean. No stale names, no placeholders, no double-prefixes."
fi

echo ""
echo "=== Summary ==="
echo "  Renamed: ${#SORTED_RENAMES[@]} skills"
echo "  Multi-parent/common-word family: added to ${#MULTI_PARENT[@]} skills"
echo "  Historical docs (docs/) were NOT modified."
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo "This was a dry run. No changes were made."
    echo "Run without --dry-run to apply changes."
fi
