# workflow-statusline

Claude Code's workflow statusline and the Claude/Codex Byobu quota cells are
maintained together in `denubis-plan-and-execute`.

## Byobu quota cells

Example:

```text
47*52 Fri 25 29 Sun
```

Each cell shows quota consumed, then the even-consumption pace target scaled over
local active hours (07:00–22:00). Green means usage is below the target; red means
usage is at or above it. Claude uses `*` between the numbers; Codex uses a space.
The final label is the local reset weekday. At 24 hours remaining it switches to
the local reset time in 24-hour format, such as `14:30`.

- `byobu-claude-quota` reads the statusline's
  `$XDG_CACHE_HOME/claude-statusline/quota-seven_day` snapshot
  (`timestamp|used_pct|resets_at`). Without `XDG_CACHE_HOME`, it uses `~/.cache`.
- `byobu-codex-quota` reads `$CODEX_HOME/state_*.sqlite` and local rollout JSONL;
  `CODEX_HOME` defaults to `~/.codex`. It considers the 16 most recently updated
  threads per state database, selects the newest main `codex` quota event by
  timestamp, and ignores independent model pools such as Spark. Legacy snapshots
  without a pool ID remain supported.

Both commands read local files. Missing, malformed, or expired quota data produces
an empty cell. The Claude cell reports the overall weekly quota: Claude Code
2.1.268 omits its separate Fable quota from statusline JSON, so Fable reporting is
deferred. The reporters do not query a quota API or manage login credentials.

### Install

Requires Linux/Byobu, uv, and Python 3.14 or newer. From this package directory in
your `denubis-plugins` checkout or installed marketplace, run:

```fish
mkdir -p ~/.byobu/bin
ln -sfn "$PWD/byobu/30_claude_quota" ~/.byobu/bin/30_claude_quota
ln -sfn "$PWD/byobu/30_codex_quota" ~/.byobu/bin/30_codex_quota
```

The launchers resolve their own symlinks and run the package through uv, regardless
of Byobu's working directory. The `30_` prefix sets a 30-second refresh interval.
These launchers replace the standalone `tmux-codex-quota` installation.

### Verify

From the repository root:

```fish
uv run --frozen --all-packages pytest plugins/denubis-plan-and-execute/scripts/workflow_statusline/tests -q
```

Run either launcher directly to inspect the tmux-formatted cell using live data.
