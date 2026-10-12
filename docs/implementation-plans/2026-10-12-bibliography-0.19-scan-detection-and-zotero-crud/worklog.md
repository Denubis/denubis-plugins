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
