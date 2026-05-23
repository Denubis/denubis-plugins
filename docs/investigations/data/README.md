# Investigation data dumps

Raw evidence excerpts referenced from causal analyses in the parent directory.

When a causal analysis (`docs/investigations/2026-MM-DD-*-analysis.md`) cites a multi-line tool result, log span, JSONL excerpt, or other primary-data fragment that would clutter the analysis itself, drop the fragment here as a plain file and cite by relative path: `data/<name>.txt`.

## Naming

`<analysis-date>-<short-slug>.<ext>`, e.g.:

- `2026-05-23-taskupdate-stall-jsonl-excerpt.txt`
- `2026-05-23-sillytavern-stall-approver-log.jsonl`
- `2026-05-23-sed-glob-failure-stderr.txt`

## What belongs here

- JSONL line ranges that the analysis references but doesn't quote fully
- Approver log entries grouped by session
- Command outputs longer than 10 lines
- Diffs of relevant config changes (when `git diff` would be too narrow)

## What doesn't

- Conversation transcripts (use the `transcript-archive` plugin instead)
- Anything containing credentials or non-public data — investigations live in a public-by-default repo
- Per-author scratch notes that aren't cited from any analysis (use `~/.notes/` for that, not here)

## Reviewing

A peer reviewer reading an analysis here should be able to verify every cited line by opening the file in this directory. If you can't trace a claim from the analysis to a primary-data file (or to a file:line in the repo), the citation is broken — fix the analysis, not the data file.
