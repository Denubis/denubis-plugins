"""Tests for plugins/denubis-academic/skills/using-bibliography/resolve.py.

Covers the pure functional core of citekey-first resolution: turning stock
local API envelopes into Papers, selecting the exact citekey matches out of a
word-ANDed quicksearch (which returns near-misses alongside the real item), and
the sweep/union/dedup seams with the HTTP transport stubbed. The HTTP shell that
talks to Zotero is verified live, not exercised here.
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


def _paper(citekey, library="My Library", *, doi="", title=""):
    """A Paper as the stock local API sweep produces it (no numeric library id)."""
    return resolve.Paper(
        citekey=citekey,
        doi=doi,
        title=title,
        authors=(),
        year=None,
        library=library,
        library_id=None,
        collection_keys=(),
    )


# A token search is word-ANDed over title, creators, year and citekey, so a
# citekey query returns near-misses (the same author's other papers, a
# disambiguation sibling) next to the exact item.
PAPERS = [
    _paper(
        "vehtariPracticalBayesianModel2017",
        doi="10.1007/s11222-016-9696-4",
        title="Practical Bayesian model evaluation using LOO-CV and WAIC",
    ),
    _paper(
        "vehtariRankNormalizationFolding2021",
        doi="10.1214/20-BA1221",
        title="Rank-normalization, folding, and localization",
    ),
]

# Same citekey present in two libraries (the real multi-library duplicate case:
# a paper lives in My Library AND a group, only some copies with a PDF).
PAPERS_MULTI = [
    _paper("sharedKey2020", "My Library", doi="10.1/x"),
    _paper("sharedKey2020", "2026-example-library-1", doi="10.1/x"),
    _paper("otherKey2020", "My Library", doi="10.2/y"),
]


def test_selects_only_exact_citekey_match():
    out = resolve.select_citekey_matches(PAPERS, "vehtariPracticalBayesianModel2017")
    assert len(out) == 1
    assert out[0].library == "My Library"
    assert out[0].doi == "10.1007/s11222-016-9696-4"


def test_returns_every_library_copy_of_a_citekey():
    out = resolve.select_citekey_matches(PAPERS_MULTI, "sharedKey2020")
    assert len(out) == 2
    assert {p.library for p in out} == {"My Library", "2026-example-library-1"}


def test_no_match_returns_empty():
    assert (
        resolve.select_citekey_matches(
            PAPERS, "lakatosFalsificationMethodologyScientific1970a"
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


# --- paper_from_local_item: the one Paper producer ---------------------------
#
# Every search now returns stock local API envelopes (fields under `data`,
# citekey as `citationKey`, creators with `lastName`/`name`, the date a string,
# the library an object with the human `name`). The shape below mirrors the live
# envelope for PP8QJM56 (kudinaUseLargeLanguage2025), captured 2026-08-31.

LOCAL_ITEM = {
    "key": "PP8QJM56",
    "library": {"type": "user", "id": 305867, "name": "My Library"},
    "data": {
        "key": "PP8QJM56",
        "itemType": "journalArticle",
        "title": "The use of large language models as scaffolds",
        "creators": [
            {"creatorType": "author", "lastName": "Kudina", "firstName": "Olya"},
            {"creatorType": "author", "lastName": "Ballsun-Stanton"},
            {"creatorType": "author", "name": "Macquarie University"},
        ],
        "date": "2025-02-01",
        "DOI": "10.1007/s44204-025-00247-1",
        "citationKey": "kudinaUseLargeLanguage2025",
        "collections": ["JCDGG2Z7", "5BPN2U2H"],
    },
}


def test_paper_from_local_item_extracts_all_fields():
    p = resolve.paper_from_local_item(LOCAL_ITEM)
    assert p.citekey == "kudinaUseLargeLanguage2025"
    assert p.doi == "10.1007/s44204-025-00247-1"
    assert p.title == "The use of large language models as scaffolds"
    # Two-field creators by surname; a single-field (institutional) creator by
    # its name. Dropping an author is the class of failure the resolver exists
    # to remove, and matches_query compares surnames for equality anyway.
    assert p.authors == ("Kudina", "Ballsun-Stanton", "Macquarie University")
    assert p.year == 2025
    assert p.library == "My Library"
    # The envelope's numeric id is Zotero's user/group id, not the BBT library
    # id enrich_paper resolves against, so it is deliberately not reported.
    assert p.library_id is None
    assert p.collection_keys == ("JCDGG2Z7", "5BPN2U2H")


def test_paper_from_local_item_tolerates_missing_fields():
    bare = {"key": "X", "library": {}, "data": {"itemType": "book"}}
    p = resolve.paper_from_local_item(bare)
    assert p.citekey == ""
    assert p.doi == ""
    assert p.title == ""
    assert p.authors == ()
    assert p.year is None
    assert p.library == ""
    assert p.collection_keys == ()


def test_paper_from_local_item_skips_a_creator_with_no_name():
    item = {
        **LOCAL_ITEM,
        "data": {
            **LOCAL_ITEM["data"],
            "creators": [{"creatorType": "author", "firstName": "Anonymous"}],
        },
    }
    assert resolve.paper_from_local_item(item).authors == ()


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
    out = resolve._trigger_autoexport(Path("/p.bib"), starting_retries=3, retry_delay=0)
    assert out is not None
    assert out.kind == "triggered"


def test_trigger_autoexport_gives_up_after_starting_retries(monkeypatch):
    monkeypatch.setattr(
        resolve,
        "post_run_autoexport",
        lambda _p, **_k: (503, '{"status": "bbt-starting"}'),
    )
    out = resolve._trigger_autoexport(Path("/p.bib"), starting_retries=2, retry_delay=0)
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
    assert (
        resolve.citekey_base("dignathHowCanPrimary2008a") == "dignathHowCanPrimary2008"
    )


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

_RANK_PAPERS = [
    _paper("vehtariPracticalBayesianModel2017", "My Library"),
    _paper(_CHENG_REAL, "2026-LegoGrant"),
    _paper("chengGenerativeAIRequirement2026", "My Library"),
]


def test_rank_citekey_candidates_orders_by_kind_then_drops_none():
    ranked = resolve.rank_citekey_candidates(_RANK_PAPERS, _CHENG_CONSTRUCTED)
    kinds = [c.kind for c in ranked]
    # The unrelated Vehtari paper is dropped (none); the real key is a variant,
    # the typo'd key is fuzzy; variant sorts before fuzzy.
    assert "none" not in kinds
    assert kinds[0] == "variant"
    assert ranked[0].paper.citekey == _CHENG_REAL
    assert "fuzzy" in kinds


def test_rank_citekey_candidates_exact_sorts_first():
    papers = [_paper(_CHENG_REAL, "2026-LegoGrant")]
    ranked = resolve.rank_citekey_candidates(papers, _CHENG_REAL)
    assert ranked[0].kind == "exact"


def test_rank_citekey_candidates_empty_when_nothing_close():
    papers = [_paper("vehtariPracticalBayesianModel2017", "x")]
    assert resolve.rank_citekey_candidates(papers, _CHENG_CONSTRUCTED) == []


# print_duplicate_note --------------------------------------------------------
#
# When an exact citekey resolves but disambiguation siblings (variant kind) also
# exist, list them with their library as the dupe-management signal. Only true
# base-variant siblings count — a fuzzy/prefix near-match is not a duplicate. No
# live duplicate exists to smoke-test against, so this pins the filtering here.


def test_print_duplicate_note_lists_only_variant_siblings(capsys):
    near = [
        resolve.ScoredHit(
            paper=_paper("dignathHowCanPrimary2008b", "My Library"),
            kind="variant",
            score=0.98,
        ),
        resolve.ScoredHit(
            paper=_paper("dignathHowCanOther2009", "Group-X"),
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
            paper=_paper("somethingClose2020", "x"),
            kind="fuzzy",
            score=0.88,
        )
    ]
    resolve.print_duplicate_note(near)
    assert capsys.readouterr().out == ""


# DOI path: stock envelopes only, and no-match honesty --------------------------
#
# The DOI path is the workflow's front door, and it once made the one claim this
# resolver exists to prevent: a CONFIRMED absence for a paper that is present.
# Reproduced live on 2026-08-31 (Zotero 10.0.1, DOI 10.1007/s44204-025-00247-1,
# key PP8QJM56, citekey kudinaUseLargeLanguage2025): the stock local API found
# the item by DOI field, `search_by_doi` re-hydrated it through BBT
# `item.search`, BBT answered "Invalid condition 'blockStart'", and the swallowed
# error left `print_no_match` asserting that no item carries the DOI.
#
# BBT is no longer consulted: the stock envelope carries everything a Paper
# needs, and BBT's item.search is broken on Zotero 10 for good (issue #3587).
# Two obligations remain pinned below: the search reports every copy the stock
# API proved exists, and a library that could not be searched is surfaced so the
# no-match message cannot claim a confirmed absence.

_KUDINA_DOI = "10.1007/s44204-025-00247-1"
_KUDINA_CITEKEY = "kudinaUseLargeLanguage2025"
_KUDINA_TITLE = "The use of large language models as scaffolds for proleptic reasoning"


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


def _stub_doi_items(monkeypatch, items, failed_libraries=()):
    monkeypatch.setattr(
        resolve,
        "search_doi_items",
        lambda _doi: resolve.LibrarySearch(
            items=tuple(items), failed_libraries=tuple(failed_libraries)
        ),
    )


def _forbid_bbt(monkeypatch):
    """Search must never touch Better BibTeX.

    BBT's JSON-RPC `item.search` errors on every query under Zotero 10 (issue
    #3587, unfixed in 9.0.63 and on master on 2026-09-02), and the stock
    envelope already carries everything a Paper needs. A search path that
    still reaches for BBT is the regression this guard exists to catch.
    """

    def explode(method, *_a, **_k):
        raise AssertionError(f"BBT JSON-RPC {method!r} must not run during search")

    monkeypatch.setattr(resolve, "rpc", explode)


def test_search_by_doi_returns_every_stock_copy_without_bbt(monkeypatch):
    _stub_doi_items(
        monkeypatch,
        [_kudina_local_item("My Library"), _kudina_local_item("2026-ailoc-stage1")],
    )
    _forbid_bbt(monkeypatch)

    papers, errors = resolve.search_by_doi(_KUDINA_DOI)

    assert errors == []
    assert [(p.citekey, p.library) for p in papers] == [
        (_KUDINA_CITEKEY, "My Library"),
        (_KUDINA_CITEKEY, "2026-ailoc-stage1"),
    ]
    assert papers[0].doi == _KUDINA_DOI
    assert papers[0].authors == ("Kudina", "Ballsun-Stanton", "Alfano")
    assert papers[0].year == 2025
    assert papers[0].title == _KUDINA_TITLE
    assert papers[0].collection_keys == ("JCDGG2Z7", "5BPN2U2H")


def test_search_by_doi_drops_a_copy_whose_doi_does_not_match(monkeypatch):
    """qmode=fields is `contains`; the equality rule holds on the way out too."""
    other = _kudina_local_item("My Library")
    other["data"] = {**other["data"], "DOI": "10.9999/not-the-one"}
    _stub_doi_items(monkeypatch, [other])
    _forbid_bbt(monkeypatch)

    papers, errors = resolve.search_by_doi(_KUDINA_DOI)

    assert papers == []
    assert errors == []


def test_search_by_doi_reports_a_library_that_could_not_be_searched(monkeypatch):
    """An unsearched library makes an empty result inconclusive, not an absence."""
    _stub_doi_items(
        monkeypatch,
        [],
        failed_libraries=("http://localhost:23119/api/groups/14/items: timeout",),
    )
    _forbid_bbt(monkeypatch)

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


# search_papers: the token sweep that replaced the BBT item.search loop --------
#
# Recall comes from searching EVERY supplied token and unioning the hits;
# precision comes from matches_query afterwards. The sweep itself is stock
# Zotero quicksearch (zotero_local_api.search_items). Pinned here: the union,
# the per-library-copy dedup, and that a library failure is recorded against
# its token rather than silently narrowing the corpus.


def _stub_search_items(monkeypatch, by_token):
    """by_token: token -> (envelopes, failed_libraries)."""

    def fake(query, *, qmode="titleCreatorYear"):
        assert qmode == "titleCreatorYear"
        items, failed = by_token[query]
        return resolve.LibrarySearch(items=tuple(items), failed_libraries=tuple(failed))

    monkeypatch.setattr(resolve, "search_items", fake)


def test_search_papers_unions_tokens_and_dedups_library_copies(monkeypatch):
    mine = _kudina_local_item("My Library")
    group = _kudina_local_item("2026-ailoc-stage1")
    _stub_search_items(
        monkeypatch,
        {
            _KUDINA_CITEKEY: ([mine, group], []),
            "kudina": ([mine], []),  # the same My Library copy, found again
        },
    )
    _forbid_bbt(monkeypatch)

    papers, errors = resolve.search_papers([_KUDINA_CITEKEY, "kudina"])

    assert errors == []
    assert [(p.citekey, p.library) for p in papers] == [
        (_KUDINA_CITEKEY, "My Library"),
        (_KUDINA_CITEKEY, "2026-ailoc-stage1"),
    ]


def test_search_papers_records_a_failed_library_against_its_token(monkeypatch):
    _stub_search_items(
        monkeypatch,
        {
            "Ghahramani": ([], ["http://localhost:23119/api/groups/14/items: timeout"]),
            "wade": ([_kudina_local_item("My Library")], []),
        },
    )
    _forbid_bbt(monkeypatch)

    papers, errors = resolve.search_papers(["Ghahramani", "wade"])

    # One token's failure must not sink the whole resolve: the other token's
    # hits still arrive, and the failure is reported so a no-match is
    # qualified as inconclusive rather than absent.
    assert [p.citekey for p in papers] == [_KUDINA_CITEKEY]
    assert len(errors) == 1
    assert "Ghahramani" in errors[0]
    assert "groups/14" in errors[0]
