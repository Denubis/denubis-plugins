# Bibliography 0.19: extraction record, trash awareness, Zotero CRUD, auto-export

**Design:** `docs/design-plans/2026-10-12-bibliography-0.19-scan-detection-and-zotero-crud.md`
(status: current design; accepted 2026-10-12, "great, lock it in").
**ADR:** `docs/architecture/decisions/0028-zotero-writes-use-the-stock-local-api-and-delete-means-trash.md`
(untracked in this worktree together with the design and the README index line; the first
checkpoint commit carries all three).
**Working root:** `/home/brian/people/Brian/brian-ed3d-plugins/.claude/worktrees/bibliography-0.19-design`
**Branch:** `worktree-bibliography-0.19-design`. **Integration branch:** `main`
(`.ed3d/merge-policy`: direct merge to main, no PRs).
**Skill under change:** `plugins/denubis-academic/skills/using-bibliography/` (`$BIB` below).
**Release:** `denubis-academic` 0.18.0 → 0.19.0.

## Repository evidence the plan rests on

Observed 2026-10-12 in this worktree unless stated.

- `renderer.py:59` `RENDER_VERSION = 2`; `render_metadata_is_current` (`renderer.py:62`)
  exempts every renderer other than `pymupdf4llm` and `docling` from the version test.
  `tests/test_bibliography_renderer.py:143-152` currently asserts that exemption for
  `mocr` and must change with the predicate (Q4).
- `_write_outputs` (`renderer.py:291`) owns `meta.json`; `render_pdf_with_fallback`
  (`renderer.py:506`) hard-codes the three-tier cascade list and the mocr tail.
- Cache readers: `resolve.render_is_present` (`resolve.py:531`) and
  `ingest.current_render_matches` (`ingest.py:156`); both call the predicate.
- `resolve.print_match` (`resolve.py:999`) prints `state:`; `paper_from_local_item`
  (`resolve.py:584`) builds `Paper` from the stock envelope; the `--force` and
  `--allow-mocr` flags are at `resolve.py:1132-1145`, `ingest.py:191-202`,
  `render.py:56-61`; `_render_cmd` (`resolve.py:755`) forwards flags to `render.py`.
- `zotero_local_api.fetch_search_page` (`zotero_local_api.py:147`) builds the quicksearch
  params; nothing passes `includeTrashed`; no code reads `data.deleted`.
- `update_item.get_collection_items` (`update_item.py:327`) lists
  `/collections/<key>/items/top` paginated, no `includeTrashed`; `update_item.py --list`
  (`update_item.py:450-477`) is its only consumer and resolves names through
  `copy_item.find_library`/`find_collection` over zotero-api-plus `/api/plus/libraries`.
- `copy_item.find_library` (`copy_item.py:111`) and `find_collection` (`copy_item.py:153`)
  are the name resolvers; `fetch.py:103-176` carries a near-duplicate pair. Both expect a
  library dict with `type`, `groupID`, `name`, and `collections: [{name,key,parentKey}]`.
- `zotero_auth.credentials()` (`zotero_auth.py:334`) returns the write headers and probes
  the server ID once; `zotero_auth.post` (`zotero_auth.py:351`) is POST-only and retries
  a 412 as a server-ID mismatch. Stock `If-Unmodified-Since-Version` conflicts also answer
  412, so the new primitive cannot route through `zotero_auth.post`.
- `resolve.post_run_autoexport`, `classify_autoexport_response`, `check_bib`
  (`resolve.py:800`, `:389`, `:354`) already trigger the zotero-api-plus export and parse
  a bibliography; `register_export.py` reuses them rather than re-implementing.
  zotero-api-plus reports only `triggered` (`~/people/Brian/zotero-api-plus/src/utils/run-autoexport.ts:6-12`).
- `blockquote.py` prints `> text` and `[@citekey, p. N]`, exits 2 on `NO MATCH`; no state
  label exists yet.
- Tests load helpers by file path (`tests/test_bibliography_update.py:32-47`) with pure
  cores and stubbed `httpx`/`pymupdf` (`tests/test_bibliography_renderer.py:43-83`).
  `tests/test_bibliography_skill.py:69-72` lists helper script names in a regex that
  flags bare invocations in the references; new helpers must join that list.
- Release surfaces: `plugins/denubis-academic/.claude-plugin/plugin.json` (0.18.0),
  `.claude-plugin/marketplace.json:150-153` (0.18.0), repository-root `CHANGELOG.md`
  (`## [denubis-academic] 0.18.0` at line 124; new entry goes above the current top).
  `plugins/denubis-academic/.codex-plugin/plugin.json` is named by
  `docs/architecture/plugins/denubis-academic/0-context.md:70-71`; `tests/test_marketplace_sync.py`
  and `tests/test_codex_marketplace.py` own manifest agreement.
- Live Zotero (this machine, 2026-10-12): `GET /api/` answers `Zotero-Server-ID: g6bzZS56RsjG`;
  `GET /api/users/0/items/D7IV2YRB` has `data.deleted: true`, version 429
  (`borgmannTechnologyCharacterContemporary1987`, My Library; its attachment
  `XCGCBRF7/Borgmann - 1987 - ….pdf` is the 16-page Word-made PDF named by Q2);
  `~/zettelkasten/papers/borgmannTechnologyCharacterContemporary2006/meta.json` is
  `render_version 2, pymupdf4llm, ocr false`, source `XD39JLVP/Borgmann - 2006 - ….pdf`
  (311 pages; Q1 and Q3).
- Tooling: `uv run pytest` (pyproject `testpaths`), `uvx ruff check` / `uvx ruff format`
  (`.ed3d/tools.md`), Python 3.14 target with the per-file 3.11 exception for PEP 723
  helpers that declare `>=3.11` (project `CLAUDE.md`: one exception per `except` clause in
  those files and anything they import).

## Deviations from design detail, with reasons

1. **Collection and library name resolution reads zotero-api-plus, as the design
   says.** Human ruling, 2026-10-12, this planning session: asked "Which source should
   `list_libraries()` read: stock Zotero, or the zotero-api-plus `/libraries` endpoint?",
   the answer was "api-plus". Consequence: every new helper resolves names through
   `copy_item.get_libraries()` (`/api/plus/libraries`) exactly as `update_item.py --list`
   does today, so the new helpers need zotero-api-plus installed even though their
   writes go to stock. Each helper probes `/api/plus` first and stops with the same
   message `copy_item.probe_copy_item` uses when the extension is absent. `SKILL.md`
   precondition 5 says so. Stock `/groups` and `/collections` are not used for names.
   Recorded in ADR 0028's consequences.
2. **412 handling.** The stock conflict status collides with `zotero_auth`'s server-ID
   mismatch status. The write primitive sends its own request with `credentials()`
   headers, never retries a 412, and reports it as `conflict` carrying Zotero's current
   object; a body naming `Zotero-Server-ID` is reported as `refused: server id` instead.
   A 401 is retried once after `forget_key`, mirroring `zotero_auth.post`.
3. **Register helper requires Zotero 10.** W3 says every write helper refuses on a server
   without a `Zotero-Server-ID` header and the design's exclusion lists all new helpers;
   `register_export.py` writes through BBT, not stock, but follows the same gate for
   uniformity as designed. Recorded so nobody reads it as an accident.
4. **Collection restore takes its descendant keys from the trash output.** The design
   says the helper "restores listed descendants itself"; the installed local API gives
   no way to list trashed descendants, so the trash step prints them and `--restore`
   accepts them as `--descendants` (Outcome D states the evidence). Found by Astra's
   review of the first plan draft, 2026-10-12, and verified in the extracted source.
5. **`--force-ocr` bypasses the cache**, since a scan whose text layer passed the gate
   has a current cache (Outcome A). Same review.
6. **The BBT collection argument is the numeric absolute form** `/<libraryID>/<names>`
   (Outcome E). Same review.
7. **A small shared CLI module.** `write_gate.py` (new) holds the preview/apply argument
   wiring, the expected-state flag checks per operation class, the stock library path
   builder, and the `accepted`/`verified` report line, so five helpers do not copy the
   gate. The write primitive itself lives in `zotero_local_api.py` as designed.

## Scope

In: Contract 1 (extraction record, `--force-ocr`, quoting states, cache invalidation);
trash awareness in resolution and listing; the stock write primitive; `collection.py`,
`item_collections.py`, `trash_item.py`, `create_item.py`, `register_export.py`,
`write_gate.py`; skill text and references; tests; architecture page; version 0.19.0.

Out (design non-goals): any `DELETE`; new zotero-api-plus endpoints; engine changes;
Zotero 7-9 support for the new writes; library-level or recursive auto-exports; saved
searches; cross-library membership (stays `copy_item.py`).

## Acceptance criteria and evidence owners

| ID | Owner | Outcome |
|---|---|---|
| Q1, Q2 | operational: `render.py` on the two Borgmann attachments, read `meta.json` | A |
| Q3 | automated (stubbed tiers prove entry point and record) + operational (synthetic PDF, Borgmann 2006) | A |
| Q4 | automated `tests/test_bibliography_renderer.py` | A |
| Q5 | automated `tests/test_bibliography_blockquote.py` (new) | A |
| T1 | automated `tests/test_bibliography_resolve.py` + operational on `D7IV2YRB` | B |
| L1 | UAT on the live `Sage SRM Guide` collection | B |
| W1, W3, W4, R1 | automated `tests/test_bibliography_zotero_local_api.py`, `tests/test_bibliography_write_gate.py`, per-helper tests | C |
| L2, L3 | UAT on scratch objects | C |
| W2 | automated per-helper tests | D |
| L4, L5 | UAT on scratch objects | D |
| E1, E3 | UAT on a scratch collection with zotero-api-plus present | E |
| E2 | automated `tests/test_bibliography_register_export.py` | E |
| F1 | operational: full gates, three version surfaces | F |

## Outcome A: extraction record, forced OCR, and the quoting contract

**Goal:** Every new render writes `extraction`, `forced`, `limitations`, and
`render_version: 3`; pre-0.19 records are stale for every renderer; `--force-ocr` starts
the cascade at the OCR tier on `render.py`, `ingest.py`, and `resolve.py`; the resolver's
state line shows extraction and the first limitation and suggests `--force-ocr` on a
likely scan; `blockquote.py` labels matches `located`; the skill text states Contract 1.
**Depends on:** nothing.
**Owns:** Q1–Q5; D3, D4.

### Files and consumers
- Modify: `$BIB/renderer.py` — `RENDER_VERSION = 3`; `render_metadata_is_current` is
  `meta.get("render_version") == RENDER_VERSION` for every renderer; `describe_pdf(pdf)`
  returns `{"page_count", "producer", "full_page_image_pages", "no_text_pages"}` via
  `pymupdf` (`doc.metadata["producer"]`, per page `get_image_info()` bbox covering ≥ 90 %
  of the page rect, `get_text("text").strip()` empty); pure `limitations_for(description,
  pages)` builds the strings (page-sized images with producer; pages without extractable
  text; replacement characters on N pages); `_write_outputs` takes `extraction` and
  `forced` and writes `extraction`, `forced`, `limitations`; `render_pdf_with_fallback`
  gains `force_ocr: bool` that drops the first two tiers (and with `allow_mocr` plus a
  session goes straight to mocr); `render_attachment` forwards it; HTML and Pandoc records
  carry `extraction: "converted"`.
- Modify: `$BIB/render.py`, `$BIB/ingest.py`, `$BIB/resolve.py` — `--force-ocr` flag;
  `--force-ocr` also bypasses the render cache in both entry points, because a scan
  whose text layer passed the gate has a *current* cache and would otherwise never be
  re-rendered: `resolve.check_rendered(info, papers_dir, force=args.force or
  args.force_ocr)` (`resolve.py:1294`) and `ingest.py:269` skips the cache check when
  either flag is set; `resolve._render_cmd` forwards it; `resolve.py` reads the render record after
  `check_rendered` and prints `state: rendered (<extraction>; <first limitation>)` and, when
  `extraction == "text-layer"` and the page-image limitation is present, one advisory line
  naming `--force-ocr`; `ingest.py` prints the same extraction label.
- Modify: `$BIB/blockquote.py` — each hit ends with `Verification: located (render match;
  check the source page before calling it verified)`; `NO MATCH` prints `Verification:
  unverified` on stderr before exit 2.
- Modify docs: `$BIB/SKILL.md` (source-fidelity rule → Contract 1; completion evidence for
  quotes names the quotation state), `references/reading-and-quoting.md` (dispatch gate
  reads `extraction` and `limitations`; reader labels and verification record carry
  `located`/`verified`/`unverified`; page-image or snapshot check for every quotation),
  `references/notes-and-bibliographies.md` (note template and blockquote section),
  `references/resolve-and-render.md` (meta contract, `--force-ocr`, render version 3,
  re-render of old records), `references/troubleshooting.md` (render and quotation rows),
  `plugins/denubis-academic/skills/annotated-bibliography/SKILL.md:54-58` (OCR paragraph
  refers to the using-bibliography quoting rule and the three states).
- Test: `tests/test_bibliography_renderer.py` (replace the exemption assertions; add
  describe/limitations/forced-path cases with stubbed `pymupdf`), `tests/test_bibliography_resolve.py`
  (state line and advisory; `--force-ocr` with a current version-3 cache still
  invokes the render subprocess with `--force-ocr`, and a positive control without
  either flag does not render), `tests/test_bibliography_ingest.py` (`--force-ocr`
  with a current cache calls `render_pdf` with `force_ocr=True`; positive control
  skips),
  `tests/test_bibliography_blockquote.py` (new, subprocess over a tmp `pages/` dir).
- First real consumer: `resolve.py --citekey borgmannTechnologyCharacterContemporary2006`
  after the stale version-2 record forces a re-render.

### Work
1. Red: predicate tests for version-2 records of `pymupdf4llm`, `docling`, `mocr`,
   `html.parser`, `pandoc` → not current; version 3 → current (both cache readers, as the
   existing two-reader test does). Red: `_write_outputs` record contains the three new
   keys; forced cascade with stubbed tiers never calls the pymupdf4llm or docling-no-OCR
   lambdas and records `extraction: "ocr", forced: true`; unforced text-layer path records
   `extraction: "text-layer", forced: false`; `limitations_for` on a 311/311 page-image
   description with the Acrobat producer yields the design's sentence, on a 0/16
   description yields no page-image sentence (Q1/Q2 shape at unit level).
2. Green: implement in `renderer.py`; thread `force_ocr` through `render.py`, `ingest.py`,
   `resolve._render_cmd`, `render_via_subprocess`; print the state line and advisory in
   `resolve.print_match` from the record on disk (`out_dir/meta.json`); `blockquote.py`
   states. Keep `ocr` and `renderer` keys unchanged for existing readers.
3. Docs listed above. Run the Q1/Q2 operational probes and paste the two `meta.json`
   records into `worklog.md`. Build the Q3 synthetic PDF with `pymupdf` in a scratch
   directory (page image rendered from text A, invisible text layer B via
   `insert_text(..., render_mode=3)`), run `render.py` with and without `--force-ocr`, and
   record which words each `pages/001.md` contains. Q3's Borgmann 2006 forced run goes
   through the front door, `resolve.py --citekey borgmannTechnologyCharacterContemporary2006
   --force-ocr [--allow-mocr]`, so the cache bypass is exercised live; it is long (311
   pages through EasyOCR, or mocr with `--allow-mocr`); run it once, record the pages
   where "in tum" disappeared, and keep the resulting render.

### Verification
- Run: `uv run pytest tests/test_bibliography_renderer.py tests/test_bibliography_resolve.py tests/test_bibliography_ingest.py tests/test_bibliography_blockquote.py -q`
- Positive signal: all pass, including the five-renderer staleness case and the
  forced-path record case.
- Failure signal: any version-2 record reported current; a forced run that invoked a
  non-OCR tier stub; a `located` label missing from blockquote output.
- Run: `uv run --with pymupdf4llm --with docling --with easyocr python "$BIB/render.py" "/home/brian/Zotero/storage/XD39JLVP/Borgmann - 2006 - Technology and the character of contemporary life a philosophical inquiry.pdf" /tmp/bib019/borgmann2006 && cat /tmp/bib019/borgmann2006/meta.json`
  and the same for `XCGCBRF7/Borgmann - 1987 - ….pdf` into `/tmp/bib019/borgmann1987`.
- Positive signal: 2006 record has `extraction: "text-layer"`, a limitation naming 311
  of 311 pages and "Adobe Acrobat 9.55 Paper Capture Plug-in"; 1987 record has
  `extraction: "text-layer"` and no page-image limitation.
- Failure signal: either record lacks `limitations`, or the 1987 record carries a
  page-image sentence.
- Docs: `uv run pytest tests/test_bibliography_skill.py tests/test_skill_reference_integrity.py tests/test_skill_descriptions.py tests/test_skill_frontmatter_yaml.py -q`.

### Finished-work implication
Human judgment after Outcome F (see UAT): whether the state line and `limitations`
read as advice rather than verdict, and whether the per-quotation source check is
workable for a delegated reader on a long book.

## Outcome B: trash awareness and the read-only collection listing

**Goal:** `resolve.py --citekey` on a trashed key retrieves it, prints `in trash`, exits 1;
author, title, and DOI searches keep Zotero's exclusion and say so on no-match;
`collection.py --list` prints every item of a collection with citekey, attachment state,
and a trash mark; `update_item.py --list` calls the shared listing.
**Depends on:** nothing (independent of A).
**Owns:** T1, L1; the trash-awareness section of the design.

### Files and consumers
- Modify: `$BIB/zotero_local_api.py` — `fetch_search_page(..., include_trashed=False)`
  adds `includeTrashed=1`; `search_items(query, *, include_trashed=False)`;
  `item_in_trash(item) -> bool` reads `data.deleted`; `library_base(library) -> str` returns
  `/users/0` or `/groups/<id>`; `get_collection_items(library, key, *, include_trashed=True)`
  moved from `update_item.py`, listing `/collections/<key>/items` (children included)
  paginated; pure `summarise_collection(items) -> list[dict]` groups attachments under
  parents and yields `key, citekey, title, itemType, in_trash, attachments: [{filename,
  in_trash}]`.
- Modify: `$BIB/resolve.py` — `Paper.in_trash: bool = False`; `paper_from_local_item`
  sets it; the citekey token's sweep passes `include_trashed=True` (the widening tokens
  do not); `print_match` prints `state: in trash` and `main` counts it as a failure;
  `print_no_match` for author/title/DOI appends "trashed items are excluded from this
  search".
- Create: `$BIB/collection.py` — `--list <name-or-key> [--library L]` only in this
  outcome; name resolution via `copy_item.find_library`/`find_collection` over
  `copy_item.get_libraries()` (zotero-api-plus `/api/plus/libraries`, per the ruling in
  deviation 1), after a `/api/plus` probe; a bare 8-character key is accepted directly; ambiguous name errors
  with candidate keys and parents; output one row per item: `key  citekey  title
  [in trash]  attachments: n (names)`, total line.
- Modify: `$BIB/update_item.py` — `--list` imports `get_collection_items` from the shared
  module and feeds `summarise_items` the top-level rows (filter `summarise_collection`
  parents), marking trashed rows.
- Modify docs: `references/resolve-and-render.md` (the `in-trash` state and exclusion),
  `SKILL.md` front door row for `in trash` and the exclusion sentence,
  `references/zotero-writes.md` gains a "List a collection (read-only)" section,
  `references/troubleshooting.md` row `in trash`.
- Modify: `tests/test_bibliography_skill.py:69-72` regex gains `collection`.
- Test: `tests/test_bibliography_zotero_local_api.py` (`includeTrashed` param presence
  per mode, `summarise_collection`, `library_base`),
  `tests/test_bibliography_resolve.py` (trashed envelope → `in_trash`, state line, exit
  1; no-match message for author), `tests/test_bibliography_update.py` (`--list` still
  works through the shared function with a stub), `tests/test_bibliography_collection.py`
  (new: parser, ambiguous name error, row rendering).
- First real consumer: `resolve.py --citekey borgmannTechnologyCharacterContemporary1987`.

### Work
1. Red tests above. For `fetch_search_page`, stub `httpx.get` and assert the params dict
   carries `includeTrashed` only when asked.
2. Green: shared module first, then `resolve.py`, then `collection.py`, then the
   `update_item.py` switch. Remove `update_item.get_collection_items`.
3. Docs and the regex. Operational T1 against `D7IV2YRB`.

### Verification
- Run: `uv run pytest tests/test_bibliography_zotero_local_api.py tests/test_bibliography_resolve.py tests/test_bibliography_update.py tests/test_bibliography_collection.py -q`
- Positive signal: pass, including the exit-1 `in trash` case and the untrashed
  positive control (same envelope without `deleted` resolves `rendered`/`ready-to-render`).
- Failure signal: trashed envelope reported as a live state; `includeTrashed` sent on
  the author sweep.
- Run: `uv run "$BIB/resolve.py" --citekey borgmannTechnologyCharacterContemporary1987 --no-render; echo exit=$?`
  and `uv run "$BIB/resolve.py" --author Borgmann --year 1987 --no-render`.
- Positive signal: first prints `state: in trash`, `exit=1`; second reports no match
  and names the trash exclusion.
- Failure signal: `rendered` for the first; a match for the second.

### Finished-work implication
L1 at UAT: `collection.py --list "Sage SRM Guide"` against the live collection; the
human checks the count and attachment states against Zotero's pane.

## Outcome C: stock write primitive, membership, item trash and restore

**Goal:** `zotero_local_api.py` can read, PATCH, and POST items and collections on
Zotero 10 with the version protection the design specifies; `item_collections.py` and
`trash_item.py` preview, apply behind `--apply --expect-version N`, and report
`accepted` and `verified` separately; `write_gate.py` carries the shared gate.
**Depends on:** B (`library_base`, `item_in_trash`, listing for previews; name resolution via `copy_item.get_libraries()`).
**Owns:** W1, W3, W4, R1, L2, L3; D1, D2 (item half), D5, D6.

### Files and consumers
- Modify: `$BIB/zotero_local_api.py` —
  `StockWriteUnavailable(RuntimeError)`; `require_stock_writes()` calls
  `zotero_auth.server_id()` and raises `stock writes need Zotero 10` when `None`;
  `read_object(library, kind, key, *, include_trashed=True) -> dict` (GET, raises
  `LibraryQueryError` on non-2xx, returns the envelope);
  `WriteResult(status: Literal["accepted","conflict","refused","failed"], version: int | None,
  body: str, current: dict | None)`;
  `write_object(library, kind, key, body, expected_version) -> WriteResult` sends PATCH
  with `credentials()` headers plus `If-Unmodified-Since-Version`, 204 → `accepted` with
  `Last-Modified-Version`, 412 whose body names `Zotero-Server-ID` → `refused`, other
  412 → `conflict` with a fresh `read_object`, 401 → `forget_key` and one retry, 403 →
  `refused` naming the library, 400 → `failed` with the body;
  `create_objects(library, kind, bodies) -> dict` POSTs ≤ 50 bodies and returns Zotero's
  `{successful, unchanged, failed}`. Transport goes through one seam
  `_http_request(method, url, *, headers, json, params, timeout)` so tests stub it.
- Create: `$BIB/write_gate.py` — `OperationClass = Literal["modify","create","register"]`;
  `add_gate_arguments(parser, cls)` adds `--apply` and the class's expected-state flags
  (`--expect-version` for modify only; `--expect-collection`, `--expect-parent`,
  `--expect-library` for create; `--expect-collection` for register);
  `check_gate(args, cls, *, previewed) -> str | None` returns the refusal text
  (`changed since preview`, `target changed`, or the usage error for missing flags);
  `format_apply_command(argv, cls, expected) -> str`;
  `report(accepted: bool, verified: bool | None, reason: str | None) -> tuple[str, int]`
  returns the final line (`accepted; verified`, `accepted; not verified: <reason>`,
  `not accepted: <reason>`) and the exit code (0 only for accepted and verified).
- Create: `$BIB/item_collections.py` — `--key K [--library L] (--add C | --remove C)`;
  preview reads the item (`include_trashed=True`), resolves `C` by name or key, prints
  title, library, version, `collections` before and after with names, and the exact apply
  command; apply re-reads, compares version to `--expect-version`, PATCHes
  `{"collections": [...]}`, reads back, verifies the target key is present (add) or
  absent (remove).
- Create: `$BIB/trash_item.py` — `--key K [--library L] [--restore]`; preview prints
  item type, title, parent key and title (attachment or note), filename and size from
  `data.filename` and the storage path when an attachment, `relations` entries under
  `owl:sameAs`, child count (`/items/<key>/children`), current `deleted`, version, apply
  command; apply PATCHes `{"deleted": true|false}` and verifies by `read_object` with
  `includeTrashed=1`.
- Modify docs: `references/zotero-writes.md` (sections for the two helpers, the modify
  class protection, the GET-only preview note, "no helper sends DELETE", the
  `accepted`/`verified` report); `SKILL.md` write-boundary rows and the precondition
  naming Zotero 10 for stock writes; `references/troubleshooting.md` rows `changed since
  preview`, 412 conflict, 403, `stock writes need Zotero 10`, `accepted; not verified`.
- Modify: `tests/test_bibliography_skill.py` regex gains `item_collections|trash_item`.
- Test: `tests/test_bibliography_zotero_local_api.py` (primitive over the stubbed seam:
  headers carried, `If-Unmodified-Since-Version` equals the argument, 204 → accepted with
  version, 412 → conflict with current object and no second request, 412 server-ID body
  → refused, 401 → one retry, `require_stock_writes` raises when `server_id()` is None
  and no request is sent), `tests/test_bibliography_write_gate.py` (per-class flag sets,
  refusals, report lines and exit codes), `tests/test_bibliography_item_collections.py`
  and `tests/test_bibliography_trash_item.py` (parser rejects a write without `--apply`
  [W4]; preview issues only GETs and prints version N [W1]; apply with
  `--expect-version N` after the stub returns N+1 refuses `changed since preview` and
  sends no PATCH [W1]; with N held and the seam answering 412, output says `conflict` and
  no success word [W1]; accepted then read-back without the change prints `accepted; not
  verified` and exits non-zero [R1]; `server_id()` None → refusal before any request
  [W3]).
- First real consumer: the Sage team's filing case, `item_collections.py --key <k> --add
  "Sage SRM Guide"` (L2 at UAT).

### Work
1. Red tests as listed, one helper at a time, primitive first.
2. Green: primitive and gate; `item_collections.py`; `trash_item.py`. Each helper's
   `main` handles `zotero_auth.AuthorizationError` like `update_item.py:544-550`.
3. Docs and regex. No live write before UAT; preview commands may be run live and their
   output recorded.

### Verification
- Run: `uv run pytest tests/test_bibliography_zotero_local_api.py tests/test_bibliography_write_gate.py tests/test_bibliography_item_collections.py tests/test_bibliography_trash_item.py -q`
- Positive signal: pass, with the seam recording exactly the requests each case allows
  (zero writes in preview, zero after a refusal, one PATCH on apply).
- Failure signal: any PATCH recorded in a preview or refusal case; a success word
  printed after a 412 or an unverified read-back.
- Run: `uvx ruff check "$BIB" tests` (also catches a multi-exception clause in a
  `>=3.11` helper only if the project's per-file target is set; the implementer checks
  the clause rule by reading, per project `CLAUDE.md`).

### Finished-work implication
L2 and L3 at UAT on scratch objects; the human judges whether the previews say enough
to approve a membership or trash change without opening Zotero.

## Outcome D: item creation and collection create, rename, trash, restore

**Goal:** `create_item.py` previews the full payload and creates one item in a named
collection behind `--apply --expect-collection KEY --expect-library ID`; `collection.py`
gains `--create NAME [--parent KEY]`, `--rename KEY NAME`, `--trash KEY`, `--restore KEY`
with descendant listing and per-descendant restore; create and register parsers do not
accept `--expect-version`.
**Depends on:** C.
**Owns:** W2, L4, L5; D2 (collection half).

### Files and consumers
- Create: `$BIB/create_item.py` — `--type T --set F=V ... --author 'Last, First'
  --creator TYPE='Last, First' [--collection C] [--library L]`; imports
  `parse_field_assignment`, `parse_creator_name`, `parse_creator_spec` from
  `update_item.py`; preview prints the JSON body (`itemType`, fields, `creators`,
  `collections: [KEY]`), the resolved library (name and stock id), the resolved collection
  key, and the apply command with `--expect-collection KEY --expect-library ID`; apply
  re-resolves both, refuses `target changed` on a difference, POSTs via
  `create_objects`, takes the key from `successful`, reads it back, verifies the fields
  set, the creator list, and the collection key, and prints key and `citationKey`
  (citekey appears once BBT assigns it; absence is reported as `citekey: not yet
  assigned`, not as a verification failure).
- Modify: `$BIB/collection.py` — `--create` (POST `{"name", "parentCollection":
  KEY|false}`, create class with `--expect-parent` when a parent is named and
  `--expect-library`); `--rename KEY NAME` (modify: PATCH `{"name"}`); `--trash KEY`
  (modify: preview lists descendant collections from `/collections/<key>/collections`
  recursively, which works because they are still live at trash time, and the member
  item count; PATCH `{"deleted": true}`; verify the parent and each descendant by direct
  key read `/collections/<key>` with `deleted: true`; the apply output ends with the
  exact restore command, `--restore KEY --descendants K1,K2,…`); `--restore KEY
  [--descendants K1,K2,…]` (modify: PATCH `{"deleted": false}` on the parent, then on
  each listed descendant from the shallowest to the deepest, each with its own read
  version; verify all read back `deleted: false` and the item membership is unchanged;
  without `--descendants` the helper restores the parent only and prints `descendants
  unknown: Zotero's collection listings exclude the trash; pass --descendants from the
  trash output or restore them in Zotero`). The parser rejects two verbs in one call.
  **Why `--descendants`:** the installed local API's collection listing routes call
  `Zotero.Collections.getByParent(id)` and `getByLibrary(libraryID, recursive)` without
  the `includeTrashed` argument (`server_localAPI.js:993-995`, extracted from omni.ja
  2026-10-12), there is no `/collections/trash` route (only `/items/trash`,
  `server_localAPI.js:1191-1195`), and `meta.numCollections` also excludes trashed
  children (`collection.js:776`). Only a direct key read returns a trashed collection
  (`getByLibraryAndKey`, `server_localAPI.js:1017`; `deleted` is in its JSON,
  `collection.js:159`). So the trash-time listing is the record of descendants and is
  carried into restore by the user, as the expected-state flags carry the preview.
- Modify docs: `references/zotero-writes.md` (create class protection, the two
  helpers, collection trash semantics); `SKILL.md` write-boundary rows;
  `references/troubleshooting.md` row `target changed`.
- Modify: `tests/test_bibliography_skill.py` regex gains `create_item`.
- Test: `tests/test_bibliography_create_item.py` and additions to
  `tests/test_bibliography_collection.py`: preview prints payload, keys, and the apply
  command containing both flags; `--apply` without them exits 2 with a usage error;
  with them, a stub that re-resolves the collection to a different key → `target
  changed` and no POST; `--expect-version` rejected by `create_item.py`'s parser and by
  `collection.py --create` [W2]; trash preview lists descendants from the stubbed
  `/collections/<key>/collections` pages and sends no write; trash apply verifies each
  descendant by direct key read and prints a restore command containing every
  descendant key; restore with `--descendants` sends one PATCH per key in the designed
  order after the parent, each verified by direct key read; restore without
  `--descendants` sends exactly one PATCH and prints the `descendants unknown` line;
  the stub for `/collections/<key>/collections` returns only untrashed children (the
  installed API's behaviour) so a test that relied on listing trashed descendants
  would fail; no `DELETE` method ever reaches the seam (assert over every recorded
  request in every case).

### Work
1. Red tests as listed.
2. Green: `create_item.py`, then `collection.py` verbs.
3. Docs and regex.

### Verification
- Run: `uv run pytest tests/test_bibliography_create_item.py tests/test_bibliography_collection.py -q`
- Positive signal: pass; the recorded request log for every case contains only GET,
  PATCH, POST.
- Failure signal: a DELETE in any log; a create parser that accepts `--expect-version`;
  a POST after `target changed`.

### Finished-work implication
L4 and L5 at UAT on a scratch parent collection with one child and one member item.

## Outcome E: auto-export registration

**Goal:** `register_export.py` previews a BBT auto-export registration, applies it
behind `--apply --expect-collection KEY`, and reports `accepted`, `completion`, and
`content` as separate observations, `verified` only when both are positive.
**Depends on:** C (gate module, `require_stock_writes`), B (listing for a citekey).
**Owns:** E1, E2, E3.

### Files and consumers
- Create: `$BIB/register_export.py` — `--collection "<lib>/<path>" --path FILE.bib
  [--translator NAME] [--replace]`; preview resolves the library and the collection path
  through `copy_item.get_libraries()` and `find_collection` segment by segment (a missing segment
  is an error; the helper never lets BBT create a collection), prints the key,
  translator (default `Better BibLaTeX`), the absolute path, whether a file exists with
  size, mtime and sha256, `registration state: unknown` with the `autoexport.add`
  semantics sentence from the design, and the apply command; apply re-resolves, refuses
  `target changed`, calls BBT `autoexport.add` over JSON-RPC (`resolve.rpc` shape) with
  `[bbt_collection_path, translator, path, {}, replace]` where `bbt_collection_path` is
  built by a pure `bbt_collection_path(library_id, names) -> str` as
  `/<libraryID>/<name>/<subname>` using the Zotero `libraryID` from
  `/api/plus/libraries` and the resolved collection names, never the CLI string.
  **Why:** BBT's parser (`content/collection.ts`, upstream master read 2026-10-12;
  installed 9.0.71 behaves the same per Astra's check) requires a leading slash
  (`collection path … is not an absolute path`), splits on
  `/^\/(?<libraryID>[^/]*)(?<treepath>\/.+)/`, matches an all-digit first segment
  against `libraryID` or `groupID` and a non-numeric one against the library *name*;
  "My Library" is not special-cased, so the numeric form is the unambiguous one. The
  helper treats a result whose `key` equals the
  expected key as `accepted` and any other result or error as `not accepted` (a BBT
  error naming another collection or translator is printed verbatim [E3]); then
  completion: `resolve.post_run_autoexport(path)` → `classify_autoexport_response`;
  `observed` when `triggered` and the file's mtime advances past the trigger timestamp
  within a 30 s poll, else `not observed` with the reason (`no zotero-api-plus` on 404
  or transport error, `trigger refused: <kind>`, `no modification seen within 30 s`);
  content: `resolve.check_bib(text, citekey)` with one citekey from
  `get_collection_items` → `satisfied` or `not satisfied`; final line
  `accepted; completion <state>; content <state>; verified|not verified`, exit 0 only
  when verified. The previewed size and hash are printed beside the new ones as an
  observation.
- Modify docs: `references/zotero-writes.md` (register section with the semantics),
  `references/notes-and-bibliographies.md` (bootstrap step 1–6 may be done by the helper;
  manual route retained), `SKILL.md` write-boundary row, `references/troubleshooting.md`
  rows `accepted; completion not observed`, `content not satisfied`.
- Modify: `tests/test_bibliography_skill.py` regex gains `register_export`.
- Test: `tests/test_bibliography_register_export.py` — `bbt_collection_path(1,
  ["Sage SRM Guide", "Readings"])` is `/1/Sage SRM Guide/Readings` and the RPC stub
  receives exactly that string as its first parameter (never the CLI's `My
  Library/...` form); preview sends no RPC and prints
  the apply command; `--expect-version` rejected [W2]; `--apply` without
  `--expect-collection` is a usage error; stubbed `autoexport.add` returning the
  expected key → `accepted`; returning another key → `not accepted`; completion with
  `post_run_autoexport` stubbed to `None` → `not observed: no zotero-api-plus`, content
  still evaluated from the existing file, exit non-zero [E2a]; stubbed `triggered` with a
  file whose bytes do not change but whose mtime is advanced by the test → `observed`,
  content reported independently [E2b]; `triggered` with no mtime change → `not
  observed`; content `satisfied` versus `not satisfied` with a fixture `.bib`.

### Work
1. Red tests as listed; time is injected (`now()` parameter) so the poll is instant.
2. Green: the helper.
3. Docs and regex.

### Verification
- Run: `uv run pytest tests/test_bibliography_register_export.py -q`
- Positive signal: pass; the degraded cases exit non-zero and print both observations.
- Failure signal: `verified` printed when either observation is negative; completion
  inferred from a hash.

### Finished-work implication
E1 and E3 at UAT; the human judges whether the registration matches a hand-made
"Keep updated" export in Zotero's BBT preferences pane.

## Outcome F: release 0.19.0

**Goal:** Skill text is coherent across all helpers, the architecture page reflects the
new helpers and boundary, version surfaces agree at 0.19.0, and the full gates pass.
**Depends on:** A–E.
**Owns:** F1; the documentation checklist in the design.

### Files and consumers
- Modify: `$BIB/SKILL.md` — final pass over Preconditions (Zotero 10 for stock writes;
  zotero-api-plus required by every write helper for name resolution and by the export
  trigger, optional for pure resolution and rendering), Front door, Source-fidelity rule,
  Write boundary table (one row per helper: preview command, operation class, what the
  preview must show), Completion evidence (`accepted` and `verified` separately with the
  read-back or export content named). Keep under 500 lines
  (`tests/test_bibliography_skill.py:60`).
- Modify: `docs/architecture/plugins/denubis-academic/0-context.md` — helper table row,
  the zotero-api-plus boundary row, the boundary bullet on rendered Markdown authority.
- Modify: `plugins/denubis-academic/.claude-plugin/plugin.json`,
  `plugins/denubis-academic/.codex-plugin/plugin.json` (carries a `version` field; verified 2026-10-12),
  `.claude-plugin/marketplace.json` entry, and a new `## [denubis-academic] 0.19.0`
  entry at the top of `CHANGELOG.md` in the repository's existing voice (what changed,
  tests, what is not verified).
- Confirm: `docs/architecture/decisions/README.md` index line for 0028 is present
  (already edited, uncommitted).
- First real consumer: a fresh session invoking `/denubis-academic:using-bibliography`
  from the installed plugin.

### Work
1. Documentation pass with a bounded agent inspection: for every helper, run `--help`
   and confirm each documented flag exists and each documented preview line is produced
   by the code (grep the format strings), recording the check per helper in `worklog.md`.
2. Version and changelog edits.
3. Full gates.

### Verification
- Run: `uv run pytest -q` (whole suite; note any unrelated pre-existing failure by
  name with its output).
- Run: `uv run pytest tests/test_bibliography_*.py tests/test_skill_*.py tests/test_marketplace_sync.py tests/test_codex_marketplace.py -q`
- Run: `uvx ruff check . && uvx ruff format --check plugins/denubis-academic tests`
- Run: `git diff --check`
- Positive signal: all pass; `grep -n '"version"' plugins/denubis-academic/.claude-plugin/plugin.json` shows 0.19.0 and `rg -n '0.19.0' .claude-plugin/marketplace.json CHANGELOG.md` hits the entry and the changelog heading.
- Failure signal: any manifest at 0.18.0; a bibliography reference naming a flag no
  helper has (caught by the inspection in step 1); ruff findings.

### Finished-work implication
The UAT below.

## Human UAT (after Outcome F, after all mechanical checks pass)

Run from a fresh session with the installed plugin, against the live Zotero. Scratch
objects are created in My Library and trashed afterwards; the first write prompts
Zotero's authorisation modal (choose Always Allow).

1. **Quoting procedure (Contract 1 judgment).** Resolve
   `borgmannTechnologyCharacterContemporary2006`; read the state line and the advisory.
   Dispatch one reader on three pages using `references/reading-and-quoting.md`. Judge:
   does the limitation line read as advice, and is the per-quotation page-image check
   workable? Falsifier: the reader calls a quotation `verified` without opening the page,
   or the state line reads as "safe to quote".
2. **L1.** `collection.py --list "Sage SRM Guide"`; compare the count and attachment
   states against Zotero's pane. Falsifier: a count mismatch or a trashed row shown live.
3. **L2.** On a scratch item in My Library: `item_collections.py --key K --add
   <scratch collection>` preview, then the printed apply command; read back in Zotero;
   `--remove` reverses it. Falsifier: a second record appears, or the preview did not say
   enough to approve.
4. **L3.** `trash_item.py` on a scratch attachment key: preview, apply, confirm in
   Zotero's trash that only the attachment moved; `--restore`. Falsifier: the parent or a
   sibling moved.
5. **L4.** `create_item.py --type book --set title=... --author 'Scratch, Author'
   --collection <scratch>`; preview, apply, read back. Falsifier: wrong collection or
   missing field.
6. **L5.** Scratch parent collection with one child and one member item: `collection.py
   --trash`, then the printed `--restore KEY --descendants CHILD` command; confirm in
   Zotero both collections return and the item is still a member. Also run `--restore`
   without `--descendants` on a re-trashed parent and confirm the helper says the
   descendants are unknown rather than claiming them restored. Falsifier: child left in
   trash silently, membership lost, or any erasure.
7. **E1, E3.** With zotero-api-plus running: `register_export.py --collection "My
   Library/<scratch>" --path /tmp/bib019/scratch.bib`, preview then apply; open BBT's
   automatic-export preferences and compare with a hand-made "Keep updated" export.
   Re-run: expect the reschedule message. Point the same path at another collection
   without `--replace`: expect refusal. Falsifier: `verified` printed while the file is
   missing the citekey, or the registration differs materially from the manual one.
8. **Q3 live.** Inspect two pages of the forced Borgmann 2006 render recorded in Outcome
   A beside their page images. Falsifier: the forced text still carries the slips.

## Git lifecycle

- Work stays on `worktree-bibliography-0.19-design` in this worktree. Invocation of the
  execution skill authorises private checkpoint commits here; the first checkpoint
  includes the design, ADR 0028, and the README index line already present uncommitted.
- No push, publication, or history rewrite during execution.
- After accepted UAT: fold checkpoints into one commit per outcome (or fewer if the human
  prefers), preserving the accepted tree, then rerun the Outcome F gates and
  `git diff --check`.
- Integration into `main`, push, and worktree cleanup wait for a separate delivery
  request (`denubis-plan-and-execute:finishing-a-development-branch`).
