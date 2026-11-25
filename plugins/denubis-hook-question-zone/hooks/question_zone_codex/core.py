"""Read a shown question, the searcher's verdict, and original human evidence."""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path


class Unavailable(RuntimeError):
    """The search could not establish a result."""


@dataclass(frozen=True)
class Question:
    text: str
    cwd: str


def question_from_event(event: object) -> Question | None:
    if not isinstance(event, dict):
        raise Unavailable("hook input must be a JSON object")
    # A synchronous question is not searched: its PostToolUse is taken to run
    # only once the person has answered (inferred from Codex's source, untested).
    if event.get("tool_name") != "request_user_input_async":
        return None
    if event.get("hook_event_name") != "PostToolUse":
        raise Unavailable("the search runs only after a question is shown")
    tool_input = event.get("tool_input")
    questions = tool_input.get("questions") if isinstance(tool_input, dict) else None
    if not isinstance(questions, list) or not questions:
        raise Unavailable("hook input does not contain the question that was shown")
    cwd = event.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise Unavailable("hook did not supply an absolute project directory")
    return Question(json.dumps(questions, ensure_ascii=False), cwd)


@dataclass(frozen=True)
class Citation:
    path: str
    line: int
    quote: str


@dataclass(frozen=True)
class Verdict:
    outcome: str
    reason: str
    citation: Citation | None = None


OUTCOMES = ("answered", "not_answered", "go_ahead", "unavailable")

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": list(OUTCOMES)},
        "reason": {"type": "string"},
        "evidence": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {"type": "integer"},
                "quote": {"type": "string"},
            },
            "required": ["path", "line", "quote"],
            "additionalProperties": False,
        },
    },
    "required": ["outcome", "reason", "evidence"],
    "additionalProperties": False,
}


# Text the person did not type inside a row they did: lines quoted with "> "
# (as the question box quotes the question) or "\u258e" (a terminal's quote
# bar), and blocks Claude Code inserts around pastes and slash commands.
QUOTED_LINE = re.compile(r"^\s*[>\u258e]")
HARNESS_BLOCK = re.compile(
    r"<(pasted_content|command-message|command-name|local-command-stdout)\b[^>]*>"
    r".*?</\1\b[^>]*>",
    re.S,
)
CODEX_REPLY = re.compile(
    r"\s*<send_user_message_question_reply>(.*)</send_user_message_question_reply>\s*",
    re.S,
)


def _person_text(record: object) -> str:
    """Words a row shows the person typed; empty where the row cannot show that.

    Claude Code marks a prompt the person typed, sent or queued, with origin
    kind human (from June 2026). In Codex only an answer given in its question
    box is marked: typed messages are recorded exactly like briefs an agent
    types into the pane, and older user_message events likewise.
    """
    if (
        not isinstance(record, dict)
        or record.get("isCompactSummary")
        or record.get("isMeta")
    ):
        return ""
    if record.get("type") == "user":
        message = record.get("message")
        if (
            _typed_by_person(record.get("origin"))
            and isinstance(message, dict)
            and message.get("role") == "user"
        ):
            return _own_words(_content_text(message.get("content")))
    if record.get("type") == "attachment":
        attachment = record.get("attachment")
        if (
            isinstance(attachment, dict)
            and attachment.get("type") == "queued_command"
            and _typed_by_person(attachment.get("origin"))
        ):
            return _own_words(_content_text(attachment.get("prompt")))
    if record.get("type") == "response_item":
        return _codex_answers(record.get("payload"))
    return ""


def _typed_by_person(origin: object) -> bool:
    return isinstance(origin, dict) and origin.get("kind") == "human"


def _own_words(text: str) -> str:
    text = HARNESS_BLOCK.sub("\n", text)
    return "\n".join(line for line in text.splitlines() if not QUOTED_LINE.match(line))


def _codex_answers(payload: object) -> str:
    """The answers in a Codex question-box reply, never the questions."""
    if not isinstance(payload, dict) or payload.get("role") != "user":
        return ""
    reply = CODEX_REPLY.fullmatch(_content_text(payload.get("content")))
    try:
        items = json.loads(reply[1]) if reply else None
    except ValueError:
        return ""
    if not isinstance(items, list):
        return ""
    return "\n".join(
        item["answer"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("answer"), str)
    )


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") in ("text", "input_text")
            and isinstance(item.get("text"), str)
        )
    return ""


def verify_evidence(evidence: dict) -> Citation:
    path, line, quote = (evidence.get(key) for key in ("path", "line", "quote"))
    if (
        not isinstance(path, str)
        or not Path(path).is_absolute()
        or not isinstance(line, int)
        or isinstance(line, bool)
        or line < 1
        or not isinstance(quote, str)
        or not quote.strip()
    ):
        raise Unavailable("answered verdict lacks an original transcript citation")
    deadline = time.monotonic() + 5
    try:
        if not Path(path).is_file():
            raise Unavailable("original transcript is not a regular file")
        with Path(path).open(encoding="utf-8") as stream:
            for number, text in enumerate(stream, 1):
                if time.monotonic() >= deadline:
                    raise Unavailable("original human citation lookup timed out")
                if number == line:
                    if quote not in _person_text(json.loads(text)):
                        raise Unavailable(
                            "cited words cannot be shown to be words the person "
                            "typed in that row"
                        )
                    return Citation(path, line, quote)
    except (OSError, ValueError) as error:
        raise Unavailable(f"cannot verify original human citation: {error}") from error
    raise Unavailable("original human citation points beyond the transcript")


def parse_verdict(text: str) -> Verdict:
    try:
        data = json.loads(text)
    except ValueError as error:
        raise Unavailable("searcher returned invalid JSON") from error
    if (
        not isinstance(data, dict)
        or set(data) != {"outcome", "reason", "evidence"}
        or data.get("outcome") not in OUTCOMES
        or not isinstance(data.get("reason"), str)
        or not data["reason"].strip()
        or not isinstance(data.get("evidence"), dict)
    ):
        raise Unavailable("searcher verdict does not match the response schema")
    citation = (
        verify_evidence(data["evidence"]) if data["outcome"] == "answered" else None
    )
    return Verdict(data["outcome"], data["reason"], citation)


@dataclass(frozen=True)
class Finding:
    """What the search leaves: an earlier answer, a warning, or nothing."""

    answer: Citation | None = None
    warning: str = ""


def hook_output(finding: Finding) -> dict:
    """PostToolUse output that can add context or warn, never hold the question."""
    result: dict[str, object] = {}
    if finding.answer is not None:
        answer = finding.answer
        result["hookSpecificOutput"] = {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "question-zone: The person may already have answered the question "
                "you just showed them. These are their own earlier words, at "
                f"{answer.path}:{answer.line}: “{answer.quote}”. Show "
                "them this earlier answer and where it is from, and let them "
                "confirm or change it. Do not act on it before they reply, and do "
                "not take it as approval of what the question asks about."
            ),
        }
    if finding.warning:
        result["systemMessage"] = (
            "question-zone: the search for an earlier answer to the question "
            f"just shown was incomplete: {finding.warning} The question stays "
            "shown; this warning authorises nothing."
        )
    return result
