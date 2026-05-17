# denubis-dream Implementation Plan — Phase 3: Sonnet retrieval subagents

**Goal:** After Phase 2's autonomous-pass orchestration completes, the dated dir contains: (1) `.windowed/<name>.jsonl` per memory + `.windowed/_corpus.jsonl` for the corpus-wide scan, (2) `<name>.audit.md` with populated `## Evidence` and `## Code-artefact flags` sections for every live memory, and (3) `flagged/region-NNN.flagged.md` files for memory-worthy transcript regions matching no existing memory.

**Architecture:** Two-layer retrieval. Bash-layer `jq` pre-windows transcripts into a stable `{ts, uuid, role, text}` JSONL shape, decoupling the subagents from the messy native transcript format. Each Claude Code transcript line is a JSON object whose `.message.content` may be a string OR an array of block objects (`text`, `thinking`, `tool_use`, `tool_result`, `image`); `tool_result.content` may itself be a string OR a nested array of `{type, text}` blocks. The pre-window filter extracts substantive text from every block type into a single per-line `text` field so subagents read one stable shape. Two flavours of Sonnet subagent then read the windowed substrate: a per-memory evidence retriever (one parallel dispatch per live memory) and a single corpus-wide flagged-region scanner. Both use `denubis-basic-agents:sonnet-general-purpose` — the repo's canonical Sonnet-tier dispatch.

**Tech Stack:** Bash (`jq`, `find`, `grep`), Claude Code `Task` tool dispatching `denubis-basic-agents:sonnet-general-purpose`, skill text.

**Scope:** Phase 3 of 7.

**Codebase verified:** 2026-05-17 (codebase-investigator confirmed: no precedent for raw `model: <id>` overrides — all denubis dispatches use `subagent_type`; JSONL transcript lines are NOT chronologically ordered, so windowing must filter; substantive text is distributed across multiple block types per message — verified by direct profile against `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d28fd3f2-dc3e-41fd-9e62-75bf79264cce.jsonl`: 960 total lines / 785 timestamped / 475 text-bearing lines using the comprehensive extractor below; memory frontmatter is flat with no existing `lastAudited` — Phase 6 will introduce it).

**Phase Type:** functionality

**Cascading correction reapplied:** memory frontmatter is flat — `lastAudited` reads (Tasks 1, 7) and writes (Phase 6) are top-level, not `metadata.lastAudited`. Rationale: the user's global CLAUDE.md convention uses flat frontmatter; existing memory files have no `lastAudited` field at all (flat or nested) — this plugin invents it at first finalisation. See phase_02.md header for the canonical statement.

---

## Acceptance Criteria Coverage

This phase implements and verifies:

### denubis-dream.AC3: Evidence retrieval (Sonnet subagents)
- **denubis-dream.AC3.1 Success:** One per-memory evidence subagent (`subagent_type: denubis-basic-agents:sonnet-general-purpose`) dispatched per live memory file.
- **denubis-dream.AC3.2 Success:** Each `<name>.audit.md` contains a populated `## Evidence` section with `ev-NNN:` entries citing transcript short-UUIDs and line ranges.
- **denubis-dream.AC3.3 Success:** Each `<name>.audit.md` contains a populated `## Code-artefact flags` section showing both hits (with `path:line`) and misses (with "verify or edit") for code-artefact mentions in the memory body.
- **denubis-dream.AC3.4 Success:** Per-memory subagent windows transcripts from the memory's `frontmatter.lastAudited` onward (full corpus if absent).
- **denubis-dream.AC3.5 Success:** Flagged-region subagent writes `flagged/region-NNN.flagged.md` files for memory-worthy transcript regions matching no existing memory. Each file includes a `## Coverage` header line stating the transcript-time range scanned and the bounding `.last-dream` timestamp.
- **denubis-dream.AC3.6 Failure:** Per-memory subagent failure: memory name appears in `memory.dream-DATE/SKIPPED.md`; no `## Disposition` is added to that memory in the judgement phase.
- **denubis-dream.AC3.7 Success:** Re-invoking `/dream` while some live memories lack a `.audit.md` in today's dated dir re-dispatches per-memory subagents only for the missing ones; already-collected `.audit.md` files are not overwritten.
- **denubis-dream.AC3.8 Success:** Corpus-wide flagged-region subagent reads transcripts with timestamps ≥ the value in `~/.claude/projects/<main-slug>/.last-dream`. If `.last-dream` is absent (first dream), the subagent reads the full corpus and reports the unbounded scan in its `## Coverage` header.

**Design-text correction:** the design's `frontmatter.metadata.lastAudited` is implemented as `frontmatter.lastAudited` (flat) — see header note above.

**Design-text correction:** the design's `model: claude-sonnet-4-6` is implemented as `subagent_type: denubis-basic-agents:sonnet-general-purpose` (matches existing repo precedent; raw model-ID parameter overrides are not the canonical surface).

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: `## Pre-windowing transcripts` section

**Verifies:** AC3.4 (per-memory windowing), AC3.8 (corpus-wide windowing)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after Phase 2's `## Dated dir creation` section.

**Implementation:**

Add a `## Pre-windowing transcripts` section. This step runs once at the start of Phase 3 and writes filtered+extracted JSONL into `<dated_dir>/.windowed/`. Both subagent flavours read from there; the main skill never hands raw `~/.claude/projects/<slug>/*.jsonl` to a subagent.

The section text:

````markdown
## Pre-windowing transcripts

Phase 3's subagents read from filtered streams, not raw transcripts. Native JSONL lines are NOT monotonic by timestamp, and substantive text is distributed across multiple block types within each message's `.content` array (`text`, `thinking`, `tool_use`, `tool_result`) — plus a string-form `.content` on some lines and entirely message-less lines (`attachment`, `queue-operation`, `system`). One central `jq` filter applied at the Bash layer extracts substantive text from every block type into a single per-line `text` field, producing a stable `{ts, uuid, role, text}` shape; subagent prompts then assume that shape and stay terse.

```bash
mkdir -p "$DATED_DIR"/.windowed

# Helper: emit windowed JSONL from a set of transcript files,
# filtered by timestamp >= $1 (or unbounded if $1 is empty).
#
# The extract_text jq function below handles every shape Claude Code transcripts
# emit. Naïve `.message.content[0].text // .text // ""` drops ~95% of lines
# because most lines have an array-form .message.content whose first block is
# tool_use, tool_result, or thinking — NOT text. The extractor walks every
# block, pulls substantive content from each type, joins on newlines, and
# returns "" for non-message-bearing lines (attachment, queue-operation, system)
# so the trailing `select(.text != "")` drops them cleanly without stderr noise.
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
              elif .type == "thinking" then (.thinking // "")
              elif .type == "tool_use" then
                ("[tool_use " + (.name // "?") + "] " + ((.input // {}) | tostring))
              elif .type == "tool_result" then
                ( if (.content | type) == "string" then .content
                  elif (.content | type) == "array" then
                    ([.content[] | (if .type == "text" then (.text // "") else "" end)]
                     | map(select(. != "")) | join("\n"))
                  else "" end)
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

**Why extract every block type.** Most assistant work in Claude Code transcripts lives in `tool_use` and `tool_result` blocks (commands invoked, outputs received); discussion lives in `text` blocks; reasoning lives in `thinking` blocks. A filter that pulls only `.message.content[0].text` drops the majority of substantive content because most messages have a non-text first block. The extractor concatenates substantive text from every block in the array (`tool_use` rendered as a `[tool_use <name>] <input-as-json>` marker line; `tool_result.content` handled for both string and nested-array forms) so subagents see the actual work history, not just the surfaced prose.

**`lastAudited` is flat.** Existing memory frontmatter uses flat fields (`name`, `description`, `type`, `originSessionId`). The `lastAudited` field this audit introduces (written by Phase 6 finalisation) is also flat — the awk extractor above reads `lastAudited:` at the top level, not `metadata.lastAudited`.

**MEMORY.md is the index.** Skip it; it has no body to audit.
````

**Verification (operational):**

After Phase 3 dispatch completes (Task 8 stub), check:
- `<dated_dir>/.windowed/<name>.jsonl` exists for each `memory/*.md` except `MEMORY.md`.
- `<dated_dir>/.windowed/_corpus.jsonl` exists.
- Each windowed file is valid JSONL (`jq -e . <file> > /dev/null`).
- For the first dream (no `.last-dream`), the corpus window contains the union of all discovered transcripts' text-bearing lines.
- **Filter-survivor sanity (smoke test for the comprehensive extractor):** for a typical transcript file, survivor count should be a sizeable fraction of timestamped lines, NOT a tiny fraction. On `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d28fd3f2-dc3e-41fd-9e62-75bf79264cce.jsonl` (the reference file used during plan-validation): 960 total lines / 785 timestamped / **475 survivors** under this filter. A naïve `.message.content[0].text` filter would produce 48 survivors on the same file. If your survivor count is in the 5%-of-timestamped-lines range on a representative transcript, the extractor has regressed to a single-block path — fix before dispatching subagents.
- **No stderr noise.** Run the helper and confirm stderr is empty (`window_jsonl "" "$one_jsonl" 2>/tmp/err >/dev/null; wc -l /tmp/err`). The naïve filter crashes with `Cannot index string with number` on lines whose `.message.content` is a string; this filter handles both shapes silently.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `## Per-memory evidence retrieval` section (orchestrator)

**Verifies:** AC3.1, AC3.7 (resumable detection logic)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Pre-windowing transcripts`.

**Implementation:**

Add a `## Per-memory evidence retrieval` section that dispatches one Sonnet subagent in parallel per live memory file. Resumable: skip memories that already have a populated `.audit.md` in today's dated dir.

The section text:

````markdown
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
````

**Verification (operational):**

After Phase 3 completes (Task 8 stub), check:
- Number of `*.audit.md` files in `<dated_dir>` equals the number of `memory/*.md` files minus 1 (for `MEMORY.md`) minus any entries in `SKIPPED.md`.
- Each `.audit.md` has a non-empty `## Evidence` section, OR its name appears in `SKIPPED.md`.
- Re-invoke `/dream` (don't delete the dated dir); confirm no `.audit.md` is re-written (mtimes unchanged).
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: `## Per-memory subagent prompt` section (prompt text)

**Verifies:** AC3.2, AC3.3

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Per-memory evidence retrieval`.

**Implementation:**

Add a `## Per-memory subagent prompt` section that documents the prompt text the orchestrator (Task 2) substitutes into each dispatch. The subagent uses `Read` and `Bash` only.

The section text:

````markdown
## Per-memory subagent prompt

The orchestrator substitutes `<MEMORY_PATH>`, `<WINDOWED_PATH>`, `<AUDIT_PATH>`, and `<REPO_ROOT>` into the following template before dispatching:

> You are auditing a single auto-memory file. You will produce one `.audit.md` file with two sections: `## Evidence` (relevant transcript excerpts) and `## Code-artefact flags` (grep hits/misses for code mentioned in the memory body).
>
> **Inputs:**
> - **Memory file:** `<MEMORY_PATH>` — read with the `Read` tool. The frontmatter (between `---` markers) is metadata; the body is the claim/insight you're checking.
> - **Windowed transcript stream:** `<WINDOWED_PATH>` — a JSONL file. Each line is `{ts, uuid, role, text}`. Lines are pre-filtered to timestamps ≥ this memory's `lastAudited` (or the full corpus if `lastAudited` was absent). Read with the `Read` tool.
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
````

**Verification (operational):**

After dispatch, open one `.audit.md` and verify:
- `## Evidence` section present, with at least one `ev-NNN:` line or a "(no transcript evidence...)" marker.
- `## Code-artefact flags` section present, with at least one hit/miss line or a "(no code artefacts...)" marker.
- File body uses Markdown only (no JSON dumped from the windowed stream).
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 4-5) -->

<!-- START_TASK_4 -->
### Task 4: `## Flagged-region scanner` section (orchestrator)

**Verifies:** AC3.5, AC3.8

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Per-memory subagent prompt`.

**Implementation:**

Add a `## Flagged-region scanner` section that dispatches a single Sonnet subagent over `_corpus.jsonl` to surface memory-worthy regions not covered by any existing memory.

The section text:

````markdown
## Flagged-region scanner

Dispatch ONE Sonnet subagent over the corpus-wide windowed stream (`<dated_dir>/.windowed/_corpus.jsonl`) to identify memory-worthy regions that don't match any existing memory. The subagent receives:

- The corpus windowed-JSONL path.
- The list of existing memory `name + description` pairs (the "discovery surface" — full bodies aren't needed; the subagent only needs to judge "is this region covered by some memory by name/description").
- The dated-dir `flagged/` path for output.
- The `## Coverage` header substrate (the bounding timestamp, the corpus line count).

**Resumable detection.** If `<dated_dir>/flagged/` already contains `region-*.flagged.md` files, the scanner has run previously this dream — skip dispatch. (This is the simplest resume strategy; a partial scan that wrote some files before crashing won't be redone, but the cost of duplicate scanning is high enough that this is the right trade-off.)

**Memory-description bundle.** Construct in Bash:

```bash
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
````

**Verification (operational):**

After dispatch:
- Either `<dated_dir>/flagged/` contains `region-001.flagged.md` (and so on), each with a `## Coverage` header, OR the directory is empty (a valid finding for a clean corpus).
- Re-invoke `/dream`; confirm the scanner doesn't redispatch if `flagged/` is non-empty.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `## Flagged-region subagent prompt` section (prompt text)

**Verifies:** AC3.5

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Flagged-region scanner`.

**Implementation:**

Add a `## Flagged-region subagent prompt` section.

The section text:

````markdown
## Flagged-region subagent prompt

The orchestrator substitutes `<CORPUS_PATH>`, `<MEMORY_DIGEST_PATH>`, `<FLAGGED_DIR>`, `<COVERAGE_BOUND>`, and `<COVERAGE_LINES>` before dispatching:

> You are scanning a windowed corpus of Claude Code transcript text for memory-worthy regions that no existing memory covers.
>
> **Inputs:**
> - **Corpus stream:** `<CORPUS_PATH>` — JSONL, lines of `{ts, uuid, role, text}`. Pre-filtered to timestamps ≥ the last dream's finalisation timestamp (or unbounded if this is the first dream). Read with the `Read` tool.
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
````

**Verification (operational):**

After dispatch:
- Each `region-*.flagged.md` has a `## Coverage` header, a `## Excerpt` blockquote, and a `## Why memory-worthy` rationale.
- The `## Coverage` line correctly cites `<COVERAGE_BOUND>` and `<COVERAGE_LINES>` (cross-check against the values printed in Task 1 stdout).
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_TASK_6 -->
### Task 6: `## SKIPPED.md handling` section

**Verifies:** AC3.6

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Flagged-region subagent prompt`.

**Implementation:**

Add a `## SKIPPED.md handling` section.

The section text:

````markdown
## SKIPPED.md handling

After all per-memory subagent dispatches return, walk `<dated_dir>/*.audit.md` and check for failures:

```bash
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
````

**Verification (operational):**

Force a subagent failure (e.g., temporarily move one memory's pre-windowed file aside so the subagent has no input). Confirm:
- That memory's `.audit.md` is absent OR lacks `## Evidence`.
- `SKIPPED.md` lists that memory's name.
- No `.audit.md` write happens for the skipped memory in subsequent re-invocations of `/dream` until the failure is resolved.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: `## Resumable retrieval` section

**Verifies:** AC3.7

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## SKIPPED.md handling`.

**Implementation:**

Add a `## Resumable retrieval` section describing the re-invocation behaviour.

The section text:

````markdown
## Resumable retrieval

If `/dream` was invoked, started Phase 3, and crashed (or the user `Ctrl-C`'d) part-way through:

1. **Pre-windowing (Task 1) re-runs unconditionally.** It's cheap (deterministic `jq` over already-computed file lists) and any windowed-file change since the last invocation (a new transcript landed, a memory's `lastAudited` changed) should be reflected.

2. **Per-memory dispatch (Task 2) skips memories with a populated `.audit.md`.** The presence-of-`## Evidence` check in Task 6's loop is reused: if the section exists, the memory was successfully retrieved; don't redispatch.

3. **Corpus-wide scan (Task 4) skips if `<dated_dir>/flagged/` is non-empty.** A partial flagged-region scan that wrote files before failing won't be re-run — re-running is expensive and the user can prune duplicates during the walk.

4. **SKIPPED.md (Task 6) is regenerated** each pass — it's truncated at the start, then re-populated based on the current state of `.audit.md` files.

The net result: re-invoking `/dream` mid-Phase 3 is safe and idempotent. Successful work persists; failed work is retried; the user pays only for what's missing.
````

**Verification (operational):**

After a successful Phase 3 run:
1. Note mtimes of all `*.audit.md` and `flagged/*` files.
2. Re-invoke `/dream`.
3. Confirm mtimes are unchanged (re-dispatch was a no-op for everything successful).

After a forced failure on one memory (per Task 6 verification):
1. Re-invoke `/dream`; confirm ONLY that memory's `.audit.md` is rewritten.
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Replace Phase 2 pipeline stub + commit

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — replace Phase 2's trailing `## Pipeline status (Phase 2)` block.

**Implementation:**

Update the trailing pipeline-status block (added in Phase 2) so it now reflects Phase 3 completion. Replace the Phase 2 stub with:

```markdown
## Pipeline status (Phase 3)

Autonomous-pass retrieval is in place: per-memory evidence (with code-artefact flags) and corpus-wide flagged regions populate the dated dir. Judgement (Phase 4), reconciliation walk (Phase 5), and finalisation (Phase 6) land in subsequent phases.

When invoked at this stage, the skill executes the autonomous pass through retrieval and prints:

> denubis-dream: retrieval complete (N memories audited, M flagged regions surfaced, K skipped). Judgement not yet implemented. Dated dir at <path>.

…and exits.
```

**Single commit for the full Phase 3 set.**

```bash
git add plugins/denubis-dream/skills/dreaming/SKILL.md
git status   # only SKILL.md modified
git commit -m "feat(dream): Phase 3 — Sonnet retrieval subagents

Adds pre-windowing (jq filter producing stable {ts, uuid, role, text}
JSONL into <dated_dir>/.windowed/), per-memory evidence-retrieval
dispatch + prompt (parallel Sonnet subagents writing <name>.audit.md
with ## Evidence + ## Code-artefact flags), and corpus-wide
flagged-region scanner + prompt. Resumable via missing-## Evidence
detection; SKIPPED.md captures subagent failures for the Phase 5 walk.

The pre-window jq filter extracts substantive text from every
Claude Code transcript block type (text, thinking, tool_use,
tool_result inc. nested-array form, plus string-form .message.content)
rather than the naive .message.content[0].text path — verified against
a representative 960-line transcript: 475 substantive lines survive
the comprehensive extractor vs 48 under the naive path.

Covers AC3.1 through AC3.8. Implementation deviates from design text
in two places: subagent_type 'denubis-basic-agents:sonnet-general-purpose'
(no raw model: <id> override precedent in repo) and flat
frontmatter.lastAudited. The subagent_type deviation matches observable
repo state (20+ existing precedents); the lastAudited deviation adopts
the user's global CLAUDE.md flat-frontmatter convention — no existing
memory file has a lastAudited field in any form (this plugin invents
it at first finalisation)."
```
<!-- END_TASK_8 -->
