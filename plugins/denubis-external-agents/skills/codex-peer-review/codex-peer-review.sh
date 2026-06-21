#!/usr/bin/env bash
# Self-contained codex critical-peer-review runner.
#
# Stages the target's git repository MINUS gitignored files into a throwaway
# working dir and points codex (-C) at it, so the review can follow the target's
# cross-references (the code it cites, the bibliography, run logs) while
# gitignored files (raw data, secrets) are absent from codex's working tree.
#
# Because `-s read-only` does not confine reads, staging is what bounds what
# codex reaches for the repo's own files: it runs in /tmp and is never told the
# real repo path, so it has no route to the excluded files. This is strong, not
# cryptographic — a future bwrap wrapper that bind-mounts only this staged dir
# would make it a hard bound (and also block codex reading its own ~/.codex etc).
#
# The rubric (review-method.md, a copy of the critical-peer-review agent) lives
# next to this script, so the skill is self-contained. The review output is
# written to ./.review/ (gitignored) in the working directory.
#
# An optional one-line focus note (second arg) tells codex what to prioritise —
# a specific ask ("check the RQ2 fixes hold and that RQ1 calibration matches the
# prereg") yields a sharper review than letting it roam. The note is a priority
# hint only: it is injected AFTER the anti-fabrication grounding rules and never
# narrows the target's scope or relaxes the verbatim-quote requirement.
#
# Usage: codex-peer-review.sh <file-or-dir-to-review> ["one-line focus note"]

set -euo pipefail

MODEL="gpt-5.5"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUBRIC="$SCRIPT_DIR/review-method.md"       # bundled copy of critical-peer-review.md
PROMPT_FILE="$SCRIPT_DIR/peer-review-smoke-prompt.md"

target="${1:?usage: codex-peer-review.sh <file-or-dir-to-review> [\"one-line focus note\"]}"
focus="${2:-}"
[ -e "$target" ]      || { echo "target not found: $target"      >&2; exit 1; }
[ -f "$RUBRIC" ]      || { echo "rubric not found: $RUBRIC"      >&2; exit 1; }
[ -f "$PROMPT_FILE" ] || { echo "prompt not found: $PROMPT_FILE" >&2; exit 1; }

target_abs="$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"

# Throwaway staging codex reads from (-C points here); not persisted.
work="$(mktemp -d /tmp/codex-review.XXXXXX)"
ctx="$work/context"
mkdir -p "$ctx"
cp "$RUBRIC" "$work/REVIEW-METHOD.md"

# Stage the surrounding repo, minus gitignored files, so the review has
# cross-reference context without raw data / secrets. Not in a git repo: fall
# back to the file alone (no repo means no .gitignore boundary to trust).
repo="$(git -C "$(dirname "$target_abs")" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$repo" ]; then
  rel="$(realpath --relative-to="$repo" "$target_abs")"
  # tracked + untracked-but-not-ignored, TEXT ONLY (skip binaries like PDFs —
  # they are never useful review context and only bloat the disclosed tree),
  # copied preserving structure.
  git -C "$repo" ls-files --cached --others --exclude-standard -z \
    | { while IFS= read -r -d '' f; do
          if grep -Iq . -- "$repo/$f" 2>/dev/null; then printf '%s\0' "$f"; fi
        done; } \
    | tar --null -C "$repo" -T - -cf - \
    | tar -C "$ctx" -xf -
  # Ensure the chosen target is present even if it is itself gitignored —
  # reviewing it is an explicit choice that overrides the ignore filter.
  mkdir -p "$ctx/$(dirname "$rel")"
  cp "$target_abs" "$ctx/$rel"
  n="$(find "$ctx" -type f | wc -l | tr -d ' ')"
  echo "context:  $n text files staged from $repo (gitignored + binaries skipped)"
else
  rel="$(basename "$target")"
  cp -r "$target_abs" "$ctx/$rel"
  echo "context:  (not a git repo — reviewing the file alone, no surrounding context)"
fi
target_in_ctx="context/$rel"

# The review lands in ./.review/ (gitignored by design) in the working dir, so
# runs persist and coexist. Drop a self-ignoring guard if the dir has none, so
# writing into any repo — including the one under review — never leaks review
# output into version control. Absolute path so codex's -o is unambiguous.
review_dir="$PWD/.review"
mkdir -p "$review_dir"
[ -e "$review_dir/.gitignore" ] || printf '# codex-peer-review output — disposable, may carry content sent to an external model\n*\n!.gitignore\n' > "$review_dir/.gitignore"
out="$review_dir/$(basename "$target").$(date +%Y%m%d-%H%M%S).REVIEW.md"

echo "package:  $work"
echo "rubric:   REVIEW-METHOD.md"
echo "target:   $target_in_ctx"
[ -n "$focus" ] && echo "focus:    $focus"
echo "running codex ($MODEL, read-only)…"
echo

# Prompt = grounding template + optional focus hint + the explicit target path,
# piped on stdin. The focus note comes AFTER the template's grounding rules so it
# reads as a priority, never an override of the anti-fabrication rules.
{ cat "$PROMPT_FILE"
  echo
  if [ -n "$focus" ]; then
    echo "REVIEW FOCUS (the requester's priorities — give these extra attention," \
         "but still review the whole target and obey the grounding rules above;" \
         "focus does not narrow scope or relax the verbatim-quote requirement): $focus"
    echo
  fi
  echo "REVIEW TARGET: $target_in_ctx"; } \
  | codex exec \
      -s read-only \
      --ignore-user-config \
      -m "$MODEL" \
      --ephemeral \
      --skip-git-repo-check \
      -C "$work" \
      -o "$out"

echo
echo "review:   $out"
echo
echo "smoke check — prove it reviewed the real file, not a hallucination:"
echo "  pick a quoted phrase from the review and confirm it exists in the target:"
echo "  grep -nF '<quoted phrase>' '$target'"
