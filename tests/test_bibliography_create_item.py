"""Tests for using-bibliography/create_item.py (0.19).

Creates one regular item through Zotero 10's stock `POST /items` (design
2026-10-12, L4). Create class: the preview prints the full payload, the
resolved library and collection keys, and the apply command carrying
`--expect-collection KEY --expect-library ID`; apply requires those flags,
re-resolves the names, refuses `target changed`, POSTs, reads the new item
back and verifies the fields, creators and collection. The parser does not
accept `--expect-version` (W2): a new object has no prior version.
"""

from __future__ import annotations

import importlib.util
import json
import re
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
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

import zotero_auth  # noqa: E402
import zotero_local_api as zla  # noqa: E402


def _load():
    spec = importlib.util.spec_from_file_location(
        "create_item_under_test", _SKILL_DIR / "create_item.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["create_item_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load()

LIBRARY = {
    "type": "user",
    "libraryID": 1,
    "name": "My Library",
    "collections": [{"name": "Scratch", "key": "SCRA0001", "parentKey": None}],
}
BASE = "http://localhost:23119/api/users/0"
CREDS = {"Zotero-Server-ID": "g6bzZS56RsjG", "Zotero-API-Key": "k1"}
ARGS = [
    "--type",
    "book",
    "--set",
    "title=A scratch book",
    "--set",
    "date=2026",
    "--author",
    "Scratch, Author",
    "--creator",
    "editor=Editor, Eve",
    "--collection",
    "Scratch",
]


def _created(
    key="NEW00001", *, collections=("SCRA0001",), citekey="scratchScratchBook2026"
):
    data = {
        "key": key,
        "version": 7,
        "itemType": "book",
        "title": "A scratch book",
        "date": "2026",
        "creators": [
            {"creatorType": "author", "firstName": "Author", "lastName": "Scratch"},
            {"creatorType": "editor", "firstName": "Eve", "lastName": "Editor"},
        ],
        "collections": list(collections),
    }
    if citekey:
        data["citationKey"] = citekey
    return {"key": key, "version": 7, "data": data}


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
        self.calls.append({"method": method, "url": url, "json": json})
        queue = self.answers.get((method, url))
        if not queue:
            raise AssertionError(f"unexpected {method} {url}")
        return queue.pop(0)

    def methods(self):
        return [c["method"] for c in self.calls]


def _live(monkeypatch, *, server="g6bzZS56RsjG", libraries=None):
    seam = _Seam()
    monkeypatch.setattr(zla, "_http_request", seam)
    monkeypatch.setattr(zotero_auth, "server_id", lambda **_k: server)
    monkeypatch.setattr(zotero_auth, "credentials", lambda **_k: dict(CREDS))
    monkeypatch.setattr(zotero_auth, "forget_key", lambda _s: None)
    monkeypatch.setattr(helper, "probe_api_plus", lambda: None)
    answers = iter(libraries or [[LIBRARY], [LIBRARY]])
    monkeypatch.setattr(helper, "get_libraries", lambda: next(answers))
    return seam


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["create_item.py", *argv])
    return helper.main()


# --- W2: preview, flags, no invented version ------------------------------------


def test_preview_prints_the_payload_the_keys_and_the_apply_command(monkeypatch, capsys):
    seam = _live(monkeypatch)
    code = _run(monkeypatch, ARGS)
    out = capsys.readouterr().out
    assert code == 0
    assert seam.calls == []
    payload = json.loads(out.split("payload:")[1].split("library:")[0])
    assert payload == {
        "itemType": "book",
        "title": "A scratch book",
        "date": "2026",
        "creators": [
            {"creatorType": "author", "firstName": "Author", "lastName": "Scratch"},
            {"creatorType": "editor", "firstName": "Eve", "lastName": "Editor"},
        ],
        "collections": ["SCRA0001"],
    }
    assert "My Library" in out and "libraryID 1" in out
    assert "SCRA0001" in out
    assert re.search(r"--apply --expect-collection SCRA0001 --expect-library 1\b", out)
    assert "accepted" not in out


def test_parser_rejects_expect_version():
    with pytest.raises(SystemExit) as error:
        helper.build_arg_parser().parse_args([*ARGS, "--expect-version", "1"])
    assert error.value.code == 2


def test_apply_without_the_expected_keys_is_a_usage_error(monkeypatch):
    seam = _live(monkeypatch)
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, [*ARGS, "--apply"])
    assert error.value.code == 2
    with pytest.raises(SystemExit):
        _run(monkeypatch, [*ARGS, "--apply", "--expect-library", "1"])
    assert seam.calls == []


def test_apply_without_a_collection_needs_only_the_library(monkeypatch, capsys):
    seam = _live(monkeypatch)
    created = _created(collections=())
    seam.answer(
        "POST",
        f"{BASE}/items",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer("GET", f"{BASE}/items/NEW00001", _Reply(200, body=created))
    code = _run(
        monkeypatch,
        [*ARGS[:-2], "--apply", "--expect-library", "1"],
    )
    assert code == 0
    assert "collections" not in seam.calls[0]["json"]
    assert capsys.readouterr().out.rstrip().endswith("accepted; verified")


# --- W3 ----------------------------------------------------------------------


def test_refuses_before_any_request_without_a_server_id(monkeypatch, capsys):
    seam = _live(monkeypatch, server=None)
    assert _run(monkeypatch, ARGS) == 1
    assert seam.calls == []
    assert "stock writes need Zotero 10" in capsys.readouterr().err


# --- target changed ----------------------------------------------------------------


def test_apply_refuses_target_changed_and_sends_no_post(monkeypatch, capsys):
    moved = {
        **LIBRARY,
        "collections": [{"name": "Scratch", "key": "SCRA0002", "parentKey": None}],
    }
    seam = _live(monkeypatch, libraries=[[moved]])
    code = _run(
        monkeypatch,
        [*ARGS, "--apply", "--expect-collection", "SCRA0001", "--expect-library", "1"],
    )
    out = capsys.readouterr().out
    assert code == 1
    assert seam.calls == []
    assert "target changed" in out
    assert "SCRA0002" in out
    assert "not accepted" in out


# --- the happy path and R1 ------------------------------------------------------------


def test_apply_posts_reads_back_and_verifies_fields_creators_and_collection(
    monkeypatch, capsys
):
    seam = _live(monkeypatch)
    created = _created()
    seam.answer(
        "POST",
        f"{BASE}/items",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer("GET", f"{BASE}/items/NEW00001", _Reply(200, body=created))

    code = _run(
        monkeypatch,
        [*ARGS, "--apply", "--expect-collection", "SCRA0001", "--expect-library", "1"],
    )

    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods() == ["POST", "GET"]
    assert seam.calls[0]["json"] == [
        {
            "itemType": "book",
            "title": "A scratch book",
            "date": "2026",
            "creators": [
                {"creatorType": "author", "firstName": "Author", "lastName": "Scratch"},
                {"creatorType": "editor", "firstName": "Eve", "lastName": "Editor"},
            ],
            "collections": ["SCRA0001"],
        }
    ]
    assert "key: NEW00001" in out
    assert "citekey: scratchScratchBook2026" in out
    assert out.rstrip().endswith("accepted; verified")


def test_citekey_absence_is_reported_not_a_verification_failure(monkeypatch, capsys):
    seam = _live(monkeypatch)
    created = _created(citekey=None)
    seam.answer(
        "POST",
        f"{BASE}/items",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer("GET", f"{BASE}/items/NEW00001", _Reply(200, body=created))
    code = _run(
        monkeypatch,
        [*ARGS, "--apply", "--expect-collection", "SCRA0001", "--expect-library", "1"],
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "citekey: not yet assigned" in out
    assert out.rstrip().endswith("accepted; verified")


def test_accepted_but_read_back_in_the_wrong_collection_is_not_verified(
    monkeypatch, capsys
):
    seam = _live(monkeypatch)
    created = _created()
    seam.answer(
        "POST",
        f"{BASE}/items",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer(
        "GET", f"{BASE}/items/NEW00001", _Reply(200, body=_created(collections=()))
    )
    code = _run(
        monkeypatch,
        [*ARGS, "--apply", "--expect-collection", "SCRA0001", "--expect-library", "1"],
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "accepted; not verified" in out
    assert "SCRA0001" in out.split("accepted; not verified")[1]


def test_a_failed_entry_in_zoteros_report_is_not_accepted(monkeypatch, capsys):
    seam = _live(monkeypatch)
    seam.answer(
        "POST",
        f"{BASE}/items",
        _Reply(
            200,
            body={
                "successful": {},
                "unchanged": {},
                "failed": {"0": {"code": 400, "message": "'pages' is not valid"}},
            },
        ),
    )
    code = _run(
        monkeypatch,
        [*ARGS, "--apply", "--expect-collection", "SCRA0001", "--expect-library", "1"],
    )
    out = capsys.readouterr().out
    assert code == 1
    assert seam.methods() == ["POST"]
    assert "not accepted" in out and "'pages' is not valid" in out


def test_no_delete_is_ever_sent(monkeypatch):
    seam = _live(monkeypatch)
    created = _created()
    seam.answer(
        "POST",
        f"{BASE}/items",
        _Reply(200, body={"successful": {"0": created}, "unchanged": {}, "failed": {}}),
    )
    seam.answer("GET", f"{BASE}/items/NEW00001", _Reply(200, body=created))
    _run(
        monkeypatch,
        [*ARGS, "--apply", "--expect-collection", "SCRA0001", "--expect-library", "1"],
    )
    assert "DELETE" not in seam.methods()


def test_type_and_a_field_are_required():
    with pytest.raises(SystemExit):
        helper.build_arg_parser().parse_args(["--set", "title=x"])
