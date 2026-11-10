"""Native question policy through the packaged hook's stdin/stdout boundary."""

import json
import os
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from websockets.sync.server import unix_serve

HOOK = (
    Path(__file__).resolve().parents[1]
    / "plugins/denubis-hook-question-zone/hooks/codex-question-zone.py"
)
sys.path.insert(0, str(HOOK.parent))

from question_zone_codex.checker import SearchTrace, check  # noqa: E402
from question_zone_codex.core import (  # noqa: E402
    Question,
    Unavailable,
    verify_evidence,
)


def invoke(payload: object, *, endpoint: str | None = None) -> dict:
    env = os.environ.copy()
    if endpoint is not None:
        env["QUESTION_ZONE_CODEX_SOCKET"] = endpoint
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def question(cwd: Path, *, tool: str = "request_user_input_async") -> dict:
    field = "title" if tool.endswith("_async") else "question"
    return {
        "hook_event_name": "PreToolUse",
        "session_id": "proposer",
        "tool_name": tool,
        "tool_input": {
            "questions": [{field: "The meeting needs a day. Which day works for you?"}]
        },
        "cwd": str(cwd),
    }


def verdict(outcome: str, *, evidence: dict | None = None) -> dict:
    return {
        "outcome": outcome,
        "reason": {
            "clear": "The question stands alone and both searches found no answer.",
            "rewrite": "The reader cannot tell which meeting this means.",
            "unavailable": "The graphics card cannot allocate the chat index model.",
            "answered": "The person chose Tuesday for this meeting.",
        }[outcome],
        "evidence": evidence or {"path": "", "line": 0, "quote": ""},
    }


def command_report(command: str, **payload) -> str:
    return json.dumps(
        {
            "schema_version": 5,
            "command": command,
            "status": "complete",
            "coverage": {"completeness": "complete"},
            **payload,
        }
    )


class Daemon:
    def __init__(self, reply: object, *, failure: str = ""):
        self.reply = reply
        self.failure = failure
        self.requests: list[dict] = []
        self.turn_count = 0
        self.turn_id = ""

    def handle(self, socket) -> None:
        for raw in socket:
            message = json.loads(raw)
            self.requests.append(message)
            method = message["method"]
            if "id" not in message:
                continue
            result = {}
            if method == "initialize":
                result = {"userAgent": "test"}
            elif method == "thread/start":
                result = {"thread": {"id": "checker"}}
            elif method == "turn/start":
                self.turn_count += 1
                self.turn_id = f"check-turn-{self.turn_count}"
                result = {"turn": {"id": self.turn_id}}
            elif method == "thread/unsubscribe" and self.failure == "cleanup":
                socket.send(
                    json.dumps(
                        {"id": message["id"], "error": {"message": "cleanup failed"}}
                    )
                )
                continue
            socket.send(json.dumps({"id": message["id"], "result": result}))
            if method == "turn/start":
                self.complete(socket)

    def complete(self, socket) -> None:
        if self.failure == "hang":
            return
        clarity = self.turn_count == 1
        if self.failure in ("approval", "unrelated_approval") and not clarity:
            socket.send(
                json.dumps(
                    {
                        "id": 999,
                        "method": "item/commandExecution/requestApproval",
                        "params": {
                            "threadId": "checker",
                            "command": "cc-search-chats index --json"
                            if self.failure == "approval"
                            else "git status",
                        },
                    }
                )
            )
            return
        commands: list[tuple[str, object, int]] = [
            (
                "cc-search-chats index --status --json",
                command_report("index", index_state={"freshness": "no_source_changes"}),
                0,
            ),
            (
                "cc-search-chats search 'meeting day' --literal --json",
                command_report("search", results=[]),
                0,
            ),
        ]
        if clarity:
            commands = []
        elif self.failure == "partial":
            commands[0] = (
                "cc-search-chats index --status --json",
                command_report(
                    "index",
                    coverage={"completeness": "partial", "blocked_files": 6},
                    index_state={"freshness": "no_source_changes"},
                ),
                0,
            )
        elif self.failure.startswith("history_report_"):
            reports: dict[str, object] = {
                "nontext": None,
                "malformed": "unreadable history output",
                "truncated": command_report(
                    "index", index_state={"freshness": "no_source_changes"}
                )[:-1],
                "schema": command_report(
                    "index",
                    schema_version=999,
                    index_state={"freshness": "no_source_changes"},
                ),
                "missing": json.dumps({"schema_version": 5, "event": "terminal"}),
                "status": command_report("index"),
            }
            commands[0] = (
                "cc-search-chats index --status --json",
                reports[self.failure.removeprefix("history_report_")],
                0,
            )
        elif self.failure == "index":
            commands[0] = (
                "cc-search-chats index --json",
                "GPU memory allocation failed",
                1,
            )
        elif self.failure == "stale":
            commands[0] = (
                "cc-search-chats index --status --json",
                command_report("index", index_state={"freshness": "source_changes"}),
                0,
            )
        elif self.failure == "no_trace":
            commands = []
        for command, output, code in commands:
            socket.send(
                json.dumps(
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": "checker",
                            "turnId": self.turn_id,
                            "item": {
                                "type": "commandExecution",
                                "command": command,
                                "aggregatedOutput": output,
                                "exitCode": code,
                            },
                        },
                    }
                )
            )
        reply = self.reply
        if clarity and not (
            isinstance(reply, dict) and reply.get("outcome") == "rewrite"
        ):
            reply = verdict("unavailable" if self.failure == "clarity" else "clear")
        socket.send(
            json.dumps(
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": "checker",
                        "turnId": self.turn_id,
                        "item": {
                            "type": "agentMessage",
                            "text": json.dumps(reply),
                        },
                    },
                }
            )
        )
        socket.send(
            json.dumps(
                {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "checker",
                        "turn": {"id": self.turn_id, "status": "completed"},
                    },
                }
            )
        )


@contextmanager
def daemon(tmp_path: Path, reply: object, *, failure: str = ""):
    fake = Daemon(reply, failure=failure)
    path = str(tmp_path / "daemon.sock")
    with unix_serve(fake.handle, path) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield path, fake
        finally:
            server.shutdown()
            thread.join(timeout=3)
            assert not thread.is_alive()


@pytest.mark.parametrize("tool", ["request_user_input", "request_user_input_async"])
def test_clear_checker_allows_native_tool_and_releases_thread(tmp_path, tool) -> None:
    with daemon(tmp_path, verdict("clear")) as (endpoint, fake):
        result = invoke(question(tmp_path, tool=tool), endpoint=endpoint)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", result
    assert any(row["method"] == "thread/unsubscribe" for row in fake.requests)
    start = next(
        row["params"] for row in fake.requests if row["method"] == "thread/start"
    )
    assert start["model"] == "gpt-6.1-terra"
    assert start["cwd"] == str(tmp_path)
    assert start["ephemeral"] is True
    assert "baseInstructions" not in start
    assert "project_doc_max_bytes" not in start["config"]
    # The native thread inherits the user's configured plugin selection. Its
    # request may disable execution hooks, but must not erase plugin skill roots.
    assert "features.plugins" not in start["config"]
    assert start["config"]["features.hooks"] is False
    turn = next(row["params"] for row in fake.requests if row["method"] == "turn/start")
    assert turn["effort"] == "xhigh"
    assert "proposer" not in json.dumps(turn["input"])


@pytest.mark.parametrize("outcome", ["rewrite"])
def test_nonclear_verdict_denies_native_tool(tmp_path, outcome) -> None:
    with daemon(tmp_path, verdict(outcome)) as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert f"({outcome})" in output["permissionDecisionReason"]


@pytest.mark.parametrize("failure", ["", "partial"])
def test_answered_verdict_cites_original_human_words(tmp_path, failure) -> None:
    transcript = tmp_path / "original.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "type": "user",
                "origin": {"kind": "human"},
                "message": {
                    "role": "user",
                    "content": "Tuesday works for the meeting.",
                },
            }
        )
        + "\n"
    )
    evidence = {
        "path": str(transcript),
        "line": 1,
        "quote": "Tuesday works for the meeting.",
    }
    with daemon(tmp_path, verdict("answered", evidence=evidence), failure=failure) as (
        endpoint,
        _,
    ):
        result = invoke(question(tmp_path), endpoint=endpoint)
    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "(answered)" in output["permissionDecisionReason"]
    assert f"{transcript}:1" in output["permissionDecisionReason"]


@pytest.mark.parametrize("bad", [None, {}, {"outcome": "clear"}])
def test_malformed_checker_reply_is_unavailable(tmp_path, bad) -> None:
    with daemon(tmp_path, bad) as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "(unavailable)" in output["permissionDecisionReason"]


@pytest.mark.parametrize("failure", ["approval", "index"])
def test_history_failure_warns_after_clarity_passes(tmp_path, failure) -> None:
    with daemon(tmp_path, verdict("clear"), failure=failure) as (endpoint, fake):
        result = invoke(question(tmp_path), endpoint=endpoint)
    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "allow"
    assert "history" in result["systemMessage"].lower()
    assert any(row["method"] == "thread/unsubscribe" for row in fake.requests)
    assert not any(row.get("id") == 999 for row in fake.requests)


def test_bundled_questions_are_refused_before_checker_or_ui() -> None:
    result = invoke(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "request_user_input_async",
            "tool_input": {
                "questions": [
                    {"title": "Which day should the meeting happen?"},
                    {"title": "Which room should the meeting use?"},
                ]
            },
            "cwd": "/project",
        }
    )
    output = result.get("hookSpecificOutput", {})
    assert output.get("permissionDecision") == "deny", result
    assert "one question" in output["permissionDecisionReason"]


def test_sync_choice_question_is_checked_with_its_native_options(tmp_path) -> None:
    payload = question(tmp_path, tool="request_user_input")
    options = [
        {"label": "Tuesday", "description": "Meet Tuesday morning."},
        {"label": "Thursday", "description": "Meet Thursday morning."},
    ]
    payload["tool_input"]["questions"][0]["options"] = options
    with daemon(tmp_path, verdict("clear")) as (endpoint, fake):
        result = invoke(payload, endpoint=endpoint)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", result
    submitted = next(
        row["params"]["input"] for row in fake.requests if row["method"] == "turn/start"
    )
    assert "Tuesday" in json.dumps(submitted)
    assert "Thursday" in json.dumps(submitted)


@pytest.mark.parametrize(
    "record",
    [
        {
            "type": "attachment",
            "attachment": {
                "type": "queued_command",
                "origin": {"kind": "human"},
                "prompt": "Tuesday works for the meeting.",
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "message": "Tuesday works for the meeting.",
            },
        },
    ],
)
def test_original_midturn_and_codex_human_records_can_settle_question(
    tmp_path, record
) -> None:
    transcript = tmp_path / "original.jsonl"
    transcript.write_text(json.dumps(record) + "\n")
    evidence = {
        "path": str(transcript),
        "line": 1,
        "quote": "Tuesday works for the meeting.",
    }
    with daemon(tmp_path, verdict("answered", evidence=evidence)) as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert "(answered)" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize(
    "record",
    [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "Tuesday works for the meeting.",
            },
        },
        {
            "type": "user",
            "origin": {"kind": "plugin"},
            "message": {"role": "user", "content": "Tuesday works for the meeting."},
        },
        {
            "type": "user",
            "message": {"role": "user", "content": "Thursday works for the meeting."},
        },
    ],
)
def test_invented_or_nonhuman_citation_cannot_settle_question(tmp_path, record) -> None:
    transcript = tmp_path / "original.jsonl"
    transcript.write_text(json.dumps(record) + "\n")
    evidence = {
        "path": str(transcript),
        "line": 1,
        "quote": "Tuesday works for the meeting.",
    }
    with daemon(tmp_path, verdict("answered", evidence=evidence)) as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert "(unavailable)" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("failure", ["no_trace", "stale"])
def test_missing_fresh_history_trace_warns_after_clarity_passes(
    tmp_path, failure
) -> None:
    with daemon(tmp_path, verdict("clear"), failure=failure) as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "history" in result["systemMessage"].lower()


@pytest.mark.parametrize("outcome", ["clear", "unavailable"])
def test_partial_history_warns_without_blocking_clear_question(
    tmp_path, outcome
) -> None:
    with daemon(tmp_path, verdict(outcome), failure="partial") as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "partial" in result["systemMessage"].lower()


@pytest.mark.parametrize(
    "kind", ["nontext", "malformed", "truncated", "schema", "missing", "status"]
)
def test_unreadable_history_report_warns_after_clarity_passes(tmp_path, kind) -> None:
    with daemon(tmp_path, verdict("clear"), failure="history_report_" + kind) as (
        endpoint,
        _,
    ):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "history" in result["systemMessage"].lower()


@pytest.mark.parametrize("failure", ["clarity", "cleanup", "unrelated_approval"])
def test_checker_or_cleanup_failure_still_denies_question(tmp_path, failure) -> None:
    with daemon(tmp_path, verdict("clear"), failure=failure) as (endpoint, fake):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    if failure == "clarity":
        assert len([r for r in fake.requests if r["method"] == "turn/start"]) == 1


def test_checker_deadline_interrupts_and_unsubscribes(tmp_path, monkeypatch) -> None:
    with daemon(tmp_path, verdict("clear"), failure="hang") as (endpoint, fake):
        monkeypatch.setenv("QUESTION_ZONE_CODEX_SOCKET", endpoint)
        started = time.monotonic()
        with pytest.raises(Unavailable, match=r"response unavailable|deadline"):
            check(Question("Which day works for you?", str(tmp_path)), timeout=0.15)
        elapsed = time.monotonic() - started
    assert elapsed < 2
    assert any(row["method"] == "turn/interrupt" for row in fake.requests)
    assert any(row["method"] == "thread/unsubscribe" for row in fake.requests)


@pytest.mark.parametrize(
    "generated",
    [
        {"isCompactSummary": True, "isVisibleInTranscriptOnly": True},
        {"isMeta": True},
    ],
)
def test_generated_claude_user_rows_are_not_original_human_evidence(
    tmp_path, generated
) -> None:
    transcript = tmp_path / "original.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "type": "user",
                "userType": "external",
                "message": {
                    "role": "user",
                    "content": "Tuesday works for the meeting.",
                },
                **generated,
            }
        )
        + "\n"
    )
    evidence = {
        "path": str(transcript),
        "line": 1,
        "quote": "Tuesday works for the meeting.",
    }
    with daemon(tmp_path, verdict("answered", evidence=evidence)) as (endpoint, _):
        result = invoke(question(tmp_path), endpoint=endpoint)
    assert "(unavailable)" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("defect", ["", "assistant", "meta", "injected", "quote"])
def test_verify_evidence_current_codex_retained_human_row(tmp_path, defect) -> None:
    record = {
        "type": "response_item",
        "payload": {
            "type": "message",
            "id": "synthetic-human-message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Tuesday works for the meeting."}
            ],
        },
        "metadata": {
            "client_authored": False,
            "retained_source": {
                "id": {"message_id": "synthetic-human-message", "role": "user"},
                "complete": True,
            },
        },
    }
    if defect == "assistant":
        payload = record["payload"]
        assert isinstance(payload, dict)
        payload["role"] = "assistant"
    elif defect == "meta":
        record["isMeta"] = True
    elif defect == "injected":
        del record["metadata"]
    path = tmp_path / "native.jsonl"
    path.write_text(json.dumps(record) + "\n")
    evidence = {
        "path": str(path),
        "line": 1,
        "quote": "Thursday" if defect == "quote" else "Tuesday works for the meeting.",
    }
    if defect:
        with pytest.raises(Unavailable):
            verify_evidence(evidence)
    else:
        assert (
            verify_evidence(evidence)
            == str(path) + ":1: Tuesday works for the meeting."
        )


def test_terminal_event_and_stale_status_report_allow_refresh_then_search() -> None:
    # Framing observed in a real 0.167 completed command: stderr's terminal
    # JSON event precedes stdout's command report in aggregatedOutput.
    terminal = json.dumps(
        {
            "schema_version": 5,
            "event": "terminal",
            "index_state": {"freshness": "refresh_pending"},
        }
    )
    status = command_report("index", index_state={"freshness": "refresh_pending"})
    trace = SearchTrace()
    trace.observe(
        {
            "type": "commandExecution",
            "command": "/usr/bin/bash -lc 'cc-search-chats index --status --json'",
            "exitCode": 0,
            "aggregatedOutput": terminal + "\n" + status + "\n",
        }
    )
    assert not trace.fresh
    for command, report in [
        ("index", command_report("index", refresh={"state": "complete"})),
        ("search 'meeting day'", command_report("search", results=[])),
    ]:
        trace.observe(
            {
                "type": "commandExecution",
                "command": f"cc-search-chats {command} --json",
                "exitCode": 0,
                "aggregatedOutput": terminal + "\n" + report,
            }
        )
    trace.require_clear_evidence()


@pytest.mark.parametrize(
    "output",
    [
        json.dumps(
            {
                "schema_version": 5,
                "event": "terminal",
                "index_state": {"freshness": "no_source_changes"},
            }
        ),
        command_report("index", index_state={"freshness": "no_source_changes"})
        + "\n{broken",
        command_report(
            "index", schema_version=999, index_state={"freshness": "no_source_changes"}
        ),
    ],
)
def test_missing_report_or_broken_json_stream_cannot_establish_freshness(
    output,
) -> None:
    trace = SearchTrace()
    with pytest.raises(Unavailable):
        trace.observe(
            {
                "type": "commandExecution",
                "command": "cc-search-chats index --status --json",
                "exitCode": 0,
                "aggregatedOutput": output,
            }
        )
