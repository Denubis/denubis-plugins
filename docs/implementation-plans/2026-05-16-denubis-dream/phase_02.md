# denubis-dream Implementation Plan — Phase 2: Autonomous-pass orchestration

**Goal:** `/dream` (with or without `--autonomous`) detects its mode, resolves the main project slug, runs the anchored slug-prefix discovery scan, creates today's dated dir if absent, and exits with a "discovery complete, retrieval/judgement not yet implemented" stub.

**Architecture:** Extend the Phase 1 `skills/dreaming/SKILL.md` with five new sections (Mode detection → Project slug resolution → Discovery → Dated dir creation → No-op detection). All operations are Bash + skill text — no Python helpers (design DR1). Slug resolution uses `git rev-parse --show-toplevel` so the command works from any subdirectory of the repo/worktree.

**Tech Stack:** Bash (`sed`, `grep -E`, `mkdir -p`, `git rev-parse`), Claude Code skill text.

**Scope:** Phase 2 of 7.

**Codebase verified:** 2026-05-17 (codebase-investigator confirmed: Claude Code slug rule is "remove leading `/`, prepend `-`, replace `/` with `-`"; worktree slug pattern is `<main>--worktrees-<name>`; `~/.claude/projects/` contains no suffix-collision candidates for this repo's main slug; `jq` available).

**Phase Type:** functionality

**Cascading correction from earlier finding:** The design plan's `frontmatter.metadata.lastAudited` references should be read as `frontmatter.lastAudited` (flat, no `metadata:` nesting). The flat shape aligns with the user's global CLAUDE.md frontmatter convention; existing memory files have no `lastAudited` field in any form (flat or nested) — this plugin invents the field at first finalisation. The "convention" being followed is the user's stated preference, not pre-existing precedent in memory files. This affects Phase 3 (windowing) and Phase 6 (finalisation). Phase 2 is unaffected — no frontmatter writes happen here.

---

## Acceptance Criteria Coverage

This phase implements and verifies:

### denubis-dream.AC2: Mode detection and discovery
- **denubis-dream.AC2.1 Success:** `/dream` (no flag) detects manual mode and resolves the main project slug from `cwd` (strips `/.worktrees/<name>` if present).
- **denubis-dream.AC2.2 Success:** `/dream --autonomous` detects autonomous mode and proceeds without prompting at any point.
- **denubis-dream.AC2.3 Success:** Anchored slug scan matches exactly `^<main>$` or `^<main>--worktrees-.+$` under `~/.claude/projects/`. A sibling directory with a suffix-collision name (e.g., `<main>-2`) is *not* included.
- **denubis-dream.AC2.4 Success:** Anchored slug scan also finds slugs of pruned worktrees whose transcript dirs still exist (the worktree was removed but `~/.claude/projects/<main>--worktrees-<name>/` persists).
- **denubis-dream.AC2.5 Failure:** Invoked outside any project directory: `/dream` reports unable to resolve main slug and exits cleanly (no dated dir created).

**Note on the design's "Done when":** Phase 2's design text says "Covers `denubis-dream.AC1.*` (mode detection)" — this is a design typo. AC1 covers plugin discoverability (Phase 1); AC2 covers mode detection and discovery. The implementation plan corrects to AC2.

---

<!-- START_TASK_1 -->
### Task 1: `## Mode detection` section

**Verifies:** denubis-dream.AC2.1, denubis-dream.AC2.2

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append new section after `## Scaffold status` (and remove `## Scaffold status` once the section list grows — Task 6 handles the stub replacement).

**Implementation:**

Add a `## Mode detection` section explaining how the skill detects whether `--autonomous` was passed.

The slash-command invocation surfaces the argument string in the user's prompt to Claude (Claude Code passes through arguments to the invoked skill/command). The skill MUST inspect the actual invocation prompt verbatim — looking for the literal token `--autonomous` (case-sensitive) bordered by whitespace or end-of-string.

The section text (skill content):

```markdown
## Mode detection

Inspect the invocation prompt for the literal token `--autonomous`. Two cases:

- **Autonomous mode** (the `--autonomous` token is present, e.g. the user (or the `schedule` skill) invoked `/dream --autonomous`): you do not prompt for user input at any point in the pipeline. After the autonomous-pass tail (MEMORY.md regeneration) you exit cleanly.
- **Manual mode** (no `--autonomous` token): the autonomous pass runs (or is skipped if a dated dir for today already exists), and you continue straight into the reconciliation walk in the same conversation.

If you are uncertain whether the user intended `--autonomous`, default to manual mode and ask for confirmation before proceeding to the walk. Manual mode is recoverable; autonomous mode that mistakenly skips the walk is not.
```

**Why describe rather than code:** mode detection is a one-line conditional that depends on the actual invocation surface. The skill's prose is the deterministic check.

**Verification (operational):**

After Task 6's stub replacement, invoke `/dream` and confirm the skill announces "manual mode"; invoke `/dream --autonomous` and confirm it announces "autonomous mode".
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `## Project slug resolution` section

**Verifies:** denubis-dream.AC2.1 (slug resolution side), denubis-dream.AC2.5 (failure mode)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Mode detection`.

**Implementation:**

Add a `## Project slug resolution` section. The skill uses `git rev-parse --show-toplevel` to get the worktree root (so the command works from any subdirectory), then strips `/.worktrees/<name>` if present, then applies the slug transformation.

The section text:

````markdown
## Project slug resolution

Resolve the **main project slug** (the slug Claude Code uses for the repo root, not a worktree) using the following Bash pipeline:

```bash
# 1. Get the worktree root (may be the main repo or a worktree)
GIT_TOP=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$GIT_TOP" ]; then
  echo "denubis-dream: unable to resolve project slug — not inside a git repository. Exiting." >&2
  exit 0   # AC2.5: clean exit, no dated dir created
fi

# 2. Strip /.worktrees/<name> if present (only at end of path)
MAIN_PATH=$(printf '%s' "$GIT_TOP" | sed -E 's|/\.worktrees/[^/]+$||')

# 3. Apply Claude Code slug rule: remove leading slash, prepend '-', replace / with -
MAIN_SLUG=$(printf '%s' "$MAIN_PATH" | sed -E 's|^/||; s|/|-|g; s|^|-|')

# Sanity: the resolved memory dir must already exist OR we are about to create it
MAIN_DIR=~/.claude/projects/"$MAIN_SLUG"
echo "denubis-dream: main slug = $MAIN_SLUG"
echo "denubis-dream: main dir = $MAIN_DIR"
```

**Worked example.**
- `pwd` = `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/plugins/foo`
- `git rev-parse --show-toplevel` → `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream`
- After `.worktrees/<name>` strip → `/home/brian/people/Brian/brian-ed3d-plugins`
- After slug transformation → `-home-brian-people-Brian-brian-ed3d-plugins`

**Failure mode (AC2.5).** If `git rev-parse --show-toplevel` returns empty (the user is outside any git repo), the skill prints a single-line message and exits with status 0 — no dated dir is created.

**Edge cases.**
- User has a non-`.worktrees/` worktree (e.g., `~/wt/foo`). The strip is a no-op; the slug derives from the worktree path itself. This means the main slug will differ from the actual main repo's slug — `/dream` will operate against this worktree's slug. This is acceptable behaviour: the design's worktree-derived discovery is scoped to repos that use the `.worktrees/` convention.
- User is in the main repo (no worktree). The strip is a no-op; the slug derives from the repo root directly.
````

**Verification (operational):**

After Task 6, invoke `/dream` from three locations and confirm the printed `MAIN_SLUG` is correct in each:

1. Worktree root: `cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream && /dream` → expects `-home-brian-people-Brian-brian-ed3d-plugins`
2. Worktree subdir: `cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/plugins && /dream` → expects same slug
3. Outside any git repo: `cd /tmp && /dream` → expects clean exit with "unable to resolve project slug" message; no dated dir created (AC2.5).
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: `## Discovery` section

**Verifies:** denubis-dream.AC2.3, denubis-dream.AC2.4

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Project slug resolution`.

**Implementation:**

Add a `## Discovery` section that scans `~/.claude/projects/` using the anchored regex from design DR7.

The section text:

````markdown
## Discovery

Scan `~/.claude/projects/` for slugs matching the anchored pattern. Both the main slug and any worktree-derived slugs (including those whose worktrees have been pruned but whose transcript dirs survive) qualify.

```bash
# MAIN_SLUG comes from the previous section
# The anchored regex matches exactly the main slug OR <main>--worktrees-<anything>
DISCOVERED_SLUGS=$(ls -1 ~/.claude/projects/ 2>/dev/null \
  | grep -E "^${MAIN_SLUG}\$|^${MAIN_SLUG}--worktrees-.+\$" \
  || true)

if [ -z "$DISCOVERED_SLUGS" ]; then
  echo "denubis-dream: no transcript dirs discovered for slug $MAIN_SLUG — first session?" >&2
  # This is not fatal; the autonomous pass can still proceed with no transcripts.
fi

echo "denubis-dream: discovered slugs:"
printf '%s\n' "$DISCOVERED_SLUGS"
```

**Anchoring is structural, not aesthetic.** Without the leading `^` and trailing `$`, a sibling project whose slug happens to start with the main slug (e.g., `-home-brian-people-Brian-brian-ed3d-plugins-experimental`) would be picked up and its transcripts treated as in-scope for this audit — leaking unrelated session data into Phase 3's evidence retrieval. The codebase-investigator confirmed no such collisions currently exist in this user's `~/.claude/projects/`, but the anchoring is defence-in-depth against future projects.

**Pruned worktrees (AC2.4).** A worktree that has been `git worktree remove`d still leaves its `~/.claude/projects/<main>--worktrees-<name>/` transcript dir behind. The anchored regex picks these up by design — the worktree no longer exists on disk, but its session history is still relevant to the audit.

**Output contract.** Set `DISCOVERED_SLUGS` as a newline-separated list of slug names (not full paths). Subsequent sections derive `~/.claude/projects/<slug>/` paths from each entry when they need to read transcripts.
````

**Verification (operational):**

After Task 6, invoke `/dream` from the worktree and confirm the printed `DISCOVERED_SLUGS` includes:
1. `-home-brian-people-Brian-brian-ed3d-plugins` (main)
2. `-home-brian-people-Brian-brian-ed3d-plugins--worktrees-denubis-dream` (this worktree)
3. Any other `--worktrees-<name>` slugs that exist (codebase-investigator found: `crash-recovery`, `research-proposer-verifier`, `skill-skills-upstream-sync`)

Confirm no unrelated slugs (e.g., other repos under `~/.claude/projects/`) appear.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: `## Dated dir creation` section

**Verifies:** scaffolding for AC3.* and AC4.* (no direct AC of its own — the dated dir is the substrate for those phases)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Discovery`.

**Implementation:**

Add a `## Dated dir creation` section that proactively creates today's dated dir (with `flagged/` and `promoted/` subdirs) under the main slug's transcript directory.

The section text:

````markdown
## Dated dir creation

Create today's dated audit directory under the main slug's transcript dir, with both subdirs pre-created so subsequent phases can `Write` into them without race conditions.

```bash
TODAY=$(date +%Y-%m-%d)
DATED_DIR=~/.claude/projects/"$MAIN_SLUG"/memory.dream-"$TODAY"

mkdir -p "$DATED_DIR"/flagged "$DATED_DIR"/promoted

echo "denubis-dream: dated dir = $DATED_DIR"
```

**`flagged/` is always created** even when the corpus-wide subagent (Phase 3) finds no memory-worthy regions to flag. Its emptiness at walk time is a valid state.

**`promoted/` is always created** even when no flagged region is promoted during reconciliation. Same reasoning.

**ISO date format (`%Y-%m-%d`).** The date is a substring of the directory name and must sort lexically — `2026-05-17` sorts correctly between `2026-05-16` and `2026-05-18`. No timezone is included; the date is taken in the system's local timezone at the moment the autonomous pass starts.

**One dated dir per day.** Re-invoking `/dream` on the same day reuses today's dir (see `## No-op detection`).
````

**Verification (operational):**

After Task 6, invoke `/dream` and confirm:
1. `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory.dream-YYYY-MM-DD/` exists (with today's date).
2. `flagged/` and `promoted/` subdirs exist and are empty.
3. Re-invoke `/dream` immediately — confirm the existing dir is reused (no error, no double-create) and the no-op message (Task 5) appears.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `## No-op detection` section

**Verifies:** denubis-dream.AC9.3 (cron no-op), foundational behaviour for AC5.7 (resume) — full resume is implemented in Phase 5; this task lays the detection foundation.

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — insert **before** `## Dated dir creation` so it can short-circuit before the mkdir.

**Implementation:**

Add a `## No-op detection` section that checks for an existing dated dir before creating one.

The section text:

````markdown
## No-op detection

Before creating today's dated dir, check whether one already exists for this main slug. Two cases:

```bash
TODAY=$(date +%Y-%m-%d)
DATED_DIR=~/.claude/projects/"$MAIN_SLUG"/memory.dream-"$TODAY"

if [ -d "$DATED_DIR" ]; then
  if [ "$MODE" = "autonomous" ]; then
    echo "denubis-dream: dated dir already exists for today: $DATED_DIR — exiting cleanly (no-op)."
    exit 0   # AC9.3
  else
    echo "denubis-dream: existing dated dir found — resuming reconciliation walk."
    # Manual mode + existing dir: jump to the reconciliation walk entry.
    # See ## Walk entry (Phase 5).
    # For Phase 2 scaffolding the jump is a print-and-exit stub:
    echo "denubis-dream: (Phase 2 stub) reconciliation walk lands in Phase 5."
    exit 0
  fi
fi
```

**Autonomous mode + existing dir = no-op.** The cron-driven invocation must not overwrite an in-progress reconciliation. AC9.3 requires the existing path be printed and the command exit cleanly.

**Manual mode + existing dir = resume.** Re-invoking `/dream` interactively when a dated dir exists is the user's "let me pick up where I left off" gesture. Phase 5 implements the actual walk-resume; Phase 2's stub just prints a placeholder so the integration point is exercised.

**No dir exists.** Fall through to `## Dated dir creation`. The autonomous pass proceeds.
````

**Verification (operational):**

After Task 6:

1. Delete any existing dated dir: `rm -rf ~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory.dream-$(date +%Y-%m-%d)/`
2. Invoke `/dream --autonomous` — confirm creation happens (no no-op message).
3. Invoke `/dream --autonomous` again — confirm AC9.3: the existing-path message prints and the command exits without re-creating anything.
4. Invoke `/dream` (no flag) — confirm the manual-mode reconciliation-stub message prints (Phase 5 will replace the stub with the actual walk).
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Replace scaffold stub with Phase 2 pipeline stub + commit

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — remove the Phase 1 `## Scaffold status` section; replace the trailing print with the Phase 2 stub.

**Implementation:**

After Tasks 1-5 have appended their sections (Mode detection → Project slug resolution → No-op detection → Dated dir creation → Discovery), the skill body should end with a clear "Phase 2 boundary" stub announcing the autonomous pass is structurally complete but retrieval/judgement (Phase 3+) has not yet been implemented.

Remove the Phase 1 `## Scaffold status` section entirely. Replace the trailing `denubis-dream:dreaming — scaffold ready, behaviour not yet implemented.` line with:

```markdown
## Pipeline status (Phase 2)

The autonomous-pass orchestration is in place: mode detection, slug resolution, discovery scan, no-op detection, and dated-dir creation. Retrieval (Phase 3), judgement (Phase 4), reconciliation walk (Phase 5), and finalisation (Phase 6) land in subsequent phases.

When invoked at this stage, the skill executes the autonomous-pass orchestration above and prints:

> denubis-dream: discovery complete, retrieval/judgement not yet implemented. Dated dir at <path>.

…and exits.
```

**Single commit for the full Phase 2 set.** Per `feedback_commit-cadence.md`, bundle the section additions and stub replacement in one commit.

```bash
git add plugins/denubis-dream/skills/dreaming/SKILL.md
git status   # sanity-check: only SKILL.md modified
git commit -m "feat(dream): Phase 2 — autonomous-pass orchestration

Adds the mode-detection, slug-resolution, discovery, dated-dir-creation,
and no-op-detection sections to the dreaming skill. /dream now resolves
the main slug via git rev-parse, scans ~/.claude/projects/ with an
anchored regex (per design DR7), and creates today's dated dir with
flagged/ and promoted/ subdirs. Retrieval and judgement land in
subsequent phases.

Covers AC2.1 through AC2.5. Cron no-op covered (AC9.3 stub).
Design typo: Phase 2 'Done when' cites AC1; actual coverage is AC2."
```
<!-- END_TASK_6 -->
