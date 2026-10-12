"""Tests for using-bibliography/blockquote.py.

The helper proves that a string occurs in rendered page Markdown, which LOCATES
a passage. It never verifies wording against the source document, so every hit
is labelled `located` and a miss is labelled `unverified` (Contract 1, design
2026-10-12). Exercised as a subprocess over a temporary pages/ directory, the
way the skill text invokes it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_BLOCKQUOTE = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "blockquote.py"
)


def _pages(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "001.md").write_text("Nothing of note here.\n", encoding="utf-8")
    (pages / "002.md").write_text(
        "The device paradigm  conceals the\nmachinery of a commodity.\n",
        encoding="utf-8",
    )
    return pages


def _run(pages, query):
    return subprocess.run(
        [sys.executable, str(_BLOCKQUOTE), str(pages), "borgmann1984", query],
        capture_output=True,
        text=True,
    )


def test_a_hit_is_a_page_keyed_blockquote_labelled_located(tmp_path):
    # The query spans a double space and a line break in the render; the
    # helper normalises whitespace for the match and echoes the query.
    result = _run(_pages(tmp_path), "device paradigm conceals the machinery")
    assert result.returncode == 0
    assert "> device paradigm conceals the machinery" in result.stdout
    assert "[@borgmann1984, p. 2]" in result.stdout
    assert "Verification: located" in result.stdout


def test_located_is_never_called_verified(tmp_path):
    result = _run(_pages(tmp_path), "device paradigm")
    lines = [line for line in result.stdout.splitlines() if "Verification" in line]
    assert lines == [
        "Verification: located (render match; check the source page before "
        "calling it verified)"
    ]


def test_no_match_is_unverified_and_exits_2(tmp_path):
    result = _run(_pages(tmp_path), "words that are not on any page")
    assert result.returncode == 2
    assert "NO MATCH" in result.stderr
    assert "Verification: unverified" in result.stderr
    assert result.stdout == ""
