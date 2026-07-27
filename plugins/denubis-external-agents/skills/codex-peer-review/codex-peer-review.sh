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
#        [--include <path>]...

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUBRIC="$SCRIPT_DIR/review-method.md"       # bundled copy of critical-peer-review.md
PROMPT_FILE="$SCRIPT_DIR/peer-review-smoke-prompt.md"

usage='usage: codex-peer-review.sh <file-or-dir-to-review> ["one-line focus note"] [--include <path>]... [--include-confirmed]'
target="${1:?$usage}"
shift
focus=""
focus_set=0
includes=()
include_confirmed=0
# Unrecognised arguments are fatal. A tolerant parser that took the first bare
# token as the focus note and dropped the rest turned `--includ evidence.md`
# into a focus note reading "--includ" and silently discarded the evidence, so
# the operator believed a file had been sent that never was. For a flag whose
# whole justification is that naming a path is a deliberate decision, silently
# ignoring a named path is the opposite of the intent.
while [ "$#" -gt 0 ]; do
  case "$1" in
    --include)
      [ "$#" -ge 2 ] || { echo "include path required after --include" >&2; exit 1; }
      includes+=("$2")
      shift 2
      ;;
    --include-confirmed)
      include_confirmed=1
      shift
      ;;
    --*)
      echo "unrecognised option: $1" >&2
      echo "$usage" >&2
      exit 1
      ;;
    *)
      [ "$focus_set" -eq 0 ] || {
        echo "unexpected argument: $1" >&2
        echo "$usage" >&2
        exit 1
      }
      focus="$1"
      focus_set=1
      shift
      ;;
  esac
done
[ -e "$target" ]      || { echo "target not found: $target"      >&2; exit 1; }
for include in "${includes[@]}"; do
  [ -e "$include" ] || { echo "include not found: $include" >&2; exit 1; }
done
[ -f "$RUBRIC" ]      || { echo "rubric not found: $RUBRIC"      >&2; exit 1; }
[ -f "$PROMPT_FILE" ] || { echo "prompt not found: $PROMPT_FILE" >&2; exit 1; }

target_abs="$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"

# Model: track whatever the operator has codex set to, never pin a version here.
# `--ignore-user-config` (below) keeps the reviewer clear of their MCP servers,
# hooks and custom instructions, so the model is read out of config.toml
# explicitly and passed back in — the one setting allowed through the isolation.
# Only the top-level key counts; parsing stops at the first [section] header so a
# profile's model is never mistaken for the default. No key, no -m: codex then
# picks its own default, which is the right answer when the operator has not
# expressed one.
codex_home="${CODEX_HOME:-$HOME/.codex}"
MODEL="$(awk '
  /^[[:space:]]*\[/ { exit }
  /^[[:space:]]*model[[:space:]]*=/ {
      line = $0
      sub(/^[^=]*=[[:space:]]*/, "", line)
      sub(/[[:space:]]*$/, "", line)
      gsub(/^"|"$/, "", line)
      print line
      exit
  }
' "$codex_home/config.toml" 2>/dev/null || true)"

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
  # A directory is bulk inclusion, so its contents retain the text-only filter.
  # A single named file remains an explicit choice and may be binary.
  if [ -d "$target_abs" ]; then
    mkdir -p "$ctx/$rel"
    find "$target_abs" -type f -print0 \
      | { while IFS= read -r -d '' f; do
            if grep -Iq . -- "$f" 2>/dev/null; then
              printf '%s\0' "${f#"$target_abs"/}"
            fi
          done; } \
      | tar --null -C "$target_abs" -T - -cf - \
      | tar -C "$ctx/$rel" -xf -
  else
    mkdir -p "$ctx/$(dirname "$rel")"
    cp "$target_abs" "$ctx/$rel"
  fi
  n="$(find "$ctx" -type f | wc -l | tr -d ' ')"
  echo "context:  $n text files staged from $repo (gitignored + binaries skipped)"
else
  rel="$(basename "$target")"
  cp -r "$target_abs" "$ctx/$rel"
  echo "context:  (not a git repo — reviewing the file alone, no surrounding context)"
fi
target_in_ctx="context/$rel"

# Explicit evidence is separate from the normal context tree so it cannot
# overwrite staged repository content. Ordinals also keep same-named includes
# distinct and give the reviewer short, stable paths to cite.
include_index=0
include_sources=()
include_destinations=()
for include in "${includes[@]}"; do
  include_index=$((include_index + 1))
  printf -v include_ordinal '%03d' "$include_index"
  include_abs="$(cd "$(dirname "$include")" && pwd)/$(basename "$include")"
  include_in_work="included/$include_ordinal/$(basename "$include_abs")"
  include_sources+=("$include_abs")
  include_destinations+=("$include_in_work")
  if [ -d "$include_abs" ]; then
    mkdir -p "$work/$include_in_work"
    find "$include_abs" -type f -print0 \
      | { while IFS= read -r -d '' f; do
            if grep -Iq . -- "$f" 2>/dev/null; then
              printf '%s\0' "${f#"$include_abs"/}"
            fi
          done; } \
      | tar --null -C "$include_abs" -T - -cf - \
      | tar -C "$work/$include_in_work" -xf -
  else
    mkdir -p "$work/$(dirname "$include_in_work")"
    cp "$include_abs" "$work/$include_in_work"
  fi
done

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
# Enumerate what each include actually stages, not merely the name given. A
# directory include discloses its whole text tree, and one printed line per
# --include argument made a four-thousand-file include indistinguishable on
# stdout from a three-file one. A name is a decision about a name; the manifest
# is the disclosure.
include_file_total=0
for include_index in "${!include_sources[@]}"; do
  echo "include:  ${include_sources[$include_index]} -> ${include_destinations[$include_index]}"
  while IFS= read -r staged_file; do
    echo "          $staged_file"
    include_file_total=$((include_file_total + 1))
  done < <(cd "$work" && find "${include_destinations[$include_index]}" -type f | sort)
done
[ "${#include_sources[@]}" -eq 0 ] \
  || echo "include:  $include_file_total file(s) staged outside the repository boundary"
[ -n "$focus" ] && echo "focus:    $focus"
# Printed so the reviewer can be attributed to the model that actually ran;
# the skill's presentation step labels the review with this value.
if [ -n "$MODEL" ]; then
  echo "model:    $MODEL"
  echo "source:   your codex default ($codex_home/config.toml)"
else
  echo "model:    codex default (no top-level model key in $codex_home/config.toml)"
fi
# Disclosure gate. Everything above this line is local: staging writes into a
# throwaway /tmp package and nothing has left the machine. `codex exec` below is
# the transmission, so the decision belongs here, while it can still be refused.
#
# The default staging excludes gitignored files precisely because they hold raw
# data and secrets; --include force-stages past that boundary from anywhere on
# the filesystem. Printing the manifest afterwards records the disclosure rather
# than authorising it, and the usual reader of that receipt is a model composing
# the command line rather than the operator whose files are being sent.
if [ "${#include_sources[@]}" -gt 0 ] && [ "$include_confirmed" -ne 1 ]; then
  echo
  echo "$include_file_total file(s) above sit outside the staged repository and will"
  echo "be transmitted to an external model. Nothing has been sent yet."
  if [ -t 0 ]; then
    printf 'Send them? [y/N] '
    read -r reply || reply=""
    case "$reply" in
      y | Y | yes | YES) ;;
      *) echo "aborted — nothing was sent" >&2; exit 3 ;;
    esac
  else
    echo "no terminal to confirm on. Re-run with --include-confirmed to proceed;" >&2
    echo "that flag is the non-interactive disclosure decision and it is recorded" >&2
    echo "in the command line that carried it." >&2
    exit 3
  fi
fi

echo "running codex (read-only)…"
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
  for include_in_work in "${include_destinations[@]}"; do
    echo "INCLUDED EVIDENCE: $include_in_work"
  done
  [ "${#include_destinations[@]}" -eq 0 ] || echo
  echo "REVIEW TARGET: $target_in_ctx"; } \
  | codex exec \
      -s read-only \
      --ignore-user-config \
      ${MODEL:+-m "$MODEL"} \
      --ephemeral \
      --skip-git-repo-check \
      -C "$work" \
      -o "$out"

echo
echo "review:   $out"
echo
echo "smoke check — verify 2–3 verbatim quoted phrases (prioritise every High-severity finding):"
echo "  grep each against the file its finding attributes it to (target '$target' or context under '$ctx'):"
echo "  grep -nF '<quoted phrase>' '<attributed file>'"
