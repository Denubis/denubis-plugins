# ADR 0038 — Hooks run under `uv run --script` at the repository Python floor; the 3.9 hook carve-out is retired

**Status:** Accepted (2026-10-24). Retires the hooks carve-out added to `CLAUDE.md` on
2026-06-20 (commit `5a547fb`) and the `py39` per-file ruff target it required.

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 1370, `user` record `f4ed2d4f-fa37-41ee-b76f-ff0ff02f047c` (2026-10-23T23:19:31Z,
  2026-10-24 10:19 Australia/Sydney): "I mean, python 3.15, why the fuck is this 3.9? ir
  3,14 uf we don't want to change pins. Do. Better."
- Line 1432, `user` record `5a36c1e2-c4ac-4878-822e-aa3451d3fb9b` (2026-10-23T23:23:37Z),
  answering "May I lift the hooks carve-out to 'hooks run under `uv run --script` at the
  repo floor, 3.14' and record that as the ruling?": "and this will work on a mac ( just
  thinking about a colleague who is running this) or some failover? But yeah, I'd prefer
  that."

Exact raw-record resolver:

```sh
sed -n '1370p;1432p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

## Context

On 2026-06-20 several hooks died on a colleague's Mac whose `python3` was 3.9, because
the hooks were launched as `uv run python "$script"` (or bare `python3 "$script"`), which
runs whatever interpreter the caller resolves and ignores PEP 723 metadata
(recorded in the module docstring of the former `test_hook_portability` test module). The
fix at the time was to write
hooks down to Python 3.9: `from __future__ import annotations`, one exception per
clause, a `py39` ruff target for `plugins/*/hooks/*.py`, and a canary test importing every
hook under a 3.9 interpreter. The rest of the repository targets 3.14.

That carve-out made hooks a standard-library island that cannot import the plugin's own
packages, which the Claude-supervision work (ADR 0037's shared package, and a planned
hook client for a local supervision service) now needs. The floor was a launcher
artefact, not a language choice.

Checked 2026-10-24 (documented): uv "will automatically download Python versions if they
cannot be found on the system" and "bundles a list of downloadable CPython and PyPy
distributions for macOS, Linux, and Windows"
(https://docs.astral.sh/uv/concepts/python-versions/). Every `python3` on Brian's machine
is 3.14; uv offers 3.15.0 for download but nothing here runs it yet, and the repository
pins `requires-python = ">=3.14"` with ruff at `py314`.

Observed 2026-10-24 (uv 0.13.4, Linux), against the documented "uv run will search for
and use the required Python version": with a `.python-version` of 3.9 in the working
directory, `uv run --script` on a file declaring `requires-python = ">=3.14"` selects
3.14, so an older default interpreter is overridden by the header alone; with an explicit
`UV_PYTHON=3.9`, uv warns that the interpreter is incompatible and runs 3.9 anyway,
exiting 0. Adding `--python '>=3.14'` to the launcher selects 3.14 in both cases. The
launcher therefore carries `--python` with the same floor as the header, both derived
from the repository's `requires-python`, and the hook gate asserts they agree.

## Decision

1. Hooks under `plugins/*/hooks/*.py` are launched as `uv run --script
   "${CLAUDE_PLUGIN_ROOT}/hooks/<name>.py"` and carry a PEP 723 block declaring the
   repository floor, `requires-python = ">=3.14"`. uv resolves or downloads a matching
   interpreter on Linux and macOS. Hooks may then use the same syntax and import the
   same packages as the rest of the repository.
2. The 3.9 carve-out in `CLAUDE.md`, the `py39` entries in
   `[tool.ruff.per-file-target-version]`, and the 3.9 canary test module
   `test_hook_portability` are retired with the hook migration. Their replacement gate,
   `tests/test_hook_uv_script_contract.py`, checks the contract itself: every hook declares
   the floor and every `hooks.json` command launches through `uv run --script`.
3. There is no fallback to a bare `python3`. A machine without `uv` cannot run this
   plugin's skills either, so the dependency is not new. A hook whose launcher is missing
   fails with one clear line on stderr naming the fix; it does not silently degrade to an
   interpreter that reintroduces the 2026-06-20 failure.
4. The floor stays at 3.14 for this work. A move to 3.15 is its own repository-wide
   change (pins, lint target, every PEP 723 header, and the formatter's syntax rewrites),
   not something to land inside a hook or service change.

## Consequences

- The hook gate changes meaning: from "imports on 3.9" (the former `test_hook_portability`
  module) to "declares the floor and is launched through uv"
  (`tests/test_hook_uv_script_contract.py`). The old test is retired, not weakened in place.
- Existing hooks and their `hooks.json` registrations migrate together, in one change,
  with the plugin version bumps the repository contracts require.
- Hook start-up gains uv's resolution cost, tens of milliseconds, accepted.
- The Codex driver's separate Python 3.12 import floor (`tests/test_codex_supervisor_python_floor.py`)
  existed only because its `--hook` relay was launched as `uv run --no-project python
  <file>`, which ignores PEP 723. With the relay registered through this launcher, and the
  permission-queue path-load replaced by a package dependency (ADR 0040), that floor has no
  consumer and retires; the supervision package and both drivers sit at the repository
  floor.
- A hook that talks to a local service (the supervision daemon under design) makes one
  call and exits zero when the service is absent or down, logging once; a down service is
  a visible state, never a wedged session.
