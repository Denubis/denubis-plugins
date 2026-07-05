"""Tests for the report engine (estimate.py): per-leaf collection with month
faceting, and the rollup that collapses leaves to (person, project) totals.

This covers the "up and down" the disclosure needs: the per-(source, person,
project, month) leaf grain, and that rolling those up sums correctly.
"""

from __future__ import annotations

import collections
import json

import estimate as E
import verify as V


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _attr_r(cwd):
    return V.attribute(cwd, ["/r"])


def test_collect_claude_leaf_grain(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    _write_jsonl(
        root / "proj" / "main.jsonl",
        [
            {
                "type": "assistant",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-06-15T10:00:00Z",
                "message": {
                    "id": "A",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 300},
                },
            },
            {
                "type": "user",
                "uuid": "u1",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-06-15T10:00:01Z",
                "message": {"content": [{"type": "text", "text": "hello there world"}]},
            },
        ],
    )
    monkeypatch.setattr(V, "CLAUDE_ROOT", root)
    leaves = collections.defaultdict(E._blank)
    E.collect_claude(leaves, _attr_r)
    assert leaves[("claude", "Alice", "ProjX", "2026-06")] == [300, 0, 3]


def test_collect_codex_leaf_grain(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    _write_jsonl(
        root / "2026" / "06" / "rollout-2026-06-15T09-00-00.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {"id": "M1", "source": "cli", "cwd": "/r/Alice/ProjX"},
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 800}},
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "text", "text": "two words here"}],
                },
            },
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)
    leaves = collections.defaultdict(E._blank)
    E.collect_codex(leaves, _attr_r)
    # month comes from the rollout filename; main-thread tokens land in slot 0.
    assert leaves[("codex", "Alice", "ProjX", "2026-06")] == [800, 0, 3]


def test_rollup_collapses_to_person_project():
    leaves = {
        ("claude", "A", "P", "2026-05"): [10, 1, 2],
        ("claude", "A", "P", "2026-06"): [20, 3, 4],
        ("codex", "A", "P", "2026-06"): [5, 0, 1],
    }
    agg = E.rollup(leaves)
    assert agg[("A", "P")] == [35, 4, 7]


def test_rollup_keeps_month_when_asked():
    leaves = {
        ("claude", "A", "P", "2026-05"): [10, 1, 2],
        ("claude", "A", "P", "2026-06"): [20, 3, 4],
        ("codex", "A", "P", "2026-06"): [5, 0, 1],
    }
    aggm = E.rollup(leaves, keep_month=True)
    assert aggm[("A", "P", "2026-06")] == [25, 3, 5]
    assert aggm[("A", "P", "2026-05")] == [10, 1, 2]


def test_share():
    assert E.share(3, 1) == 25.0
    assert E.share(0, 0) == 0.0
