"""Tests never inherit the git repository of the process that launched pytest."""

import os
import subprocess
from pathlib import Path


def test_scratch_repository_commands_stay_in_the_scratch_repository(
    tmp_path: Path,
) -> None:
    leaked = sorted(
        name
        for name in subprocess.run(
            ["git", "rev-parse", "--local-env-vars"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        if name in os.environ
    )
    assert leaked == []

    scratch = tmp_path / "scratch"
    subprocess.run(["git", "init", "-q", str(scratch)], check=True)
    top = subprocess.run(
        ["git", "-C", str(scratch), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert Path(top).resolve() == scratch.resolve()
