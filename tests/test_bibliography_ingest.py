"""Tests for using-bibliography/ingest.py DOI resolution.

`find_by_doi` used to run DOI -> Crossref first-author surname -> BBT
`item.search` -> exact-DOI filter. That chain reported papers that ARE in
Zotero as absent whenever Crossref carried no author (Wiley chapter DOIs) or
the DOI belonged to a class Crossref answers thinly. It now searches the DOI
field directly through the stock local API.

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
_HIT = {
    "citation-key": "collinsLanza2010Ch07RMLCAandLTA",
    "DOI": _DOI,
    "library": "2026-ailoc-stage1",
    "title": "Repeated-measures latent class analysis",
}


def test_find_by_doi_resolves_through_the_doi_field(monkeypatch):
    seen = {}

    def fake_search(doi):
        seen["doi"] = doi
        return ["collinsLanza2010Ch07RMLCAandLTA"]

    monkeypatch.setattr(ingest, "search_doi_field", fake_search)
    monkeypatch.setattr(ingest, "rpc", lambda _m, _p: [_HIT])

    out = ingest.find_by_doi(_DOI)

    assert out is not None
    assert out["citation-key"] == "collinsLanza2010Ch07RMLCAandLTA"
    # The DOI reached the field search unmangled: no surname substitution, no
    # last-segment fallback token.
    assert seen["doi"] == _DOI


def test_find_by_doi_no_longer_calls_crossref():
    # Structural: the Crossref helper is gone from the module, so the
    # empty-author DOI classes cannot silently reappear as a failure path.
    assert not hasattr(ingest, "crossref_first_author_family")


def test_find_by_doi_returns_none_when_the_field_search_is_empty(monkeypatch):
    monkeypatch.setattr(ingest, "search_doi_field", lambda _doi: [])

    def explode(*_a, **_k):
        raise AssertionError("rpc must not run when no citekey matched the DOI")

    monkeypatch.setattr(ingest, "rpc", explode)
    assert ingest.find_by_doi("10.9999/absent") is None


def test_find_by_doi_rejects_a_hit_whose_doi_differs(monkeypatch):
    # BBT resolves a citekey across libraries and can return a near-miss; the
    # exact-DOI gate must still hold on the way out.
    monkeypatch.setattr(ingest, "search_doi_field", lambda _doi: ["someKey2010"])
    monkeypatch.setattr(
        ingest,
        "rpc",
        lambda _m, _p: [{"citation-key": "someKey2010", "DOI": "10.1/other"}],
    )
    assert ingest.find_by_doi(_DOI) is None


def test_find_by_doi_matches_doi_case_insensitively(monkeypatch):
    monkeypatch.setattr(ingest, "search_doi_field", lambda _doi: ["k2010"])
    monkeypatch.setattr(
        ingest,
        "rpc",
        lambda _m, _p: [{"citation-key": "k2010", "DOI": _DOI.upper()}],
    )
    assert ingest.find_by_doi(_DOI) is not None
