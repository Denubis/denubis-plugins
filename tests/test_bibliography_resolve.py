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
    assert (
        resolve.select_citekey_matches(
            HITS, "lakatosFalsificationMethodologyScientific1970a"
        )
        == []
    )


# --- matches_query / classify_state / collection_names ----------------------


def _vehtari():
    return resolve.Paper(
        citekey="vehtariPracticalBayesianModel2017",
        doi="10.1007/s11222-016-9696-4",
        title=(
            "Practical Bayesian model evaluation using "
            "leave-one-out cross-validation and WAIC"
        ),
        authors=("Vehtari", "Gelman"),
        year=2017,
        library="My Library",
        library_id=305867,
        collection_keys=("PG5D93ZH",),
    )


def test_matches_query_by_citekey_exact():
    assert resolve.matches_query(
        _vehtari(), citekey="vehtariPracticalBayesianModel2017"
    )
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
    assert (
        resolve.classify_state(
            found=False, has_pdf=False, pdf_exists=False, rendered=False
        )
        == "not-in-zotero"
    )
    assert (
        resolve.classify_state(
            found=True, has_pdf=False, pdf_exists=False, rendered=False
        )
        == "no-pdf"
    )
    assert (
        resolve.classify_state(
            found=True, has_pdf=True, pdf_exists=False, rendered=False
        )
        == "no-pdf"
    )
    assert (
        resolve.classify_state(
            found=True, has_pdf=True, pdf_exists=True, rendered=False
        )
        == "ready-to-render"
    )
    assert (
        resolve.classify_state(found=True, has_pdf=True, pdf_exists=True, rendered=True)
        == "rendered"
    )


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
    hit = {
        **BBT_HIT,
        "author": [{"given": "Anonymous"}, {"family": "Gelman", "given": "Andrew"}],
    }
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


# --- search_tokens (union of every supplied key; Bug B) ----------------------
#
# BBT item.search indexes only the FIRST author surname and is AND-fuzzy, so the
# old "pick ONE key by priority" elif chain silently failed whenever that key was
# a co-author or a drifted title. search_tokens returns every supplied key so the
# shell can union the hits and let matches_query filter; recall from the union,
# precision from the filter.


def test_search_tokens_unions_author_and_title():
    # The exact query that returned "No matches" while the paper was present:
    # author is the SECOND author (Wade, Ghahramani), so an author-only search
    # finds nothing — but the title token does, and the union carries it.
    assert resolve.search_tokens(
        author="Ghahramani", title="Bayesian Cluster Analysis"
    ) == ["Ghahramani", "Bayesian Cluster Analysis"]


def test_search_tokens_order_is_citekey_author_freeterm_title():
    assert resolve.search_tokens(
        citekey="k2020", author="Smith", freeterm="ft", title="A Title"
    ) == ["k2020", "Smith", "ft", "A Title"]


def test_search_tokens_dedupes_repeated_values():
    assert resolve.search_tokens(author="dup", freeterm="dup") == ["dup"]


def test_search_tokens_ignores_none_and_blank():
    assert resolve.search_tokens(author=None, title="   ", freeterm="") == []


def test_search_tokens_empty_when_nothing_supplied():
    assert resolve.search_tokens() == []


# --- matches_query author: hyphen-component matching (Bug A) ------------------
#
# BBT item.search substring-matches a partial surname ("Malsiner" surfaces the
# "Malsiner-Walli" item), but the old exact-equality filter then DROPPED it. A
# hyphen-split component matches; a space-split component does NOT (else "van"
# would match every "van X"); no arbitrary substring (so "Veh" never matches
# "Vehtari").


def _malsiner():
    return resolve.Paper(
        citekey="malsiner-walliModelbasedClusteringBased2016",
        doi="10.1007/s11222-014-9500-2",
        title="Model-based clustering based on sparse finite Gaussian mixtures",
        authors=("Malsiner-Walli", "Frühwirth-Schnatter", "Grün"),
        year=2016,
        library="2026-mq-amanda-annotation-survey",
        library_id=26,
        collection_keys=(),
    )


def _van_onna():
    return resolve.Paper(
        citekey="vanonnaBayesianEstimation2002",
        doi="",
        title="Bayesian estimation of conditional independence",
        authors=("van Onna",),
        year=2002,
        library="My Library",
        library_id=1,
        collection_keys=(),
    )


def test_matches_query_author_matches_hyphen_component():
    assert resolve.matches_query(_malsiner(), author="Malsiner")
    assert resolve.matches_query(_malsiner(), author="Walli")
    assert resolve.matches_query(_malsiner(), author="Frühwirth")
    assert resolve.matches_query(_malsiner(), author="malsiner-walli")  # exact still


def test_matches_query_author_does_not_space_split():
    assert resolve.matches_query(_van_onna(), author="van Onna")
    assert not resolve.matches_query(_van_onna(), author="van")


def test_matches_query_author_no_arbitrary_substring():
    assert not resolve.matches_query(_vehtari(), author="Veh")
    assert not resolve.matches_query(_vehtari(), author="elman")


# --- diacritic folding (Bug C) -----------------------------------------------
#
# BBT item.search matches against an ASCII-folded index, so a query carrying
# diacritics ("Frühwirth", "Grün") returns zero while the paper — filed with the
# ASCII citekey "fruhwirth-schnatter…" — is present. The fix folds on the search
# side (search the folded variant too) and on the filter side (matches_query
# compares folded on both sides), so the correctly-spelled name and its ASCII
# form both resolve.


def test_ascii_fold_strips_diacritics_preserving_case():
    assert resolve._ascii_fold("Frühwirth") == "Fruhwirth"
    assert resolve._ascii_fold("Grün") == "Grun"
    assert resolve._ascii_fold("Méthodes") == "Methodes"
    assert resolve._ascii_fold("Ghahramani") == "Ghahramani"  # ASCII: unchanged


def test_search_tokens_adds_ascii_folded_variant():
    # The exact From-here-to-infinity failure: "Frühwirth" must also be searched
    # as "Fruhwirth" or BBT's folded index never surfaces the paper.
    assert resolve.search_tokens(author="Frühwirth") == ["Frühwirth", "Fruhwirth"]


def test_search_tokens_no_fold_variant_for_pure_ascii():
    assert resolve.search_tokens(author="Ghahramani") == ["Ghahramani"]


def test_matches_query_author_diacritic_insensitive():
    p = _malsiner()  # authors: Malsiner-Walli, Frühwirth-Schnatter, Grün
    assert resolve.matches_query(p, author="Frühwirth")  # umlaut as filed
    assert resolve.matches_query(p, author="Fruhwirth")  # ASCII as typed
    assert resolve.matches_query(p, author="Grün")
    assert resolve.matches_query(p, author="Grun")


def test_matches_query_title_diacritic_insensitive():
    p = resolve.Paper(
        citekey="mueller2020",
        doi="",
        title="Méthodes de clustering bayésien",
        authors=("Müller",),
        year=2020,
        library="My Library",
        library_id=1,
        collection_keys=(),
    )
    assert resolve.matches_query(p, title="methodes")  # ASCII query, accented title
    assert resolve.matches_query(p, title="Méthodes")
    assert resolve.matches_query(p, author="Muller")


# --- make-citeable consumer: pure core -------------------------------------
# `resolve.py --bib <path> --citekey <key>` triggers the run-autoexport endpoint
# then verifies the citekey is present in a WELL-FORMED bib. The verification must
# not be fooled by a partial/truncated write that contains the citekey string yet
# is broken BibLaTeX — hence a real parser (bibtexparser v2 failed_blocks), not a
# grep. These cover the three pure pieces: the parser check, the HTTP-response
# classifier, and the --bib/--citekey argument validation.

_GOOD_BIB = (
    "@article{smithFoo2020,\n"
    "  author = {Smith, Alice},\n"
    "  title = {Foo and Bar},\n"
    "  year = {2020},\n"
    "}\n"
)


def test_check_bib_well_formed_with_citekey_is_citeable():
    c = resolve.check_bib(_GOOD_BIB, "smithFoo2020")
    assert c.well_formed is True
    assert c.citekey_present is True
    assert c.citeable is True
    assert c.failed_count == 0
    assert c.entry_count == 1


def test_check_bib_well_formed_without_citekey_is_not_citeable():
    c = resolve.check_bib(_GOOD_BIB, "absentKey2099")
    assert c.well_formed is True
    assert c.citekey_present is False
    assert c.citeable is False


def test_check_bib_truncated_entry_is_not_well_formed():
    # The citekey's own entry is cut off mid-write: contains the citekey string
    # but is broken BibLaTeX. A grep would pass; the parser must not.
    truncated = "@article{smithFoo2020,\n  author = {Smith, Alice},\n  title = {Foo"
    c = resolve.check_bib(truncated, "smithFoo2020")
    assert c.well_formed is False
    assert c.failed_count >= 1
    assert c.citeable is False


def test_check_bib_citekey_only_as_substring_is_not_present():
    # The citekey appears inside a field value, not as an entry key.
    other = (
        "@article{otherKey2019,\n"
        "  title = {A note mentioning smithFoo2020 in passing},\n"
        "  year = {2019},\n"
        "}\n"
    )
    c = resolve.check_bib(other, "smithFoo2020")
    assert c.well_formed is True
    assert c.citekey_present is False


def test_check_bib_empty_is_well_formed_but_absent():
    c = resolve.check_bib("", "smithFoo2020")
    assert c.well_formed is True
    assert c.entry_count == 0
    assert c.citeable is False


def test_classify_autoexport_triggered():
    body = '{"status": "triggered", "path": "/p.bib", "type": "collection"}'
    o = resolve.classify_autoexport_response(200, body)
    assert o.kind == "triggered"


def test_classify_autoexport_no_autoexport_lists_registered_paths():
    body = (
        '{"status": "no-autoexport", "path": "/p.bib", '
        '"registeredPaths": ["/x.bib", "/y.bib"]}'
    )
    o = resolve.classify_autoexport_response(404, body)
    assert o.kind == "no-autoexport"
    assert o.registered_paths == ("/x.bib", "/y.bib")


def test_classify_autoexport_endpoint_absent_on_generic_404():
    # The endpoint isn't registered (old/absent plugin): Zotero's generic 404 with
    # a plain-text body, distinct from the JSON no-autoexport 404.
    o = resolve.classify_autoexport_response(404, "No endpoint found")
    assert o.kind == "endpoint-absent"


def test_classify_autoexport_bbt_unavailable_and_starting():
    assert (
        resolve.classify_autoexport_response(503, '{"status": "bbt-unavailable"}').kind
        == "bbt-unavailable"
    )
    assert (
        resolve.classify_autoexport_response(503, '{"status": "bbt-starting"}').kind
        == "bbt-starting"
    )


def test_classify_autoexport_other_status_is_error():
    assert resolve.classify_autoexport_response(400, "Error: no path").kind == "error"
    assert (
        resolve.classify_autoexport_response(500, "Internal Server Error: x").kind
        == "error"
    )


def test_bib_arg_error_accepts_absolute_path_and_citekey():
    assert resolve.bib_arg_error("/abs/project/references.bib", "smithFoo2020") is None


def test_bib_arg_error_rejects_relative_path():
    err = resolve.bib_arg_error("project/references.bib", "smithFoo2020")
    assert err is not None
    assert "absolute" in err.lower()


def test_bib_arg_error_requires_citekey():
    err = resolve.bib_arg_error("/abs/references.bib", None)
    assert err is not None
    assert "citekey" in err.lower()
    err2 = resolve.bib_arg_error("/abs/references.bib", "   ")
    assert err2 is not None


def test_explain_autoexport_failure_endpoint_absent_tells_user_to_install():
    # Decision 2: when the endpoint is absent, direct the user to install/upgrade
    # the plugin — never a wrong-scope library pull.
    msg = resolve.explain_autoexport_failure(
        resolve.AutoexportOutcome(kind="endpoint-absent"), Path("/p/refs.bib")
    )
    low = msg.lower()
    assert "0.4.0" in msg
    assert "install" in low or "upgrade" in low
    # If the message mentions the library pull at all, it must be to warn against
    # it (the wrong-scope clobber), never to recommend it.
    assert "would clobber" in low


def test_explain_autoexport_failure_no_autoexport_lists_registered_paths():
    out = resolve.AutoexportOutcome(
        kind="no-autoexport", registered_paths=("/a/x.bib", "/b/y.bib")
    )
    msg = resolve.explain_autoexport_failure(out, Path("/p/refs.bib"))
    assert "/a/x.bib" in msg
    assert "/b/y.bib" in msg
    assert "keep updated" in msg.lower()


def test_explain_autoexport_failure_bbt_states():
    assert (
        "not installed"
        in resolve.explain_autoexport_failure(
            resolve.AutoexportOutcome(kind="bbt-unavailable"), Path("/p.bib")
        ).lower()
    )
    assert (
        "starting"
        in resolve.explain_autoexport_failure(
            resolve.AutoexportOutcome(kind="bbt-starting"), Path("/p.bib")
        ).lower()
    )


# _trigger_autoexport is shell, but its retry-while-starting control flow is worth
# pinning. Stub the HTTP boundary (post_run_autoexport) and use retry_delay=0 so
# the tests neither touch the network nor sleep.
def test_trigger_autoexport_retries_while_starting_then_succeeds(monkeypatch):
    responses = iter(
        [
            (503, '{"status": "bbt-starting"}'),
            (503, '{"status": "bbt-starting"}'),
            (200, '{"status": "triggered", "path": "/p.bib"}'),
        ]
    )
    monkeypatch.setattr(
        resolve, "post_run_autoexport", lambda _p, **_k: next(responses)
    )
    out = resolve._trigger_autoexport(
        Path("/p.bib"), starting_retries=3, retry_delay=0
    )
    assert out is not None
    assert out.kind == "triggered"


def test_trigger_autoexport_gives_up_after_starting_retries(monkeypatch):
    monkeypatch.setattr(
        resolve,
        "post_run_autoexport",
        lambda _p, **_k: (503, '{"status": "bbt-starting"}'),
    )
    out = resolve._trigger_autoexport(
        Path("/p.bib"), starting_retries=2, retry_delay=0
    )
    assert out is not None
    assert out.kind == "bbt-starting"


def test_trigger_autoexport_unreachable_returns_none(monkeypatch):
    # post_run_autoexport returns None on an httpx transport error (Zotero down).
    monkeypatch.setattr(resolve, "post_run_autoexport", lambda _p, **_k: None)
    assert resolve._trigger_autoexport(Path("/p.bib"), retry_delay=0) is None
