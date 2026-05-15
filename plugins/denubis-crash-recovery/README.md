# denubis-crash-recovery

Identify and resume Claude Code sessions that ended abnormally. The plugin
classifies live, crashed, borderline, concluded, and irrecoverable sessions
deterministically from local state (liveness files, JSONL tails, live PIDs),
then renders `~/llm-resume.md` containing the resume command and reason for
each affected session. The markdown is always regenerated from the SQLite
database — never edited by hand — so regeneration is byte-identical given the
same inputs.

## Installation

```bash
claude plugin install denubis-crash-recovery@brian-ed3d-plugins
```

## Dependency

This plugin depends on the `claude-wrapper.sh` liveness-file behaviour shipped
by `denubis-plan-and-execute`. Crash detection requires
`denubis-plan-and-execute >= TBD-PHASE-8`.

Phase 8 of the implementation plan wires the wrapper patch in
`denubis-plan-and-execute` to write the liveness file on session start and
remove it on clean exit. Until that wrapper patch lands, this plugin's
`scan` and `triage` flows will see zero liveness files and classify every
session as `concluded`. The CLI surface (`init`, schema, render, note, prune)
is functional in v0.1.0 — only the live/crash signal depends on the wrapper
patch.

## Usage

Run triage to scan sessions, classify them, and regenerate `~/llm-resume.md`:

```bash
crash-recovery triage
```

Other subcommands (`init`, `scan`, `render`, `note`, `prune`) are documented
under `crash-recovery --help` and land incrementally across Phases 1–6 of the
implementation plan.

## Database

State lives in `~/.claude/crash-recovery.db` (SQLite, WAL journal mode).
Override the path with the `CRASH_RECOVERY_DB` environment variable. Run
`crash-recovery init` once to create the schema; the command is idempotent
and safe to re-run.

## Status

v0.1.0 ships the plugin scaffold, SQLite schema, and `crash-recovery init`
subcommand. The wrapper-patch dependency on `denubis-plan-and-execute` lands
in Phase 8 of the implementation plan, at which point crash detection
becomes operational end-to-end.
