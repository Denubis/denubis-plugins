"""Tests for the crash-recovery CLI help and error surfaces.

Covers AC2.5 (unknown subcommand exits non-zero and points at ``--help``) and
seeds the AC2.1 / AC2.2 subcommand-listing test that grows phase-by-phase.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

# Subcommands wired by the current phase. Later phases append entries; the
# test that consumes this list grows with the CLI surface.
EXPECTED_SUBCOMMANDS: tuple[str, ...] = (
    "init",
    "scan",
    "render",
    "triage",
    "regenerate",
    "note",
    "history",
    "prune",
    "list-live",
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run ``python -m crash_recovery ...`` so tests use the same interpreter."""
    return subprocess.run(
        [sys.executable, "-m", "crash_recovery", *args],
        capture_output=True,
        text=True,
        env={**os.environ},
    )


# Typer renders CLI errors through Rich. When colour is forced (``FORCE_COLOR``
# in the environment, as CI and the Claude Code harness set), Rich colourises
# the ``--help`` hint and emits the two hyphens as separate SGR spans, so the
# captured bytes read ``-\x1b[...m-help`` and a literal ``"--help"`` substring
# check fails even though the rendered text is correct. Strip SGR codes before
# substring assertions so they test the rendered text, not its ANSI styling.
_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI SGR (colour) escape sequences from ``text``."""
    return _ANSI_SGR_RE.sub("", text)


class TestHelp:
    def test_help_exits_zero(self) -> None:
        """``crash-recovery --help`` prints help and exits 0."""
        result = _run_cli("--help")
        assert result.returncode == 0, (result.stdout, result.stderr)

    def test_help_lists_expected_subcommands(self) -> None:
        """Each subcommand wired in this phase appears in --help output.

        Phase 1 seeds the list with ``init``; later phases append. Asserts
        each name appears in stdout (typer renders subcommands in the
        Commands section of the help page).
        """
        result = _run_cli("--help")
        assert result.returncode == 0, (result.stdout, result.stderr)
        for cmd in EXPECTED_SUBCOMMANDS:
            assert cmd in result.stdout, (cmd, result.stdout)


class TestUnknownSubcommand:
    def test_unknown_subcommand_exits_nonzero(self) -> None:
        """``crash-recovery wibble`` exits non-zero with a ``--help`` hint."""
        result = _run_cli("wibble")
        assert result.returncode != 0, (result.stdout, result.stderr)
        combined = _strip_ansi(result.stdout + result.stderr)
        assert "--help" in combined, combined
