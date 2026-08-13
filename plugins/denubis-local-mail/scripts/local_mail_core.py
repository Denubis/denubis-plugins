"""Validation shared by the local-mail MCP server and CLI."""

from __future__ import annotations

import re

ADDRESS_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
MAX_SUBJECT_LENGTH = 160


class MailValidationError(ValueError):
    """Raised when a caller supplies invalid mail data."""


def validate_address(address: str) -> str:
    canonical = address.strip().lower()
    if not ADDRESS_PATTERN.fullmatch(canonical):
        raise MailValidationError("invalid mailbox address")
    return canonical


def require_text(value: str, field: str) -> str:
    if not value.strip():
        raise MailValidationError(f"{field} must not be blank")
    return value


def validate_subject(subject: str) -> str:
    require_text(subject, "subject")
    if "\n" in subject or "\r" in subject:
        raise MailValidationError("subject must be a single line")
    if len(subject) > MAX_SUBJECT_LENGTH:
        raise MailValidationError(
            f"subject must be at most {MAX_SUBJECT_LENGTH} characters"
        )
    if any(ord(character) < 32 for character in subject):
        raise MailValidationError("subject must not contain control characters")
    return subject
