"""Tests for plugins/denubis-bibliography/skills/using-bibliography/fetch.py.

Covers the functional core: resolve_target (human group + collection names ->
numeric groupID + collectionKey, the step that used to be improvised as a
fragile multi-line `python3 -c` block in bash) and parse_add_item_response
(the add-item-by-id contract: 200 success vs 400/404/500 plain-text errors).

The HTTP shell is not exercised here; only the pure functions are.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_FETCH = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-bibliography"
    / "skills"
    / "using-bibliography"
    / "fetch.py"
)


def _load_fetch():
    spec = importlib.util.spec_from_file_location("fetch_under_test", _FETCH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fetch_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


fetch = _load_fetch()


# Shape mirrors GET /api/plus/libraries (addon.ts GetLibrariesEndpoint):
# My Library is type "user" with no groupID; groups carry a groupID.
LIBRARIES = [
    {
        "type": "user",
        "libraryID": 1,
        "name": "My Library",
        "collections": [
            {"key": "AAA", "name": "Bayesian", "parentKey": None},
        ],
    },
    {
        "type": "group",
        "libraryID": 99,
        "groupID": 6549571,
        "name": "2026-bbs-jt-em-bjet-AI-metacognitive-1",
        "collections": [
            {"key": "BJETKEY", "name": "Bayesian / Methods", "parentKey": None},
            {"key": "OTHER", "name": "Drafts", "parentKey": None},
        ],
    },
    {
        "type": "group",
        "libraryID": 100,
        "groupID": 5224649,
        "name": "Dup",
        "collections": [
            {"key": "D1", "name": "Shared", "parentKey": None},
            {"key": "D2", "name": "Shared", "parentKey": "D1"},
        ],
    },
]


# --- resolve_target ---------------------------------------------------------


def test_resolves_group_by_name_and_collection_by_name():
    r = fetch.resolve_target(
        LIBRARIES,
        group="2026-bbs-jt-em-bjet-AI-metacognitive-1",
        collection="Bayesian / Methods",
    )
    assert r.group_id == 6549571
    assert r.collection_key == "BJETKEY"
    assert r.collection_name == "Bayesian / Methods"
    assert r.library_name == "2026-bbs-jt-em-bjet-AI-metacognitive-1"


def test_resolves_my_library_when_group_none():
    r = fetch.resolve_target(LIBRARIES, group=None, collection="Bayesian")
    assert r.group_id is None
    assert r.library_name == "My Library"
    assert r.collection_key == "AAA"


def test_resolves_my_library_by_name_case_insensitive():
    r = fetch.resolve_target(LIBRARIES, group="my library", collection=None)
    assert r.group_id is None
    assert r.library_name == "My Library"


def test_resolves_group_by_numeric_id():
    r = fetch.resolve_target(LIBRARIES, group="6549571", collection="Drafts")
    assert r.group_id == 6549571
    assert r.collection_key == "OTHER"


def test_no_collection_requested_yields_no_key():
    r = fetch.resolve_target(LIBRARIES, group="6549571", collection=None)
    assert r.group_id == 6549571
    assert r.collection_key is None
    assert r.collection_name is None


def test_collection_match_is_case_insensitive():
    r = fetch.resolve_target(
        LIBRARIES, group="6549571", collection="bayesian / methods"
    )
    assert r.collection_key == "BJETKEY"


def test_group_not_found_raises_and_lists_groups():
    with pytest.raises(fetch.ResolutionError) as ei:
        fetch.resolve_target(LIBRARIES, group="Nonexistent", collection=None)
    msg = str(ei.value)
    assert "Nonexistent" in msg
    # the available groups should be surfaced to the operator
    assert "2026-bbs-jt-em-bjet-AI-metacognitive-1" in msg


def test_collection_not_found_lists_available():
    with pytest.raises(fetch.ResolutionError) as ei:
        fetch.resolve_target(LIBRARIES, group="6549571", collection="Nope")
    msg = str(ei.value)
    assert "Nope" in msg
    assert "Drafts" in msg  # available collections listed


def test_ambiguous_collection_name_raises():
    with pytest.raises(fetch.ResolutionError) as ei:
        fetch.resolve_target(LIBRARIES, group="Dup", collection="Shared")
    assert "ambiguous" in str(ei.value).lower()


# --- parse_add_item_response ------------------------------------------------


def test_parse_success_returns_items():
    body = json.dumps(
        {
            "status": "success",
            "addedCount": 1,
            "titles": ["A Title"],
            "items": [{"title": "A Title", "key": "K1", "pdf": "present"}],
        }
    )
    r = fetch.parse_add_item_response(200, body, "application/json")
    assert r["addedCount"] == 1
    assert r["items"][0]["pdf"] == "present"


def test_parse_400_raises_with_server_message():
    with pytest.raises(fetch.FetchError) as ei:
        fetch.parse_add_item_response(
            400,
            "Error: No collection with key X in the target library",
            "text/plain",
        )
    assert "No collection with key" in str(ei.value)


def test_parse_404_raises_with_server_message():
    with pytest.raises(fetch.FetchError) as ei:
        fetch.parse_add_item_response(
            404, "Failed to find or save any items.", "text/plain"
        )
    assert "Failed to find or save" in str(ei.value)


def test_parse_non_json_200_raises():
    with pytest.raises(fetch.FetchError):
        fetch.parse_add_item_response(200, "not json at all", "text/plain")


# --- should_render -----------------------------------------------------------


def test_should_render_present():
    assert fetch.should_render("present") is True


def test_should_render_fetched():
    assert fetch.should_render("fetched") is True


def test_should_render_unavailable():
    # item added but no PDF on disk — nothing to render
    assert fetch.should_render("unavailable") is False


def test_should_render_error():
    assert fetch.should_render("error") is False


def test_should_render_unknown_status():
    assert fetch.should_render("") is False
    assert fetch.should_render("something-new") is False


def test_renderable_dois_filters_to_pdf_bearing_items():
    # Given add-item results keyed by DOI, only DOIs whose item has a
    # renderable PDF should be selected for the render pass.
    results = {
        "10.1/present": {"items": [{"key": "A", "pdf": "present"}]},
        "10.2/unavailable": {"items": [{"key": "B", "pdf": "unavailable"}]},
        "10.3/fetched": {"items": [{"key": "C", "pdf": "fetched"}]},
        "10.4/empty": {"items": []},
    }
    assert fetch.renderable_dois(results) == ["10.1/present", "10.3/fetched"]
