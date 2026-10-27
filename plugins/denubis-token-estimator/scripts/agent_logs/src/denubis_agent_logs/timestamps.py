"""Parse the timestamps Claude Code and Codex write into their logs."""

from __future__ import annotations

from datetime import datetime


def parse_timestamp(value: object) -> datetime | None:
    """Return ``value`` as an aware datetime, or ``None`` when it is not one.

    Claude Code and Codex write ISO 8601 strings ending in ``Z``, which
    :meth:`datetime.fromisoformat` accepts. A string without a UTC offset names no
    single instant, so it parses to ``None`` rather than to a naive datetime that
    would later fail to compare with an aware one. Non-strings parse to ``None``.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.utcoffset() is None:
        return None
    return parsed
