# denubis-token-estimator

Measure AI token/word usage from **Claude Code** and **Codex** logs, for the AI-use
disclosure section of a paper. Two real measures, never proxies:

- **output tokens** — origin-deduplicated, split into **main** (human-steered main thread)
  and **sub** (autonomous subagent fan-out);
- **human input words** — user turns with machine wrappers stripped, pasted human content
  kept.

Reported per project, rolled up from the directory, optionally by month.

> **Status: WIP (0.1.0).** The methodology is established and reproducible (every headline
> number re-derives from the live logs via `scripts/verify.py`), but the external audit
> (`docs/AUDIT-BRIEF.md`) has not yet been run. Treat numbers as corrected-pending-audit.

**Requirements:** Python ≥3.11 (stdlib only — uses `tomllib`). All log access is read-only.

## Quick start

```
/estimate                        # the project of the current directory, one total
/estimate --dir <path> --month   # one project, rolled up, per-month rows
/estimate --person <name>        # every project under a person
/estimate --all                  # every person/project
```

Or directly: `python3 scripts/estimate.py --dir <path> --month`.

## Configuration

People-roots come from `~/.token-estimator` (TOML). Without it, the tool scopes to the
local directory only.

```toml
# ~/.token-estimator
roots = ["/home/you/people", "/mnt/store/people"]
```

Each root's immediate subdirs are people; their subdirs are projects.

## The `.token-estimator` mapper (moved directories)

Drop a `.token-estimator` in a project dir to bind directories — current **and** moved —
to one canonical project, so a dir shuffle doesn't fragment its history:

```toml
person  = "Jodie"
project = "BJET-Phase1"
paths = [
  "/home/you/people/Jodie/BJET-current",   # holds this file
  "/home/you/people/Jodie/old-moved-dir",  # history-only; still matches the logs
]
```

Matching is pure longest-prefix on the **recorded cwd string**, so defunct paths still
resolve (the logs already recorded them). After each move, **append** the new path.

## Auditing

The methodology was wrong twice before it was right — both caught by reproducibility, not
by review. So nothing is final until it re-derives.

- `python3 scripts/verify.py` — re-derives every headline figure from the live logs;
  PASS/FAIL on structural invariants, `[base]` on point-in-time counts that drift.
- `docs/AUDIT-BRIEF.md` + `docs/findings.schema.json` — hand to a *different* engine
  (read-only) to falsify the assumptions independently.

## Layout

```
commands/estimate.md                  # /estimate
skills/using-token-estimator/         # methodology + usage reference (user-invocable)
scripts/verify.py                     # single source of truth: rules + audit harness
scripts/mapper.py                     # .token-estimator reader
scripts/estimate.py                   # report engine
docs/DESIGN.md                        # the 5-node methodology, corrected
docs/AUDIT-BRIEF.md                   # adversarial brief for an external engine
docs/findings.schema.json
```

All log access is **read-only** over `~/.claude/projects` and `~/.codex/sessions`.

## Not in scope

Real-time cost tracking (use `ccusage`), and anything needing session *content* — this
only counts. Antigravity logs carry no recoverable token field.
