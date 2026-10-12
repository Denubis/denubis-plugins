# Bibliography 0.19: quotation verification, Zotero CRUD, and auto-export registration

**Status:** Current design

## Purpose

Seven defects were found on 10 and 11 October 2026 while the Sage SRM Guide team used
`denubis-academic:using-bibliography` 0.18.0: a scanned book's embedded OCR was
presented as exact quotation authority; a trashed item resolved as live; filing an
existing item into a collection was only possible by copying it, which duplicated a
record and carried a wrong attachment; the existing collection listing was
undocumented in the skill; no helper could trash an attachment, create an item, or
register a Better BibTeX auto-export.

The review of the first draft found a common defect in the proposed fixes: each asked a
proxy to prove more than it can. Image coverage was made to stand for provenance, a
version number for approval, and an existing file for evidence of execution. This design
is reduced to three contracts that remove those proxies:

1. **Extraction supports reading; exact quotation requires source verification.** The
   renderer records how text was extracted and what limits that has. It never certifies
   that text is safe to quote.
2. **Approve the intended change; protect the state it depends on.** Every write
   previews its target and effect. Modifying an existing object is protected by that
   object's version. Creation and registration have their own concrete previews and
   re-check the state they resolved, without an invented version.
3. **Report only the outcome observed.** A request being accepted is reported
   separately from its effect being verified. Writes are verified by read-back, exports
   by their resulting content.

Stock Zotero 10 local-API writes, trash-only deletion, and an explicit forced-OCR path
are retained from the first draft.

## Authority Sources

| Decision or instruction | Exact source | Resolver | Resolution condition |
|---|---|---|---|
| The five-item defect report that opened this work, "let us discuss" | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:35604375-2496-43c8-9e76-3045c2a77f9c` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:35604375-2496-43c8-9e76-3045c2a77f9c --reference-only --json` | One user message of 2026-10-10T23:36Z beginning with the pasted "Defects in denubis-academic:using-bibliography (0.18.0)" |
| Scope widened to add-item, add from another collection or library, "all the basic CRUD capabilities", design all, and review OCR options | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:3bfc219f-1bc6-4c2c-bcfd-1f159b96cbf7` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:3bfc219f-1bc6-4c2c-bcfd-1f159b96cbf7 --reference-only --json` | One user message of 2026-10-11T23:08Z beginning "ok, and yes we want to add item" |
| Auto-export of a `.bib` from a collection without intervention; work in a worktree | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:d540a787-7c80-4459-9eca-3499266aabfe` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:d540a787-7c80-4459-9eca-3499266aabfe --reference-only --json` | One user message of 2026-10-11T23:29Z beginning "oh, one other thing" |
| Route ruling: "whatever we need that is as simple and as reliable as possible", answering the stock-API-versus-extension question with the stock API and trash-not-erase recommended | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:f4364e99-f5fc-4c4f-b02d-ae3b115f517c` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:f4364e99-f5fc-4c4f-b02d-ae3b115f517c --reference-only --json` | One user message of 2026-10-11T23:58Z reading "whatever we need that is as simple and as reiable as possible" |
| Trash ruling for every object type: "we just want to send things into trash, we never want to expunge right now", qualified next as "where trash exists we use it" | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:1573dc00-efe6-42bf-8950-09443090812b` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:1573dc00-efe6-42bf-8950-09443090812b --reference-only --json` | One user message of 2026-10-12T00:17Z beginning "um, yes, we just want to send things into trash" |
| Generalisation ruling: "right, please generalise. I don't want increasing clockwork epicycles", adopting the three contracts quoted in Purpose and the instruction to stop making the renderer an authority on whether text is safe to quote; the same message carries the second review's four remaining findings | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:1ff0eb70-ff50-415e-b4a8-18b3e11d1af8` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:1ff0eb70-ff50-415e-b4a8-18b3e11d1af8 --reference-only --json` | One user message of 2026-10-12T00:35Z containing the pasted review beginning "Partly." followed by "right, please generalise" |
| Acceptance of the design as written after the third review's corrections: "great, lock it in" | `ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:38e8b48a-9959-407e-81df-01dba50ec6ca` | `cc-search-chats resolve ccchat:v1:claude:e65bf924-a18d-429a-881d-418e144eb062:uuid:38e8b48a-9959-407e-81df-01dba50ec6ca --reference-only --json` | One user message of 2026-10-12T00:54Z reading "great, lock it in" |

## Universe of discourse

Actors: the human author; Claude Code and Codex sessions running the skill; delegated
reader and bibliography agents on a writing project.

Systems and contracts:

- **Zotero 10.0.6** (Flatpak, server ID `g6bzZS56RsjG` on this machine). Its stock
  local API at `http://localhost:23119/api/` serves reads ungated and, on Zotero 10,
  item, collection, and search writes behind the server-ID and API-key gate that
  `zotero_auth.py` already satisfies. Source read from the installed bundle,
  `chrome/content/zotero/xpcom/server/server_localAPI.js` (2,722 lines, extracted from
  `/var/lib/flatpak/app/org.zotero.Zotero/current/active/files/share/zotero/app/omni.ja`
  on 2026-10-12), and cross-checked against `zotero/zotero` main the same day.
- **Better BibTeX 9.0.71**, JSON-RPC at `/better-bibtex/json-rpc`: citekeys,
  `item.collections`, `item.attachments`, `item.export`, and `autoexport.add`. Its
  `item.search` is broken on Zotero 10 (BBT issue 3587) and is already unused.
- **zotero-api-plus 0.7.2** (`~/people/Brian/zotero-api-plus`), thirteen endpoints.
  Unchanged by this design; `run-autoexport` is used when present.
- **The render cascade** in `renderer.py`: pymupdf4llm, Docling, Docling with EasyOCR,
  and the confirm-gated dots.mocr tier on the local RTX 4090.
- **The zettelkasten** `~/zettelkasten/papers/<citekey>/` with `meta.json` as the
  extraction record a reader consults.

Consumers of the changed contracts: `resolve.py`'s state line; `blockquote.py`; the
`annotated-bibliography` and `paper-review` skills and the reference files that read
`meta.json`; `tests/test_bibliography_*`; the architecture page
`docs/architecture/plugins/denubis-academic/0-context.md`.

Exclusions: Zotero 7 to 9 for the new write helpers (no stock write routes);
cross-library membership (a Zotero item lives in exactly one library, so "add from
another library" remains `copy_item.py`); any erasure; library-level or recursive
auto-exports (`autoexport.add` cannot register them); replacing the OCR engine; saved
searches.

## Current state

**Quotation authority.** `meta.json` records `"ocr"` as which cascade tier ran. A Paper
Capture scan with an embedded OCR layer passes tier 1 and is recorded `"ocr": false`,
and `SKILL.md`'s source-fidelity rule reads that as exact-quotation authority. Observed
2026-10-12: `borgmannTechnologyCharacterContemporary2006` (group library
`2026-bbs-cat-agent-philosophy-metaphor`, attachment `XD39JLVP`) is 311 pages, producer
"Adobe Acrobat 9.55 Paper Capture Plug-in", one page-sized image on all 311 pages,
rendered `"renderer": "pymupdf4llm", "ocr": false`, with 29 OCR slips such as "in tum"
and "Jiving" in `full.md`. The reviewer on the Sage guide verified ten quoted pages
against page images by hand (sage-srm-guide session, 2026-10-10T21:17Z).

**Cache predicate.** `render_metadata_is_current` (`renderer.py:62`) treats any renderer
other than pymupdf4llm and docling as current regardless of `render_version`, so a
version bump does not invalidate mocr, HTML, or Pandoc records.

**Forced OCR.** `--allow-mocr` permits escalation only after earlier tiers fail
(`render_pdf_with_fallback`). A scan whose embedded layer passes the quality gate never
reaches OCR; `--force` only bypasses the cache.

**Trash.** `GET /api/users/0/items/D7IV2YRB` returns `"deleted": true` for the 1987
Borgmann record, which `resolve.py` reported as `rendered` earlier the same day.
Quicksearch excludes trashed items unless `includeTrashed=1`; a direct key read returns
them; nothing in the skill reads the `deleted` field.

**Collections.** The only write that files an item into a collection is
`copy_item.py`, which also tops up attachments from the linked source. That produced
the duplicate Paper B record and the version 1 PDF under
`torringtonTeachingStudentsHow2025a` (bib-populate agent report, sage-srm-guide
session, 2026-10-10). A paginated collection listing already exists as
`update_item.py --list <collection>` (`get_collection_items`, `update_item.py:327`),
but no skill reference documents it, so the Sage team hand-typed the local-API call.
The listing does not pass `includeTrashed` and does not mark trashed rows.

**Stock write contract, verified in the installed source.** `writeSingleObject` (PATCH
or PUT on `/items/:key` and `/collections/:key`) merges the body over `obj.toJSON()` for
PATCH, applies it with `fromJSON(json, {strict: false})`, requires
`If-Unmodified-Since-Version` or a `version` property, answers 412 on mismatch and 204
with `Last-Modified-Version` on success. `writeMultipleObjects` (POST on `/items` and
`/collections`) takes up to 50 objects and returns `{successful, unchanged, failed}`.
`deleteSingleObject` calls `eraseTx()` and is permanent; for items it cascades to child
notes and attachments and removes storage directories, for collections it erases
descendants and memberships. `Zotero.Item.fromJSON` handles `collections` through
`setCollections`, which resolves keys within the item's library and throws
`ZoteroMissingObjectError` for an unknown key. Both `Zotero.Item.fromJSON` and
`Zotero.Collection.fromJSON` accept `deleted` as a boolean; Zotero trashes a
collection's descendants with it but restores non-recursively. Probe results on
2026-10-12: uncredentialled `POST /items` 428, `PATCH /items/<key>` 400,
`DELETE /items/<key>` 428, a nonsense route 404.

**Auto-export.** BBT's `autoexport.add(collection, translator, path, displayOptions?,
replace?)` registers an enabled collection export, reschedules an existing one at the
same path and translator with its settings untouched, errors when the path is
registered to a different collection or translator unless `replace` is true, and
returns the collection's `libraryID`, `key`, and `id`. It creates the collection when
missing, cannot register a library export, hard-codes `recursive: false`, and has no
list or remove counterpart.

**OCR survey (read 2026-10-12 by a research agent; vendor-reported figures from each
project's README or model card).** On olmOCR-bench overall: Chandra 2 85.8
(github.com/datalab-to/chandra; weights under a modified OpenRAIL-M licence), dots.mocr
83.9 (github.com/rednote-hilab/dots.ocr), Surya 2 83.3 (github.com/datalab-to/surya),
olmOCR 2 82.4 (github.com/allenai/olmocr), Marker balanced 76.0
(github.com/datalab-to/marker), GLM-OCR 75.2 (huggingface.co/zai-org/GLM-OCR). On the
old-scans slice the only published figures found are olmOCR 2 at 47.7 and Chandra at
51.1 (arxiv.org/abs/2510.19817); none was found for dots.mocr. No source measured
dropped or invented lines over long book pages. The survey supports "insufficient
evidence to justify switching engines", not a ranking.

## Goals and non-goals

Goals:

1. Rendered text is a reading and locating aid; every exact quotation is verified
   against the source before it is called verified, whatever the renderer recorded.
2. The render record states how text was extracted and its known limits, and a scan
   can be sent to OCR on demand.
3. Resolution and listing report an item's trash state.
4. Gated helpers for collection membership, trash and restore, item creation,
   collection create, rename, trash and restore, and auto-export registration, each
   previewing its target and effect and reporting accepted and verified outcomes
   separately.
5. A read-only collection listing.
6. Skill text, tests, changelog, and version entries that make the above usable from a
   fresh session.

Non-goals: a renderer verdict on quotation safety; new zotero-api-plus endpoints; any
erasure; changing the OCR engines; Zotero 7 to 9 support for the new writes;
library-level auto-exports.

## Design

### Contract 1: extraction supports reading; quotation requires source verification

**Quoting rule.** Rendered Markdown, for every renderer and every source type, is a
reading text and a locator. An exact quotation is `verified` only after the quoted
wording has been checked against the source document itself: the PDF page image at the
physical page the render names, or the HTML snapshot or original attachment for non-PDF
sources. `blockquote.py` continues to prove that a string occurs in the render, which
locates the passage; it does not verify it. The three states a quotation can carry are
`located` (found in the render), `verified` (checked against the source), and
`unverified` (neither, or `NO MATCH`). The reading-and-quoting procedure asks the
reader to open the page image for every quotation it will call verified. The cost is
accepted: more checking when quoting, no classifier to maintain.

**Extraction record.** `meta.json` describes extraction, not safety. It keeps
`renderer`, `ocr`, `page_count`, `sha256_prefix`, and `source_pdf`, and adds:

- `extraction`: `"text-layer"` (the PDF's own layer was read), `"ocr"` (an OCR tier
  produced the text), or `"converted"` (HTML or Pandoc);
- `forced`: true when `--force-ocr` was used;
- `limitations`: a list of free-text observations the renderer can make cheaply and
  that a reader should know, such as `"311 of 311 pages carry a page-sized image; the
  text layer is likely third-party OCR (producer: Adobe Acrobat 9.55 Paper Capture
  Plug-in)"`, `"12 pages have no extractable text"`, or `"replacement characters on
  3 pages"`. These are advisory. Nothing in the skill grants or withholds authority on
  their basis.

`RENDER_VERSION` becomes 3 and `render_metadata_is_current` becomes a version-equality
test for every renderer, so each pre-0.19 record re-renders on next use and gains the
record above. `resolve.py`'s state line prints `extraction` and the first limitation,
for example `state: rendered (text-layer; 311/311 pages are page-sized images)`.

**Scan detection guides OCR.** The page-image count that feeds the limitation is also
offered as a prompt: when most pages carry a page-sized image and the record is
`text-layer`, the state line suggests `--force-ocr`. `--force-ocr` on `resolve.py`,
`ingest.py`, and `render.py` starts the cascade at the Docling-with-EasyOCR tier;
`--force-ocr --allow-mocr` goes straight to dots.mocr. Either way the record says
`extraction: ocr, forced: true`. The suggestion is advice; the reader's verification
duty under the quoting rule is the same before and after.

### Contract 2: approve the intended change; protect the state it depends on

`zotero_local_api.py` gains one write primitive over the stock API:
`write_object(method, library, kind, key, body, expected_version)` for PATCH on one
item or collection, and `create_objects(library, kind, bodies)` for POST. Both send
`zotero_auth.credentials()` headers and refuse before any request on a server without
a `Zotero-Server-ID` header (`stock writes need Zotero 10`). Neither reads a version
itself. A 412 is returned as `conflict` with Zotero's current object and never
retried.

Every helper has a preview that writes nothing and an `--apply` that performs exactly
the previewed change. What protects the change depends on what it depends on:

| Operation class | Preview shows | What `--apply` checks before writing | Protection during the write |
|---|---|---|---|
| Modify an existing item or collection (membership, trash, restore, rename) | The object as read, its `version`, and the resulting object | Re-reads the object; stops with `changed since preview` if its version differs from the previewed one (`--expect-version N` is required and must match); builds the payload from that read | `If-Unmodified-Since-Version: N`; Zotero's 412 covers the window after the read |
| Create an item or collection | The full JSON to be written, the resolved library, the resolved parent or collection key by name, and the exact apply command including `--expect-collection KEY` (or `--expect-parent KEY`) and `--expect-library ID` | Requires those flags; re-resolves the library and the named collection or parent and stops with `target changed` if a resolved key differs from the flag's value | None needed beyond acceptance; the new object has no prior state |
| Register an auto-export | The resolved collection key, translator, absolute path, whether a file exists there and its size and modification time, `registration state: unknown` with the `autoexport.add` semantics stated, and the exact apply command including `--expect-collection KEY` | Requires that flag; re-resolves the collection and stops with `target changed` if its key differs | None; the method is idempotent for a matching registration and errors for a conflicting one |

The expected-state flags are the interface that carries the previewed state into
apply: `--expect-version N` for the modify class, `--expect-collection KEY`,
`--expect-parent KEY`, and `--expect-library ID` for the create and register classes.
The preview prints the complete apply command so the user or agent copies it rather
than reconstructing it, and apply refuses to run without the flags its class needs.

There is no universal `--expect-version`; the flag exists only in the first class. All
three classes share the gate shape (no flag means preview, `--apply` means write) and
the refusal to proceed when the previewed state is no longer what was approved.

### Contract 3: report only the outcome observed

Every helper's final line separates two facts:

- `accepted`: Zotero or BBT accepted the request (a 204 with `Last-Modified-Version`, a
  `successful` entry from a POST, or an `autoexport.add` result);
- `verified`: the effect was observed. For a modify or create, the helper reads the
  object back and compares the fields it changed; for a trash, it reads the object with
  `includeTrashed=1` and confirms `deleted`; for a restore, the reverse; for an export,
  see below.

A helper that gets `accepted` but cannot verify says `accepted; not verified` with the
reason, and exits non-zero. It never prints a bare success.

**Export verification.** A changed file does not prove the requested export completed,
and an unchanged file does not prove it failed: a correct repeat export can write
identical bytes. So after `autoexport.add` is accepted, `register_export.py` reports
two observations separately and infers neither from the other:

- `completion`: `observed` when zotero-api-plus is present, `run-autoexport` returned
  `triggered`, and the file's modification time advanced past the trigger within a
  bounded wait; otherwise `not observed`, with the reason (no zotero-api-plus, trigger
  refused, or no modification seen). zotero-api-plus itself does not report export
  success, and the helper says so.
- `content`: `satisfied` when the file at the path parses as a bibliography and
  contains one citekey from the collection listing; `not satisfied` otherwise. The
  previewed size and hash are printed beside the new ones as an observation, not a
  verdict.

The export is `verified` only when both are positive. Any other combination is
reported as `accepted; completion <state>; content <state>` with a non-zero exit. The
acceptance criteria test the verified path and the honest degraded paths separately.

### Helpers

| Helper | Operation | Mechanism | Operation class |
|---|---|---|---|
| `collection.py --list <name-or-key> [--library]` | Read-only listing with trashed rows marked | `get_collection_items` moved from `update_item.py` into `zotero_local_api.py`, gaining `includeTrashed=1`; `update_item.py --list` keeps working by calling the shared function | read |
| `collection.py --create NAME [--parent KEY]` | Create collection | `POST /collections` | create |
| `collection.py --rename KEY NAME`, `--trash KEY`, `--restore KEY` | Modify collection | `PATCH /collections/<key>` with `name` or `deleted`; never `DELETE`. Trash preview lists the descendants Zotero will trash with it; restore clears the flag on each listed trashed descendant, deepest last | modify |
| `item_collections.py --key K [--library L] --add <collection> / --remove <collection>` | Membership | `PATCH /items/<key>` with the merged `collections` array | modify |
| `trash_item.py --key K [--library L]`, `--restore` | Trash or restore an item or attachment | `PATCH /items/<key>` with `deleted`. Preview shows title, parent, filename and size for an attachment, `sameAs` relations, and child count for a parent | modify |
| `create_item.py --type T --set F=V ... --author 'Last, First' [--collection C] [--library L]` | Create item | `POST /items`; the field grammar is `update_item.py`'s | create |
| `register_export.py --collection "<lib>/<path>" --path FILE.bib [--translator NAME] [--replace]` | Auto-export registration | BBT `autoexport.add`; default translator `Better BibLaTeX`, the one `ingest.py` already uses | register |

Collection name resolution is the one shared by `fetch.py` and `copy_item.py`; an
ambiguous name errors with the candidate keys. `copy_item.py` is unchanged and is
described as "copy between libraries with attachment top-up", never as the way to file
an existing item.

### Trash awareness in resolution

`zotero_local_api.py` surfaces `data.deleted` on every envelope; `paper_from_local_item`
carries `in_trash`. The exact-citekey sweep adds `includeTrashed=1`, so `resolve.py`
retrieves a trashed item, prints `in trash` in the state line, and exits 1 with that
reason. Author, title, and DOI searches keep Zotero's trash exclusion and say so in the
no-match message.

### Skill text and documentation

The readers of the old OCR rule are `SKILL.md`, `references/reading-and-quoting.md`,
`references/notes-and-bibliographies.md`, `references/resolve-and-render.md`,
`references/troubleshooting.md`, and `skills/annotated-bibliography/SKILL.md`; all
change.

- `SKILL.md`: the source-fidelity rule becomes Contract 1 in full (render is a
  locator; `located`, `verified`, `unverified`; verification against the source for
  every exact quotation; `limitations` and `--force-ocr` as advice). Preconditions name
  Zotero 10 for the new writes. The front door states the trashed-item exit and which
  searches exclude the trash. The write-boundary table gains one row per helper with
  its preview command, its operation class, and what the preview must show. Completion
  evidence requires `accepted` and `verified` to be reported separately for every
  write, with the read-back or export content named.
- `references/reading-and-quoting.md` and `references/notes-and-bibliographies.md`:
  reader labels and note templates carry the three quotation states; the page-image
  check is a step for every quotation, and for non-PDF sources the check is against the
  snapshot or attachment.
- `references/resolve-and-render.md`: the `meta.json` contract (`extraction`,
  `forced`, `limitations`, render version 3), `--force-ocr` as a cascade entry, the
  `in-trash` state, and the re-render of every pre-0.19 record.
- `references/zotero-writes.md`: one section per helper with preview and apply
  commands, the operation class and what protects it, the GET-only preview note, the
  statement that no helper sends `DELETE`, the `autoexport.add` semantics, and the
  `accepted` versus `verified` report.
- `references/troubleshooting.md`: `changed since preview`, `target changed`, 412
  conflict, 403 non-editable library, `stock writes need Zotero 10`, `in trash`,
  `accepted; not verified`, `accepted; completion not observed`, and `content not
  satisfied`.
- `skills/annotated-bibliography/SKILL.md`: its OCR sentence refers to Contract 1.
- After implementation: `docs/architecture/plugins/denubis-academic/0-context.md`
  (helper table, zotero-api-plus boundary row, the boundary bullet on rendered Markdown
  authority); `CHANGELOG.md`, `plugin.json`, `marketplace.json` to 0.19.0 together.

## Failure and recovery

- **Render misdescribes its source.** The record is advisory, so a wrong limitation
  misleads nobody about authority; the reader still checks the page image. A reader who
  skips the check has violated the procedure, which the skill text states as the one
  invariant.
- **Changed since preview or target changed.** The helper stops before building a
  payload. The user re-runs the preview.
- **412 conflict.** Zotero refuses the write; the helper prints Zotero's current object
  and stops.
- **Unknown collection key in a PATCH.** 400 from `ZoteroMissingObjectError`; nothing
  written.
- **Non-editable library.** 403 before the body is read; the helper names the library.
- **Trashing a parent.** Children or descendant collections follow in Zotero's own
  semantics; the preview lists them. Item restore brings children; collection restore
  is done per listed descendant by the helper.
- **Accepted but not verified.** The helper exits non-zero with the reason; the user
  checks Zotero or BBT directly. The change may have landed; the helper does not say
  it did. For an export, completion and content are reported as separate observations
  and neither is inferred from the file's bytes.
- **Stale renders.** Any record below render version 3 re-renders on next use.

## Decisions

**D1. Writes go through Zotero 10's stock local API; zotero-api-plus is kept only for
what stock cannot do.** Evidence: the installed `server_localAPI.js`; the extension has
no such endpoints. Consequence: Zotero 10 only for the new helpers. Recorded as ADR
0028.

**D2. Delete means trash for every object that has one; the skill never erases.**
Evidence: `_eraseData` in `item.js` and `collection.js`; both `fromJSON` accept
`deleted`. Part of ADR 0028.

**D3. The renderer is not an authority on quotation safety.** Alternative: a page
classifier that grants authority to pages judged native. Rejected because image
coverage is a proxy for provenance that fails on sparse, tiled, and vectorised scans
and would grow exceptions without bound. Consequence: every exact quotation is checked
against the source; the render record is descriptive. Invalidated only by a renderer
that can prove provenance, which none in the survey claims.

**D4. The OCR cascade keeps its engines and gains a forced path.** Evidence: the survey
gives no comparable old-scans figure for dots.mocr; Chandra's weights carry a
restrictive licence; dots.mocr is deployed. Consequence: an engine change is a separate
design.

**D5. Each write is protected by the state it depends on, not by a universal version
gate.** Modify uses the object's version; create re-resolves its target; registration
re-resolves its collection. Consequence: no invented versions and one gate shape.

**D6. Accepted and verified are reported separately, and a helper never prints bare
success.** Consequence: a degraded path is visible as such, and tests cover the two
paths independently.

## Acceptance criteria

| ID | Observation | Failure it catches |
|---|---|---|
| Q1 | Rendering the Borgmann 2006 attachment yields `extraction: text-layer` and a limitation naming 311 page-sized images and the producer; the state line suggests `--force-ocr` | Scan described as clean |
| Q2 | Rendering the 16-page Word PDF yields `extraction: text-layer` and no page-image limitation | Noise on clean sources |
| Q3 | On a synthetic PDF whose page image shows one set of words and whose hidden text layer says different words, `--force-ocr` yields page Markdown containing the image's words and not the layer's, with `extraction: ocr, forced: true`; without the flag the Markdown contains the layer's words. Live check: `--force-ocr` on the Borgmann 2006 attachment changes the page text where the slips were (for example page text no longer contains "in tum" on the pages that had it) | Path selected but embedded text not replaced |
| Q4 | A `render_version: 2` record for each of pymupdf4llm, docling, mocr, html, and pandoc is reported stale by both cache readers; a version-3 record is current | Renderer exemption |
| Q5 | `blockquote.py` output and the reading procedure label a match `located`, never `verified`; the skill test for the quoting rule is a behavioural check that a quotation record without a source check cannot reach `verified` through any helper | Render treated as authority |
| T1 | `resolve.py --citekey` on a trashed key exits 1 with `in trash`; `--author` on the same item reports no match and names the trash exclusion; the listing marks the row | Trashed item reported live |
| W1 | A modify preview sends no write and prints version N; `--apply --expect-version N` after a stubbed change to N+1 refuses with `changed since preview`; with N held, a stubbed 412 yields `conflict` and no change is claimed | Stale payload overwriting a concurrent edit |
| W2 | A create preview prints the full payload, the resolved keys, and the apply command with `--expect-collection` and `--expect-library`; `--apply` without them is a usage error; `--apply` with them after a stubbed change of the named collection's key refuses with `target changed`; `--expect-version` is not accepted by create or register parsers | Wrong target, invented version, missing interface |
| W3 | Against a Zotero without `Zotero-Server-ID`, every write helper refuses before any request | Zotero 7 to 9 confusion |
| W4 | Each helper's parser rejects a write without `--apply` | Unguarded write |
| R1 | After a stubbed `accepted` response and a read-back that does not show the change, the helper prints `accepted; not verified` and exits non-zero | Bare success |
| L1 | `collection.py --list "Sage SRM Guide"` prints the 26 items observed on 2026-10-12 with citekeys and attachment state, and errors on an ambiguous name with the candidate keys | Listing gap |
| L2 | `item_collections.py --add` on an item in My Library leaves one record whose `collections` contains the target key, read back; `--remove` reverses it; `copy_item.py` is not involved | Duplicate records from copy |
| L3 | `trash_item.py` on an attachment key trashes only that attachment, read back with `includeTrashed=1`; the parent's other children are unchanged; `--restore` returns it | Wrong object trashed |
| L4 | `create_item.py` creates one regular item with the previewed fields in the named collection; the read-back shows key, citekey, and collection | Item created in the wrong place |
| L5 | On a scratch parent collection with one child collection and one member item: `--trash` trashes parent and child and the item stays in the library; `--restore` on the parent returns both with the membership intact; no `DELETE` request is sent | Collection erased or child left in trash |
| E1 | With zotero-api-plus present, `register_export.py --apply` on a scratch collection with no file at the path reports `accepted`, `completion observed`, `content satisfied`, and `verified`; the file's modification time is after the trigger and it contains a listed citekey | Export claimed without observation |
| E2 | With `run-autoexport` stubbed absent, the same command reports `accepted; completion not observed` with the reason, still reports the content check on whatever file exists, and exits non-zero; with a stubbed trigger and a pre-existing file whose bytes do not change, completion is judged by modification time, not hash, and content is reported independently | Degraded path reported as success, or failure inferred from identical bytes |
| E3 | Re-running E1 reports the reschedule and that settings were untouched; a path registered to a different collection is refused without `--replace` | Silent misregistration |
| F1 | `uv run pytest tests/test_bibliography_*.py` and `ruff check` are clean; 0.19.0 appears in `plugin.json`, `marketplace.json`, and `CHANGELOG.md` | Release drift |

L1 to L5, E1, and E3 run against a live Zotero on scratch objects created for the test
and trashed afterwards; they are UAT steps with recorded commands, not CI. Documentation
coverage is a release checklist item, not a test.

## Implementation phases

1. **Quotation contract and extraction record** (Contract 1, criteria Q1 to Q5). No
   dependencies. Leaves the renderer, cache readers, state line, forced-OCR path, and
   quoting rule consistent; pre-0.19 records re-render on demand.
2. **Trash and listing** (trash awareness; `get_collection_items` moved to the shared
   module with `includeTrashed`; `collection.py --list` and `update_item.py --list`
   both consuming it; criteria T1, L1). Independent of phase 1.
3. **Write primitive, membership, trash** (Contracts 2 and 3 for the modify class,
   `item_collections.py`, `trash_item.py`, criteria W1, W3, W4, R1, L2, L3). Depends on
   phase 2. Closes the two defects that caused the Sage duplicates.
4. **Create and collection CRUD** (`create_item.py`, the write half of
   `collection.py`, criteria W2, L4, L5). Depends on phase 3.
5. **Auto-export** (`register_export.py`, criteria E1 to E3). Depends on phase 2.
6. **Release** (skill text, criterion F1, documentation checklist, ADR 0028 index
   entry). Depends on all phases.

## Verification and human judgment

Automation proves: the extraction record on the fixtures, cache invalidation, the
forced path's record, header construction and refusal paths, name resolution, payload
shapes, the preview-to-apply checks, the accepted-versus-verified report, and the two
export paths.

Reserved for human judgment: whether the quoting procedure, with its source check on
every quotation, is workable for a delegated reader on a long book; whether the
`limitations` line and the `--force-ocr` suggestion read as advice rather than verdict;
whether the previews say enough to approve a trash or membership change without
opening Zotero; and whether the auto-export registration matches how the user sets up
"Keep updated" exports by hand.
