"""A pending approval must be reported as an approval, whatever the pane title says.

`classify_snapshot` decides what the supervisor is told about a Codex pane. It reads
the tmux pane title first and the pane body second, and the title branch for `Ready`
returns before the body is ever examined for approval text. Codex's steady-state
title is `Ready`, so an approval prompt drawn under it is classified `DONE`.

That failure is worse than silence. The supervisor is told Codex has finished at the
moment Codex is blocked waiting for them, and `DONE` is unscoped, so the digest gate
in `advance` then drops every redraw of the same stationary screen. Observed live on
2026-07-27: a pane asking "Please confirm this Task 1 result meets UAT" classified as
`done`, while its supervisor had been waiting on notifications that never came.

The expectations below come from what the tool promises its supervisor — a pane
awaiting a human is reported as awaiting a human — not from the current branch order.
The last case is the guard that keeps the repair honest: a genuinely finished pane
must still read as finished, so widening the approval branch cannot pass by calling
everything an approval.

Extracted from google-live `postgres-schema-53` at commit 7981a6a,
`scripts/codex_watch.py`, blob 64a6dc26, sha256 abc1ad5b…21f1ac.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-external-agents"
    / "scripts"
    / "codex_supervisor.py"
)

# The body Codex draws when it wants permission to run something.
_APPROVAL_BODY = "\n".join(
    [
        "  $ podman run --rm -v /tmp/evidence:/out:Z eald-test pytest -q",
        "",
        "  Would you like to run this command?",
        "  > 1. Yes   2. No, and tell Codex what to do differently",
    ]
)

# Codex's steady-state title. Its window carries branch and quota decoration.
_READY_TITLE = "Ready | postgres-schema-53 | weekly 91% left | gpt-5.6-sol xhigh"


@pytest.fixture(scope="module")
def watch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_supervisor", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so dataclasses resolve __module__ during class creation.
    sys.modules["codex_supervisor"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "title",
    [
        pytest.param(_READY_TITLE, id="ready-title"),
        pytest.param("codex — action required", id="action-required-title"),
        pytest.param("postgres-schema-53", id="neutral-title"),
    ],
)
def test_pending_approval_is_reported_under_any_title(
    watch: ModuleType,
    title: str,
) -> None:
    """The same approval body is an approval regardless of the title above it."""
    observation = watch.classify_snapshot(title, _APPROVAL_BODY)
    assert observation.kind is watch.ObservationKind.APPROVAL, (
        f"pane awaiting approval classified as {observation.kind} under title "
        f"{title!r}; a supervisor reading this is told Codex needs nothing."
    )


def test_finished_pane_still_reads_as_finished(watch: ModuleType) -> None:
    """The repair must not buy approvals by calling every Ready pane an approval."""
    observation = watch.classify_snapshot(_READY_TITLE, "• Finished.")
    assert observation.kind is watch.ObservationKind.DONE
