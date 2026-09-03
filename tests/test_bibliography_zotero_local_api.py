"""Tests for using-bibliography/zotero_local_api.py.

Covers the pure filters over stock Zotero local API hits: exact DOI-field
matching, dropping attachment children, and citekey de-duplication across
library copies. The httpx shell that sweeps the libraries is verified live, not
exercised here.

Shape mirrors a live stock hit from
  /api/users/0/items?q=<doi>&qmode=fields&format=json
a different envelope from a BBT item.search hit: fields live under `data`, and
the citekey is `data.citationKey` (not `citation-key`).

Two properties of qmode=fields force client-side filtering, both verified
against Zotero 9.0.6 on 2026-08-03:
  1. The underlying condition is `contains`, so querying a DOI *prefix* also
     returns items whose DOI merely starts with it.
  2. Unlike quicksearch-titleCreatorYear, the mode does not set `noChildren`,
     so attachment children come back beside their parents.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "zotero_local_api.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "zotero_local_api_under_test", _MODULE
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["zotero_local_api_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


zla = _load()


def _stock_hit(key, *, doi=None, item_type="journalArticle", citekey=None, parent=None):
    data = {"itemType": item_type, "title": "t"}
    if doi is not None:
        data["DOI"] = doi
    if citekey is not None:
        data["citationKey"] = citekey
    if parent is not None:
        data["parentItem"] = parent
    return {"key": key, "data": data}


def test_select_doi_matches_returns_the_exact_parent():
    items = [
        _stock_hit("PL6KC9MS", doi="10.1007/s11222-016-9696-4", citekey="vehtari2017")
    ]
    out = zla.select_doi_matches(items, "10.1007/s11222-016-9696-4")
    assert [i["key"] for i in out] == ["PL6KC9MS"]


def test_select_doi_matches_excludes_attachment_children():
    # The live query for the Vehtari DOI returns the parent AND its PDF child;
    # the child carries no DOI and must never be offered as a resolved paper.
    items = [
        _stock_hit("PL6KC9MS", doi="10.1007/s11222-016-9696-4", citekey="vehtari2017"),
        _stock_hit("JQ33H3ZT", item_type="attachment", parent="PL6KC9MS"),
    ]
    out = zla.select_doi_matches(items, "10.1007/s11222-016-9696-4")
    assert [i["key"] for i in out] == ["PL6KC9MS"]


def test_select_doi_matches_rejects_substring_overmatch():
    # `contains` semantics: a prefix query reaches the longer DOI. Resolution by
    # DOI is exact, so the longer DOI is not an answer to the prefix.
    items = [
        _stock_hit("PL6KC9MS", doi="10.1007/s11222-016-9696-4", citekey="vehtari2017")
    ]
    assert zla.select_doi_matches(items, "10.1007/s11222") == []


def test_select_doi_matches_is_case_insensitive():
    items = [_stock_hit("RGLIK7CT", doi="10.32614/RJ-2016-039", citekey="lombardo2016")]
    out = zla.select_doi_matches(items, "10.32614/rj-2016-039")
    assert [i["key"] for i in out] == ["RGLIK7CT"]


def test_select_doi_matches_keeps_every_library_copy():
    # The same DOI legitimately exists in My Library and in groups as separate
    # items, only some with the PDF attached. The caller picks; we return all.
    doi = "10.1002/9780470567333.ch7"
    items = [
        _stock_hit("YLIDC5RW", doi=doi, citekey="collinsLanza2010Ch07RMLCAandLTA"),
        _stock_hit("7UZWGA92", doi=doi, citekey="collinsLanza2010Ch07RMLCAandLTA"),
    ]
    out = zla.select_doi_matches(items, doi)
    assert [i["key"] for i in out] == ["YLIDC5RW", "7UZWGA92"]


def test_select_doi_matches_tolerates_items_without_a_doi_field():
    items = [_stock_hit("NOD0I001", citekey="nodoi2020")]
    assert zla.select_doi_matches(items, "10.1/x") == []


def test_select_doi_matches_never_matches_on_an_empty_doi():
    # A blank query must not equal a blank DOI field and sweep up every
    # DOI-less item in the library.
    items = [
        _stock_hit("NOD0I001", citekey="nodoi2020"),
        _stock_hit("NOD0I002", doi="", citekey="blankdoi2020"),
    ]
    assert zla.select_doi_matches(items, "") == []
    assert zla.select_doi_matches(items, "   ") == []


def test_doi_citekeys_dedups_across_libraries_preserving_order():
    doi = "10.1002/9780470567333.ch7"
    items = [
        _stock_hit("YLIDC5RW", doi=doi, citekey="collinsLanza2010Ch07RMLCAandLTA"),
        _stock_hit("7UZWGA92", doi=doi, citekey="collinsLanza2010Ch07RMLCAandLTA"),
        _stock_hit("QQQQ1111", doi=doi, citekey="someOtherCopy2010"),
    ]
    assert zla.doi_citekeys(items, doi) == [
        "collinsLanza2010Ch07RMLCAandLTA",
        "someOtherCopy2010",
    ]


def test_doi_citekeys_skips_matches_without_a_citekey():
    # An exact DOI match with no BBT citekey cannot be resolved through BBT.
    # Observed rate: 0 of 42 DOI-bearing items sampled on 2026-08-03, so this
    # documents the boundary rather than a routine case.
    doi = "10.1/x"
    items = [
        _stock_hit("HASCK001", doi=doi, citekey="hasKey2020"),
        _stock_hit("NOCK0002", doi=doi),
    ]
    assert zla.doi_citekeys(items, doi) == ["hasKey2020"]


# search_doi_field over search_doi_items --------------------------------------
#
# search_doi_field keeps its list[str] contract for ingest.py while the richer
# search_doi_items carries the failed libraries a caller needs to tell "no item
# carries this DOI" apart from "part of the corpus was never searched". The
# httpx sweep itself stays live-verified per this module's docstring; what is
# pinned here is the delegation, which is what ingest.py depends on.


def _stub_items(monkeypatch, items, failed_libraries=()):
    monkeypatch.setattr(
        zla,
        "search_doi_items",
        lambda _doi: zla.LibrarySearch(
            items=tuple(items), failed_libraries=tuple(failed_libraries)
        ),
    )


def test_search_doi_field_returns_deduped_citekeys(monkeypatch):
    doi = "10.1002/9780470567333.ch7"
    _stub_items(
        monkeypatch,
        [
            _stock_hit("YLIDC5RW", doi=doi, citekey="collinsLanza2010Ch07RMLCAandLTA"),
            _stock_hit("7UZWGA92", doi=doi, citekey="collinsLanza2010Ch07RMLCAandLTA"),
            _stock_hit("QQQQ1111", doi=doi, citekey="someOtherCopy2010"),
        ],
    )
    assert zla.search_doi_field(doi) == [
        "collinsLanza2010Ch07RMLCAandLTA",
        "someOtherCopy2010",
    ]


def test_search_doi_field_warns_on_stderr_when_a_library_was_unsearchable(
    monkeypatch, capsys
):
    _stub_items(
        monkeypatch,
        [],
        failed_libraries=("http://localhost:23119/api/groups/14/items: timeout",),
    )

    assert zla.search_doi_field("10.1/x") == []
    assert "inconclusive" in capsys.readouterr().err


def test_search_doi_field_is_silent_when_every_library_was_searched(
    monkeypatch, capsys
):
    """Positive control: the warning marks a real failure, not every empty result."""
    _stub_items(monkeypatch, [])

    assert zla.search_doi_field("10.1/x") == []
    assert capsys.readouterr().err == ""


# search_items: the stock quicksearch sweep that replaced BBT item.search --------
#
# Zotero 10 removed the `blockStart` quicksearch marker that BBT's JSON-RPC
# item.search still emits (BBT issue #3587; still present in 9.0.63 and on master
# on 2026-09-02), so resolution runs on Zotero's own quicksearch instead. Both
# Zotero 9.0.6 and 10.0.1 expand `quicksearch-titleCreatorYear` over title,
# publicationTitle, shortTitle, court, year, citationKey and EVERY creator, and
# set noChildren (search.js in each). The sweep is the same per-library,
# paginated walk the DOI path uses. Pinned here: every library is visited,
# children never surface as papers, and a library that could not be searched is
# reported rather than silently treated as empty.


def test_select_parent_items_drops_attachment_and_note_children():
    items = [
        _stock_hit("PARENT01", citekey="vehtari2017"),
        _stock_hit("CHILD001", item_type="attachment", parent="PARENT01"),
        _stock_hit("CHILD002", item_type="note", parent="PARENT01"),
        _stock_hit("CHILD003", item_type="annotation", parent="CHILD001"),
    ]
    assert [i["key"] for i in zla.select_parent_items(items)] == ["PARENT01"]


def _stub_sweep(monkeypatch, pages):
    """Stub the library list and the per-library page fetch.

    `pages` maps a library items-URL to the envelopes it returns, or to the
    LibraryQueryError it raises.
    """
    monkeypatch.setattr(zla, "library_item_urls", lambda **_k: list(pages))

    def fake_fetch(url, query, *, qmode, timeout=30.0):
        assert query == "Giner-Sorolla"
        assert qmode == "titleCreatorYear"
        page = pages[url]
        if isinstance(page, Exception):
            raise page
        return page

    monkeypatch.setattr(zla, "fetch_search_page", fake_fetch)


def test_search_items_sweeps_every_library_and_keeps_only_parents(monkeypatch):
    mine = "http://localhost:23119/api/users/0/items"
    group = "http://localhost:23119/api/groups/6624981/items"
    _stub_sweep(
        monkeypatch,
        {
            mine: [_stock_hit("BRANDT14", citekey="brandtReplicationRecipeWhat2014")],
            group: [
                _stock_hit("GINER24", citekey="giner-sorollaPowerDetectWhat2024"),
                _stock_hit("GINERPDF", item_type="attachment", parent="GINER24"),
            ],
        },
    )

    found = zla.search_items("Giner-Sorolla")

    assert [i["key"] for i in found.items] == ["BRANDT14", "GINER24"]
    assert found.failed_libraries == ()


def test_search_items_reports_a_library_that_could_not_be_searched(monkeypatch):
    mine = "http://localhost:23119/api/users/0/items"
    group = "http://localhost:23119/api/groups/14/items"
    _stub_sweep(
        monkeypatch,
        {mine: [], group: zla.LibraryQueryError("timeout")},
    )

    found = zla.search_items("Giner-Sorolla")

    assert found.items == ()
    assert len(found.failed_libraries) == 1
    assert "groups/14" in found.failed_libraries[0]
    assert "timeout" in found.failed_libraries[0]
