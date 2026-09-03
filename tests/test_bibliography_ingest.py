"""Tests for using-bibliography/ingest.py DOI resolution.

`find_by_doi` used to run DOI -> Crossref first-author surname -> BBT
`item.search` -> exact-DOI filter. That chain reported papers that ARE in
Zotero as absent whenever Crossref carried no author (Wiley chapter DOIs) or
the DOI belonged to a class Crossref answers thinly. It then searched the DOI
field through the stock local API but re-hydrated each citekey through BBT
`item.search`, which errors on every query under Zotero 10 (BBT issue #3587).
It now uses the stock envelope directly; BBT is reached only for the export
that carries the attachment path.

The network boundary is mocked; the live path is verified by running ingest.py
against a real DOI.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_INGEST = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "ingest.py"
)


def _load_ingest():
    spec = importlib.util.spec_from_file_location("ingest_under_test", _INGEST)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


ingest = _load_ingest()

_DOI = "10.1002/9780470567333.ch7"
_CITEKEY = "collinsLanza2010Ch07RMLCAandLTA"


def _envelope(key, citekey, library, *, doi=_DOI):
    """A stock local API envelope for a group copy of the chapter."""
    return {
        "key": key,
        "library": {"type": "group", "id": 6624981, "name": library},
        "data": {
            "key": key,
            "itemType": "bookSection",
            "citationKey": citekey,
            "DOI": doi,
            "title": "Repeated-measures latent class analysis",
        },
    }


def _stub_doi_items(monkeypatch, items, failed_libraries=()):
    seen = {}

    def fake(doi):
        seen["doi"] = doi
        return ingest.LibrarySearch(
            items=tuple(items), failed_libraries=tuple(failed_libraries)
        )

    monkeypatch.setattr(ingest, "search_doi_items", fake)
    return seen


def _forbid_bbt(monkeypatch):
    def explode(method, *_a, **_k):
        raise AssertionError(f"BBT JSON-RPC {method!r} must not run during search")

    monkeypatch.setattr(ingest, "rpc", explode)


def test_find_by_doi_resolves_through_the_doi_field(monkeypatch):
    seen = _stub_doi_items(
        monkeypatch, [_envelope("YLIDC5RW", _CITEKEY, "2026-ailoc-stage1")]
    )
    _forbid_bbt(monkeypatch)

    out = ingest.find_by_doi(_DOI)

    assert out is not None
    assert ingest.item_citekey(out) == _CITEKEY
    assert ingest.item_library(out) == "2026-ailoc-stage1"
    # The DOI reached the field search unmangled: no surname substitution, no
    # last-segment fallback token.
    assert seen["doi"] == _DOI


def test_find_by_doi_no_longer_calls_crossref():
    # Structural: the Crossref helper is gone from the module, so the
    # empty-author DOI classes cannot silently reappear as a failure path.
    assert not hasattr(ingest, "crossref_first_author_family")


def test_find_by_doi_returns_none_when_the_field_search_is_empty(monkeypatch):
    _stub_doi_items(monkeypatch, [])
    _forbid_bbt(monkeypatch)
    assert ingest.find_by_doi("10.9999/absent") is None


def test_find_by_doi_rejects_a_hit_whose_doi_differs(monkeypatch):
    # qmode=fields is `contains`; the exact-DOI gate must still hold on the
    # way out.
    _stub_doi_items(monkeypatch, [_envelope("X", "someKey2010", "L", doi="10.1/o")])
    _forbid_bbt(monkeypatch)
    assert ingest.find_by_doi(_DOI) is None


def test_find_by_doi_matches_doi_case_insensitively(monkeypatch):
    _stub_doi_items(monkeypatch, [_envelope("X", "k2010", "L", doi=_DOI.upper())])
    _forbid_bbt(monkeypatch)
    assert ingest.find_by_doi(_DOI) is not None


def test_find_by_doi_warns_when_a_library_was_unsearchable(monkeypatch, capsys):
    # An empty result over a partly unsearched corpus is inconclusive, and the
    # warning is the only signal the batch caller gets before "NOT FOUND".
    _stub_doi_items(
        monkeypatch,
        [],
        failed_libraries=("http://localhost:23119/api/groups/14/items: timeout",),
    )
    _forbid_bbt(monkeypatch)

    assert ingest.find_by_doi(_DOI) is None
    assert "inconclusive" in capsys.readouterr().err


def test_resolve_pdf_exports_the_envelope_copy_by_library_name(monkeypatch):
    # The export still goes through BBT (it carries the attachment path), keyed
    # by the citekey and the BBT library id that user.groups maps the
    # envelope's library NAME to.
    item = _envelope("YLIDC5RW", _CITEKEY, "2026-ailoc-stage1")
    calls = []

    def fake_rpc(method, params, *_a, **_k):
        calls.append((method, params))
        return [
            "@incollection{k,\n  file = {PDF:/papers/collins.pdf:application/pdf}\n}"
        ]

    monkeypatch.setattr(ingest, "rpc", fake_rpc)

    pdf = ingest.resolve_pdf(item, {"2026-ailoc-stage1": 7})

    assert pdf == Path("/papers/collins.pdf")
    assert calls == [("item.export", [[_CITEKEY], "Better BibLaTeX", 7])]
