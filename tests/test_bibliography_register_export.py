"""Tests for using-bibliography/register_export.py (0.19, Outcome E).

Registers a Better BibTeX "Keep updated" auto-export for a collection through
`autoexport.add` (design 2026-10-12, Contract 3). Register class: preview
resolves the collection path and prints the apply command with
`--expect-collection KEY`; apply re-resolves, refuses `target changed`, calls
BBT with the NUMERIC absolute collection path `/<libraryID>/<names>` (BBT's
parser matches an all-digit first segment by libraryID; the CLI's "My
Library/..." form never reaches it), and reports three observations
separately: `accepted` (BBT returned the expected key), `completion`
(zotero-api-plus triggered the export and the file's mtime advanced), and
`content` (the file parses and holds a citekey from the collection).
`verified` only when both observations are positive. Time is injected so the
poll is instant.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import sys
import time
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


def _load():
    spec = importlib.util.spec_from_file_location(
        "register_export_under_test", _SKILL_DIR / "register_export.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["register_export_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load()

LIBRARY = {
    "type": "user",
    "libraryID": 1,
    "name": "My Library",
    "collections": [
        {"name": "Sage SRM Guide", "key": "SAGE0001", "parentKey": None},
        {"name": "Readings", "key": "READ0001", "parentKey": "SAGE0001"},
        {"name": "Readings", "key": "READ0002", "parentKey": "OTHER001"},
        {"name": "Other", "key": "OTHER001", "parentKey": None},
    ],
}
GOOD_BIB = (
    "@book{polanyiTacitDimension1966,\n"
    "  author = {Polanyi, Michael},\n"
    "  title = {The tacit dimension},\n"
    "  year = {1966},\n"
    "}\n"
)
LISTING = [
    {
        "key": "PARENT01",
        "data": {
            "key": "PARENT01",
            "itemType": "book",
            "citationKey": "polanyiTacitDimension1966",
        },
    }
]


class _Clock:
    """Starts at real time so a file written by the test is BEFORE the trigger
    unless a case advances its mtime explicitly."""

    def __init__(self, start=None):
        self.t = time.time() if start is None else start
        self.slept: list[float] = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds


def _live(monkeypatch, tmp_path, *, server="g6bzZS56RsjG", library=None):
    monkeypatch.setattr(zotero_auth, "server_id", lambda **_k: server)
    monkeypatch.setattr(helper, "probe_api_plus", lambda: None)
    monkeypatch.setattr(helper, "get_libraries", lambda: [library or LIBRARY])
    monkeypatch.setattr(helper, "get_collection_items", lambda *_a, **_k: LISTING)
    rpc_calls: list[tuple[str, list]] = []
    state = {"rpc_result": {"libraryID": 1, "key": "READ0001", "id": 12}}

    def fake_rpc(method, params, *_a, **_k):
        rpc_calls.append((method, params))
        result = state["rpc_result"]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(helper, "rpc", fake_rpc)
    clock = _Clock()
    monkeypatch.setattr(helper, "now", clock.now)
    monkeypatch.setattr(helper, "sleep", clock.sleep)
    bib = tmp_path / "refs.bib"
    return {"rpc": rpc_calls, "state": state, "clock": clock, "bib": bib}


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["register_export.py", *argv])
    return helper.main()


def _triggered(live, *, advance_mtime=True, body=None):
    """A stub trigger that answers `triggered` and, optionally, makes the file
    look rewritten: same bytes (or `body`), later mtime."""

    def fake_post(path, *_a, **_k):
        if advance_mtime:
            bib = Path(path)
            text = body if body is not None else bib.read_text()
            bib.write_text(text)
            later = live["clock"].now() + 5
            os.utime(bib, (later, later))
        return 200, f'{{"status": "triggered", "path": "{path}"}}'

    return fake_post


# --- pure: the BBT collection path -------------------------------------------


def test_bbt_collection_path_is_numeric_and_absolute():
    assert (
        helper.bbt_collection_path(1, ["Sage SRM Guide", "Readings"])
        == "/1/Sage SRM Guide/Readings"
    )
    assert helper.bbt_collection_path(14, ["Top"]) == "/14/Top"


def test_parse_collection_spec_splits_library_from_the_path():
    assert helper.parse_collection_spec("My Library/Sage SRM Guide/Readings") == (
        "My Library",
        ["Sage SRM Guide", "Readings"],
    )
    with pytest.raises(ValueError):
        helper.parse_collection_spec("Sage SRM Guide")


def test_resolve_collection_path_walks_segments_under_their_parent():
    assert helper.resolve_collection_path(LIBRARY, ["Sage SRM Guide", "Readings"]) == [
        ("Sage SRM Guide", "SAGE0001"),
        ("Readings", "READ0001"),
    ]


def test_resolve_collection_path_errors_on_a_missing_segment():
    with pytest.raises(helper.ResolutionError, match="Missing"):
        helper.resolve_collection_path(LIBRARY, ["Sage SRM Guide", "Missing"])


def test_resolve_collection_path_is_not_fooled_by_a_same_named_sibling_elsewhere():
    # "Readings" exists under two parents; the path picks the one under Sage.
    assert helper.resolve_collection_path(LIBRARY, ["Other", "Readings"]) == [
        ("Other", "OTHER001"),
        ("Readings", "READ0002"),
    ]


# --- gate: preview, flags ---------------------------------------------------------


def test_preview_sends_no_rpc_and_prints_the_apply_command(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text(GOOD_BIB)
    code = _run(
        monkeypatch,
        [
            "--collection",
            "My Library/Sage SRM Guide/Readings",
            "--path",
            str(live["bib"]),
        ],
    )
    out = capsys.readouterr().out
    assert code == 0
    assert live["rpc"] == []
    assert "READ0001" in out
    assert "Better BibLaTeX" in out
    assert str(live["bib"]) in out
    assert "registration state: unknown" in out
    # A standing export no helper can take back must be announced before approval.
    assert re.search(r"removal:\s+manual.*Better BibTeX.*Automatic export", out)
    assert "sha256" in out and hashlib.sha256(GOOD_BIB.encode()).hexdigest()[:16] in out
    assert "--apply --expect-collection READ0001" in out


def test_preview_reports_a_missing_file(monkeypatch, tmp_path, capsys):
    live = _live(monkeypatch, tmp_path)
    code = _run(
        monkeypatch,
        ["--collection", "My Library/Sage SRM Guide", "--path", str(live["bib"])],
    )
    assert code == 0
    assert "no file at that path yet" in capsys.readouterr().out


def test_parser_rejects_expect_version():
    with pytest.raises(SystemExit) as error:
        helper.build_arg_parser().parse_args(
            [
                "--collection",
                "My Library/X",
                "--path",
                "/x.bib",
                "--expect-version",
                "1",
            ]
        )
    assert error.value.code == 2


def test_apply_without_expect_collection_is_a_usage_error(monkeypatch, tmp_path):
    live = _live(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as error:
        _run(
            monkeypatch,
            [
                "--collection",
                "My Library/Sage SRM Guide",
                "--path",
                str(live["bib"]),
                "--apply",
            ],
        )
    assert error.value.code == 2
    assert live["rpc"] == []


def test_refuses_before_any_request_without_a_server_id(monkeypatch, tmp_path, capsys):
    live = _live(monkeypatch, tmp_path, server=None)
    code = _run(
        monkeypatch,
        ["--collection", "My Library/Sage SRM Guide", "--path", str(live["bib"])],
    )
    assert code == 1
    assert live["rpc"] == []
    assert "stock writes need Zotero 10" in capsys.readouterr().err


def test_apply_refuses_target_changed_without_an_rpc(monkeypatch, tmp_path, capsys):
    moved = {
        **LIBRARY,
        "collections": [
            {"name": "Sage SRM Guide", "key": "SAGE0009", "parentKey": None}
        ],
    }
    live = _live(monkeypatch, tmp_path, library=moved)
    code = _run(
        monkeypatch,
        [
            "--collection",
            "My Library/Sage SRM Guide",
            "--path",
            str(live["bib"]),
            "--apply",
            "--expect-collection",
            "SAGE0001",
        ],
    )
    assert code == 1
    assert live["rpc"] == []
    assert "target changed" in capsys.readouterr().out


# --- apply: accepted, completion, content -----------------------------------------


def _apply_args(live):
    return [
        "--collection",
        "My Library/Sage SRM Guide/Readings",
        "--path",
        str(live["bib"]),
        "--apply",
        "--expect-collection",
        "READ0001",
    ]


def test_apply_sends_the_numeric_path_and_verifies_when_both_observations_hold(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text("")
    monkeypatch.setattr(helper, "post_run_autoexport", _triggered(live, body=GOOD_BIB))

    code = _run(monkeypatch, _apply_args(live))

    out = capsys.readouterr().out
    assert code == 0
    assert live["rpc"] == [
        (
            "autoexport.add",
            [
                "/1/Sage SRM Guide/Readings",
                "Better BibLaTeX",
                str(live["bib"]),
                {},
                False,
            ],
        )
    ]
    assert "My Library/" not in str(live["rpc"][0][1][0])
    assert "accepted" in out
    assert out.rstrip().endswith(
        "accepted; completion observed; content satisfied; verified"
    )


def test_replace_and_translator_reach_the_rpc(monkeypatch, tmp_path, capsys):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text(GOOD_BIB)
    monkeypatch.setattr(helper, "post_run_autoexport", _triggered(live))
    code = _run(
        monkeypatch, [*_apply_args(live), "--translator", "Better BibTeX", "--replace"]
    )
    assert code == 0
    assert live["rpc"][0][1][1] == "Better BibTeX"
    assert live["rpc"][0][1][4] is True


def test_another_key_from_bbt_is_not_accepted_and_printed_verbatim(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["state"]["rpc_result"] = {"libraryID": 1, "key": "ZZZZ9999", "id": 99}
    code = _run(monkeypatch, _apply_args(live))
    out = capsys.readouterr().out
    assert code == 1
    assert "not accepted" in out and "ZZZZ9999" in out
    assert "verified" not in out.replace("not verified", "")


def test_a_bbt_error_is_not_accepted_and_printed_verbatim(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["state"]["rpc_result"] = RuntimeError(
        {"code": -32000, "message": "/tmp/refs.bib is already registered for /1/Other"}
    )
    code = _run(monkeypatch, _apply_args(live))
    out = capsys.readouterr().out
    assert code == 1
    assert "not accepted" in out
    assert "already registered for /1/Other" in out


def test_e2a_no_api_plus_is_not_observed_but_content_still_checked(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text(GOOD_BIB)
    monkeypatch.setattr(helper, "post_run_autoexport", lambda *_a, **_k: None)

    code = _run(monkeypatch, _apply_args(live))

    out = capsys.readouterr().out
    assert code == 1
    assert "completion not observed: no zotero-api-plus" in out
    assert "content satisfied" in out
    assert out.rstrip().endswith("not verified")


def test_e2b_identical_bytes_with_a_later_mtime_is_observed(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text(GOOD_BIB)
    before = hashlib.sha256(GOOD_BIB.encode()).hexdigest()[:16]
    monkeypatch.setattr(
        helper, "post_run_autoexport", _triggered(live, advance_mtime=True)
    )

    code = _run(monkeypatch, _apply_args(live))

    out = capsys.readouterr().out
    assert code == 0
    assert "completion observed" in out
    # The hash is shown as an observation, unchanged, and did not decide anything.
    assert out.count(before) >= 2


def test_triggered_without_an_mtime_change_is_not_observed(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text(GOOD_BIB)
    earlier = live["clock"].t - 100
    os.utime(live["bib"], (earlier, earlier))
    monkeypatch.setattr(
        helper, "post_run_autoexport", _triggered(live, advance_mtime=False)
    )

    code = _run(monkeypatch, _apply_args(live))

    out = capsys.readouterr().out
    assert code == 1
    assert "completion not observed: no modification seen within 30 s" in out
    assert "content satisfied" in out
    assert sum(live["clock"].slept) >= 30


def test_trigger_refused_is_not_observed_with_the_kind(monkeypatch, tmp_path, capsys):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text(GOOD_BIB)
    monkeypatch.setattr(
        helper,
        "post_run_autoexport",
        lambda *_a, **_k: (404, '{"status": "no-autoexport", "registeredPaths": []}'),
    )
    code = _run(monkeypatch, _apply_args(live))
    out = capsys.readouterr().out
    assert code == 1
    assert "completion not observed: trigger refused: no-autoexport" in out


def test_content_not_satisfied_when_the_citekey_is_absent(
    monkeypatch, tmp_path, capsys
):
    live = _live(monkeypatch, tmp_path)
    live["bib"].write_text("@book{otherKey2020,\n  title = {Other},\n}\n")
    monkeypatch.setattr(helper, "post_run_autoexport", _triggered(live))
    code = _run(monkeypatch, _apply_args(live))
    out = capsys.readouterr().out
    assert code == 1
    assert "completion observed" in out
    assert "content not satisfied" in out and "polanyiTacitDimension1966" in out
    assert out.rstrip().endswith("not verified")


def test_content_not_satisfied_when_no_file_exists(monkeypatch, tmp_path, capsys):
    live = _live(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "post_run_autoexport", lambda *_a, **_k: None)
    code = _run(monkeypatch, _apply_args(live))
    out = capsys.readouterr().out
    assert code == 1
    assert "content not satisfied: no file" in out
