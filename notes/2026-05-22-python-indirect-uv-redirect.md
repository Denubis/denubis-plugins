# python_indirect uv-redirect deny — added to approver (2026-05-22)

## Trigger

In `/home/brian/people/Brian/nicegui-bug-repro/` a separate Claude session proposed:

```
.venv/bin/pre-commit install 2>&1 | tail -3; echo ---RUN---; .venv/bin/pre-commit run --all-files 2>&1 | tail -100
```

This hit the normal Claude Code permission prompt — no approver rule had an opinion. User: "I thought we had an autodeny for this sort of bullshit." Goal: "stop trying 15 ways to run ruff and bandit and all the other bullshit and should simply always us uv run." In a uv project, direct `.venv/bin/*`, `python -m X`, and bare `pre-commit` should all be denied with a baked-in deny message that tells the calling Claude to retry as `uv run X`.

## What was done

Added a new rule module that denies three patterns and a dispatcher tweak that threads `cwd` through to the classifier so the rule can gate on "am I in a uv project".

**Files changed (all in `~/.claude/hooks/approver/`, single machine — not in git, not on claude-sync):**

- `rules/python_indirect.py` (new) — three classifiers:
  - `classify_venv_bin(argv, cwd)` — path-based. Matches `.venv/bin/<tool>`, `./.venv/bin/<tool>`, `venv/bin/<tool>`, `./venv/bin/<tool>`, or any absolute path containing `/.venv/bin/` or `/venv/bin/`. Called directly from `pipeline._classify_component` BEFORE basename lookup (the basename `pre-commit` / `ruff` wouldn't carry the venv-path signal otherwise).
  - `classify_python(argv, cwd)` — registry-keyed on `python` / `python3`. Denies only `-m <module> ...` invocations; no opinion on bare `python`, `python -V`, `python script.py`, `python -c '...'`. Suggests `uv run <module> <args>` as primary and `uv run -m <module> <args>` as backstop (some `-m` invocations target modules that aren't console-scripts).
  - `classify_pre_commit(argv, cwd)` — registry-keyed on `pre-commit`. Denies the bare invocation entirely; suggests `uv run pre-commit <args>`. Pattern is a thin `_deny_bare_tool` wrapper — adding `ruff`, `bandit`, `mypy`, etc. is one line each.
- `pipeline.py` — three changes:
  - `_classify_component(argv, registry, cwd=None)` — added `cwd` param. Calls `classify_venv_bin` as a path-based short-circuit before basename lookup.
  - Added third classifier mode `"tri_cwd"`: classifier called as `f(argv[1:], cwd=cwd)` and returns `(decision|None, reason)`. Existing `"bool"` and `"tri"` modes unchanged.
  - `classify_pipeline(cmd, registry=None, cwd=None)` — added `cwd` param, threaded into `_classify_component`.
- `approver.py` — three new `RULE_REGISTRY` entries (`python`, `python3`, `pre-commit` → `python_indirect:*`, mode `"tri_cwd"`). `_dispatch_bash` and `dispatch` take optional `cwd` kwarg. `run_hook` passes `cwd` from the hook payload through `dispatch(..., cwd=cwd)`.
- `tests/test_python_indirect.py` (new, 35 tests) — full coverage of `is_uv_project`, `is_venv_bin_path`, and the three classifiers. Fixtures use real `git init` rather than empty `.git/` directories because `is_uv_project` now calls `git rev-parse`.
- `tests/test_pipeline.py` — added 16 integration tests using real `git init` fixtures, covering the user's exact original command, mixed pipelines (`ls; .venv/bin/pre-commit run`), `uv run` still being allowed, and the "not in a uv project → no deny" path.

Full suite: 369 tests passing (was 318 before this work + the parallel `gh pr create` deny work).

## The "uv project" gate

The deny only fires when CWD is inside a uv project. Definition:

1. `pyproject.toml` exists in CWD directly, **OR**
2. `git rev-parse --show-toplevel` (run with `cwd=cwd`, 2s timeout) returns a path whose root contains `pyproject.toml`.

Both checks are `@lru_cache(maxsize=128)`'d. The stat-in-cwd happens first, so most calls answer in one syscall; `git rev-parse` only runs when there's no `pyproject.toml` directly in CWD. Outside both cases → no opinion ("yolo, the user's normal permission flow handles it").

The cwd-first check was added specifically because the trigger directory (`nicegui-bug-repro/`) has `pyproject.toml` but had never been `git init`'d — the original strict gate ("git root contains pyproject.toml") missed it.

## Live verification

```bash
$ echo '{"tool_name":"Bash","tool_input":{"command":".venv/bin/pre-commit install 2>&1 | tail -3; echo ---RUN---; .venv/bin/pre-commit run --all-files 2>&1 | tail -100"},"session_id":"test-live","cwd":"/home/brian/people/Brian/nicegui-bug-repro","hook_event_name":"PreToolUse"}' \
  | python3 /home/brian/.claude/hooks/approver/approver.py | jq .
```

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "pipeline_deny: .venv/bin/pre-commit: this project routes Python through `uv`. Re-run as `uv run pre-commit install 2>&1` instead of `.venv/bin/pre-commit install 2>&1` directly.; tail: trivially safe; echo: trivially safe; .venv/bin/pre-commit: this project routes Python through `uv`. Re-run as `uv run pre-commit run --all-files 2>&1` instead of `.venv/bin/pre-commit run --all-files 2>&1` directly.; tail: trivially safe",
    "additionalContext": "approver: pipeline_deny"
  }
}
```

## Scope of the deny (narrow on purpose)

What IS denied in a uv project:

- `.venv/bin/<anything>` (any path containing `/.venv/bin/` or `/venv/bin/`)
- `python -m <module>` and `python3 -m <module>`
- bare `pre-commit ...`

What is NOT denied (deliberately, per user scoping):

- `python script.py` — out of scope
- `python -V`, `python --version` — out of scope
- `python -c '...'` — out of scope
- bare `ruff`, `bandit`, `mypy`, `pytest` — easy to add as one-line `_deny_bare_tool` wrappers when the need arises, but not currently denied
- `/usr/bin/python3 -V` style system-Python — same as above, out of scope per "no -m" rule
- Anything OUTSIDE a uv project (no `pyproject.toml` in cwd and no `git rev-parse` answer) — no opinion at all

## Known minor caveat

When the original command has `2>&1` or other shell redirects, those tokens end up in the suggested rewrite string (e.g., `uv run pre-commit install 2>&1`). Shell-wise this is still correct — when Claude reads the deny reason and rewrites the command, the redirect re-parses as a redirect at the new shell. Just visually noisy in the deny text. A small filter in `_joined_suffix` could strip redirect-like tokens if it bothers in practice; leaving as-is for now.

## New mode: `tri_cwd`

The dispatcher now supports three classifier modes:

| Mode      | Signature                              | Return                                   |
|-----------|----------------------------------------|------------------------------------------|
| `bool`    | `f(argv) -> (ok: bool, reason: str)`   | True → allow; False → None               |
| `tri`     | `f(argv) -> (decision\|None, reason)`  | decision passed through                  |
| `tri_cwd` | `f(argv, cwd=...) -> (decision\|None, reason)` | decision passed through, cwd available |

`cwd` is the CWD reported by the hook payload (whatever Claude Code passes as `cwd` in the JSON). New rules that need filesystem context should use `tri_cwd`.

## Follow-ups

1. **Corpus re-run** — the `Adding a new rule` workflow says to rerun `corpus/classify_corpus.py` to measure the coverage delta. Not done in this session because the previous coverage line was 65.4% with 302 tests, and we're now at 369 tests with new rules. Run it next session if interested in the headline number.
2. **Reference snapshot drift** — `notes/approver-reference.md` predates both the `gh pr create` deny and this `python_indirect` rule. It still lists the old registry and old layout. Consolidation pass overdue (intentionally deferred per the convention: dated deltas first, refresh reference on demand).
3. **Memory file is also stale** — `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/reference_approver-script.md` is the upstream snapshot of this same content. Same staleness applies. Update on demand.
4. **More bare-tool wrappers** — user motivation included "stop trying 15 ways to run ruff and bandit". Pattern is one-line wrappers via `_deny_bare_tool`. Add `ruff` / `bandit` / `mypy` / `pytest` when concrete annoyance recurs; don't pre-populate before the need is real.
5. **claude-sync gap (still)** — `~/.claude/hooks/approver/` still isn't on the sync list. This rule is single-machine until that's addressed.

## Conversation source

Built in a single session on 2026-05-22 after the user hit the prompt in `nicegui-bug-repro/`. TDD throughout — RED confirmed on missing module, RED confirmed on missing `cwd` kwarg in `classify_pipeline`, GREEN after each implementation slice. Live-tested end-to-end against the exact triggering command.
