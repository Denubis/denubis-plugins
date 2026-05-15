"""crash-recovery CLI entry point.

Exposes a module-level ``app`` (typer.Typer) so tests can import it without
invoking the CLI. ``main()`` is the console-script entry point declared in
``[project.scripts]``.

Subcommands are wired by later phases. Task 5 adds ``init``; Phases 4-6 add
``scan``, ``render``, ``note``, ``prune``, ``triage``.
"""

from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Deterministic triage of Claude Code sessions.

    Run ``crash-recovery <subcommand> --help`` for details. Subcommands are
    wired by later phases of the implementation plan.
    """


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
