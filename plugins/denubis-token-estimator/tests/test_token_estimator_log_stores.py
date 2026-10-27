"""The estimator reads the log stores Claude Code and Codex actually write, and says
how much of them it could not read.

Claude Code keeps its transcripts under `$CLAUDE_CONFIG_DIR/projects` and Codex its
rollouts under `$CODEX_HOME/sessions` when those variables are set. A verifier that
always read `~/.claude/projects` and `~/.codex/sessions` would audit the wrong store.
The decoy store under HOME is the positive control: it is what the verifier reads
when the variables are unset, so the second run cannot pass by reading nothing.

A live transcript's last line may be torn mid-append. Skipping it is right; skipping it
without counting it would make a smaller total indistinguishable from a complete one.
"""

from __future__ import annotations

import collections
import json
import os
import subprocess
import sys
from pathlib import Path

import estimate as E
import verify as V
from denubis_agent_logs.records import ReadReport

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _assistant(mid, out, cwd="/r/Alice/ProjX"):
    return {
        "type": "assistant",
        "cwd": cwd,
        "timestamp": "2026-10-01T10:00:00Z",
        "message": {
            "id": mid,
            "model": "claude-opus-4",
            "usage": {"output_tokens": out},
        },
    }


def _rollout(thread_id, output):
    return [
        {
            "timestamp": "2026-10-01T10:00:00Z",
            "type": "session_meta",
            "payload": {"id": thread_id, "source": "cli", "cwd": "/r/Alice/ProjX"},
        },
        {
            "timestamp": "2026-10-01T10:00:05Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"output_tokens": output}},
            },
        },
    ]


def _verify_json(tmp_path, home, **variables):
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CLAUDE_CONFIG_DIR", "CODEX_HOME"}
    }
    env["HOME"] = str(home)
    env.update(variables)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify.py"), "--json"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_verify_reads_the_stores_named_by_claude_config_dir_and_codex_home(tmp_path):
    home = tmp_path / "home"
    _write_jsonl(home / ".claude" / "projects" / "-p" / "s.jsonl", [_assistant("D", 7)])
    _write_jsonl(
        home / ".codex" / "sessions" / "2026" / "10" / "rollout-d.jsonl",
        _rollout("decoy", 70),
    )
    config = tmp_path / "claude-config"
    codex_home = tmp_path / "codex-home"
    _write_jsonl(
        config / "projects" / "-p" / "s.jsonl",
        [_assistant("W1", 11), _assistant("W2", 13)],
    )
    _write_jsonl(
        codex_home / "sessions" / "2026" / "10" / "rollout-w.jsonl",
        _rollout("wanted", 500),
    )

    default = _verify_json(tmp_path, home)
    configured = _verify_json(
        tmp_path, home, CLAUDE_CONFIG_DIR=str(config), CODEX_HOME=str(codex_home)
    )

    assert (default["claude"]["distinct_ids"], default["claude"]["main_tok"]) == (1, 7)
    assert default["codex"]["main_tok"] == 70
    assert (configured["claude"]["distinct_ids"], configured["claude"]["main_tok"]) == (
        2,
        24,
    )
    assert configured["codex"]["main_tok"] == 500


def _corpus_with_torn_tail(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    path = root / "proj" / "main.jsonl"
    _write_jsonl(path, [_assistant("A", 5)])
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"type": "assistant", "message": {"id": "B", "usa')
    monkeypatch.setattr(V, "CLAUDE_ROOT", root)


def test_verify_claude_pass_counts_the_torn_line_it_skips(tmp_path, monkeypatch):
    _corpus_with_torn_tail(tmp_path, monkeypatch)
    report = ReadReport()

    result = V.claude_pass(report)

    assert (result["distinct_ids"], result["main_tok"]) == (1, 5)
    assert (report.files_read, report.torn_lines, report.unreadable) == (1, 1, [])


def test_estimate_collect_claude_counts_the_torn_line_it_skips(tmp_path, monkeypatch):
    _corpus_with_torn_tail(tmp_path, monkeypatch)
    report = ReadReport()
    leaves = collections.defaultdict(E._blank)

    E.collect_claude(leaves, lambda cwd: V.attribute(cwd, ["/r"]), report=report)

    assert leaves[("claude", "Alice", "ProjX", "2026-10")] == [5, 0, 0, 0]
    assert (report.files_read, report.torn_lines, report.unreadable) == (1, 1, [])
