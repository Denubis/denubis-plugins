"""Tests for plugins/denubis-academic/skills/using-bibliography/bbt.py.

Path-shape coverage for parse_pdf_paths: Linux/macOS, Windows (unescaped
and BibLaTeX-escaped drive-letter colon), multi-attachment entries,
snapshot/non-PDF entries, missing or malformed file fields.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_BBT = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "bbt.py"
)


def _load_bbt():
    spec = importlib.util.spec_from_file_location("bbt_under_test", _BBT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bbt_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


bbt = _load_bbt()


def _wrap(file_field: str) -> str:
    """Wrap a `file = {...}` body in a minimal BibLaTeX entry skeleton."""
    return "@article{key,\n  title = {x},\n  file = {" + file_field + "}\n}"


# --- Linux / macOS shape --------------------------------------------------


def test_linux_single_pdf():
    bib = _wrap("Full Text:/home/u/Zotero/storage/ABCD/paper.pdf:application/pdf")
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path("/home/u/Zotero/storage/ABCD/paper.pdf")]


def test_linux_label_with_space():
    bib = _wrap("Submitted Version:/home/u/Zotero/storage/X/p.pdf:application/pdf")
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path("/home/u/Zotero/storage/X/p.pdf")]


# --- Windows shapes -------------------------------------------------------


def test_windows_unescaped_drive_letter():
    """The shape Brian's parser couldn't handle in 0.2.1 and earlier."""
    bib = _wrap(
        r"Full Text:C:\Users\example\Zotero\storage\XYZ\paper.pdf:application/pdf"
    )
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path(r"C:\Users\example\Zotero\storage\XYZ\paper.pdf")]


def test_windows_escaped_drive_letter():
    """BibLaTeX convention escapes `:` as `\\:`."""
    bib = _wrap(
        r"Full Text:C\:\Users\example\Zotero\storage\XYZ\paper.pdf:application/pdf"
    )
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path(r"C:\Users\example\Zotero\storage\XYZ\paper.pdf")]


def test_windows_forward_slash_drive_letter():
    """Some BBT versions normalise to forward slashes after the drive letter."""
    bib = _wrap(
        "Full Text:C:/Users/example/Zotero/storage/XYZ/paper.pdf:application/pdf"
    )
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path("C:/Users/example/Zotero/storage/XYZ/paper.pdf")]


# --- Multi-entry ----------------------------------------------------------


def test_multiple_entries_pdf_plus_snapshot():
    """item.export often returns the PDF and a webpage snapshot together."""
    bib = _wrap(
        "Full Text:/home/u/Zotero/storage/A/paper.pdf:application/pdf;"
        "Snapshot:/home/u/Zotero/storage/B/index.html:text/html"
    )
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path("/home/u/Zotero/storage/A/paper.pdf")]


def test_multiple_pdfs_keeps_both():
    bib = _wrap(
        "Submitted:/home/u/Zotero/storage/A/v1.pdf:application/pdf;"
        "Accepted:/home/u/Zotero/storage/B/v2.pdf:application/pdf"
    )
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [
        Path("/home/u/Zotero/storage/A/v1.pdf"),
        Path("/home/u/Zotero/storage/B/v2.pdf"),
    ]


def test_windows_multi_entry_drops_html_keeps_pdf():
    bib = _wrap(
        r"Full Text:C:\Zotero\storage\A\paper.pdf:application/pdf;"
        r"Snapshot:C:\Zotero\storage\B\page.html:text/html"
    )
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path(r"C:\Zotero\storage\A\paper.pdf")]


# --- Extension casing -----------------------------------------------------


def test_uppercase_pdf_extension():
    bib = _wrap("Full Text:/home/u/Zotero/storage/A/SCAN.PDF:application/pdf")
    paths = bbt.parse_pdf_paths(bib)
    assert paths == [Path("/home/u/Zotero/storage/A/SCAN.PDF")]


# --- Negative cases -------------------------------------------------------


def test_missing_file_field_returns_empty():
    bib = "@article{key,\n  title = {x}\n}"
    assert bbt.parse_pdf_paths(bib) == []


def test_empty_file_field_returns_empty():
    bib = _wrap("")
    assert bbt.parse_pdf_paths(bib) == []


def test_only_non_pdf_entry_returns_empty():
    bib = _wrap("Snapshot:/home/u/Zotero/storage/B/index.html:text/html")
    assert bbt.parse_pdf_paths(bib) == []


def test_snapshot_is_used_when_there_is_no_pdf():
    bib = _wrap("Snapshot:/home/u/Zotero/storage/B/index.html:text/html")
    assert bbt.parse_attachment_paths(bib) == [
        Path("/home/u/Zotero/storage/B/index.html")
    ]


def test_pdf_is_preferred_over_snapshot():
    bib = _wrap(
        "Snapshot:/z/index.html:text/html;Full Text:/z/paper.pdf:application/pdf"
    )
    assert bbt.parse_attachment_paths(bib)[0] == Path("/z/paper.pdf")


# --- Regression: 0.2.1 reference bib in this repo -------------------------


@pytest.mark.parametrize(
    "fragment",
    [
        "Submitted Version:/home/brian/Zotero/storage/936D8S6A/Arksey and O'Malley - 2005 - Scoping studies towards a methodological framework.pdf:application/pdf",  # noqa: E501 — real Zotero path literal
        "Full Text PDF:/home/brian/Zotero/storage/S2P7TUKN/Keshav - 2007 - How to read a paper.pdf:application/pdf",  # noqa: E501 — real Zotero path literal
    ],
)
def test_real_linux_entries_from_repo_bib(fragment):
    paths = bbt.parse_pdf_paths(_wrap(fragment))
    assert len(paths) == 1
    assert paths[0].name.endswith(".pdf")
