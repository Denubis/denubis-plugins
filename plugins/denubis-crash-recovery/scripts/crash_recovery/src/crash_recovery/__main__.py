"""crash-recovery CLI entry point.

Exposes a module-level ``app`` (typer.Typer) so tests can import it without
invoking the CLI. ``main()`` is the console-script entry point declared in
``[project.scripts]``.

Phase 1 wires the ``init`` subcommand. Phases 4-6 add ``scan``, ``render``,
``note``, ``prune``, ``triage``.
"""

from __future__ import annotations

from pathlib import Path

import typer

from crash_recovery import db

app = typer.Typer(no_args_is_help=True)


# Typer 0.25.1 requires either a command or a callback to dispatch the app.
# This no-op callback preserves `crash-recovery --help` exit-0 behaviour during
# phases that have not yet added @app.command() subcommands. Coexists with
# @app.command() decorators added in Task 5 and later phases.
@app.callback()
def _root() -> None:
    """Deterministic triage of Claude Code sessions.

    Run ``crash-recovery <subcommand> --help`` for details. Subcommands are
    wired by later phases of the implementation plan.
    """


@app.command()
def init(
    db_path: Path = typer.Option(
        None,
        "--db",
        help="Path to crash-recovery SQLite DB (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db).",
    ),
) -> None:
    """Initialise the crash-recovery SQLite database.

    Idempotent: re-running on an existing DB applies no changes because every
    DDL statement is guarded by ``CREATE … IF NOT EXISTS``. Exceptions are
    not caught — typer's default handler prints them to stderr and exits non-zero.
    """
    resolved = db_path if db_path is not None else db.default_db_path()
    db.init(resolved)
    typer.echo(f"Initialised crash-recovery DB at {resolved}")


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
