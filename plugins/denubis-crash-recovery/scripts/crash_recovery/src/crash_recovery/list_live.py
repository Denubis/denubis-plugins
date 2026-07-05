"""Diagnostic survey of currently-running Claude wrappers.

The ``crash-recovery list-live`` subcommand reads the per-PID liveness files
under ``run_dir`` (Phase 3) and reduces them to the subset whose wrapper
process is still alive. The result carries each row's ``boot_id_current``
flag so the user can immediately distinguish "this wrapper is running on
the current boot" from "this PID exists but came up under a different boot
id" (the latter being a recycled PID — the original wrapper is gone, the
new occupant is unrelated).

The module is intentionally side-effect-free: it composes
:func:`crash_recovery.liveness.list_liveness_files`,
:func:`crash_recovery.liveness.pid_alive`, and
:func:`crash_recovery.liveness.current_boot_id` into a single read-only
sweep. No DB access, no filesystem mutation, no logging beyond the
``UserWarning`` that ``list_liveness_files`` may itself emit on malformed
files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from crash_recovery.liveness import current_boot_id, list_liveness_files, pid_alive

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class LiveEntry:
    """One liveness row whose process is alive at survey time.

    Frozen so callers can flow it through pure rendering code without
    worrying about mutation. The ``boot_id_current`` flag is the only
    field not lifted verbatim from the on-disk liveness file — it is
    computed by comparing the file's ``boot_id`` to
    :func:`crash_recovery.liveness.current_boot_id` at survey time.
    """

    pid: int
    cwd: str
    started: int
    argv: str
    boot_id_current: bool


def survey_live(run_dir: Path) -> tuple[LiveEntry, ...]:
    """Return liveness records whose PID is alive AND mark boot-id currency.

    Iterates every ``*.live`` file under ``run_dir`` via
    :func:`crash_recovery.liveness.list_liveness_files`, drops any record
    whose PID is no longer alive (per
    :func:`crash_recovery.liveness.pid_alive`), and projects the survivors
    into :class:`LiveEntry` with ``boot_id_current`` computed against the
    live kernel boot id.

    Missing ``run_dir`` yields an empty tuple — the legitimate pre-wrapper
    state before any liveness file has ever been written. Malformed files
    are skipped with a ``UserWarning`` upstream in ``list_liveness_files``.
    """
    current_bid = current_boot_id()
    entries: list[LiveEntry] = []
    for live in list_liveness_files(run_dir):
        if not pid_alive(live.pid):
            continue
        entries.append(
            LiveEntry(
                pid=live.pid,
                cwd=live.cwd,
                started=live.started,
                argv=live.argv,
                boot_id_current=(live.boot_id == current_bid),
            )
        )
    return tuple(entries)
