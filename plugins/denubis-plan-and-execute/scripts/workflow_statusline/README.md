# workflow-statusline

The workflow statusline (for Claude Code and Antigravity CLI) and the
Claude/Codex/Antigravity Byobu quota cells are maintained together in
`denubis-plan-and-execute`.

## Byobu quota cells

Example:

```text
47*52 Fr 25§29 Su 32Ʌ52 Fr
```

Each cell renders as a compact dark brand-tinted tmux pill so adjacent providers
stay visually separated across Byobu's single-space gap: Claude uses dark
terracotta (`#421e0f`) with `*`, Codex uses dark graphite (`#26282e`) with `§`,
and Antigravity uses dark cerulean (`#0e3147`) with `Ʌ`. Inside each pill, the
first number is quota consumed and the second is the even-consumption pace target
scaled over local active hours (07:00–22:00). High-contrast mint green (`#86efac`)
means usage is below the target; coral red (`#ff8585`) means usage is at or above
it. The final label is the two-letter local reset weekday (`Mo`–`Su`), switching
to the 24-hour reset hour (`14h`) at 24 hours remaining and `HH:MM` (`14:30`) in
the final hour.

- `byobu-claude-quota` reads the statusline's
  `$XDG_CACHE_HOME/claude-statusline/quota-seven_day` snapshot
  (`timestamp|used_pct|resets_at`). Without `XDG_CACHE_HOME`, it uses `~/.cache`.
- `byobu-codex-quota` reads `$CODEX_HOME/state_*.sqlite` and local rollout JSONL;
  `CODEX_HOME` defaults to `~/.codex`. It considers the 16 most recently updated
  threads per state database, selects the newest main `codex` quota event by
  timestamp, and ignores independent model pools such as Spark. Legacy snapshots
  without a pool ID remain supported.
- `byobu-agy-quota` reads the statusline's
  `$XDG_CACHE_HOME/agy-statusline/quota-seven_day` snapshot
  (`timestamp|used_pct|resets_at`), written from Antigravity CLI's
  `quota.gemini-weekly` statusline payload. Without `XDG_CACHE_HOME`, it uses
  `~/.cache`.

All three commands read local files. Missing, malformed, or expired quota data
produces an empty cell. The Claude cell reports the overall weekly quota (Claude
Code 2.1.268 omits its separate Fable quota from statusline JSON, so Fable
reporting is deferred), and the Antigravity cell reports the main `gemini-weekly`
pool (ignoring separate 3p pools). The reporters do not query a quota API or
manage login credentials.

### Install

Requires Linux/Byobu, uv, and Python 3.14 or newer. From this package directory in
your `denubis-plugins` checkout or installed marketplace, run:

```fish
mkdir -p ~/.byobu/bin
ln -sfn "$PWD/byobu/30_claude_quota" ~/.byobu/bin/30_claude_quota
ln -sfn "$PWD/byobu/30_codex_quota" ~/.byobu/bin/30_codex_quota
ln -sfn "$PWD/byobu/30_agy_quota" ~/.byobu/bin/30_agy_quota
```

To feed the Antigravity snapshot (and render the workflow statusline in `agy`),
configure `statusLine` in `~/.gemini/antigravity-cli/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run --frozen --project /path/to/plugins/denubis-plan-and-execute/scripts/workflow_statusline --package workflow-statusline workflow-statusline"
  }
}
```

The launchers resolve their own symlinks and run the package through uv, regardless
of Byobu's working directory. The `30_` prefix sets a 30-second refresh interval.
These launchers replace the standalone `tmux-codex-quota` installation.

### Verify

From the repository root:

```fish
uv run --frozen --all-packages pytest plugins/denubis-plan-and-execute/scripts/workflow_statusline/tests -q
```

Run any launcher directly to inspect the tmux-formatted cell using live data.
