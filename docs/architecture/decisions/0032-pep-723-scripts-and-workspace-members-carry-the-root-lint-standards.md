# ADR 0032 — PEP 723 scripts and workspace members carry the root lint standards in their own configuration

**Status:** Accepted (2026-10-22). Closes ticket L2 of the lint baseline paydown
(`docs/audits/2026-10-21-lint-baseline-defects.md`, section 4, question 2) and closes
ticket L12 (the commit gate runs every configured testpath, 2284 tests, with the
workspace members installed), confirmed directly at
`ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:4d3e2ec6-ecd6-4bb8-b9fd-3ab501779bfa`
(2026-10-22T06:51Z): "yes, commit?".

## Authority evidence

Original human messages in session `f30676a7-e08c-43cb-86f8-9dc704202a5a`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:1bde0255-f1f5-47ce-9a42-b7753d54c228`
  (2026-10-22T04:37Z): "and yes, that does mean that we need to go make sure those things
  pyprojects have our same standards"
- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:d77067cb-96e0-4a6c-a42d-c1fd9f704041`
  (2026-10-22T04:39Z), confirming option 1 (a settings table inside each script's own
  metadata block) when the two options were restated: "yes", quoting the message above.

Resolvers:

```sh
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:1bde0255-f1f5-47ce-9a42-b7753d54c228 --reference-only --json
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:d77067cb-96e0-4a6c-a42d-c1fd9f704041 --reference-only --json
```

## Context

ty treats a file with PEP 723 inline script metadata as its own project and reads
`[tool.ty]` from that metadata block, not from the repository `pyproject.toml`. The
2026-10-21 audit observed that the root `[tool.ty]` settings therefore never reach the
13 bibliography and token-estimator scripts, and that 40 sibling imports inside them
(`zotero_auth`, `zotero_local_api`, `write_gate`, `renderer`, and so on, resolved at
runtime by a `sys.path` insert of the script's own directory) stay unresolved. The two
uv workspace members, `workflow_statusline` and `crash_recovery`, have their own
`pyproject.toml` files with no tool sections.

The alternative was to pass the same settings as `ty check -c` flags from
`scripts/lint.sh`, which keeps one place to edit but leaves a script unconfigured when
anyone checks it directly.

## Decision

1. Each PEP 723 script carries a `[tool.ty]` table in its own metadata block. The table
   expresses the root standards for that script (python version matching its
   `requires-python`, the sibling-module search path), not a looser set.
2. The workspace members' `pyproject.toml` files state their relationship to the root
   standards explicitly, so a reader does not need ruff's or ty's discovery rules to know
   which configuration applies. Thresholds, rule sets and pins are the root's; a member
   does not declare its own.
3. `scripts/lint.sh` stays the single runner and does not carry per-script flags.

## Consequences

- A script's own header is the complete statement of how it is run and checked, which
  matches how those scripts already declare their dependencies.
- When the root standards change, the script tables and member files must follow; the
  warn-only lint report is where drift shows up.
- Dependencies that are not in the project environment (`httpx`, `pymupdf`, `docling`,
  `torch`) are a separate question (ticket L3) and are not resolved by this decision.
