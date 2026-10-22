# Lint baseline defects, 2026-10-21

This audit covers the warn-only lint, type, complexity and dead-code gates added in commit
`8a0962b`. It is read-only. No code, configuration or test was changed. Scratch work lived
under `/tmp/lintaudit-20261021/`.

- Repository: `brian-ed3d-plugins`, branch `main`, HEAD `8a0962b`.
- Tools, from `uv run --frozen <tool> --version`: ruff 0.16.9, ty 0.0.84, complexipy 8.0.1,
  vulture 2.16.
- Author: the `lint-baseline-audit` teammate (Claude Opus 5.5), dispatched by `team-lead`.
  Runs were made on 2026-10-21 and 2026-10-22 against the same HEAD.

## How to read this document

Evidence labels:

- **Observed**: output of a command run for this audit. The command is named.
- **Inferred**: a conclusion drawn from observed facts. The reasoning is given.
- **Not checked**: said explicitly wherever it applies.

Classes used in every table:

| Class | Meaning |
|---|---|
| (a) | Real defect. The code is wrong or its types are false now. |
| (b) | Mechanical: safe, with no design choice. `auto` means the formatter or `ruff check --fix` applies it. `unsafe-auto` means ruff has a fix but marks it unsafe, and this audit checked that it is safe here. `manual` means a short hand edit. |
| (c) | Tooling configuration gap. The code is fine; the tool lacks information. |
| (d) | Intentional pattern. Keep the code and document an ignore. |
| (e) | Needs human judgement. |

### Commands and counts (all observed at HEAD)

| Tool | Command | Result |
|---|---|---|
| ruff check | `uv run --frozen ruff check . --output-format concise` | 81 findings; 3 safe fixes, 8 unsafe fixes |
| ruff format | `uv run --frozen ruff format --check .` | 40 files would be reformatted: 18 Markdown, 22 Python |
| ty | `uv run --frozen ty check --output-format concise` | 184 diagnostics, 88 of them `unresolved-import` |
| complexipy | `uv run --frozen complexipy --failed --plain .` | 58 functions over 15 |
| vulture | `uv run --frozen vulture` | 9 findings, exit 3 |
| pytest | `uv run --frozen pytest -q -p no:cacheprovider -rs` | 2270 passed, 14 skipped, exit 0; all 14 skips need spaCy |

**Coverage method.** An out-of-tree pytest plugin recorded which source lines each test module
executed, using `sys.monitoring` (`/tmp/lintaudit-20261021/covplug/lintaudit_cov.py`, loaded
with `PYTHONPATH=... pytest -p lintaudit_cov`). The traced run gave the same 2270 passed and 14
skipped. Limits: it sees in-process execution only. Code that tests launch with `subprocess`
shows 0 lines, and those files are marked "subprocess-tested". An executed line proves
execution, not that a test asserts on its result.

### Contradictions with the dispatch brief

1. **Format count.** Observed 40 files at HEAD, not 43. The 43 reproduces on the tree before
   commit `eeb6ee3` (the instruction-control retirement) with the `8a0962b` `pyproject.toml`
   overlaid. That commit removed three unformatted files. The baseline comment in
   `pyproject.toml` and the `8a0962b` commit message still say 43.
2. **Format scope.** Ruff 0.16.9 includes `*.md` by default (`uv run --frozen ruff config
   include`). It formats Python code blocks inside Markdown. 18 of the 40 files are Markdown.
   Only 4 files sit under `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`;
   16 sit under `docs/implementation-plans/` as a whole.
3. **Complexity count.** Observed 58, not 62. The pre-retirement tree gives 60. The 62 was
   not reproduced.
4. **Unresolved imports.** Observed 88, not 90. The total of 184 matches.
5. **Permission-queue count.** Observed 37 ruff findings, not 36: 19 E501, 17 S101 and one
   I001. All are in one file, `experiments/permission-queue/pending/installed_daemon.py`.
6. **The 17 asserts are not runtime asserts in shipped code.** `pending/installed_daemon.py`
   is a pytest module. It defines a fixture and
   `test_installed_daemon_shares_occurrences_and_only_first_answer_applies`. Its name escapes
   the test globs, and the configured testpaths do not include it. It is also the subject of
   the open ticket "Isolated Codex two-client approval test retry" in
   `.notes/project_open-questions.md`. Line 130 still sends `"sandbox": "workspaceWrite"`,
   the value that ticket asks permission to change.
7. **UP045 is not a deliberate py39 style.** At the py39 target, UP045 fires only because the
   file has `from __future__ import annotations`. A probe of the same code without that import
   gives no finding. With the import, annotations are never evaluated, and the hook does not
   introspect them: `rg` for `get_type_hints`, `__annotations__` and `annotationlib` finds
   nothing in the hook or its test. `instruction-budget.py` is the only hook that uses
   `Optional`. `code-quality-guard.py` and `pretooluse-bash-dispatcher.py` already write
   `X | None` behind the same import, which is what CLAUDE.md asks for.
8. **Sibling imports.** Nine bibliography scripts insert their own directory into `sys.path`,
   and `annotated-bibliography/check.py` inserts `../using-bibliography`. `copy_item.py`,
   `update_item.py`, `fetch.py` and the plain modules rely on the script directory being
   `sys.path[0]`.
9. **ty settings in `pyproject.toml` do not reach PEP 723 scripts.** Section 1.3 gives the
   evidence. This changes the shape of the `[tool.ty]` fix.
10. **The commit gate does not run every test.** `.pre-commit-config.yaml` runs `pytest
    tests/`, which collects 1786 tests. A bare `pytest` collects 2284. The missing 498 are the
    token-estimator, crash-recovery and status-line suites. The retired `scripts/pre-commit`
    had the same scope, so the gap is old, not a regression.

## 1. Defect inventory

### 1.1 ruff check: 81 findings

Command: `uv run --frozen ruff check . --output-format concise`.

**docs (5)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py:78, 93, 161, 198, 205` | E501 (5) | (e) | A script from a completed April plan. No test, hook or script runs it: `rg --hidden --no-ignore` and `git grep` find only its own plan documents. The formatter clears 161 and 198. Whether `docs/` Python is gated at all is question 5. |

**experiments/permission-queue (37), all in `pending/installed_daemon.py`**

| Location | Rule | Class | Why |
|---|---|---|---|
| `:3` | I001 | (b) auto | Moves the bare `test_permission_queue_codex_server` import beside third-party imports. Order only. Held by the open ticket. |
| `:26, 35, 45, 59, 73, 75, 79, 81, 89, 107, 125, 130, 132, 133, 135, 136, 143, 148, 149` | E501 (19) | (b) auto | The formatter clears 18. One remains: the sentinel command f-string, line 72 after formatting. Held by the open ticket. |
| `:46, 69, 111, 113, 122, 139, 141, 142, 143, 145, 147, 150, 154, 155, 159, 162, 163` | S101 (17) | (d) | Pytest assertions in a parked pytest module. Configure, do not edit, while the ticket is open. Question 4. |

**plugins/denubis-academic (15)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `skills/using-bibliography/copy_item.py:274, 308, 322` | PLC0415 (3) | (d) | Lazy `import httpx`. httpx is not installed in the dev environment, and 8 test modules execute `copy_item.py` in-process, so a top-level import would break them. The same reason is already documented per file for `annotate.py`, `fetch.py`, `renderer.py` and `zotero_auth.py`, and inline for `zotero_local_api.py`, `resolve.py` and `ingest.py`. |
| `skills/using-bibliography/copy_item.py:338` | S112 | (a) | `find_items` catches every `Exception` and continues. A library whose search fails drops out of the candidates with no message, and programming errors are hidden too. This breaks the global "never use empty catch blocks" rule. The reporting choice is question 11. |
| `skills/using-bibliography/copy_item.py:378` | PLR0912, PLR0915 | (e) | `main` has 14 branches and 51 statements. It is also a complexity hotspot (19). Section 3.2. |
| `skills/using-bibliography/renderer.py:176` | RUF012 | (b) manual | `BLOCKS` is a class-level set that is only read (lines 202 and 208). Make it a `frozenset`. Ruff offers no fix. |
| `skills/using-bibliography/renderer.py:199` | ARG002 | (d) | `attrs` belongs to the `HTMLParser.handle_starttag` signature. Renaming it to `_attrs` makes ty report `invalid-method-override` (probe `/tmp/lintaudit-20261021/probe/renamed.py`). `typing.override` would exempt it but needs Python 3.12, and this file is pinned to 3.11. One comment, `# noqa: ARG002, V107`, satisfies ruff and vulture without tripping RUF100 (probe `combined.py`). |
| `skills/using-bibliography/renderer.py:425` | PLR0917 | (e) | `_write_outputs` takes 6 positional parameters. Question 7. |
| `skills/using-bibliography/update_item.py:138` | PLR0917 | (e) | `build_update_payload`. Every caller already passes keywords: the tests and `main` at line 498. Question 7. |
| `skills/using-bibliography/update_item.py:338` | PLC0415 | (d) | Lazy `import httpx`, for the same reason as `copy_item.py`. |
| `skills/using-bibliography/update_item.py:416` | PLW2901 | (b) manual | `for name in args.clear: name = name.strip()`. Rename the loop variable. |
| `skills/using-bibliography/update_item.py:431` | PLR0911, PLR0912 | (e) | `main` has 12 returns and 16 branches. Complexity 22. Section 3.2. |
| `skills/using-bibliography/update_item.py:445` | PLC0415 | (b) manual | `from copy_item import find_collection` inside `main`. `copy_item` is already imported at line 69, and no test patches `find_collection`, so joining the top-level import changes nothing. |

**plugins/denubis-crash-recovery (1)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `scripts/crash_recovery/tests/fixtures/jsonl_builder.py:254` | PLR0917 | (c) | Test helper `make_liveness_file`. Every caller in `test_scan.py` passes keywords. The test ignore lists omit the size rules, although `[tool.complexipy]` exempts tests by design. |

**plugins/denubis-hook-instruction-budget (9)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `hooks/instruction-budget.py:73, 103, 194, 226, 305, 306, 336` | UP045 (7) | (b) unsafe-auto | See contradiction 7. Ruff marks the fix unsafe because it cannot rule out runtime introspection; this audit checked that there is none. After the rewrite, `Optional` becomes an unused import, which a safe F401 fix removes. |
| `hooks/instruction-budget.py:103, 331` | E501 (2) | (b) auto | Cleared by the formatter at the py39 target. |

**plugins/denubis-plan-and-execute (2)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `scripts/workflow_statusline/src/workflow_statusline/cache.py:132` | PLR0917 | (e) | `append_rate_sample`. Callers pass three arguments by position and the rest by keyword (`__main__.py:182, 201`, `test_cache.py`). Question 7. |
| `scripts/workflow_statusline/src/workflow_statusline/ratelimit.py:290` | PLR0917 | (e) | `is_fast_burn`. Its only callers are tests; `rg` and `ast-grep` both find no production caller. Questions 7 and 14. |

**plugins/denubis-project-notes (2)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `skills/scanning-project-notes/scripts/inventory.py:4` | I001 | (b) auto | Removes one blank line. |
| `skills/scanning-project-notes/scripts/inventory.py:53` | PLR0911 | (d) | `extract_frontmatter` returns one status per outcome, 7 in all. The repository already ignores PLR0911 per file for the same shape in `crash_recovery/jsonl.py` and `render.py`. |

**tests (10)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `tests/test_bibliography_copy.py:211, 242` | E501 (2) | (b) auto | Cleared by the formatter. |
| `tests/test_hook_launcher_cwd_independence.py:136, 218` | E501 (2) | (b) auto | Cleared by the formatter. |
| `tests/test_hook_launcher_cwd_independence.py:154` | S602 | (d) | The test runs each `hooks.json` launcher string through a shell on purpose, because Claude Code expands `${CLAUDE_PLUGIN_ROOT}` in a shell. Add an inline `# noqa: S602` with that reason. |
| `tests/test_hook_portability.py:169` | E501 | (b) manual | The formatter wraps the assertion, but its f-string message stays 89 characters (line 168 after formatting). Shorten the message. |
| `tests/test_instruction_budget_guard.py:11` | TC003 | (b) unsafe-auto | `types.ModuleType` appears only in annotations, and the file has postponed annotations, so a `TYPE_CHECKING` import is safe. |
| `tests/test_paper_review_skill.py:62` | E501 | (b) auto | Cleared by the formatter. |
| `tests/test_project_notes_inventory.py:3` | I001 | (b) auto | Removes one blank line. |
| `tests/test_project_notes_inventory.py:57` | PLR0915 | (c) | Test size. Same gap as `jsonl_builder.py`. |

Total: 5 + 37 + 15 + 1 + 9 + 2 + 2 + 10 = 81.

### 1.2 ruff format: 40 files

Commands: `uv run --frozen ruff format --check .` and `uv run --frozen ruff format --diff .`.
"Lines" counts changed lines in that diff (845 in all).

**Markdown (18).**

| File | Lines | Class | Why |
|---|---|---|---|
| `docs/implementation-plans/2026-01-30-project-context-inventory/phase_01.md` | 93 | (e) | Historical plan. Six `except (A, B):` clauses in plan code become the 3.14-only `except A, B:` form. |
| `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` | 16 | (e) | Historical review. |
| `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02.md` | 24 | (e) | Historical plan. |
| `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05.md` | 13 | (e) | Historical plan. |
| `docs/implementation-plans/2026-05-08-crash-recovery/code-review-findings-phase-7.md` | 2 | (e) | Historical review. |
| `docs/implementation-plans/2026-05-08-crash-recovery/phase_01.md` | 4 | (e) | Historical plan. |
| `docs/implementation-plans/2026-05-08-crash-recovery/phase_02.md` | 28 | (e) | Historical plan. |
| `docs/implementation-plans/2026-05-08-crash-recovery/phase_03.md` | 67 | (e) | Historical plan. One `except` rewrite. |
| `docs/implementation-plans/2026-05-08-crash-recovery/phase_04.md` | 94 | (e) | Historical plan. |
| `docs/implementation-plans/2026-05-08-crash-recovery/phase_05.md` | 66 | (e) | Historical plan. |
| `docs/implementation-plans/2026-05-08-crash-recovery/phase_06.md` | 62 | (e) | Historical plan. |
| `docs/implementation-plans/2026-06-12-crash-detection/phase_02.md` | 8 | (e) | Historical plan. One `except` rewrite. |
| `docs/implementation-plans/2026-06-12-crash-detection/phase_03.md` | 9 | (e) | Historical plan. |
| `docs/implementation-plans/2026-06-12-crash-detection/phase_04.md` | 5 | (e) | Historical plan. |
| `docs/implementation-plans/2026-06-12-crash-detection/phase_05.md` | 1 | (e) | Historical plan. |
| `plugins/denubis-basic-agents/agents/python-developer.md` | 2 | (e) | Shipped agent prompt. Adds blank lines inside a teaching example. |
| `plugins/denubis-extending-agents/skills/writing-skills/anthropic-best-practices.md` | 10 | (d) | Shipped. Its frontmatter says the obra body is "byte-identical" to upstream commit `6fd4507`. The formatter changes quote style and comment alignment inside that body. Never format this file. |
| `plugins/denubis-plan-and-execute/skills/coding-fcis/SKILL.md` | 5 | (e) | Shipped skill. Moves `...  # deterministic domain decision` onto the signature line, which makes the example harder to read. |

The plans are (e) because they are records. Formatting changes what they show, and in three
of them it rewrites code into syntax the planned scripts may not have targeted. Question 1.

**Python (22).**

| File | Lines | Class | Tests | Note |
|---|---|---|---|---|
| `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py` | 25 | (e) | none | Question 5. |
| `experiments/permission-queue/pending/installed_daemon.py` | 150 | (e) | not collected | Held by the open ticket. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_classify.py` | 3 | (b) auto | itself | Rejoins a docstring and creates a new 89-character E501 at line 29. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_jsonl_tail.py` | 6 | (b) auto | itself | Same. New E501 at lines 102 and 158. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_note.py` | 3 | (b) auto | itself | Same. New E501 at line 217. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_plugin_manifest.py` | 3 | (b) auto | itself | Same. New E501 at line 49. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py` | 4 | (b) auto | itself | Joins a comprehension. |
| `plugins/denubis-external-agents/scripts/update_codex_profile.py` | 4 | (b) auto | `tests/test_update_codex_profile.py`, 47 of 68 lines executed | Joins one call. Pinned py310. Compiles under 3.10 after formatting. |
| `plugins/denubis-hook-instruction-budget/hooks/instruction-budget.py` | 11 | (b) auto | `tests/test_instruction_budget_guard.py`, 233 of 330 lines; `tests/test_hook_portability.py` imports it under 3.9 | Wraps two lines and merges an implicit string concatenation into one f-string. Pinned py39. Compiles under 3.9 after formatting. |
| `plugins/denubis-project-notes/skills/scanning-project-notes/scripts/inventory.py` | 3 | (b) auto | `tests/test_project_notes_inventory.py`, subprocess-tested | Joins one condition. Compiles under 3.11. |
| `scripts/test_quality.py` | 23 | (b) auto | `tests/test_test_quality.py` | Joins expressions. |
| `tests/skill-evals/plan-and-execute/checkpoint-uat/fixture/greeting.py` | 1 | (b) auto | none; an agent eval fixture | Removes a trailing blank line. The pre-commit end-of-file fixer would do the same. |
| `tests/skill-evals/plan-and-execute/outcome-planning/fixture/greeting.py` | 1 | (b) auto | none; an agent eval fixture | Same. |
| `tests/test_bibliography_copy.py` | 14 | (b) auto | itself | Layout. |
| `tests/test_hook_launcher_cwd_independence.py` | 12 | (b) auto | itself | Includes two `except (A, B):` rewrites to the 3.14 form. Valid: tests run on the project Python, 3.14. |
| `tests/test_hook_portability.py` | 8 | (b) auto | itself | Layout. |
| `tests/test_instruction_budget_guard.py` | 2 | (b) auto | itself | Layout. |
| `tests/test_instruction_delivery.py` | 6 | (b) auto | itself | Layout. |
| `tests/test_paper_review_skill.py` | 20 | (b) auto | itself | Layout. |
| `tests/test_skill_reference_integrity.py` | 1 | (b) auto | itself | Layout. |
| `tests/test_test_quality.py` | 34 | (b) auto | itself | Layout. |
| `tests/test_update_codex_profile.py` | 2 | (b) auto | itself | Layout. |

**The py311 pins work.** `uv run --frozen ruff format --diff` on the 14 pinned bibliography
files reports "14 files already formatted" with exit 0. A probe shows the formatter rewrites
`except (OSError, ValueError):` at py314 and leaves it alone at py311
(`/tmp/lintaudit-20261021/probe/exc.py`). The pinned files hold one parenthesised
multi-exception clause today, `renderer.py:256`, and it binds `as error`, which keeps its
parentheses at any target. So the pins guard future edits. No rewrite is pending now.

### 1.3 ty: 184 diagnostics

Command: `uv run --frozen ty check --output-format concise`.

**How ty treats PEP 723 scripts.** Seventeen files carry `# /// script` metadata
(`rg -l '^# /// script' -g '*.py'`). ty checks each one as its own environment with the
script's own `requires-python`, per the ty configuration reference. Four experiments show
which settings reach them:

| Where the setting lives | Reaches PEP 723 scripts? | Evidence (observed) |
|---|---|---|
| `[tool.ty]` in `pyproject.toml` | No. Sibling imports stay unresolved in every script. | Scratch copy of HEAD with the proposed table: 160 diagnostics; 40 sibling imports unresolved, all inside scripts. |
| `ty check -c 'environment.extra-paths=[...]'` | Yes. Paths resolve from the working directory. | In-repo run: all 56 sibling imports resolve. |
| `ty check --config-file x.toml` | Yes, but paths resolve from each script's own directory. Every script then fails with `invalid-script-metadata` and is not checked. | In-repo run with `/tmp/lintaudit-20261021/proposed_ty.toml`: 114 diagnostics, 17 of them `invalid-script-metadata`. That 114 is not a valid count. |
| `[tool.ty.environment] extra-paths = ["."]` inside the script's own metadata block | Yes. | Scratch edit of `annotate.py`: sibling and `pymupdf` imports resolve; only `httpx` remains. The block still parses as TOML with `tomllib`. |

So an honest fix has two parts: `pyproject.toml` settings for tests and plain modules, and
script-level settings for the 13 scripts that need them. Question 2 chooses the second part's
form.

**1.3.1 unresolved-import (88)**

| Cluster | Count | Class | Locations | Why |
|---|---|---|---|---|
| Sibling module, inside a PEP 723 script | 40 | (c) | `using-bibliography/annotate.py:42, 43, 257`; `collection.py:49, 50, 51, 58`; `copy_item.py:61`; `create_item.py:37, 38, 39, 40, 46, 47`; `fetch.py:56`; `ingest.py:38, 39, 46`; `item_collections.py:38, 39, 40, 41, 47`; `register_export.py:64, 65, 66, 67, 68`; `resolve.py:63, 64, 65`; `trash_item.py:41, 42, 43, 44`; `update_item.py:65, 69, 73, 445`; `annotated-bibliography/check.py:15` | Bare sibling imports work at runtime because the script directory is on `sys.path`. Needs the script-level setting (question 2). |
| Sibling module, inside a test | 16 | (c) | `tests/test_bibliography_collection.py:216, 217`; `test_bibliography_create_item.py:32, 33`; `test_bibliography_item_collections.py:31, 32`; `test_bibliography_register_export.py:39`; `test_bibliography_renderer.py:176, 177`; `test_bibliography_trash_item.py:31, 32`; `plugins/denubis-token-estimator/tests/test_token_estimator_estimate.py:13, 15`; `test_token_estimator_mapper.py:12`; `test_token_estimator_passes.py:23`; `test_token_estimator_rules.py:11` | Resolved by `extra-paths` in `pyproject.toml` (scratch copy, observed). |
| `httpx` | 19 | (c) | `annotate.py:206, 224, 296`; `copy_item.py:274, 308, 322`; `fetch.py:234, 252`; `ingest.py:86, 101`; `resolve.py:559, 578, 848`; `update_item.py:338`; `zotero_auth.py:268, 275`; `zotero_local_api.py:169, 187, 451` | httpx is a declared PEP 723 dependency but is absent from `uv.lock`. Install it or allow it unresolved: question 3. |
| Heavy optional dependency | 12 | (c) | `annotate.py:315` (pymupdf); `renderer.py:88, 284, 306` (pymupdf), `285` (pymupdf4llm), `307, 308, 309, 321` (docling), `310` (docling_core), `521` (torch); `academic-writing/prose_shape.py:267` (spacy) | Lazy imports of large dependencies (docling, torch, the spaCy transformer model). Installing them for a type check is not proportionate. `allowed-unresolved-imports` suppresses all 12 (observed with `-c`). |
| Test module imported by a parked test | 1 | (e) | `experiments/permission-queue/pending/installed_daemon.py:18` (`test_permission_queue_codex_server`) | Resolves only if the file moves under `tests/` or `tests/` becomes a search path. Held by the open ticket. |

**1.3.2 Shipped code, other rules: 40 at HEAD, plus 4 that appear once siblings resolve**

| Location | Rule | Class | Why |
|---|---|---|---|
| `docs/branch-bg-colour-eval.py:599, 600 (2)` | invalid-argument-type, unresolved-attribute (3) | (b) manual | `spec_from_file_location` may return None. Add a guard that raises a clear error. Question 5 decides whether `docs/` is in scope. |
| `experiments/permission-queue/board.py:1630` | invalid-assignment | (a) | The only unguarded write to `self.readback`. Lines 933, 1565, 1599 and 1605 check `is not None` first. Probably unreachable, because the picker opens after mount (inferred). Add the same guard. |
| `experiments/permission-queue/claude_state.py:175 (3), 178` | unsupported-operator (4) | (c) | `type(x) not in {int, float}` is correct at runtime and rejects `bool`, but ty does not narrow on it. An `isinstance` check with a `bool` exclusion would narrow; it also accepts int subclasses such as `IntEnum`, which is equivalent for JSON input. |
| `experiments/permission-queue/codex_pane_state.py:48, 49 (2), 52` | invalid-argument-type, unsupported-operator (4) | (c) | Same guard pattern in `timestamp()`. |
| `experiments/permission-queue/codex_server.py:80 (2), 82 (2)` | invalid-argument-type, unsupported-operator (4) | (c) | Same guard pattern in `timestamp()`. |
| `experiments/permission-queue/pending/installed_daemon.py:63` | invalid-method-override | (d) | `log_message(self, _format, *_args)` renames the base parameters to silence unused-argument warnings. Held by the open ticket. |
| `plugins/denubis-academic/skills/using-bibliography/register_export.py:331` | invalid-argument-type | (e) | `library.get("libraryID")` may be None, and `bbt_collection_path` would then build `"/None/..."` silently. Libraries come from `/api/plus/libraries`, which presumably always carries the field (not checked). Question 13. |
| `zotero_local_api.py:387` | invalid-argument-type | (a) | `doi_citekeys(items: list[dict], ...)` receives a tuple and only iterates. The annotation is wrong. Widen it to `Sequence[dict]`. |
| `zotero_local_api.py:566, 573, 578` | invalid-return-type, not-iterable (2) | (a) | Inner `send()` in `write_object` is annotated `-> WriteResult` but returns `(WriteResult, status_code)`, and its callers unpack the pair. Runtime is correct; the annotation is false. Change it to `-> tuple[WriteResult, int]`. |
| `collection.py:333, 414, 502, 511` (appear once siblings resolve) | invalid-argument-type (4) | (e) | `collection_version()` returns `int \| None`. With a None version, the preview prints `--expect-version None`, `write_gate.state_refusal` compares strings and passes, and the write sends `If-Unmodified-Since-Version: None`. Zotero presumably always returns a version (not checked). Question 13. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan_db.py:90, 142, 186, 227` | unresolved-attribute (4) | (d) | `conn: object` is deliberate; its comment says so, to admit mock connections in tests. A small `Protocol` that declares `execute` keeps the mocks valid and removes the need for an ignore. |
| `plugins/denubis-external-agents/scripts/update_codex_profile.py:93` | possibly-missing-submodule | (b) manual | Uses `tomlkit.exceptions.ParseError` without importing the submodule. It works because tomlkit 0.15.1 imports it (observed at runtime). Write `from tomlkit.exceptions import ParseError`. |
| `plugins/denubis-hook-gh-fork-guard/hooks/gh-fork-guard.py:142` | unresolved-attribute | (c) | `ALLOWED_REPO` is `str \| None`, but `main()` exits at line 169 when it is None, so `repo_is_allowed` never sees None. ty cannot follow that module-level invariant. |
| `plugins/denubis-token-estimator/scripts/verify.py:481, 485, 494, 508, 511, 535` (not-iterable); `495, 508, 511, 524, 531, 536` (unsupported-operator) | 12 | (e) | `codex_threads` stores each thread as a dict literal with mixed value types, so every value has a union type. Runtime is correct. The real fix is a record type, which belongs with the `codex_threads` decomposition (section 3.1). |

Count at HEAD: 3 + 1 + 4 + 4 + 4 + 1 + 1 + 1 + 3 + 4 + 1 + 1 + 12 = 40.

**1.3.3 Tests, other rules (56)**

| Location | Rule | Class | Why |
|---|---|---|---|
| `tests/test_academic_literature_helpers.py:21, 22 (2)`; `tests/test_academic_prose_shape.py:34, 36, 37 (2)`; `tests/test_gh_fork_guard.py:25, 26 (2)`; `tests/test_supervisee_offers.py:50, 51, 53, 54` | invalid-argument-type, unresolved-attribute (14) | (b) manual | The `spec_from_file_location` loading idiom without a None check. Add `assert spec is not None and spec.loader is not None`, which is allowed in tests. |
| `tests/test_academic_literature_helpers.py:81, 108, 121, 135` | invalid-argument-type (4) | (b) manual | `HTTPError(..., hdrs={})`: typeshed wants a `Message`. Pass `email.message.Message()`. |
| `tests/test_academic_literature_helpers.py:91, 123` | unresolved-attribute (2) | (d) | Sets `status` on a `BytesIO` fake. A small fake response class would type-check. |
| `tests/test_bibliography_resolve.py:447, 558` | invalid-argument-type (2) | (b) manual | `**` over a fixture dict whose values have mixed types. Annotate the dict as `dict[str, Any]`. |
| `tests/test_bibliography_write_credentials.py:77, 78, 79, 80, 81, 82, 83, 84` | unresolved-attribute (8) | (d) | Builds a fake `httpx` from `types.ModuleType` by setting attributes. `types.SimpleNamespace` would type-check. Question 6. |
| `tests/test_branch_bg.py:263` | invalid-argument-type | (b) manual | Dict invariance. Type the helper's parameter as `Mapping`. |
| `tests/test_codex_supervisor_default_model.py:140, 156` | invalid-argument-type (2) | (b) manual | Dict invariance. Type `_spawn_calls`'s parameter as `Mapping[str, object]`. |
| `tests/test_gh_fork_guard.py:42, 44, 106, 108, 133, 135, 159, 161` | unresolved-attribute (8) | (d) | Assigns `ALLOWED_REPO` on the loaded module. `monkeypatch.setattr` is the idiomatic replacement. Question 6. |
| `tests/test_hook_portability.py:88` | no-matching-overload | (b) manual | `_uv()` returns `str \| None`. Narrow it before building the command. |
| `tests/test_permission_queue_launch.py:37, 57` | no-matching-overload (2) | (b) manual | `TMUX = shutil.which("tmux")` may be None. Narrow it. |
| `tests/test_permission_queue_board.py:749, 988, 1013, 1208, 1238, 1283, 1414, 1442, 1448` | invalid-assignment (9) | (d) | Replaces methods on instances. `monkeypatch.setattr` would satisfy ty. Question 6. |
| `tests/test_permission_queue_board.py:1717, 1719` | unresolved-attribute (2) | (d) | Sets attributes the `FakeSource` class does not declare. Declare them on the fake. |
| `tests/test_update_codex_profile.py:108` | possibly-missing-submodule | (b) manual | Same `tomlkit.exceptions` access as the script. |

Count: 14 + 4 + 2 + 2 + 8 + 1 + 2 + 8 + 1 + 2 + 9 + 2 + 1 = 56.

### 1.4 complexipy: 58 functions over 15

Command: `uv run --frozen complexipy --failed --plain .`. "Coverage" is executed body lines out
of executable body lines, from the in-process trace. Every row is class (e): the threshold is
settled, but the shape of each decomposition is a design choice. Section 3 gives the helpers
and the risk. "noqa" marks functions that already silence ruff's size rules inline.

| Location | Function | Score | Coverage | Note |
|---|---|---|---|---|
| `docs/branch-bg-colour-eval.py:653` | `largest_separated_subset` | 25 | 0/29 | Live generator of the branch-bg colour table, cited by `docs/architecture/plugins/denubis-hook-branch-bg/0-context.md`. Question 5. |
| `docs/branch-bg-colour-eval.py:1217` | `main` | 18 | 0/50 | Same. |
| `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py:139` | `audit_file` | 30 | 0/27 | Completed plan artefact. Question 5. |
| same file `:170` | `main` | 21 | 0/39 | Same. |
| `docs/usage-forecast-probe/backtest.py:45` | `forecast_eval` | 21 | 0/25 | Probe script. Its handover records a known division by zero at `blend_from=168`. Question 5. |
| `experiments/permission-queue/board.py:1101` | `WindowBoard::render_source_list` | 18 | 47/47 | Section 3.7. |
| `experiments/permission-queue/board.py:1216` | `WindowBoard::show_source` | 18 | 61/67 | Section 3.7. |
| `experiments/permission-queue/board.py:981` | `WindowBoard::refresh_windows` | 17 | 38/43 | Section 3.7. |
| `experiments/permission-queue/board.py:1485` | `WindowBoard::queue_input` | 16 | 29/33 | Section 3.7. |
| `experiments/permission-queue/board.py:1303` | `WindowBoard::update_input_status` | 16 | 22/24 | Section 3.7. |
| `experiments/permission-queue/codex_pane_state.py:92` | `rollout_time` | 20 | 27/32 | Section 3.7. |
| `experiments/permission-queue/codex_server.py:311` | `CodexServer::_snapshot` | 36 | 65/73 | Section 3.7. |
| `experiments/permission-queue/codex_server.py:198` | `CodexServer::_handle` | 24 | 34/42 | Section 3.7. |
| `experiments/permission-queue/tmux_source.py:442` | `TmuxSource::conversation` | 24 | 11/22 | Section 3.7. |
| `experiments/permission-queue/tmux_source.py:331` | `TmuxSource::snapshots` | 17 | 83/84 | Section 3.7. |
| `plugins/denubis-academic/skills/academic-writing/prose_shape.py:164` | `split_markdown` | 21 | 34/34 | Section 3.2. |
| `.../academic-writing/prose_shape.py:462` | `_analyse_section` | 20 | 0/39 | Needs spaCy; its tests skip. |
| `.../academic-writing/prose_shape.py:600` | `_section_table` | 19 | 38/40 | Section 3.2. |
| `.../academic-writing/prose_shape.py:340` | `_structural_hits` | 16 | 0/29 | Needs spaCy; its tests skip. |
| `plugins/denubis-academic/skills/annotated-bibliography/check.py:18` | `check` | 35 | subprocess-tested | noqa PLR0912. |
| `plugins/denubis-academic/skills/literature-scout/search.py:65` | `build_request` | 23 | 34/38 | Section 3.2. |
| `plugins/denubis-academic/skills/using-bibliography/collection.py:448` | `restore_collection` | 29 | 62/74 | noqa PLR0911, PLR0912. |
| `.../using-bibliography/collection.py:230` | `create_collection` | 18 | 41/54 | noqa PLR0911. |
| `.../using-bibliography/collection.py:369` | `trash_collection` | 16 | 58/66 | noqa PLR0911. |
| `.../using-bibliography/copy_item.py:111` | `find_library` | 24 | 22/27 | Shared by six scripts. |
| `.../using-bibliography/copy_item.py:378` | `main` | 19 | 0/81 | No test reaches it. |
| `.../using-bibliography/create_item.py:73` | `verification_problems` | 19 | 18/20 | Section 3.2. |
| `.../using-bibliography/fetch.py:332` | `main` | 25 | 0/90 | No test reaches it. |
| `.../using-bibliography/fetch.py:103` | `_find_library` | 20 | 19/27 | Diverges from `copy_item.find_library`. Question 10. |
| `.../using-bibliography/ingest.py:197` | `main` | 32 | 69/98 | Per-file PLR0912, PLR0915 ignore. |
| `.../using-bibliography/renderer.py:130` | `limitations_for` | 23 | 21/21 | Section 3.2. |
| `.../using-bibliography/renderer.py:653` | `render_pdf_with_fallback` | 18 | 77/88 | Section 3.2. |
| `.../using-bibliography/resolve.py:1179` | `main` | 66 | 118/163 | noqa PLR0912, PLR0915. |
| `.../using-bibliography/resolve.py:705` | `enrich_paper` | 18 | 25/30 | Section 3.2. |
| `.../using-bibliography/resolve.py:276` | `matches_query` | 17 | 20/22 | Section 3.2. |
| `.../using-bibliography/update_item.py:431` | `main` | 22 | 17/79 | Thin coverage. |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py:258` | `correlate` | 19 | 36/41 | Section 3.3. |
| `.../crash_recovery/jsonl.py:284` | `_classify_dispatch` | 19 | 31/38 | Section 3.3. |
| `.../crash_recovery/jsonl.py:395` | `parse_tail` | 16 | 52/59 | Section 3.3. |
| `.../crash_recovery/render.py:418` | `render` | 37 | 58/58 | noqa PLR0912. |
| `.../crash_recovery/scan.py:352` | `_walk_sessions` | 19 | 49/58 | Section 3.3. |
| `plugins/denubis-external-agents/scripts/codex_supervisor.py:472` | `_approval_options` | 20 | 27/30 | Section 3.6. |
| `.../codex_supervisor.py:2664` | `run_slash_command` | 18 | 39/44 | Section 3.6. |
| `.../codex_supervisor.py:699` | `select_codex_pane` | 18 | 24/26 | Section 3.6. |
| `.../codex_supervisor.py:2523` | `_confirm_clear` | 17 | 33/34 | Section 3.6. |
| `plugins/denubis-hook-branch-bg/hooks/branch-bg.py:262` | `assign` | 18 | 33/33 | py39 floor. |
| `plugins/denubis-hook-code-quality-guard/hooks/code-quality-guard.py:41` | `_patch_writes` | 16 | subprocess-tested | py39 floor. |
| `plugins/denubis-hook-instruction-budget/hooks/instruction-budget.py:138` | `_claude_imports` | 16 | 17/23 | py39 floor. |
| `plugins/denubis-plan-and-execute/scripts/workflow_statusline/src/workflow_statusline/__main__.py:128` | `main` | 21 | 82/83 | Per-file PLR0915 ignore. |
| `.../workflow_statusline/codex_quota.py:143` | `_dated_quota_from_rollout` | 21 | 20/27 | Section 3.4. |
| `plugins/denubis-token-estimator/scripts/estimate.py:102` | `collect_claude` | 59 | 50/56 | Per-file PLR0912 ignore. |
| `.../token-estimator/scripts/estimate.py:165` | `collect_codex` | 19 | 17/17 | Section 3.1. |
| `.../token-estimator/scripts/estimate.py:240` | `print_person` | 19 | 0/30 | No test reaches it. |
| `.../token-estimator/scripts/estimate.py:81` | `_add_claude_human_words` | 17 | 17/17 | Section 3.1. |
| `.../token-estimator/scripts/mapper.py:37` | `load` | 16 | 20/22 | Section 3.1. |
| `.../token-estimator/scripts/verify.py:249` | `claude_pass` | 107 | 105/117 | Per-file PLR0912, PLR0915 ignore. |
| `.../token-estimator/scripts/verify.py:406` | `codex_threads` | 91 | 111/115 | Per-file PLR0912, PLR0915 ignore. |
| `.../token-estimator/scripts/verify.py:578` | `codex_pass` | 31 | 61/61 | Section 3.1. |

**Hidden by configuration (not in the 58).** `scripts/test_quality.py` is a production script
whose name matches the `**/test_*.py` exclude, so complexipy skips it and ruff applies
test-only ignores to it. Running complexipy on a copy (observed) finds
`_document_path_names_in_function` at 24 and `_is_raw_text_expression` at 17. Ruff hides no
finding there today. Question 8.

### 1.5 vulture: 9 findings

Command: `uv run --frozen vulture`, exit 3.

| Location | Finding | Class | Why |
|---|---|---|---|
| `plugins/denubis-academic/skills/using-bibliography/renderer.py:199` | unused variable `attrs` | (d) | Same site as the ARG002 row. `# noqa: ARG002, V107` clears both (probe). |
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_liveness.py:221, 243` | unused variable `sig` (2) | (b) manual | Fakes for `os.kill`. `liveness.py:153` calls `os.kill(pid, 0)` positionally, so renaming to `_sig` is safe. |
| `tests/test_codex_supervisor_slash.py:1445, 1470, 1499, 1537, 1560, 1604` | unused variable `utc` (6) | (b) manual | A fixture requested for its side effect (defined at line 1377, yields None). `@pytest.mark.usefixtures("utc")` is equivalent. |

**What vulture cannot see here.** `min_confidence = 80` excludes unused functions, which
vulture reports at 60%. At 60 it reports 45 findings, 14 of them unused functions (observed).
The configured `paths` also include the tests, so a function that only tests call is never
reported. Example: `ratelimit.is_fast_burn` has no production caller (`rg` and `ast-grep`).

## 2. Mechanical pass plan

The pass has four steps: configuration, formatting, safe fixes, and the hand edits the
formatter forces. Each step changes behaviour-neutral text only.

### 2.1 What the mechanical pass must not touch

1. **Markdown.** Leave all 18 Markdown files alone until question 1 is answered.
   `anthropic-best-practices.md` stays unformatted in every case, because its body is declared
   byte-identical to upstream.
2. **`experiments/permission-queue/pending/installed_daemon.py`.** Do not format or fix it. The
   open ticket holds every fix to the installed-server experiment, and this file holds the
   value in dispute.
3. **Python under `docs/`**, until question 5 is answered.
4. **`[tool.ruff.per-file-target-version]`.** Settled. Keep every pin.
5. **No `--unsafe-fixes`.** The two unsafe fixes checked safe here (UP045 and TC003) go to
   section 3, so each lands with its own test run.
6. **No other source edits** beyond step 4.

### 2.2 Step 1: configuration

Changes to `pyproject.toml`. Each block says why.

```toml
[tool.ruff.lint.per-file-ignores]
# Add to BOTH "**/tests/**/*.py" and "**/test_*.py": complexipy already exempts
# tests, so ruff's size rules should too.
#   "PLR0915",
#   "PLR0917",

# Lazy httpx imports keep the functional core importable without httpx,
# which the tests rely on (httpx is not in the dev environment).
"plugins/denubis-academic/skills/using-bibliography/copy_item.py" = ["PLC0415"]
"plugins/denubis-academic/skills/using-bibliography/update_item.py" = ["PLC0415"]
# One return per frontmatter status, as for crash_recovery jsonl.py.
"plugins/denubis-project-notes/skills/scanning-project-notes/scripts/inventory.py" = [
    "PLR0911",
]

[tool.ty.environment]
python-version = "3.14"
# Tests and plain modules import the bibliography and estimator helpers by bare name.
extra-paths = [
    "plugins/denubis-academic/skills/using-bibliography",
    "plugins/denubis-token-estimator/scripts",
]

[tool.ty.analysis]
# Large optional dependencies, imported lazily; not installed for type checking.
allowed-unresolved-imports = [
    "pymupdf",
    "pymupdf4llm",
    "docling.**",
    "docling_core.**",
    "torch",
    "spacy",
]
```

Only if question 1 is answered yes:

```toml
[tool.ruff.format]
exclude = ["*.md"]
```

Only if question 4 is answered yes, a configuration-only rule that leaves the file untouched:

```toml
"experiments/permission-queue/pending/*.py" = ["S101"]
```

Only if question 3 chooses suppression, add `"httpx"` to `allowed-unresolved-imports`.

The script-level part, in one of two forms (question 2). Option A goes in the metadata block
of each of the 13 scripts that need it: the 11 `using-bibliography` scripts with PEP 723
headers, `annotated-bibliography/check.py` and `academic-writing/prose_shape.py`.

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "pymupdf"]
#
# [tool.ty.environment]
# extra-paths = ["."]
#
# [tool.ty.analysis]
# allowed-unresolved-imports = ["pymupdf"]
# ///
```

`check.py` would need `extra-paths = ["../using-bibliography"]`; that relative form was not
checked. `prose_shape.py` needs only `allowed-unresolved-imports = ["spacy"]`. Option A was
verified on `annotate.py` only.

Option B goes in `scripts/lint.sh` and leaves the scripts untouched:

```bash
run "ty check" uv run --frozen ty check \
    -c 'environment.extra-paths=["plugins/denubis-academic/skills/using-bibliography","plugins/denubis-token-estimator/scripts"]' \
    -c 'analysis.allowed-unresolved-imports=["pymupdf","pymupdf4llm","docling.**","docling_core.**","torch","spacy"]'
```

With option B, a plain `ty check` or an editor would still report the 40 script imports.

Also correct the baseline comment in `pyproject.toml` to the HEAD values: 40 unformatted files
and 58 functions over 15.

No `[tool.vulture]` change. An `ignore_names` entry would also hide future real hits on `utc`
and `sig`. The code fixes in section 3 are smaller and exact.

**Effect of step 1:**

| Check | Before | After | Evidence |
|---|---|---|---|
| ruff check | 81 | 73 | Observed in the scratch copy. Removes PLC0415 (5), PLR0917 (1), PLR0915 (1), PLR0911 (1). |
| ty, `pyproject.toml` part only | 184 | about 158 | Scratch copy reported 160. Two are scratch-only duplicates, caused by the workspace package existing at both the scratch path and the repository path. |
| ty, with the script part | 184 | 120 | Observed in the repository with the equivalent `-c` flags. Includes the 4 new `collection.py` diagnostics. |
| ty, also allowing httpx | 184 | 101 | Observed with `-c`. |

The 21 module names on the two extra paths shadow no standard-library or installed module, and
no name appears on both paths (checked with `sys.stdlib_module_names` and
`importlib.util.find_spec`).

### 2.3 Step 2: format 20 Python files

Use an explicit file list, so the held files and the Markdown stay out whatever question 1
decides:

```bash
uv run --frozen ruff format \
  plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_classify.py \
  plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_jsonl_tail.py \
  plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_note.py \
  plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_plugin_manifest.py \
  plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py \
  plugins/denubis-external-agents/scripts/update_codex_profile.py \
  plugins/denubis-hook-instruction-budget/hooks/instruction-budget.py \
  plugins/denubis-project-notes/skills/scanning-project-notes/scripts/inventory.py \
  scripts/test_quality.py \
  tests/skill-evals/plan-and-execute/checkpoint-uat/fixture/greeting.py \
  tests/skill-evals/plan-and-execute/outcome-planning/fixture/greeting.py \
  tests/test_bibliography_copy.py \
  tests/test_hook_launcher_cwd_independence.py \
  tests/test_hook_portability.py \
  tests/test_instruction_budget_guard.py \
  tests/test_instruction_delivery.py \
  tests/test_paper_review_skill.py \
  tests/test_skill_reference_integrity.py \
  tests/test_test_quality.py \
  tests/test_update_codex_profile.py
```

What changes in each file, and which tests cover it, is in the Python table in 1.2.

### 2.4 Step 3: safe fixes

```bash
uv run --frozen ruff check --fix --extend-exclude experiments/permission-queue/pending .
```

This applies two I001 fixes, each removing one blank line: `inventory.py:4` and
`tests/test_project_notes_inventory.py:3`. The third safe fix, in `installed_daemon.py`, is
excluded.

### 2.5 Step 4: hand edits that the formatter forces

Docstring, message and comment text only.

| File, line after formatting | Edit |
|---|---|
| `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_classify.py:29` | Shorten the docstring to 88 characters or fewer. |
| `.../tests/test_jsonl_tail.py:102, 158` | Same. |
| `.../tests/test_note.py:217` | Same. |
| `.../tests/test_plugin_manifest.py:49` | Same. |
| `tests/test_hook_portability.py:168` | Shorten the assertion message. |
| `plugins/denubis-academic/skills/using-bibliography/renderer.py:199` | Add `# noqa: ARG002, V107` (clears one ruff and one vulture finding). |
| `tests/test_hook_launcher_cwd_independence.py:154` | Add `# noqa: S602` with the reason: it runs `hooks.json` strings through a shell, as Claude Code does. |

### 2.6 Evidence that the pass preserves behaviour

1. **Baseline at HEAD:** 2270 passed, 14 skipped.
2. **Planned state:** a scratch copy (`git archive HEAD` into `/tmp/lintaudit-20261021/sim`)
   with step 1's ruff and ty settings, step 2's 20-file format and step 3's fixes gave 2270
   passed and 14 skipped under `uv run --frozen --project <repo> pytest -q -p
   no:cacheprovider`. A second scratch run that formatted all 40 files gave the same result.
3. **The scratch tests exercised the formatted files.** Script tests locate their targets from
   their own path (`Path(__file__).resolve().parents[1]`). The two workspace packages,
   `crash_recovery` and `workflow_statusline`, imported from the repository, but formatting
   changes none of their source files, only their tests.
4. **Runtime floors hold after formatting.** Every hook compiles under Python 3.9,
   `update_codex_profile.py` under 3.10, and the 14 pinned files plus `inventory.py` under
   3.11. Command shape: `uv run --offline --no-project --python 3.x python -I -c
   'compile(...)'`.
5. **Not covered by a test:** the two skill-eval `greeting.py` fixtures (one trailing blank
   line each), and step 4's text edits, which only the tests themselves exercise.

After the real pass, verify with a bare `uv run --frozen pytest`, not the pre-commit hook,
which skips 498 tests. Then run `scripts/lint.sh`.

**Known intermittent failures (observed on 2026-10-22, unrelated to any lint change).** Two
Textual tests in the permission-queue suite fail now and then under full-suite load, with no
code or test changed in the tree:

| Test | Seen failing | Alone |
|---|---|---|
| `tests/test_permission_queue_board.py::test_watch_latest_text_and_refresh_preserve_actual_reading_position` | 3 of 12 full runs. The one traceback captured stops at line 1020, which asserts the view reached the bottom after one `pilot.pause()`. | 12 of 12 passed |
| `tests/test_permission_queue_daemon_ui.py::test_ctrl_c_closes_view_and_main_releases_daemon_connection` | 1 of 12 full runs | not run alone |

One further full run failed one test whose name was not captured. The cause was not
established. Machine load from other sessions is a plausible factor but
was not measured. A single failure of either test after the pass is therefore not evidence
against it; rerun before concluding. A repeatable failure is.

### 2.7 Expected state after the mechanical pass

| Check | Value | Basis |
|---|---|---|
| ruff check | 69 after steps 1 to 3; 61 after step 4 | 69 observed in the scratch copy. 61 inferred: step 4 removes 6 E501, ARG002 and S602. |
| ruff format | 2 Python files (the held ones), plus 18 Markdown unless question 1 excludes them | Observed in the scratch copy. |
| ty | 120, or about 158 without the script part | Section 2.2. |
| complexipy | 58 | Unchanged by design. |
| vulture | 8 | Inferred from the `V107` probe. |

The 61 remaining ruff findings: `installed_daemon.py` 37, `phase_05_cross_ref_audit.py` 5,
UP045 7, PLR0917 4, PLR0912 2, PLR0915 1, PLR0911 1, TC003 1, S112 1, RUF012 1, PLW2901 1.

## 3. Judgement pass plan, one plugin at a time

Rules for every plugin:

- **Runtime floors:** hooks must parse on 3.9. The 14 pinned bibliography files must stay
  valid on 3.11: one exception per `except` clause, no `typing.override`.
  `update_codex_profile.py` must stay valid on 3.10.
- **Tests first where coverage is thin.** Write a characterisation test that pins today's
  output before splitting a function with low coverage (red, green, refactor).
- **Run the bare suite.** The pre-commit hook skips the token-estimator, crash-recovery and
  status-line tests.
- **Releases:** a change that alters shipped behaviour needs the version, marketplace entry
  and changelog updates that CLAUDE.md requires. A pure refactor needs a decision on whether
  to release.

Recommended order, by value and safety: token-estimator, crash-recovery, plan-and-execute,
hooks, external-agents, academic, permission-queue. The first three have strong coverage and
small surfaces. Academic is largest and has three untested entry points. Permission-queue is
partly held by open tickets.

### 3.1 denubis-token-estimator

Tests: `plugins/denubis-token-estimator/tests/` (four modules). The commit gate does not run
them.

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `verify.py:249 claude_pass` | 107 | `_iter_records(fp)` yielding parsed lines; `_ClaudeTokenTally` with `observe(record, is_subfile)` and `totals()`; `_HumanWordTally` with `observe(record, fp)`, `_user_texts(record)` and `_keep_largest()`; `_cross_attribution(ids, cwds_all)` | 105/117; `test_token_estimator_passes` | Medium. This is the audit harness, and its docstring asks for independence from the estimator. `estimate.py` already imports it as `V`, so sharing more helpers couples the report to its audit. `cwd_atmax` (lines 255 to 303) is computed and never returned; question 9. |
| `verify.py:406 codex_threads` | 91 | A `CodexThread` dataclass replacing the dict, which also clears the 12 ty diagnostics; `_read_codex_thread(fp)`; `_counter_mode(thread)`, pure; `_replay_split(events, task_seq)`; `_parent_at_fork(thread, parent)`; `_owned_events(thread, baseline, mode)` | 111/115; `estimate` and `passes` tests | Medium. `estimate.collect_codex` and `windowed_output` read the dict keys, so all consumers change together. |
| `verify.py:578 codex_pass` | 31 | `_codex_totals(threads)`, `_codex_human_words(threads)`, `_replay_anomalies(subs)` | 61/61 | Low. |
| `estimate.py:102 collect_claude` | 59 | `_observe_assistant(state, record, is_sub)` over a small `_ClaudeOrigins` state object; `_binds_cwd(out, current_max, cwd, previous_cwd, seen)`, pure; `_emit_claude_leaves(leaves, attr, state, start, end)` | 50/56 | Medium. The cwd tie-break decides attribution. Give `_binds_cwd` a property test before moving it. |
| `estimate.py:165 collect_codex` | 19 | `_codex_month(fp, start)`, `_codex_human_words(thread, start, end)` | 17/17 | Low. |
| `estimate.py:240 print_person` | 19 | `_project_totals(rows, person, project)`, `_print_project_row(...)` | 0/30 | Medium: untested output. Add an output test first. |
| `estimate.py:81 _add_claude_human_words` | 17 | `_count_block_words(blocks)`, `_in_window(when, start, end)` | 17/17 | Low. |
| `mapper.py:37 load` | 16 | `_read_mapper(f)`, `_claim_paths(claimed, paths, owner, f)` | 20/22 | Low. |

### 3.2 denubis-academic

Tests: `tests/test_bibliography_*.py` and `tests/test_academic_*.py`. Constraints: 14 pinned
py311 files; lazy httpx imports are load-bearing; the write helpers go through `write_gate`
and must keep the preview-then-apply order.

Defects and small fixes:

| Item | Class | Fix | Tests |
|---|---|---|---|
| `copy_item.py:338` S112 | (a) | Report a skipped library on stderr, or keep silent (question 11). | Add a `find_items` test with one failing library. |
| `zotero_local_api.py:566` inner `send()` | (a) | Annotate `-> tuple[WriteResult, int]`. | `tests/test_bibliography_zotero_local_api.py`. |
| `zotero_local_api.py:387` `doi_citekeys` | (a) | Annotate `items: Sequence[dict]`. | Same. |
| `collection.py:333, 414, 502, 511`; `register_export.py:331` | (e) | Question 13. | `test_bibliography_collection.py`, `test_bibliography_register_export.py`. |
| `renderer.py:176` RUF012 | (b) | `frozenset`. | `test_bibliography_renderer.py`. |
| `update_item.py:416` PLW2901 and `:445` lazy import | (b) | Rename the loop variable; join the top-level import. | `test_bibliography_update.py`. |

Complexity:

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `resolve.py:1179 main` | 66 | `build_parser()`; `_classify_query(args)`; `_validate_args(args) -> str \| None`; `_search_papers(args, keys)` returning papers, near matches and search errors; `_filter_papers(papers, keys, library)`; `_report_paper(paper, args, library_map)`; `_report_near(near)`; `_make_citeable(args, ...)` | 118/163; `test_bibliography_resolve` drives `main` through argv | High. Exit codes 0, 1 and 2 and the printed text are the contract. Pin each branch's exit code and output first. |
| `ingest.py:197 main` | 32 | `_read_dois(args)`, `_mocr_context(args, cfg)`, `_ingest_one(doi, ...)` | 69/98; `test_bibliography_ingest` | Medium. The per-DOI `except Exception` keeps a batch going; keep it. |
| `collection.py:448 restore_collection` | 29 | `_load_descendants(library, listed)`, `_apply_restore(...)`, `_verify_restored(...)` | 62/74; `test_bibliography_collection` | Medium: a Zotero write path. |
| `collection.py:230 create_collection` | 18 | `_resolve_parent(args, library)`, `_verify_created(...)` | 41/54 | Medium: write path. |
| `collection.py:369 trash_collection` | 16 | `_verify_trashed(library, keys)` | 58/66 | Medium: write path. |
| `fetch.py:332 main` | 25 | `_resolve_target(args, libraries)`, `_fetch_all(args, target)`, `_render_fetched(args, results)` | 0/90 | High: no test reaches it. Add CLI tests first. |
| `fetch.py:103 _find_library` | 20 | Replace with `copy_item.find_library`, or keep (question 10) | 19/27; `test_bibliography_fetch` | Medium: consolidation changes accepted inputs. |
| `copy_item.py:111 find_library` | 24 | `_user_library(libraries)`, `_library_by_number(libraries, n)`, `_library_by_name(libraries, name)` | 22/27; 7 test modules | Medium: six scripts import from `copy_item`. |
| `copy_item.py:378 main` | 19 | `_resolve_destination(args, libraries)`, `_print_attachment_report(result)` | 0/81 | High: no test reaches it. |
| `update_item.py:431 main` | 22 | `_list_collection(args)`, `_resolve_update_target(args)`, `_print_update_result(response, lost)` | 17/79 | High: thin coverage. |
| `create_item.py:73 verification_problems` | 19 | `_field_problems`, `_creator_problems`, `_collection_problems` | 18/20 | Low. |
| `renderer.py:653 render_pdf_with_fallback` | 18 | `_run_cascade(...)`, `_try_mocr(...)` | 77/88 | Medium: renderer order is behaviour. |
| `renderer.py:130 limitations_for` | 23 | `_scan_limitations(description)`, `_replacement_char_limitations(pages)` | 21/21 | Low. |
| `resolve.py:705 enrich_paper` | 18 | `_collections_for(citekey)`, `_pdf_status(paper, library_map)` | 25/30 | Low. Its `except Exception` maps failures to "unknown" on purpose. |
| `resolve.py:276 matches_query` | 17 | `_author_matches(paper, author)` | 20/22 | Low. A good property-test candidate for diacritic folding. |
| `annotated-bibliography/check.py:18 check` | 35 | `_require_entry_fields(entry)`, `_require_current_render(meta, entry)`, `_point_failure(index, point, page_count, paper_dir)` | Subprocess-tested: one success path and ten failure paths, but failures assert only the exit code | Medium. Validation order decides which message wins, and no test would notice a reorder. Add message assertions first. |
| `literature-scout/search.py:65 build_request` | 23 | `_crossref_datacite_request(...)`, `_semantic_scholar_request(...)` | 34/38 | Low. |
| `academic-writing/prose_shape.py:164 split_markdown` | 21 | A small section builder with `add_heading` and `add_line` | 34/34 | Low. |
| `prose_shape.py:600 _section_table` | 19 | `_table_header(t)`, `_table_row(name, shape, kinds, t)` | 38/40 | Low. |
| `prose_shape.py:462 _analyse_section` | 20 | `_sentence_hits(sent, text, previous, targets)` | 0/39 | High: needs spaCy, and all 14 dependent tests skip here. |
| `prose_shape.py:340 _structural_hits` | 16 | One predicate per pattern, in a table | 0/29 | High, for the same reason. |

### 3.3 denubis-crash-recovery

Tests: the plugin's own suite. The commit gate does not run it.

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `render.py:418 render` | 37 | `_read_render_rows(db_path)`, `_group_by_section(rows)`, `_lean_rows(section, rows, collapsed)`, `_render_section(section, rows)`, `_render_markers(markers)`, `_render_collapsed(collapsed, total)` | 58/58; `test_render`, `test_note` | Low. Output must stay byte-identical (AC3.2 in its docstring), and the tests compare rendered text. |
| `correlate.py:258 correlate` | 19 | `_direct_session_match(...)`, `_resume_match(...)`, `_tight_window_candidates(...)` | 36/41 | Medium: the precedence of the three matches is the contract. |
| `jsonl.py:284 _classify_dispatch` | 19 | `_ask_question_outcome(...)`, `_dispatch_outcome(...)` | 31/38 | Medium. |
| `jsonl.py:395 parse_tail` | 16 | `_read_tail(path, n)`, `_parse_lines(tail)` | 52/59 | Low. |
| `scan.py:352 _walk_sessions` | 19 | `_correlate_marker(liveness, snapshots)`, `_abnormal_exit_fact(liveness, boot_id)`, and `_consider` as a small class | 49/58; `test_scan` | Medium: precedence ranking and the UNIQUE constraint in its docstring. |

Also: replace `scan_db.py`'s `conn: object` with a `Protocol` (1.3.2), and rename `sig` to
`_sig` in `tests/test_liveness.py:221, 243`.

### 3.4 denubis-plan-and-execute (workflow_statusline)

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `__main__.py:128 main` | 21 | `_location_cells(cwd)`, `_rate_limit_cells(rate_limits, now)`, `_line_two(...)` | 82/83; `test_main`, `test_bar` | Low. |
| `codex_quota.py:143 _dated_quota_from_rollout` | 21 | `_event_time(event)`, `_quota_snapshot(event)` | 20/27 | Low. |

Also: PLR0917 on `cache.py:132` and `ratelimit.py:290` (question 7), and `is_fast_burn`
(question 14).

### 3.5 Hooks: branch-bg, code-quality-guard, instruction-budget, gh-fork-guard

All must stay valid on Python 3.9: no `match`, and no runtime PEP 604 unions.

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `branch-bg.py:262 assign` | 18 | `_wanted_names(names)`, `_pinned_slots(wanted)`, `_hashed_slot(name, slots)` | 33/33; `test_branch_bg` | Low. |
| `code-quality-guard.py:41 _patch_writes` | 16 | A small patch parser with `on_file`, `on_move`, `on_end` and `on_added_line` | Subprocess-tested by `test_code_quality_guard` | Medium: no line figure, because tests run the hook as a process. |
| `instruction-budget.py:138 _claude_imports` | 16 | `_visible_lines(text)` for fence tracking, `_resolve_import(raw, base, home)` | 17/23 | Low. |

Also: apply UP045 and the resulting F401 with `uv run --frozen ruff check --select UP045,F401
--unsafe-fixes --fix plugins/denubis-hook-instruction-budget/hooks/instruction-budget.py`, then
run `tests/test_instruction_budget_guard.py` and `tests/test_hook_portability.py`. Optionally
pass the allowed repository into `gh-fork-guard.repo_is_allowed` as a parameter, which removes
the ty finding at line 142. Note that `gh-fork-guard.py main` sits at exactly 15.

### 3.6 denubis-external-agents

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `codex_supervisor.py:472 _approval_options` | 20 | `_option_block(lines, columns)`, `_collect_options(lines, start, end, columns)` | 27/30; `test_codex_supervisor_approve` | Medium: parses Codex screen text. |
| `codex_supervisor.py:2664 run_slash_command` | 18 | `_run_clear(...)`, `_run_compact(...)` | 39/44 | Medium. |
| `codex_supervisor.py:699 select_codex_pane` | 18 | `_parse_pane_row(line)` | 24/26 | Low. |
| `codex_supervisor.py:2523 _confirm_clear` | 17 | `_poll_once(target, previous_id)` | 33/34 | Medium: a timing loop. |

Also: explicit `tomlkit.exceptions` imports in `update_codex_profile.py:93` and
`tests/test_update_codex_profile.py:108`; `@pytest.mark.usefixtures("utc")` for the six
vulture findings in `tests/test_codex_supervisor_slash.py`.

### 3.7 experiments/permission-queue (shipped)

Two open tickets bear on this area. "Standalone viewer Open source target" holds changes to
`tmux_source.py:open_source`. "Isolated Codex two-client approval test retry" holds every fix
and retry of the installed-server experiment, which covers `pending/`. The items below avoid
both.

| Function | Score | Proposed helpers | Coverage and tests | Risk |
|---|---|---|---|---|
| `codex_server.py:311 CodexServer::_snapshot` | 36 | `_read_thread(thread_id, deadline)`, `_recent_turns(thread_id, deadline)`, `_thread_state(status)`, `_pending_requests(thread_id)`, `_since(state, requests, turns)`, `_parent_thread(thread)` | 65/73; `test_permission_queue_codex_server`, `test_permission_queue_daemon_ui` | Medium: daemon protocol parsing. |
| `codex_server.py:198 CodexServer::_handle` | 24 | `_handle_resolved(params)`, `_handle_request(message, params)` | 34/42 | Medium. |
| `tmux_source.py:442 TmuxSource::conversation` | 24 | `_item_line(item)` | 11/22 | Medium: half its lines never run. Add tests first. |
| `tmux_source.py:331 TmuxSource::snapshots` | 17 | `_codex_threads()`, `_snapshot_row(row, threads)` | 83/84 | Low. |
| `codex_pane_state.py:92 rollout_time` | 20 | `_read_stable_tail(path)`, `_latest_turn_event(raw)` | 27/32 | Low. |
| `board.py` five `WindowBoard` methods, 16 to 18 | 16 to 18 | `refresh_windows`: `_choose_selection()`. `render_source_list`: `_visible_panes()`, `_table_row(pane)`. `show_source`: `_load_source(snapshot)`, `_restore_scroll()`. `queue_input`: `_answer_for(key, request)`. `update_input_status`: `_input_status_text()` | 22/24 to 47/47 | Medium: Textual UI state across async callbacks. |

Also: add the `is not None` guard at `board.py:1630` (a). For the 12 `type()` guard
diagnostics (c), choose between `isinstance` with a `bool` exclusion and an inline ty ignore.

### 3.8 Top-level scripts, docs and tests

- `scripts/test_quality.py`: two hidden hotspots, 24 and 17. Question 8.
- `docs/`: five hotspots, five E501 and three ty findings. Question 5.
- Tests: 56 ty findings. The (b) items are short manual edits. The (d) items wait on
  question 6.

## 4. Open questions for the human

Each question names the decision it blocks.

1. **Should `ruff format` skip Markdown files, by adding `exclude = ["*.md"]` under
   `[tool.ruff.format]`?** Blocks: whether the 18 Markdown files enter the mechanical pass.
   Fifteen are historical plans, three are shipped skill or agent prompts, and one of those
   is declared byte-identical to upstream.
2. **Should the 13 PEP 723 scripts carry their own `[tool.ty]` table in their metadata block,
   or should `scripts/lint.sh` pass the same settings as `ty check -c` flags?** Blocks: how ty
   resolves the 40 sibling imports inside scripts, which `pyproject.toml` settings do not
   reach.
3. **Should `httpx` be added to the dev dependency group so ty checks its 19 call sites, or be
   listed in `allowed-unresolved-imports`?** Blocks: the 19 httpx diagnostics. Adding it
   changes `uv.lock` and installs through the uv cache. The four test files that touch httpx
   inject fakes through `sys.modules`; whether any test relies on httpx being absent was not
   checked.
4. **May the mechanical pass add a configuration-only rule that lints
   `experiments/permission-queue/pending/` as test code, leaving the file untouched until the
   Codex-retry ticket is answered?** Blocks: the 17 S101 findings there.
5. **Should Python under `docs/` be excluded from ruff, ty, complexipy and vulture?** Blocks: 5
   E501, 3 ty and 5 complexity findings, and one file's formatting. Note that
   `branch-bg-colour-eval.py` is the live generator cited by the branch-bg architecture page,
   `backtest.py` has a documented bug, and `phase_05_cross_ref_audit.py` belongs to a finished
   plan.
6. **Should ty check tests at full strictness, or should a `[[tool.ty.overrides]]` for test
   paths ignore `unresolved-attribute` and `invalid-assignment`?** Blocks: 39 of the 56 test
   diagnostics, which come from monkeypatching idioms. With that override, ty falls from 120 to
   81 (observed with `-c`).
7. **Should PLR0917 join PLR0913 in the global ignore list, or should the four shipped
   functions take keyword-only trailing parameters?** Blocks: four findings. Every current
   caller already passes the trailing arguments by keyword.
8. **Should `scripts/test_quality.py` be renamed, or the test globs narrowed, so the
   complexity gate sees it?** Blocks: two hidden hotspots, at 24 and 17.
9. **Should `verify.py`'s `claude_pass` drop its unused `cwd_atmax` tracking, or be extended to
   re-derive and compare `estimate.py`'s cwd binding?** Blocks: the `claude_pass`
   decomposition. The two rules differ today: `estimate.py` binds the first occurrence, and
   `verify.py` does not.
10. **Should `fetch.py` use `copy_item.find_library`, or keep its own group-only resolver?**
    Blocks: the `fetch.py` decomposition. Consolidating would let `fetch.py` accept libraryID
    numbers and non-group library names. `update_item.py` records that resolution was
    centralised because a hand-rolled copy broke.
11. **When one library's search fails in `copy_item.find_items`, should the helper name the
    skipped library on stderr?** Blocks: the S112 fix.
12. **Should the pre-commit pytest hook run the configured testpaths (2284 tests) instead of
    `tests/` (1786 tests)?** Blocks: whether the commit gate covers the token-estimator,
    crash-recovery and status-line refactors.
13. **Should a missing identity field in a Zotero response, a collection version or a
    libraryID, be an explicit error?** Blocks: fixes for `collection.py:333, 414, 502, 511`
    and `register_export.py:331`.
14. **Should `ratelimit.is_fast_burn`, which has no production caller, be deleted, kept for a
    planned use, or wired in?** Blocks: its PLR0917 fix.
