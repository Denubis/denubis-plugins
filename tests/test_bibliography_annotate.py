"""Tests for plugins/denubis-bibliography/skills/using-bibliography/annotate.py.

Covers the functional core of the annotate-back workflow: turning a citation
(citekey, page, quote, note) into a Zotero highlight annotation via the
zotero-api-plus add-highlight endpoint in rects (position) mode.

The pure functions tested here:
  - extract_item_key       BBT item.search `id` URI -> Zotero item key
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
    / "denubis-bibliography"
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


# --- extract_item_key -------------------------------------------------------


def test_extract_item_key_from_user_library_uri():
    uri = "http://zotero.org/users/305867/items/MAAT7PA5"
    assert annotate.extract_item_key(uri) == "MAAT7PA5"


def test_extract_item_key_from_group_library_uri():
    uri = "http://zotero.org/groups/6549571/items/ABCD1234"
    assert annotate.extract_item_key(uri) == "ABCD1234"


def test_extract_item_key_passes_through_a_bare_key():
    # Tolerate being handed an already-extracted key.
    assert annotate.extract_item_key("MAAT7PA5") == "MAAT7PA5"


def test_extract_item_key_tolerates_trailing_slash():
    uri = "http://zotero.org/users/305867/items/MAAT7PA5/"
    assert annotate.extract_item_key(uri) == "MAAT7PA5"


def test_extract_item_key_rejects_empty():
    with pytest.raises(ValueError):
        annotate.extract_item_key("")


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
    assert annotate.marker_present(annotations, annotate.quote_fingerprint("missing")) is False


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
    body = json.dumps(
        {"ok": True, "key": "H1", "page": 8, "rects": [[1, 2, 3, 4]]}
    )
    r = annotate.parse_highlight_response(200, body, "application/json")
    assert r["key"] == "H1"
    assert r["page"] == 8


def test_parse_highlight_structured_error_carries_code():
    body = json.dumps(
        {"ok": False, "code": "span_not_found", "message": "Error: end of span not found"}
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
# the PDF attached. (Live case: ballsun-stanton...2025 exists in both 'GenAI
# workshop Aarhus' (no PDF) and the bjet group (PDF present).)


def test_choose_resolution_picks_the_copy_with_a_pdf():
    candidates = [
        {"item_key": "NOPDF", "library_id": 23, "library": "Aarhus", "pdf_paths": []},
        {"item_key": "HASPDF", "library_id": 27, "library": "bjet", "pdf_paths": ["/x/y.pdf"]},
    ]
    key, lib, pdf = annotate.choose_resolution(candidates)
    assert key == "HASPDF"
    assert lib == 27
    assert str(pdf) == "/x/y.pdf"


def test_choose_resolution_prefers_first_when_multiple_have_pdf():
    candidates = [
        {"item_key": "A", "library_id": 1, "library": "My Library", "pdf_paths": ["/a.pdf"]},
        {"item_key": "B", "library_id": 27, "library": "bjet", "pdf_paths": ["/b.pdf"]},
    ]
    key, _, pdf = annotate.choose_resolution(candidates)
    assert key == "A"
    assert str(pdf) == "/a.pdf"


def test_choose_resolution_raises_listing_libraries_when_no_pdf():
    candidates = [
        {"item_key": "A", "library_id": 23, "library": "Aarhus", "pdf_paths": []},
        {"item_key": "B", "library_id": 99, "library": "Other", "pdf_paths": []},
    ]
    with pytest.raises(annotate.ResolveError) as ei:
        annotate.choose_resolution(candidates)
    msg = str(ei.value)
    assert "Aarhus" in msg and "Other" in msg  # libraries tried are surfaced


def test_choose_resolution_raises_on_no_candidates():
    with pytest.raises(annotate.ResolveError):
        annotate.choose_resolution([])
