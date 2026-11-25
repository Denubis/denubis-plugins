"""The Codex search for an earlier answer, through the packaged hook's stdin/stdout.

The hook runs in the background after Codex has shown a question, so it can
only hand the asking session context or show the person a warning.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from websockets.sync.server import unix_serve

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/denubis-hook-question-zone"
HOOK = PLUGIN / "hooks/codex-question-zone.py"
MANIFEST = PLUGIN / "hooks/codex-hooks.json"
sys.path.insert(0, str(HOOK.parent))

from question_zone_codex.checker import check  # noqa: E402
from question_zone_codex.core import Question, Unavailable  # noqa: E402

QUOTE = "Tuesday works for the meeting."
QUESTION_TOOLS = ("request_user_input", "request_user_input_async")


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
    output = json.loads(result.stdout)
    # A PostToolUse `decision`, `continue: false` or exit code 2 would replace
    # the question tool's result (Codex hooks documentation, PostToolUse). The
    # search may only add context for the asking model or warn the person.
    assert set(output) <= {"systemMessage", "hookSpecificOutput"}, output
    specific = output.get("hookSpecificOutput")
    if specific is not None:
        assert set(specific) == {"hookEventName", "additionalContext"}, output
        assert specific["hookEventName"] == "PostToolUse", output
    return output


def shown(cwd: Path, *, tool: str = "request_user_input_async") -> dict:
    """The PostToolUse input Codex 0.169.0 sent for a shown question (live probe)."""
    return {
        "hook_event_name": "PostToolUse",
        "session_id": "asking-session",
        "turn_id": "asking-turn",
        "tool_name": tool,
        "tool_use_id": "call_question",
        "tool_input": {
            "questions": [
                {"title": "The meeting needs a day. Which day works for you?"}
            ]
        },
        "tool_response": json.dumps({"accepted": True}),
        "cwd": str(cwd),
        "model": "gpt-6.2-sol",
        "permission_mode": "default",
        "transcript_path": str(cwd / "asking.jsonl"),
    }


def verdict(outcome: str, *, evidence: dict | None = None) -> dict:
    return {
        "outcome": outcome,
        "reason": {
            "answered": "The person chose Tuesday for this meeting.",
            "not_answered": "Both searches found no answer.",
            "go_ahead": "The question asks to go ahead with a commit now.",
            "unavailable": "The graphics card cannot allocate the chat index model.",
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


History = list[tuple[str, object, int]]

FRESH = (
    "cc-search-chats index --status --json",
    command_report("index", index_state={"freshness": "no_source_changes"}),
    0,
)
SEARCH = (
    "cc-search-chats search 'meeting day' --literal --json",
    command_report("search", results=[]),
    0,
)
REFRESH = (
    "cc-search-chats index --json",
    command_report("index", refresh={"state": "complete"}),
    0,
)

# The person's ruling of 2026-11-18 ("yes please", to skipping the chat index
# refresh when the index is less than five minutes old), in the milliseconds
# `index_state.age_ms` reports.
FIVE_MINUTES_MS = 5 * 60 * 1000


def status(**index_state: object) -> tuple[str, object, int]:
    """A status report whose index has native changes not yet indexed."""
    return (
        "cc-search-chats index --status --json",
        command_report(
            "index", index_state={"freshness": "refresh_pending", **index_state}
        ),
        0,
    )


class Daemon:
    """A Codex daemon whose search turn runs ``history`` and replies ``reply``.

    ``failure`` makes it hang instead of answering or fail to release the
    thread; ``approval`` makes the turn ask to approve that command instead.
    """

    def __init__(
        self,
        reply: object,
        *,
        history: History | None = None,
        failure: str = "",
        approval: str = "",
    ):
        self.reply = reply
        self.history = [FRESH, SEARCH] if history is None else history
        self.failure = failure
        self.approval = approval
        self.requests: list[dict] = []
        self.turn_count = 0
        self.turn_id = ""

    def turns(self) -> int:
        return len([row for row in self.requests if row.get("method") == "turn/start"])

    def released(self) -> bool:
        return any(row.get("method") == "thread/unsubscribe" for row in self.requests)

    def handle(self, socket) -> None:
        for raw in socket:
            message = json.loads(raw)
            self.requests.append(message)
            method = message.get("method")
            if "id" not in message or method is None:
                continue
            result = {}
            if method == "initialize":
                result = {"userAgent": "test"}
            elif method == "thread/start":
                result = {"thread": {"id": "searcher"}}
            elif method == "turn/start":
                self.turn_count += 1
                self.turn_id = f"search-turn-{self.turn_count}"
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

    def send_item(self, socket, item: dict) -> None:
        socket.send(
            json.dumps(
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": "searcher",
                        "turnId": self.turn_id,
                        "item": item,
                    },
                }
            )
        )

    def complete(self, socket) -> None:
        if self.failure == "hang":
            return
        if self.approval:
            socket.send(
                json.dumps(
                    {
                        "id": 999,
                        "method": "item/commandExecution/requestApproval",
                        "params": {"threadId": "searcher", "command": self.approval},
                    }
                )
            )
            return
        for command, output, code in self.history:
            self.send_item(
                socket,
                {
                    "type": "commandExecution",
                    "command": command,
                    "aggregatedOutput": output,
                    "exitCode": code,
                },
            )
        self.send_item(socket, {"type": "agentMessage", "text": json.dumps(self.reply)})
        socket.send(
            json.dumps(
                {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "searcher",
                        "turn": {"id": self.turn_id, "status": "completed"},
                    },
                }
            )
        )


@contextmanager
def daemon(
    tmp_path: Path,
    reply: object,
    *,
    history: History | None = None,
    failure: str = "",
    approval: str = "",
):
    fake = Daemon(reply, history=history, failure=failure, approval=approval)
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


def transcript(tmp_path: Path, record: dict) -> Path:
    """A transcript whose second row is ``record``, after an unrelated row."""
    path = tmp_path / "original.jsonl"
    unrelated = {"type": "user", "message": {"role": "user", "content": "Hello."}}
    path.write_text(json.dumps(unrelated) + "\n" + json.dumps(record) + "\n")
    return path


def cited(path: Path, *, line: int = 2, quote: str = QUOTE) -> dict:
    return verdict(
        "answered", evidence={"path": str(path), "line": line, "quote": quote}
    )


def typed(content: object) -> dict:
    """A prompt Claude Code marks as typed by the person (``origin.kind`` human)."""
    return {
        "type": "user",
        "origin": {"kind": "human"},
        "promptId": "prompt",
        "message": {"role": "user", "content": content},
    }


def codex_message(text: str, *, role: str = "user") -> dict:
    """A Codex user message with the metadata Codex 0.169 gives typed input."""
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "id": "synthetic-message",
            "role": role,
            "content": [{"type": "input_text", "text": text}],
        },
        "metadata": {
            "client_authored": False,
            "retained_source": {
                "id": {"message_id": "synthetic-message", "role": "user"},
                "complete": True,
            },
        },
    }


def question_reply(answer: str, question: str) -> str:
    """The message Codex records when the person answers in its question box."""
    item = {"answer": answer, "question": question, "questionItemId": "item"}
    return (
        "<send_user_message_question_reply>\n"
        + json.dumps([item])
        + "\n</send_user_message_question_reply>"
    )


ASKED = "Which day works for the meeting?"

HUMAN_ROWS = {
    "typed": typed(QUOTE),
    "typed-text-items": typed([{"type": "text", "text": QUOTE}]),
    # The person's words below a question quoted by the question box, beside
    # pasted material: only the words they typed are searched.
    "typed-below-quote": typed(
        f'> {ASKED}\n\n<pasted_content id="ab12">\nnotes\n'
        f'</pasted_content id="ab12">\n{QUOTE}'
    ),
    "midturn": {
        "type": "attachment",
        "attachment": {
            "type": "queued_command",
            "origin": {"kind": "human"},
            "prompt": QUOTE,
        },
    },
    "codex-question-box": codex_message(question_reply(QUOTE, ASKED)),
}


@pytest.mark.parametrize("row", sorted(HUMAN_ROWS))
def test_verified_earlier_answer_reaches_the_asking_model_with_quote_and_locator(
    tmp_path, row
) -> None:
    path = transcript(tmp_path, HUMAN_ROWS[row])
    with daemon(tmp_path, cited(path)) as (endpoint, fake):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    context = result["hookSpecificOutput"]["additionalContext"]
    assert QUOTE in context
    assert f"{path}:2" in context
    assert "systemMessage" not in result, result
    assert fake.released()


# Rows seen in real transcripts whose text the person did not type there. In
# Claude, teammate messages carry no origin; in Codex, briefs an agent typed
# into the pane through tmux are recorded exactly like the person's typing.
NONHUMAN_ROWS = {
    "assistant": {
        "type": "assistant",
        "message": {"role": "assistant", "content": QUOTE},
    },
    "plugin": {
        "type": "user",
        "origin": {"kind": "plugin"},
        "message": {"role": "user", "content": QUOTE},
    },
    "no-origin": {
        "type": "user",
        "promptId": "prompt",
        "message": {
            "role": "user",
            "content": f"Another Claude session sent a message:\n{QUOTE}",
        },
    },
    "other-words": typed("Thursday works for the meeting."),
    "compact-summary": {**typed(QUOTE), "isCompactSummary": True},
    "meta": {**typed(QUOTE), "isMeta": True},
    "quoted-question": typed(f"> {QUOTE}\n>\n> {ASKED}\n\nyes"),
    "quoted-bar": typed(f"\u258e {QUOTE}\n\nyes"),
    "pasted": typed(
        f'ok\n<pasted_content id="ab12">\n{QUOTE}\n</pasted_content id="ab12">'
    ),
    "command-message": typed(f"<command-message>{QUOTE}</command-message>"),
    "command-name": typed(f"<command-name>{QUOTE}</command-name>"),
    "command-output": typed(f"<local-command-stdout>{QUOTE}</local-command-stdout>"),
    "queued-notification": {
        "type": "attachment",
        "attachment": {
            "type": "queued_command",
            "origin": {"kind": "task-notification"},
            "prompt": QUOTE,
        },
    },
    "codex-typed": codex_message(QUOTE),
    "codex-event": {
        "type": "event_msg",
        "payload": {"type": "user_message", "message": QUOTE},
    },
    "codex-question-text": codex_message(question_reply("Tuesday", QUOTE)),
    "codex-reply-by-assistant": codex_message(
        question_reply(QUOTE, ASKED), role="assistant"
    ),
    "codex-reply-inside-brief": codex_message(
        "Read this earlier reply:\n" + question_reply(QUOTE, ASKED)
    ),
}


@pytest.mark.parametrize("row", sorted(NONHUMAN_ROWS))
def test_quote_not_in_an_original_human_row_is_not_presented_as_an_answer(
    tmp_path, row
) -> None:
    path = transcript(tmp_path, NONHUMAN_ROWS[row])
    with daemon(tmp_path, cited(path)) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result
    assert QUOTE not in json.dumps(result)


@pytest.mark.parametrize("defect", ["beyond-end", "relative", "missing-file"])
def test_citation_that_cannot_be_read_is_not_presented_as_an_answer(
    tmp_path, defect
) -> None:
    path = transcript(tmp_path, HUMAN_ROWS["typed"])
    reply = {
        "beyond-end": cited(path, line=3),
        "relative": cited(Path(path.name)),
        "missing-file": cited(tmp_path / "absent.jsonl"),
    }[defect]
    with daemon(tmp_path, reply) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result
    assert QUOTE not in json.dumps(result)


def test_completed_search_finding_no_answer_leaves_nothing(tmp_path) -> None:
    with daemon(tmp_path, verdict("not_answered")) as (endpoint, fake):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert result == {}
    assert fake.turns() == 1
    assert fake.released()


def test_go_ahead_verdict_leaves_nothing_without_search_evidence(tmp_path) -> None:
    # Only the adapter's handling of the verdict: whether Terra names
    # go-aheads well, or searches anyway, is not shown here.
    with daemon(tmp_path, verdict("go_ahead"), history=[]) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert result == {}


def test_no_answer_without_an_observed_search_warns(tmp_path) -> None:
    # The control for the go-ahead verdict: the same turn with no commands,
    # claiming a search found nothing, has shown no search.
    with daemon(tmp_path, verdict("not_answered"), history=[]) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result


UNREADABLE_REPORTS: dict[str, object] = {
    "nontext": None,
    "malformed": "unreadable history output",
    "truncated": command_report(
        "index", index_state={"freshness": "no_source_changes"}
    )[:-1],
    "trailing-broken": command_report(
        "index", index_state={"freshness": "no_source_changes"}
    )
    + "\n{broken",
    "schema": command_report(
        "index", schema_version=999, index_state={"freshness": "no_source_changes"}
    ),
    "missing": json.dumps(
        {
            "schema_version": 5,
            "event": "terminal",
            "index_state": {"freshness": "no_source_changes"},
        }
    ),
    "status": command_report("index"),
}

FAILED_LOOKUPS: dict[str, tuple[object, History | None]] = {
    "index-failed": (
        verdict("not_answered"),
        [("cc-search-chats index --json", "GPU memory allocation failed", 1), SEARCH],
    ),
    "stale-unrefreshed": (
        verdict("not_answered"),
        [
            (
                "cc-search-chats index --status --json",
                command_report("index", index_state={"freshness": "source_changes"}),
                0,
            ),
            SEARCH,
        ],
    ),
    "searched-before-refresh": (
        verdict("not_answered"),
        [status(age_ms=FIVE_MINUTES_MS), SEARCH, REFRESH],
    ),
    "unavailable": (verdict("unavailable"), None),
    **{
        f"report-{kind}": (
            verdict("not_answered"),
            [("cc-search-chats index --status --json", output, 0), SEARCH],
        )
        for kind, output in UNREADABLE_REPORTS.items()
    },
    "reply-null": (None, None),
    "reply-empty": ({}, None),
    "reply-no-reason": ({"outcome": "not_answered"}, None),
    "reply-gate-verdict": (
        {
            "outcome": "rewrite",
            "reason": "The reader cannot tell which meeting this means.",
            "evidence": {"path": "", "line": 0, "quote": ""},
        },
        None,
    ),
}


@pytest.mark.parametrize("case", sorted(FAILED_LOOKUPS))
def test_failed_or_unreadable_lookup_only_warns(tmp_path, case) -> None:
    reply, history = FAILED_LOOKUPS[case]
    with daemon(tmp_path, reply, history=history) as (endpoint, fake):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result
    assert result["systemMessage"].strip()
    assert fake.released()


@pytest.mark.parametrize(
    "command", ["cc-search-chats index --json", "git status"], ids=["history", "git"]
)
def test_approval_request_only_warns_and_is_never_granted(tmp_path, command) -> None:
    with daemon(tmp_path, verdict("not_answered"), approval=command) as (
        endpoint,
        fake,
    ):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result
    assert fake.released()
    assert not any(row.get("id") == 999 for row in fake.requests)


def test_cleanup_failure_only_warns(tmp_path) -> None:
    with daemon(tmp_path, verdict("not_answered"), failure="cleanup") as (
        endpoint,
        _,
    ):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result


PARTIAL = {"completeness": "partial", "blocked_files": 6}


@pytest.mark.parametrize(
    "index_state",
    [{"freshness": "no_source_changes"}, {"freshness": "refresh_pending", "age_ms": 1}],
    ids=["fresh", "recent-unrefreshed"],
)
def test_partial_coverage_only_warns(tmp_path, index_state) -> None:
    partial = (
        "cc-search-chats index --status --json",
        command_report("index", coverage=PARTIAL, index_state=index_state),
        0,
    )
    with daemon(tmp_path, verdict("not_answered"), history=[partial, SEARCH]) as (
        endpoint,
        _,
    ):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result


def test_verified_answer_with_partial_coverage_gives_answer_and_warning(
    tmp_path,
) -> None:
    path = transcript(tmp_path, HUMAN_ROWS["typed"])
    partial = (
        "cc-search-chats index --status --json",
        command_report(
            "index", coverage=PARTIAL, index_state={"freshness": "no_source_changes"}
        ),
        0,
    )
    with daemon(tmp_path, cited(path), history=[partial, SEARCH]) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert QUOTE in result["hookSpecificOutput"]["additionalContext"]
    assert result["systemMessage"].strip()


@pytest.mark.parametrize("age_ms", [0, FIVE_MINUTES_MS // 2, FIVE_MINUTES_MS - 1])
def test_index_under_five_minutes_old_is_searched_unrefreshed_without_warning(
    tmp_path, age_ms
) -> None:
    with daemon(
        tmp_path, verdict("not_answered"), history=[status(age_ms=age_ms), SEARCH]
    ) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert result == {}


@pytest.mark.parametrize("age_ms", [FIVE_MINUTES_MS, 10 * FIVE_MINUTES_MS])
@pytest.mark.parametrize("refreshed", [True, False], ids=["refreshed", "unrefreshed"])
def test_older_index_with_changes_must_be_refreshed_before_search(
    tmp_path, age_ms, refreshed
) -> None:
    history = [status(age_ms=age_ms), *([REFRESH] if refreshed else []), SEARCH]
    with daemon(tmp_path, verdict("not_answered"), history=history) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert (result == {}) is refreshed, result
    assert ("systemMessage" in result) is not refreshed, result


# The shape of the live failure of 2026-11-24: inside Codex's sandbox the index
# run could not create its systemd scope. The person's ruling of 2026-11-25
# ("yes", to searching the older index when it cannot be brought up to date
# inside Codex, noting that recent chats were not covered).
STALE = status(age_ms=FIVE_MINUTES_MS)
FAILED_REFRESH = (
    "/usr/bin/bash -lc 'cc-search-chats index --json'",
    json.dumps(
        {
            "schema_version": 5,
            "status": "containment_unavailable",
            "error": {"code": "systemd_scope_unavailable"},
        }
    ),
    1,
)


def interrupted(fake: Daemon) -> bool:
    """Whether the adapter ended the searcher's turn before its verdict."""
    return any(row.get("method") == "turn/interrupt" for row in fake.requests)


def test_failed_refresh_then_verified_answer_gives_answer_and_coverage_note(
    tmp_path,
) -> None:
    path = transcript(tmp_path, HUMAN_ROWS["typed"])
    history = [STALE, FAILED_REFRESH, SEARCH]
    with daemon(tmp_path, cited(path), history=history) as (endpoint, fake):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    context = result["hookSpecificOutput"]["additionalContext"]
    assert QUOTE in context
    assert f"{path}:2" in context
    assert result["systemMessage"].strip()
    assert not interrupted(fake)


def test_failed_refresh_then_no_answer_gives_the_coverage_note_alone(
    tmp_path,
) -> None:
    path = transcript(tmp_path, HUMAN_ROWS["typed"])
    outputs = {}
    for name, reply in (("found", cited(path)), ("none", verdict("not_answered"))):
        (tmp_path / name).mkdir()
        with daemon(
            tmp_path / name, reply, history=[STALE, FAILED_REFRESH, SEARCH]
        ) as (endpoint, fake):
            outputs[name] = invoke(shown(tmp_path), endpoint=endpoint)
        assert not interrupted(fake), name
    assert set(outputs["none"]) == {"systemMessage"}, outputs
    # The same note whether or not an answer was found.
    assert outputs["none"]["systemMessage"] == outputs["found"]["systemMessage"]


def test_refreshed_index_gives_a_verified_answer_without_a_note(tmp_path) -> None:
    path = transcript(tmp_path, HUMAN_ROWS["typed"])
    with daemon(tmp_path, cited(path), history=[STALE, REFRESH, SEARCH]) as (
        endpoint,
        _,
    ):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"hookSpecificOutput"}, result
    assert QUOTE in result["hookSpecificOutput"]["additionalContext"]


def failed(command: str) -> tuple[str, object, int]:
    return (command, "GPU memory allocation failed", 1)


# Only the index refresh may fail without ending the search.
FAILED_COMMANDS: dict[str, History] = {
    "status": [failed("cc-search-chats index --status --json"), SEARCH],
    "literal-search": [
        FRESH,
        failed("cc-search-chats search 'meeting day' --literal --json"),
        SEARCH,
    ],
    "semantic-search": [
        FRESH,
        failed("cc-search-chats search 'meeting day' --semantic --json"),
        SEARCH,
    ],
    "context": [
        FRESH,
        SEARCH,
        failed("cc-search-chats context ccchat:v1:claude:abc:uuid:def --json"),
    ],
    "search-after-failed-refresh": [
        STALE,
        FAILED_REFRESH,
        failed("cc-search-chats search 'meeting day' --semantic --json"),
        SEARCH,
    ],
}


@pytest.mark.parametrize("case", sorted(FAILED_COMMANDS))
def test_failed_status_search_or_context_command_ends_the_search_with_a_warning(
    tmp_path, case
) -> None:
    path = transcript(tmp_path, HUMAN_ROWS["typed"])
    with daemon(tmp_path, cited(path), history=FAILED_COMMANDS[case]) as (
        endpoint,
        fake,
    ):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result
    assert QUOTE not in json.dumps(result)
    assert interrupted(fake)
    assert fake.released()


@pytest.mark.parametrize(
    "age",
    [{}, {"age_ms": None}, {"age_ms": "60000"}, {"age_ms": True}],
    ids=["missing", "null", "text", "boolean"],
)
def test_unknown_index_age_is_not_treated_as_recent(tmp_path, age) -> None:
    with daemon(tmp_path, verdict("not_answered"), history=[status(**age), SEARCH]) as (
        endpoint,
        _,
    ):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result


def test_terminal_events_before_each_report_still_show_a_refreshed_search(
    tmp_path,
) -> None:
    # Framing observed in a real 0.167 completed command: stderr's terminal
    # JSON event precedes stdout's command report in aggregatedOutput.
    terminal = json.dumps(
        {
            "schema_version": 5,
            "event": "terminal",
            "index_state": {"freshness": "refresh_pending"},
        }
    )
    history: History = [
        (
            "/usr/bin/bash -lc 'cc-search-chats index --status --json'",
            terminal
            + "\n"
            + command_report("index", index_state={"freshness": "refresh_pending"})
            + "\n",
            0,
        ),
        (
            "cc-search-chats index --json",
            terminal + "\n" + command_report("index", refresh={"state": "complete"}),
            0,
        ),
        (
            "cc-search-chats search 'meeting day' --json",
            terminal + "\n" + command_report("search", results=[]),
            0,
        ),
    ]
    with daemon(tmp_path, verdict("not_answered"), history=history) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert result == {}


# Seen in live Terra searches on 2026-11-24: commands naming the search whose
# output is not cc-search-chats's JSON report.
NOT_REPORTS = {
    "piped": (
        "/usr/bin/bash -lc \"cc-search-chats search --literal --json 'meeting day' "
        "| python3 -c 'import sys; print(sys.stdin.read()[:80])'\"",
        '[["ccchat:v1:claude:abc:uuid:def", "Tuesday works"]]',
        0,
    ),
    "help": (
        "/usr/bin/bash -lc 'cc-search-chats search --help'",
        "usage: cc-search-chats search [-h] [--json] [--progress {auto,ndjson,human}]",
        0,
    ),
}
SHELL_WRAPPED_SEARCH = (
    "/usr/bin/bash -lc \"cc-search-chats search --literal --json 'meeting day'\"",
    command_report("search", results=[]),
    0,
)


@pytest.mark.parametrize("other", sorted(NOT_REPORTS))
@pytest.mark.parametrize("search", [SEARCH, SHELL_WRAPPED_SEARCH], ids=["bare", "bash"])
def test_command_whose_output_is_not_a_report_is_not_read_as_one(
    tmp_path, search, other
) -> None:
    history = [FRESH, NOT_REPORTS[other], search]
    with daemon(tmp_path, verdict("not_answered"), history=history) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert result == {}


@pytest.mark.parametrize("other", sorted(NOT_REPORTS))
def test_command_whose_output_is_not_a_report_is_no_search_evidence(
    tmp_path, other
) -> None:
    with daemon(
        tmp_path, verdict("not_answered"), history=[FRESH, NOT_REPORTS[other]]
    ) as (endpoint, _):
        result = invoke(shown(tmp_path), endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result


def test_search_runs_in_a_fresh_released_terra_thread(tmp_path) -> None:
    with daemon(tmp_path, verdict("not_answered")) as (endpoint, fake):
        invoke(shown(tmp_path), endpoint=endpoint)
    start = next(
        row["params"] for row in fake.requests if row.get("method") == "thread/start"
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
    turn = next(
        row["params"] for row in fake.requests if row.get("method") == "turn/start"
    )
    assert turn["effort"] == "xhigh"
    assert "asking-session" not in json.dumps(turn["input"])
    assert fake.turns() == 1
    assert fake.released()


def test_choice_question_is_searched_with_its_native_options(tmp_path) -> None:
    payload = shown(tmp_path)
    payload["tool_input"]["questions"][0]["options"] = [
        {"label": "Tuesday", "description": "Meet Tuesday morning."},
        {"label": "Thursday", "description": "Meet Thursday morning."},
    ]
    with daemon(tmp_path, verdict("not_answered")) as (endpoint, fake):
        invoke(payload, endpoint=endpoint)
    submitted = json.dumps(
        next(
            row["params"]["input"]
            for row in fake.requests
            if row.get("method") == "turn/start"
        )
    )
    assert "Tuesday" in submitted
    assert "Thursday" in submitted


@pytest.mark.parametrize("tool", ["request_user_input", "Bash"])
def test_other_tools_start_no_search(tmp_path, tool) -> None:
    # A synchronous question is not searched: its PostToolUse is taken to come
    # after the person answered (inferred from Codex's source, untested).
    with daemon(tmp_path, verdict("not_answered")) as (endpoint, fake):
        result = invoke(shown(tmp_path, tool=tool), endpoint=endpoint)
    assert result == {}
    assert fake.requests == []


@pytest.mark.parametrize("defect", ["not-object", "no-questions", "relative-cwd"])
def test_unreadable_hook_input_warns_without_a_search(tmp_path, defect) -> None:
    payload: object = shown(tmp_path)
    assert isinstance(payload, dict)
    if defect == "not-object":
        payload = [payload]
    elif defect == "no-questions":
        payload["tool_input"] = {}
    else:
        payload["cwd"] = "project"
    with daemon(tmp_path, verdict("not_answered")) as (endpoint, fake):
        result = invoke(payload, endpoint=endpoint)
    assert set(result) == {"systemMessage"}, result
    assert fake.requests == []


def test_search_deadline_interrupts_and_unsubscribes(tmp_path, monkeypatch) -> None:
    with daemon(tmp_path, verdict("not_answered"), failure="hang") as (
        endpoint,
        fake,
    ):
        monkeypatch.setenv("QUESTION_ZONE_CODEX_SOCKET", endpoint)
        started = time.monotonic()
        with pytest.raises(Unavailable, match=r"response unavailable|deadline"):
            check(Question("Which day works for you?", str(tmp_path)), timeout=0.15)
        elapsed = time.monotonic() - started
    assert elapsed < 2
    assert any(row.get("method") == "turn/interrupt" for row in fake.requests)
    assert fake.released()


def test_no_hook_can_hold_a_question_before_or_after_it_is_shown() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    question_handlers = [
        (event, tool, handler)
        for event, groups in manifest["hooks"].items()
        for group in groups
        for tool in QUESTION_TOOLS
        if re.search(group.get("matcher", ""), tool)
        for handler in group["hooks"]
    ]
    # Positive control: the background search does run for a shown question.
    assert ("PostToolUse", "request_user_input_async") in {
        (event, tool) for event, tool, _ in question_handlers
    }
    for event, tool, handler in question_handlers:
        assert event == "PostToolUse", (event, tool)
        assert handler.get("async") is True, (event, tool, handler)
