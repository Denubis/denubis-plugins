"""Liveness file parsing and process-liveness primitives.

A liveness file lives at ``~/.claude/run/<pid>.live`` and is written by the
patched ``claude-wrapper.sh`` at wrapper startup. The four required keys
(``cwd``, ``started``, ``argv``, ``boot_id``) capture everything Phase 4's
scan needs to decide whether a still-on-disk JSONL session is live, crashed,
or already concluded.

The module is split between four responsibilities:

* :class:`Liveness` + :func:`read_liveness` — parse the file into a frozen
  dataclass with one PID, one boot_id, one cwd, one argv string. (AC5.1)
* :func:`current_boot_id` — read the kernel-supplied boot id so the scan
  can detect across-reboot casualties (AC5.6 read side).
* :func:`pid_alive` — non-destructive process probe via ``os.kill(pid, 0)``.
  Contract: always returns ``bool``, never ``None``; ``PermissionError`` is
  treated-as-dead (recycled-PID semantics) and any other ``OSError`` is
  logged as a ``UserWarning`` and treated-as-dead. CA2 (2026-05-16) — this
  contract is load-bearing on Phase 2's ``classify()`` boundary check.
* :func:`list_liveness_files` — directory enumeration with malformed-file
  tolerance (skip + warn). (AC5.4)
* :func:`assert_local_filesystem` — refuse network or union filesystems
  where ``rename(2)`` atomicity isn't guaranteed. Phase 4's scan calls this
  at entry so the diagnostic surfaces early rather than mid-walk.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Liveness:
    """One parsed liveness file. Frozen so it can flow through pure code."""

    path: Path
    pid: int
    cwd: str
    started: int
    argv: str
    boot_id: str


# Required keys are listed in canonical order so the "first missing key"
# error message is deterministic across runs (helpful for test pinning).
_REQUIRED_KEYS: tuple[str, ...] = ("cwd", "started", "argv", "boot_id")


def read_liveness(path: Path) -> Liveness:
    """Parse a ``<pid>.live`` file into a :class:`Liveness` record.

    Implementation contract (Phase 3 plan, Task 1):

    * ``path.stem`` must be all-digit. The PID is extracted from the filename
      so the parser cannot be fooled by an in-file ``pid=`` line.
    * Each line is split on the **first** ``=`` so argv values may contain
      further ``=`` signs (e.g. ``--extra=value=with=signs``).
    * All four required keys must be present; the first missing key raises.
    * Unknown keys are tolerated so Phase 8 can add fields without breaking
      forward-compatibility.
    * ``started`` is coerced to ``int`` (a wrapped ``ValueError`` is raised
      on a non-integer value).
    * ``boot_id`` is defensively lowercased — the kernel writes lowercase
      already but normalisation removes a class of subtle bugs.
    """
    stem = path.stem
    if not stem.isdigit():
        raise ValueError(f"liveness filename not <pid>.live: {path}")
    pid = int(stem)

    parsed: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key] = value

    for required in _REQUIRED_KEYS:
        if required not in parsed:
            raise ValueError(
                f"liveness file missing required key {required}: {path}"
            )

    try:
        started = int(parsed["started"])
    except ValueError as exc:
        raise ValueError(f"liveness 'started' is not an int: {path}") from exc

    return Liveness(
        path=path,
        pid=pid,
        cwd=parsed["cwd"],
        started=started,
        argv=parsed["argv"],
        boot_id=parsed["boot_id"].lower(),
    )


def current_boot_id() -> str:
    """Return the kernel boot id, lowercased and whitespace-stripped.

    No caching: the file is a kernel-supplied constant for the lifetime of
    the process, the read is cheap, and the absence of state keeps the
    function trivially testable across forks.
    """
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip().lower()


def pid_alive(pid: int) -> bool:
    """Probe ``pid`` non-destructively via ``os.kill(pid, 0)``.

    Always returns ``bool``; never ``None``; never propagates ``OSError``.

    * ``ProcessLookupError`` → ``False`` (the wrapper is gone).
    * ``PermissionError`` → ``False`` *with* a ``UserWarning``. The PID has
      been recycled to a process this user doesn't own; the wrapper itself
      is gone.
    * Any other ``OSError`` → ``False`` *with* a ``UserWarning``. Treat-as-
      dead is the conservative choice (a crashed wrapper is never pinned
      live forever).

    CA2 (2026-05-16): this single-``bool`` return is load-bearing on Phase 2's
    ``classify()`` boundary check. Returning ``None`` paired with
    ``LivenessState.present=True`` raises ``ValueError`` and crashes the
    scan.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError as exc:
        # PermissionError is an OSError subclass; this branch covers it plus
        # any other platform/system error. All variants warn-and-return-False.
        warnings.warn(
            f"pid_alive({pid}) saw {type(exc).__name__}: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return False
    return True


def list_liveness_files(run_dir: Path) -> Iterator[Liveness]:
    """Yield a :class:`Liveness` for each ``*.live`` file in ``run_dir``.

    * Missing or non-directory ``run_dir`` yields nothing (legitimately the
      case before the wrapper has ever run).
    * Lexicographic glob order so test ordering is deterministic.
    * Malformed files emit a ``UserWarning`` and are skipped — one bad file
      doesn't abort the whole iteration.
    """
    if not run_dir.exists() or not run_dir.is_dir():
        return
    for path in sorted(run_dir.glob("*.live")):
        try:
            yield read_liveness(path)
        except ValueError as exc:
            warnings.warn(
                f"skipping malformed liveness file {path}: {exc}",
                UserWarning,
                stacklevel=2,
            )


# ---------------------------------------------------------------------------
# Local-filesystem guard
# ---------------------------------------------------------------------------

# Refused fstypes (exact match). Network filesystems break rename(2) atomicity
# (NFS write+rename races, SMB/CIFS open-handle semantics, sshfs latency) or
# layer over arbitrary backends (FUSE) that may themselves be remote. The
# liveness lifecycle relies on POSIX atomic-rename semantics for the wrapper's
# temp-file → final-name handoff, so misbehaviour here would manifest as
# either spurious "missing" classifications or torn reads.
#
# Curated 2026-05-16 against the Linux fstype namespace observed in
# /proc/filesystems and the findmnt(8) man page. The set is exhaustive for
# the common-distro shipping defaults at that date; new networked or union
# filesystems should be added here as they appear. Coherence review L4.
_REFUSED_FSTYPES_EXACT: frozenset[str] = frozenset(
    {
        "nfs",
        "nfs4",
        "cifs",
        "smb3",
        "smbfs",
        "sshfs",
        "davfs",
        "glusterfs",
        "ceph",
        "beegfs",
        "lustre",
        "afs",
        "fuse",
    }
)

# Refused fstype prefixes. ``fuse.<anything>`` catches fuse.gvfsd, fuse.sshfs,
# fuseiso, etc. — any FUSE-backed filesystem inherits the same uncertainty.
_REFUSED_FSTYPE_PREFIXES: tuple[str, ...] = ("fuse.",)


def _detect_fstype(path: Path) -> str | None:
    """Return the filesystem type for ``path``, or ``None`` if undetectable.

    Prefers ``findmnt -no FSTYPE -T <path>`` (handles bind mounts and
    overlay correctly). Falls back to longest-prefix matching the resolved
    path against ``/proc/mounts`` when ``findmnt`` is unavailable. Returns
    ``None`` if neither succeeds — the caller treats this as "allow" so
    unknown setups aren't blocked spuriously.
    """
    if shutil.which("findmnt"):
        result = subprocess.run(
            ["findmnt", "-no", "FSTYPE", "-T", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            fstype = result.stdout.strip()
            return fstype or None
    try:
        mounts = Path("/proc/mounts").read_text().splitlines()
    except OSError:
        return None
    resolved = str(path.resolve())
    best_mount, best_fstype = "", None
    for line in mounts:
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point, fstype = parts[1], parts[2]
        if resolved == mount_point or resolved.startswith(
            mount_point.rstrip("/") + "/"
        ):
            if len(mount_point) > len(best_mount):
                best_mount, best_fstype = mount_point, fstype
    return best_fstype


def assert_local_filesystem(path: Path) -> None:
    """Raise ``RuntimeError`` if ``path`` is on a network or union filesystem.

    The message names ``CRASH_RECOVERY_RUN_DIR`` (Phase 4's env-var override)
    so the user has an immediate escape hatch. Undetectable fstype → allow;
    spurious refusals are a worse UX than a rare false-allow on an exotic
    setup.
    """
    fstype = _detect_fstype(path)
    if fstype is None:
        return
    if fstype in _REFUSED_FSTYPES_EXACT or any(
        fstype.startswith(prefix) for prefix in _REFUSED_FSTYPE_PREFIXES
    ):
        raise RuntimeError(
            f"crash-recovery refuses to operate on {path}: filesystem type "
            f"{fstype!r} does not provide reliable atomic-rename semantics "
            f"(network or union filesystem). Liveness files require POSIX "
            f"rename(2) atomicity on a local filesystem. Set "
            f"CRASH_RECOVERY_RUN_DIR to a path on a local filesystem "
            f"(ext4, btrfs, xfs, zfs, tmpfs)."
        )
