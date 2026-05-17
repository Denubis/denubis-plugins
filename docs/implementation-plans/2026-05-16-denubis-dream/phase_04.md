# denubis-dream Implementation Plan — Phase 4: Opus judgement

**Goal:** After Phase 3's Sonnet retrieval populates `.audit.md` files with `## Evidence` and `## Code-artefact flags`, Opus (the calling session) reads each `.audit.md`, applies the five gates (*holds*, *correct*, *useful*, *duplicate*, *supported*), appends `## Changes` (diff-narrative hunks with cited gate motivations) and `## Disposition` (`keep`, `edit`, or `prune`), writes the proposed-state mirror `<dated_dir>/<name>.md`, and regenerates `<dated_dir>/MEMORY.md` conservatively (remove pruned-file links; preserve all other content byte-for-byte). In autonomous mode the pass exits cleanly after MEMORY.md is written; in manual mode it continues straight into the Phase 5 walk.

**Architecture:** Opus judgement is in-session — the calling Opus does the work directly via `Read`, `Write`, `Edit`. No subagent dispatch. The five gates are operationalised against concrete evidence sources from Phase 3 outputs (`## Evidence` and `## Code-artefact flags` sections) plus Opus's own read of the memory body. Duplicate detection cross-references descriptions across the full live memory set (loaded once at the start of the pass). MEMORY.md regeneration preserves the user's hand-curated topical sections and prose hooks — Phase 4 only removes lines pointing to pruned files; substantive hook edits are deferred to Phase 5's reconciliation walk where the user can review them.

**Tech Stack:** Read/Write/Edit (skill text instructs Opus directly). No external tools.

**Scope:** Phase 4 of 7.

**Codebase verified:** 2026-05-17 (live `MEMORY.md` read confirmed the topical-section + prose-hook structure; hand-curated organisation cannot be auto-derived from frontmatter descriptions, motivating the conservative regeneration approach).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and verifies:

### denubis-dream.AC4: Judgement and proposal (Opus)
- **denubis-dream.AC4.1 Success:** Each `<name>.audit.md` gets a `## Changes` section with diff-narrative hunks; each hunk cites the gate (*holds* / *correct* / *useful* / *duplicate* / *supported*) that motivated it.
- **denubis-dream.AC4.2 Success:** Each `<name>.audit.md` gets a `## Disposition` line: exactly one of `keep`, `edit`, or `prune`.
- **denubis-dream.AC4.3 Success:** Proposed-state mirror `<name>.md` written for each existing memory (a single line `<!-- PRUNE -->` for full removal).
- **denubis-dream.AC4.4 Success:** `memory.dream-DATE/MEMORY.md` regenerated to reflect proposed kept + edited entries; pruned ones omitted; flagged regions not yet listed (those join at promote-acceptance time).
- **denubis-dream.AC4.5 Success:** `--autonomous` mode exits cleanly after MEMORY.md regeneration; no reconciliation walk occurs.
- **denubis-dream.AC4.6 Success:** Re-invoking `/dream` while some `.audit.md` files lack a `## Disposition` section re-runs Opus judgement only on those (skipping already-judged ones), then regenerates `MEMORY.md` to reflect the now-complete set.

---

<!-- START_TASK_1 -->
### Task 1: `## Gate semantics` section

**Verifies:** AC4.1 (gates that motivate the diff-narrative)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after Phase 3's `## Resumable retrieval` section.

**Implementation:**

Add a `## Gate semantics` section that operationalises each of the five gates: what concrete evidence source the gate consults, and what a positive/negative finding looks like.

The section text:

````markdown
## Gate semantics

The five gates are evaluative criteria — each gate's verdict motivates one or more diff-narrative hunks in the `## Changes` section. Gates are NOT recorded as standalone verdicts (no per-gate verdict table — see design DR5). Instead, every `## Changes` hunk cites which gate motivated the proposed change.

| Gate | Operational test | Primary evidence source | Negative finding looks like |
|------|------------------|-------------------------|------------------------------|
| **holds** | The memory's claim still describes reality in this project right now. | `## Evidence` (recent supporting transcript content) plus your own read of the memory body against current state. | The claim is about a workflow/practice/component that no longer exists or has been replaced; supporting transcripts are stale. |
| **correct** | Code artefacts named in the body still exist as named. | `## Code-artefact flags` — HITS support `correct`; MISSES contradict it. | One or more code-artefact MISSES that aren't intentional historical references (renamed file, removed function). |
| **useful** | A future Claude session in this project would behaviourally benefit from knowing this. | Your judgement of the body's shape — preference / pattern / constraint / domain knowledge (useful), vs. trivia / one-off context (not useful). | The body documents a one-time event with no durable behavioural implication. |
| **duplicate** | Another memory's description plausibly covers this claim. | The full list of memory `name :: description` pairs (load once at start of pass). | Two memories share the same description-level scope; the older or less-precise one is a duplicate. |
| **supported** | Transcript evidence exists for the claim. | `## Evidence` section — empty/sparse = `supported` is weak; rich ev-NNN content = `supported` strong. | `## Evidence` says "(no transcript evidence in window since lastAudited)". |

**Duplicate-gate workflow.** At the START of the Phase 4 pass (before judging any memory), `Read` every `memory/*.md` frontmatter and assemble a `MEMORY_DESCRIPTIONS` list in working context — one entry per memory: `<name> :: <description>`. This is the cross-reference substrate for the `duplicate` gate. Re-reading per-memory wastes context tokens; reading once at the start is sufficient because the live memory set doesn't change during a single Phase 4 pass.

**Skipped memories from Phase 3.** Before applying gates, check `<dated_dir>/SKIPPED.md` (if it exists). Any memory listed there is excluded from Phase 4 judgement — it gets no `## Disposition` appended and no mirror written. Phase 5's reconciliation walk surfaces skipped memories as a special category at walk start.
````

**Verification (operational):**

After Phase 4 runs, open one `.audit.md` and confirm the appended `## Changes` section cites at least one of the five gates by name in italics (e.g., `— *useful*: ...`, `— *correct*: ...`). Confirm no per-gate verdict block (no rows of `holds: true | correct: false | ...`) appears — the gates are motivators, not stand-alone verdicts.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `## Diff-narrative writing` section

**Verifies:** AC4.1 (diff-narrative format)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Gate semantics`.

**Implementation:**

Add a `## Diff-narrative writing` section.

The section text:

````markdown
## Diff-narrative writing

`## Changes` is one Markdown unordered list. Each top-level bullet is one hunk — one concrete change you propose to the memory body, with a verb leading the bullet and an em-dashed gate citation explaining why.

**Hunk shape:**

```
- <Verb> <concrete reference to what changes> — *<gate-name>*[: <evidence-id or 1-line reason>][; *<second-gate>*: <reason>]
```

**Verbs:**
- `Removed` — a paragraph, sentence, code-block, or bullet drops out.
- `Edited` — a phrase or fact is rewritten in place (often code-artefact renames).
- `Reordered` — the same content, different sequence (lead with the active concern, etc.).
- `Added` — a sentence/paragraph drawn from `## Evidence` is woven in (rare in Phase 4 — usually only when new transcript content has clearly updated the user's stance).

**Gate citation rules:**
- Italicise the gate name with single asterisks: `*useful*`, `*correct*`, `*supported*`, `*holds*`, `*duplicate*`.
- Always cite the **primary motivating gate first**. A secondary gate may follow after a semicolon if its evidence reinforces the same hunk.
- When the hunk cites `*supported*`, name the relevant ev-NNN (`*supported*: ev-003`) — or `*supported*: no transcript evidence` for a negative finding.
- When the hunk cites `*correct*`, name the code-artefact (`*correct*: code-artefact flag shows scripts/auth.py renamed`).
- When the hunk cites `*useful*` or `*holds*`, a one-sentence reason suffices (these are judgement gates, not evidence-pointer gates).

**Cosmetic-only hunks** (reordering for narrative coherence, fixing a typo) need not cite a gate — write them with a trailing `— narrative coherence` or `— typo` instead.

**Worked example** (`feedback_review-all-levels.md`):

```
## Changes

- Removed paragraph 3 (the example about the prior session's misread) — *useful*: the example is too specific to that session and doesn't generalise; *supported*: no transcript evidence in window since lastAudited that anyone re-encountered the same misread.
- Edited "always interrogate Minor findings" to "interrogate Minor and Flagged findings before acting" — *holds*: the user clarified in transcript ev-002 that Flagged is structurally distinct from Minor.
- Reordered the three failure modes so the strongest (false-world-model) leads — narrative coherence.

## Disposition

edit
```

**Empty `## Changes`** (no proposed change at all) is written explicitly as:

```
## Changes

(no changes proposed — memory holds correct, useful, and supported as-written)

## Disposition

keep
```

— never omitted. Phase 5's walk detects empty-changes-keep memories via this exact marker and batches them.
````

**Verification (operational):**

After Phase 4, open one `keep`-disposition audit.md and confirm `## Changes` contains the literal "(no changes proposed — ..." marker. Open one `edit`-disposition audit.md and confirm hunks use the `- Verb ... — *gate*: ...` shape.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: `## Disposition computation` section

**Verifies:** AC4.2

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Diff-narrative writing`.

**Implementation:**

Add a `## Disposition computation` section.

The section text:

````markdown
## Disposition computation

After writing `## Changes`, append a `## Disposition` line. Exactly one verb:

| Disposition | When to write it |
|-------------|-------------------|
| `keep` | `## Changes` is the empty marker — no proposed change. |
| `edit` | One or more substantive hunks (`Removed`, `Edited`, `Added`, `Reordered`) — the memory survives but its body changes. |
| `prune` | The memory should not survive this audit. Use ONLY when at least two of *holds*, *useful*, *supported* fail decisively. A single failing gate is usually `edit`-worthy, not prune-worthy. |

The disposition is the verb on its own line, no trailing punctuation:

```
## Disposition

keep
```

**Conservative prune principle.** Pruning loses the user's prior judgement. Bias toward `edit` over `prune` when a partial salvage is plausible. The Phase 5 walk lets the user override an `edit` to `prune` (or a `keep` to `prune`) easily; the reverse — restoring a pruned memory — requires re-typing it. Asymmetric cost favours edit-leaning judgement here.

**`duplicate` gate and disposition.** When `duplicate` fires, prune the LESS PRECISE of the two memories (the one whose description is the broader scope, or the older `originSessionId`). The surviving memory's `## Changes` should cite a `*duplicate*: <name of pruned counterpart>` line acknowledging the merge.
````

**Verification (operational):**

After Phase 4, count `## Disposition` occurrences across `<dated_dir>/*.audit.md`. The count must equal `(memories) - (SKIPPED entries)`. Each disposition line must be one of the three verbs.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: `## Judgement orchestration` section

**Verifies:** AC4.6 (resumable judgement)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Disposition computation`.

**Implementation:**

Add a `## Judgement orchestration` section that describes the in-session Opus loop.

The section text:

````markdown
## Judgement orchestration

Phase 4 runs in the current Opus session (no subagent dispatch). The loop:

1. **Load skipped list.** Read `<dated_dir>/SKIPPED.md` if it exists. Hold the list of skipped memory names.
2. **Load memory descriptions.** Read every `<main_dir>/memory/*.md` frontmatter (excluding `MEMORY.md`). Build the `MEMORY_DESCRIPTIONS` list once — used for the `duplicate` gate cross-reference.
3. **Walk `<dated_dir>/*.audit.md`** (any order — judgement is per-file independent):
   - **Skip if** the file already has a `## Disposition` section (AC4.6: resumable — re-invocation only judges what hasn't been judged).
   - **Skip if** the memory name is in `SKIPPED.md` (no `## Evidence` was retrieved; nothing to judge against).
   - **Otherwise:** apply the five gates; append `## Changes` (Task 2 format); append `## Disposition` (Task 3 verb).
4. **Mirror-write** every judged memory's proposed body (Task 5).
5. **Regenerate `<dated_dir>/MEMORY.md`** (Task 6).
6. **Autonomous-mode exit** check (Task 7).

**Order independence.** Memories are judged independently — `duplicate` is the only gate that needs cross-memory context, and `MEMORY_DESCRIPTIONS` provides that without ordering constraints. You may judge memories in any order (mtime, alphabetical, by inspection).

**Resumable (AC4.6).** If a Phase 4 pass crashed after judging some memories (their `.audit.md` files have `## Disposition` lines) but before others, re-invocation picks up where it left off. The presence of `## Disposition` is the marker for "this memory has been judged in some prior pass".

**Mirror writing after judgement, not interleaved.** Write all `## Changes` and `## Disposition` sections to all audit files FIRST, then walk again to write mirrors. This separates the model-mediated judgement phase from the mechanical file-output phase — and means a crash mid-Phase 4 leaves the judgement record intact even if mirror writing didn't complete.
````

**Verification (operational):**

After Phase 4:
- Every non-skipped `*.audit.md` has both `## Changes` and `## Disposition` sections.
- Re-invoke `/dream`; confirm no `.audit.md` is re-written (no mtimes change for already-judged files).
- Manually delete the `## Disposition` section from one `.audit.md` and re-invoke `/dream`; confirm ONLY that file is re-judged (mtime updates only on the touched file).
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `## Mirror writing` section

**Verifies:** AC4.3

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Judgement orchestration`.

**Implementation:**

Add a `## Mirror writing` section.

The section text:

````markdown
## Mirror writing

After all `*.audit.md` files have their `## Changes` and `## Disposition` sections, walk them again and write the proposed-state mirror `<dated_dir>/<name>.md` per disposition:

| Disposition | Mirror body |
|-------------|-------------|
| `keep` | Byte-for-byte copy of the live `<main_dir>/memory/<name>.md`. The frontmatter and body are preserved unchanged. |
| `edit` | The live memory's frontmatter PLUS a revised body reflecting the `## Changes` hunks applied to the original body. The frontmatter's `description` line may also need updating if a hunk cited a description-level claim — apply that edit too. |
| `prune` | A single line: `<!-- PRUNE -->` (no frontmatter, no body — just the marker). |

**`Write` semantics.** Use the `Write` tool to create each mirror. Each `Write` overwrites unconditionally — a mid-pass crash that wrote some mirrors but not others is OK; re-invocation regenerates them.

**Skipped memories: no mirror.** Mirrors are NOT written for memories in `SKIPPED.md` — Phase 5 surfaces them as a special category and the user decides whether to retry retrieval or prune them manually.

**Why mirror at all when keep just copies?** Phase 5's reconciliation walk reads from the mirror, not the live memory. If a user override during the walk changes a kept memory to a prune (the user disagrees with the gate analysis), the change applies to the mirror — the live memory is untouched until finalisation. Mirror-as-substrate keeps the live `memory/` untouched during the walk (DoD #3).
````

**Verification (operational):**

After Phase 4:
- One `<name>.md` mirror file exists in `<dated_dir>` per non-skipped audit.
- `keep` mirrors are byte-identical to their live counterparts: `diff <main>/memory/<name>.md <dated_dir>/<name>.md` returns nothing.
- `prune` mirrors are exactly `<!-- PRUNE -->\n` (no other content).
- `edit` mirrors have the same frontmatter shape as their live counterparts but the body diverges.
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: `## MEMORY.md regeneration` section

**Verifies:** AC4.4 (kept + edited reflected; pruned omitted; flagged regions deferred to Phase 5)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Mirror writing`.

**Implementation:**

Add a `## MEMORY.md regeneration` section with the conservative algorithm.

The section text:

````markdown
## MEMORY.md regeneration

Regenerate `<dated_dir>/MEMORY.md` from the live `<main_dir>/memory/MEMORY.md` conservatively. The user's hand-curated topical sections and prose hooks are not Phase 4's content to author — Phase 4 only removes lines pointing to pruned files.

**Algorithm:**

```bash
# Build the set of pruned-memory names from the mirrors
PRUNED_NAMES=()
for mirror in "$DATED_DIR"/*.md; do
  # Skip subdirectories' .md files and the regenerated MEMORY.md itself
  basename=$(basename "$mirror")
  [ "$basename" = "MEMORY.md" ] && continue
  case "$basename" in *.audit.md) continue;; esac

  if [ "$(cat "$mirror")" = "<!-- PRUNE -->" ]; then
    name="${basename%.md}"
    PRUNED_NAMES+=("$name")
  fi
done
```

Then in the current Opus session:

1. `Read` the live `<main_dir>/memory/MEMORY.md`.
2. Identify lines matching the link pattern `- [<Title>](<file>.md) — <hook>`.
3. For each such line, if `<file>` (basename without `.md`) is in `PRUNED_NAMES`, drop the line; otherwise keep it byte-for-byte.
4. Non-link lines (section headings like `## Feedback`, narrative text, blank lines) are preserved unconditionally.
5. **Edit case: hook text is preserved.** If a memory is `edit`-disposition, its hook line in MEMORY.md is preserved as-is. If the user wants to update the hook to reflect the body edit, they do so in the Phase 5 walk's `edit <instructions>` turn — Phase 4 doesn't predict that judgement.
6. **Flagged regions are deferred.** New entries (for `flagged/region-NNN.flagged.md` files the user accepts during Phase 5 promotion) are added to MEMORY.md in Phase 6 finalisation — Phase 4 doesn't include them.
7. `Write` the result to `<dated_dir>/MEMORY.md`.

**Post-regeneration sanity:**

```bash
# Count link lines in both files — proposed should be live minus pruned
LIVE_LINKS=$(grep -cE '^\- \[.+\]\([^)]+\.md\)' "$MAIN_DIR"/memory/MEMORY.md)
PROPOSED_LINKS=$(grep -cE '^\- \[.+\]\([^)]+\.md\)' "$DATED_DIR"/MEMORY.md)
EXPECTED=$((LIVE_LINKS - ${#PRUNED_NAMES[@]}))
if [ "$PROPOSED_LINKS" -ne "$EXPECTED" ]; then
  echo "denubis-dream: MEMORY.md regeneration link-count mismatch (live=$LIVE_LINKS proposed=$PROPOSED_LINKS pruned=${#PRUNED_NAMES[@]} expected=$EXPECTED)"
fi
```

A mismatch indicates a bug in the regeneration (either dropped a non-pruned link or kept a pruned one). Halt and surface to the user; do not write the autonomous-pass-complete message until resolved.
````

**Verification (operational):**

After Phase 4:
- `<dated_dir>/MEMORY.md` exists.
- If at least one mirror is `prune`, `diff <main_dir>/memory/MEMORY.md <dated_dir>/MEMORY.md` shows only line-deletions (no other content changes).
- If no mirror is `prune`, the diff is empty.
- `grep -E '^\- \[.+\]\([^)]+\.md\)' <dated_dir>/MEMORY.md` does not list any pruned file's basename.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: `## Autonomous exit` section

**Verifies:** AC4.5

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## MEMORY.md regeneration`.

**Implementation:**

Add a `## Autonomous exit` section.

The section text:

````markdown
## Autonomous exit

After `<dated_dir>/MEMORY.md` has been written, branch on `MODE`:

```bash
if [ "$MODE" = "autonomous" ]; then
  echo "denubis-dream: autonomous pass complete."
  echo "  Dated dir: $DATED_DIR"
  echo "  Memories judged: $(grep -l '^## Disposition$' "$DATED_DIR"/*.audit.md 2>/dev/null | wc -l)"
  echo "  Flagged regions: $(find "$DATED_DIR"/flagged -name 'region-*.flagged.md' 2>/dev/null | wc -l)"
  echo "  Skipped memories: $(if [ -f "$DATED_DIR"/SKIPPED.md ]; then grep -c '^- ' "$DATED_DIR"/SKIPPED.md; else echo 0; fi)"
  exit 0
fi

# Manual mode: continue straight into the Phase 5 reconciliation walk.
# See ## Walk entry below.
```

**The cron path ends here (AC4.5 + AC9.2).** A cron-driven `/dream --autonomous` produces the same dated-dir artefact as a manual run but never enters the walk. The user re-invokes `/dream` (no flag) interactively when they want to reconcile.
````

**Verification (operational):**

- Run `/dream --autonomous` (after deleting any existing dated dir for today). Confirm: dated dir exists, all `.audit.md` files have dispositions, `MEMORY.md` regenerated, the autonomous-pass-complete message printed with non-zero "memories judged" count, and the command exited cleanly (no walk).
- Run `/dream` (no flag) against the same state. Confirm execution continues past the autonomous-exit check (the actual walk is Phase 5; for this verification, the Phase 4 stub message should give way to the Phase 5 walk-entry stub once Phase 5 lands).
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Replace Phase 3 pipeline stub + commit

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — replace Phase 3's trailing `## Pipeline status (Phase 3)` block.

**Implementation:**

Replace the Phase 3 stub with:

```markdown
## Pipeline status (Phase 4)

Autonomous-pass judgement is in place: every retrieved memory has a `## Changes` diff-narrative and a `## Disposition`; mirrors and a regenerated `MEMORY.md` populate the dated dir. In autonomous mode the pass exits cleanly here. In manual mode the next step is the Phase 5 reconciliation walk (not yet implemented).

When invoked manually at this stage, the skill executes the full autonomous pass and prints:

> denubis-dream: autonomous pass complete (N kept, M edited, P pruned, K skipped). Reconciliation walk not yet implemented. Dated dir at <path>.

…and exits without entering the walk.
```

**Single commit for the full Phase 4 set.**

```bash
git add plugins/denubis-dream/skills/dreaming/SKILL.md
git status
git commit -m "feat(dream): Phase 4 — Opus judgement

Adds gate semantics (holds/correct/useful/duplicate/supported),
diff-narrative writing format (verb-led hunks with cited gates),
disposition computation (keep/edit/prune), in-session judgement
orchestration (resumable via ## Disposition presence), mirror writing
(prune = single-line <!-- PRUNE --> marker), conservative MEMORY.md
regeneration (remove pruned-file links only, preserve all other
content byte-for-byte), and autonomous-mode exit.

Covers AC4.1 through AC4.6. Conservative MEMORY.md regeneration
defers hook-line edits to Phase 5's reconciliation walk where the
user can review them alongside the body edits."
```
<!-- END_TASK_8 -->
