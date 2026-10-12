# Pending work

Plan: `plan.md` in this directory. Each outcome is done when its verification block
passes and its evidence is in `worklog.md`.

## Outcome A: extraction record, forced OCR, quoting contract
- [ ] Operational Q3 live: forced Borgmann 2006 run through `resolve.py --force-ocr` (started 2026-10-12, log `/tmp/bib019/forced2006.log`); on completion record which of the 28 "in tum" pages lost the slip, and keep the render

## Outcome B: trash awareness and read-only listing
- [ ] Red: `includeTrashed` param only when requested; `item_in_trash`; `summarise_collection`; `library_base`
- [ ] Red: trashed envelope → `in_trash`, `state: in trash`, exit 1; untrashed control; author no-match names the exclusion
- [ ] Green: `zotero_local_api.py` (`fetch_search_page`/`search_items` flag, `item_in_trash`, `library_base`, moved `get_collection_items`, `summarise_collection`)
- [ ] Green: `resolve.py` (`Paper.in_trash`, citekey sweep, state line, no-match text)
- [ ] Green: `collection.py --list`; `update_item.py --list` through the shared function; remove the old `get_collection_items`
- [ ] Docs: `resolve-and-render.md`, `SKILL.md` front door, `zotero-writes.md` listing section, `troubleshooting.md`; regex in `tests/test_bibliography_skill.py`
- [ ] Operational T1 against `D7IV2YRB` (citekey and author forms)
- [ ] Verification block B; checkpoint commit

## Outcome C: write primitive, membership, item trash/restore
- [ ] Red: primitive over the stubbed seam (headers, version header, 204, 412 conflict, 412 server-ID body, 401 retry, `require_stock_writes`)
- [ ] Red: `write_gate.py` flag sets per class, refusals, report lines and exit codes
- [ ] Red: `item_collections.py` and `trash_item.py` cases W1, W3, W4, R1
- [ ] Green: `zotero_local_api.py` primitive (`read_object`, `write_object`, `create_objects`, `_http_request` seam, `StockWriteUnavailable`)
- [ ] Green: `write_gate.py`
- [ ] Green: `item_collections.py`
- [ ] Green: `trash_item.py`
- [ ] Docs: `zotero-writes.md`, `SKILL.md` rows and Zotero 10 precondition, `troubleshooting.md` rows; regex update
- [ ] Verification block C; checkpoint commit

## Outcome D: item creation and collection CRUD
- [ ] Red: `create_item.py` W2 cases; `collection.py` verbs (descendant listing at trash time with a stub that excludes trashed children, trash output prints the `--restore … --descendants` command, restore order with `--descendants`, `descendants unknown` without it, parser rejects two verbs, no DELETE in any request log)
- [ ] Green: `create_item.py`
- [ ] Green: `collection.py --create/--rename/--trash/--restore`
- [ ] Docs: `zotero-writes.md`, `SKILL.md` rows, `troubleshooting.md` `target changed`; regex update
- [ ] Verification block D; checkpoint commit

## Outcome E: auto-export registration
- [ ] Red: `register_export.py` cases (`bbt_collection_path` numeric absolute form reaches the RPC stub, preview no RPC, `--expect-version` rejected, missing flag usage error, accepted/not accepted by returned key, E2a, E2b, no-mtime-change, content satisfied/not)
- [ ] Green: `register_export.py` (injected clock)
- [ ] Docs: `zotero-writes.md`, `notes-and-bibliographies.md`, `SKILL.md` row, `troubleshooting.md` rows; regex update
- [ ] Verification block E; checkpoint commit

## Outcome F: release 0.19.0
- [ ] Final `SKILL.md` pass (preconditions, front door, write-boundary table, completion evidence; ≤ 500 lines)
- [ ] Bounded inspection: every documented flag and preview line exists in the helper (`--help` plus format strings), recorded per helper
- [ ] `docs/architecture/plugins/denubis-academic/0-context.md` update
- [ ] Version 0.19.0 in both `plugin.json` manifests (Claude and Codex), `marketplace.json`, `CHANGELOG.md` entry
- [ ] Verification block F (full suite, ruff check and format, `git diff --check`); checkpoint commit

## Human UAT (after F)
- [ ] Steps 1–8 in `plan.md` "Human UAT"; record each result in `worklog.md`
- [ ] After acceptance: normalise checkpoints per outcome, rerun F gates
