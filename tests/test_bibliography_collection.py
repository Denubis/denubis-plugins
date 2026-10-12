"""Tests for using-bibliography/collection.py (0.19).

`--list` is the read-only collection listing with trashed rows marked (design
2026-10-12, L1). Name resolution goes through copy_item's resolvers over the
zotero-api-plus `/libraries` response (ruling: "api-plus"); the listing itself
is the stock local API through zotero_local_api.get_collection_items. The HTTP
shell is stubbed; the live listing is UAT.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SKILL_DIR = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
)


def _load():
    if str(_SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(_SKILL_DIR))
    spec = importlib.util.spec_from_file_location(
        "collection_under_test", _SKILL_DIR / "collection.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["collection_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


collection = _load()

LIBRARY = {
    "type": "user",
    "libraryID": 1,
    "name": "My Library",
    "collections": [
        {"name": "Sage SRM Guide", "key": "SAGE0001", "parentKey": None},
        {"name": "Readings", "key": "READ0001", "parentKey": "SAGE0001"},
        {"name": "Readings", "key": "READ0002", "parentKey": "OTHER001"},
    ],
}


def _listing():
    return [
        {
            "key": "PARENT01",
            "data": {
                "key": "PARENT01",
                "itemType": "book",
                "title": "Technology and the character of contemporary life",
                "citationKey": "borgmann1984",
            },
        },
        {
            "key": "ATTACH01",
            "data": {
                "key": "ATTACH01",
                "itemType": "attachment",
                "parentItem": "PARENT01",
                "filename": "Borgmann - 1984.pdf",
            },
        },
        {
            "key": "PARENT02",
            "data": {
                "key": "PARENT02",
                "itemType": "journalArticle",
                "title": "Trashed paper",
                "citationKey": "trashed2020",
                "deleted": True,
            },
        },
    ]


def _stub_live(monkeypatch, listing):
    monkeypatch.setattr(collection, "probe_api_plus", lambda: None)
    monkeypatch.setattr(collection, "get_libraries", lambda: [LIBRARY])
    seen = {}

    def fake_listing(lib, key, *, include_trashed=True):
        seen["args"] = (lib, key, include_trashed)
        return listing

    monkeypatch.setattr(collection, "get_collection_items", fake_listing)
    return seen


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["collection.py", *argv])
    return collection.main()


# --- resolution --------------------------------------------------------------


def test_resolve_target_by_name():
    assert collection.resolve_collection(LIBRARY, "Sage SRM Guide") == "SAGE0001"


def test_resolve_target_accepts_a_bare_key_directly():
    assert collection.resolve_collection(LIBRARY, "SAGE0001") == "SAGE0001"
    # A key is accepted as given even if no name matches it.
    assert collection.resolve_collection(LIBRARY, "ZZZZ9999") == "ZZZZ9999"


def test_ambiguous_name_errors_with_candidate_keys_and_parents():
    with pytest.raises(collection.ResolutionError) as error:
        collection.resolve_collection(LIBRARY, "Readings")
    message = str(error.value)
    assert "READ0001" in message and "READ0002" in message
    assert "SAGE0001" in message and "OTHER001" in message


def test_unknown_name_errors():
    with pytest.raises(collection.ResolutionError):
        collection.resolve_collection(LIBRARY, "No Such Collection")


# --- row rendering -----------------------------------------------------------


def test_render_rows_marks_trash_and_counts_attachments():
    rows = collection.summarise_collection(_listing())
    text = collection.render_rows(rows)
    lines = text.splitlines()
    assert lines[0].split() == [
        "PARENT01",
        "borgmann1984",
        "Technology",
        "and",
        "the",
        "character",
        "of",
        "contemporary",
        "life",
        "attachments:",
        "1",
        "(Borgmann",
        "-",
        "1984.pdf)",
    ]
    assert (
        "PARENT02  trashed2020  Trashed paper  [in trash]  attachments: 0" in lines[1]
    )
    assert lines[-1] == "2 items (1 in trash)"


# --- main --------------------------------------------------------------------


def test_list_resolves_the_name_and_lists_with_trash(monkeypatch, capsys):
    seen = _stub_live(monkeypatch, _listing())
    assert _run(monkeypatch, ["--list", "Sage SRM Guide"]) == 0
    out = capsys.readouterr().out
    assert seen["args"] == (LIBRARY, "SAGE0001", True)
    assert "Sage SRM Guide (SAGE0001) in My Library" in out
    assert "[in trash]" in out
    assert "2 items (1 in trash)" in out


def test_list_ambiguous_name_exits_2_without_listing(monkeypatch, capsys):
    seen = _stub_live(monkeypatch, _listing())
    assert _run(monkeypatch, ["--list", "Readings"]) == 2
    assert "args" not in seen
    assert "ambiguous" in capsys.readouterr().err


def test_list_requires_api_plus_for_name_resolution(monkeypatch, capsys):
    def refuse():
        raise SystemExit("zotero-api-plus not reachable")

    monkeypatch.setattr(collection, "probe_api_plus", refuse)
    monkeypatch.setattr(
        collection, "get_libraries", lambda: pytest.fail("must not be reached")
    )
    with pytest.raises(SystemExit):
        _run(monkeypatch, ["--list", "Sage SRM Guide"])


def test_parser_requires_a_verb(monkeypatch):
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, [])
    assert error.value.code == 2
