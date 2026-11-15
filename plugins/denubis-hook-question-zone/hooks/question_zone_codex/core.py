"""Validate questions, checker verdicts, and original human evidence."""

import json
import time
from dataclasses import dataclass
from pathlib import Path


class Unavailable(RuntimeError):
    """The check could not establish an answer."""


class HistoryUnavailable(Unavailable):
    """History lookup failed after the question passed clarity review."""


class Rewrite(ValueError):
    """The proposed question does not meet the input contract."""


@dataclass(frozen=True)
class Question:
    text: str
    cwd: str


def question_from_event(event: object) -> Question | None:
    if not isinstance(event, dict):
        raise Unavailable("hook input must be a JSON object")
    if event.get("tool_name") not in (
        "request_user_input",
        "request_user_input_async",
    ):
        return None
    if event.get("hook_event_name") != "PreToolUse":
        raise Unavailable("question gate requires PreToolUse")
    tool_input = event.get("tool_input")
    questions = tool_input.get("questions") if isinstance(tool_input, dict) else None
    if not isinstance(questions, list) or len(questions) != 1:
        raise Rewrite("Ask exactly one question at a time.")
    question = questions[0]
    if not isinstance(question, dict):
        raise Rewrite("Give one question with its full context in plain words.")
    field = "title" if event["tool_name"].endswith("_async") else "question"
    text = question.get(field)
    if not isinstance(text, str) or not text.strip():
        raise Rewrite("Give one nonempty question with its full context.")
    cwd = event.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise Unavailable("hook did not supply an absolute project directory")
    return Question(json.dumps(question, ensure_ascii=False), cwd)


@dataclass(frozen=True)
class Verdict:
    outcome: str
    reason: str
    evidence: str = ""
    warning: str = ""


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {
            "type": "string",
            "enum": ["clear", "answered", "rewrite", "unavailable"],
        },
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


def _human_text(record: object) -> str:
    """Only original transcript rows, never a decision record's paraphrase."""
    if (
        not isinstance(record, dict)
        or record.get("isCompactSummary")
        or record.get("isMeta")
    ):
        return ""
    if record.get("type") == "user":
        origin = record.get("origin", {})
        message = record.get("message", {})
        if (
            isinstance(origin, dict)
            and origin.get("kind", "human") == "human"
            and isinstance(message, dict)
            and message.get("role") == "user"
        ):
            return _content_text(message.get("content"))
    if record.get("type") == "attachment":
        attachment = record.get("attachment", {})
        if (
            isinstance(attachment, dict)
            and attachment.get("type") == "queued_command"
            and attachment.get("origin") == {"kind": "human"}
        ):
            return _content_text(attachment.get("prompt"))
    if record.get("type") == "response_item":
        return _codex_human_text(record)
    if record.get("type") == "event_msg":
        payload = record.get("payload", {})
        if isinstance(payload, dict) and payload.get("type") == "user_message":
            message = payload.get("message")
            return message if isinstance(message, str) else ""
    return ""


def _codex_human_text(record: dict) -> str:
    """Recognize retained human input, excluding harness-authored user context."""
    payload = record.get("payload")
    metadata = record.get("metadata")
    if not isinstance(payload, dict) or not isinstance(metadata, dict):
        return ""
    retained = metadata.get("retained_source")
    if not isinstance(retained, dict):
        return ""
    identity = retained.get("id")
    if (
        payload.get("type") != "message"
        or payload.get("role") != "user"
        or not isinstance(payload.get("id"), str)
        or metadata.get("client_authored") is not False
        or retained.get("complete") is not True
        or not isinstance(identity, dict)
        or identity.get("role") != "user"
        or identity.get("message_id") != payload["id"]
    ):
        return ""
    return _content_text(payload.get("content"))


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


def verify_evidence(evidence: dict) -> str:
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
                    if quote not in _human_text(json.loads(text)):
                        raise Unavailable(
                            "cited words are not in an original human row"
                        )
                    return f"{path}:{line}: {quote}"
    except (OSError, ValueError) as error:
        raise Unavailable(f"cannot verify original human citation: {error}") from error
    raise Unavailable("original human citation points beyond the transcript")


def parse_verdict(text: str) -> Verdict:
    try:
        data = json.loads(text)
    except ValueError as error:
        raise Unavailable("checker returned invalid JSON") from error
    if (
        not isinstance(data, dict)
        or set(data) != {"outcome", "reason", "evidence"}
        or data.get("outcome") not in ("clear", "answered", "rewrite", "unavailable")
        or not isinstance(data.get("reason"), str)
        or not data["reason"].strip()
        or not isinstance(data.get("evidence"), dict)
    ):
        raise Unavailable("checker verdict does not match the response schema")
    citation = (
        verify_evidence(data["evidence"]) if data["outcome"] == "answered" else ""
    )
    return Verdict(data["outcome"], data["reason"], citation)


def hook_output(verdict: Verdict) -> dict:
    output = {"hookEventName": "PreToolUse"}
    if verdict.outcome != "clear":
        output["permissionDecision"] = "deny"
        action = {
            "answered": "Use the existing answer instead of asking again.",
            "rewrite": (
                "Rewrite the question and try again without discussing the rewrite "
                "in chat."
            ),
            "unavailable": (
                "Tell the person once what stopped the check. Do not ask this question "
                "until the cause is resolved."
            ),
        }[verdict.outcome]
        output["permissionDecisionReason"] = (
            f"question-zone ({verdict.outcome}): {verdict.reason} {action}"
            + (
                f" Original human evidence: {verdict.evidence}"
                if verdict.evidence
                else ""
            )
        )
    result: dict[str, object] = {"hookSpecificOutput": output}
    if verdict.outcome == "clear" and verdict.warning:
        result["systemMessage"] = (
            f"question-zone: history warning: {verdict.warning} "
            "The question may be asked; this does not authorize the action."
        )
    return result
