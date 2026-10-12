"""Tests for using-bibliography/collection.py (0.19).

`--list` is the read-only collection listing with trashed rows marked (design
2026-10-12, L1). Name resolution goes through copy_item's resolvers over the
zotero-api-plus `/libraries` response (ruling: "api-plus"); the listing itself
is the stock local API through zotero_local_api.get_collection_items. The HTTP
shell is stubbed; the live listing is UAT.
"""

from __future__ import annotations

import importlib.util
import re
import shlex
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


def _load():
    if str(_SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(_SKILL_DIR))
    spec = importlib.util.spec_from_file_location(
        "collection_under_test", _SKILL_DIR / "collection.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["collection_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


collection = _load()

LIBRARY = {
    "type": "user",
    "libraryID": 1,
    "name": "My Library",
    "collections": [
        {"name": "Sage SRM Guide", "key": "SAGE0001", "parentKey": None},
        {"name": "Readings", "key": "READ0001", "parentKey": "SAGE0001"},
        {"name": "Readings", "key": "READ0002", "parentKey": "OTHER001"},
    ],
}


def _listing():
    return [
        {
            "key": "PARENT01",
            "data": {
                "key": "PARENT01",
                "itemType": "book",
                "title": "Technology and the character of contemporary life",
                "citationKey": "borgmann1984",
            },
        },
        {
            "key": "ATTACH01",
            "data": {
                "key": "ATTACH01",
                "itemType": "attachment",
                "parentItem": "PARENT01",
                "filename": "Borgmann - 1984.pdf",
            },
        },
        {
            "key": "PARENT02",
            "data": {
                "key": "PARENT02",
                "itemType": "journalArticle",
                "title": "Trashed paper",
                "citationKey": "trashed2020",
                "deleted": True,
            },
        },
    ]


def _stub_live(monkeypatch, listing):
    monkeypatch.setattr(collection, "probe_api_plus", lambda: None)
    monkeypatch.setattr(collection, "get_libraries", lambda: [LIBRARY])
    seen = {}

    def fake_listing(lib, key, *, include_trashed=True):
        seen["args"] = (lib, key, include_trashed)
        return listing

    monkeypatch.setattr(collection, "get_collection_items", fake_listing)
    return seen


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["collection.py", *argv])
    return collection.main()


# --- resolution --------------------------------------------------------------


def test_resolve_target_by_name():
    assert collection.resolve_collection(LIBRARY, "Sage SRM Guide") == "SAGE0001"


def test_resolve_target_accepts_a_bare_key_directly():
    assert collection.resolve_collection(LIBRARY, "SAGE0001") == "SAGE0001"
    # A key is accepted as given even if no name matches it.
    assert collection.resolve_collection(LIBRARY, "ZZZZ9999") == "ZZZZ9999"


def test_ambiguous_name_errors_with_candidate_keys_and_parents():
    with pytest.raises(collection.ResolutionError) as error:
        collection.resolve_collection(LIBRARY, "Readings")
    message = str(error.value)
    assert "READ0001" in message and "READ0002" in message
    assert "SAGE0001" in message and "OTHER001" in message


def test_unknown_name_errors():
    with pytest.raises(collection.ResolutionError):
        collection.resolve_collection(LIBRARY, "No Such Collection")


# --- row rendering -----------------------------------------------------------


def test_render_rows_marks_trash_and_counts_attachments():
    rows = collection.summarise_collection(_listing())
    text = collection.render_rows(rows)
    lines = text.splitlines()
    assert lines[0].split() == [
        "PARENT01",
        "borgmann1984",
        "Technology",
        "and",
        "the",
        "character",
        "of",
        "contemporary",
        "life",
        "attachments:",
        "1",
        "(Borgmann",
        "-",
        "1984.pdf)",
    ]
    assert (
        "PARENT02  trashed2020  Trashed paper  [in trash]  attachments: 0" in lines[1]
    )
    assert lines[-1] == "2 items (1 in trash)"


# --- main --------------------------------------------------------------------


def test_list_resolves_the_name_and_lists_with_trash(monkeypatch, capsys):
    seen = _stub_live(monkeypatch, _listing())
    assert _run(monkeypatch, ["--list", "Sage SRM Guide"]) == 0
    out = capsys.readouterr().out
    assert seen["args"] == (LIBRARY, "SAGE0001", True)
    assert "Sage SRM Guide (SAGE0001) in My Library" in out
    assert "[in trash]" in out
    assert "2 items (1 in trash)" in out


def test_list_ambiguous_name_exits_2_without_listing(monkeypatch, capsys):
    seen = _stub_live(monkeypatch, _listing())
    assert _run(monkeypatch, ["--list", "Readings"]) == 2
    assert "args" not in seen
    assert "ambiguous" in capsys.readouterr().err


def test_list_requires_api_plus_for_name_resolution(monkeypatch, capsys):
    def refuse():
        raise SystemExit("zotero-api-plus not reachable")

    monkeypatch.setattr(collection, "probe_api_plus", refuse)
    monkeypatch.setattr(
        collection, "get_libraries", lambda: pytest.fail("must not be reached")
    )
    with pytest.raises(SystemExit):
        _run(monkeypatch, ["--list", "Sage SRM Guide"])


def test_parser_requires_a_verb(monkeypatch):
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, [])
    assert error.value.code == 2


def test_parser_rejects_two_verbs(monkeypatch):
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, ["--list", "A", "--trash", "SAGE0001"])
    assert error.value.code == 2


# --- write verbs (0.19, Outcome D) --------------------------------------------
#
# --create (create class), --rename / --trash / --restore (modify class) through
# the stock write primitive. The installed local API lists sub-collections and
# counts `numCollections` WITHOUT trashed children (server_localAPI.js:993-995,
# collection.js:776, read 2026-10-12), and only a direct key read returns a
# trashed collection; so the trash step prints the descendants and `--restore`
# takes them back as `--descendants`. The stub below answers the
# sub-collection route with live children only, as the installed API does.

import zotero_auth  # noqa: E402
import zotero_local_api as zla  # noqa: E402

BASE = "http://localhost:23119/api/users/0"
CREDS = {"Zotero-Server-ID": "g6bzZS56RsjG", "Zotero-API-Key": "k1"}


def _coll(key, name, *, parent=False, version=10, deleted=False, items=0):
    return {
        "key": key,
        "version": version,
        "meta": {"numCollections": 0, "numItems": items},
        "data": {
            "key": key,
            "version": version,
            "name": name,
            "parentCollection": parent,
            "deleted": deleted,
        },
    }


class _Reply:
    def __init__(self, status, *, headers=None, text="", body=None):
        self.status_code = status
        self.headers = headers or {}
        self.text = text
        self._body = body

    def json(self):
        return self._body


class _Seam:
    def __init__(self):
        self.calls: list[dict] = []
        self.answers: dict[tuple[str, str], list[_Reply]] = {}

    def answer(self, method, url, reply):
        self.answers.setdefault((method, url), []).append(reply)

    def __call__(
        self, method, url, *, headers=None, json=None, params=None, timeout=30.0
    ):
        self.calls.append(
            {"method": method, "url": url, "json": json, "headers": dict(headers or {})}
        )
        queue = self.answers.get((method, url))
        if not queue:
            raise AssertionError(f"unexpected {method} {url}")
        return queue.pop(0)

    def methods(self):
        return [c["method"] for c in self.calls]


def _write_live(monkeypatch, *, server="g6bzZS56RsjG", library=None):
    seam = _Seam()
    monkeypatch.setattr(zla, "_http_request", seam)
    monkeypatch.setattr(zotero_auth, "server_id", lambda **_k: server)
    monkeypatch.setattr(zotero_auth, "credentials", lambda **_k: dict(CREDS))
    monkeypatch.setattr(zotero_auth, "forget_key", lambda _s: None)
    monkeypatch.setattr(collection, "probe_api_plus", lambda: None)
    monkeypatch.setattr(collection, "get_libraries", lambda: [library or LIBRARY])
    return seam


def _accepted(version):
    return _Reply(204, headers={"Last-Modified-Version": str(version)})


# --- flag sets (W2) -------------------------------------------------------------------


def test_create_rejects_expect_version(monkeypatch):
    _write_live(monkeypatch)
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, ["--create", "New", "--apply", "--expect-version", "1"])
    assert error.value.code == 2


def test_modify_verbs_reject_create_flags(monkeypatch):
    _write_live(monkeypatch)
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, ["--trash", "SAGE0001", "--apply", "--expect-library", "1"])
    assert error.value.code == 2


def test_write_verbs_refuse_before_any_request_without_a_server_id(monkeypatch, capsys):
    seam = _write_live(monkeypatch, server=None)
    assert _run(monkeypatch, ["--trash", "SAGE0001"]) == 1
    assert seam.calls == []
    assert "stock writes need Zotero 10" in capsys.readouterr().err


# --- create ---------------------------------------------------------------------------


def test_create_preview_prints_body_library_and_apply_command(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    code = _run(
        monkeypatch, ["--create", "Readings 2026", "--parent", "Sage SRM Guide"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert seam.calls == []
    assert '"name": "Readings 2026"' in out
    assert '"parentCollection": "SAGE0001"' in out
    assert "libraryID 1" in out
    assert re.search(r"--apply --expect-parent SAGE0001 --expect-library 1\b", out)


def test_create_apply_requires_parent_only_when_named(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    with pytest.raises(SystemExit):
        _run(monkeypatch, ["--create", "Top", "--apply"])
    with pytest.raises(SystemExit):
        _run(
            monkeypatch,
            [
                "--create",
                "Child",
                "--parent",
                "SAGE0001",
                "--apply",
                "--expect-library",
                "1",
            ],
        )
    assert seam.calls == []
    created = _coll("NEWC0001", "Top", version=12)
    seam.answer(
        "POST",
        f"{BASE}/collections",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer("GET", f"{BASE}/collections/NEWC0001", _Reply(200, body=created))
    assert (
        _run(monkeypatch, ["--create", "Top", "--apply", "--expect-library", "1"]) == 0
    )
    assert seam.calls[0]["json"] == [{"name": "Top", "parentCollection": False}]
    assert capsys.readouterr().out.rstrip().endswith("accepted; verified")


def test_create_apply_refuses_target_changed_without_a_post(monkeypatch, capsys):
    moved = {
        **LIBRARY,
        "collections": [
            {"name": "Sage SRM Guide", "key": "SAGE0009", "parentKey": None}
        ],
    }
    seam = _write_live(monkeypatch, library=moved)
    code = _run(
        monkeypatch,
        [
            "--create",
            "Child",
            "--parent",
            "Sage SRM Guide",
            "--apply",
            "--expect-parent",
            "SAGE0001",
            "--expect-library",
            "1",
        ],
    )
    assert code == 1
    assert seam.calls == []
    assert "target changed" in capsys.readouterr().out


def test_create_apply_verifies_name_and_parent_by_read_back(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    created = _coll("NEWC0001", "Child", parent="SAGE0001", version=12)
    seam.answer(
        "POST",
        f"{BASE}/collections",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer("GET", f"{BASE}/collections/NEWC0001", _Reply(200, body=created))
    code = _run(
        monkeypatch,
        [
            "--create",
            "Child",
            "--parent",
            "SAGE0001",
            "--apply",
            "--expect-parent",
            "SAGE0001",
            "--expect-library",
            "1",
        ],
    )
    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods() == ["POST", "GET"]
    assert "key: NEWC0001" in out
    assert out.rstrip().endswith("accepted; verified")


# --- rename --------------------------------------------------------------------------


def test_rename_preview_reads_and_apply_patches_the_name(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=10)),
    )
    code = _run(monkeypatch, ["--rename", "SAGE0001", "Sage SRM Guide 2026"])
    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods() == ["GET"]
    assert "Sage SRM Guide 2026" in out
    assert "--apply --expect-version 10" in out

    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=10)),
    )
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(11))
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide 2026", version=11)),
    )
    code = _run(
        monkeypatch,
        [
            "--rename",
            "SAGE0001",
            "Sage SRM Guide 2026",
            "--apply",
            "--expect-version",
            "10",
        ],
    )
    assert code == 0
    patch = seam.calls[2]
    assert patch["method"] == "PATCH"
    assert patch["json"] == {"name": "Sage SRM Guide 2026"}
    assert patch["headers"]["If-Unmodified-Since-Version"] == "10"
    assert capsys.readouterr().out.rstrip().endswith("accepted; verified")


# --- trash ----------------------------------------------------------------------------


def _tree(seam, *, version=10):
    """Parent SAGE0001 with child READ0001 and grandchild DEEP0001, all live."""
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=version, items=3)),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001/collections",
        _Reply(200, body=[_coll("READ0001", "Readings", parent="SAGE0001")]),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/READ0001/collections",
        _Reply(200, body=[_coll("DEEP0001", "Deep", parent="READ0001")]),
    )
    seam.answer("GET", f"{BASE}/collections/DEEP0001/collections", _Reply(200, body=[]))


def test_trash_preview_lists_descendants_and_item_count_without_writing(
    monkeypatch, capsys
):
    seam = _write_live(monkeypatch)
    _tree(seam)
    code = _run(monkeypatch, ["--trash", "SAGE0001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "PATCH" not in seam.methods() and "DELETE" not in seam.methods()
    assert "READ0001" in out and "DEEP0001" in out
    assert re.search(r"items:\s+3\b", out)
    assert "--apply --expect-version 10" in out


def test_trash_apply_verifies_each_descendant_and_prints_the_restore_command(
    monkeypatch, capsys
):
    seam = _write_live(monkeypatch)
    _tree(seam)
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(11))
    for key, name, parent in (
        ("SAGE0001", "Sage SRM Guide", False),
        ("READ0001", "Readings", "SAGE0001"),
        ("DEEP0001", "Deep", "READ0001"),
    ):
        seam.answer(
            "GET",
            f"{BASE}/collections/{key}",
            _Reply(200, body=_coll(key, name, parent=parent, version=11, deleted=True)),
        )

    code = _run(
        monkeypatch, ["--trash", "SAGE0001", "--apply", "--expect-version", "10"]
    )

    out = capsys.readouterr().out
    assert code == 0
    patch = next(c for c in seam.calls if c["method"] == "PATCH")
    assert patch["url"] == f"{BASE}/collections/SAGE0001"
    assert patch["json"] == {"deleted": True}
    assert "DELETE" not in seam.methods()
    assert "--restore SAGE0001 --descendants READ0001,DEEP0001" in out
    assert out.rstrip().endswith("accepted; verified")


def test_trash_apply_restore_command_round_trips_through_the_parser(
    monkeypatch, capsys
):
    """A library name with a space must survive copy-paste of the restore line."""
    seam = _write_live(monkeypatch)
    _tree(seam)
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(11))
    for key, name, parent in (
        ("SAGE0001", "Sage SRM Guide", False),
        ("READ0001", "Readings", "SAGE0001"),
        ("DEEP0001", "Deep", "READ0001"),
    ):
        seam.answer(
            "GET",
            f"{BASE}/collections/{key}",
            _Reply(200, body=_coll(key, name, parent=parent, version=11, deleted=True)),
        )

    code = _run(
        monkeypatch,
        [
            "--trash",
            "SAGE0001",
            "--library",
            "My Library",
            "--apply",
            "--expect-version",
            "10",
        ],
    )

    out = capsys.readouterr().out
    assert code == 0
    restore_line = next(line for line in out.splitlines() if "--restore" in line)
    argv = shlex.split(restore_line.strip().removeprefix("uv run "))
    args = collection.build_arg_parser().parse_args(argv[1:])
    assert args.restore == "SAGE0001"
    assert args.descendants == "READ0001,DEEP0001"
    assert args.library == "My Library"


def test_trash_apply_with_a_descendant_still_live_is_not_verified(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    _tree(seam)
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(11))
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=11, deleted=True)),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/READ0001",
        _Reply(
            200, body=_coll("READ0001", "Readings", parent="SAGE0001", deleted=False)
        ),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/DEEP0001",
        _Reply(200, body=_coll("DEEP0001", "Deep", parent="READ0001", deleted=True)),
    )
    code = _run(
        monkeypatch, ["--trash", "SAGE0001", "--apply", "--expect-version", "10"]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "accepted; not verified" in out
    assert "READ0001" in out.split("accepted; not verified")[1]


def test_trash_apply_refuses_when_the_version_moved(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    _tree(seam, version=12)
    code = _run(
        monkeypatch, ["--trash", "SAGE0001", "--apply", "--expect-version", "10"]
    )
    assert code == 1
    assert "PATCH" not in seam.methods()
    assert "changed since preview" in capsys.readouterr().out


# --- restore --------------------------------------------------------------------------


def test_restore_with_descendants_patches_parent_then_each_in_depth_order(
    monkeypatch, capsys
):
    seam = _write_live(monkeypatch)
    # Preview-time reads: the parent and each listed descendant, by key.
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(
            200,
            body=_coll("SAGE0001", "Sage SRM Guide", version=11, deleted=True, items=3),
        ),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/DEEP0001",
        _Reply(
            200,
            body=_coll("DEEP0001", "Deep", parent="READ0001", version=11, deleted=True),
        ),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/READ0001",
        _Reply(
            200,
            body=_coll(
                "READ0001", "Readings", parent="SAGE0001", version=11, deleted=True
            ),
        ),
    )
    # Writes, parent first, then shallowest to deepest.
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(12))
    seam.answer("PATCH", f"{BASE}/collections/READ0001", _accepted(12))
    seam.answer("PATCH", f"{BASE}/collections/DEEP0001", _accepted(12))
    # Read-backs.
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=12, items=3)),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/READ0001",
        _Reply(200, body=_coll("READ0001", "Readings", parent="SAGE0001", version=12)),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/DEEP0001",
        _Reply(200, body=_coll("DEEP0001", "Deep", parent="READ0001", version=12)),
    )

    code = _run(
        monkeypatch,
        [
            "--restore",
            "SAGE0001",
            "--descendants",
            "DEEP0001,READ0001",  # deliberately deepest first on the command line
            "--apply",
            "--expect-version",
            "11",
        ],
    )

    out = capsys.readouterr().out
    assert code == 0
    patches = [c for c in seam.calls if c["method"] == "PATCH"]
    assert [p["url"].rsplit("/", 1)[1] for p in patches] == [
        "SAGE0001",
        "READ0001",
        "DEEP0001",
    ]
    assert all(p["json"] == {"deleted": False} for p in patches)
    assert [p["headers"]["If-Unmodified-Since-Version"] for p in patches] == [
        "11",
        "11",
        "11",
    ]
    assert "DELETE" not in seam.methods()
    assert re.search(r"items:\s+3\b", out)
    assert out.rstrip().endswith("accepted; verified")


def test_restore_without_descendants_patches_the_parent_only_and_says_unknown(
    monkeypatch, capsys
):
    seam = _write_live(monkeypatch)
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=11, deleted=True)),
    )
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(12))
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=12)),
    )

    code = _run(
        monkeypatch, ["--restore", "SAGE0001", "--apply", "--expect-version", "11"]
    )

    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods().count("PATCH") == 1
    assert (
        "descendants unknown: Zotero's collection listings exclude the trash; pass "
        "--descendants from the trash output or restore them in Zotero"
    ) in out
    assert out.rstrip().endswith("accepted; verified")


def test_the_subcollection_listing_cannot_reveal_trashed_descendants(
    monkeypatch, capsys
):
    """The installed API lists live children only, so a restore that tried to
    discover trashed descendants through the listing would find none. The
    helper must not claim to have restored what it could not see."""
    seam = _write_live(monkeypatch)
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=11, deleted=True)),
    )
    seam.answer("GET", f"{BASE}/collections/SAGE0001/collections", _Reply(200, body=[]))
    seam.answer("PATCH", f"{BASE}/collections/SAGE0001", _accepted(12))
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=12)),
    )
    _run(monkeypatch, ["--restore", "SAGE0001", "--apply", "--expect-version", "11"])
    out = capsys.readouterr().out
    assert "READ0001" not in out
    assert "descendants unknown" in out


def test_restore_preview_reads_each_listed_descendant(monkeypatch, capsys):
    seam = _write_live(monkeypatch)
    seam.answer(
        "GET",
        f"{BASE}/collections/SAGE0001",
        _Reply(200, body=_coll("SAGE0001", "Sage SRM Guide", version=11, deleted=True)),
    )
    seam.answer(
        "GET",
        f"{BASE}/collections/READ0001",
        _Reply(
            200,
            body=_coll(
                "READ0001", "Readings", parent="SAGE0001", version=11, deleted=True
            ),
        ),
    )
    code = _run(monkeypatch, ["--restore", "SAGE0001", "--descendants", "READ0001"])
    out = capsys.readouterr().out
    assert code == 0
    assert "PATCH" not in seam.methods()
    assert "READ0001" in out and "Readings" in out
    assert (
        "--restore SAGE0001 --descendants READ0001 --apply --expect-version 11" in out
    )
