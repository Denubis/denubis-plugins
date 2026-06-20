"""crash-recovery CLI entry point.

Exposes a module-level ``app`` (typer.Typer) so tests can import it without
invoking the CLI. ``main()`` is the console-script entry point declared in
``[project.scripts]``.

Phase 1 wires the ``init`` subcommand. Phase 4 adds ``scan``. Phases 5-6 add
``render``, ``note``, ``prune``, ``triage``.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import typer

from crash_recovery import db
from crash_recovery import history as _history
from crash_recovery import list_live as _list_live
from crash_recovery import liveness as _liveness
from crash_recovery import note as _note
from crash_recovery import prune as _prune
from crash_recovery import render as _render
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
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
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
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
    run_dir: Path = typer.Option(
        None,
        "--run-dir",
        help=(
            "Liveness-file directory"
            " (default: $CRASH_RECOVERY_RUN_DIR or ~/.claude/run)."
        ),
    ),
    projects_root: Path = typer.Option(
        None,
        "--projects-root",
        help=(
            "Projects root"
            " (default: $CRASH_RECOVERY_PROJECTS_ROOT or ~/.claude/projects)."
        ),
    ),
    resurrect_dir: Path = typer.Option(
        None,
        "--resurrect-dir",
        help=(
            "tmux-resurrect snapshot dir"
            " (default: $CRASH_RECOVERY_RESURRECT_DIR or ~/.byobu-sessions)."
        ),
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
        resurrect_dir=_resolve(
            resurrect_dir, "CRASH_RECOVERY_RESURRECT_DIR", "~/.byobu-sessions"
        ),
    )
    try:
        _liveness.assert_local_filesystem(ctx.run_dir)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    result = _scan.run_scan(ctx)
    typer.echo(
        f"Scanned {result.sessions_scanned} sessions; "
        f"{result.sessions_reclassified} re-classified (orphans/version-stale); "
        f"scan_run_id={result.scan_run_id}"
    )


def _build_scan_ctx_and_run(
    db_path: Path | None,
    run_dir: Path | None,
    projects_root: Path | None,
    resurrect_dir: Path | None = None,
) -> _scan.ScanContext:
    """Resolve scan options, apply Linux + local-filesystem guards, then scan.

    Replicates the guard sequence from the ``scan`` subcommand so the
    composite commands (``triage``, ``regenerate``) reject the same
    environments at the same exit code (2). Returns the :class:`ScanContext`
    that was used so callers can re-open the DB path for rendering.
    """
    if sys.platform != "linux":
        typer.echo(
            "crash-recovery requires Linux: reboot detection reads "
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
        resurrect_dir=_resolve(
            resurrect_dir, "CRASH_RECOVERY_RESURRECT_DIR", "~/.byobu-sessions"
        ),
    )
    try:
        _liveness.assert_local_filesystem(ctx.run_dir)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    _scan.run_scan(ctx)
    return ctx


def _render_to_file(db_path: Path, output: Path) -> int:
    """Render ``db_path``'s markdown and write atomically to ``output``.

    Returns the count of rows in the ``sessions`` table for the user-visible
    confirmation line. The tempfile is created in ``output.parent`` so the
    final :func:`os.replace` stays on the same filesystem (cross-device
    ``os.replace`` would silently degrade to a copy-and-unlink, defeating
    the atomicity guarantee).

    Raises :exc:`RuntimeError` if ``output.parent`` is on a network or union
    filesystem (same guard as Phase 4's ``run_dir`` check). Set
    ``CRASH_RECOVERY_RESUME_PATH`` to a path on a local filesystem to resolve.
    """
    _liveness.assert_local_filesystem(output.parent)
    content, n = _render.render(db_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(output)
    return n


@app.command()
def render(
    db_path: Path = typer.Option(
        None,
        "--db",
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
    output: Path = typer.Option(
        None,
        "--output",
        help=(
            "Path to the rendered markdown file"
            " (default: $CRASH_RECOVERY_RESUME_PATH or ~/llm-resume.md)."
        ),
    ),
) -> None:
    """Render the crash-recovery DB to a markdown file.

    The DB is opened read-only. The output file is written atomically via
    ``tempfile + os.replace`` so an interrupted write cannot leave a
    partially-rendered file at the destination path.
    """
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    resolved_out = _resolve(output, "CRASH_RECOVERY_RESUME_PATH", "~/llm-resume.md")
    try:
        count = _render_to_file(resolved_db, resolved_out)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"Rendered {count} sessions to {resolved_out}")


@app.command()
def triage(
    db_path: Path = typer.Option(
        None,
        "--db",
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
    run_dir: Path = typer.Option(
        None,
        "--run-dir",
        help=(
            "Liveness-file directory"
            " (default: $CRASH_RECOVERY_RUN_DIR or ~/.claude/run)."
        ),
    ),
    projects_root: Path = typer.Option(
        None,
        "--projects-root",
        help=(
            "Projects root"
            " (default: $CRASH_RECOVERY_PROJECTS_ROOT or ~/.claude/projects)."
        ),
    ),
    resurrect_dir: Path = typer.Option(
        None,
        "--resurrect-dir",
        help=(
            "tmux-resurrect snapshot dir"
            " (default: $CRASH_RECOVERY_RESURRECT_DIR or ~/.byobu-sessions)."
        ),
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show the full all-means-all roster. Default is the lean view: "
        "crash victims and active/ambiguous sessions in full, with concluded, "
        "irrecoverable, and unrecognised-ending sessions collapsed to counts.",
    ),
) -> None:
    """Scan the filesystem, then print the rendered report to stdout.

    Composite of ``scan`` + ``render``-to-stdout. Same Linux + local-filesystem
    guards as ``scan``. The terminal read is lean by default — "what crashed" is
    a glance; pass ``--all`` for the full roster (also always in ``~/llm-resume.md``).
    """
    ctx = _build_scan_ctx_and_run(db_path, run_dir, projects_root, resurrect_dir)
    content, _ = _render.render(ctx.db_path, show_all=show_all)
    typer.echo(content, nl=False)


@app.command()
def regenerate(
    db_path: Path = typer.Option(
        None,
        "--db",
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
    run_dir: Path = typer.Option(
        None,
        "--run-dir",
        help=(
            "Liveness-file directory"
            " (default: $CRASH_RECOVERY_RUN_DIR or ~/.claude/run)."
        ),
    ),
    projects_root: Path = typer.Option(
        None,
        "--projects-root",
        help=(
            "Projects root"
            " (default: $CRASH_RECOVERY_PROJECTS_ROOT or ~/.claude/projects)."
        ),
    ),
    resurrect_dir: Path = typer.Option(
        None,
        "--resurrect-dir",
        help=(
            "tmux-resurrect snapshot dir"
            " (default: $CRASH_RECOVERY_RESURRECT_DIR or ~/.byobu-sessions)."
        ),
    ),
    output: Path = typer.Option(
        None,
        "--output",
        help=(
            "Path to the rendered markdown file"
            " (default: $CRASH_RECOVERY_RESUME_PATH or ~/llm-resume.md)."
        ),
    ),
) -> None:
    """Scan the filesystem, then write the rendered report to the output file.

    Composite of ``scan`` + ``render``-to-file. Uses the same atomic-write
    path as the standalone ``render`` subcommand so an interrupted write
    cannot leave a partial markdown file at the destination.
    """
    ctx = _build_scan_ctx_and_run(db_path, run_dir, projects_root, resurrect_dir)
    resolved_out = _resolve(output, "CRASH_RECOVERY_RESUME_PATH", "~/llm-resume.md")
    try:
        count = _render_to_file(ctx.db_path, resolved_out)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"Rendered {count} sessions to {resolved_out}")


@app.command()
def note(
    uuid: str = typer.Argument(..., help="Session UUID."),
    text: str = typer.Argument(
        None, help="Note text. Omit and pass --clear to remove."
    ),
    clear: bool = typer.Option(
        False, "--clear", help="Remove the existing note for this UUID."
    ),
    db_path: Path = typer.Option(
        None,
        "--db",
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
) -> None:
    """Set, overwrite, or clear the user note for a session.

    AC4.5: unknown UUIDs exit with code 2 and a "no session with uuid" error
    on stderr. The ``--clear`` and positional text arguments are mutually
    exclusive — supplying both raises ``typer.BadParameter`` so a caller
    cannot ambiguously request "set this text" and "clear" in one call.
    """
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    try:
        if clear:
            if text is not None:
                raise typer.BadParameter(
                    "--clear cannot be combined with a text argument"
                )
            _note.clear_note(resolved_db, uuid)
            typer.echo(f"Cleared note for {uuid}")
        else:
            if text is None:
                raise typer.BadParameter("missing note text (or pass --clear)")
            _note.set_note(resolved_db, uuid, text)
            typer.echo(f"Set note for {uuid}")
    except _note.UnknownSessionError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@app.command()
def history(
    uuid: str = typer.Argument(..., help="Session UUID."),
    db_path: Path = typer.Option(
        None,
        "--db",
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
) -> None:
    """Show all recorded classifications for a session, chronologically.

    Reads ``classification_history`` joined with ``scan_runs`` so each row
    carries the originating scan's ``ts`` and the recorded
    ``classifier_version``. Rows print oldest-first in a plain-text table.
    A UUID with no history exits 1 with a stderr message; this distinguishes
    "no rows" from "table fetched and table was empty" for downstream tools.
    """
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    entries = _history.fetch_history(resolved_db, uuid)
    if not entries:
        typer.echo(f"No history for {uuid}", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        f"{'scan_id':>8} {'ts':>11} {'classification':<16} {'reason':<40} {'cv':>3}"
    )
    for entry in entries:
        reason = entry.reason or ""
        typer.echo(
            f"{entry.scan_id:>8} {entry.scan_ts:>11} "
            f"{entry.classification:<16} {reason:<40} {entry.classifier_version:>3}"
        )


@app.command()
def prune(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List candidate rows; do not delete."
    ),
    confirm: bool = typer.Option(False, "--confirm", help="Execute deletion."),
    db_path: Path = typer.Option(
        None,
        "--db",
        help=(
            "Path to crash-recovery SQLite DB"
            " (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db)."
        ),
    ),
) -> None:
    """Delete concluded sessions whose JSONLs are gone (gated).

    Four-condition guard (see :mod:`crash_recovery.prune`): a row is a
    candidate only if it is concluded, has no user note, its ``jsonl_path``
    is no longer on disk, and its ``classifier_version`` matches
    :data:`crash_recovery.classify.CLASSIFIER_VERSION`. ``--dry-run`` and
    ``--confirm`` are mutually exclusive. Without either flag the command
    refuses to delete (AC7.3); the user must opt in explicitly.

    Rows excluded only by the AC7.7 ``classifier_version`` guard surface as
    a stderr warning so the user knows running ``scan`` would unlock them.
    """
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    # Fail-fast on caller error before running survey(). Plan prescribed
    # survey()-first then mutex check; reversed here so callers get the
    # parameter error without an unnecessary DB read. Trade-off: when both
    # --dry-run and --confirm are passed AND the DB has stale-version
    # concluded rows, the AC7.7 warning is suppressed (the user fixes their
    # args, re-runs, then sees the warning). Approved in Phase 6 review 2026-05-18.
    if dry_run and confirm:
        raise typer.BadParameter("--dry-run and --confirm are mutually exclusive")
    survey = _prune.survey(resolved_db)
    if survey.stale_version_concluded_rows > 0:
        typer.echo(
            f"warning: {survey.stale_version_concluded_rows} concluded session(s)"
            " are at a stale classifier_version and were excluded from this prune."
            " Run `crash-recovery scan` to refresh them, then re-run prune.",
            err=True,
        )
    if dry_run:
        # AC7.2: list candidates, do not delete.
        if not survey.candidates:
            typer.echo("No prune candidates.")
            return
        typer.echo(f"{len(survey.candidates)} session(s) would be deleted:")
        for candidate in survey.candidates:
            typer.echo(
                f"  {candidate.uuid}  cwd={candidate.cwd}  "
                f"last_scanned={candidate.last_scanned}"
            )
        return
    if not confirm:
        # AC7.3: refuse without --confirm.
        typer.echo(
            "Refusing to delete without --confirm.\n"
            "Run `crash-recovery prune --dry-run` to see what would be deleted, "
            "then re-run with --confirm.",
            err=True,
        )
        raise typer.Exit(code=1)
    # AC7.4: --confirm executes.
    deleted = _prune.delete_candidates(
        resolved_db, tuple(c.uuid for c in survey.candidates)
    )
    typer.echo(f"Deleted {deleted} session(s).")


@app.command(name="list-live")
def list_live(
    run_dir: Path = typer.Option(
        None,
        "--run-dir",
        help=(
            "Liveness-file directory"
            " (default: $CRASH_RECOVERY_RUN_DIR or ~/.claude/run)."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON array instead of plain table.",
    ),
) -> None:
    """List currently-running Claude wrappers per liveness data.

    Reads the per-PID liveness files under ``run_dir`` and prints the
    subset whose wrapper process is still alive. The ``boot_ok`` column
    (``--json``: ``boot_id_current``) flags whether each wrapper is
    running under the current kernel boot id — ``NO`` (or ``false``)
    indicates a recycled PID whose original wrapper is gone. Empty
    ``run_dir`` prints ``No live sessions.`` (or ``[]`` under ``--json``).
    """
    resolved_run_dir = _resolve(run_dir, "CRASH_RECOVERY_RUN_DIR", "~/.claude/run")
    # survey_live deliberately does NOT filter on boot_id_current; it reports
    # boot_id_current as the `boot_ok` column instead. Rationale: a row with
    # boot_ok=NO means the PID exists but came up under a different boot id —
    # the original wrapper is gone and the new occupant is an unrelated
    # process that happens to share the recycled PID. Surfacing the row lets
    # the user see the evidence; filtering would hide what's actually on
    # disk. A future "fix" that filters by boot_id_current=True would lose
    # diagnostic signal. See DR7 (design plan): a non-current-boot liveness
    # file is a "guaranteed casualty" for scan's classification purposes,
    # but list-live is a diagnostic, not a classifier.
    entries = _list_live.survey_live(resolved_run_dir)
    if json_out:
        payload = [
            {
                "pid": e.pid,
                "cwd": e.cwd,
                "started": e.started,
                "argv": e.argv,
                "boot_id_current": e.boot_id_current,
            }
            for e in entries
        ]
        typer.echo(json.dumps(payload, indent=2))
        return
    if not entries:
        typer.echo("No live sessions.")
        return
    typer.echo(f"{'pid':>8} {'started':>11} {'boot_ok':>7} {'cwd':<40} argv")
    for e in entries:
        typer.echo(
            f"{e.pid:>8} {e.started:>11} "
            f"{'yes' if e.boot_id_current else 'NO':>7} {e.cwd:<40} {e.argv}"
        )


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
