"""Repo-wide hook-portability fitness function.

Incident (2026-06-20): several Python hooks had acquired Python-3.14-only
syntax and died on a colleague's stock-3.9 Mac before any logic ran. Hooks are
invoked `uv run python "$script"` from the user's working directory, so they
inherit whatever interpreter that machine resolves, which may be far older than
3.14. `uv run python <file>` also ignores PEP 723 metadata, so a requires-python
floor cannot rescue them. The repo CLAUDE.md carves hooks out of the "3.14-only
syntax is intentional" doctrine and requires them to run on Python >= 3.9.

This test lifts that rule from reviewer-eye to an automated check (Ford et al.,
Building Evolutionary Architectures). It imports every `plugins/*/hooks/*.py`
under an interpreter below both relevant thresholds and fails if any hook will
not load there.

Why import rather than compile: the two failure modes have different triggers.
The parenthesis-less `except` (PEP 758) is a `SyntaxError` caught at compile.
The runtime-evaluated `X | Y` annotation (PEP 604) is a `TypeError` raised only
when the `def` executes, which `py_compile` never reaches. Executing the module
body via import is the faithful reproduction of the incident and catches both.

Why 3.9 as the floor: it sits below both thresholds, the 3.10 line where PEP 604
unions gained runtime support and the 3.14 line where PEP 758 syntax parses. An
interpreter at 3.10-3.13 would accept the union annotation and silently miss
half the failure class, so a higher canary would be a weaker guard.

Limitation: import catches every newer *syntax* anywhere in the file (the whole
file is compiled) and every failure on the import-time code path. A newer
*runtime* API (a 3.11+ stdlib import, say) buried inside a function that import
never calls would slip. The hooks are small and top-level, so this is an
accepted gap rather than a silent one.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

# tests/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PLUGINS_DIR = _REPO_ROOT / "plugins"

# The canary interpreter. Must stay below 3.10 (PEP 604 runtime) and 3.14
# (PEP 758 syntax) for the teeth test below to hold. See module docstring.
PORTABILITY_FLOOR = "3.9"

# First run may provision the floor interpreter via uv; later runs hit the cache.
_TIMEOUT_S = 180

# Imports the target file by path, executing its module body. Exit non-zero with
# a traceback on stderr if loading raises (SyntaxError, TypeError, anything).
_IMPORT_SHIM = (
    "import importlib.util, sys\n"
    "spec = importlib.util.spec_from_file_location('hook_under_test', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "sys.modules[spec.name] = mod\n"
    "spec.loader.exec_module(mod)\n"
)


def _hook_paths() -> list[Path]:
    """Every Python hook under `plugins/*/hooks/`, excluding caches."""
    return sorted(
        p
        for p in _PLUGINS_DIR.glob("*/hooks/*.py")
        if "__pycache__" not in p.parts
    )


def _hook_id(path: Path) -> str:
    """Readable test id: '<plugin>/<file>'."""
    return f"{path.parts[-3]}/{path.name}"


def _uv() -> str | None:
    return shutil.which("uv")


def _imports_under_floor(path: Path) -> tuple[bool, str]:
    """Import `path` under the floor interpreter. Return (ok, detail).

    Uses `--no-project` so uv resolves only the requested interpreter and does
    not drag in the workspace environment.
    """
    proc = subprocess.run(
        [
            _uv(),
            "run",
            "--python",
            PORTABILITY_FLOOR,
            "--no-project",
            "python",
            "-c",
            _IMPORT_SHIM,
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        check=False,
    )
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _require_uv() -> None:
    if _uv() is None:
        pytest.skip("uv unavailable; see test_uv_available_for_portability_checks")


def test_uv_available_for_portability_checks() -> None:
    """Fail loud, not silent, if uv is missing.

    The per-hook checks skip without uv to avoid duplicate noise. This single
    test fails so the guard can never quietly vanish from a misconfigured run.
    """
    assert _uv() is not None, (
        "uv is required to run the hook-portability checks (it provisions the "
        f"Python {PORTABILITY_FLOOR} canary). Install uv: https://docs.astral.sh/uv/"
    )


def test_at_least_one_hook_discovered() -> None:
    """Sanity: the glob finds hooks. Catches a silent layout regression."""
    assert _hook_paths(), f"no hooks found under {_PLUGINS_DIR}/*/hooks/*.py"


@pytest.mark.parametrize(
    ("label", "source", "should_load"),
    [
        # Positive control: portable union annotation loads under the floor.
        (
            "future-guarded-union",
            "from __future__ import annotations\n"
            "def f(x: int | None) -> str | None:\n"
            "    return None\n",
            True,
        ),
        # PEP 604 union evaluated at runtime: TypeError on < 3.10 (Amanda's error).
        (
            "runtime-union-annotation",
            "def f(x: int | None) -> str | None:\n    return None\n",
            False,
        ),
        # PEP 758 parenthesis-less except: SyntaxError on < 3.14.
        (
            "parenless-except",
            "try:\n    pass\nexcept ValueError, TypeError:\n    pass\n",
            False,
        ),
    ],
)
def test_floor_interpreter_has_teeth(
    tmp_path: Path, label: str, source: str, should_load: bool
) -> None:
    """The canary genuinely rejects 3.14-only patterns and accepts portable ones.

    Without this, a misconfigured floor (e.g. uv silently handing back 3.14)
    would make every per-hook check a green no-op. The two negative cases pin
    that the provisioned interpreter is old enough to catch both failure modes.
    """
    _require_uv()
    bad_file = tmp_path / f"{label}.py"
    bad_file.write_text(source, encoding="utf-8")
    ok, detail = _imports_under_floor(bad_file)
    if should_load:
        assert ok, f"portable snippet '{label}' should load under {PORTABILITY_FLOOR}: {detail}"
    else:
        assert not ok, (
            f"snippet '{label}' loaded under {PORTABILITY_FLOOR}, so the canary is "
            f"not actually below the 3.10/3.14 thresholds; the guard has no teeth"
        )


@pytest.mark.parametrize("hook_path", _hook_paths(), ids=_hook_id)
def test_hook_imports_on_floor(hook_path: Path) -> None:
    """Every Python hook must import on Python >= 3.9 (the carved-out floor).

    A hook that gains 3.14-only syntax (parenthesis-less except, runtime union
    annotation without `from __future__ import annotations`, match/case, etc.)
    fails here instead of in a colleague's terminal.
    """
    _require_uv()
    ok, detail = _imports_under_floor(hook_path)
    assert ok, (
        f"{_hook_id(hook_path)} does not import on Python {PORTABILITY_FLOOR}.\n"
        f"Hooks run under the user's interpreter via `uv run python`, which may "
        f"predate 3.14. Add `from __future__ import annotations` and use portable "
        f"excepts (collapse to a base class, or split into single clauses; never a "
        f"bare tuple). Interpreter output:\n{detail}"
    )
