"""Tests for the report engine (estimate.py): per-leaf collection with month
faceting, and the rollup that collapses leaves to (person, project) totals.

This covers the "up and down" the disclosure needs: the per-(source, person,
project, month) leaf grain, and that rolling those up sums correctly.
"""

from __future__ import annotations

import collections
import json

import estimate as E
import pytest
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


def test_collect_claude_equal_max_attribution_is_traversal_order_independent(
    tmp_path, monkeypatch
):
    root = tmp_path / "projects"
    bob = root / "proj" / "bob.jsonl"
    alice = root / "proj" / "alice.jsonl"
    _write_jsonl(
        bob,
        [
            {
                "type": "assistant",
                "cwd": "/r/Bob/ProjY",
                "timestamp": "2026-06-15T10:00:01Z",
                "message": {
                    "id": "same-message",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 300},
                },
            }
        ],
    )
    _write_jsonl(
        alice,
        [
            {
                "type": "assistant",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-06-15T10:00:00Z",
                "message": {
                    "id": "same-message",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 300},
                },
            }
        ],
    )
    monkeypatch.setattr(V, "claude_files", lambda: [bob, alice])
    leaves = collections.defaultdict(E._blank)
    E.collect_claude(leaves, _attr_r)

    assert leaves[("claude", "Alice", "ProjX", "2026-06")] == [300, 0, 0]
    assert leaves[("claude", "Bob", "ProjY", "2026-06")] == [0, 0, 0]


def test_collect_claude_window_uses_message_origin_not_replay_time(
    tmp_path, monkeypatch
):
    root = tmp_path / "projects"
    _write_jsonl(
        root / "proj" / "main.jsonl",
        [
            {
                "type": "assistant",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-11T10:00:00Z",
                "message": {
                    "id": "inside",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 100},
                },
            },
            {
                "type": "assistant",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-10T10:00:00Z",
                "message": {
                    "id": "before",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 200},
                },
            },
            {
                "type": "user",
                "uuid": "inside-user",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-11T11:00:00Z",
                "message": {"content": "three human words"},
            },
            {
                "type": "user",
                "uuid": "before-user",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-10T11:00:00Z",
                "message": {"content": "excluded human words"},
            },
        ],
    )
    _write_jsonl(
        root / "proj" / "subagents" / "sub.jsonl",
        [
            {
                "type": "assistant",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-12T10:00:00Z",
                "message": {
                    "id": "inside",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 300},
                },
            },
            {
                "type": "assistant",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-11T12:00:00Z",
                "message": {
                    "id": "before",
                    "model": "claude-opus-4",
                    "usage": {"output_tokens": 500},
                },
            },
        ],
    )
    monkeypatch.setattr(V, "CLAUDE_ROOT", root)
    leaves = collections.defaultdict(E._blank)
    E.collect_claude(
        leaves,
        _attr_r,
        start=V.parse_timestamp("2026-08-11T00:00:00Z"),
        end=V.parse_timestamp("2026-08-12T00:00:00Z"),
    )

    # "inside" is counted once at its main-thread origin, using its global MAX.
    # "before" is excluded even though a replay lands inside the window.
    assert leaves[("claude", "Alice", "ProjX", "(window)")] == [300, 0, 3]


def test_collect_claude_window_user_dedup_is_traversal_order_independent(
    tmp_path, monkeypatch
):
    root = tmp_path / "projects"
    replay = root / "proj" / "replay.jsonl"
    origin = root / "proj" / "origin.jsonl"
    _write_jsonl(
        replay,
        [
            {
                "type": "user",
                "uuid": "same-turn",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-12T01:00:00Z",
                "message": {"content": "three human words"},
            }
        ],
    )
    _write_jsonl(
        origin,
        [
            {
                "type": "user",
                "uuid": "same-turn",
                "cwd": "/r/Alice/ProjX",
                "timestamp": "2026-08-11T01:00:00Z",
                "message": {"content": "three human words"},
            }
        ],
    )
    monkeypatch.setattr(V, "claude_files", lambda: [replay, origin])
    leaves = collections.defaultdict(E._blank)
    E.collect_claude(
        leaves,
        _attr_r,
        start=V.parse_timestamp("2026-08-11T00:00:00Z"),
        end=V.parse_timestamp("2026-08-12T00:00:00Z"),
    )

    assert leaves[("claude", "Alice", "ProjX", "(window)")] == [0, 0, 3]


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


def test_collect_codex_uses_child_owned_counter_after_replay(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    parent = root / "2026" / "08" / "rollout-2026-08-16-parent.jsonl"
    child = root / "2026" / "08" / "rollout-2026-08-16-child.jsonl"
    _write_jsonl(
        parent,
        [
            {
                "timestamp": "2026-08-16T00:00:00Z",
                "type": "session_meta",
                "payload": {
                    "id": "M1",
                    "source": "cli",
                    "cwd": "/r/Alice/ProjX",
                },
            },
            {
                "timestamp": "2026-08-16T00:00:05Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 5_000}},
                },
            },
        ],
    )
    _write_jsonl(
        child,
        [
            {
                "timestamp": "2026-08-16T00:00:05Z",
                "type": "session_meta",
                "payload": {
                    "id": "S1",
                    "forked_from_id": "M1",
                    "source": {
                        "subagent": {"thread_spawn": {"parent_thread_id": "M1"}}
                    },
                    "cwd": "/r/Alice/ProjX",
                },
            },
            {
                "timestamp": "2026-08-16T00:00:05.100Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 5_000}},
                },
            },
            {
                "timestamp": "2026-08-16T00:00:06Z",
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Message Type: NEW_TASK\nDo the child work.",
                        }
                    ],
                },
            },
            {
                "timestamp": "2026-08-16T00:00:07Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 6_500}},
                },
            },
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)
    leaves = collections.defaultdict(E._blank)
    E.collect_codex(leaves, _attr_r)

    assert leaves[("codex", "Alice", "ProjX", "2026-08")] == [5_000, 1_500, 0]


def test_collect_codex_window_uses_owned_counter_delta(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    _write_jsonl(
        root / "2026" / "08" / "rollout-2026-08-16-main.jsonl",
        [
            {
                "timestamp": "2026-08-10T00:00:00Z",
                "type": "session_meta",
                "payload": {
                    "id": "M1",
                    "source": "cli",
                    "cwd": "/r/Alice/ProjX",
                },
            },
            {
                "timestamp": "2026-08-10T23:59:59Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 100}},
                },
            },
            {
                "timestamp": "2026-08-11T01:00:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 900}},
                },
            },
            {
                "timestamp": "2026-08-12T00:00:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {"output_tokens": 1_200}},
                },
            },
            {
                "timestamp": "2026-08-11T02:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "text", "text": "inside human words"}],
                },
            },
            {
                "timestamp": "2026-08-10T02:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "text", "text": "outside human words"}],
                },
            },
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)
    leaves = collections.defaultdict(E._blank)
    E.collect_codex(
        leaves,
        _attr_r,
        start=V.parse_timestamp("2026-08-11T00:00:00Z"),
        end=V.parse_timestamp("2026-08-12T00:00:00Z"),
    )

    # Inclusive start, exclusive end: 900 - 100; the 1,200 event is excluded.
    assert leaves[("codex", "Alice", "ProjX", "(window)")] == [800, 0, 3]


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


def test_parse_args_accepts_paired_aware_window():
    args = E.parse_args(
        [
            "--dir",
            ".",
            "--start",
            "2026-08-11T05:37:40.185+00:00",
            "--end",
            "2026-08-16T07:44:15.657Z",
        ]
    )

    assert args.start == V.parse_timestamp("2026-08-11T05:37:40.185Z")
    assert args.end == V.parse_timestamp("2026-08-16T07:44:15.657Z")


@pytest.mark.parametrize(
    "window_args",
    [
        ["--start", "2026-08-11T00:00:00Z"],
        [
            "--start",
            "2026-08-11T00:00:00",
            "--end",
            "2026-08-12T00:00:00Z",
        ],
        [
            "--start",
            "2026-08-12T00:00:00Z",
            "--end",
            "2026-08-11T00:00:00Z",
        ],
        [
            "--month",
            "--start",
            "2026-08-11T00:00:00Z",
            "--end",
            "2026-08-12T00:00:00Z",
        ],
    ],
)
def test_parse_args_rejects_invalid_window(window_args):
    with pytest.raises(SystemExit):
        E.parse_args(["--dir", ".", *window_args])
