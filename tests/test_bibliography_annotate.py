"""Tests for plugins/denubis-academic/skills/using-bibliography/annotate.py.

Covers the functional core of the annotate-back workflow: turning a citation
(citekey, page, quote, note) into a Zotero highlight annotation via the
zotero-api-plus add-highlight endpoint in rects (position) mode.

The pure functions tested here:
  - quote_fingerprint      stable dedup key for a passage (whitespace/case proof)
  - build_annotation_comment   note + pandoc cite + embedded dedup marker
  - marker_present         has this passage already been annotated? (idempotency)
  - build_highlight_payload    the rects-mode POST body
  - parse_highlight_response   the add-highlight response / structured-error contract

The HTTP + PyMuPDF shell is not exercised here; only the pure functions are.

Endpoint contracts read from ~/people/Brian/zotero-api-plus/src/{addon.ts,
utils/highlight.ts,utils/annotations.ts}, not transcribed from documentation.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ANNOTATE = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "annotate.py"
)


def _load_annotate():
    spec = importlib.util.spec_from_file_location("annotate_under_test", _ANNOTATE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["annotate_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


annotate = _load_annotate()


# --- quote_fingerprint ------------------------------------------------------


def test_quote_fingerprint_is_deterministic():
    q = "teachers face challenges such as insufficient CK"
    assert annotate.quote_fingerprint(q) == annotate.quote_fingerprint(q)


def test_quote_fingerprint_ignores_whitespace_differences():
    # The rendered markdown and the live PDF text layer differ in spacing /
    # line breaks; the same passage must dedup across that drift.
    a = annotate.quote_fingerprint("teachers face   challenges\nsuch as")
    b = annotate.quote_fingerprint("teachers face challenges such as")
    assert a == b


def test_quote_fingerprint_ignores_case():
    assert annotate.quote_fingerprint("The Cat Sat") == annotate.quote_fingerprint(
        "the cat sat"
    )


def test_quote_fingerprint_distinguishes_different_quotes():
    assert annotate.quote_fingerprint("alpha beta") != annotate.quote_fingerprint(
        "gamma delta"
    )


def test_quote_fingerprint_is_short_hex():
    fp = annotate.quote_fingerprint("anything at all")
    assert len(fp) == 8
    int(fp, 16)  # raises if not hex


# --- build_annotation_comment + marker_present (roundtrip) ------------------


def test_comment_contains_note_citation_and_is_dedupable():
    note = "used to support the CK-gap claim"
    quote = "teachers face challenges such as insufficient CK"
    comment = annotate.build_annotation_comment(
        note=note, citekey="yimTeachers2024", page=7, quote=quote
    )
    assert note in comment
    assert "[@yimTeachers2024, p. 7]" in comment
    # The comment carries a marker that marker_present can recover.
    fp = annotate.quote_fingerprint(quote)
    assert annotate.marker_present([{"comment": comment}], fp) is True


def test_comment_without_note_still_cites_and_dedups():
    quote = "a quote with no human note attached"
    comment = annotate.build_annotation_comment(
        note="", citekey="k2024", page=3, quote=quote
    )
    assert "[@k2024, p. 3]" in comment
    assert annotate.marker_present(
        [{"comment": comment}], annotate.quote_fingerprint(quote)
    )


def test_marker_present_false_when_passage_absent():
    annotations = [
        {"type": "highlight", "comment": "[@other2020, p. 1] some unrelated marker"},
        {"type": "note", "comment": "a plain sticky note"},
    ]
    assert (
        annotate.marker_present(annotations, annotate.quote_fingerprint("missing"))
        is False
    )


def test_marker_present_scans_all_annotation_types():
    quote = "shared across a note fallback"
    note_comment = annotate.build_annotation_comment(
        note="", citekey="k", page=2, quote=quote
    )
    # The passage was recorded as a NOTE (the highlight fell back); a later run
    # must still see it as done.
    annotations = [{"type": "note", "comment": note_comment}]
    assert annotate.marker_present(annotations, annotate.quote_fingerprint(quote))


def test_marker_present_empty_list_is_false():
    assert annotate.marker_present([], annotate.quote_fingerprint("x")) is False


# --- build_highlight_payload ------------------------------------------------


def test_highlight_payload_carries_rects_to_select_position_mode():
    rects = [[72.0, 100.0, 300.0, 112.0]]
    payload = annotate.build_highlight_payload(
        key="ABCD1234",
        page=8,
        rects=rects,
        page_height=792.0,
        text="the highlighted span",
        comment="a comment",
    )
    # Presence of `rects` is what switches the endpoint to rects mode.
    assert payload["rects"] == rects
    assert payload["pageHeight"] == 792.0
    assert payload["key"] == "ABCD1234"
    assert payload["page"] == 8
    assert payload["text"] == "the highlighted span"
    assert payload["comment"] == "a comment"


def test_highlight_payload_omits_optional_fields_when_absent():
    payload = annotate.build_highlight_payload(
        key="K",
        page=1,
        rects=[[0.0, 0.0, 1.0, 1.0]],
        page_height=792.0,
        text="t",
        comment="c",
    )
    assert "libraryID" not in payload
    assert "color" not in payload


def test_highlight_payload_includes_optional_fields_when_set():
    payload = annotate.build_highlight_payload(
        key="K",
        page=1,
        rects=[[0.0, 0.0, 1.0, 1.0]],
        page_height=792.0,
        text="t",
        comment="c",
        library_id=27,
        color="#ffd400",
    )
    assert payload["libraryID"] == 27
    assert payload["color"] == "#ffd400"


# --- parse_highlight_response -----------------------------------------------


def test_parse_highlight_success_returns_body():
    body = json.dumps({"ok": True, "key": "H1", "page": 8, "rects": [[1, 2, 3, 4]]})
    r = annotate.parse_highlight_response(200, body, "application/json")
    assert r["key"] == "H1"
    assert r["page"] == 8


def test_parse_highlight_structured_error_carries_code():
    body = json.dumps(
        {
            "ok": False,
            "code": "span_not_found",
            "message": "Error: end of span not found",
        }
    )
    with pytest.raises(annotate.HighlightError) as ei:
        annotate.parse_highlight_response(422, body, "application/json")
    assert ei.value.code == "span_not_found"
    assert "end of span" in str(ei.value)


def test_parse_highlight_plaintext_error_has_no_code():
    with pytest.raises(annotate.HighlightError) as ei:
        annotate.parse_highlight_response(
            404, "Error: No item with key ZZZ", "text/plain"
        )
    assert ei.value.code is None
    assert "No item with key" in str(ei.value)


def test_parse_highlight_non_json_200_raises():
    with pytest.raises(annotate.HighlightError):
        annotate.parse_highlight_response(200, "not json", "text/plain")


# --- choose_resolution (multi-library copy selection) -----------------------
# A paper can live in several libraries under one citekey; only some copies have
# the PDF attached. (Live case: one citekey exists in both a workshop group
# (no PDF) and another group (PDF present).)


def test_choose_resolution_picks_the_copy_with_a_pdf():
    candidates = [
        {"item_key": "NOPDF", "library_id": 23, "library": "GroupA", "pdf_paths": []},
        {
            "item_key": "HASPDF",
            "library_id": 27,
            "library": "groupB",
            "pdf_paths": ["/x/y.pdf"],
        },
    ]
    key, lib, pdf = annotate.choose_resolution(candidates)
    assert key == "HASPDF"
    assert lib == 27
    assert str(pdf) == "/x/y.pdf"


def test_choose_resolution_prefers_first_when_multiple_have_pdf():
    candidates = [
        {
            "item_key": "A",
            "library_id": 1,
            "library": "My Library",
            "pdf_paths": ["/a.pdf"],
        },
        {
            "item_key": "B",
            "library_id": 27,
            "library": "groupB",
            "pdf_paths": ["/b.pdf"],
        },
    ]
    key, _, pdf = annotate.choose_resolution(candidates)
    assert key == "A"
    assert str(pdf) == "/a.pdf"


def test_choose_resolution_raises_listing_libraries_when_no_pdf():
    candidates = [
        {"item_key": "A", "library_id": 23, "library": "GroupA", "pdf_paths": []},
        {"item_key": "B", "library_id": 99, "library": "Other", "pdf_paths": []},
    ]
    with pytest.raises(annotate.ResolveError) as ei:
        annotate.choose_resolution(candidates)
    msg = str(ei.value)
    assert "GroupA" in msg and "Other" in msg  # libraries tried are surfaced


def test_choose_resolution_raises_on_no_candidates():
    with pytest.raises(annotate.ResolveError):
        annotate.choose_resolution([])


# resolve_item: stock search replaced BBT item.search ---------------------------
#
# The same citekey can live in several libraries. The stock envelope carries the
# Zotero item key directly (no `id` URI to parse) and the library's human name,
# which user.groups maps to the BBT library id that item.export still needs for
# the attachment path. BBT's item.search errors on every query under Zotero 10
# (issue #3587), so it must never be reached from here.

_CITEKEY = "kudinaUseLargeLanguage2025"


def _envelope(key, citekey, library, *, group_id=None):
    lib = {
        "type": "group" if group_id else "user",
        "id": group_id or 305867,
        "name": library,
    }
    data = {"key": key, "itemType": "journalArticle", "citationKey": citekey}
    return {"key": key, "library": lib, "data": data}


def _no_rpc(method, *_a, **_k):
    raise AssertionError(f"BBT JSON-RPC {method!r} must not run here")


def test_resolve_item_uses_stock_search_and_the_envelope_key(monkeypatch):
    found = annotate.LibrarySearch(
        items=(
            _envelope("NEARMISS", "kudinaOtherPaper2020", "My Library"),
            _envelope("NOPDF001", _CITEKEY, "My Library"),
            _envelope("HASPDF02", _CITEKEY, "2026-ailoc-stage1", group_id=6624981),
        ),
        failed_libraries=(),
    )
    monkeypatch.setattr(annotate, "search_items", lambda _q, **_k: found)
    calls = []

    def fake_rpc(method, params):
        calls.append((method, params))
        if method == "user.groups":
            return [
                {"id": 1, "name": "My Library"},
                {"id": 7, "name": "2026-ailoc-stage1"},
            ]
        if method == "item.export":
            _keys, _fmt, library_id = params
            if library_id == 7:
                return [
                    "@article{k,\n  file = {PDF:/papers/kudina.pdf:application/pdf}\n}"
                ]
            return ["@article{k,\n}"]
        raise AssertionError(f"unexpected RPC {method!r}")

    monkeypatch.setattr(annotate, "_rpc", fake_rpc)

    item_key, library_id, pdf = annotate.resolve_item(_CITEKEY)

    assert (item_key, library_id, pdf) == ("HASPDF02", 7, Path("/papers/kudina.pdf"))
    # Only the exact-citekey copies are exported; the near-miss never reaches
    # BBT, and nothing here is a search.
    assert [p for m, p in calls if m == "item.export"] == [
        [[_CITEKEY], "Better BibLaTeX", 1],
        [[_CITEKEY], "Better BibLaTeX", 7],
    ]
    assert not any(m == "item.search" for m, _p in calls)


def test_resolve_item_reports_no_exact_match_and_unsearched_libraries(monkeypatch):
    found = annotate.LibrarySearch(
        items=(_envelope("NEARMISS", "kudinaOtherPaper2020", "My Library"),),
        failed_libraries=("http://localhost:23119/api/groups/14/items: timeout",),
    )
    monkeypatch.setattr(annotate, "search_items", lambda _q, **_k: found)
    monkeypatch.setattr(annotate, "_rpc", _no_rpc)

    with pytest.raises(annotate.ResolveError) as ei:
        annotate.resolve_item(_CITEKEY)

    msg = str(ei.value)
    assert _CITEKEY in msg
    # A library that could not be searched makes the miss inconclusive, and the
    # annotate path WRITES to the library, so the caller must see it.
    assert "groups/14" in msg
