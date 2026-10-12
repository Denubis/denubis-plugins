# Work completed

## 2026-10-12 — Planning evidence (no implementation yet)

Established while writing `plan.md`; every item is an observation, not a claim about
planned behaviour.

- Worktree `worktree-bibliography-0.19-design` holds the design, ADR 0028, and the ADR
  README index line uncommitted (`git status --short`: `M docs/architecture/decisions/README.md`,
  two untracked files). No other dirty state.
- `.notes/project_open-questions.md` carries no ticket bearing on this work (one parked
  messaging item only).
- Live Zotero 10 on this machine: `curl -s -D - -o /dev/null http://localhost:23119/api/`
  returns `Zotero-Server-ID: g6bzZS56RsjG`.
- `GET /api/users/0/items/D7IV2YRB?format=json`: `data.deleted` is `true`, `version` 429,
  title "Technology and the character of contemporary life: …" (the 1987 Borgmann record).
- `~/zettelkasten/papers/borgmannTechnologyCharacterContemporary1987/meta.json`:
  `render_version 2, page_count 16, pymupdf4llm, ocr false, source_pdf
  /home/brian/Zotero/storage/XCGCBRF7/Borgmann - 1987 - Technology and the character of contemporary life a philosophical inquiry.pdf`.
  Prior-chat search (`cc-search-chats search "16-page Word PDF" --literal`) resolved the
  design's "16-page Word PDF" to this attachment: assistant messages of
  2026-10-10T23:37Z and 2026-10-11T00:30Z in session `e65bf924-…` describe it as the
  Word-made PDF with a native text layer.
- `~/zettelkasten/papers/borgmannTechnologyCharacterContemporary2006/meta.json`:
  `render_version 2, page_count 311, pymupdf4llm, ocr false, source_pdf
  /home/brian/Zotero/storage/XD39JLVP/Borgmann - 2006 - Technology and the character of contemporary life a philosophical inquiry.pdf`.
- `tests/test_bibliography_renderer.py:152` asserts `render_metadata_is_current({"renderer": "mocr", "ocr": True})`
  is true; Q4 inverts that for a version-2 record, so this assertion changes with the
  predicate.
- Astra review of the first plan draft (2026-10-12, pasted by Brian) raised three
  boundary findings; each verified here before the plan was repaired:
  - Installed `server_localAPI.js:993-995` calls `getByParent`/`getByLibrary` without
    `includeTrashed`; no `/collections/trash` route exists (`:1191-1195` is items only);
    `collection.js:205-210` filters `deleted` children by default. Restore therefore
    takes `--descendants` from the trash-time output (plan deviation 4).
  - BBT `content/collection.ts` (upstream master, fetched 2026-10-12) requires an
    absolute `/<library>/<path>` string and matches an all-digit library segment by
    `libraryID`/`groupID`; the helper builds `/<libraryID>/<names>` (deviation 6).
  - `resolve.check_rendered` (`resolve.py:1294`) and `ingest.py:269` bypass the cache
    only on `--force`; `--force-ocr` now also bypasses it in both (deviation 5).
- zotero-api-plus `run-autoexport` reports only `triggered` and never success
  (`~/people/Brian/zotero-api-plus/src/utils/run-autoexport.ts:6-12`), matching the
  design's completion/content split.

## 2026-10-12 — Outcome A: extraction record, forced OCR, quoting contract

Baseline before any edit: `uv run pytest tests/test_bibliography_*.py -q` → 315 passed.

Changed surfaces:

- `renderer.py`: `RENDER_VERSION = 3`; `render_metadata_is_current` is a version
  equality for every renderer; new `describe_pdf`, `limitations_for`,
  `extraction_label`, `suggests_forced_ocr`; `_write_outputs` takes keyword-only
  `extraction`, `forced`, `limitations`; `render_pdf_with_fallback(force_ocr=)` runs
  only the OCR tier (or goes straight to mocr with a session); HTML and Pandoc records
  say `converted`.
- Deviation found by the Q3 synthetic probe: Docling's default OCR mode keeps the PDF's
  own text cells and merges OCR of bitmap regions into them, so the first forced render
  still carried the hidden layer's words. The forced tier now passes
  `EasyOcrOptions(mode=OcrMode.FULL_PAGE)` (`_render_with_docling(full_page_ocr=True)`);
  verified on the installed docling 2.130.0 (`OcrMode` members printed) and by the
  rerun below. The ordinary escalation tier keeps Docling's default mode.
- `render.py`, `ingest.py`, `resolve.py`: `--force-ocr`; the cache is bypassed when it is
  set in both entry points; `resolve._render_cmd`/`render_via_subprocess` forward it;
  `resolve.print_match` reads `out_dir/meta.json` (`read_render_record`,
  `render_state_detail`) and prints `state: rendered (<extraction>; <first limitation>)`
  plus an `advice:` line when `suggests_forced_ocr`.
- `blockquote.py`: every hit ends `Verification: located (render match; check the source
  page before calling it verified)`; `NO MATCH` prints `Verification: unverified` to
  stderr before exit 2.
- Consumer outside the plan's file list: `annotated-bibliography/check.py` keyed
  `visual_verification_required` on `meta["ocr"]`, which contradicts Contract 1. It now
  requires `extraction` in the record and reports `quotation_state: located`,
  `source_verification_required: true`, `extraction`, `forced`, `limitations`.
  `tests/test_academic_literature_helpers.py` and
  `annotated-bibliography/references/entry-contract.md` updated with it;
  `paper-review/references/source-fidelity.md` and
  `annotated-bibliography/references/review-and-revision.md` lost their OCR-only wording.
- Docs: `SKILL.md` (quoting rule as Contract 1, completion evidence names the quotation
  state), `references/reading-and-quoting.md`, `notes-and-bibliographies.md`,
  `resolve-and-render.md` (meta contract, forced OCR, version 3 re-render),
  `troubleshooting.md`, `annotated-bibliography/SKILL.md`.
- Tests: `tests/test_bibliography_renderer.py` (five-renderer staleness in both cache
  readers, record keys, forced cascade, full-page OCR option, `limitations_for` shapes,
  `describe_pdf` with stubbed pymupdf, converted records), `tests/test_bibliography_resolve.py`
  (`--force-ocr` in the command, state line and advisory, `main()` re-renders a current
  version-3 cache with `--force-ocr` and a positive control without flags does not),
  `tests/test_bibliography_ingest.py` (same pair through `ingest.main`),
  `tests/test_bibliography_blockquote.py` (new, subprocess).

Evidence:

- `uv run pytest tests/test_bibliography_renderer.py tests/test_bibliography_resolve.py tests/test_bibliography_ingest.py tests/test_bibliography_blockquote.py -q`:
  34 failed / 110 passed before the implementation (red for the intended reasons; the
  resolve positive control failed only because its version-3 fixture was stale under
  version 2), then all pass. Full `tests/test_academic_literature_helpers.py tests/test_bibliography_*.py tests/test_skill_*.py tests/test_paper_review_skill.py`:
  972 passed.
- `uvx ruff check` on the touched files: only the three pre-existing renderer.py findings
  (RUF012 `_SnapshotText.BLOCKS`, ARG002 `attrs`, PLR0917 on `_write_outputs`, present on
  the base commit; the positional count fell from 7 to 6). Touched files are
  `ruff format`-clean. Pre-existing findings in `copy_item.py` and `update_item.py` were
  left alone (not owned by this outcome).
- Q1 (`render.py` on `XD39JLVP/Borgmann - 2006 - ….pdf` → `/tmp/bib019/borgmann2006`):
  `render_version 3, page_count 311, pymupdf4llm, ocr false, extraction "text-layer",
  forced false, limitations ["311 of 311 pages carry a page-sized image; the text layer
  is likely third-party OCR (producer: Adobe Acrobat 9.55 Paper Capture Plug-in)",
  "7 pages have no extractable text"]`, exit 0.
- Q2 (`XCGCBRF7/Borgmann - 1987 - ….pdf` → `/tmp/bib019/borgmann1987`): `render_version 3,
  page_count 16, pymupdf4llm, ocr false, extraction "text-layer", forced false,
  limitations []`, exit 0.
- Q3 synthetic (`/tmp/bib019/synthetic.pdf`: page image rendered from "IMAGEWORD alpha
  bravo charlie / the picture says delta echo", invisible layer "LAYERWORD foxtrot golf
  hotel / the layer says india juliet", `insert_text(render_mode=3)`): without the flag
  `pages/001.md` is the layer's words only (`LAYERWORD foxtrot golf hotel`); with
  `--force-ocr` (after the FULL_PAGE fix) it is `IMAGEWORD alpha bravo char the picture
  says delta echo` and contains no `LAYERWORD`, record `docling, ocr true, extraction
  "ocr", forced true`. Before the fix the forced page carried both sets of words.
- "in tum" in the text-layer render of Borgmann 2006 (`/tmp/bib019/borgmann2006/pages`):
  29 occurrences on 28 pages (013 023 024 042 045 050 051 052 062 095 119 120 132 136 139
  140 150 154 172 176 188 192 193 201 211 220 251 256); "Jiving" on 205. The previous
  version-2 cache was copied to `/tmp/bib019/borgmann2006-previous-cache` before the
  live forced run.
- Q3 live: `uv run resolve.py --citekey borgmannTechnologyCharacterContemporary2006
  --force-ocr` (log `/tmp/bib019/forced2006.log`) went through the front door with a
  current version-3-equivalent cache bypassed, ran `docling +OCR OK: 311 pages, 6
  near-empty, 0 U+FFFD`, exit 0, and the state line now reads `rendered (ocr, forced;
  311 of 311 pages carry a page-sized image; …)` with no advice line. In the forced
  render "in tum" remains on 2 pages (192, 201) and "in turn" now appears on the other
  26 former slip pages; "Jiving" on 205 is gone ("living" present). Render kept at
  `~/zettelkasten/papers/borgmannTechnologyCharacterContemporary2006/` (meta: `docling,
  ocr true, extraction "ocr", forced true`).

Checkpoints: `8590878` (design, ADR 0028, README index, plan directory), `9c87200`
(Outcome A).

## 2026-10-12 — Outcome B: trash awareness and the read-only listing

Changed surfaces:

- `zotero_local_api.py`: `item_in_trash`, `library_base`, `_fetch_all_pages` (shared
  pagination), `fetch_search_page(include_trashed=)`, `search_items(include_trashed=)`
  through `_sweep`, `get_collection_items(library, key, *, include_trashed=True)` listing
  `/collections/<key>/items` (children included) and raising `LibraryQueryError`,
  `summarise_collection` (one row per parent, attachments grouped, linked-URL
  attachments named by title).
- `resolve.py`: `Paper.in_trash`; `paper_from_local_item` sets it;
  `search_papers(include_trashed_for=)` and `main` pass the exact citekey only;
  `print_no_match(trash_excluded=)` for author/title/DOI; trashed copies print
  `state: in trash` with collections and attachment `(not checked: item is in the
  trash)` (`trashed_info`), are never rendered, and the run exits 1 only when every
  copy is in the trash.
- Deviation found live: the design's T1 scenario had one (trashed) copy; Zotero now
  holds three items with the citekey `borgmannTechnologyCharacterContemporary1987` in
  My Library (5N8ATYMZ live, two trashed including D7IV2YRB). Two consequences: (a)
  `enrich_paper` aggregates collections and attachments by citekey through BBT, so a
  trashed row would have borrowed the live copy's attachment; trashed rows are no
  longer enriched. (b) exit 1 with a live copy resolved would hide the usable paper, so
  the exit is 1 only when no live copy resolved. Both are recorded in
  `references/resolve-and-render.md` and tested (`test_main_exits_0_when_a_live_copy_sits_beside_trashed_ones`,
  `test_print_match_reports_in_trash_without_borrowing_live_facts`). This is a
  judgement call on a case the design did not cover; raised in the report.
- `copy_item.py`: `probe_api_plus()` split out of `probe_copy_item()` (which now calls
  it) so helpers that only resolve names through `/api/plus/libraries` share the probe.
  `ruff format` also normalised pre-existing hunks of `copy_item.py` and `update_item.py`
  (formatter-only).
- `update_item.py`: `--list` consumes the shared listing with the trash included,
  `summarise_items` carries `in_trash`, `render_item_table` prints `IN TRASH`; the
  private `get_collection_items` and `STOCK_API` are gone; the import block is sorted.
- New `collection.py --list <name-or-key> [--library L]`: `probe_api_plus`, name
  resolution through `copy_item.find_library`/`find_collection`, bare 8-character key
  accepted, ambiguous name error names candidate keys and parents, rows
  `key  citekey  title  [in trash]  attachments: n (names)`, total line.
- Docs: `resolve-and-render.md` (`in trash` state), `SKILL.md` front door row,
  `zotero-writes.md` "List a collection (read-only)", `troubleshooting.md` two rows;
  `tests/test_bibliography_skill.py` regex gains `collection`.
- Tests: `tests/test_bibliography_zotero_local_api.py` (params with and without
  `includeTrashed`, forwarding to every library, `item_in_trash`, `library_base`,
  paginated listing with the param, listing error), `tests/test_bibliography_resolve.py`
  (flag on the Paper, citekey-only trash sweep, `in trash` output, no-match exclusion
  sentence and its positive control, `main` exit 1 for an only-trashed citekey, exit 0
  with a live sibling, untrashed control), `tests/test_bibliography_update.py` (`--list`
  through the shared function with `include_trashed=True`, `IN TRASH` flag),
  `tests/test_bibliography_collection.py` (new).

Evidence:

- Red: 17 failed / 128 passed across the four suites plus the missing module, then
  `uv run pytest tests/test_bibliography_*.py tests/test_skill_*.py -q` → 988 passed
  (the linked-URL attachment case joined the existing summarise test). `uvx ruff check`
  on the touched files:
  only pre-existing findings in `copy_item.py`, `update_item.py`, `renderer.py`;
  `uvx ruff format --check plugins/denubis-academic` clean.
- A structural test asserting the private lister attribute was gone was written and
  then removed (it tripped on the shared import and established no behaviour).
- T1 live, citekey form: `resolve.py --citekey borgmannTechnologyCharacterContemporary1987
  --no-render` prints three blocks, `ready-to-render` for 5N8ATYMZ and `in trash` twice
  with `(not checked: item is in the trash)` lines, exit 0 (a live copy exists; before
  the exit rule change it exited 1).
- T1 live, author form: `resolve.py --author Borgmann --year 1987 --no-render` returns
  only the live copy (`ready-to-render`, exit 0); the trashed copies are excluded, as
  designed. The plan's expected "no match naming the exclusion" assumed no live copy;
  that message is covered by the unit test instead.
- Listing live (read-only): `collection.py --list "Sage SRM Guide"` → `Sage SRM Guide
  (UJPGKR74) in My Library`, 35 rows, `35 items (4 in trash)` (K6HE8KBB, KSSPB3DH,
  4TU2XD9B, D7IV2YRB marked), exit 0; `update_item.py --list "Sage SRM Guide"` → `35
  top-level items`, exit 0. The design's L1 count of 26 predates additions to the
  collection; UAT compares against Zotero's pane.
