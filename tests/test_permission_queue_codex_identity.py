"""Verify fresh native-footer associations without any live input or configuration."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments/permission-queue/codex_identity.py"
)
SPEC = importlib.util.spec_from_file_location("permission_codex_identity", PATH)
assert SPEC is not None and SPEC.loader is not None
IDENTITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = IDENTITY
SPEC.loader.exec_module(IDENTITY)

FIRST = "01a13dd3-e299-7e30-9cfa-3ab647121e1f"
SECOND = "01a13924-9506-7913-9553-3041a1d73764"
KEY = ("/socket", 100, 10, "$2", "@4", "%14", 200, 20, 300, 30)


def native_frame(thread=FIRST, *, composer=True, hints=True):
    rows = [""] * 20
    rows[3] = "Conversation text is not a terminal identity."
    rows[-4] = "\x1b[48;2;54;42;30m\u203a \x1b[0m" if composer else ""
    rows[-2] = (
        "  \x1b[38;2;246;226;183m" + thread + "\x1b[0m"
        " · GPT-6.1 Sol xhigh · Context 59% left"
    )
    rows[-1] = "  ← for agents · ? for shortcuts" if hints else "Popup covers footer"
    return "\n".join(rows) + "\n"


def resolve(preview, *, previous=None, key=KEY, loaded=(FIRST, SECOND), height=20):
    return IDENTITY.CodexIdentity.resolve(
        preview, pane_key=key, loaded_threads=loaded, height=height, previous=previous
    )


def test_exact_native_full_uuid_resolves_against_loaded_server_threads():
    preview = native_frame()
    result = resolve(preview)
    assert result.thread_id == FIRST
    assert result.status == "linked"
    assert result.pane_key == KEY


@pytest.mark.parametrize("location", ["conversation", "composer", "title-like-text"])
def test_uuid_merely_in_conversation_or_input_is_not_identity(location):
    rows = native_frame("GPT-6.1 Sol xhigh").splitlines()
    if location == "conversation":
        rows[3] = FIRST
    elif location == "composer":
        rows[-4] = "\u203a " + FIRST
    else:
        rows[3] = "Ready | project | main | " + FIRST
    result = resolve("\n".join(rows) + "\n")
    assert result.thread_id is None
    assert result.status == "setup_required"


@pytest.mark.parametrize("composer,hints", [(False, True), (True, False)])
def test_uuid_in_popup_or_unrecognized_frame_is_not_a_native_footer(composer, hints):
    result = resolve(native_frame(composer=composer, hints=hints))
    assert result.thread_id is None
    assert result.status == "unavailable"


@pytest.mark.parametrize("fragment", [FIRST[:29] + "...", FIRST[:-1], FIRST + "x"])
def test_truncated_or_extended_uuid_never_uses_prefix_lookup(fragment):
    result = resolve(native_frame(fragment))
    assert result.thread_id is None


def test_loaded_thread_membership_is_required_without_auto_selection():
    result = resolve(native_frame(), loaded=(SECOND,))
    assert result.thread_id is None
    assert result.status == "not_loaded"


def test_fresh_thread_switch_replaces_previous_association():
    first = resolve(native_frame())
    assert first.thread_id == FIRST
    second = resolve(native_frame(SECOND), previous=first)
    assert second.thread_id == SECOND
    assert second.changed
    assert not resolve(native_frame(SECOND), previous=second).changed


def test_hidden_footer_clears_previous_binding_instead_of_restoring_cached_id():
    first = resolve(native_frame())
    assert first.thread_id == FIRST
    hidden = resolve(native_frame(hints=False), previous=first)
    assert hidden.thread_id is None
    assert hidden.changed
    assert resolve(native_frame(SECOND), previous=hidden).thread_id == SECOND


def test_process_lifetime_change_invalidates_previous_binding():
    first = resolve(native_frame())
    replacement_key = (*KEY[:-1], 31)
    result = resolve(native_frame(SECOND), key=replacement_key, previous=first)
    assert result.thread_id == SECOND and result.pane_key == replacement_key
    assert result.changed
    unknown = resolve(native_frame(), key=(*KEY[:-1], None), previous=first)
    assert unknown.thread_id is None
    assert unknown.status == "unavailable"


def test_incomplete_viewport_cannot_move_a_conversation_uuid_into_footer_position():
    result = resolve(native_frame(), height=21)
    assert result.thread_id is None
    assert result.status == "unavailable"


def test_resolver_has_no_cross_pane_identity_cache():
    resolver = IDENTITY.CodexIdentity()
    assert (
        resolver.resolve(
            native_frame(), pane_key=KEY, loaded_threads=(FIRST,)
        ).thread_id
        == FIRST
    )
    other = resolver.resolve(
        native_frame(SECOND),
        pane_key=(*KEY[:5], "%15", *KEY[6:]),
        loaded_threads=(SECOND,),
    )
    assert other.thread_id == SECOND
    assert (
        resolver.resolve(
            native_frame(hints=False), pane_key=KEY, loaded_threads=(FIRST,)
        ).thread_id
        is None
    )
