# denubis-external-agents

Tooling for driving a second model as a subordinate: two worktree launchers and the
Codex supervision monitor.

| Script | What it does |
|---|---|
| `scripts/claude-ponytail` | Reuses the caller checkout or selects a worktree and launches Claude with audited Ponytail loaded for that session |
| `scripts/codex-ponytail` | Reuses the caller checkout or selects a worktree and launches **isolated** Codex with audited Ponytail installed |
| `scripts/codex_supervisor.py` | Watches a joined Codex pane and drives it; see the `supervising-codex` skill |

Both launchers run the selected CLI in the current terminal. Their first argument selects
the branch. If that is the branch checked out where the command was invoked, the launcher
uses that checkout directly. Otherwise it reuses or creates a worktree. Every later
argument is passed to Claude or Codex unchanged.

## Isolated Codex Ponytail sessions

`codex-ponytail` launches Codex with state isolated beneath `~/.codex-ponytail`. These
sessions carry an exact checkout of the audited upstream Ponytail commit and disable every
user-installed skill discovered beneath `~/.agents/skills`.

The launcher installs that checkout through a stable local Codex marketplace. When the
audited SHA in the launcher changes, the next invocation fetches, installs, and verifies
the new checkout automatically. No separate marketplace-upgrade command is required. The
first invocation after this change installs the local plugin before retiring the previous
remote marketplace, so a failed migration leaves the previous installation intact.

### One-time setup

1. Run `codex-ponytail <branch>`. If selecting a different branch may create a worktree,
   the repository's `.worktrees/` directory must be gitignored.
2. Complete the isolated Codex login if prompted.
3. Open `/hooks`, review the Ponytail hooks, and trust only those you accept.
4. Close Codex and run `codex-ponytail <name>` again, so the trusted `SessionStart` hook runs
   in a new thread.

Login persists in `~/.codex-ponytail/auth.json`. The one-time migration changes the Codex
plugin identity from `ponytail@ponytail` to `ponytail@ponytail-pinned`, so review `/hooks`
again after it. Thereafter hook trust persists until a hook's content hash changes; that
normally happens only when the audited pin deliberately moves.

### Normal use

```fish
codex-ponytail <name> [<codex-args>...]
claude-ponytail <name> [<claude-args>...]
```

Each invocation verifies both the audited checkout and Codex's installed copy, then
refreshes the global-skill deny-list before launching the CLI. It needs no new login or
hook review unless the hook content changed.

Fish completion offers every local branch, including the caller checkout and branches not
yet attached to a worktree, including after `--dry-run`. Install the completion files into
Fish's autoload directory with:

```fish
plugins/denubis-external-agents/scripts/install-ponytail-fish-completions
```

The installer writes regular files rather than checkout-dependent symlinks; rerun it after
updating these completion sources. The checkout where the launcher was invoked wins when
it already has the selected branch. Otherwise an existing managed worktree is resolved by
branch even when its directory spelling differs, such as branch
`research/proposer/verifier` at `.worktrees/research-proposer-verifier`. A path at
`.worktrees/<name>` is still refused when it contains another branch.
An unqualified name that uniquely matches an existing qualified branch is refused with
the full-name suggestion rather than silently creating a second branch.

New worktrees branch from the `HEAD` of the checkout where the launcher was invoked. This
means invoking it from a linked worktree creates the new branch from that worktree's current
commit. `--dry-run` is a launcher option only when it precedes the worktree name; all
arguments after the worktree name belong to the underlying CLI.

Ponytail's persistent configuration lives under `~/.codex-ponytail/xdg-config`; its
audited checkout and local marketplace live under `~/.codex-ponytail/marketplace`. Normal
Codex, Claude Ponytail, `~/.codex`, and normal XDG configuration are untouched.

### What the launcher writes into the isolated config

Two sections, each marked with a comment naming this script as the author:

- `[tui]` — a status line and terminal title, so a supervisor can read Codex's state.
  `context-remaining` in the status line is what the supervisor's context floor reads.
- `[sandbox_workspace_write]` — network access so a package index is reachable, and
  `writable_roots` for the uv and npm caches so they are reused rather than refilled into
  the sandbox's private tmp on every run.

A section **without** that marker comment is treated as yours and left alone. A section
**with** it is upgraded when the launcher gains a key it did not previously write, which
is why the marker exists: without it, a config written before a grant was added could
never receive that grant. That defect was live between 2026-08-06 and 2026-08-08.

## Tests

```sh
bats tests/test_codex_ponytail.bats
bats tests/test_claude_ponytail.bats
```

Both suites are hermetic: they run against a fake Codex binary in
`tests/fixtures/fake_codex` and a temporary HOME, and touch no real Codex or Claude
state.
