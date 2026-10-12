"""Tests for using-bibliography/item_collections.py (0.19).

Files an existing item into, or out of, a collection by PATCHing its
`collections` array through the stock local API (design 2026-10-12, L2). The
modify class: preview reads and prints version N, apply requires
`--expect-version N`, re-reads, refuses `changed since preview`, PATCHes with
`If-Unmodified-Since-Version`, reads back and reports `accepted` and
`verified` separately. The HTTP seam and the credentials are stubbed; every
request is recorded so a preview or a refusal can be shown to write nothing.
"""

from __future__ import annotations

import importlib.util
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
        "item_collections_under_test", _SKILL_DIR / "item_collections.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["item_collections_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load()

LIBRARY = {
    "type": "user",
    "libraryID": 1,
    "name": "My Library",
    "collections": [
        {"name": "Sage SRM Guide", "key": "SAGE0001", "parentKey": None},
        {"name": "Archive", "key": "ARCH0001", "parentKey": None},
    ],
}
ITEM_URL = "http://localhost:23119/api/users/0/items/ABCD1234"
CREDS = {"Zotero-Server-ID": "g6bzZS56RsjG", "Zotero-API-Key": "k1"}


def _envelope(version, collections, *, deleted=False):
    return {
        "key": "ABCD1234",
        "version": version,
        "library": {"type": "user", "id": 305867, "name": "My Library"},
        "data": {
            "key": "ABCD1234",
            "version": version,
            "itemType": "book",
            "title": "The tacit dimension",
            "citationKey": "polanyiTacitDimension1966",
            "collections": list(collections),
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
        self.answers: dict[str, list[_Reply]] = {}

    def answer(self, method, reply):
        self.answers.setdefault(method, []).append(reply)

    def __call__(
        self, method, url, *, headers=None, json=None, params=None, timeout=30.0
    ):
        self.calls.append(
            {"method": method, "url": url, "json": json, "headers": dict(headers or {})}
        )
        queue = self.answers.get(method)
        if not queue:
            raise AssertionError(f"unexpected {method} {url}")
        return queue.pop(0)

    def methods(self):
        return [c["method"] for c in self.calls]


def _live(monkeypatch, *, server="g6bzZS56RsjG"):
    seam = _Seam()
    monkeypatch.setattr(zla, "_http_request", seam)
    monkeypatch.setattr(zotero_auth, "server_id", lambda **_k: server)
    monkeypatch.setattr(zotero_auth, "credentials", lambda **_k: dict(CREDS))
    monkeypatch.setattr(zotero_auth, "forget_key", lambda _s: None)
    monkeypatch.setattr(helper, "probe_api_plus", lambda: None)
    monkeypatch.setattr(helper, "get_libraries", lambda: [LIBRARY])
    return seam


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["item_collections.py", *argv])
    return helper.main()


# --- W4: no write without --apply ------------------------------------------


def test_preview_reads_only_and_prints_version_and_apply_command(monkeypatch, capsys):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["ARCH0001"])))

    code = _run(monkeypatch, ["--key", "ABCD1234", "--add", "Sage SRM Guide"])

    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods() == ["GET"]
    assert "The tacit dimension" in out
    assert re.search(r"version:\s+429", out)
    assert "Archive (ARCH0001)" in out
    assert "Sage SRM Guide (SAGE0001)" in out
    assert "--apply --expect-version 429" in out
    assert "accepted" not in out


def test_parser_rejects_expect_version_without_apply_as_preview(monkeypatch, capsys):
    """`--expect-version` alone is still a preview: nothing writes."""
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, [])))
    code = _run(
        monkeypatch,
        ["--key", "ABCD1234", "--add", "Sage SRM Guide", "--expect-version", "429"],
    )
    assert code == 0
    assert seam.methods() == ["GET"]
    assert "--apply" in capsys.readouterr().out


def test_apply_without_expect_version_is_a_usage_error(monkeypatch):
    seam = _live(monkeypatch)
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, ["--key", "ABCD1234", "--add", "Sage SRM Guide", "--apply"])
    assert error.value.code == 2
    assert seam.calls == []


def test_add_and_remove_are_mutually_exclusive_and_one_is_required(monkeypatch):
    _live(monkeypatch)
    with pytest.raises(SystemExit):
        _run(monkeypatch, ["--key", "ABCD1234"])
    with pytest.raises(SystemExit):
        _run(monkeypatch, ["--key", "ABCD1234", "--add", "A", "--remove", "B"])


# --- W3: Zotero 10 only --------------------------------------------------------


def test_refuses_before_any_request_without_a_server_id(monkeypatch, capsys):
    seam = _live(monkeypatch, server=None)
    code = _run(monkeypatch, ["--key", "ABCD1234", "--add", "Sage SRM Guide"])
    assert code == 1
    assert seam.calls == []
    assert "stock writes need Zotero 10" in capsys.readouterr().err


# --- W1: the previewed version protects the write ------------------------------


def test_apply_refuses_when_the_version_moved_and_sends_no_patch(monkeypatch, capsys):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(430, ["ARCH0001"])))

    code = _run(
        monkeypatch,
        [
            "--key",
            "ABCD1234",
            "--add",
            "Sage SRM Guide",
            "--apply",
            "--expect-version",
            "429",
        ],
    )

    out = capsys.readouterr().out
    assert code == 1
    assert seam.methods() == ["GET"]
    assert "changed since preview" in out
    assert "not accepted" in out


def test_apply_conflict_412_is_reported_without_a_success_word(monkeypatch, capsys):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["ARCH0001"])))
    seam.answer("PATCH", _Reply(412, text="Precondition Failed"))
    seam.answer("GET", _Reply(200, body=_envelope(431, ["ARCH0001", "ZZZZ0001"])))

    code = _run(
        monkeypatch,
        [
            "--key",
            "ABCD1234",
            "--add",
            "Sage SRM Guide",
            "--apply",
            "--expect-version",
            "429",
        ],
    )

    out = capsys.readouterr().out
    assert code == 1
    assert seam.methods() == ["GET", "PATCH", "GET"]
    assert "conflict" in out
    assert "431" in out  # Zotero's current object is shown
    assert "accepted" not in out.replace("not accepted", "")


# --- the happy path and R1 -----------------------------------------------------


def test_apply_patches_the_merged_collections_and_verifies_by_read_back(
    monkeypatch, capsys
):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["ARCH0001"])))
    seam.answer("PATCH", _Reply(204, headers={"Last-Modified-Version": "430"}))
    seam.answer("GET", _Reply(200, body=_envelope(430, ["ARCH0001", "SAGE0001"])))

    code = _run(
        monkeypatch,
        [
            "--key",
            "ABCD1234",
            "--add",
            "Sage SRM Guide",
            "--apply",
            "--expect-version",
            "429",
        ],
    )

    out = capsys.readouterr().out
    assert code == 0
    patch = seam.calls[1]
    assert patch["method"] == "PATCH"
    assert patch["url"] == ITEM_URL
    assert patch["json"] == {"collections": ["ARCH0001", "SAGE0001"]}
    assert patch["headers"]["If-Unmodified-Since-Version"] == "429"
    assert patch["headers"]["Zotero-API-Key"] == "k1"
    assert out.rstrip().endswith("accepted; verified")


def test_remove_drops_the_key_and_verifies_its_absence(monkeypatch, capsys):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["ARCH0001", "SAGE0001"])))
    seam.answer("PATCH", _Reply(204, headers={"Last-Modified-Version": "430"}))
    seam.answer("GET", _Reply(200, body=_envelope(430, ["ARCH0001"])))

    code = _run(
        monkeypatch,
        [
            "--key",
            "ABCD1234",
            "--remove",
            "SAGE0001",
            "--apply",
            "--expect-version",
            "429",
        ],
    )

    assert code == 0
    assert seam.calls[1]["json"] == {"collections": ["ARCH0001"]}
    assert capsys.readouterr().out.rstrip().endswith("accepted; verified")


def test_accepted_but_read_back_unchanged_is_not_verified(monkeypatch, capsys):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["ARCH0001"])))
    seam.answer("PATCH", _Reply(204, headers={"Last-Modified-Version": "430"}))
    seam.answer("GET", _Reply(200, body=_envelope(430, ["ARCH0001"])))  # no SAGE0001

    code = _run(
        monkeypatch,
        [
            "--key",
            "ABCD1234",
            "--add",
            "Sage SRM Guide",
            "--apply",
            "--expect-version",
            "429",
        ],
    )

    out = capsys.readouterr().out
    assert code == 1
    assert "accepted; not verified" in out
    assert "SAGE0001" in out.split("accepted; not verified")[1]


def test_no_delete_is_ever_sent(monkeypatch):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["ARCH0001"])))
    seam.answer("PATCH", _Reply(204, headers={"Last-Modified-Version": "430"}))
    seam.answer("GET", _Reply(200, body=_envelope(430, ["ARCH0001", "SAGE0001"])))
    _run(
        monkeypatch,
        [
            "--key",
            "ABCD1234",
            "--add",
            "Sage SRM Guide",
            "--apply",
            "--expect-version",
            "429",
        ],
    )
    assert "DELETE" not in seam.methods()


def test_add_of_an_already_present_collection_is_reported_as_no_change(
    monkeypatch, capsys
):
    seam = _live(monkeypatch)
    seam.answer("GET", _Reply(200, body=_envelope(429, ["SAGE0001"])))
    code = _run(monkeypatch, ["--key", "ABCD1234", "--add", "Sage SRM Guide"])
    out = capsys.readouterr().out
    assert code == 0
    assert "already" in out
    assert "--apply" not in out
