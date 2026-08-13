"""Better BibTeX helpers - parsing-only, no network dependencies.

Kept separate from ingest.py so the parsing logic is unit-testable without
needing httpx or a running Zotero. Extend here when BBT-emitted formats
change in ways the simple regex can't follow.
"""

from __future__ import annotations

import re
from pathlib import Path

_FILE_FIELD_RE = re.compile(r"file\s*=\s*\{([^}]*)\}")
_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _unescape_biblatex_colons(s: str) -> str:
    """Unescape `\\:` -> `:` only.

    BBT/JabRef escape the drive-letter colon on Windows (`C\\:\\Users\\...`).
    Other backslashes in the path (`\\U`, `\\j` etc.) are NOT escapes - they
    are literal directory separators - so we must not touch them. A naive
    universal unescape (`\\\\(.)` -> `\\1`) destroys Windows paths.
    """
    return s.replace("\\:", ":")


def parse_attachment_paths(bib: str) -> list[Path]:
    """Extract renderable attachment paths from a BibLaTeX `file` field.

    BBT format per entry: `<label>:<path>:<mime>`, entries `;`-separated.
    On Windows the path contains a drive-letter colon (`C:\\Users\\...`)
    that collides with naive `.split(':')`. We split, then re-glue the
    middle tokens whenever the first middle token looks like a drive
    letter (`^[A-Za-z]:[\\/]?`).

    PDFs are preferred; otherwise Zotero HTML snapshots are returned.
    """
    m = _FILE_FIELD_RE.search(bib)
    if not m:
        return []

    paths: list[Path] = []
    for raw_entry in m.group(1).split(";"):
        entry = _unescape_biblatex_colons(raw_entry.strip())
        if not entry:
            continue
        tokens = entry.split(":")
        if len(tokens) < 2:
            continue

        path_str = _extract_path(tokens)
        if path_str:
            paths.append(Path(path_str))
    return sorted(
        paths,
        key=lambda path: (
            path.suffix.lower() != ".pdf",
            path.suffix.lower() not in {".html", ".htm"},
        ),
    )


def parse_pdf_paths(bib: str) -> list[Path]:
    """Backward-compatible PDF-only view of :func:`parse_attachment_paths`."""
    return [p for p in parse_attachment_paths(bib) if p.suffix.lower() == ".pdf"]


def _extract_path(tokens: list[str]) -> str:
    """Pick the path token out of a `:`-split BBT file entry.

    Handles three shapes:
      - Linux/macOS: `["label", "/abs/path/file.pdf", "application/pdf"]`
      - Windows unescaped: `["label", "C", "\\path\\file.pdf", "application/pdf"]`
      - Windows escaped (already de-escaped above): same as unescaped after
        the `\\:` -> `:` pass.
    """
    if len(tokens) == 2:
        return tokens[1].strip()

    # Linux case: middle token is the whole path.
    if len(tokens) == 3:
        return tokens[1].strip()

    # 4+ tokens: probable Windows drive-letter split. Drop label (tokens[0])
    # and mime (tokens[-1]); rejoin the middle with `:`.
    middle = tokens[1:-1]
    candidate = ":".join(middle).strip()

    # Sanity-check: the rejoined middle should start with a drive letter
    # (`X:\\` or `X:/`). If not, fall back to the longest middle token
    # (best-effort for unexpected shapes).
    if _DRIVE_LETTER_RE.match(candidate):
        return candidate
    return max(middle, key=len).strip()
