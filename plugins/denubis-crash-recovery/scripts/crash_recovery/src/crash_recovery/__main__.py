"""crash-recovery CLI entry point.

Exposes a module-level ``app`` (typer.Typer) so tests can import it without
invoking the CLI. ``main()`` is the console-script entry point declared in
``[project.scripts]``.

Phase 1 wires the ``init`` subcommand. Phase 4 adds ``scan``. Phases 5-6 add
``render``, ``note``, ``prune``, ``triage``.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import typer

from crash_recovery import db
from crash_recovery import liveness as _liveness
from crash_recovery import scan as _scan

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


def _resolve(option_value: Path | None, env_var: str, default: str) -> Path:
    """CLI option → env var → default precedence resolver.

    Returns ``option_value`` when explicitly passed; otherwise reads
    ``env_var`` from the environment, falling back to ``default``.
    ``Path.expanduser`` is applied so ``~``-prefixed values from env or
    default expand against the caller's HOME.
    """
    if option_value is not None:
        return option_value
    return Path(os.environ.get(env_var, default)).expanduser()


@app.command()
def scan(
    db_path: Path = typer.Option(
        None,
        "--db",
        help="Path to crash-recovery SQLite DB (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db).",
    ),
    run_dir: Path = typer.Option(
        None,
        "--run-dir",
        help="Liveness-file directory (default: $CRASH_RECOVERY_RUN_DIR or ~/.claude/run).",
    ),
    projects_root: Path = typer.Option(
        None,
        "--projects-root",
        help="Projects root (default: $CRASH_RECOVERY_PROJECTS_ROOT or ~/.claude/projects).",
    ),
) -> None:
    """Walk the filesystem, classify each session, upsert to the DB."""
    if sys.platform != "linux":
        typer.echo(
            "crash-recovery scan requires Linux: reboot detection reads "
            "/proc/sys/kernel/random/boot_id, which only exists on Linux. "
            f"Detected platform: {sys.platform}.",
            err=True,
        )
        raise typer.Exit(code=2)
    ctx = _scan.ScanContext(
        db_path=_resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db"),
        run_dir=_resolve(run_dir, "CRASH_RECOVERY_RUN_DIR", "~/.claude/run"),
        projects_root=_resolve(
            projects_root, "CRASH_RECOVERY_PROJECTS_ROOT", "~/.claude/projects"
        ),
        now=int(time.time()),
    )
    try:
        _liveness.assert_local_filesystem(ctx.run_dir)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    result = _scan.run_scan(ctx)
    typer.echo(
        f"Scanned {result.sessions_scanned} sessions; "
        f"{result.sessions_reclassified} re-classified; "
        f"scan_run_id={result.scan_run_id}"
    )


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
