"""Fixture-driven tests for the two counting passes — the methodology lock.

These build tiny synthetic ~/.claude and ~/.codex corpora with known-correct answers
and assert the exact token split and word count. They exist because the two worst
bugs this code ever had were *counting* bugs that prose review missed:

  * Claude: a subagent transcript REPLAYS the parent's assistant messages under the
    parent's message.id. Counting by file location double-counts the main thread.
    Correct rule: dedup globally by id (MAX output), classify main if the id appears
    in any main-thread file.
  * Codex: modern subagent rollouts may replay the parent's counter before NEW_TASK,
    then continue that cumulative counter. Correct rule: remove replay and subtract
    the inherited baseline before adding the child's owned output.

If either rule regresses, these fail.
"""

from __future__ import annotations

import json

import pytest
import verify as V


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _asst(mid, out, cwd):
    return {
        "type": "assistant",
        "cwd": cwd,
        "message": {
            "id": mid,
            "model": "claude-opus-4",
            "usage": {"output_tokens": out},
        },
    }


def _user(text, uuid, cwd="/r/Alice/ProjX", list_form=True, **extra):
    content = [{"type": "text", "text": text}] if list_form else text
    rec = {"type": "user", "uuid": uuid, "cwd": cwd, "message": {"content": content}}
    rec.update(extra)
    return rec


def _codex_token(output, timestamp):
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {"output_tokens": output}},
        },
    }


def _new_task(timestamp):
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "agent_message",
            "content": [
                {
                    "type": "input_text",
                    "text": "Message Type: NEW_TASK\nImplement the bounded task.",
                }
            ],
        },
    }


# ----------------------------------------------------------------- Claude
@pytest.fixture
def claude_corpus(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    _write_jsonl(
        root / "proj" / "main.jsonl",
        [
            _asst("A", 100, "/r/Alice/ProjX"),
            _asst(
                "A", 300, "/r/Alice/ProjX"
            ),  # same id, streamed higher -> max 300 so far
            _asst("B", 50, "/r/Alice/ProjX"),
            _user("Hello human prompt", "u1"),  # 3 human words
            _user(
                "<system-reminder>x</system-reminder>", "u2", list_form=False
            ),  # machine
            _user("<p>pasted html kept</p>", "u3"),  # human-pasted markup -> 3 words
            _user("dupe ignored", "u1"),  # duplicate uuid -> skipped
            {  # tool result -> skipped
                "type": "user",
                "uuid": "u4",
                "cwd": "/r/Alice/ProjX",
                "toolUseResult": {"x": 1},
                "message": {"content": [{"type": "text", "text": "tr"}]},
            },
            {  # isMeta -> skipped
                "type": "user",
                "uuid": "u5",
                "isMeta": True,
                "cwd": "/r/Alice/ProjX",
                "message": {"content": [{"type": "text", "text": "meta"}]},
            },
        ],
    )
    _write_jsonl(
        root / "proj" / "subagents" / "sub.jsonl",
        [
            _asst(
                "A", 999, "/r/Alice/ProjX"
            ),  # REPLAY of A -> counted once at max, still main
            _asst("C", 900, "/r/Alice/ProjX"),  # sub-only id
            _user("subagent text", "us1"),  # user text in a sub file -> not counted
        ],
    )
    monkeypatch.setattr(V, "CLAUDE_ROOT", root)
    monkeypatch.setattr(V, "ROOTS", ["/r"])
    return root


@pytest.mark.usefixtures("claude_corpus")
def test_claude_origin_dedup_and_words():
    c = V.claude_pass()
    assert c["distinct_ids"] == 3  # A, B, C
    assert c["main_tok"] == 1049  # A(max 999) + B(50); A NOT double-counted by file
    assert c["sub_tok"] == 900  # C only; A is main despite the subagent replay
    assert c["cross_partition"] == 1  # A appears in both a main and a sub file
    assert c["node3_blocks"] == 2  # "Hello..." + "<p>..."; subfile user text excluded
    assert c["node3_words"] == 6
    assert c["wrap_hist"] == {"system-reminder": 1}
    assert c["cross_person"] == 0
    assert c["cross_person_project"] == 0


def test_claude_cross_person_reconciliation(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    _write_jsonl(root / "p" / "main.jsonl", [_asst("D", 200, "/r/Alice/ProjX")])
    _write_jsonl(
        root / "p" / "subagents" / "s.jsonl", [_asst("D", 500, "/r/Bob/ProjY")]
    )
    monkeypatch.setattr(V, "CLAUDE_ROOT", root)
    monkeypatch.setattr(V, "ROOTS", ["/r"])
    c = V.claude_pass()
    # one id whose recorded cwds span two people -> both reconciliation counters tick.
    assert c["cross_person"] == 1
    assert c["cross_person_project"] == 1


# ----------------------------------------------------------------- Codex
@pytest.fixture
def codex_corpus(tmp_path, monkeypatch):
    root = tmp_path / "sessions"

    def tok(n):
        return {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"output_tokens": n}},
            },
        }

    def uitem(text):
        return {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": text}],
            },
        }

    _write_jsonl(
        root / "2026" / "06" / "rollout-main.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {"id": "M1", "source": "cli", "cwd": "/r/Alice/ProjX"},
            },
            tok(500),
            tok(1500),  # parent max
            uitem("do the thing"),  # 3 human words
            uitem("<turn_aborted> interrupted"),  # machine marker -> excluded
            uitem("# Claude do X"),  # markdown-heading prompt -> kept, 4 words
        ],
    )
    _write_jsonl(
        root / "2026" / "06" / "rollout-sub.jsonl",
        [
            {
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
            tok(400),  # fresh start, well below the parent total
            tok(900),  # the subagent's own max
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)
    monkeypatch.setattr(V, "ROOTS", ["/r"])
    return root


@pytest.mark.usefixtures("codex_corpus")
def test_codex_subagents_additive():
    x = V.codex_pass()
    assert x["files"] == 2
    assert x["n_main"] == 1  # source is a string -> root thread
    assert x["n_sub"] == 1  # source is a structured dict -> subagent
    assert x["main_tok"] == 1500  # parent thread max
    assert x["sub_tok"] == 900  # ADDITIVE — the child's own counter, not merged away
    assert x["distinct_ids"] == 2  # node2 "no resumes": one id per file
    assert x["sub_all"] == [(400, 900, 1500)]  # (first_out, own_max, parent_max)


@pytest.mark.usefixtures("codex_corpus")
def test_codex_node4_words():
    x = V.codex_pass()
    assert x["node4_turns"] == 2  # "do the thing" + "# Claude do X"
    assert x["node4_words"] == 7  # 3 + 4
    assert x["node4_excl"] == {"turn_aborted": 1}


def test_codex_continued_child_subtracts_pre_task_replay(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    parent = root / "2026" / "08" / "rollout-parent.jsonl"
    child = root / "2026" / "08" / "rollout-child.jsonl"
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
            _codex_token(1_000, "2026-08-16T00:00:01Z"),
            _codex_token(5_000, "2026-08-16T00:00:05Z"),
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
            # Parent events replay before the child's task boundary.
            _codex_token(1_000, "2026-08-16T00:00:05.100Z"),
            _codex_token(5_000, "2026-08-16T00:00:05.200Z"),
            _new_task("2026-08-16T00:00:06Z"),
            # The child continues the inherited cumulative counter.
            _codex_token(5_200, "2026-08-16T00:00:07Z"),
            _codex_token(6_500, "2026-08-16T00:00:08Z"),
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)

    threads = {thread["id"]: thread for thread in V.codex_threads()}
    assert threads["S1"]["counter_mode"] == "continued-parent-counter"
    assert threads["S1"]["replay_baseline"] == 5_000
    assert threads["S1"]["parent_at_fork"] == 5_000
    assert threads["S1"]["output_tokens"] == 1_500
    assert (
        V.windowed_output(
            threads["S1"],
            V.parse_timestamp("2026-08-16T00:00:06Z"),
            V.parse_timestamp("2026-08-16T00:00:08Z"),
        )
        == 200
    )

    result = V.codex_pass()
    assert result["main_tok"] == 5_000
    assert result["sub_tok"] == 1_500
    assert result["unresolved_replay_parents"] == []
    assert result["replay_parent_mismatches"] == []


def test_codex_child_reset_after_replay_counts_fresh_counter(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    _write_jsonl(
        root / "2026" / "08" / "rollout-parent.jsonl",
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
            _codex_token(5_000, "2026-08-16T00:00:05Z"),
        ],
    )
    _write_jsonl(
        root / "2026" / "08" / "rollout-child.jsonl",
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
            _codex_token(5_000, "2026-08-16T00:00:05.100Z"),
            _new_task("2026-08-16T00:00:06Z"),
            # A future runtime may reset rather than continue after replay.
            _codex_token(400, "2026-08-16T00:00:07Z"),
            _codex_token(2_000, "2026-08-16T00:00:08Z"),
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)

    threads = {thread["id"]: thread for thread in V.codex_threads()}
    assert threads["S1"]["counter_mode"] == "fresh-after-replay"
    assert threads["S1"]["output_tokens"] == 2_000
    assert V.codex_pass()["sub_tok"] == 2_000


def test_codex_replay_without_resolvable_parent_is_reported(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    _write_jsonl(
        root / "2026" / "08" / "rollout-orphan-child.jsonl",
        [
            {
                "timestamp": "2026-08-16T00:00:05Z",
                "type": "session_meta",
                "payload": {
                    "id": "S1",
                    "forked_from_id": "missing-parent",
                    "source": {
                        "subagent": {
                            "thread_spawn": {"parent_thread_id": "missing-parent"}
                        }
                    },
                    "cwd": "/r/Alice/ProjX",
                },
            },
            _codex_token(5_000, "2026-08-16T00:00:05.100Z"),
            _new_task("2026-08-16T00:00:06Z"),
            _codex_token(5_500, "2026-08-16T00:00:07Z"),
        ],
    )
    monkeypatch.setattr(V, "CODEX_ROOT", root)

    assert V.codex_pass()["unresolved_replay_parents"] == ["S1"]
