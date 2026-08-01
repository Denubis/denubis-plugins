---
name: dreaming
description: Use when auditing per-project auto-memory against the historical record of Claude Code conversations — produces a reviewable proposed-change tree without touching live memory.
user-invocable: true
last-reviewed: 2026-05-18
---

# denubis-dream

**Announce at start:** "I'm using the denubis-dream:dreaming skill."

## Helper resolution

Before running any Bash block below, locate `_lib.sh` (co-located with this skill). The Claude Code session has direct knowledge of this skill's plugin path — use that to construct the absolute path to `_lib.sh` and substitute it into every subsequent `source ...` line.

Worked path examples:
- Local dev: `<repo-root>/plugins/denubis-dream/skills/dreaming/_lib.sh`
- Installed: `~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-dream/skills/dreaming/_lib.sh`

The Bash blocks below all begin with `source "$DREAM_LIB"`. Substitute `$DREAM_LIB` with the resolved absolute path when you assemble each Bash tool call. (`$DREAM_LIB` is a clearly-flagged template placeholder in this skill text — it is NOT an environment variable that survives across blocks.)

## Bash-block convention

Every Bash block in this skill is **self-contained**: each Bash tool call runs in a fresh shell, so variables defined in one block do NOT persist into subsequent blocks. To avoid re-deriving values like `MAIN_SLUG` and `DATED_DIR` in every block, this skill ships `_lib.sh` co-located in the skill directory. Each Bash block begins with `source "$DREAM_LIB"` and then calls the relevant helper function (`dream_main_slug`, `dream_main_dir`, `dream_dated_dir`, `dream_discovered_slugs`, etc.).

See `## Helper resolution` (above) for how to resolve `$DREAM_LIB` to the absolute path at runtime.

If you find yourself wanting to "clean up" a `source "$DREAM_LIB"` line because the previous block already sourced it — don't. Each block is a separate tool call and the source must happen in every block that uses a helper.

## Mode detection

Inspect the invocation prompt for the literal token `--autonomous`. Two cases:

- **Autonomous mode** (the `--autonomous` token is present, e.g. the user (or the `schedule` skill) invoked `/dream --autonomous`): you do not prompt for user input at any point in the pipeline. After the autonomous-pass tail (MEMORY.md regeneration) you exit cleanly.
- **Manual mode** (no `--autonomous` token): the autonomous pass runs (or is skipped if a dated dir for today already exists), and you continue straight into the reconciliation walk in the same conversation.

If you are uncertain whether the user intended `--autonomous`, default to manual mode and ask for confirmation before proceeding to the walk. Manual mode is recoverable; autonomous mode that mistakenly skips the walk is not.

## Project slug resolution

Resolve the **main project slug** (the slug Claude Code uses for the repo root, not a worktree) by sourcing the helper and calling `dream_main_slug`:

```bash
source "$DREAM_LIB"

MAIN_SLUG=$(dream_main_slug) || exit 0   # AC2.5: clean exit if not in a git repo
MAIN_DIR=$(dream_main_dir)
echo "denubis-dream: main slug = $MAIN_SLUG"
echo "denubis-dream: main dir = $MAIN_DIR"
```

The helper's `dream_main_slug` function (1) runs `git rev-parse --show-toplevel`, (2) strips `/.worktrees/<name>` if present, and (3) applies the Claude Code slug rule (remove leading `/`, prepend `-`, replace `/` with `-`). It returns non-zero and prints to stderr if the cwd is outside a git repo — the `|| exit 0` above honours AC2.5 (clean exit, no dated dir created).

**Worked example.**
- `pwd` = `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/plugins/foo`
- `git rev-parse --show-toplevel` → `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream`
- After `.worktrees/<name>` strip → `/home/brian/people/Brian/brian-ed3d-plugins`
- After slug transformation → `-home-brian-people-Brian-brian-ed3d-plugins`

**Failure mode (AC2.5).** If `git rev-parse --show-toplevel` returns empty (the user is outside any git repo), the skill prints a single-line message and exits with status 0 — no dated dir is created.

**Edge cases.**
- User has a non-`.worktrees/` worktree (e.g., `~/wt/foo`). The strip is a no-op; the slug derives from the worktree path itself. This means the main slug will differ from the actual main repo's slug — `/dream` will operate against this worktree's slug. This is acceptable behaviour: the design's worktree-derived discovery is scoped to repos that use the `.worktrees/` convention.
- User is in the main repo (no worktree). The strip is a no-op; the slug derives from the repo root directly.

## Discovery

Scan `~/.claude/projects/` for slugs matching the anchored pattern. Both the main slug and any worktree-derived slugs (including those whose worktrees have been pruned but whose transcript dirs survive) qualify.

```bash
source "$DREAM_LIB"

DISCOVERED_SLUGS=$(dream_discovered_slugs)

if [ -z "$DISCOVERED_SLUGS" ]; then
  echo "denubis-dream: no transcript dirs discovered for slug $(dream_main_slug) — first session?" >&2
  # This is not fatal; the autonomous pass can still proceed with no transcripts.
fi

echo "denubis-dream: discovered slugs:"
printf '%s\n' "$DISCOVERED_SLUGS"
```

`dream_discovered_slugs` applies the anchored regex `^<main>$|^<main>--worktrees-.+$` against `~/.claude/projects/` listings, so both the main slug and any worktree-derived slugs (including pruned-worktree leftovers, AC2.4) qualify.

**Anchoring is structural, not aesthetic.** Without the leading `^` and trailing `$`, a sibling project whose slug happens to start with the main slug (e.g., `-home-brian-people-Brian-brian-ed3d-plugins-experimental`) would be picked up and its transcripts treated as in-scope for this audit — leaking unrelated session data into Phase 3's evidence retrieval. The codebase-investigator confirmed no such collisions currently exist in this user's `~/.claude/projects/`, but the anchoring is defence-in-depth against future projects.

**Pruned worktrees (AC2.4).** A worktree that has been `git worktree remove`d still leaves its `~/.claude/projects/<main>--worktrees-<name>/` transcript dir behind. The anchored regex picks these up by design — the worktree no longer exists on disk, but its session history is still relevant to the audit.

**Output contract.** Set `DISCOVERED_SLUGS` as a newline-separated list of slug names (not full paths). Subsequent sections derive `~/.claude/projects/<slug>/` paths from each entry when they need to read transcripts.

## No-op detection

Before creating today's dated dir, check whether one already exists for this main slug.

First, compute the path:

```bash
source "$DREAM_LIB"

DATED_DIR=$(dream_dated_dir)
```

If `"$DATED_DIR"` does **not** exist as a directory, fall through to `## Dated dir creation`. The autonomous pass proceeds normally.

If `"$DATED_DIR"` exists, branch on mode (which you determined in `## Mode detection`):

**Autonomous mode + existing dir = no-op (AC9.3).** The cron-driven invocation must not overwrite an in-progress reconciliation. Print the existing path and exit cleanly:

```bash
source "$DREAM_LIB"

if [ -d "$(dream_dated_dir)" ]; then
  echo "denubis-dream: dated dir already exists for today: $(dream_dated_dir) — exiting cleanly (no-op)."
  exit 0   # AC9.3
fi
```

**Manual mode + existing dir = resume.** Re-invoking `/dream` interactively when a dated dir exists is the user's "let me pick up where I left off" gesture. Phase 5 implements the actual walk-resume; Phase 2's stub just prints a placeholder so the integration point is exercised:

```bash
source "$DREAM_LIB"

if [ -d "$(dream_dated_dir)" ]; then
  echo "denubis-dream: existing dated dir found — resuming reconciliation walk."
  echo "denubis-dream: (Phase 2 stub) reconciliation walk lands in Phase 5."
  exit 0
fi
```

Run **only the block matching the mode you detected.** Do not run both.

## Dated dir creation

Create today's dated audit directory under the main slug's transcript dir, with both subdirs pre-created so subsequent phases can `Write` into them without race conditions.

```bash
source "$DREAM_LIB"

DATED_DIR=$(dream_dated_dir)
mkdir -p "$DATED_DIR"/flagged "$DATED_DIR"/promoted

echo "denubis-dream: dated dir = $DATED_DIR"
```

**`flagged/` is always created** even when the corpus-wide subagent (Phase 3) finds no memory-worthy regions to flag. Its emptiness at walk time is a valid state.

**`promoted/` is always created** even when no flagged region is promoted during reconciliation. Same reasoning.

**ISO date format (`%Y-%m-%d`).** The date is a substring of the directory name and must sort lexically — `2026-05-17` sorts correctly between `2026-05-16` and `2026-05-18`. No timezone is included; the date is taken in the system's local timezone at the moment the autonomous pass starts.

**One dated dir per day.** Re-invoking `/dream` on the same day reuses today's dir (see `## No-op detection`).

## Pre-windowing transcripts

Phase 3's subagents read from filtered streams, not raw transcripts. Native JSONL lines are NOT monotonic by timestamp, and substantive prose is mixed in with `tool_use` / `tool_result` / `thinking` blocks that carry work-product (file contents, command outputs, internal reasoning) rather than memory-worthy signal. One central `jq` filter applied at the Bash layer extracts ONLY conversational text — the `text` blocks in array-form `.message.content` plus the raw string for string-form `.message.content` (assistant text-only responses) — into a single per-line `text` field, producing a stable `{ts, uuid, role, text}` shape; subagent prompts then assume that shape and stay terse.

```bash
source "$DREAM_LIB"
DATED_DIR=$(dream_dated_dir)
MAIN_DIR=$(dream_main_dir)
DISCOVERED_SLUGS=$(dream_discovered_slugs)

mkdir -p "$DATED_DIR"/.windowed

# Helper: emit windowed JSONL from a set of transcript files,
# filtered by timestamp >= $1 (or unbounded if $1 is empty).
#
# The extract_text jq function below pulls ONLY conversational text — the
# `text` blocks in array-form .message.content, plus the raw string when
# .message.content itself is a string (assistant text-only responses).
# tool_use, tool_result, thinking, and image blocks are dropped. They carry
# work-product (file contents, command output, internal reasoning) that
# bloats the substrate at project scale (a Read tool_result embeds a full
# file; a Write tool_use embeds the full file being written) without
# contributing memory-worthy signal. Memory-worthy claims live in user
# prompts and assistant prose. If a subagent needs to verify a claim
# against actual code or file content, the per-memory subagent prompt's
# `## Code-artefact flags` rules instruct it to grep the live repo
# directly — that's the "dig in on demand" path, not pre-staged bulk.
window_jsonl() {
  local since="$1"; shift
  local files=("$@")
  for jsonl in "${files[@]}"; do
    jq -c --arg ts "$since" '
      def extract_text:
        if .message == null then ""
        elif (.message.content | type) == "string" then .message.content
        elif (.message.content | type) == "array" then
          [ .message.content[] |
            ( if .type == "text" then (.text // "")
              else "" end )
          ] | map(select(. != null and . != "")) | join("\n")
        else "" end;
      select(.timestamp != null) |
      select($ts == "" or .timestamp >= $ts) |
      {ts: .timestamp,
       uuid: .uuid,
       role: (.type // .role // "unknown"),
       text: extract_text}
      | select(.text != "")
    ' "$jsonl"
  done
}

# Build the all-slugs transcript file list (main + worktrees, per Phase 2 discovery)
ALL_JSONL=()
for slug in $DISCOVERED_SLUGS; do
  while IFS= read -r f; do
    ALL_JSONL+=("$f")
  done < <(find ~/.claude/projects/"$slug"/ -maxdepth 1 -name '*.jsonl' 2>/dev/null)
done

# Per-memory windows (AC3.4)
for memfile in "$MAIN_DIR"/memory/*.md; do
  name=$(basename "$memfile" .md)
  [ "$name" = "MEMORY" ] && continue   # index, not a memory

  # Extract lastAudited from frontmatter; empty string if absent.
  # Frontmatter is flat (no metadata: nesting). Field name: lastAudited.
  lastaudited=$(awk '
    /^---$/{f++; next}
    f==1 && /^lastAudited:/{
      sub(/^lastAudited:[[:space:]]*/, "")
      gsub(/["'\''[:space:]]/, "")
      print
      exit
    }
    f>=2{exit}
  ' "$memfile")

  window_jsonl "$lastaudited" "${ALL_JSONL[@]}" > "$DATED_DIR"/.windowed/"$name".jsonl
done

# Corpus-wide window (AC3.8) — bounded by .last-dream timestamp
LASTDREAM_FILE="$MAIN_DIR"/.last-dream
if [ -f "$LASTDREAM_FILE" ]; then
  LASTDREAM_TS=$(tr -d '[:space:]' < "$LASTDREAM_FILE")
else
  LASTDREAM_TS=""   # first dream — unbounded
fi
window_jsonl "$LASTDREAM_TS" "${ALL_JSONL[@]}" > "$DATED_DIR"/.windowed/_corpus.jsonl

# Capture the actual scan-window metadata for the corpus subagent's ## Coverage header.
# The bounding timestamp is what we passed to jq; the actual line-count is what survived.
COVERAGE_BOUND="${LASTDREAM_TS:-<unbounded — first dream>}"
COVERAGE_LINES=$(wc -l < "$DATED_DIR"/.windowed/_corpus.jsonl | tr -d ' ')
echo "denubis-dream: corpus window: since=$COVERAGE_BOUND lines=$COVERAGE_LINES"
```

**Why pre-window.** Without pre-windowing, every subagent independently parses raw JSONL (variable shape, large files) — wastes context tokens and introduces per-subagent variance in what gets read. Centralising the filter is also the right place to absorb future Claude Code transcript-format changes (one filter to update, not N subagent prompts).

**Why text-only.** A "comprehensive" extractor that pulls every block type produces a substrate dominated by file-content echoes. Concretely on this project (104 transcript files at the dream's first invocation, no `lastAudited` set yet so per-memory windows are unbounded scans): the comprehensive filter emitted a 27 MB per-memory file with average 1,186 bytes per line; the top-5 largest lines were 60-72 KB `Read` tool_results carrying full skill/design-document contents. Those bytes have no relationship to a memory's claim — they're just file contents that flowed through the transcript. Memory-worthy claims live in user prompts and assistant prose responses (the `text` blocks). When a per-memory subagent needs to verify a claim against actual code or file content, the `## Per-memory subagent prompt` instructs it to grep the live repo directly — the "dig in on demand" path is intentional, not an oversight to be papered over by pre-staging.

**`lastAudited` is flat.** Existing memory frontmatter uses flat fields (`name`, `description`, `type`, `originSessionId`). The `lastAudited` field this audit introduces (written by Phase 6 finalisation) is also flat — the awk extractor above reads `lastAudited:` at the top level, not `metadata.lastAudited`.

**MEMORY.md is the index.** Skip it; it has no body to audit.

## Per-memory evidence retrieval

For each `memory/*.md` (excluding `MEMORY.md`), dispatch one Sonnet subagent in parallel. The subagent reads the memory body and its pre-windowed transcript stream, then writes `<dated_dir>/<name>.audit.md` with `## Evidence` and `## Code-artefact flags` sections.

**Resumable (AC3.7).** Before dispatching, check whether `<dated_dir>/<name>.audit.md` already exists and already has a populated `## Evidence` section (the marker for a successful prior retrieval). If yes, skip — re-invocation of `/dream` after a crash mid-Phase 3 picks up where it left off without redoing successful work.

**Parallel dispatch.** Issue all subagent calls in a single message (the Claude Code Task tool runs them concurrently when invoked together). Subagents have no inter-dependencies — each writes to its own `<name>.audit.md` path.

**Subagent type.** Always `denubis-basic-agents:sonnet-general-purpose`. The design's `model: claude-sonnet-4-6` reads as a model-tier indication, not a parameter override syntax; the canonical surface in this repo is the agent-tier subagent_type. (See Phase 3 codebase-verification findings.)

**Per-memory dispatch shape:**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Per-memory evidence retrieval: <name></parameter>
<parameter name="prompt">
{see ## Per-memory subagent prompt below — substitute MEMORY_PATH, WINDOWED_PATH, AUDIT_PATH, REPO_ROOT}
</parameter>
</invoke>
```

After all dispatches return, walk `<dated_dir>/*.audit.md` and detect failures by absence of `## Evidence` — handle via `## SKIPPED.md handling` (Task 6).

## Per-memory subagent prompt

The orchestrator substitutes `<MEMORY_PATH>`, `<WINDOWED_PATH>`, `<AUDIT_PATH>`, and `<REPO_ROOT>` into the following template before dispatching:

> You are auditing a single auto-memory file. You will produce one `.audit.md` file with two sections: `## Evidence` (relevant transcript excerpts) and `## Code-artefact flags` (grep hits/misses for code mentioned in the memory body).
>
> **Inputs:**
> - **Memory file:** `<MEMORY_PATH>` — read with the `Read` tool. The frontmatter (between `---` markers) is metadata; the body is the claim/insight you're checking.
> - **Windowed transcript stream:** `<WINDOWED_PATH>` — a JSONL file. Each line is `{ts, uuid, role, text}`. Lines are pre-filtered to timestamps ≥ this memory's `lastAudited` (or the full corpus if `lastAudited` was absent).
>   - On a first dream (or after a long gap) this stream can be **5,000+ lines / 5+ MB** — larger than the `Read` tool's default page. Filter server-side with `Bash` (`jq`/`grep`) first; use `Read` only to fetch full context for specific candidate lines you have already identified.
>   - Starter shapes: `head -1 <WINDOWED_PATH> | jq .` (inspect line structure); `jq -c 'select(.text | test("<term>"; "i"))' <WINDOWED_PATH> | head -30` (pick terms from the memory body and iterate).
> - **Repo root:** `<REPO_ROOT>` — the absolute path of the live worktree. Use for `Bash grep` against live code.
>
> **Output path:** `<AUDIT_PATH>` — write with the `Write` tool. The file's body must be:
>
> ```markdown
> # Audit: <memory name>
>
> ## Evidence
>
> ev-001: <uuid-short> [ts] <role>: <one-line excerpt grounded in the body's claim>
> ev-002: ...
>
> ## Code-artefact flags
>
> - `<artefact>` — hit at `<repo-relative path>:<line>` (matches body's claim)
> - `<artefact>` — miss (verify or edit)
> ```
>
> **Evidence rules.**
> - Surface up to 5 strongest excerpts as `ev-NNN:` lines (more if genuinely useful). One line per excerpt; include the short UUID (first 8 chars of the line's `uuid` field), the `ts`, the `role`, and a one-line text snippet (truncate at ~120 chars).
> - "Strongest" = the excerpt most directly supports or contradicts the memory's claim. Excerpts that merely mention related terms without speaking to the claim aren't evidence — they're noise.
> - If the windowed stream has no relevant excerpts, write `## Evidence\n\n(no transcript evidence in window since lastAudited)\n` — an empty section is a finding (the memory may have gone stale).
>
> **Code-artefact rules.**
> - Scan the memory body for things that look like code artefacts: relative or absolute file paths (`scripts/foo.py`, `src/auth.py`), function/method names in identifier shape (`compute_X`, `MyClass`, `parse_foo`), schema constants in ALL_CAPS, flag/env-var names, slash-command names.
> - Skip prose nouns ("authentication", "parser") — only flag terms that look like they'd appear verbatim in source code.
> - For each candidate, run `Bash` with: `cd <REPO_ROOT> && grep -rn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=__pycache__ -F '<artefact>' . | head -5`
> - Report **hits** as `- \`<artefact>\` — hit at <relative path>:<line>` (one line per first-5 hit; "(more occurrences hidden)" if grep output is non-empty after head -5).
> - Report **misses** as `- \`<artefact>\` — miss (verify or edit)`.
> - If the memory body contains no code-artefact candidates, write `## Code-artefact flags\n\n(no code artefacts mentioned in body)\n`.
>
> **Do not** add `## Changes` or `## Disposition` sections — those land in Phase 4 Opus judgement.
> **Do not** write to live `memory/` — only to `<AUDIT_PATH>`.

**Prompt notes (for the implementer).**
- The orchestrator generates `<AUDIT_PATH>` as `<DATED_DIR>/<name>.audit.md` (using `name` = basename of `<MEMORY_PATH>` with `.md` stripped).
- The orchestrator generates `<WINDOWED_PATH>` as `<DATED_DIR>/.windowed/<name>.jsonl`.
- The subagent's `Bash` tool is invoked from within the subagent — the `cd <REPO_ROOT>` is required because subagents inherit the orchestrator's working directory unreliably.

## Flagged-region scanner

Dispatch ONE Sonnet subagent over the corpus-wide windowed stream (`<dated_dir>/.windowed/_corpus.jsonl`) to identify memory-worthy regions that don't match any existing memory. The subagent receives:

- The corpus windowed-JSONL path.
- The list of existing memory `name + description` pairs (the "discovery surface" — full bodies aren't needed; the subagent only needs to judge "is this region covered by some memory by name/description").
- The dated-dir `flagged/` path for output.
- The `## Coverage` header substrate (the bounding timestamp, the corpus line count).

**Resumable detection.** If `<dated_dir>/flagged/` already contains `region-*.flagged.md` files, the scanner has run previously this dream — skip dispatch. (This is the simplest resume strategy; a partial scan that wrote some files before crashing won't be redone, but the cost of duplicate scanning is high enough that this is the right trade-off.)

**Memory-description bundle.** Construct in Bash:

```bash
source "$DREAM_LIB"
MAIN_DIR=$(dream_main_dir)

MEMORY_DIGEST=$(mktemp)
for m in "$MAIN_DIR"/memory/*.md; do
  name=$(basename "$m" .md)
  [ "$name" = "MEMORY" ] && continue
  desc=$(awk '/^---$/{f++;next} f==1 && /^description:/{sub(/^description:[[:space:]]*/,""); print; exit}' "$m")
  printf '%s :: %s\n' "$name" "$desc" >> "$MEMORY_DIGEST"
done
```

**Dispatch:**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Corpus-wide flagged-region scan</parameter>
<parameter name="prompt">
{see ## Flagged-region subagent prompt — substitute CORPUS_PATH, MEMORY_DIGEST_PATH, FLAGGED_DIR, COVERAGE_BOUND, COVERAGE_LINES}
</parameter>
</invoke>
```

## Flagged-region subagent prompt

The orchestrator substitutes `<CORPUS_PATH>`, `<MEMORY_DIGEST_PATH>`, `<FLAGGED_DIR>`, `<COVERAGE_BOUND>`, and `<COVERAGE_LINES>` before dispatching:

> You are scanning a windowed corpus of Claude Code transcript text for memory-worthy regions that no existing memory covers.
>
> **Inputs:**
> - **Corpus stream:** `<CORPUS_PATH>` — JSONL, lines of `{ts, uuid, role, text}`. Pre-filtered to timestamps ≥ the last dream's finalisation timestamp (or unbounded if this is the first dream).
>   - On a first dream this stream can be **5,000+ lines / 5+ MB** — larger than the `Read` tool's default page. Filter server-side with `Bash` (`jq`/`grep`) first; use `Read` only for small samples or to fetch full context for specific candidate lines.
>   - Starter shapes: `head -1 <CORPUS_PATH> | jq .` (inspect line structure); `jq -c 'select(.role == "user") | .text' <CORPUS_PATH> | head -30` (sample user prompts); `jq -c 'select(.role == "assistant") | .text' <CORPUS_PATH> | head -30` (assistant prose); `grep -i -E 'we decided|user (explicitly|prefers)|stop doing|never|always' <CORPUS_PATH> | head -50` (memory-worthy signals). Iterate.
> - **Existing memory digest:** `<MEMORY_DIGEST_PATH>` — one line per memory: `<name> :: <description>`. Read with the `Read` tool. Use this to judge "is this region already covered by some memory?".
> - **Output directory:** `<FLAGGED_DIR>` — write one file per surfaced region.
>
> **Coverage metadata (for the `## Coverage` header in every output file):**
> - **Bounding timestamp:** `<COVERAGE_BOUND>` — the `.last-dream` timestamp this scan starts after. The literal string `<unbounded — first dream>` if `.last-dream` was absent.
> - **Corpus line count:** `<COVERAGE_LINES>` — total number of text-bearing lines you scanned.
>
> **What counts as a "memory-worthy region":**
> - A claim, preference, decision, fact, or pattern that a future Claude session in this project would benefit from knowing — and that no existing memory already captures.
> - Examples: "user explicitly preferred approach X for reason Y", "we discovered library Z behaves oddly when condition W", "the user's understanding of pattern P was corrected to P'".
> - NOT memory-worthy: routine debugging exchanges, transient task context, mistakes that were corrected and have no lasting implication.
>
> **What counts as "no existing memory covers it":**
> - Compare the candidate region against each line in `<MEMORY_DIGEST_PATH>`. If a memory's description plausibly encompasses the claim/insight, do NOT flag — the existing memory is the right place for it.
> - Borderline cases lean toward flagging (false positives are cheap to dismiss; false negatives are lost insights).
>
> **Output format.** Write one file per surfaced region as `<FLAGGED_DIR>/region-NNN.flagged.md` (NNN is a 3-digit zero-padded sequential counter starting at 001). File body:
>
> ```markdown
> # Flagged region NNN
>
> ## Coverage
>
> Scanned <COVERAGE_LINES> text-bearing lines since <COVERAGE_BOUND>.
>
> ## Excerpt
>
> > <one or more transcript excerpts, blockquoted, with [uuid-short ts role] prefix per line>
>
> ## Why memory-worthy
>
> <2-4 sentence rationale: what's the durable claim/preference/decision; why isn't it already covered by some existing memory; what type of memory it would become (user / feedback / project / reference).>
> ```
>
> **Volume guidance.** Aim for 0-10 flagged regions per dream. If you find more than 10 candidates, surface the strongest 10 and note in the final region's `## Why memory-worthy` that further candidates were elided (the user can re-dream after promoting to see new flags surface).
>
> **Do not** write candidate frontmatter or attempt to draft the memory file itself. The Phase 5 reconciliation walk's "promote" workflow drafts scaffolds interactively with the user — see design DR2 (no Sonnet authoring).
> **Do not** write to live `memory/` or anywhere outside `<FLAGGED_DIR>`.
> **Do not** touch existing `.audit.md` files.

**Prompt notes.** The `## Coverage` header in every flagged file is the user's visibility into scan completeness. If `<COVERAGE_BOUND>` is `<unbounded — first dream>` and `<COVERAGE_LINES>` is enormous, the user can judge whether some flags may be missing due to subagent context-window truncation.

## SKIPPED.md handling

After all per-memory subagent dispatches return, walk `<dated_dir>/*.audit.md` and check for failures:

```bash
source "$DREAM_LIB"
DATED_DIR=$(dream_dated_dir)
MAIN_DIR=$(dream_main_dir)

SKIPPED_FILE="$DATED_DIR"/SKIPPED.md
: > "$SKIPPED_FILE"   # truncate at the start of every Phase 3 pass

for memfile in "$MAIN_DIR"/memory/*.md; do
  basefile=$(basename "$memfile")   # e.g. feedback_review-all-levels.md (WITH .md)
  [ "$basefile" = "MEMORY.md" ] && continue
  name="${basefile%.md}"            # e.g. feedback_review-all-levels (without .md)

  auditfile="$DATED_DIR"/"$name".audit.md
  if [ ! -f "$auditfile" ] || ! grep -q '^## Evidence$' "$auditfile"; then
    # IMPORTANT — strict format: "- <basefile>" with the .md extension and NOTHING else on the
    # line. The decisions.log identifier convention requires identifiers with .md (Phase 5 Task 6
    # field table); SKIPPED.md must be parseable into that identifier cleanly. Annotations belong
    # in a separate SKIPPED-notes.md file if anyone wants them — do not annotate inline.
    echo "- $basefile" >> "$SKIPPED_FILE"
  fi
done

if [ -s "$SKIPPED_FILE" ]; then
  echo "denubis-dream: Phase 3 SKIPPED the following memories (see $SKIPPED_FILE):"
  cat "$SKIPPED_FILE"
else
  rm -f "$SKIPPED_FILE"   # keep dated dir clean when nothing was skipped
fi
```

**Failure-mode propagation (AC3.6).** Phase 4 (Opus judgement) reads `SKIPPED.md` at the start of its pass and skips judgement for those memories — they get no `## Disposition` and so are presented in the reconciliation walk (Phase 5) as "skipped — no evidence; user must decide manually".

## Resumable retrieval

If `/dream` was invoked, started Phase 3, and crashed (or the user `Ctrl-C`'d) part-way through:

1. **Pre-windowing (Task 1) re-runs unconditionally.** It's cheap (deterministic `jq` over already-computed file lists) and any windowed-file change since the last invocation (a new transcript landed, a memory's `lastAudited` changed) should be reflected.

2. **Per-memory dispatch (Task 2) skips memories with a populated `.audit.md`.** The pre-dispatch check uses the same predicate as Task 6's post-dispatch SKIPPED.md detector (file exists AND `^## Evidence$` present). A partial write — file present but no `## Evidence` header — is treated as a failed retrieval and re-dispatched; if the second attempt also fails to populate the header, Task 6 catches it.

3. **Corpus-wide scan (Task 4) skips if `<dated_dir>/flagged/` is non-empty.** A partial flagged-region scan that wrote files before failing won't be re-run — re-running is expensive and the user can prune duplicates during the walk.

4. **SKIPPED.md (Task 6) is regenerated** each pass — it's truncated at the start, then re-populated based on the current state of `.audit.md` files.

The net result: re-invoking `/dream` mid-Phase 3 is safe and idempotent. Successful work persists; failed work is retried; the user pays only for what's missing.

## Pipeline status (Phase 3)

Autonomous-pass retrieval is in place: per-memory evidence (with code-artefact flags) and corpus-wide flagged regions populate the dated dir. Judgement (Phase 4), reconciliation walk (Phase 5), and finalisation (Phase 6) land in subsequent phases.

When invoked at this stage, the skill executes the autonomous pass through retrieval and prints:

> denubis-dream: retrieval complete (N memories audited, M flagged regions surfaced, K skipped). Judgement not yet implemented. Dated dir at <path>.

…and exits.

## Reference

- Design plan: `docs/design-plans/2026-05-16-denubis-dream.md`
- Implementation plan: `docs/implementation-plans/2026-05-16-denubis-dream/`
