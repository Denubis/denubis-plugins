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

## Pipeline status (Phase 2)

The autonomous-pass orchestration is in place: mode detection, slug resolution, discovery scan, no-op detection, and dated-dir creation. Retrieval (Phase 3), judgement (Phase 4), reconciliation walk (Phase 5), and finalisation (Phase 6) land in subsequent phases.

When invoked at this stage, the skill executes the autonomous-pass orchestration above and prints:

> denubis-dream: discovery complete, retrieval/judgement not yet implemented. Dated dir at <path>.

…and exits.

## Reference

- Design plan: `docs/design-plans/2026-05-16-denubis-dream.md`
- Implementation plan: `docs/implementation-plans/2026-05-16-denubis-dream/`
