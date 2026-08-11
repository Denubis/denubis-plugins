# denubis-plugins

Claude Code plugins for design, implementation, and development workflows.

## Runtime boundaries

- Application and packaged-tool Python targets 3.14 or newer. Modern 3.14 syntax,
  including parenthesis-free multi-exception clauses, is intentional. PEP 723
  `requires-python` declarations must match the syntax a script uses.
- Hook programs under `plugins/*/hooks/*.py` must parse and import on Python 3.9 or
  newer. Keep annotations runtime-safe with `from __future__ import annotations` and
  use portable exception clauses. Hooks run through the caller's resolved Python, not a
  PEP 723 script environment.

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
- Main-repository memory and relevant prior chat work:
  `denubis-project-notes:scanning-project-notes`.
