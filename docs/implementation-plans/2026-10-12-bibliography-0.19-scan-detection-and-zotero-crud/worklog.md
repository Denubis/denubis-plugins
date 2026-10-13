# Work completed

## 2026-10-12 — Planning evidence (no implementation yet)

Established while writing `plan.md`; every item is an observation, not a claim about
planned behaviour.

- Worktree `worktree-bibliography-0.19-design` holds the design, ADR 0029, and the ADR
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

Checkpoints: `8590878` (design, ADR 0029, README index, plan directory), `9c87200`
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

Checkpoint: `8ad11d0` (Outcome B).

## 2026-10-12 — Outcome C: write primitive, membership, item trash and restore

Changed surfaces:

- `zotero_local_api.py`: `StockWriteUnavailable`, `WriteResult`, `require_stock_writes`
  (`zotero_auth.server_id()` is None → raises, no request), `_http_request` seam
  (`httpx.request`), `read_object` (GET with `includeTrashed=1` by default,
  `LibraryQueryError` on non-2xx), `get_item_children`, pure `classify_write_reply`,
  `write_object` (PATCH with `credentials()` + `If-Unmodified-Since-Version`; 204 →
  `accepted` with `Last-Modified-Version`; 412 naming `Zotero-Server-ID` → `refused`;
  other 412 → `conflict` with a fresh `read_object`, never retried; 401 → `forget_key`
  and one retry; 403 → `refused` naming the library; 428 → `refused`; else `failed`),
  `create_objects` (POST ≤ 50 bodies, 401 retried once, non-200 raises). The module
  now imports `zotero_auth` (sys.path insert, as resolve.py does).
- New `write_gate.py`. The plan sketched `check_gate(args, cls, *, previewed)`; the
  implemented split is `add_gate_arguments(parser, cls)`, `missing_expectations(args,
  required)` (the caller names what its run needs, so a create without a parent does
  not need `--expect-parent`), `expected_from_args`, `state_refusal(expected, current)`
  (`changed since preview: version is N, expected M` / `target changed: <name> is K,
  expected X`), `format_apply_command(argv, expected)` (repeats the invocation minus
  stale gate flags, shell-quoted), and `report(accepted=, verified=, reason=)`.
- New `item_collections.py` (`--key K [--library L] (--add C | --remove C)`): modify
  class; preview GET-only with title, citekey, library, version, collections before and
  after with names, and the apply command; `No change` when the target is already
  present or absent; apply re-reads, refuses `changed since preview`, PATCHes the merged
  array, reads back, verifies presence or absence of the target key.
- New `trash_item.py` (`--key K [--library L] [--restore]`): modify class; preview
  shows type, title, citekey, library, parent key and title, file name and size from
  `~/Zotero/storage/<key>/<filename>` when present (`STORAGE_ROOT`, an observation),
  `owl:sameAs` relations, child count with "they follow it into the trash", `deleted`,
  version, apply command; `No change` when already in the requested state; apply
  PATCHes `{"deleted": bool}` and verifies by read-back with the trash included.
- Both helpers call `require_stock_writes()` first (preview included), then
  `probe_api_plus()`, and handle `zotero_auth.AuthorizationError` like `update_item.py`.
- Docs: `zotero-writes.md` ("Stock writes: preview, protect, report", the two helper
  sections, no `DELETE`), `SKILL.md` (precondition 5 widened, new precondition 7 for
  Zotero 10, two write-boundary rows, the GET-only preview and no-`DELETE` paragraph,
  completion evidence names `accepted`/`verified`), `troubleshooting.md` ("Stock-API
  write helpers" table). `tests/test_bibliography_skill.py` regex gains
  `item_collections|trash_item`.
- Tests: `tests/test_bibliography_zotero_local_api.py` (13 primitive cases over the
  seam), `tests/test_bibliography_write_gate.py` (new, 16), `tests/test_bibliography_item_collections.py`
  (new, 12: W4 preview GET-only and apply-without-flag usage error, W3 refusal before
  any request, W1 version moved and 412 conflict with no success word, happy add and
  remove with the exact PATCH body and headers, R1 read-back unchanged, no DELETE),
  `tests/test_bibliography_trash_item.py` (new, 11: same shape plus parent child count,
  trash and restore bodies, read-back with `includeTrashed`).

Evidence:

- Red: 13 primitive failures, then the helper suites failed on missing modules; after
  implementation `uv run pytest tests/test_bibliography_*.py -q` → 421 passed; with
  `tests/test_skill_*.py tests/test_academic_literature_helpers.py` → 1043 passed.
  `SKILL.md` is 199 lines (limit 500).
- `uvx ruff check` on the eight touched files: clean (a RUF100, an S105 on a loop
  variable named `token`, a PLR0911 and a PLR0915 were fixed by restructuring;
  `item_collections.main` was split into `print_preview` and `apply_change`).
  `uvx ruff format --check plugins/denubis-academic` clean; under `tests/` the
  formatter still flags 13 pre-existing files this work does not own
  (`test_bibliography_copy.py` among them).
- Live, read-only (no `--apply`): `item_collections.py --key 2B9HPL4W --add "Sage SRM
  Guide"` → `No change: the item is already in UJPGKR74`, exit 0; `--remove` → preview
  with `version: 487`, `after: (none)`, apply command ending `--apply --expect-version
  487`, exit 0. `trash_item.py --key 2B9HPL4W` → `relation: owl:sameAs
  http://zotero.org/groups/6556525/items/UTHVA3TP`, `children: 1 (they follow it into
  the trash)`, `deleted: false`, `version: 487`; `trash_item.py --key D7IV2YRB
  --restore` → `children: 2`, `deleted: true`, `version: 429`, apply command with
  `--restore --apply --expect-version 429`. No write was sent (L2, L3 are UAT).
- Not yet exercised live: a real PATCH (the 204/`Last-Modified-Version` contract and
  the 412 collision are read from the installed source, not observed); UAT L2/L3 are
  the first live writes.

Checkpoint: `cdd585e` (Outcome C).

## 2026-10-12 — Outcome D: item creation and collection create, rename, trash, restore

Changed surfaces:

- `write_gate.py`: `add_gate_arguments(parser, *classes)` (one `--apply`, the union of
  the classes' flags) and `foreign_expectations(args, cls)` so `collection.py`, which
  carries create and modify verbs on one parser, rejects the other class's flags per
  verb (W2 for `--create`).
- `zotero_local_api.py`: `get_subcollections(library, key)` over
  `/collections/<key>/collections` (live children only, as the installed API lists).
- `collection.py`: verbs `--create NAME [--parent P]` (create class: body `{"name",
  "parentCollection": KEY|false}`, apply needs `--expect-library` and, when a parent is
  named, `--expect-parent`; re-resolves, `target changed`, POST through
  `create_objects`, read-back verifies name and parent), `--rename KEY NAME`, `--trash
  KEY` (preview lists live descendants recursively and `meta.numItems`; apply PATCHes
  `deleted: true`, verifies the parent and every listed descendant by direct key read,
  prints `--restore KEY --descendants K1,K2`), `--restore KEY [--descendants …]`
  (reads the parent and each listed descendant by key, PATCHes the parent then each
  descendant shallowest first by walking `parentCollection`, each with its own read
  version; verifies every read-back and that `numItems` is unchanged; without
  `--descendants` prints the exact `descendants unknown: …` sentence and PATCHes the
  parent only). Two verbs on one call is a parser error. Pure `order_by_depth`.
- New `create_item.py` (`--type T --set F=V … --author … --creator TYPE=… [--collection
  C] [--library L]`): create class; `build_item_body`, `verification_problems`,
  `created_key` are pure; preview prints the JSON body, library (name, libraryID),
  collection key, apply command with `--expect-collection` (when named) and
  `--expect-library`; apply re-resolves, `target changed`, POSTs one body, reads back,
  verifies fields, creators, and collection; prints key and citekey or `citekey: not
  yet assigned`. `--expect-version` is not a flag of its parser.
- Docs: `zotero-writes.md` ("Create an item", "Create, rename, trash, or restore a
  collection" with the trash semantics and the evidence), `SKILL.md` three
  write-boundary rows; `tests/test_bibliography_skill.py` regex gains `create_item`.
- Tests: `tests/test_bibliography_create_item.py` (new, 12: payload/keys/apply
  command, parser rejects `--expect-version`, usage error without the keys, library-only
  when no collection, W3, `target changed` with no POST, happy POST + read-back with the
  exact body, citekey absence, wrong collection on read-back → not verified, a `failed`
  entry → not accepted, no DELETE); `tests/test_bibliography_collection.py` (+18: two
  verbs rejected, foreign flags rejected per class, W3, create preview/required
  flags/target changed/read-back, rename preview and PATCH body, trash preview with
  descendants and item count, trash apply verifies each descendant and prints the
  restore command, descendant still live → not verified, version moved, restore with
  descendants in depth order with per-key versions, restore without descendants PATCHes
  one and prints the sentence, listing cannot reveal trashed descendants, restore
  preview reads each listed descendant); `tests/test_bibliography_write_gate.py` (+1).
  Every write-verb case asserts no DELETE reached the seam.

Evidence:

- Red: 14 collection-verb failures and the missing `create_item.py`; then the three
  suites pass; `uv run pytest tests/test_bibliography_*.py tests/test_skill_*.py
  tests/test_academic_literature_helpers.py -q` → 1073 passed (see the rerun after the
  lint fixes below).
- Live, read-only: `create_item.py --type book --set "title=Scratch book for 0.19 UAT"
  --set date=2026 --author "Scratch, Author" --collection "Sage SRM Guide"` → payload
  with `collections: ["UJPGKR74"]`, `library: My Library (libraryID 1)`, apply command
  ending `--apply --expect-collection UJPGKR74 --expect-library 1`, no request to the
  seam, exit 0. `collection.py --trash UJPGKR74` → `items: 31` (`meta.numItems`,
  which excludes the 4 trashed members the listing marks), `descendants: 0`, `version:
  295`, exit 0, nothing written. `collection.py --create "Scratch 0.19" --parent "Sage
  SRM Guide"` → body `{"name": "Scratch 0.19", "parentCollection": "UJPGKR74"}`, apply
  command with `--expect-parent UJPGKR74 --expect-library 1`, exit 0.
- Not yet exercised live: any POST or collection PATCH (UAT L4, L5).

Checkpoint: `e82e407` (Outcome D).

## 2026-10-12 — Outcome E: auto-export registration

Changed surfaces:

- New `register_export.py` (`--collection "<lib>/<path>" --path FILE.bib [--translator]
  [--replace]`, register class with `--expect-collection`). Declares Python ≥ 3.14 (it
  imports `resolve.py`, which the formatter writes with PEP 758 clauses) and
  `bibtexparser` for `check_bib`. Pure: `parse_collection_spec`,
  `resolve_collection_path` (segment under its parent; a missing segment is an error,
  so BBT is never allowed to create a collection), `bbt_collection_path` →
  `/<libraryID>/<names>`, `describe_file` (size, mtime, sha256 prefix),
  `collection_citekey` (first live parent with a citekey). Shell: `observe_completion`
  (`post_run_autoexport` → `classify_autoexport_response`; `observed` only when
  `triggered` and the file mtime advances past the trigger within 30 s, polling with
  injected `now`/`sleep`) and `check_content` (`check_bib` on the file). Apply calls
  `rpc("autoexport.add", [bbt_path, translator, path, {}, replace])`; `accepted` only
  when the returned `key` equals the expected key, any other result or RPC error
  printed verbatim as `not accepted`. Final line `accepted; completion <state>;
  content <state>; verified|not verified`, exit 0 only when verified; the previewed
  size and hash are printed beside the new ones as an observation.
- Docs: `zotero-writes.md` ("Register a Better BibTeX auto-export"),
  `notes-and-bibliographies.md` (bootstrap steps 1–4 may use the helper; manual route
  kept), `SKILL.md` write-boundary row, `troubleshooting.md` four rows;
  `tests/test_bibliography_skill.py` regex gains `register_export`.
- Tests: `tests/test_bibliography_register_export.py` (new, 21): numeric path, spec
  parsing, path resolution (missing segment, same-named sibling under another parent),
  preview without RPC and with file facts, missing file, `--expect-version` rejected,
  usage error without `--expect-collection`, W3, `target changed` without RPC, the RPC
  receives `/1/Sage SRM Guide/Readings` and never the `My Library/...` form, replace and
  translator forwarded, another key → not accepted verbatim, BBT error → not accepted
  verbatim, E2a (no zotero-api-plus → `completion not observed`, content still checked,
  exit 1), E2b (identical bytes with a later mtime → observed), no mtime change → not
  observed after a 30 s injected wait, trigger refused with its kind, content not
  satisfied on an absent citekey and on a missing file.

Evidence:

- The first run of the suite had 20 passing and one false negative caused by the test
  clock (it started at 1000, so a real file mtime was always "after the trigger"); the
  fixture now starts at real time and back-dates the file. After that the suite passes;
  `uv run pytest tests/test_bibliography_*.py tests/test_skill_*.py
  tests/test_academic_literature_helpers.py -q` → 1094 passed. `uvx ruff check` on
  the helper and tests clean (`main` split into `apply_registration` for the statement
  count); `uvx ruff format --check plugins/denubis-academic` clean. `SKILL.md` is 203
  lines.
- Not exercised live: `autoexport.add` itself and the trigger-then-mtime observation
  (E1, E3 are UAT on a scratch collection with zotero-api-plus present). The empty-params
  probe of `autoexport.add` answered `-32602 required argument collection missing,
  translator missing, path missing`, which is the verbatim error shape the helper
  prints.

Checkpoint: `f637cac` (Outcome E).

## 2026-10-12 — Outcome F: release 0.19.0

Changed surfaces:

- `SKILL.md` final pass: precondition 5 names every write helper and the listing as
  zotero-api-plus consumers; precondition 7 (Zotero 10 for the stock-API helpers,
  `register_export.py` included for uniformity) renumbered into order; the procedure
  table row for Zotero writes names listing, filing, trash, restore, create,
  collections, and export registration. Front door, quoting rule, write-boundary table
  (one row per helper with preview command, class, and what the preview shows), and
  completion evidence were written in Outcomes A to E. 204 lines (limit 500).
- `docs/architecture/plugins/denubis-academic/0-context.md`: helper table row, the
  Zotero/BBT and zotero-api-plus boundary rows, the rendered-Markdown bullet rewritten to
  Contract 1, a new bullet for `accepted` versus `verified`.
- Versions: `plugins/denubis-academic/.claude-plugin/plugin.json`,
  `plugins/denubis-academic/.codex-plugin/plugin.json`, and the
  `.claude-plugin/marketplace.json` entry at 0.19.0; new `## [denubis-academic] 0.19.0`
  at the top of `CHANGELOG.md`.

Bounded inspection (every documented flag exists in the helper; `--help` captured by
`/tmp/bib019/helpflags.sh` on 2026-10-12):

| Helper | `--help` flags | Documented in the skill text |
|---|---|---|
| `resolve.py` | `--allow-mocr --author --bib --citekey --date --doi --force --force-ocr --library --no-render --title --year` | all present |
| `ingest.py` | `--allow-mocr --force --force-ocr` | all present |
| `render.py` | `--allow-mocr --force-ocr` | all present |
| `collection.py` | `--apply --create --descendants --expect-* --library --list --parent --rename --restore --trash` | all present |
| `item_collections.py` | `--add --apply --expect-version --key --library --remove` | all present |
| `trash_item.py` | `--apply --expect-version --key --library --restore` | all present |
| `create_item.py` | `--apply --author --collection --creator --expect-collection --expect-library --expect-parent --library --set --type` | all documented flags present; `--expect-parent` exists through the create class but has no meaning here (passing it refuses as `target changed`) |
| `register_export.py` | `--apply --collection --expect-collection --path --replace --translator` | all present |
| `update_item.py`, `copy_item.py`, `fetch.py`, `annotate.py` | unchanged flag sets | unchanged docs |

Preview lines documented in `zotero-writes.md` and `SKILL.md` were checked against the
helpers' format strings while writing Outcomes C to E and by the live read-only previews
recorded above (`version:`, `collections:`/`after:`, `parent:`, `file:`, `relation:`,
`children:`, `deleted:`, `payload:`, `library:`, `collection:`, `descendants:`, `items:`,
`translator:`, `path:`, `registration state: unknown`, and the `Preview only … To apply
exactly this change:` block).

Evidence:

- `uv run pytest tests/test_bibliography_*.py tests/test_skill_*.py
  tests/test_marketplace_sync.py tests/test_codex_marketplace.py
  tests/test_academic_literature_helpers.py tests/test_paper_review_skill.py -q` →
  1128 passed.
- Whole suite: `uv run pytest -q` stops at collection with 20 errors, all in
  `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/` (`ModuleNotFoundError:
  No module named 'typer'`; that sub-project has its own environment, last changed in
  `44b5fbc`, untouched here), and
  `plugins/denubis-plan-and-execute/scripts/workflow_statusline/tests` fails collection
  the same way (`No module named 'workflow_statusline'`, its own package). Both are
  pre-existing environment facts outside this work. Run by explicit path:
  `plugins/denubis-token-estimator/tests` → 45 passed; `tests` → one failure,
  `tests/test_test_quality.py::test_python_tests_have_no_detectable_markdown_wording_assertions`,
  pointing at a new assertion in `tests/test_bibliography_renderer.py` that read a
  generated `pages/001.md` and checked its text. The assertion was redundant with the
  recorded tier calls (only the OCR tier ran, so only its pages could be written) and
  was replaced by a `page_count` check; `uv run pytest -q tests` → 1533 passed.
- `uvx ruff check .`: 54 findings on the base commit, fewer now; every remaining
  finding is in a file this work did not create (`copy_item.py` 6 and `update_item.py` 6,
  down from 10, pre-existing; `renderer.py` 3 pre-existing; the rest outside the
  plugin). `uvx ruff format --check plugins/denubis-academic` clean; under `tests/` 13
  pre-existing files this work does not own would be reformatted.
- `git diff --check` clean.
- `rg -n '0\.19\.0'` hits the two manifests, the marketplace entry, and the changelog
  heading.
- ADR renumbered 0028 → 0029 after `main` took 0028 (`f5609a5`) post-fork: `git mv` of
  the decision file, README index line, and every citation in the design, plan, todo,
  changelog, skill text, references, and helper docstrings. `rg -n 0028` on the branch
  afterwards hits only the todo's note about `main`'s own ADR.

Checkpoint series before normalisation (2026-10-12, no upstream, nothing pushed):
`8590878 9c87200 8ad11d0 cdd585e e82e407 f637cac 2c612a7 a9792e0 acd5694`, tree
`aa66e4ae8fb23b26291217cee427102eb1589fff`. Normalised at the human's request before
UAT: `2c612a7` and the two renumber commits (`a9792e0`, `acd5694`) folded into one
Outcome F commit by `git reset --soft f637cac` and recommitting; commits A to E keep
their SHAs. The only tree difference from `aa66e4a` is this worklog entry and the todo.

## 2026-10-12 — Review fix: the restore command was not shell-quoted

A reviewer running `collection.py --trash` with stubbed writes found the emitted
`uv run collection.py --restore KEY --library My Library` line joined with plain spaces,
so pasting it back exited 2 (`unrecognized arguments: Library`). Serves Outcome D.

- `collection.py`: the restore line now uses `shlex.join`, matching
  `write_gate.format_apply_command`, which every other emitted command already used
  (`rg '" "\.join\('` over the helpers hits only two text-normalisation joins in
  `annotate.py` and `renderer.py`).
- `tests/test_bibliography_collection.py`: new
  `test_trash_apply_restore_command_round_trips_through_the_parser` trashes with
  `--library "My Library"`, `shlex.split`s the emitted line, and parses it with the
  helper's own parser. Red before the fix for the reviewer's reason (`unrecognized
  arguments: Library`); green after.
- `uv run pytest tests/test_bibliography_collection.py tests/test_skill_*.py -q` → 644
  passed; ruff check and format clean on both files; `git diff --check` clean.
- Private checkpoint on top of the normalised series; folds into Outcome D
  (`e82e407`) after UAT.

## 2026-10-12 — Live UAT results and the parent-trash fix

Live checks by the human's reviewer session (log `/tmp/bib019-live-check.log`, five
scratch objects left verified in Zotero's trash, harness files removed, repository
unchanged): passed creation (L4), membership add and remove (L2), collection rename,
attachment trash and restore without touching parent or sibling (L3), collection-tree
restore preserving membership (L5), and stale-version refusal. Export registration
(E1/E3) remains untested live because the available API cannot remove a registration
afterwards. The quoting fix (`28e8f06`) was confirmed: 1,534 tests passed there.

Confirmed bug: `trash_item.py --restore` on an attachment under a trashed parent
reported `accepted; verified` while the attachment stayed in the trash, and on a child
whose own flag was clear said "not in the trash. Nothing to apply." Cause:
`zotero_local_api.item_in_trash` reads only the object's own `deleted` flag, while
Zotero's `isInTrash()` includes the parent's state (parent `D7IV2YRB`, attachment
`XCGCBRF7`). Serves Outcome C.

- `trash_item.py`: `read_parent` reads the parent envelope once (trash included);
  pure `in_trash_via_parent` and `deleted_label`; the preview's `deleted:` line reads
  `false (in the trash through parent KEY)` or `true (parent KEY is in the trash
  too)`; `--restore` on such a child prints the preview, explains that the parent owns
  the trash state, prints `uv run trash_item.py --key PARENT --restore [--library …]`
  (shell-quoted), ends `not accepted: in the trash through parent KEY`, exit 1, and
  sends no PATCH with or without `--apply`; a trash preview of such a child reports
  "already in the trash through its parent KEY"; the restore read-back re-reads the
  parent so `verified` means Zotero's trash state, not the child's flag. `main` split
  into `preview_outcome` and `apply_change` for the statement and branch limits.
  `item_in_trash` itself is unchanged: `resolve.py` and the listings apply it to
  top-level items, where own flag and trash state coincide.
- Docs: helper docstring, `zotero-writes.md` trash section, `SKILL.md` table row (204
  lines), changelog line.
- Tests (`tests/test_bibliography_trash_item.py`): three new cases, restore preview
  under a trashed parent, restore apply under a trashed parent with the child's own flag
  set, trash preview under a trashed parent. Red before the fix for the reviewer's
  reasons (exit 0 with the apply command offered; the PATCH reached the seam; no parent
  mention); green after. Five existing apply-path cases now answer the parent read and
  locate the PATCH by method.
- Gates: focused set → 1132 passed; ruff check and format clean; `git diff --check`
  clean.
- Not covered: a collection listing still marks rows by the item's own flag; children
  are listed under their parent row, so a child of a trashed parent appears under a
  marked row. Recorded as a limit, not changed.

## 2026-10-12 — Registration removal is manual: said in the preview

A side note observed that `autoexport.add` has no remove counterpart (the reference and
the helper docstring already said so) but that nothing told the human where removal
happens, and the preview did not warn before approval. Serves Outcome E.

- `register_export.py` preview gains `removal:    manual; no helper can take a
  registration back. Delete it in Zotero under Settings > Better BibTeX > Automatic
  export`. `zotero-writes.md` and the `SKILL.md` row say the same (204 lines).
- `tests/test_bibliography_register_export.py`: the preview test asserts the removal
  line; red before (`assert None` on the search), green after. Focused set → 1132
  passed; ruff check and format clean; `git diff --check` clean.
- E1/E3 still have no live evidence. Running them creates a standing export that only
  the BBT preferences pane removes; use a scratch collection and a throwaway path.

## 2026-10-12 — Review fix: the parent-restore command dropped the helper's directory

Live, from the repository root, the refusal printed `uv run trash_item.py --key … --restore
--library 'My Library'`, which failed to spawn. Cause: the command used
`Path(sys.argv[0]).name`. It now keeps `sys.argv[0]`, as `collection.py` already did.
New `test_parent_restore_command_keeps_the_helper_path_when_run_from_elsewhere` runs
the helper under its absolute path and asserts the emitted command's first word is that
path; red before (`'trash_item.py' == '/…/trash_item.py'`), green after. Gates: trash_item,
collection, and skill tests → 658 passed; ruff check and format clean; `git diff --check`
clean. The reviewer reports the parent-trash refusal works live; no writes performed.

## 2026-10-12 — Live E1/E3: registration works; the host could not see the file

Authorised by the human ("run it once anyways"). Scratch objects, all still live:

- `collection.py --create bib019-uat-export --apply --expect-library 1` → key
  `G333AT78`, `accepted; verified`.
- `item_collections.py --key 7XWWDHT5 --add G333AT78 --apply --expect-version 445`
  (the human's geography preprint, `torringtonAILessonPlanning2026`, already in Zotero
  under Sage SRM Guide; the OSF record is pending moderation and not public) → version
  519, `accepted; verified`.
- `register_export.py --collection 'My Library/bib019-uat-export' --path
  /tmp/bib019/uat-export.bib --apply --expect-collection G333AT78` → `accepted:
  autoexport.add returned {'libraryID': 1, 'key': 'G333AT78', 'id': 161}`, then
  `completion not observed: no modification seen within 30 s`, `content not
  satisfied: no file`, final line `accepted; completion not observed; content not
  satisfied; not verified`, exit 1. The preview printed the new `removal:` line.

Diagnosis: Zotero is the Flatpak `org.zotero.Zotero` 10.0.6 (`bwrap`), which has a
private `/tmp`. BBT's own record in
`~/.zotero/zotero/jf60v7u8.default/prefs.js` (`autoExport./tmp/bib019/uat-export.bib`,
id 161, type collection, `status: done`, `error: ""`, updated 5 s after creation) and
the file at `/proc/<zotero-pid>/root/tmp/bib019/uat-export.bib` (380 bytes, one
`@unpublished{torringtonAILessonPlanning2026, …}` entry; host copy at
`/tmp/bib019/uat-export.sandbox-copy.bib`) show the export ran and is well formed.
The helper reported truthfully from the host's view; the throwaway path was the
mistake, not the helper. The human's existing registrations all point under
`~/people`, which the Flatpak shares.

State saved at the human's request ("not physically present, save state, tomorrow").

## 2026-10-13 — Live E1/E3 re-run with a host-visible path: verified

`register_export.py --collection 'My Library/bib019-uat-export' --path
<plan-dir>/uat-export.bib`: preview exit 0 with the `removal:` line and the exact apply
command; `--apply --expect-collection G333AT78` → `accepted: autoexport.add returned
{'libraryID': 1, 'key': 'G333AT78', 'id': 161}`, `completion observed: mtime
2026-10-13T01:14:31Z after the trigger`, `content satisfied:
torringtonAILessonPlanning2026 present in a well-formed bib (1 entries)`, `file before:
no file; after: 437 bytes`, final line `accepted; completion observed; content
satisfied; verified`, exit 0. The file held one `@online{torringtonAILessonPlanning2026,
…}` entry and was deleted afterwards, uncommitted. BBT's prefs now hold both
registrations (the sandbox `/tmp/bib019/uat-export.bib` one and this one); removal is
manual in Zotero. E1/E3 complete; all plan UAT steps now have live evidence except the
human's two judgement calls.

## 2026-10-13 — Scratch state cleaned up

The human deleted both `uat-export` registrations in Zotero (prefs.js grep count 0
afterwards). Then `item_collections.py --key 7XWWDHT5 --remove G333AT78 --apply
--expect-version 522` → version 526, read-back collections `Sage SRM Guide (UJPGKR74)`
only, `accepted; verified`; `collection.py --trash G333AT78 --apply --expect-version 518`
→ `accepted; verified`, exit 0 (0 items, 0 descendants). The preprint remains in Sage
SRM Guide. Only the reviewer's five scratch objects remain, in Zotero's trash.

## 2026-10-13 — Sandboxed-Zotero symptom documented, no runtime warning

The human accepted the recommended default: no sandbox detection in
`register_export.py`. `references/troubleshooting.md` gains one row under "Stock-API
write helpers" naming the symptom (`accepted; completion not observed …; content not
satisfied: no file` while BBT shows the export done), the cause (Flatpak private `/tmp`),
and the remedy (a shared path, delete the unreachable registration). Gates: skill and
register_export tests 26 passed; `git diff --check` clean.

## 2026-10-13 — E3 live: re-run and cross-collection refusal

Scratch collection restored (`collection.py --restore G333AT78 --apply --expect-version
527` → `accepted; verified`; the preview and apply both said descendants unknown, as
designed). Registered `<plan-dir>/uat-export.bib` for it again (empty collection: BBT
exported a 0-byte file, `content not satisfied: no live item with a citekey in the
collection to look for`, as designed). Re-run of the identical apply: `accepted:
autoexport.add returned {… 'id': 161}`, completion observed 6 s later, same report, exit 1
(unverifiable content, not a failure of the write). BBT answers a re-run identically to a
first registration and keeps the settings; the "reschedule message" the plan's UAT step
names is the preview's registration-state line, which is present. Same path for
`My Library/Sage SRM Guide` without `--replace`: preview printed the apply command;
apply → `not accepted: autoexport.add error: {'code': -32602, 'message': "Auto-export
exists with incompatible parameters, but no 'replace' was requested"}`, exit 1, nothing
written (the registration still names G333AT78). Remaining for the human: compare the
registration with a hand-made "Keep updated" export in BBT's preferences, then delete it.

## 2026-10-13 — E1 human judgement passed; scratch state cleaned up again

The human compared the live registration with a hand-made "Keep updated" export in
BBT's preferences ("it looks fine") and deleted it (prefs.js `uat-export` count 0).
The 0-byte export file was deleted, uncommitted. `collection.py --trash G333AT78 --apply
--expect-version 528` → `accepted; verified`, exit 0. Items 2–7 of the plan's Human UAT
are complete with live evidence; items 1 and 8 remain.

## 2026-10-13 — UAT step 8 (Q3 live) accepted

Pages 192 and 205 of the forced Borgmann 2006 render were compared with page images
(`/tmp/bib019/borgmann2006-p192.png`, `-p205.png`, PyMuPDF 110 dpi). Observed: "Jiving"
→ "living" on 205, but Docling's OCR displaces words to paragraph ends ("thing, living
logs gods"; "things point points"), "HeidegIt" for "Heideg-ger's"; on 192 "in tum",
"settlcd", "s0", "t0", "cO-opt" and a dropped clause ("populated by understand"). The
forced render removes some slips and adds others; the state line names it OCR and the
quoting contract requires the page-image check. The human accepted Q3 on that basis
("um yes, that's fine"). Remaining: UAT step 1.

## 2026-10-13 — UAT step 1 accepted; `contradicted` added to the quotation states

One reader (Opus, xhigh, named by the human) read physical pages 192, 205 and 211 of
the forced Borgmann 2006 render under `reading-and-quoting.md`. It located three
quotations with `blockquote.py` (re-run by the orchestrator: all three `located`),
rendered the page images itself, called two `verified` naming itself as inspector, and
refused the third because the page reads "a thing, was seen" where the render reads
"a was seen". The falsifier (a `verified` label without opening the page) did not
occur. The state line was treated as a description of extraction, not as permission.
The reader also reported whole dropped lines on pages 192 and 211 and reversed
paragraph order on 211. The human accepted step 1 and chose to add the missing label
("or we just do contradicted as a label?"): `contradicted` now sits beside
`located`/`verified`/`unverified` in `using-bibliography/SKILL.md` (quoting rule and
completion evidence), `references/reading-and-quoting.md` (source-fidelity, output
template, verification record), `annotated-bibliography/SKILL.md`, and the 0.19.0
changelog entry. `check.py` is unchanged: it can only locate. Gates: skill,
literature-helper, and blockquote tests 13 passed; `git diff --check` clean. All eight
Human UAT steps are now accepted or evidenced.

## 2026-10-13 — History normalised after accepted UAT

Accepted tree `46775cabf267d6a690c43ecb4cffef1acaae0d2c` (commit `44b91a4`); private
series before the rewrite: `8590878 9c87200 8ad11d0 cdd585e e82e407 f637cac ff8cf89
28e8f06 290b8fa 50d37da a1765ea cf82320 dcdac3b b270be0 4e2789a c43ee1b f14cec6 8625896
44b91a4`. Rebuilt on a detached head from base `e417da4` by cherry-pick plus
path-limited 3-way patch application (`/tmp/bib019/rebuild*.sh`): the design/ADR/plan
commit unchanged; `44b91a4`'s skill-text hunks into Outcome A; `290b8fa` and `a1765ea`
into Outcome C (the todo had named D for `a1765ea`, but the fix is to `trash_item.py`,
Outcome C's helper); `28e8f06` into Outcome D; `50d37da` and `4e2789a` into Outcome E;
the changelog hunks of `290b8fa` and `44b91a4` into the release commit; the plan
directory's accepted state as one final docs commit. Three conflicts, all in
`SKILL.md` where adjacent lines were edited by different commits (the quote/Zotero-write
bullets twice; the write-boundary table rows once), resolved by keeping the outcome-era
neighbour lines. `git diff --stat 44b91a4 <rebuilt>` was empty before this entry was
added. Gates on the rebuilt checkout: `uv run pytest -q tests` → 1538 passed; `uvx ruff
check plugins/denubis-academic` → the same 15 pre-existing findings (`copy_item.py` 6,
`update_item.py` 6, `renderer.py` 3); `uvx ruff format --check plugins/denubis-academic`
clean; `git diff --check` clean; version grep hits both manifests, the marketplace entry,
and the changelog heading. Whole-repository `pytest -q` and `ruff check .` still fail
only in the pre-existing places recorded under Outcome F.

## 2026-10-13 — Rebased onto main for integration

The human asked for integration into `main` ("yes"). `git merge-tree main HEAD` showed
two conflicts (`CHANGELOG.md` top; the ADR index, where `main` added 0028 after the
fork), so the private series was rebased onto `main` (`f6603f2`): the index keeps
`main`'s 0028 line and this branch's 0029 line; the changelog puts the 0.19.0 entry
first, above `main`'s token-estimator 0.3.0 and external-agents 0.24.0 entries. The
rebased tree differs from the normalised tree (`ef52233`) only by `main`'s own commits
and those two files. `git merge-base --is-ancestor main HEAD` holds, so the merge is a
fast-forward; `merge-tree` is now conflict-free. Gates after the rebase: `uv run pytest
-q tests` → 1557 passed; ruff check on the plugin → the same 15 pre-existing findings;
format check clean; `git diff --check` clean. The merge itself is the human's
`/denubis-plan-and-execute:merge-to-main`; no push or cleanup authority has been named.
