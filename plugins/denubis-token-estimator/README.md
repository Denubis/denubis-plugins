# denubis-token-estimator

Measure AI token/word usage from **Claude Code** and **Codex** logs, for the AI-use
disclosure section of a paper. Two real measures, never proxies:

- **output tokens** — origin-deduplicated, split into **main** (human-steered main thread)
  and **sub** (autonomous subagent fan-out);
- **human input words** — user turns with machine wrappers stripped, pasted human content
  kept.

Reported per project, rolled up from the directory, optionally by month or by an
exact timezone-aware interval.

> **Status: WIP (0.2.0).** Fixture tests and the live verifier exercise the implemented
> methodology, but the independent audit in `docs/AUDIT-BRIEF.md` remains pending.
> Treat publication numbers as corrected-pending-audit.

**Requirements:** Python ≥3.14 (stdlib only — uses `tomllib`). All log access is read-only.

## Quick start

```
/estimate                        # the project of the current directory, one total
/estimate --dir <path> --month   # one project, rolled up, per-month rows
/estimate --dir <path> --start <ISO> --end <ISO>
/estimate --person <name>        # every project under a person
/estimate --all                  # every person/project
```

Or invoke `scripts/estimate.py` directly. Exact windows use `[start, end)` and require
an explicit UTC offset or `Z`; they cannot be combined with `--month`.

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

Use the live verifier to check the implementation and a separate audit actor to attack
the method itself.

- `python3 scripts/verify.py` — re-derives every headline figure from the live logs;
  PASS/FAIL on structural invariants, `[base]` on point-in-time counts that drift.
- `docs/AUDIT-BRIEF.md` + `docs/findings.schema.json` — give the brief, but not the
  evaluator-only `docs/AUDIT-ORACLE.md`, to a different engine for a read-only audit.

## Layout

```
commands/estimate.md                  # /estimate
skills/using-token-estimator/         # methodology + usage reference (user-invocable)
scripts/verify.py                     # single source of truth: rules + audit harness
scripts/mapper.py                     # .token-estimator reader
scripts/estimate.py                   # report engine
docs/DESIGN.md                        # current methodology and limitations
docs/AUDIT-BRIEF.md                   # adversarial brief for an external engine
docs/AUDIT-ORACLE.md                  # evaluator answers; never give to audit actor
docs/findings.schema.json
```

All log access is **read-only** over `~/.claude/projects` and `~/.codex/sessions`.

## Not in scope

Real-time cost tracking (use `ccusage`), and anything needing session *content* — this
only counts. Antigravity logs carry no recoverable token field.
