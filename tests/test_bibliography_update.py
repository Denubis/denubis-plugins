"""Tests for plugins/denubis-academic/skills/using-bibliography/update_item.py.

Covers the functional core: CLI change specs -> payload channels, response
parsing (200 vs structured {ok:false,code,message} vs plain-text resolution
failures), and the diff rendering that the --apply gate exists to protect.

Every expected value below is written literally. Nothing is imported from
update_item.py to compare against, so a change to its constants or formatting
makes these fail rather than silently agreeing with itself.

The HTTP shell is not exercised here; only the pure functions are.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SKILL_DIR = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
)


def _load_update():
    # update_item.py imports copy_item at module scope, so the skill directory
    # has to be importable before the spec is executed.
    if str(_SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(_SKILL_DIR))
    spec = importlib.util.spec_from_file_location(
        "update_under_test", _SKILL_DIR / "update_item.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["update_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


update_mod = _load_update()


class TestParseFieldAssignment:
    def test_splits_on_first_equals(self):
        assert update_mod.parse_field_assignment("pages=53-82") == ("pages", "53-82")

    def test_value_may_contain_equals(self):
        # DOIs and URLs carry '=', so only the first one may split.
        assert update_mod.parse_field_assignment(
            "url=https://x.test/a?b=c&d=e"
        ) == ("url", "https://x.test/a?b=c&d=e")

    def test_empty_value_is_legal_and_clears(self):
        assert update_mod.parse_field_assignment("shortTitle=") == ("shortTitle", "")

    def test_missing_equals_raises(self):
        with pytest.raises(ValueError):
            update_mod.parse_field_assignment("pages")

    def test_empty_field_name_raises(self):
        with pytest.raises(ValueError):
            update_mod.parse_field_assignment("=53-82")


class TestParseCreatorName:
    def test_two_field_name(self):
        assert update_mod.parse_creator_name("Boellstorff, Tom") == {
            "firstName": "Tom",
            "lastName": "Boellstorff",
        }

    def test_no_comma_is_a_single_field_name(self):
        assert update_mod.parse_creator_name("World Health Organization") == {
            "name": "World Health Organization"
        }

    def test_surname_only_with_trailing_comma(self):
        assert update_mod.parse_creator_name("Boellstorff,") == {
            "firstName": "",
            "lastName": "Boellstorff",
        }

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            update_mod.parse_creator_name("   ")

    def test_missing_surname_raises(self):
        with pytest.raises(ValueError):
            update_mod.parse_creator_name(", Tom")


class TestParseCreatorSpec:
    def test_type_and_name(self):
        assert update_mod.parse_creator_spec("editor=Nardi, Bonnie") == {
            "creatorType": "editor",
            "firstName": "Bonnie",
            "lastName": "Nardi",
        }

    def test_missing_equals_raises(self):
        with pytest.raises(ValueError):
            update_mod.parse_creator_spec("editor")


class TestBuildUpdatePayload:
    def test_minimal_payload_omits_untouched_channels(self):
        # An absent "creators" key leaves creators alone; an empty list would
        # clear them. The distinction is the whole reason for omission.
        assert update_mod.build_update_payload(
            key="ABCD1234",
            library_id=None,
            item_type=None,
            fields={"pages": "53-82"},
            creators=None,
            apply=False,
        ) == {"key": "ABCD1234", "fields": {"pages": "53-82"}, "apply": False}

    def test_full_payload(self):
        assert update_mod.build_update_payload(
            key="ABCD1234",
            library_id=17,
            item_type="bookSection",
            fields={"pages": "53-82"},
            creators=[{"creatorType": "author", "name": "WHO"}],
            apply=True,
        ) == {
            "key": "ABCD1234",
            "libraryID": 17,
            "itemType": "bookSection",
            "fields": {"pages": "53-82"},
            "creators": [{"creatorType": "author", "name": "WHO"}],
            "apply": True,
        }

    def test_empty_creator_list_is_sent_and_means_remove_all(self):
        payload = update_mod.build_update_payload(
            key="ABCD1234",
            library_id=None,
            item_type=None,
            fields={},
            creators=[],
            apply=False,
        )
        assert payload["creators"] == []

    def test_apply_is_a_real_boolean_not_a_string(self):
        payload = update_mod.build_update_payload(
            key="ABCD1234",
            library_id=None,
            item_type=None,
            fields={"pages": "1"},
            creators=None,
            apply=False,
        )
        assert payload["apply"] is False


class TestParseUpdateResponse:
    def test_200_returns_parsed_body(self):
        body = json.dumps({"ok": True, "key": "ABCD1234", "applied": False})
        assert update_mod.parse_update_response(200, body, "application/json") == {
            "ok": True,
            "key": "ABCD1234",
            "applied": False,
        }

    def test_200_with_non_json_body_raises(self):
        with pytest.raises(update_mod.UpdateError):
            update_mod.parse_update_response(200, "not json", "text/plain")

    def test_structured_error_surfaces_code_and_message(self):
        body = json.dumps(
            {
                "ok": False,
                "code": "invalid_field",
                "message": "'pages' is not a valid field for type 'book'",
            }
        )
        with pytest.raises(update_mod.UpdateError) as e:
            update_mod.parse_update_response(400, body, "application/json")
        assert "invalid_field" in str(e.value)
        assert "not a valid field" in str(e.value)

    def test_plain_text_resolution_failure_surfaced_verbatim(self):
        with pytest.raises(update_mod.UpdateError) as e:
            update_mod.parse_update_response(
                404, "Error: No item with key ZZZ", "text/plain"
            )
        assert "No item with key ZZZ" in str(e.value)


class TestRenderDiff:
    def test_no_changes_says_so(self):
        rendered = update_mod.render_diff(
            {"key": "ABCD1234", "libraryID": 1, "hasChanges": False}
        )
        assert "No change" in rendered

    def test_requested_field_shows_both_sides(self):
        rendered = update_mod.render_diff(
            {
                "key": "ABCD1234",
                "libraryID": 1,
                "hasChanges": True,
                "typeChange": None,
                "collateral": [],
                "requested": [
                    {
                        "kind": "field",
                        "field": "publisher",
                        "from": "Princeton University Press",
                        "to": "MIT Press",
                    }
                ],
            }
        )
        assert "Princeton University Press" in rendered
        assert "MIT Press" in rendered
        assert "->" in rendered

    def test_empty_value_is_labelled_not_blank(self):
        # A blank on either side would read as "unchanged" at a glance.
        rendered = update_mod.render_diff(
            {
                "key": "ABCD1234",
                "libraryID": 1,
                "hasChanges": True,
                "typeChange": None,
                "collateral": [],
                "requested": [
                    {"kind": "field", "field": "pages", "from": "", "to": "53-82"}
                ],
            }
        )
        assert "(empty)" in rendered

    def test_collateral_is_labelled_as_zoteros_doing(self):
        rendered = update_mod.render_diff(
            {
                "key": "ABCD1234",
                "libraryID": 1,
                "hasChanges": True,
                "typeChange": {"kind": "itemType", "from": "book", "to": "bookSection"},
                "collateral": [
                    {
                        "kind": "field",
                        "field": "numPages",
                        "from": "248",
                        "to": "",
                    }
                ],
                "requested": [],
            }
        )
        assert "book" in rendered and "bookSection" in rendered
        assert "Consequences" in rendered
        assert "numPages" in rendered

    def test_creator_change_lists_both_sides_with_signs(self):
        rendered = update_mod.render_diff(
            {
                "key": "ABCD1234",
                "libraryID": 1,
                "hasChanges": True,
                "typeChange": None,
                "collateral": [],
                "requested": [
                    {
                        "kind": "creators",
                        "from": [
                            {
                                "creatorType": "author",
                                "firstName": "Tom",
                                "lastName": "Boellstorff",
                            }
                        ],
                        "to": [
                            {
                                "creatorType": "author",
                                "firstName": "Tom",
                                "lastName": "Boellstorff",
                            },
                            {
                                "creatorType": "author",
                                "firstName": "Bonnie",
                                "lastName": "Nardi",
                            },
                        ],
                    }
                ],
            }
        )
        assert "- Boellstorff, Tom (author)" in rendered
        assert "+ Nardi, Bonnie (author)" in rendered

    def test_single_field_creator_renders_without_a_comma(self):
        rendered = update_mod.render_diff(
            {
                "key": "ABCD1234",
                "libraryID": 1,
                "hasChanges": True,
                "typeChange": None,
                "collateral": [],
                "requested": [
                    {
                        "kind": "creators",
                        "from": [],
                        "to": [
                            {"creatorType": "author", "name": "World Health Organization"}
                        ],
                    }
                ],
            }
        )
        assert "+ World Health Organization (author)" in rendered


class TestClearedFields:
    def test_collects_clears_from_both_sections(self):
        assert update_mod.cleared_fields(
            {
                "collateral": [
                    {"kind": "field", "field": "numPages", "from": "248", "to": ""}
                ],
                "requested": [
                    {"kind": "field", "field": "shortTitle", "from": "EVW", "to": ""}
                ],
            }
        ) == ["numPages", "shortTitle"]

    def test_a_field_being_filled_is_not_a_clear(self):
        assert (
            update_mod.cleared_fields(
                {
                    "collateral": [],
                    "requested": [
                        {"kind": "field", "field": "pages", "from": "", "to": "53-82"}
                    ],
                }
            )
            == []
        )

    def test_a_creator_change_is_not_a_field_clear(self):
        assert (
            update_mod.cleared_fields(
                {"collateral": [], "requested": [{"kind": "creators", "from": [], "to": []}]}
            )
            == []
        )

    def test_missing_sections_are_empty(self):
        assert update_mod.cleared_fields({}) == []
