"""Tests for using-bibliography/trash_item.py (0.19).

Trashes or restores one item or attachment by PATCHing `deleted` through the
stock local API; never `DELETE` (ADR 0028). Modify class: preview reads only
and prints version N with what the trash will take with it; apply requires
`--expect-version N`, re-reads, refuses `changed since preview`, PATCHes with
`If-Unmodified-Since-Version`, reads back with the trash included and reports
`accepted` and `verified` separately.
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
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

import zotero_auth  # noqa: E402
import zotero_local_api as zla  # noqa: E402


def _load():
    spec = importlib.util.spec_from_file_location(
        "trash_item_under_test", _SKILL_DIR / "trash_item.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["trash_item_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load()

LIBRARY = {"type": "user", "libraryID": 1, "name": "My Library", "collections": []}
BASE = "http://localhost:23119/api/users/0"
CREDS = {"Zotero-Server-ID": "g6bzZS56RsjG", "Zotero-API-Key": "k1"}


def _attachment(version, *, deleted=False):
    return {
        "key": "ATTACH01",
        "version": version,
        "data": {
            "key": "ATTACH01",
            "version": version,
            "itemType": "attachment",
            "parentItem": "PARENT01",
            "title": "Full Text PDF",
            "filename": "Borgmann - 1987.pdf",
            "relations": {"owl:sameAs": "http://zotero.org/groups/1/items/OTHER001"},
            "deleted": deleted,
        },
    }


def _parent(version, *, deleted=False):
    return {
        "key": "PARENT01",
        "version": version,
        "data": {
            "key": "PARENT01",
            "version": version,
            "itemType": "book",
            "title": "Technology and the character of contemporary life",
            "citationKey": "borgmann1984",
            "relations": {},
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
            {
                "method": method,
                "url": url,
                "json": json,
                "headers": dict(headers or {}),
                "params": dict(params or {}),
            }
        )
        queue = self.answers.get((method, url))
        if not queue:
            raise AssertionError(f"unexpected {method} {url}")
        return queue.pop(0)

    def methods(self):
        return [c["method"] for c in self.calls]


def _live(monkeypatch, tmp_path, *, server="g6bzZS56RsjG"):
    seam = _Seam()
    monkeypatch.setattr(zla, "_http_request", seam)
    monkeypatch.setattr(zotero_auth, "server_id", lambda **_k: server)
    monkeypatch.setattr(zotero_auth, "credentials", lambda **_k: dict(CREDS))
    monkeypatch.setattr(zotero_auth, "forget_key", lambda _s: None)
    monkeypatch.setattr(helper, "probe_api_plus", lambda: None)
    monkeypatch.setattr(helper, "get_libraries", lambda: [LIBRARY])
    storage = tmp_path / "storage"
    (storage / "ATTACH01").mkdir(parents=True)
    (storage / "ATTACH01" / "Borgmann - 1987.pdf").write_bytes(b"%PDF" * 100)
    monkeypatch.setattr(helper, "STORAGE_ROOT", storage)
    return seam


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["trash_item.py", *argv])
    return helper.main()


# --- preview (W4, W1) ----------------------------------------------------------


def test_preview_of_an_attachment_reads_only_and_shows_what_moves(
    monkeypatch, tmp_path, capsys
):
    seam = _live(monkeypatch, tmp_path)
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(12)))
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer("GET", f"{BASE}/items/ATTACH01/children", _Reply(200, body=[]))

    code = _run(monkeypatch, ["--key", "ATTACH01"])

    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods() == ["GET", "GET", "GET"]
    assert "attachment" in out
    assert "Full Text PDF" in out
    assert re.search(r"parent:\s+PARENT01", out)
    assert "Technology and the character of contemporary life" in out
    assert "Borgmann - 1987.pdf" in out
    assert "400 bytes" in out
    assert "owl:sameAs" in out and "OTHER001" in out
    assert re.search(r"children:\s+0", out)
    assert re.search(r"deleted:\s+false", out)
    assert re.search(r"version:\s+12", out)
    assert "--apply --expect-version 12" in out
    assert "accepted" not in out


def test_preview_of_a_parent_counts_its_children(monkeypatch, tmp_path, capsys):
    seam = _live(monkeypatch, tmp_path)
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer(
        "GET",
        f"{BASE}/items/PARENT01/children",
        _Reply(200, body=[_attachment(12), {"key": "NOTE0001", "data": {}}]),
    )
    code = _run(monkeypatch, ["--key", "PARENT01"])
    out = capsys.readouterr().out
    assert code == 0
    assert re.search(r"children:\s+2", out)
    assert "follow it into the trash" in out


def test_apply_without_expect_version_is_a_usage_error(monkeypatch, tmp_path):
    seam = _live(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, ["--key", "ATTACH01", "--apply"])
    assert error.value.code == 2
    assert seam.calls == []


# --- W3 ----------------------------------------------------------------------


def test_refuses_before_any_request_without_a_server_id(monkeypatch, tmp_path, capsys):
    seam = _live(monkeypatch, tmp_path, server=None)
    assert _run(monkeypatch, ["--key", "ATTACH01"]) == 1
    assert seam.calls == []
    assert "stock writes need Zotero 10" in capsys.readouterr().err


# --- W1 refusals ------------------------------------------------------------------


def test_apply_refuses_when_the_version_moved(monkeypatch, tmp_path, capsys):
    seam = _live(monkeypatch, tmp_path)
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(13)))
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))

    code = _run(monkeypatch, ["--key", "ATTACH01", "--apply", "--expect-version", "12"])

    assert code == 1
    assert seam.methods() == ["GET", "GET"]
    assert "changed since preview" in capsys.readouterr().out


def test_apply_conflict_is_reported_with_the_current_object(
    monkeypatch, tmp_path, capsys
):
    seam = _live(monkeypatch, tmp_path)
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(12)))
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer("PATCH", f"{BASE}/items/ATTACH01", _Reply(412, text="Precondition"))
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(14)))

    code = _run(monkeypatch, ["--key", "ATTACH01", "--apply", "--expect-version", "12"])

    out = capsys.readouterr().out
    assert code == 1
    assert seam.methods() == ["GET", "GET", "PATCH", "GET"]
    assert "conflict" in out and "14" in out
    assert "accepted" not in out.replace("not accepted", "")


# --- trash, restore, R1 -------------------------------------------------------------


def test_apply_trashes_only_that_key_and_verifies_with_the_trash_included(
    monkeypatch, tmp_path, capsys
):
    seam = _live(monkeypatch, tmp_path)
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(12)))
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer(
        "PATCH",
        f"{BASE}/items/ATTACH01",
        _Reply(204, headers={"Last-Modified-Version": "13"}),
    )
    seam.answer(
        "GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(13, deleted=True))
    )

    code = _run(monkeypatch, ["--key", "ATTACH01", "--apply", "--expect-version", "12"])

    out = capsys.readouterr().out
    assert code == 0
    assert seam.methods() == ["GET", "GET", "PATCH", "GET"]
    patch = seam.calls[2]
    assert patch["url"] == f"{BASE}/items/ATTACH01"
    assert patch["json"] == {"deleted": True}
    assert patch["headers"]["If-Unmodified-Since-Version"] == "12"
    read_back = seam.calls[3]
    assert read_back["params"].get("includeTrashed") == 1
    assert out.rstrip().endswith("accepted; verified")
    assert "DELETE" not in seam.methods()


def test_restore_patches_deleted_false_and_verifies(monkeypatch, tmp_path, capsys):
    seam = _live(monkeypatch, tmp_path)
    seam.answer(
        "GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(13, deleted=True))
    )
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer(
        "PATCH",
        f"{BASE}/items/ATTACH01",
        _Reply(204, headers={"Last-Modified-Version": "14"}),
    )
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(14)))
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))

    code = _run(
        monkeypatch,
        ["--key", "ATTACH01", "--restore", "--apply", "--expect-version", "13"],
    )

    assert code == 0
    patch = next(c for c in seam.calls if c["method"] == "PATCH")
    assert patch["json"] == {"deleted": False}
    assert capsys.readouterr().out.rstrip().endswith("accepted; verified")


def _attachment_under_trashed_parent(seam, *, own_deleted):
    seam.answer(
        "GET",
        f"{BASE}/items/ATTACH01",
        _Reply(200, body=_attachment(12, deleted=own_deleted)),
    )
    seam.answer(
        "GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40, deleted=True))
    )
    seam.answer("GET", f"{BASE}/items/ATTACH01/children", _Reply(200, body=[]))


def _restore_command_for_parent(out):
    line = next(line for line in out.splitlines() if "--key PARENT01" in line)
    return line.strip().removeprefix("uv run ")


def test_restore_preview_under_a_trashed_parent_names_the_parent_restore(
    monkeypatch, tmp_path, capsys
):
    """Zotero's isInTrash() includes the parent; the helper must say so."""
    seam = _live(monkeypatch, tmp_path)
    _attachment_under_trashed_parent(seam, own_deleted=False)

    code = _run(monkeypatch, ["--key", "ATTACH01", "--restore"])

    out = capsys.readouterr().out
    assert code == 1
    assert "PATCH" not in seam.methods()
    assert re.search(r"deleted:\s+false \(in the trash through parent PARENT01\)", out)
    assert "--apply --expect-version" not in out
    assert "trash_item.py --key PARENT01 --restore" in _restore_command_for_parent(out)
    assert out.rstrip().endswith("not accepted: in the trash through parent PARENT01")


def test_restore_apply_under_a_trashed_parent_writes_nothing(
    monkeypatch, tmp_path, capsys
):
    """Clearing the attachment's own flag would leave it in the trash."""
    seam = _live(monkeypatch, tmp_path)
    _attachment_under_trashed_parent(seam, own_deleted=True)

    code = _run(
        monkeypatch,
        ["--key", "ATTACH01", "--restore", "--apply", "--expect-version", "12"],
    )

    out = capsys.readouterr().out
    assert code == 1
    assert "PATCH" not in seam.methods()
    assert re.search(r"deleted:\s+true \(parent PARENT01 is in the trash too\)", out)
    assert "trash_item.py --key PARENT01 --restore" in _restore_command_for_parent(out)
    assert "accepted; verified" not in out
    assert out.rstrip().endswith("not accepted: in the trash through parent PARENT01")


def test_parent_restore_command_keeps_the_helper_path_when_run_from_elsewhere(
    monkeypatch, tmp_path, capsys
):
    """Run from the repository root, the printed command must still find the helper."""
    seam = _live(monkeypatch, tmp_path)
    _attachment_under_trashed_parent(seam, own_deleted=False)
    helper_path = str(_SKILL_DIR / "trash_item.py")
    monkeypatch.setattr(sys, "argv", [helper_path, "--key", "ATTACH01", "--restore"])

    code = helper.main()

    out = capsys.readouterr().out
    assert code == 1
    command = _restore_command_for_parent(out)
    assert shlex.split(command)[0] == helper_path
    assert shlex.split(command)[1:] == ["--key", "PARENT01", "--restore"]


def test_trash_preview_under_a_trashed_parent_is_already_in_the_trash(
    monkeypatch, tmp_path, capsys
):
    seam = _live(monkeypatch, tmp_path)
    _attachment_under_trashed_parent(seam, own_deleted=False)

    code = _run(monkeypatch, ["--key", "ATTACH01"])

    out = capsys.readouterr().out
    assert code == 0
    assert "PATCH" not in seam.methods()
    assert "already in the trash through its parent PARENT01" in out
    assert "--apply" not in out


def test_accepted_but_still_live_on_read_back_is_not_verified(
    monkeypatch, tmp_path, capsys
):
    seam = _live(monkeypatch, tmp_path)
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(12)))
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer(
        "PATCH",
        f"{BASE}/items/ATTACH01",
        _Reply(204, headers={"Last-Modified-Version": "13"}),
    )
    seam.answer("GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(13)))

    code = _run(monkeypatch, ["--key", "ATTACH01", "--apply", "--expect-version", "12"])

    out = capsys.readouterr().out
    assert code == 1
    assert "accepted; not verified" in out
    assert "deleted" in out.split("accepted; not verified")[1]


def test_trashing_an_item_already_in_the_trash_is_reported_as_no_change(
    monkeypatch, tmp_path, capsys
):
    seam = _live(monkeypatch, tmp_path)
    seam.answer(
        "GET", f"{BASE}/items/ATTACH01", _Reply(200, body=_attachment(13, deleted=True))
    )
    seam.answer("GET", f"{BASE}/items/PARENT01", _Reply(200, body=_parent(40)))
    seam.answer("GET", f"{BASE}/items/ATTACH01/children", _Reply(200, body=[]))
    code = _run(monkeypatch, ["--key", "ATTACH01"])
    out = capsys.readouterr().out
    assert code == 0
    assert "already in the trash" in out
    assert "--apply" not in out
