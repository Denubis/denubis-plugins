# denubis-dream Implementation Plan — Phase 6: Finalisation

**Goal:** After Phase 5's walk-end `y` confirmation, apply the dated-dir state to live `memory/`: atomic per-file writes for kept + edited memories (with `lastAudited` bumped to today's date), deletes for pruned memories, atomic moves for promoted scaffolds, atomic replace of live `MEMORY.md` (with promoted entries inserted by `type`→section heuristic), DoD #8 grep self-check, `.tmp` orphan cleanup, `.last-dream` timestamp write, and dated-dir `rm -rf` only after all preceding steps succeed.

**Architecture:** All operations happen in the calling Opus session via `Bash` (mv, rm, find, grep) and `Read`/`Write`/`Edit` (for the inline `lastAudited` bump and MEMORY.md type→section insertion). The `.tmp + mv` pattern guarantees per-file atomicity at the POSIX syscall level (the dated dir and live `memory/` are on the same filesystem under `~/.claude/projects/<main-slug>/`, so cross-filesystem caveats don't apply). Operation ordering is explicit because several steps have invariants (collision check before any write; DoD self-check before `.last-dream`; dated-dir removal last).

**Tech Stack:** Bash (`mv`, `rm`, `find`, `grep -RE`, `date -u`), Read/Write/Edit (lastAudited bump, MEMORY.md edits).

**Scope:** Phase 6 of 7.

**Codebase verified:** 2026-05-17 (dated dir and live `memory/` are sibling directories under `~/.claude/projects/<main-slug>/` — same filesystem confirmed; flat `lastAudited` cascade established in Phase 3).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and verifies:

### denubis-dream.AC7: Finalisation
- **denubis-dream.AC7.1 Success:** Finalise prompts for explicit user confirmation (`Apply to live memory/? [y/n]`) before any live `memory/` write. The prompt fires automatically at walk-end (AC5.10); it does not fire while un-decided entries remain.
- **denubis-dream.AC7.2 Success:** Mirror → live transfers use a `<name>.md.tmp` + `Bash mv` pattern; the `mv` rename is atomic at the POSIX syscall level (a concurrent read of `memory/<name>.md` sees either the pre-rename or post-rename content). A mid-finalisation interruption between the `.tmp` write and the `mv` may leave `.tmp` orphans in `memory/`; orphans are cleaned at the start of the next finalisation pass (AC7.10) before that pass reports success.
- **denubis-dream.AC7.3 Success:** PRUNE-marked mirrors result in deletion of the corresponding live `memory/<name>.md`.
- **denubis-dream.AC7.4 Success:** Promoted files are moved into live `memory/<name>.md` via the atomic pattern.
- **denubis-dream.AC7.5 Success:** Live `memory/MEMORY.md` is replaced from the dated-dir version via the atomic pattern.
- **denubis-dream.AC7.6 Success:** `frontmatter.lastAudited` bumped to today's date on every surviving live memory file (kept + edited + promoted).
- **denubis-dream.AC7.7 Failure:** Name collision in `promoted/` (matching an existing live memory name): finalise aborts and reports; no live writes occur; dated dir is preserved.
- **denubis-dream.AC7.8 Failure:** User rejects confirmation (`n`): finalise exits without applying; dated dir remains intact for later re-entry. *(handled by Phase 5's walk-end prompt; Phase 6 only starts on `y`)*
- **denubis-dream.AC7.9 Success:** After self-check passes, `~/.claude/projects/<main-slug>/.last-dream` is written (via `.tmp` + `mv`) containing the ISO date of this dream's finalisation, before the dated dir is removed. First dream creates the file; subsequent dreams overwrite it.
- **denubis-dream.AC7.10 Success:** Before reporting finalisation success, `Bash find memory/ -name '*.md.tmp' -delete` removes any `.tmp` orphans (defence against interrupted prior finalisations).

### denubis-dream.AC8: Self-check and dated-dir lifecycle
- **denubis-dream.AC8.1 Success:** Post-finalisation self-check `grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' memory/` returns zero matches.
- **denubis-dream.AC8.2 Success:** Dated dir is removed (`rm -rf`) only after the self-check passes.
- **denubis-dream.AC8.3 Failure:** Self-check returns non-zero matches: finalise aborts, reports the offending `file:line` pairs, leaves the dated dir intact.
- **denubis-dream.AC8.4 Success:** Repo `.gitignore` lists `memory.dream-*` (defence-in-depth — the dated dir is normally outside any worktree). *(handled in Phase 1 — already in place by the time Phase 6 runs)*

---

<!-- START_TASK_1 -->
### Task 1: `## Finalise entry` section

**Verifies:** AC7.1 (entry only after walk-end `y`)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after Phase 5's `## Walk-end detection + auto-finalise prompt` section.

**Implementation:**

Add a `## Finalise entry` section that documents the contract: Phase 6 runs only after a positive walk-end `y`.

The section text:

````markdown
## Finalise entry

Finalisation runs **only** after the Phase 5 walk-end prompt receives a `y`. The prompt is the single confirmation gate (per AC7.1); Phase 6 has no second prompt.

Pre-conditions when Phase 6 starts:
- `<dated_dir>` exists with mirrors, `promoted/`, `decisions.log` complete (walk-end was reached).
- Live `memory/` mtimes match the walk-entry baseline (AC5.8 was verified at walk-end).
- `MODE = manual` (autonomous mode never enters the walk, so never reaches Phase 6).

Print a one-line entry banner:

```
denubis-dream: finalisation starting. Operations: same-device check → collision check → orphan cleanup → pre-flight self-check → mirror transfer → prunes → promotes → MEMORY.md → post-write sanity → .tmp sanity → .last-dream → dated-dir cleanup.
```

Then proceed through Tasks 2 through 11 in order. Any abort condition (collision detected, pre-flight self-check fails, post-write sanity fails) leaves the dated dir intact and prints a specific abort message — the user can re-enter with `/dream` to resolve the issue and finalise again.

**Important-3 fix (two-phase self-check):** the design's single self-check has been replaced with a pre-flight (Task 7a) on the dated-dir proposed state BEFORE any live write, plus a post-write sanity (Task 7b) on live `memory/` AFTER. The pre-flight is what makes "abort" cleanly recoverable; the post-write sanity preserves AC8.1's literal verification point and catches the edge case where pre-existing live content carried a leak the dream didn't touch.

**Entry-time pre-write checks** (this section owns them — Important-2 fix). Before passing control to Task 2 (collision pre-flight), the `## Finalise entry` section runs these two checks:

```bash
# 1. Filesystem same-device check (per the atomic_write_memory helper's invariant).
mem_dev=$(stat -c '%d' "$MAIN_DIR"/memory)
dated_dev=$(stat -c '%d' "$DATED_DIR")
if [ "$mem_dev" != "$dated_dev" ]; then
  echo "denubis-dream: ABORT — memory/ and dated dir on different filesystems; atomic mv guarantee lost."
  echo "Dated dir preserved at $DATED_DIR. Move it to live alongside memory/ before re-invoking /dream."
  exit 1
fi

# 2. Start-of-pass .tmp orphan cleanup (AC7.10 — defence against prior interrupted finalisations).
#    Owned by THIS task (Task 1) so the implementer doesn't miss it. Task 8 describes the end-of-pass
#    sanity check; the start-of-pass cleanup belongs here at finalise entry.
PRE_FINALISE_ORPHANS=$(find "$MAIN_DIR"/memory/ -maxdepth 1 -name '*.md.tmp' 2>/dev/null)
if [ -n "$PRE_FINALISE_ORPHANS" ]; then
  count=$(printf '%s\n' "$PRE_FINALISE_ORPHANS" | wc -l)
  echo "denubis-dream: cleaning $count pre-existing .tmp orphan(s) from a prior interrupted finalisation:"
  printf '%s\n' "$PRE_FINALISE_ORPHANS" | sed 's/^/  - /'
  find "$MAIN_DIR"/memory/ -maxdepth 1 -name '*.md.tmp' -delete
fi
```

After these two checks pass, proceed to Task 2 (collision pre-flight).
````

**Verification (operational):**

After Phase 5's walk-end `y`, confirm the finalise-entry banner prints. After Phase 5's walk-end `n`, confirm Phase 6 does NOT start (dated dir persists).

Force a pre-existing `.tmp` orphan (`touch "$MAIN_DIR"/memory/fake.md.tmp`) then walk + finalise; confirm the entry-time cleanup message lists `fake.md.tmp` and removes it before Task 2 runs.

Stage `<dated_dir>` on a different filesystem than `<MAIN_DIR>/memory/` (e.g., bind-mount or move the dated dir to `/tmp/`) — confirm the same-device check aborts cleanly.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `## Collision pre-flight check` section

**Verifies:** AC7.7 (collision aborts cleanly)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Finalise entry`.

**Implementation:**

Add a `## Collision pre-flight check` section. This runs FIRST in finalisation — before any live write — so an abort leaves zero side effects.

The section text:

````markdown
## Collision pre-flight check

For each `<dated_dir>/promoted/*.md`, check whether a live memory of the same name already exists. If yes, abort.

```bash
COLLISIONS=()
for promoted in "$DATED_DIR"/promoted/*.md; do
  [ -e "$promoted" ] || continue   # empty promoted/ is fine
  name=$(basename "$promoted")
  if [ -e "$MAIN_DIR"/memory/"$name" ]; then
    COLLISIONS+=("$name")
  fi
done

if [ ${#COLLISIONS[@]} -gt 0 ]; then
  echo "denubis-dream: ABORT — promoted memory name collision(s):"
  for c in "${COLLISIONS[@]}"; do
    echo "  - $c (already exists at $MAIN_DIR/memory/$c)"
  done
  echo ""
  echo "No live writes occurred. Dated dir preserved at $DATED_DIR."
  echo "Resolve by renaming the promoted file or editing the colliding live memory,"
  echo "then re-invoke /dream to re-enter the walk and finalise."
  exit 1
fi
```

**Why pre-flight (before any write):** AC7.7 requires that a collision aborts without side effects. Detecting collisions AFTER the first promoted move would leave a half-applied state. The pre-flight check has the entire live `memory/` directory still untouched.

**Why not during the walk:** the walk doesn't know which scaffold names will land in `promoted/` until each promote turn completes. The pre-flight here is the single point at which the full promoted-set is knowable.

**Stale data possibility:** between this check and the actual Promoted file move (Task 5), another process could create the colliding live file. That's vanishingly unlikely in a single-user interactive workflow but worth documenting. The atomic mv pattern would then overwrite the foreign file silently — a follow-up concern only if `/dream` is ever made concurrent.
````

**Verification (operational):**

- Force a collision: before walking, manually create a live `memory/<name>.md` matching a planned promote slug. Walk to walk-end, type `y`; confirm Phase 6 aborts with the listed collision and dated dir is intact.
- Resolve (rename the colliding live file or rename the promoted scaffold via re-entry walk + edit); re-invoke `/dream`; confirm finalisation now succeeds.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: `## Per-file atomic write pattern` section

**Verifies:** AC7.2, AC7.6 (atomic mv + lastAudited bump pattern used by Tasks 4-6)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Collision pre-flight check`.

**Implementation:**

Add a `## Per-file atomic write pattern` section that defines the reusable pattern.

The section text:

````markdown
## Per-file atomic write pattern

All live `memory/` writes use the same atomic pattern: write to `<live>/<name>.md.tmp`, then `mv` over the live path. POSIX `mv` is atomic at the syscall level when source and destination are on the same filesystem — both the dated dir and live `memory/` are siblings under `~/.claude/projects/<main-slug>/`, so the guarantee holds.

**Helper function** (define once at the start of Phase 6, reuse throughout):

```bash
atomic_write_memory() {
  # $1 = source body file (mirror or promoted scaffold)
  # $2 = destination basename (e.g., "feedback_review-all-levels.md")
  local src="$1"
  local dest="$MAIN_DIR/memory/$2"
  local tmp="$dest.tmp"

  local today=$(date -u +%Y-%m-%d)

  # Bump lastAudited in the body during the write. Idempotent: insert if absent,
  # replace if present. Frontmatter is flat (no metadata: nesting) per Phase 3.
  awk -v today="$today" '
    BEGIN { in_fm=0; has_la=0; printed_la=0 }
    /^---$/ {
      if (in_fm == 0) { in_fm=1; print; next }
      else {
        if (!has_la) print "lastAudited: " today
        in_fm=2; print; next
      }
    }
    in_fm == 1 && /^lastAudited:/ {
      print "lastAudited: " today
      has_la=1
      next
    }
    { print }
  ' "$src" > "$tmp"

  mv "$tmp" "$dest"   # atomic
}
```

**Why awk and not jq or yq:** the frontmatter is YAML-ish but the body is freeform Markdown — a full YAML parse-and-rewrite would either lose body content or require splitting and re-joining. The awk script preserves the body verbatim and only edits the frontmatter line(s) for `lastAudited`.

**Idempotency.** Running `atomic_write_memory` twice produces identical output (the second run's `lastAudited` overwrites the first's — same date — leaving the file byte-identical). This is important if a partial finalisation needs to be re-run.

**Same-filesystem invariant.** The pattern depends on `<MAIN_DIR>/memory/` and `<DATED_DIR>` being on the same filesystem. If a future deployment puts them on different filesystems (e.g., symlinking the dated dir to `/tmp`), the `mv` falls back to copy-and-delete which is NOT atomic. Detect at finalise-entry time and refuse:

```bash
mem_dev=$(stat -c '%d' "$MAIN_DIR"/memory)
dated_dev=$(stat -c '%d' "$DATED_DIR")
if [ "$mem_dev" != "$dated_dev" ]; then
  echo "denubis-dream: ABORT — memory/ and dated dir on different filesystems; atomic mv guarantee lost."
  exit 1
fi
```

Add this filesystem check to the `## Finalise entry` banner section (Task 1) — fail fast before any of Tasks 2-10 runs.
````

**Verification (operational):**

- Walk and finalise a memory with no existing `lastAudited` field; `head <live>/<name>.md` after finalisation; confirm `lastAudited: <today>` appears in the frontmatter.
- Walk and finalise a previously-finalised memory (re-dream); confirm `lastAudited:` was updated to the new date (not appended as a duplicate line).
- Use `cmp` to confirm the body content (lines after the frontmatter close marker) is byte-for-byte identical to the dated-dir mirror's body.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: `## Mirror transfer` section

**Verifies:** AC7.2, AC7.3, AC7.6 (keep + edit transfer; prune deletion)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Per-file atomic write pattern`.

**Implementation:**

Add a `## Mirror transfer` section that walks the dated-dir mirrors and applies them.

The section text:

````markdown
## Mirror transfer

Walk `<dated_dir>/*.md` (excluding `MEMORY.md` and excluding the regenerated MEMORY.md — see Task 6). For each mirror:

```bash
for mirror in "$DATED_DIR"/*.md; do
  bn=$(basename "$mirror")
  [ "$bn" = "MEMORY.md" ] && continue

  if [ "$(cat "$mirror")" = "<!-- PRUNE -->" ]; then
    # AC7.3: PRUNE marker triggers live deletion
    live="$MAIN_DIR/memory/$bn"
    if [ -e "$live" ]; then
      rm "$live"
    fi
    continue
  fi

  # keep or edit: atomic write with lastAudited bump
  atomic_write_memory "$mirror" "$bn"
done
```

**Skipped memories.** Memories listed in `<dated_dir>/SKIPPED.md` were given a `keep` or `prune` decision in the Phase 5 walk's skipped-memory turn. That decision wrote a mirror (`keep` = byte-for-byte live copy; `prune` = `<!-- PRUNE -->`). Mirror transfer handles them through the same loop — no special case needed.

**Failed retries.** Memories where the Phase 5 retry workflow ultimately produced a successful re-judgement get a normal `.audit.md` and mirror by walk-end — they're indistinguishable from un-skipped memories at Phase 6.
````

**Verification (operational):**

After Phase 6 mirror transfer:
- Every non-pruned memory's live `lastAudited` is today's date.
- Every pruned memory's live file is absent.
- A `diff` between each live memory's body (post-frontmatter) and its dated-dir mirror's body shows zero changes.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `## Promoted file move` section

**Verifies:** AC7.4, AC7.6 (promoted entries get lastAudited bump too)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Mirror transfer`.

**Implementation:**

Add a `## Promoted file move` section.

The section text:

````markdown
## Promoted file move

For each `<dated_dir>/promoted/*.md`:

```bash
for promoted in "$DATED_DIR"/promoted/*.md; do
  [ -e "$promoted" ] || continue
  bn=$(basename "$promoted")
  atomic_write_memory "$promoted" "$bn"
done
```

The same `atomic_write_memory` helper (Task 3) writes the promoted scaffold and bumps `lastAudited` to today. Promoted memories are "freshly audited" by virtue of being authored from a flagged region whose excerpt was reviewed in this dream.

**Collision was pre-flighted** (Task 2). At this point a collision cannot occur (the pre-flight aborted before reaching Task 4); if `<live>/<name>.md` exists when this loop runs, that's a bug.

**Dismissed flagged regions** stay in `<dated_dir>/flagged/` and are removed when the dated dir itself is removed (Task 10). No explicit cleanup here.
````

**Verification (operational):**

After Phase 6:
- Every accepted promote has a live `memory/<slug>.md` with today's `lastAudited`.
- `<dated_dir>/promoted/` is empty (or, equivalently, its contents have all been written to live `memory/` — both states are valid since the dated dir is about to be removed anyway).
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: `## MEMORY.md replacement` section

**Verifies:** AC7.5 (atomic replace) + the promoted-entry insertion that Phase 4's conservative regeneration deferred

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Promoted file move`.

**Implementation:**

Add a `## MEMORY.md replacement` section that handles the type→section insertion of promoted entries, then atomically replaces live MEMORY.md.

The section text:

````markdown
## MEMORY.md replacement

Phase 4 regenerated `<dated_dir>/MEMORY.md` conservatively (removed pruned-file links only). Phase 6 inserts promoted entries before the atomic replace.

**Type→section mapping** (read from live MEMORY.md):

| Promoted memory's `type` | Insert under |
|---------------------------|--------------|
| `feedback` | `## Feedback` |
| `project` | `## Active Design Work` |
| `user` | `## User Communication Signals` (or first section starting with "## User") |
| `reference` | `## Reference` |

If the matching section heading doesn't exist in the dated-dir MEMORY.md, append it at the end of the file (preserving the file's trailing newline).

**Algorithm** (run on the dated-dir MEMORY.md, then atomic-replace live):

```bash
DATED_MEMORY="$DATED_DIR/MEMORY.md"
LIVE_MEMORY="$MAIN_DIR/memory/MEMORY.md"

for promoted in "$DATED_DIR"/promoted/*.md; do
  [ -e "$promoted" ] || continue

  bn=$(basename "$promoted")
  name="${bn%.md}"

  # Extract type and description from the promoted file's flat frontmatter
  ptype=$(awk '/^---$/{f++;next} f==1 && /^type:/{sub(/^type:[[:space:]]*/,""); print; exit}' "$promoted")
  desc=$(awk '/^---$/{f++;next} f==1 && /^description:/{sub(/^description:[[:space:]]*/,""); print; exit}' "$promoted")

  # Map type to section heading
  case "$ptype" in
    feedback)  section="## Feedback" ;;
    project)   section="## Active Design Work" ;;
    user)      section="## User Communication Signals" ;;
    reference) section="## Reference" ;;
    *)         section="## Promoted" ;;   # fallback for unknown types
  esac

  # Build the link line. Use the description as the hook; the user can edit
  # post-finalisation by hand.
  line="- [$name]($bn) — $desc"

  # Insert under the matching section. If the section exists, append after
  # the last bullet under it (or after the heading if no bullets yet).
  # If the section is absent, append the section + heading + line at file end.
  #
  # Match semantics MUST be exact-line (-Fxq), not substring (-qF). The awk
  # below uses `$0 == sec` (exact-line equality); using `grep -qF` (substring)
  # for the precondition would create a mismatch where a longer heading like
  # `## Feedback Patterns` substring-matches `## Feedback` here but fails the
  # awk's exact-line check — silently dropping the insertion and triggering
  # the post-write sanity halt without naming the cause. Keep both predicates
  # aligned (Medium-4 fix).
  if grep -Fxq "$section" "$DATED_MEMORY"; then
    # Append after the section's existing bullets (use awk for in-place insertion)
    awk -v sec="$section" -v line="$line" '
      BEGIN { in_section=0; inserted=0 }
      $0 == sec { in_section=1; print; next }
      in_section && /^## / && $0 != sec {
        if (!inserted) { print line; inserted=1 }
        in_section=0
        print
        next
      }
      { print }
      END { if (in_section && !inserted) print line }
    ' "$DATED_MEMORY" > "$DATED_MEMORY.work"
    mv "$DATED_MEMORY.work" "$DATED_MEMORY"
  else
    # Section absent — append at end
    printf '\n%s\n\n%s\n' "$section" "$line" >> "$DATED_MEMORY"
  fi
done

# Atomic replace of live MEMORY.md (uses cp not mv so the dated-dir source survives any later abort — Important-3 fix)
cp "$DATED_MEMORY" "$LIVE_MEMORY.tmp"
mv "$LIVE_MEMORY.tmp" "$LIVE_MEMORY"
```

**Why `cp` then `mv` (not two `mv`s — Important-3 fix):** if a later step (post-write sanity at Task 7b, or `.tmp` sanity at Task 8, or `.last-dream` write) aborts, the dated dir must remain intact so the user can re-enter with `/dream` and finalise after resolving the issue. The original two-`mv` pattern moved the dated `MEMORY.md` away first, leaving the dated dir's MEMORY.md gone on abort. Using `cp` instead leaves the dated `MEMORY.md` in place; the second `mv` (`.tmp` → live) is still atomic on the same filesystem.

**Section-heading text matching** depends on the live MEMORY.md's existing section headings. If the user has customised them (e.g., renamed `## Feedback` to `## Lessons`), the default mapping above won't find a match and the promoted entry will land in a fallback `## Promoted` section at the end. The user can then move it manually.

**Uniqueness assumption** (Minor-2 fix): the awk insertion above assumes section headings are unique in MEMORY.md. The awk uses `$0 == sec` as a heading match and `in_section && /^## / && $0 != sec` as the terminator — if a heading appears twice, the awk inserts the link line after the FIRST occurrence's bullets only, leaving the second occurrence empty. Live MEMORY.md hand-curated by the user is overwhelmingly likely to satisfy this (no one creates two `## Feedback` sections deliberately) but the assumption is worth surfacing. The post-regeneration sanity check (the link-count comparison earlier in this section) catches the case where the awk insertion silently failed to fire.
````

**Verification (operational):**

- After a dream with at least one promote, confirm the live MEMORY.md has the new entry's link line under the section matching its `type`.
- Confirm the live MEMORY.md's other section headings, prose, and pre-existing link lines are unchanged (only the new entry was added).
- Use `diff` against a pre-Phase-6 snapshot to verify.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Two-phase DoD #8 self-check (pre-flight + post-write sanity) — Important-3 fix

**Verifies:** AC8.1 (post-write sanity preserves literal AC wording), AC8.3 (abort with intact dated dir)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — add TWO sections at distinct positions in the skill body:
  - **`## Pre-flight self-check`** — position in the body **after `## .tmp orphan cleanup` (Task 8's start-of-pass cleanup) and before `## Mirror transfer` (Task 4).** This is the abort-cleanly checkpoint — no live writes have happened yet.
  - **`## Post-write self-check sanity`** — position in the body **after `## MEMORY.md replacement` (Task 6) and before `## .tmp orphan cleanup` end-of-pass sanity (Task 8).** This is the AC8.1 literal-wording verification.

**Why two-phase (Important-3 finding from code-reviewer):** the original single-pass design ran the self-check post-write on live `memory/`. If the check found a leak, "abort" was nominal — Tasks 4-6 had already mutated live `memory/` (frontmatter bumps, prune deletes, MEMORY.md replaced). The pre-flight on the dated-dir proposed state is the only abort point where zero live writes have happened. The post-write sanity is retained to preserve the design's AC8.1 wording and to catch the edge case where a pre-existing live memory had leakage the dream didn't touch.

**Pre-flight section body (positioned before mirror transfer):**

````markdown
## Pre-flight self-check

Greps the proposed state that's about to land in live `memory/` for transcript-UUID and line-range citations. Runs BEFORE any live write so an abort fully reverts.

```bash
# Build the set of files destined for live memory:
# - mirrors at <dated_dir>/*.md (excluding *.audit.md which intentionally contain UUIDs as evidence)
# - excluding mirrors whose body is <!-- PRUNE --> (those become deletions, not content)
# - promoted/*.md (newly-authored scaffolds)
# - the regenerated MEMORY.md (could carry leakage if the user pasted into a hand-curated hook)
SELFCHECK_FILES=()

for f in "$DATED_DIR"/*.md; do
  bn=$(basename "$f")
  case "$bn" in
    *.audit.md) continue ;;
    MEMORY.md)  SELFCHECK_FILES+=("$f"); continue ;;
  esac
  if [ "$(cat "$f")" = "<!-- PRUNE -->" ]; then
    continue
  fi
  SELFCHECK_FILES+=("$f")
done

for f in "$DATED_DIR"/promoted/*.md; do
  [ -e "$f" ] && SELFCHECK_FILES+=("$f")
done

if [ ${#SELFCHECK_FILES[@]} -gt 0 ]; then
  PREFLIGHT_HITS=$(grep -nE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' "${SELFCHECK_FILES[@]}" 2>/dev/null)
else
  PREFLIGHT_HITS=""
fi

if [ -n "$PREFLIGHT_HITS" ]; then
  echo "denubis-dream: ABORT — DoD #8 pre-flight self-check failed. Offending lines in proposed state:"
  echo "$PREFLIGHT_HITS"
  echo ""
  echo "No live writes occurred. Dated dir intact at $DATED_DIR."
  echo "Source: a Phase 5 walk \`edit\` turn introduced (or failed to scrub) transcript-citation content"
  echo "into a memory body. Evidence citations belong in the .audit.md files, not in the memory bodies."
  echo ""
  echo "Recovery: re-invoke /dream to re-enter the walk; edit the offending mirror(s) to remove the"
  echo "citations; finalise again."
  exit 1
fi

echo "denubis-dream: pre-flight self-check passed (zero transcript-citation leaks in proposed state)."
```

**Why exclude `.audit.md` files.** They contain `ev-NNN: <uuid-short> [ts] <role>:` lines — `<uuid-short>` is 8 hex chars which matches the `transcript [a-f0-9]+` regex if prefixed by the literal "transcript". The audit files are never destined for live `memory/`; they live and die with the dated dir.

**Why exclude PRUNE-marked mirrors.** They become `rm` operations, not content writes. Their `<!-- PRUNE -->` body never lands anywhere.

**Why include the dated `MEMORY.md`.** A hand-curated hook line could (theoretically) carry leakage — e.g., if a user's existing MEMORY.md hook prose mentioned a transcript UUID. We check before atomic-replacing live MEMORY.md.
````

**Post-write sanity section body (positioned after MEMORY.md replace):**

````markdown
## Post-write self-check sanity

The design's literal AC8.1 verification: grep on live `memory/` after all writes completed. Trivially passes if the pre-flight passed AND mirror transfer was bug-free. The check exists as defence-in-depth for two edge cases the pre-flight cannot catch: (a) a pre-existing live memory file had leakage that the dream didn't touch (so it's still leaked post-finalise), and (b) a bug in the atomic_write_memory helper introduced new leakage during the write itself.

```bash
SANITY_HITS=$(grep -RnE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' "$MAIN_DIR"/memory/ 2>/dev/null)

if [ -n "$SANITY_HITS" ]; then
  echo "denubis-dream: ABORT — post-write self-check sanity failed. Offending lines in live memory/:"
  echo "$SANITY_HITS"
  echo ""
  echo "This is unexpected: the pre-flight passed but the post-write sanity caught leakage. Either:"
  echo "  (a) a pre-existing live memory file had leakage the dream didn't touch (and didn't write over), OR"
  echo "  (b) a bug in atomic_write_memory introduced new leakage during the write."
  echo ""
  echo "Dated dir preserved at $DATED_DIR. Live memory/ has the partially-applied dream state."
  echo "Recovery: inspect the offending files. If case (a), edit by hand to clean. If case (b),"
  echo "investigate the helper. Re-invoke /dream to re-enter and finalise once clean."
  exit 1
fi

echo "denubis-dream: post-write self-check sanity passed."
```

**Why \`MEMORY.md\` replace is now `cp` not `mv`** (also part of Important-3 fix): the original `mv "$DATED_MEMORY" "$LIVE_MEMORY.tmp"` moved the dated source away before the sanity check could fail. With `cp`, the dated `MEMORY.md` source survives any later abort, keeping the dated dir intact for re-entry. See Task 6's updated implementation.
````

**Verification (operational):**

Pre-flight:
- Edit one dated-dir mirror to include `transcript abc12345` BEFORE the user types `y` at walk-end (artificial leak via direct file edit). Finalise; confirm pre-flight aborts with the offending file:line listed AND zero live mutations (live `memory/` mtimes unchanged from walk-entry baseline).
- Re-edit the mirror to remove the leak; re-invoke `/dream`; finalise; confirm success.

Post-write sanity:
- Manually inject leakage into a live memory file BEFORE invoking `/dream` (so the pre-existing live file has a leak the dream won't touch). Walk + finalise; confirm post-write sanity catches it (since the pre-flight only sees dated-dir content). The abort message should distinguish "pre-existing" vs "bug" cases.
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: `## .tmp orphan cleanup` section

**Verifies:** AC7.10

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## DoD #8 self-check`.

**Implementation:**

Add a `## .tmp orphan cleanup` section.

The section text:

````markdown
## .tmp orphan cleanup (end-of-pass sanity)

**Note on ownership** (Important-2 fix): the start-of-pass cleanup is owned by Task 1's `## Finalise entry` section — that's where it actually lives in the skill body. This `## .tmp orphan cleanup` section in the skill body holds ONLY the end-of-pass sanity check below. The split is intentional: start-of-pass runs at finalise entry (before any write), end-of-pass runs after the post-write self-check sanity (after all writes). Two skill-body sections, two distinct lifecycle points.

**End-of-pass sanity check** (after self-check sanity passes, before `.last-dream` write): confirm that this finalisation's atomic writes left no fresh orphans. If any exist, that's a bug in the atomic_write_memory helper — halt and report.

```bash
POST_FINALISE_ORPHANS=$(find "$MAIN_DIR"/memory/ -maxdepth 1 -name '*.md.tmp')
if [ -n "$POST_FINALISE_ORPHANS" ]; then
  echo "denubis-dream: BUG — this finalisation left fresh .tmp orphans:"
  echo "$POST_FINALISE_ORPHANS" | sed 's/^/  - /'
  echo "Atomic mv pattern is leaking. Halt — investigate atomic_write_memory."
  exit 1
fi
```

**Why two distinct lifecycle points.** Start-of-pass cleanup (Task 1) is the AC7.10 defence against PRIOR-interruption orphans inherited from a previous crashed finalisation. End-of-pass sanity (this section) is belt-and-braces against bugs in THIS pass's atomic writes — never expected to find anything; if it does, the atomic invariant is broken and we want to know before we declare success.
````

**Verification (operational):**

- Force a pre-existing `.tmp` orphan: `touch <live>/memory/fake.md.tmp`. Run `/dream` through finalisation. Confirm the orphan-cleanup message lists `fake.md.tmp` and removes it.
- Run `/dream` again immediately; confirm the start cleanup reports zero orphans (the previous run cleaned them all).
<!-- END_TASK_8 -->

<!-- START_TASK_9 -->
### Task 9: `## .last-dream timestamp write` section

**Verifies:** AC7.9

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## .tmp orphan cleanup`.

**Implementation:**

Add a `## .last-dream timestamp write` section.

The section text:

````markdown
## .last-dream timestamp write

After the self-check passes and post-finalise sanity cleanup confirms no orphans, write today's ISO timestamp to `<MAIN_DIR>/.last-dream` via the atomic pattern:

```bash
LASTDREAM_PATH="$MAIN_DIR/.last-dream"
LASTDREAM_TMP="$LASTDREAM_PATH.tmp"

# Use the timestamp at finalisation moment (not at Phase 2 entry) so the file
# reflects when audit-state actually applied to live memory/.
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s\n' "$NOW_ISO" > "$LASTDREAM_TMP"

mv "$LASTDREAM_TMP" "$LASTDREAM_PATH"
```

**Why finalisation-time, not Phase 2 entry-time.** The corpus-wide flagged-region subagent's window in the NEXT dream uses this timestamp as the lower bound. Using the actual finalisation moment means the next dream's window starts exactly where this dream's coverage ended — no gaps, no overlap.

**First dream creates the file; subsequent dreams overwrite it.** The atomic pattern handles both cases the same way.

**Inter-dream persistence.** This is the only artefact that survives between dreams (apart from `frontmatter.lastAudited` per memory). Per design DR9, the dated dir itself is removed at finalisation (Task 10). The `.last-dream` file is the minimal corpus-windowing state that allows subsequent dreams to bound their flagged-region scans.
````

**Verification (operational):**

- After Phase 6: `cat <MAIN_DIR>/.last-dream` shows today's ISO timestamp.
- Inspect the timestamp value vs. `date -u +%Y-%m-%dT%H:%M:%SZ` at the moment of inspection — should be within a few seconds.
- Run a second dream the same day; finalise; confirm `.last-dream` is overwritten with the new timestamp.
<!-- END_TASK_9 -->

<!-- START_TASK_10 -->
### Task 10: `## Dated-dir removal` section

**Verifies:** AC8.2

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## .last-dream timestamp write`.

**Implementation:**

Add a `## Dated-dir removal` section.

The section text:

````markdown
## Dated-dir removal

Last operation of Phase 6. Only runs if every preceding step succeeded:

- Collision pre-flight passed (Task 2).
- Mirror transfer + prune deletes + promoted moves completed (Tasks 4-5).
- MEMORY.md atomic replace succeeded (Task 6).
- DoD #8 self-check returned zero matches (Task 7).
- Start-of-pass `.tmp` cleanup ran; end-of-pass sanity cleanup found no orphans (Task 8).
- `.last-dream` written (Task 9).

```bash
rm -rf "$DATED_DIR"

if [ -d "$DATED_DIR" ]; then
  echo "denubis-dream: BUG — dated dir still exists after rm -rf. Investigate."
  exit 1
fi

echo "denubis-dream: finalisation complete."
echo "  Dated dir removed: $DATED_DIR"
echo "  .last-dream written: $(cat "$LASTDREAM_PATH")"
echo "  Live memory/ updated: <list of changes>"
```

**Why `rm -rf` (not `rm -r`).** The `-f` suppresses errors if a subdirectory's `.tmp` orphan or other transient file disappeared between listing and removal. `rm -rf` of a contained dated dir is safe — the dir contains only audit artefacts, all of which have been transferred to live memory/ or intentionally dismissed.

**Why removal is the very last step.** If anything between Phase 5 walk-end and this point fails, the dated dir is preserved — the user can re-invoke `/dream` to resume (Phase 5 resume detection re-reads decisions.log; Phase 6 re-runs from Task 1's entry banner).
````

**Verification (operational):**

- After a successful finalisation: `ls -d <DATED_DIR>` returns "No such file or directory".
- After an aborted finalisation (e.g., forced collision or self-check failure): `ls -d <DATED_DIR>` returns the dir; its contents are intact.
<!-- END_TASK_10 -->

<!-- START_TASK_11 -->
### Task 11: Replace Phase 5 pipeline stub + commit

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — replace Phase 5's trailing `## Pipeline status (Phase 5)` block.

**Implementation:**

Replace the Phase 5 stub with:

```markdown
## Pipeline status (Phase 6)

Finalisation is in place: mirror transfer (with lastAudited bump), prune deletions, promoted moves (with collision pre-flight), MEMORY.md replacement (with type→section insertion of promoted entries), DoD #8 self-check, .tmp orphan cleanup, .last-dream timestamp write, and dated-dir removal. The full `/dream` pipeline (manual mode) is now end-to-end functional.

When invoked manually, the skill executes the full pipeline. On walk-end `y`, finalisation applies the dated-dir state to live `memory/` and removes the dated dir. On walk-end `n`, the dated dir persists for later re-entry.

Cron-integration documentation and UAT checklist land in Phase 7.
```

**Single commit for the full Phase 6 set.**

```bash
git add plugins/denubis-dream/skills/dreaming/SKILL.md
git status
git commit -m "feat(dream): Phase 6 — finalisation

Adds finalise entry (filesystem-same-device check + entry banner),
collision pre-flight (AC7.7), per-file atomic write pattern (.tmp + mv
with awk-based lastAudited bump in flat frontmatter), mirror transfer
(keep/edit/prune), promoted file move, MEMORY.md atomic replacement
with type→section heuristic insertion for promoted entries, DoD #8
self-check (grep -RE for transcript-UUID + line-range citations),
two-phase .tmp orphan cleanup (start + sanity), .last-dream timestamp
write (atomic), and dated-dir rm -rf as the very last step.

Covers AC7.1 through AC7.10 and AC8.1 through AC8.4. Operation
ordering is explicit because several steps have invariants
(collision check before any write; self-check before .last-dream;
dated-dir removal last). The /dream pipeline is now end-to-end
functional in manual mode."
```
<!-- END_TASK_11 -->
