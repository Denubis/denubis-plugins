"""Tests for plugins/denubis-bibliography/skills/using-bibliography/resolve.py.

Covers the pure functional core of citekey-first resolution: selecting the exact
citekey matches out of BBT `item.search` hits (which are fuzzy/AND-token and
return near-misses alongside the real item). The HTTP shell that talks to BBT is
verified live, not exercised here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_RESOLVE = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-bibliography"
    / "skills"
    / "using-bibliography"
    / "resolve.py"
)


def _load_resolve():
    spec = importlib.util.spec_from_file_location("resolve_under_test", _RESOLVE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["resolve_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


resolve = _load_resolve()


# Shape mirrors a live BBT item.search hit: each carries `citation-key`,
# `library` (the human library NAME, not id), and `DOI`. A citekey query is
# AND-token fuzzy, so it returns near-misses next to the exact item.
HITS = [
    {
        "citation-key": "vehtariPracticalBayesianModel2017",
        "library": "My Library",
        "DOI": "10.1007/s11222-016-9696-4",
        "title": "Practical Bayesian model evaluation using LOO-CV and WAIC",
    },
    {
        "citation-key": "vehtariRankNormalizationFolding2021",
        "library": "My Library",
        "DOI": "10.1214/20-BA1221",
        "title": "Rank-normalization, folding, and localization",
    },
]

# Same citekey present in two libraries (the real multi-library duplicate case:
# a paper lives in My Library AND a group, only some copies with a PDF).
HITS_MULTI = [
    {"citation-key": "sharedKey2020", "library": "My Library", "DOI": "10.1/x"},
    {
        "citation-key": "sharedKey2020",
        "library": "2026-example-library-1",
        "DOI": "10.1/x",
    },
    {"citation-key": "otherKey2020", "library": "My Library", "DOI": "10.2/y"},
]


def test_selects_only_exact_citekey_match():
    out = resolve.select_citekey_matches(HITS, "vehtariPracticalBayesianModel2017")
    assert len(out) == 1
    assert out[0]["library"] == "My Library"
    assert out[0]["DOI"] == "10.1007/s11222-016-9696-4"


def test_returns_every_library_copy_of_a_citekey():
    out = resolve.select_citekey_matches(HITS_MULTI, "sharedKey2020")
    assert len(out) == 2
    assert {h["library"] for h in out} == {
        "My Library",
        "2026-example-library-1",
    }


def test_no_match_returns_empty():
    assert resolve.select_citekey_matches(HITS, "lakatosFalsificationMethodologyScientific1970a") == []


# --- matches_query / classify_state / collection_names ----------------------


def _vehtari():
    return resolve.Paper(
        citekey="vehtariPracticalBayesianModel2017",
        doi="10.1007/s11222-016-9696-4",
        title="Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC",
        authors=("Vehtari", "Gelman"),
        year=2017,
        library="My Library",
        library_id=305867,
        collection_keys=("PG5D93ZH",),
    )


def test_matches_query_by_citekey_exact():
    assert resolve.matches_query(_vehtari(), citekey="vehtariPracticalBayesianModel2017")
    assert not resolve.matches_query(_vehtari(), citekey="somethingElse2020")


def test_matches_query_by_author_surname_case_insensitive():
    assert resolve.matches_query(_vehtari(), author="vehtari")
    assert resolve.matches_query(_vehtari(), author="Gelman")
    assert not resolve.matches_query(_vehtari(), author="Smith")


def test_matches_query_by_year_accepts_int_or_str():
    assert resolve.matches_query(_vehtari(), year=2017)
    assert resolve.matches_query(_vehtari(), year="2017")
    assert not resolve.matches_query(_vehtari(), year=2019)


def test_matches_query_by_title_substring():
    assert resolve.matches_query(_vehtari(), title="leave-one-out")
    assert not resolve.matches_query(_vehtari(), title="quantum chromodynamics")


def test_matches_query_by_doi_case_insensitive():
    assert resolve.matches_query(_vehtari(), doi="10.1007/S11222-016-9696-4")
    assert not resolve.matches_query(_vehtari(), doi="10.9999/x")


def test_matches_query_ands_all_constraints():
    # right author, wrong year -> no match (AND, not OR)
    assert not resolve.matches_query(_vehtari(), author="Vehtari", year=2019)
    assert resolve.matches_query(_vehtari(), author="Vehtari", year=2017)


def test_classify_state_progression():
    assert resolve.classify_state(found=False, has_pdf=False, pdf_exists=False, rendered=False) == "not-in-zotero"
    assert resolve.classify_state(found=True, has_pdf=False, pdf_exists=False, rendered=False) == "no-pdf"
    assert resolve.classify_state(found=True, has_pdf=True, pdf_exists=False, rendered=False) == "no-pdf"
    assert resolve.classify_state(found=True, has_pdf=True, pdf_exists=True, rendered=False) == "ready-to-render"
    assert resolve.classify_state(found=True, has_pdf=True, pdf_exists=True, rendered=True) == "rendered"


def test_collection_names_maps_known_and_passes_through_unknown():
    names = resolve.collection_names(
        ["PG5D93ZH", "UNKNOWN1"], {"PG5D93ZH": "Bayesian / Methods"}
    )
    assert names == ["Bayesian / Methods", "UNKNOWN1"]


# --- _render_cmd (render.py has no PEP 723 header → deps go on the CLI) -------


def test_render_cmd_passes_heavy_deps_to_render_py():
    cmd = resolve._render_cmd(Path("/tmp/x.pdf"), Path("/tmp/out"))
    # render.py has NO PEP 723 header, so its deps MUST be on the command line;
    # plain `uv run render.py` would die on ModuleNotFoundError.
    assert "--with" in cmd
    for dep in ("pymupdf4llm", "docling", "easyocr"):
        assert dep in cmd
    assert "python" in cmd
    assert str(resolve.RENDER_SCRIPT) in cmd
    assert "/tmp/x.pdf" in cmd and "/tmp/out" in cmd
    assert "--allow-mocr" not in cmd


def test_render_cmd_appends_allow_mocr():
    cmd = resolve._render_cmd(Path("/tmp/x.pdf"), Path("/tmp/out"), allow_mocr=True)
    assert cmd[-1] == "--allow-mocr"


# --- _year_from_issued / normalize_bbt_hit (new pure functions) --------------

# A well-formed BBT item.search hit (the shape the live API produces).
BBT_HIT = {
    "citation-key": "vehtariPracticalBayesianModel2017",
    "citekey": "vehtariPracticalBayesianModel2017",
    "DOI": "10.1007/s11222-016-9696-4",
    "title": "Practical Bayesian model evaluation using LOO-CV and WAIC",
    "author": [
        {"family": "Vehtari", "given": "Aki"},
        {"family": "Gelman", "given": "Andrew"},
    ],
    "issued": {"date-parts": [[2017, 9]]},
    "library": "My Library",
    "type": "article-journal",
}


# _year_from_issued -----------------------------------------------------------


def test_year_from_issued_normal():
    assert resolve._year_from_issued({"date-parts": [[2017, 9]]}) == 2017


def test_year_from_issued_year_only():
    assert resolve._year_from_issued({"date-parts": [[2021]]}) == 2021


def test_year_from_issued_missing_issued():
    assert resolve._year_from_issued(None) is None
    assert resolve._year_from_issued({}) is None


def test_year_from_issued_empty_date_parts():
    assert resolve._year_from_issued({"date-parts": []}) is None
    assert resolve._year_from_issued({"date-parts": [[]]}) is None


def test_year_from_issued_non_int_year():
    # A non-integer first element should not crash — return None.
    assert resolve._year_from_issued({"date-parts": [["unknown"]]}) is None


# normalize_bbt_hit -----------------------------------------------------------


def test_normalize_bbt_hit_extracts_all_fields():
    p = resolve.normalize_bbt_hit(BBT_HIT)
    assert p.citekey == "vehtariPracticalBayesianModel2017"
    assert p.doi == "10.1007/s11222-016-9696-4"
    assert p.title == "Practical Bayesian model evaluation using LOO-CV and WAIC"
    assert p.authors == ("Vehtari", "Gelman")
    assert p.year == 2017
    assert p.library == "My Library"
    assert p.library_id is None
    assert p.collection_keys == ()


def test_normalize_bbt_hit_missing_author_list():
    hit = {**BBT_HIT, "author": []}
    p = resolve.normalize_bbt_hit(hit)
    assert p.authors == ()


def test_normalize_bbt_hit_author_without_family_skipped():
    hit = {**BBT_HIT, "author": [{"given": "Anonymous"}, {"family": "Gelman", "given": "Andrew"}]}
    p = resolve.normalize_bbt_hit(hit)
    assert p.authors == ("Gelman",)


def test_normalize_bbt_hit_missing_doi_defaults_empty():
    hit = {k: v for k, v in BBT_HIT.items() if k != "DOI"}
    p = resolve.normalize_bbt_hit(hit)
    assert p.doi == ""


def test_normalize_bbt_hit_missing_title_defaults_empty():
    hit = {k: v for k, v in BBT_HIT.items() if k != "title"}
    p = resolve.normalize_bbt_hit(hit)
    assert p.title == ""


def test_normalize_bbt_hit_missing_library_defaults_empty():
    hit = {k: v for k, v in BBT_HIT.items() if k != "library"}
    p = resolve.normalize_bbt_hit(hit)
    assert p.library == ""


def test_normalize_bbt_hit_missing_issued_year_is_none():
    hit = {k: v for k, v in BBT_HIT.items() if k != "issued"}
    p = resolve.normalize_bbt_hit(hit)
    assert p.year is None


def test_normalize_bbt_hit_collection_keys_always_empty_tuple():
    # BBT item.search hits carry no collection info — always empty.
    p = resolve.normalize_bbt_hit(BBT_HIT)
    assert p.collection_keys == ()
