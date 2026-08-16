---
description: Estimate AI token/word usage for a project, optionally by month or exact time window
allowed-tools: Bash
argument-hint: "[--dir <path> | --person <name> | --all] [--month | --start <ISO> --end <ISO>] [--csv <file>]"
---

# /estimate — AI token / word usage

Run the estimator and present its table to the user. Execute via Bash:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/estimate.py" $ARGUMENTS
```

(If `${CLAUDE_PLUGIN_ROOT}` is not set in your shell, resolve it to this plugin's
installed directory — the `scripts/estimate.py` under `denubis-token-estimator`.)

**Scope** (mutually exclusive; default is the current directory's project):
- no flag, or `--dir <path>` — one project, resolved by rolling up `<path>` (or cwd)
  through its `.token-estimator` mapper.
- `--person <name>` — every project under a person.
- `--all` — every person/project.

**Modifiers:** `--month` adds a per-month breakdown. Paired timezone-aware `--start`
and `--end` select one inclusive/exclusive interval `[start, end)` and cannot be used
with `--month`. `--csv <file>` also writes the tidy
`(source, person, project, month)` leaf grain.

**What it reports** (reproducible methodology — see the
`using-token-estimator` skill):
- **output tokens**, origin-deduplicated, split into **main** (human-steered main
  thread) and **sub** (autonomous subagent fan-out);
- **human input words**, with machine wrappers stripped and pasted human content kept.

Present the table as-is; call out the subagent share and the human-word total. The grand
total equals the sum of the monthly rows by construction. If a figure looks surprising,
re-derive the headline numbers from the live logs with
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"`.

People-roots come from `~/.token-estimator`; without it the tool scopes to the local
directory. This is read-only over `~/.claude` and `~/.codex` logs.
