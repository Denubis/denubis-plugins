# ADR 0031 — `ruff format` covers Markdown code blocks; vendored upstream files are excluded

**Status:** Accepted (2026-10-22). Closes ticket L1 of the lint baseline paydown
(`docs/audits/2026-10-21-lint-baseline-defects.md`, section 4, question 1).

## Authority evidence

Original human messages in session `f30676a7-e08c-43cb-86f8-9dc704202a5a`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:be765608-aaac-4355-98f1-c50bc540f49e`
  (2026-10-22T04:24Z), answering "should `ruff format` skip Markdown files?": "ok, so
  no, let's do proper formatting, that's a good idea, and linting markdown is good?"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:89e5901d-59b5-4b27-909d-9250fb84ff65`
  (2026-10-22T04:25Z), answering "exclude the single vendored file, or format it too?":
  "yes, that's fine, vendored is ignored for a reason".

Resolvers:

```sh
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:be765608-aaac-4355-98f1-c50bc540f49e --reference-only --json
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:89e5901d-59b5-4b27-909d-9250fb84ff65 --reference-only --json
```

## Context

Ruff 0.16.9 includes `*.md` by default and formats the Python code blocks inside
Markdown. At the 2026-10-21 baseline, 18 of the 40 files `ruff format --check` reports
are Markdown: fifteen historical implementation plans, two shipped skill or agent
prompts, and `plugins/denubis-extending-agents/skills/writing-skills/anthropic-best-practices.md`,
whose body is a verbatim copy of an obra/superpowers file pinned to upstream commit
`6fd4507`. Nothing tests that pin; its value is that the next upstream sync diffs our
copy against theirs and sees only upstream's changes.

## Decision

1. Markdown stays inside `ruff format`'s scope. Code blocks in our own documents,
   including historical plans, are formatted like any other code.
2. Files vendored verbatim from an upstream repository are excluded from the formatter
   by name under `[tool.ruff.format] exclude`. Today that is the one obra import above.
   A later vendored import is added to the same list when it is pinned.

## Consequences

- The mechanical pass formats 17 Markdown files alongside the 22 Python files; three
  historical plans gain the 3.14-only `except A, B:` form in their examples, which is
  accepted as cosmetic.
- The vendored file keeps its upstream-diffable body and its frontmatter stays true.
- The per-file-target-version table in `pyproject.toml` still governs the Python files
  pinned at py311; this decision does not change it.
