"""Tests for using-bibliography/write_gate.py (0.19, Contracts 2 and 3).

One gate shape for every write helper: no flag means preview, `--apply` means
write, and apply refuses when the previewed state is no longer what was
approved. The expected-state flags differ by operation class (design
2026-10-12): modify carries `--expect-version`; create carries
`--expect-collection`, `--expect-parent`, `--expect-library`; register carries
`--expect-collection`. The final line separates `accepted` from `verified`.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "write_gate.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("write_gate_under_test", _MODULE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["write_gate_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


gate = _load()


def _parser(cls):
    parser = argparse.ArgumentParser(prog="helper.py", exit_on_error=False)
    gate.add_gate_arguments(parser, cls)
    return parser


# --- flag sets per class -------------------------------------------------------


def test_modify_class_has_expect_version_and_nothing_else():
    args = _parser("modify").parse_args(["--apply", "--expect-version", "429"])
    assert args.apply is True
    assert args.expect_version == 429
    with pytest.raises(argparse.ArgumentError):
        _parser("modify").parse_args(["--expect-collection", "X"])


def test_create_class_has_collection_parent_and_library_but_no_version():
    args = _parser("create").parse_args(
        ["--apply", "--expect-collection", "COLL0001", "--expect-library", "1"]
    )
    assert args.expect_collection == "COLL0001"
    assert args.expect_library == "1"
    assert args.expect_parent is None
    with pytest.raises(argparse.ArgumentError):
        _parser("create").parse_args(["--expect-version", "1"])


def test_register_class_has_only_expect_collection():
    args = _parser("register").parse_args(["--expect-collection", "COLL0001"])
    assert args.expect_collection == "COLL0001"
    for rejected in (["--expect-version", "1"], ["--expect-parent", "X"]):
        with pytest.raises(argparse.ArgumentError):
            _parser("register").parse_args(rejected)


def test_preview_is_the_default():
    args = _parser("modify").parse_args([])
    assert args.apply is False
    assert args.expect_version is None


# --- missing expectations -------------------------------------------------------


def test_missing_expectations_only_when_applying():
    args = _parser("modify").parse_args(["--apply"])
    assert gate.missing_expectations(args, ["--expect-version"]) == ["--expect-version"]
    args = _parser("modify").parse_args([])
    assert gate.missing_expectations(args, ["--expect-version"]) == []


def test_missing_expectations_lists_every_absent_required_flag():
    args = _parser("create").parse_args(["--apply", "--expect-library", "1"])
    assert gate.missing_expectations(
        args, ["--expect-collection", "--expect-parent", "--expect-library"]
    ) == ["--expect-collection", "--expect-parent"]


# --- refusals -------------------------------------------------------------------


def test_state_refusal_changed_since_preview():
    assert gate.state_refusal({"version": 429}, {"version": 430}) == (
        "changed since preview: version is 430, expected 429"
    )


def test_state_refusal_target_changed():
    assert gate.state_refusal(
        {"collection": "COLL0001", "library": "1"},
        {"collection": "COLL0002", "library": "1"},
    ) == ("target changed: collection is COLL0002, expected COLL0001")


def test_state_refusal_none_when_unchanged():
    assert gate.state_refusal({"version": 429}, {"version": 429}) is None
    assert gate.state_refusal({"version": 429}, {"version": "429"}) is None


# --- apply command -----------------------------------------------------------


def test_format_apply_command_repeats_the_invocation_with_the_flags():
    argv = ["/plug/skills/using-bibliography/trash_item.py", "--key", "ABCD1234"]
    assert gate.format_apply_command(argv, {"version": 429}) == (
        "uv run /plug/skills/using-bibliography/trash_item.py --key ABCD1234 "
        "--apply --expect-version 429"
    )


def test_format_apply_command_quotes_and_drops_stale_gate_flags():
    argv = [
        "create_item.py",
        "--set",
        "title=A title, with comma",
        "--apply",
        "--expect-collection",
        "OLD00001",
    ]
    assert gate.format_apply_command(
        argv, {"collection": "COLL0001", "library": "1"}
    ) == (
        "uv run create_item.py --set 'title=A title, with comma' --apply "
        "--expect-collection COLL0001 --expect-library 1"
    )


# --- report -----------------------------------------------------------------


def test_report_accepted_and_verified_exits_0():
    assert gate.report(accepted=True, verified=True) == ("accepted; verified", 0)


def test_report_accepted_but_not_verified_exits_1_with_the_reason():
    assert gate.report(
        accepted=True, verified=False, reason="read-back still lists COLL0001"
    ) == ("accepted; not verified: read-back still lists COLL0001", 1)


def test_report_not_accepted_exits_1_with_the_reason():
    assert gate.report(accepted=False, verified=None, reason="conflict (412)") == (
        "not accepted: conflict (412)",
        1,
    )


def test_report_never_prints_a_bare_success():
    for accepted, verified in ((True, None), (False, True)):
        line, code = gate.report(accepted=accepted, verified=verified, reason="x")
        assert code == 1
        assert line != "accepted; verified"
