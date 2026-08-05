"""Tests for plugins/denubis-academic/skills/using-bibliography/copy_item.py.

Covers the functional core: resolve_copy_target (a human library name -> the
numeric **libraryID** copy-item needs, which is a different number space from
the groupID that add-item-by-id takes), build_copy_payload, and
parse_copy_response (the copy-item contract: 200 success vs structured
{ok:false, code, message} failures vs plain-text resolution failures).

Every expected value below is written literally in the test. Nothing is
imported from copy.py to compare against, so a change to its constants makes
these fail rather than silently agreeing with itself.

The HTTP shell is not exercised here; only the pure functions are.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_COPY = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "copy_item.py"
)


def _load_copy():
    spec = importlib.util.spec_from_file_location("copy_under_test", _COPY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["copy_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


copy_mod = _load_copy()


# Shape mirrors GET /api/plus/libraries (addon.ts GetLibrariesEndpoint).
# Note libraryID and groupID differ: the SARDI-style group below has
# libraryID 33 and groupID 6627731, which is exactly the confusion this
# module's resolution exists to prevent.
LIBRARIES = [
    {
        "type": "user",
        "libraryID": 1,
        "name": "My Library",
        "collections": [{"key": "AAA", "name": "Reading", "parentKey": None}],
    },
    {
        "type": "group",
        "libraryID": 33,
        "groupID": 6627731,
        "name": "2026-SARDI-LLM-Lecture",
        "collections": [
            {"key": "BBB", "name": "Lecture", "parentKey": None},
            {"key": "CCC", "name": "Dupe", "parentKey": None},
            {"key": "DDD", "name": "Dupe", "parentKey": "BBB"},
        ],
    },
]


class TestFindLibrary:
    def test_none_resolves_to_my_library(self):
        assert copy_mod.find_library(LIBRARIES, None)["libraryID"] == 1

    def test_my_library_by_name_case_insensitive(self):
        assert copy_mod.find_library(LIBRARIES, "my library")["libraryID"] == 1

    def test_group_by_exact_name(self):
        assert (
            copy_mod.find_library(LIBRARIES, "2026-SARDI-LLM-Lecture")["libraryID"]
            == 33
        )

    def test_digits_prefer_group_id_over_library_id(self):
        # 6627731 is the groupID of the library whose libraryID is 33.
        assert copy_mod.find_library(LIBRARIES, "6627731")["libraryID"] == 33

    def test_digits_fall_back_to_library_id(self):
        assert copy_mod.find_library(LIBRARIES, "33")["libraryID"] == 33

    def test_unknown_name_raises_and_lists_available(self):
        with pytest.raises(copy_mod.ResolutionError) as e:
            copy_mod.find_library(LIBRARIES, "nope")
        assert "nope" in str(e.value)
        assert "My Library" in str(e.value)

    def test_unknown_number_raises(self):
        with pytest.raises(copy_mod.ResolutionError):
            copy_mod.find_library(LIBRARIES, "424242")


class TestFindCollection:
    def test_none_returns_no_collection(self):
        assert copy_mod.find_collection(LIBRARIES[1], None) == (None, None)

    def test_exact_name(self):
        assert copy_mod.find_collection(LIBRARIES[1], "Lecture") == ("Lecture", "BBB")

    def test_unknown_name_raises(self):
        with pytest.raises(copy_mod.ResolutionError) as e:
            copy_mod.find_collection(LIBRARIES[1], "Missing")
        assert "Missing" in str(e.value)

    def test_ambiguous_name_raises_and_names_the_escape_hatch(self):
        with pytest.raises(copy_mod.ResolutionError) as e:
            copy_mod.find_collection(LIBRARIES[1], "Dupe")
        assert "--to-collection-key" in str(e.value)


class TestResolveCopyTarget:
    def test_resolves_group_to_library_id_not_group_id(self):
        t = copy_mod.resolve_copy_target(
            LIBRARIES, to="2026-SARDI-LLM-Lecture", collection=None
        )
        # The whole point: 33, never 6627731.
        assert t.library_id == 33
        assert t.collection_key is None

    def test_resolves_collection_within_target(self):
        t = copy_mod.resolve_copy_target(
            LIBRARIES, to="2026-SARDI-LLM-Lecture", collection="Lecture"
        )
        assert (t.library_id, t.collection_key) == (33, "BBB")

    def test_my_library_target(self):
        t = copy_mod.resolve_copy_target(LIBRARIES, to="My Library", collection=None)
        assert t.library_id == 1


class TestBuildCopyPayload:
    def _target(self, collection_key=None):
        return copy_mod.CopyTarget(
            library_name="My Library",
            library_id=1,
            collection_name=None,
            collection_key=collection_key,
        )

    def test_minimal_payload_omits_optional_fields(self):
        payload = copy_mod.build_copy_payload(
            key="ABCD1234", source_library_id=None, target=self._target()
        )
        assert payload == {"key": "ABCD1234", "targetLibraryID": 1}

    def test_includes_source_library_when_given(self):
        payload = copy_mod.build_copy_payload(
            key="ABCD1234", source_library_id=33, target=self._target()
        )
        assert payload == {
            "key": "ABCD1234",
            "targetLibraryID": 1,
            "libraryID": 33,
        }

    def test_includes_collection_when_given(self):
        payload = copy_mod.build_copy_payload(
            key="ABCD1234",
            source_library_id=None,
            target=self._target(collection_key="AAA"),
        )
        assert payload == {
            "key": "ABCD1234",
            "targetLibraryID": 1,
            "targetCollectionKey": "AAA",
        }


class TestParseCopyResponse:
    def test_200_returns_parsed_body(self):
        body = json.dumps(
            {"ok": True, "key": "NEW123", "created": True, "attachments": []}
        )
        assert copy_mod.parse_copy_response(200, body, "application/json") == {
            "ok": True,
            "key": "NEW123",
            "created": True,
            "attachments": [],
        }

    def test_200_with_non_json_body_raises(self):
        with pytest.raises(copy_mod.CopyError):
            copy_mod.parse_copy_response(200, "not json", "text/plain")

    def test_structured_error_surfaces_code_and_message(self):
        body = json.dumps(
            {
                "ok": False,
                "code": "unknown_target_collection",
                "message": "Target collection does not exist in the target library",
            }
        )
        with pytest.raises(copy_mod.CopyError) as e:
            copy_mod.parse_copy_response(400, body, "application/json")
        assert "unknown_target_collection" in str(e.value)
        assert "does not exist" in str(e.value)

    def test_plain_text_resolution_failure_surfaced_verbatim(self):
        # resolveItemByKey failures are text/plain with no code (addon.ts).
        with pytest.raises(copy_mod.CopyError) as e:
            copy_mod.parse_copy_response(404, "Error: No item with key ZZZ", "text/plain")
        assert "No item with key ZZZ" in str(e.value)


class TestSummariseAttachments:
    def test_counts_by_status(self):
        resp = {
            "attachments": [
                {"key": "A", "status": "copied"},
                {"key": "B", "status": "copied"},
                {"key": "C", "status": "source-file-missing"},
            ]
        }
        assert copy_mod.summarise_attachments(resp) == {
            "copied": 2,
            "source-file-missing": 1,
        }

    def test_empty_and_missing_are_both_empty(self):
        assert copy_mod.summarise_attachments({"attachments": []}) == {}
        assert copy_mod.summarise_attachments({}) == {}


class TestCopySucceeded:
    def test_clean_copy_succeeds(self):
        assert copy_mod.copy_succeeded(
            {"ok": True, "key": "K", "attachments": [{"key": "A", "status": "copied"}]}
        )

    def test_imported_linked_file_counts_as_success(self):
        assert copy_mod.copy_succeeded(
            {"ok": True, "key": "K", "attachments": [{"key": "A", "status": "imported"}]}
        )

    def test_already_present_is_a_successful_top_up(self):
        assert copy_mod.copy_succeeded(
            {
                "ok": True,
                "key": "K",
                "attachments": [{"key": "A", "status": "already-present"}],
            }
        )

    def test_missing_source_file_is_a_partial_not_a_success(self):
        assert not copy_mod.copy_succeeded(
            {
                "ok": True,
                "key": "K",
                "attachments": [{"key": "A", "status": "source-file-missing"}],
            }
        )

    def test_copy_failed_is_a_partial(self):
        assert not copy_mod.copy_succeeded(
            {
                "ok": True,
                "key": "K",
                "attachments": [
                    {"key": "A", "status": "copied"},
                    {"key": "B", "status": "copy-failed", "message": "boom"},
                ],
            }
        )

    def test_null_key_means_nothing_landed(self):
        assert not copy_mod.copy_succeeded(
            {"ok": True, "key": None, "attachments": []}
        )
