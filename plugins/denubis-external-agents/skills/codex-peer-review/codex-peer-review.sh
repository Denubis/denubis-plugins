#!/usr/bin/env bash
# Self-contained codex critical-peer-review smoke test.
#
# The rubric (review-method.md, a copy of the critical-peer-review agent) lives
# next to this script, so the skill is self-contained. Each run stages the rubric
# + the target into one throwaway working dir and points codex (-C) at that root,
# so there are no out-of-root file references. That keeps the prompt working if
# reads are ever confined (bwrap/container); it does not itself enforce confinement.
# The review output is written to ./.review/ (gitignored) in the working directory.
#
# Usage: codex-peer-review.sh <file-or-dir-to-review>

set -euo pipefail

MODEL="gpt-5.5"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUBRIC="$SCRIPT_DIR/review-method.md"       # bundled copy of critical-peer-review.md
PROMPT_FILE="$SCRIPT_DIR/peer-review-smoke-prompt.md"

target="${1:?usage: codex-peer-review.sh <file-or-dir-to-review>}"
[ -e "$target" ]      || { echo "target not found: $target"      >&2; exit 1; }
[ -f "$RUBRIC" ]      || { echo "rubric not found: $RUBRIC"      >&2; exit 1; }
[ -f "$PROMPT_FILE" ] || { echo "prompt not found: $PROMPT_FILE" >&2; exit 1; }

# Throwaway staging codex reads from (-C points here); not persisted.
work="$(mktemp -d /tmp/codex-review.XXXXXX)"
mkdir -p "$work/under-review"
cp "$RUBRIC" "$work/REVIEW-METHOD.md"
cp -r "$target" "$work/under-review/"

# The review lands in ./.review/ (gitignored by design) in the working dir, so
# runs persist and coexist. Drop a self-ignoring guard if the dir has none, so
# writing into any repo — including the one under review — never leaks review
# output into version control. Absolute path so codex's -o is unambiguous
# regardless of its -C working root.
review_dir="$PWD/.review"
mkdir -p "$review_dir"
[ -e "$review_dir/.gitignore" ] || printf '# codex-peer-review output — disposable, may carry content sent to an external model\n*\n!.gitignore\n' > "$review_dir/.gitignore"
out="$review_dir/$(basename "$target").$(date +%Y%m%d-%H%M%S).REVIEW.md"

echo "package:  $work"
echo "rubric:   REVIEW-METHOD.md"
echo "target:   under-review/$(basename "$target")"
echo "running codex ($MODEL, read-only)…"
echo

# Prompt is read from stdin (codex exec reads instructions from a piped stdin).
codex exec \
  -s read-only \
  --ignore-user-config \
  -m "$MODEL" \
  --ephemeral \
  --skip-git-repo-check \
  -C "$work" \
  -o "$out" \
  < "$PROMPT_FILE"

echo
echo "review:   $out"
echo
echo "smoke check — prove it reviewed the real file, not a hallucination:"
echo "  pick a quoted phrase from the review and confirm it exists in the target:"
echo "  grep -nF '<quoted phrase>' '$target'"
