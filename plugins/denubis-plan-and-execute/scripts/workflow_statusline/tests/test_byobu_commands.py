"""Exercise the installed Byobu command entry points."""

from __future__ import annotations

import datetime
import importlib.metadata
import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_installed_quota_command_reads_its_provider_data(
    provider, tmp_path, monkeypatch, capsys
):
    entries = {
        entry.name: entry
        for entry in importlib.metadata.distribution("workflow-statusline").entry_points
        if entry.group == "console_scripts"
    }
    assert "workflow-statusline" in entries
    command = f"byobu-{provider}-quota"
    assert command in entries

    now = datetime.datetime(2026, 9, 15, 7, 0).timestamp()
    reset = datetime.datetime(2026, 9, 17, 7, 0).timestamp()
    monkeypatch.setattr("time.time", lambda: now)
    if provider == "claude":
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        cache = tmp_path / "claude-statusline"
        cache.mkdir()
        (cache / "quota-seven_day").write_text(f"{now}|20|{reset}\n")
        expected = "#[fg=green]20*71 Thu#[default]\n"
    else:
        monkeypatch.setenv("CODEX_HOME", str(tmp_path))
        rollout = tmp_path / "rollout.jsonl"
        rollout.write_text(
            json.dumps(
                {
                    "timestamp": "2026-09-14T21:00:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "rate_limits": {
                            "limit_id": "codex",
                            "primary": {
                                "used_percent": 20,
                                "window_minutes": 10080,
                                "resets_at": int(reset),
                            },
                        },
                    },
                }
            )
            + "\n"
        )
        with sqlite3.connect(tmp_path / "state_5.sqlite") as connection:
            connection.execute(
                "CREATE TABLE threads (rollout_path TEXT, updated_at_ms INTEGER)"
            )
            connection.execute("INSERT INTO threads VALUES (?, ?)", (str(rollout), 1))
        expected = "#[fg=green]20 71 Thu#[default]\n"

    entries[command].load()()
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_symlinked_byobu_launcher_selects_its_own_package(provider, tmp_path):
    project = Path(__file__).parents[1]
    bindir = tmp_path / "bin with spaces"
    bindir.mkdir()
    uv = bindir / "uv"
    uv.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    uv.chmod(0o755)
    launcher = bindir / f"30_{provider}_quota"
    launcher.symlink_to(project / "byobu" / launcher.name)

    result = subprocess.run(
        ["sh", str(launcher)],
        env={**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"},
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "run",
        "--frozen",
        "--project",
        str(project),
        "--package",
        "workflow-statusline",
        f"byobu-{provider}-quota",
    ]
