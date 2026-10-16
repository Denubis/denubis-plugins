"""Resolve current Codex footer identity without treating terminal text as authority."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

SETUP_INSTRUCTIONS = (
    "In this source Codex, run /statusline, enable thread-id and move it first. "
    "Keep the existing model/context fields, save, and close the picker. "
    "Editing config.toml alone does not refresh an existing client."
)
SGR = re.compile(r"\x1b\[[0-9;:]*m")
FOOTER_ID = re.compile(
    r"^  ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(?:$| · )"
)
FOOTER_HINTS = re.compile(
    r"^  (?:[^·\n]+ for agents · )?[^·\n]+ for shortcuts(?: {2,}.*)?$"
)


@dataclass(frozen=True)
class IdentityResult:
    thread_id: str | None
    status: str
    reason: str
    pane_key: tuple[object, ...]
    changed: bool = False


def result(
    thread_id: str | None,
    status: str,
    reason: str,
    pane_key: tuple[object, ...],
    previous: IdentityResult | None,
) -> IdentityResult:
    changed = previous is not None and (
        previous.thread_id != thread_id or previous.pane_key != pane_key
    )
    return IdentityResult(thread_id, status, reason, pane_key, changed)


def native_footer(preview: str, height: int | None) -> str | None:
    """Recognize the current composer/footer frame, rather than searching a transcript.

    Codex 0.162.1 puts its configured status line before the final shortcut row,
    below a blank row and the single-line composer. Other layouts fail closed:
    this association decorates server requests and never authorizes an answer.
    """
    rows = preview.splitlines()
    if len(rows) < 4 or (height is not None and len(rows) != height):
        return None
    composer, blank, footer, hints = (SGR.sub("", row).rstrip(" ") for row in rows[-4:])
    if not composer.startswith("\u203a") or blank:
        return None
    if FOOTER_HINTS.fullmatch(hints) is None or "\x1b" in footer:
        return None
    return footer


class CodexIdentity:
    """Resolve fresh frames; previous results only describe changes."""

    @staticmethod
    def resolve(
        preview: str,
        *,
        pane_key: tuple[object, ...],
        loaded_threads: Collection[str],
        height: int | None = None,
        previous: IdentityResult | None = None,
    ) -> IdentityResult:
        if not pane_key or any(value is None or value == "" for value in pane_key):
            return result(
                None,
                "unavailable",
                "Pane process identity is unverified",
                pane_key,
                previous,
            )
        footer = native_footer(preview, height)
        if footer is None:
            return result(
                None,
                "unavailable",
                "Native footer is covered, clipped or unrecognized",
                pane_key,
                previous,
            )
        found = FOOTER_ID.match(footer)
        if found is None:
            return result(
                None, "setup_required", SETUP_INSTRUCTIONS, pane_key, previous
            )
        thread_id = found[1]
        if thread_id not in loaded_threads:
            return result(
                None,
                "not_loaded",
                "Native footer thread is not loaded on this Codex server",
                pane_key,
                previous,
            )
        return result(
            thread_id, "linked", "Full native Codex footer UUID", pane_key, previous
        )
