"""Tests for plugins/denubis-academic/skills/using-bibliography/resolve.py.

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
    / "denubis-academic"
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


# --- fuzzy citekey candidates ------------------------------------------------
#
# BBT item.search already prefix-matches the citation-key, so a constructed key
# missing its disambiguation suffix (chengGenerativeAIRequirements2026 for the
# stored chengGenerativeAIRequirements2026a) surfaces the real item — but the
# exact-equality filter then discards it, reporting "no matches". These pure
# functions classify a hit's citekey against the query so the shell can RETURN
# the near matches (never render them — the caller re-runs with the real key).

_CHENG_REAL = "chengGenerativeAIRequirements2026a"
_CHENG_CONSTRUCTED = "chengGenerativeAIRequirements2026"  # the key the session built


# citekey_base ----------------------------------------------------------------


def test_citekey_base_strips_disambiguator_after_year():
    assert resolve.citekey_base(_CHENG_REAL) == _CHENG_CONSTRUCTED
    assert resolve.citekey_base("dignathHowCanPrimary2008a") == "dignathHowCanPrimary2008"


def test_citekey_base_leaves_bare_year_unchanged():
    assert resolve.citekey_base(_CHENG_CONSTRUCTED) == _CHENG_CONSTRUCTED
    assert resolve.citekey_base("smithFoo2020") == "smithFoo2020"


def test_citekey_base_no_year_returned_unchanged():
    # No 4-digit year to anchor the suffix strip — leave the key alone.
    assert resolve.citekey_base("noYearHere") == "noYearHere"


# citekey_author --------------------------------------------------------------


def test_citekey_author_extracts_leading_surname():
    assert resolve.citekey_author(_CHENG_REAL) == "cheng"
    assert resolve.citekey_author("vehtariPracticalBayesianModel2017") == "vehtari"


def test_citekey_author_keeps_hyphenated_surname():
    assert (
        resolve.citekey_author("malsiner-walliModelbasedClustering2016")
        == "malsiner-walli"
    )


# classify_citekey ------------------------------------------------------------


def test_classify_citekey_exact():
    kind, score = resolve.classify_citekey(_CHENG_REAL, _CHENG_REAL)
    assert kind == "exact"
    assert score == 1.0


def test_classify_citekey_variant_is_the_demonstrated_bug():
    # The constructed key (no 'a') vs the stored key (with 'a'): same base ->
    # 'variant'. This is exactly the pair the exact filter used to drop.
    kind, _ = resolve.classify_citekey(_CHENG_CONSTRUCTED, _CHENG_REAL)
    assert kind == "variant"


def test_classify_citekey_variant_between_sibling_suffixes():
    # Two disambiguation siblings (a vs b) share a base -> variant (the dupe pair).
    kind, _ = resolve.classify_citekey(
        "dignathHowCanPrimary2008a", "dignathHowCanPrimary2008b"
    )
    assert kind == "variant"


def test_classify_citekey_prefix_when_year_omitted():
    # Query truncated before the year is a prefix of the stored key.
    kind, _ = resolve.classify_citekey("chengGenerativeAIRequirements", _CHENG_REAL)
    assert kind == "prefix"


def test_classify_citekey_fuzzy_typo_above_threshold():
    # A mid-string typo (Requirement for Requirements) won't prefix-match but is
    # a near-identical string -> fuzzy.
    kind, score = resolve.classify_citekey(
        "chengGenerativeAIRequirement2026", _CHENG_REAL
    )
    assert kind == "fuzzy"
    assert score >= 0.85


def test_classify_citekey_none_for_unrelated_keys():
    kind, _ = resolve.classify_citekey(
        "lakatosFalsification1970", "vehtariPracticalBayesianModel2017"
    )
    assert kind == "none"


def test_classify_citekey_threshold_is_tunable():
    # Raising the bar past the pair's similarity demotes fuzzy to none.
    kind, _ = resolve.classify_citekey(
        "chengGenerativeAIRequirement2026", _CHENG_REAL, fuzzy_threshold=0.999
    )
    assert kind == "none"


# rank_citekey_candidates -----------------------------------------------------

_RANK_HITS = [
    {"citation-key": "vehtariPracticalBayesianModel2017", "library": "My Library"},
    {"citation-key": _CHENG_REAL, "library": "2026-LegoGrant"},
    {"citation-key": "chengGenerativeAIRequirement2026", "library": "My Library"},
]


def test_rank_citekey_candidates_orders_by_kind_then_drops_none():
    ranked = resolve.rank_citekey_candidates(_RANK_HITS, _CHENG_CONSTRUCTED)
    kinds = [c.kind for c in ranked]
    # The unrelated Vehtari hit is dropped (none); the real key is a variant, the
    # typo'd key is fuzzy; variant sorts before fuzzy.
    assert "none" not in kinds
    assert kinds[0] == "variant"
    assert ranked[0].hit["citation-key"] == _CHENG_REAL
    assert "fuzzy" in kinds


def test_rank_citekey_candidates_exact_sorts_first():
    hits = [{"citation-key": _CHENG_REAL, "library": "2026-LegoGrant"}]
    ranked = resolve.rank_citekey_candidates(hits, _CHENG_REAL)
    assert ranked[0].kind == "exact"


def test_rank_citekey_candidates_empty_when_nothing_close():
    hits = [{"citation-key": "vehtariPracticalBayesianModel2017", "library": "x"}]
    assert resolve.rank_citekey_candidates(hits, _CHENG_CONSTRUCTED) == []


# print_duplicate_note --------------------------------------------------------
#
# When an exact citekey resolves but disambiguation siblings (variant kind) also
# exist, list them with their library as the dupe-management signal. Only true
# base-variant siblings count — a fuzzy/prefix near-match is not a duplicate. No
# live duplicate exists to smoke-test against, so this pins the filtering here.


def test_print_duplicate_note_lists_only_variant_siblings(capsys):
    near = [
        resolve.ScoredHit(
            hit={"citation-key": "dignathHowCanPrimary2008b", "library": "My Library"},
            kind="variant",
            score=0.98,
        ),
        resolve.ScoredHit(
            hit={"citation-key": "dignathHowCanOther2009", "library": "Group-X"},
            kind="fuzzy",
            score=0.9,
        ),
    ]
    resolve.print_duplicate_note(near)
    out = capsys.readouterr().out
    assert "dignathHowCanPrimary2008b" in out
    assert "My Library" in out
    assert "duplicate" in out.lower()
    # The fuzzy near-match is NOT a duplicate and must not be listed.
    assert "dignathHowCanOther2009" not in out


def test_print_duplicate_note_silent_without_variants(capsys):
    near = [
        resolve.ScoredHit(
            hit={"citation-key": "somethingClose2020", "library": "x"},
            kind="fuzzy",
            score=0.88,
        )
    ]
    resolve.print_duplicate_note(near)
    assert capsys.readouterr().out == ""


# DOI path: no-match honesty and BBT-hydration failure ------------------------
#
# The DOI path is the workflow's front door, and it made the one claim this
# resolver exists to prevent: a CONFIRMED absence for a paper that is present.
#
# Mechanism reproduced live on 2026-08-31 (Zotero 10.0.1, DOI
# 10.1007/s44204-025-00247-1, Zotero key PP8QJM56, citekey
# kudinaUseLargeLanguage2025): the stock local API finds the citekey by DOI
# field, `search_by_doi` then re-hydrates it through BBT `item.search`, and
# Better BibTeX answered -32603 "ZoteroInvalidDataError: Invalid condition
# 'blockStart' in hasOperator()". The hydration error was swallowed, so the DOI
# branch of `print_no_match` still asserted that no item carries the DOI.
#
# Two separate obligations are pinned below: the search must SURFACE the failure
# (and still report the copies the stock API already proved exist), and the
# no-match message must not claim a confirmed absence once anything errored.

_KUDINA_DOI = "10.1007/s44204-025-00247-1"
_KUDINA_CITEKEY = "kudinaUseLargeLanguage2025"
_KUDINA_TITLE = "The use of large language models as scaffolds for proleptic reasoning"

# The BBT fault in the shape rpc() raises it: RuntimeError(error_object).
_BBT_ITEM_SEARCH_FAULT = RuntimeError(
    {
        "code": -32603,
        "message": (
            "ZoteroInvalidDataError: Invalid condition 'blockStart' in hasOperator()"
        ),
    }
)


def _kudina_local_item(library_name, *, citekey=_KUDINA_CITEKEY):
    """A stock local API envelope, shaped as the live one for PP8QJM56."""
    return {
        "key": "PP8QJM56",
        "library": {"type": "user", "id": 305867, "name": library_name},
        "data": {
            "key": "PP8QJM56",
            "itemType": "journalArticle",
            "title": _KUDINA_TITLE,
            "creators": [
                {"creatorType": "author", "lastName": "Kudina", "firstName": "Olya"},
                {"creatorType": "author", "lastName": "Ballsun-Stanton"},
                {"creatorType": "author", "lastName": "Alfano"},
            ],
            "date": "2025-02-01",
            "DOI": _KUDINA_DOI,
            "citationKey": citekey,
            "collections": ["JCDGG2Z7", "5BPN2U2H"],
        },
    }


def _fail_rpc(*_args, **_kwargs):
    raise _BBT_ITEM_SEARCH_FAULT


def _stub_doi_items(monkeypatch, items, failed_libraries=()):
    monkeypatch.setattr(
        resolve,
        "search_doi_items",
        lambda _doi: resolve.DoiSearch(
            items=tuple(items), failed_libraries=tuple(failed_libraries)
        ),
    )


def test_search_by_doi_reports_the_bbt_hydration_failure(monkeypatch):
    """A swallowed hydration error is what turned a present paper into 'absent'."""
    _stub_doi_items(monkeypatch, [_kudina_local_item("My Library")])
    monkeypatch.setattr(resolve, "rpc", _fail_rpc)

    _papers, errors = resolve.search_by_doi(_KUDINA_DOI)

    assert errors, "a failed BBT hydration must be reported, never swallowed"
    assert _KUDINA_CITEKEY in errors[0]


def test_search_by_doi_falls_back_to_the_stock_envelope_when_bbt_fails(monkeypatch):
    """The stock API already returned the item; BBT failing must not lose it."""
    _stub_doi_items(
        monkeypatch,
        [_kudina_local_item("My Library"), _kudina_local_item("2026-ailoc-stage1")],
    )
    monkeypatch.setattr(resolve, "rpc", _fail_rpc)

    papers, _errors = resolve.search_by_doi(_KUDINA_DOI)

    assert [(p.citekey, p.library) for p in papers] == [
        (_KUDINA_CITEKEY, "My Library"),
        (_KUDINA_CITEKEY, "2026-ailoc-stage1"),
    ]
    assert papers[0].doi == _KUDINA_DOI
    assert papers[0].authors == ("Kudina", "Ballsun-Stanton", "Alfano")
    assert papers[0].year == 2025
    assert papers[0].title == _KUDINA_TITLE


def test_search_by_doi_fallback_drops_a_copy_whose_doi_does_not_match(monkeypatch):
    """The fallback keeps the DOI equality rule the BBT path applies."""
    other = _kudina_local_item("My Library")
    other["data"] = {**other["data"], "DOI": "10.9999/not-the-one"}
    _stub_doi_items(monkeypatch, [other])
    monkeypatch.setattr(resolve, "rpc", _fail_rpc)

    papers, errors = resolve.search_by_doi(_KUDINA_DOI)

    assert papers == []
    assert errors, "the hydration failure is still reported for an empty result"


def test_search_by_doi_prefers_bbt_hydration_while_it_works(monkeypatch):
    """Positive control: the healthy path is unchanged, and reports no errors."""
    _stub_doi_items(monkeypatch, [_kudina_local_item("My Library")])
    bbt_hit = {
        "citation-key": _KUDINA_CITEKEY,
        "library": "2026-SARDI-LLM-Lecture-BallsunStanton",
        "DOI": _KUDINA_DOI,
        "title": _KUDINA_TITLE,
        "author": [{"family": "Kudina"}],
        "issued": {"date-parts": [[2025, 2, 1]]},
    }
    monkeypatch.setattr(resolve, "rpc", lambda *_a, **_k: [bbt_hit])

    papers, errors = resolve.search_by_doi(_KUDINA_DOI)

    assert errors == []
    # The BBT hit's library, not the stock envelope's, proves BBT was used.
    assert [(p.citekey, p.library) for p in papers] == [
        (_KUDINA_CITEKEY, "2026-SARDI-LLM-Lecture-BallsunStanton")
    ]


def test_search_by_doi_reports_a_library_that_could_not_be_searched(monkeypatch):
    """An unsearched library makes an empty result inconclusive, not an absence."""
    _stub_doi_items(
        monkeypatch,
        [],
        failed_libraries=("http://localhost:23119/api/groups/14/items: timeout",),
    )
    monkeypatch.setattr(resolve, "rpc", _fail_rpc)

    papers, errors = resolve.search_by_doi(_KUDINA_DOI)

    assert papers == []
    assert errors and "groups/14" in errors[0]


def test_doi_no_match_is_inconclusive_when_a_search_errored(capsys):
    """The reported defect: a confirmed-absence claim over a failed search."""
    resolve.print_no_match(
        [_KUDINA_DOI],
        doi=_KUDINA_DOI,
        search_errors=[f"item.search {_KUDINA_CITEKEY!r}: ZoteroInvalidDataError"],
    )
    out = capsys.readouterr().out

    assert "no item carries this DOI" not in out
    assert "inconclusive" in out


def test_doi_no_match_still_concludes_absence_when_every_search_succeeded(capsys):
    """Positive control: without errors the DOI field search IS conclusive.

    Without this the test above could pass against a resolver that had simply
    stopped making the claim at all, which would be a different defect.
    """
    resolve.print_no_match([_KUDINA_DOI], doi=_KUDINA_DOI, search_errors=[])
    out = capsys.readouterr().out

    assert "no item carries this DOI" in out
