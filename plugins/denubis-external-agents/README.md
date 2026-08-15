# denubis-external-agents

Tooling for driving a second model as a subordinate: two worktree launchers and the
Codex supervision monitor.

| Script | What it does |
|---|---|
| `scripts/claude-ponytail` | Creates or reuses a worktree and launches Claude with Ponytail loaded for that session |
| `scripts/codex-ponytail` | Creates or reuses a worktree and launches **isolated** Codex with upstream Ponytail installed |
| `scripts/codex_supervisor.py` | Watches a joined Codex pane and drives it; see the `supervising-codex` skill |

Both launchers run the selected CLI in the current terminal. Their first argument selects
the worktree branch; every later argument is passed to Claude or Codex unchanged.

## Isolated Codex Ponytail sessions

`codex-ponytail` creates or reuses a named git worktree and launches Codex with state
isolated beneath `~/.codex-ponytail`. These sessions carry the pinned upstream
Ponytail plugin and disable every user-installed skill discovered beneath
`~/.agents/skills`.

### One-time setup

1. Run `codex-ponytail <name>` from a repository whose `.worktrees/` directory is
   gitignored.
2. Complete the isolated Codex login if prompted.
3. Open `/hooks`, review the Ponytail hooks, and trust only those you accept.
4. Close Codex and run `codex-ponytail <name>` again, so the trusted `SessionStart` hook runs
   in a new thread.

Login persists in `~/.codex-ponytail/auth.json`. Hook trust persists until a hook's
content hash changes; the audited Ponytail revision is pinned, so that normally happens
only when the pin is deliberately moved.

### Normal use

```fish
codex-ponytail <name> [<codex-args>...]
claude-ponytail <name> [<claude-args>...]
```

Each invocation verifies the Ponytail installation and refreshes the global-skill
deny-list before launching the CLI. It needs no new login or hook review.

Fish completion offers the branches of registered worktrees beneath `.worktrees/` as the
worktree selector, including after `--dry-run`. Install the completion files into Fish's
autoload directory with:

```fish
plugins/denubis-external-agents/scripts/install-ponytail-fish-completions
```

The installer writes regular files rather than checkout-dependent symlinks; rerun it after
updating these completion sources. An existing managed worktree is resolved by branch even
when its directory spelling differs, such as branch `research/proposer/verifier` at
`.worktrees/research-proposer-verifier`. A path at `.worktrees/<name>` is still refused when
it contains another branch.

New worktrees branch from the `HEAD` of the checkout where the launcher was invoked. This
means invoking it from a linked worktree creates the new branch from that worktree's current
commit. `--dry-run` is a launcher option only when it precedes the worktree name; all
arguments after the worktree name belong to the underlying CLI.

Ponytail's persistent configuration lives under `~/.codex-ponytail/xdg-config`. Normal
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
