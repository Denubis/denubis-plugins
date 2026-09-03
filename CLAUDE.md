# denubis-plugins

Claude Code plugins for design, implementation, and development workflows.

## Runtime boundaries

- Application and packaged-tool Python targets 3.14 or newer. Modern 3.14 syntax,
  including parenthesis-free multi-exception clauses, is intentional. PEP 723
  `requires-python` declarations must match the syntax a script uses. `ruff format`
  runs at the 3.14 target and silently rewrites `except (A, B):` into that
  parenthesis-free form, which is a SyntaxError below 3.14, so a script declaring
  `>=3.11` (the five `using-bibliography` helpers) and any module it imports must
  catch one exception per clause unless the file is listed in
  `[tool.ruff.per-file-target-version]`. Evidence: the `except OSError` comment in
  `plugins/denubis-academic/skills/using-bibliography/zotero_auth.py`, caught on
  2026-09-03 when the formatter produced the rewrite.
- Hook programs under `plugins/*/hooks/*.py` must parse and import on Python 3.9 or
  newer. Keep annotations runtime-safe with `from __future__ import annotations` and
  use portable exception clauses. Hooks run through the caller's resolved Python, not a
  PEP 723 script environment.
- In this uv project, invoke repository Python and tools through `uv run`; prefer console
  entry points over `python -m`. Packaged hooks follow the runtime exception above.
  Authority: `cc-search-chats context e3d35d8d-bfe1-4677-adc1-e92ef3ad6e9d --json`
  and `cc-search-chats context 8fc827c0-b9d3-4e7d-8f92-268a7743e930 --json` (raw
  records: `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/64611e50-8793-451a-82ca-0b4fc5264e02.jsonl:58` and `:69`).

## Repository contracts

- Derive schema-level value sets from the authoritative implementation at the point of
  use. Do not redeclare CHECK values, enum members, or valid-state tuples from memory or
  documentation.
- When authoritative external sources disagree, record both with citations and
  verification dates, label each claim `observed` or `documented`, and gate behavior on
  the conservative intersection until the conflict is resolved.
- A plugin version change updates its `.claude-plugin/plugin.json`, matching
  `.claude-plugin/marketplace.json` entry, and top-of-file `CHANGELOG.md` entry in the
  same release change. Tests travel with the implementation they establish.
- Each plugin owns one coherent concern unless its orchestration boundary explicitly
  requires a mixed bundle. Cross-cutting behavior is documented by behavioral boundary,
  not marketplace folder.

## Finding aids

- Current topology and constraints: `docs/architecture/README.md`.
- Design decisions: `docs/architecture/decisions/`.
- Testing commands: `.ed3d/testing-guidance.md` when present, otherwise `pyproject.toml`
  and `scripts/pre-commit`.
- Task-invocation syntax and directive structure:
  `denubis-extending-claude:writing-claude-directives`.
- Repository search flags, scope, and negative-result handling:
  `denubis-plan-and-execute:using-code-search`.
- Reviews of instruction, skill, hook, evidence, or deployment-control changes:
  `docs/review-rubrics/instruction-control.md`.
- Main-repository memory: resolve the Git common directory, inventory its parent's
  `.notes/` including hidden and ignored files, and open relevant bodies and sources.
