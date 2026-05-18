---
name: dreaming
description: Audit a project's per-project auto-memory against the historical record of Claude Code conversations. Produces a reviewable proposed-change tree under ~/.claude/projects/<slug>/memory.dream-YYYY-MM-DD/ without touching live memory during the audit.
user-invocable: true
last-reviewed: 2026-05-18
---

# denubis-dream

**Announce at start:** "I'm using the denubis-dream:dreaming skill."

## Mode detection

Inspect the invocation prompt for the literal token `--autonomous`. Two cases:

- **Autonomous mode** (the `--autonomous` token is present, e.g. the user (or the `schedule` skill) invoked `/dream --autonomous`): you do not prompt for user input at any point in the pipeline. After the autonomous-pass tail (MEMORY.md regeneration) you exit cleanly.
- **Manual mode** (no `--autonomous` token): the autonomous pass runs (or is skipped if a dated dir for today already exists), and you continue straight into the reconciliation walk in the same conversation.

If you are uncertain whether the user intended `--autonomous`, default to manual mode and ask for confirmation before proceeding to the walk. Manual mode is recoverable; autonomous mode that mistakenly skips the walk is not.

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

## Pipeline status (Phase 2)

The autonomous-pass orchestration is in place: mode detection, slug resolution, discovery scan, no-op detection, and dated-dir creation. Retrieval (Phase 3), judgement (Phase 4), reconciliation walk (Phase 5), and finalisation (Phase 6) land in subsequent phases.

When invoked at this stage, the skill executes the autonomous-pass orchestration above and prints:

> denubis-dream: discovery complete, retrieval/judgement not yet implemented. Dated dir at <path>.

…and exits.

## Reference

- Design plan: `docs/design-plans/2026-05-16-denubis-dream.md`
- Implementation plan: `docs/implementation-plans/2026-05-16-denubis-dream/`
