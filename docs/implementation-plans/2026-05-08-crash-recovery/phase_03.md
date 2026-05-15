# denubis-crash-recovery Implementation Plan — Phase 3: Liveness file handling, boot awareness, and UUID correlation

**Goal:** Parse `~/.claude/run/<pid>.live` files, read the kernel boot identifier, check whether a PID is still alive, and correlate a liveness record to a candidate session UUID.

**Architecture:** Two modules. `crash_recovery.liveness` exposes the `Liveness` dataclass, `read_liveness()`, `current_boot_id()`, `pid_alive()`, and `list_liveness_files()`. `crash_recovery.correlate` exposes `CorrelationResult` and `correlate()`. UUID resolution prefers argv-resume direct match; falls back to an mtime-window scan over JSONLs in the matching project directory; project directory is resolved by reading the canonical `cwd` from each project's first JSONL entry (NOT by reverse-engineering Claude Code's lossy directory encoding).

**Tech Stack:** Python 3.12+, stdlib only (`os`, `pathlib`, `shlex`, `re`, `json`, `dataclasses`, `enum`, `datetime`).

**Scope:** Phase 3 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-13. `/proc/sys/kernel/random/boot_id` readable on host; `~/.claude/run/` not yet present (Phase 8 wrapper patch creates it on first wrapper startup); project-dir encoding observed to be lossy (`/` and `.` both collapse to `-`).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests the parser/check/correlator side of:

### crash-recovery.AC5: Wrapper liveness lifecycle
- **crash-recovery.AC5.1 Success:** When the patched `claude-wrapper.sh` starts, `~/.claude/run/<wrapper-pid>.live` exists with key=value lines for `cwd`, `started`, `argv`, and `boot_id`

  *Phase 3 covers: parser correctly reads a file with those four keys. Writer side (the wrapper actually writing the file) lands in Phase 8.*

- **crash-recovery.AC5.4 Edge:** Two concurrent wrapper invocations each write distinct liveness files (PID-keyed; no collision); cleaning one does not affect the other

  *Phase 3 covers: `list_liveness_files()` enumerates each `.live` file independently. Writer concurrency lands in Phase 8.*

- **crash-recovery.AC5.6 Success:** A liveness file whose `boot_id` does not match the current `/proc/sys/kernel/random/boot_id` is classified as a casualty by `scan` regardless of whether its PID is alive

  *Phase 3 covers: `current_boot_id()` returns the kernel value and `Liveness.boot_id` exposes the file value so Phase 4's scan can compare. Full classification wiring lands in Phase 4.*

### crash-recovery.AC6: Idle-live-session detection end-to-end
- **crash-recovery.AC6.1 Success:** A liveness file whose PID is no longer in `pgrep` correlates to a session UUID (via argv `--resume <uuid>` or via single-candidate mtime-window match) and is classified `hard_crash`

  *Phase 3 covers: `correlate()` returns `DIRECT_MATCH(uuid)` or `MTIME_MATCH(uuid)`; classification of the correlated session as `hard_crash` is Phase 2's rule + Phase 4's wiring.*

> AC5.2, AC5.3, AC5.5 (exit-status-dependent wrapper behaviour) → Phase 8 bats tests.
> AC6.2, AC6.3, AC6.4 → Phase 4 scan + Phase 8 UAT.

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: `crash_recovery.liveness` — types, parser, primitives

**Verifies:** parser-side of AC5.1, AC5.4, AC5.6 (full verification via Task 2 tests).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/liveness.py`

**Implementation:**

The module exposes:

1. **`Liveness`** — frozen dataclass:

   ```python
   from dataclasses import dataclass
   from pathlib import Path

   @dataclass(frozen=True)
   class Liveness:
       path: Path     # absolute path to the .live file
       pid: int       # extracted from filename: ~/.claude/run/<pid>.live
       cwd: str       # the cwd= line value
       started: int   # the started= line value, parsed as unix epoch (int)
       argv: str      # the argv= line value (string after the = sign, raw)
       boot_id: str   # the boot_id= line value (kernel UUID, lowercase)
   ```

2. **`read_liveness(path: Path) -> Liveness`** — parses a key=value file with four required keys. Implementation contract:
   - Extract `pid` from `path.stem` (the basename without `.live` extension). Raise `ValueError("liveness filename not <pid>.live: {path}")` if `path.stem` is not all-digit.
   - Open the file with UTF-8 encoding, iterate lines, split each on the first `=` (preserving the value verbatim including any `=` signs in argv). Build a dict.
   - Required keys: `cwd`, `started`, `argv`, `boot_id`. Raise `ValueError(f"liveness file missing required key {k}: {path}")` for the first missing key.
   - Ignore any extra unknown keys (forward compat — Phase 8 might add fields later).
   - Coerce `started` to `int`; on `ValueError`, raise a wrapped `ValueError("liveness 'started' is not an int: {path}")`.
   - Coerce `boot_id` to lowercase via `.lower()` (kernel writes lowercase, but defensive normalisation).
   - Return `Liveness(path=path, pid=pid, cwd=cwd, started=started, argv=argv, boot_id=boot_id)`.

3. **`current_boot_id() -> str`** — reads `/proc/sys/kernel/random/boot_id` as text, strips whitespace, returns lowercase string. No caching at module level (the boot_id is a kernel-supplied constant for the process; reading the file is cheap and stays correct across forks).

4. **`pid_alive(pid: int) -> bool`** — wraps `os.kill(pid, 0)`:

   ```python
   import os

   def pid_alive(pid: int) -> bool:
       try:
           os.kill(pid, 0)
       except ProcessLookupError:
           return False
       except PermissionError:
           # Process exists but we lack permission to signal it; counts as alive.
           return True
       return True
   ```

   Any other `OSError` propagates (signals a deeper system problem worth surfacing to the caller).

5. **`list_liveness_files(run_dir: Path) -> Iterator[Liveness]`** — yields parsed `Liveness` records for each `*.live` file in `run_dir`:
   - If `run_dir` does not exist or is not a directory, return immediately (yield nothing). No error — the directory legitimately may not exist before the wrapper has ever run.
   - Iterate `run_dir.glob("*.live")` in lexicographic order (deterministic test ordering).
   - For each, attempt `read_liveness(path)`. On `ValueError`, log a warning (use Python's `warnings.warn` with `UserWarning`) and skip — a malformed file should not abort the whole iteration.

6. **`assert_local_filesystem(path: Path) -> None`** — refuses to operate on network or union filesystems where `rename(2)` atomicity is not guaranteed (NFS write+rename races, FUSE/sshfs latency, overlayfs union semantics). Raises `RuntimeError` with a clear message pointing at the `CRASH_RECOVERY_RUN_DIR` env var as the local-path override.

   ```python
   import shutil
   import subprocess

   _REFUSED_FSTYPES_EXACT = frozenset({
       "nfs", "nfs4", "cifs", "smb3", "smbfs", "sshfs", "davfs",
       "glusterfs", "ceph", "beegfs", "lustre", "afs", "fuse",
   })
   _REFUSED_FSTYPE_PREFIXES = ("fuse.",)  # fuse.<anything> — fuseiso, fuse.gvfsd, etc.

   def _detect_fstype(path: Path) -> str | None:
       """Return the filesystem type for `path` (e.g. 'ext4', 'nfs4', 'tmpfs'),
       or None if it cannot be determined. Uses `findmnt -no FSTYPE -T <path>`
       when available; falls back to parsing /proc/mounts."""
       if shutil.which("findmnt"):
           result = subprocess.run(
               ["findmnt", "-no", "FSTYPE", "-T", str(path)],
               capture_output=True, text=True, check=False,
           )
           if result.returncode == 0:
               return result.stdout.strip() or None
       # Fallback: longest-prefix match against /proc/mounts.
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
           if resolved == mount_point or resolved.startswith(mount_point.rstrip("/") + "/"):
               if len(mount_point) > len(best_mount):
                   best_mount, best_fstype = mount_point, fstype
       return best_fstype

   def assert_local_filesystem(path: Path) -> None:
       fstype = _detect_fstype(path)
       if fstype is None:
           return  # Can't determine — allow; better UX than spurious refusals.
       if fstype in _REFUSED_FSTYPES_EXACT or any(
           fstype.startswith(p) for p in _REFUSED_FSTYPE_PREFIXES
       ):
           raise RuntimeError(
               f"crash-recovery refuses to operate on {path}: filesystem type "
               f"{fstype!r} does not provide reliable atomic-rename semantics "
               f"(network or union filesystem). Liveness files require POSIX "
               f"rename(2) atomicity on a local filesystem. Set CRASH_RECOVERY_RUN_DIR "
               f"to a path on a local filesystem (ext4, btrfs, xfs, zfs, tmpfs)."
           )
   ```

   Phase 4's `scan` CLI subcommand calls `assert_local_filesystem(ctx.run_dir)` immediately after the platform guard, so the error surfaces at the entry point with a useful diagnostic rather than during a half-completed walk.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.liveness import current_boot_id, pid_alive
import os
bid = current_boot_id()
assert len(bid) == 36, bid  # UUID string length
assert pid_alive(os.getpid()) is True
assert pid_alive(2**30) is False
print(f'OK: boot_id={bid}, self alive, sentinel dead')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/liveness.py
git commit -m "feat(crash-recovery): add liveness module with Liveness, read_liveness, pid_alive"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Tests for liveness primitives

**Verifies:** parser-side of AC5.1, AC5.4, AC5.6.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_liveness.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py` — add `make_liveness_file` helper.

**Implementation:**

`make_liveness_file(run_dir: Path, pid: int, cwd: str = "/tmp/test", started: int = 1715151234, argv: str = "", boot_id: str = "8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d") -> Path` — writes a four-key file at `run_dir/<pid>.live`, returns the path.

Tests (all unit):

- **`test_read_liveness_parses_four_keys`** — write a well-formed file with all four keys; `read_liveness(path)` returns a `Liveness` whose fields match the inputs verbatim. (AC5.1)
- **`test_read_liveness_extracts_pid_from_filename`** — write a file with PID `99999`; assert `read_liveness(path).pid == 99999`.
- **`test_read_liveness_rejects_non_numeric_filename`** — write `wibble.live`; assert `ValueError` mentioning the path.
- **`test_read_liveness_missing_key_raises`** — write a file missing `boot_id`; assert `ValueError` mentioning `boot_id`.
- **`test_read_liveness_ignores_extra_keys`** — write a file with an extra `future_key=foo` line; assert parse succeeds.
- **`test_read_liveness_handles_equals_in_argv`** — write `argv=--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b --extra=value=with=signs`; assert `Liveness.argv` preserves the full value.
- **`test_current_boot_id_returns_kernel_value`** — `assert current_boot_id() == Path("/proc/sys/kernel/random/boot_id").read_text().strip().lower()`. (AC5.6 boot-id-read side)
- **`test_current_boot_id_is_lowercase`** — assert the returned string equals its `.lower()`.
- **`test_pid_alive_self_is_true`** — `assert pid_alive(os.getpid()) is True`.
- **`test_pid_alive_sentinel_is_false`** — `assert pid_alive(2**30) is False`.
- **`test_list_liveness_files_tolerates_missing_directory`** — pass a `Path` that doesn't exist; assert `list(list_liveness_files(...))` is empty (no exception).
- **`test_list_liveness_files_enumerates_distinct_pids`** — write 3 `.live` files (PIDs 100, 200, 300); assert iteration yields all three with distinct PIDs. (AC5.4)
- **`test_list_liveness_files_skips_malformed_with_warning`** — write 1 well-formed and 1 malformed (missing key) `.live` file; assert iteration yields only 1 record and `pytest.warns(UserWarning)` fires.

- **`test_assert_local_filesystem_accepts_tmp_path`** — call `assert_local_filesystem(tmp_path)`; assert no exception (tmpfs / ext4 / btrfs / xfs / zfs all acceptable). Smoke test that the happy path is silent.

- **`test_assert_local_filesystem_refuses_simulated_nfs`** — monkey-patch `_detect_fstype` to return `"nfs4"`; assert `assert_local_filesystem(tmp_path)` raises `RuntimeError` whose message contains `CRASH_RECOVERY_RUN_DIR` and the fstype `nfs4`. Parametrise over the refused set: `["nfs", "nfs4", "cifs", "smb3", "sshfs", "fuse.gvfsd", "fuse.sshfs"]`.

- **`test_assert_local_filesystem_silent_when_fstype_undetectable`** — monkey-patch `_detect_fstype` to return `None`; assert no exception. Documents the deliberate choice to allow rather than spuriously refuse.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_liveness.py -q
```

Expected: all tests pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_liveness.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py
git commit -m "test(crash-recovery): cover liveness parser, current_boot_id, pid_alive, list_liveness_files"
```
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (tasks 3-5) -->

<!-- START_TASK_3 -->
### Task 3: `crash_recovery.correlate` — types and `_project_dir_for_cwd` helper

**Verifies:** none directly; foundation for Tasks 4 and 5.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py`

**Implementation:**

```python
"""Correlate a liveness record to candidate session UUIDs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Optional


class CorrelationKind(StrEnum):
    DIRECT_MATCH = "direct_match"
    MTIME_MATCH = "mtime_match"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class CorrelationResult:
    kind: CorrelationKind
    uuid: Optional[str] = None                       # set for DIRECT_MATCH and MTIME_MATCH
    candidates: tuple[str, ...] = field(default_factory=tuple)  # full list for AMBIGUOUS


def _project_dir_for_cwd(projects_root: Path, cwd: str) -> Optional[Path]:
    """Find the ~/.claude/projects/<encoded>/ directory whose JSONLs declare `cwd`.

    Reads the first valid JSON line of any .jsonl file in each child directory and
    matches against the entry's `cwd` field. Returns the matching directory or None.
    """
    if not projects_root.exists() or not projects_root.is_dir():
        return None
    for child in sorted(projects_root.iterdir()):
        if not child.is_dir():
            continue
        for jsonl in child.glob("*.jsonl"):
            try:
                with jsonl.open("r", encoding="utf-8") as f:
                    first = f.readline()
                if not first.strip():
                    continue
                entry = json.loads(first)
            except (OSError, json.JSONDecodeError):
                continue
            entry_cwd = entry.get("cwd")
            if isinstance(entry_cwd, str) and entry_cwd == cwd:
                return child
            # First JSONL in this dir didn't match; remaining JSONLs in the same dir
            # have the same cwd by Claude Code's convention, so break out of inner loop.
            break
    return None
```

The break-out-of-inner-loop optimisation: once we've read one JSONL from a project directory, its `cwd` is authoritative for the whole directory (Claude Code groups all sessions for a given cwd under one encoded directory). No need to keep opening other JSONLs in the same dir.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.correlate import CorrelationKind, CorrelationResult
r = CorrelationResult(kind=CorrelationKind.NO_MATCH)
assert r.kind == 'no_match'  # StrEnum
assert r.uuid is None
assert r.candidates == ()
print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py
git commit -m "feat(crash-recovery): add correlate module with types and project-dir resolver"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: `correlate()` — argv direct match + mtime-window correlation

**Verifies:** correlate side of AC6.1 (direct_match for argv resume; mtime_match for single mtime-window candidate).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py`

**Implementation:**

Add to `correlate.py`:

1. **`_extract_resume_uuid(argv: str) -> Optional[str]`** — parse `argv` for a `--resume <uuid>` pair:

   ```python
   import re
   import shlex

   _UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

   def _extract_resume_uuid(argv: str) -> Optional[str]:
       """Return the UUID following --resume in argv, or None if not present."""
       try:
           tokens = shlex.split(argv)
       except ValueError:
           return None
       for i, token in enumerate(tokens):
           if token == "--resume" and i + 1 < len(tokens):
               candidate = tokens[i + 1]
               if _UUID_RE.match(candidate):
                   return candidate.lower()
       return None
   ```

   Why shlex over regex: handles shell-quoted argv strings; tolerates the `=` signs the design allows in argv (`argv=--resume db0...`). The UUID regex match guards against accidentally accepting a non-UUID token.

2. **`correlate(liveness, projects_root) -> CorrelationResult`**:

   ```python
   from crash_recovery.liveness import Liveness

   def correlate(liveness: Liveness, projects_root: Path) -> CorrelationResult:
       # 1. Argv direct-match.
       resume_uuid = _extract_resume_uuid(liveness.argv)
       project_dir = _project_dir_for_cwd(projects_root, liveness.cwd)
       if resume_uuid is not None and project_dir is not None:
           jsonl_path = project_dir / f"{resume_uuid}.jsonl"
           if jsonl_path.exists():
               return CorrelationResult(kind=CorrelationKind.DIRECT_MATCH, uuid=resume_uuid)
           # argv claimed a UUID but the JSONL is gone — fall through to mtime
           # so we still report something useful.

       if project_dir is None:
           return CorrelationResult(kind=CorrelationKind.NO_MATCH)

       # 2. mtime-window scan over JSONLs in project_dir.
       candidates: list[str] = []
       for jsonl in sorted(project_dir.glob("*.jsonl")):
           try:
               stat = jsonl.stat()
           except OSError:
               continue
           if stat.st_mtime < liveness.started:
               continue
           # Refine: confirm first-entry timestamp is also >= liveness.started.
           if not _jsonl_first_entry_ts_meets_threshold(jsonl, liveness.started):
               continue
           candidates.append(jsonl.stem)

       if not candidates:
           return CorrelationResult(kind=CorrelationKind.NO_MATCH)
       if len(candidates) == 1:
           return CorrelationResult(kind=CorrelationKind.MTIME_MATCH, uuid=candidates[0])
       return CorrelationResult(kind=CorrelationKind.AMBIGUOUS, candidates=tuple(candidates))
   ```

3. **`_jsonl_first_entry_ts_meets_threshold(jsonl: Path, threshold: int) -> bool`** — opens the JSONL, reads the first line, parses it as JSON, extracts `timestamp`, converts to unix epoch, returns whether `entry_ts >= threshold - 60` (60-second grace for clock skew). On any parsing error: return False (be conservative — exclude the candidate).

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.correlate import _extract_resume_uuid
assert _extract_resume_uuid('--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b') == 'db0cc58f-dc30-4195-a64a-4f25a5c19d6b'
assert _extract_resume_uuid('--no-flag-here') is None
assert _extract_resume_uuid('--resume not-a-uuid') is None
print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py
git commit -m "feat(crash-recovery): add correlate() with argv-resume + mtime-window matching"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Tests for correlate

**Verifies:** correlate side of AC6.1; also covers ambiguous-match and no-match paths.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_correlate.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py` — add `make_project_dir(projects_root: Path, cwd: str, uuids: Sequence[str], first_entry_ts: int = ...) -> Path` helper that creates a project directory under `projects_root` (with an arbitrary encoded-dir name) containing N JSONL files, each starting with a single entry that has the supplied `cwd` and `timestamp`.

**Implementation — required tests (all unit; use `tmp_path` as `projects_root` and `run_dir`):**

- **`test_correlate_direct_match_via_argv_resume`** — build a project dir with cwd `/home/user/proj` and one JSONL `db0cc58f-….jsonl`; build a Liveness with `argv="--resume db0cc58f-…"` and `cwd="/home/user/proj"`; assert `correlate(...).kind == DIRECT_MATCH` and `.uuid == "db0cc58f-…"`.
- **`test_correlate_single_mtime_match`** — project dir with cwd `/home/user/proj` and one JSONL whose mtime > liveness.started and whose first-entry timestamp >= liveness.started; argv has no `--resume`; assert `MTIME_MATCH` with the JSONL's UUID.
- **`test_correlate_multiple_mtime_candidates_is_ambiguous`** — project dir with two JSONLs both in the mtime window; assert `AMBIGUOUS` with `len(.candidates) == 2`.
- **`test_correlate_zero_candidates_is_no_match`** — project dir with one JSONL whose mtime is BEFORE liveness.started; assert `NO_MATCH`.
- **`test_correlate_no_project_dir_is_no_match`** — empty `projects_root`; assert `NO_MATCH`.
- **`test_correlate_argv_uuid_but_jsonl_missing_falls_back_to_mtime`** — argv claims `--resume <uuid>` but the corresponding `<uuid>.jsonl` doesn't exist; another JSONL in the dir does match the mtime window; assert `MTIME_MATCH` with the surviving UUID.
- **`test_correlate_filters_out_jsonl_with_old_first_entry`** — JSONL whose filesystem mtime is recent but whose first entry's timestamp is far older than `liveness.started`; assert `NO_MATCH`. Guards against false positives when the same cwd had a long-running session before the wrapper started.
- **`test_project_dir_for_cwd_finds_match_among_multiple_dirs`** — three project dirs each declaring a different cwd; `_project_dir_for_cwd(root, "/home/user/target")` returns the directory whose JSONL `cwd` matches.
- **`test_project_dir_for_cwd_returns_none_for_no_match`** — three project dirs, none matching the requested cwd; helper returns `None`.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_correlate.py -q
```

Expected: all tests pass.

**Step: Confirm Phase 3 done-when criteria**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q
```

Expected: all Phase 1 + Phase 2 + Phase 3 tests pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_correlate.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py
git commit -m "test(crash-recovery): cover correlate for argv-resume, mtime-match, ambiguous, no-match"
```
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 3 Done When

- `crash_recovery.liveness` exposes `Liveness`, `read_liveness`, `current_boot_id`, `pid_alive`, `list_liveness_files`. Parser handles all four design-required keys plus tolerates extras.
- `crash_recovery.correlate` exposes `CorrelationResult` and `correlate()`. Argv-resume direct match wins when both argv UUID and `<uuid>.jsonl` are present; mtime-window fallback returns single match, ambiguous, or no_match.
- All Phase 3 tests pass; repo-root `uv run pytest -q` passes (Phases 1–3 cumulative).

## Outstanding for later phases

- Phase 4's `scan` wires `Liveness` records + `correlate()` + `classify()` + DB upsert into a single transaction.
- Phase 4's `scan` compares `Liveness.boot_id` against `current_boot_id()` and passes `boot_id_current` to `classify()` (AC5.6 end-to-end).
- Phase 8's wrapper patch produces the `.live` files this phase parses (AC5.1, AC5.4, AC5.5 writer side).
