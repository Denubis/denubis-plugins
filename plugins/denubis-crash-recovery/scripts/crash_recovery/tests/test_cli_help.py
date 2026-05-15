"""Tests for the crash-recovery CLI help and error surfaces.

Covers AC2.5 (unknown subcommand exits non-zero and points at ``--help``) and
seeds the AC2.1 / AC2.2 subcommand-listing test that grows phase-by-phase.
"""

from __future__ import annotations

import os
import subprocess
import sys

# Subcommands wired by the current phase. Later phases append entries; the
# test that consumes this list grows with the CLI surface.
EXPECTED_SUBCOMMANDS: tuple[str, ...] = ("init",)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run ``python -m crash_recovery ...`` so tests use the same interpreter."""
    return subprocess.run(
        [sys.executable, "-m", "crash_recovery", *args],
        capture_output=True,
        text=True,
        env={**os.environ},
    )


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
        combined = result.stdout + result.stderr
        assert "--help" in combined, combined
