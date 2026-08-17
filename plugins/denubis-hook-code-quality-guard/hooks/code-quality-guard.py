#!/usr/bin/env python3
"""Block concrete code writes that bypass user-facing tests or migrations."""

from __future__ import annotations

import json
import re
import shlex
import sys

_USER_SURFACE_TEST = re.compile(
    r"tests?/(?:e2e|playwright|integration)/.*\.(?:py|ts|js)$"
)
_JAVASCRIPT_INJECTION = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bpage\.evaluate\(",
        r"\bui\.run_javascript\(",
        r"\bpage\.add_script_tag\(",
        r"\bpage\.add_init_script\(",
    )
)
_DIRECT_SCHEMA_CREATION = re.compile(r"\b(?:SQLModel\.)?metadata\.create_all\(")
_PATCH_FILE_HEADER = re.compile(r"^\*\*\* (?:Add|Update) File: (.+)$")
_PATCH_MOVE_HEADER = re.compile(r"^\*\*\* Move to: (.+)$")
_HEREDOC = re.compile(r"(?<!<)<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*['\"]?")
_CAT_COMMAND = re.compile(r"(?:^|[;&|]\s*)cat(?:\s|$)")
_TEE_COMMAND = re.compile(r"(?:^|[;&|]\s*)tee(?:\s|$)")
_FILE_REDIRECTION = re.compile(r"(?<![<>])>>?(?![<>])")
_SHELL_CONTROLS = frozenset({"|", "||", ";", ";;", "&", "&&", ">", ">>"})


def _new_text(input_data: dict) -> str:
    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return ""
    return tool_input.get("content", "") or tool_input.get("new_string", "")


def _file_path(input_data: dict) -> str:
    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return ""
    return tool_input.get("file_path", "")


def _patch_writes(input_data: dict) -> list[tuple[str, str]]:
    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return []
    command = tool_input.get("command", "")
    if not isinstance(command, str):
        return []

    writes: list[tuple[str, str]] = []
    file_path: str | None = None
    additions: list[str] = []

    def flush() -> None:
        if file_path is not None:
            writes.append((file_path, "\n".join(additions)))

    for line in command.splitlines():
        file_match = _PATCH_FILE_HEADER.match(line)
        if file_match:
            flush()
            file_path = file_match.group(1)
            additions = []
            continue

        move_match = _PATCH_MOVE_HEADER.match(line)
        if move_match and file_path is not None:
            file_path = move_match.group(1)
            continue

        if line.startswith("*** Delete File:") or line == "*** End Patch":
            flush()
            file_path = None
            additions = []
            continue

        if file_path is not None and line.startswith("+"):
            additions.append(line[1:])

    flush()
    return writes


def _writes(input_data: dict) -> list[tuple[str, str]]:
    if input_data.get("tool_name") == "apply_patch":
        return _patch_writes(input_data)

    file_path = _file_path(input_data)
    new_text = _new_text(input_data)
    if not isinstance(file_path, str) or not isinstance(new_text, str):
        return []
    return [(file_path, new_text)]


def _bash_command(input_data: dict) -> str:
    tool_input = input_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command", "")
    return command if isinstance(command, str) else ""


def _tee_writes_file(line: str) -> bool:
    lexer = shlex.shlex(line, posix=True, punctuation_chars="|;&<>")
    lexer.commenters = ""
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return False
    for index, shell_word in enumerate(tokens):
        if shell_word != "tee":
            continue
        options_finished = False
        for candidate in tokens[index + 1 :]:
            if candidate in _SHELL_CONTROLS:
                break
            if not options_finished and candidate == "--":
                options_finished = True
                continue
            if not options_finished and candidate.startswith("-"):
                continue
            if candidate != "/dev/null":
                return True
    return False


def _heredoc_file_write_reason(command: str) -> str | None:
    for line in command.splitlines():
        if not _HEREDOC.search(line):
            continue
        without_heredoc = _HEREDOC.sub("", line)
        streamed_to_file = _FILE_REDIRECTION.search(without_heredoc) and (
            _CAT_COMMAND.search(line) or _TEE_COMMAND.search(line)
        )
        if not streamed_to_file and not _tee_writes_file(without_heredoc):
            continue
        return """BLOCKED: shell heredoc used to author a file.

Use Claude's structured Write/Edit tool for model-authored file content. Do not use
cat, tee, shell redirection, or a heredoc as a substitute for the file-editing tools."""
    return None


def _javascript_injection_reason(file_path: str, new_text: str) -> str | None:
    if not _USER_SURFACE_TEST.search(file_path):
        return None
    if not any(pattern.search(new_text) for pattern in _JAVASCRIPT_INJECTION):
        return None

    return """BLOCKED: JavaScript injection in a user-surface test.

Use Playwright's native mouse, keyboard, locator, and assertion APIs so the test
exercises the browser event pipeline. page.evaluate(), run_javascript(), and script
injection bypass the interaction being tested and can pass for the wrong reason."""


def _direct_schema_creation_reason(file_path: str, new_text: str) -> str | None:
    if "alembic/versions/" in file_path:
        return None
    if not _DIRECT_SCHEMA_CREATION.search(new_text):
        return None

    return """BLOCKED: metadata.create_all() outside an Alembic migration.

Direct schema creation bypasses migration history and can cause schema drift. Create,
review, apply, and reversal-test an Alembic migration instead."""


def _deny(reason: str, *, include_system_message: bool) -> dict:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }
    if include_system_message:
        output["systemMessage"] = reason
    return output


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if not isinstance(input_data, dict) or input_data.get("tool_name") not in {
        "Write",
        "Edit",
        "apply_patch",
        "Bash",
    }:
        return 0

    if input_data.get("tool_name") == "Bash":
        reason = _heredoc_file_write_reason(_bash_command(input_data))
        if reason:
            print(json.dumps(_deny(reason, include_system_message=True)))
            return 2
        return 0

    codex_input = input_data.get("tool_name") == "apply_patch"
    for file_path, new_text in _writes(input_data):
        for check in (_javascript_injection_reason, _direct_schema_creation_reason):
            reason = check(file_path, new_text)
            if reason:
                print(json.dumps(_deny(reason, include_system_message=not codex_input)))
                return 0 if codex_input else 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
