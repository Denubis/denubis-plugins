# Zotero writes

These operations modify Zotero and may sync to other devices. Resolve and
preview first, state the exact item and destination/change, and obtain explicit
confirmation before the write flag.

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
```

Probe the optional extension without exposing credentials:

```bash
curl -sS --max-time 3 http://localhost:23119/api/plus
```

The expected banner is `Zotero Local API Plus is running.` Helpers also probe
their specific endpoint and stop on an older build.

## Zotero 10: writes need a one-time authorisation

Zotero 10 authenticates every local-API write in the base class each endpoint
inherits, so the rule covers all `zotero-api-plus` `POST` endpoints and runs
before their own validation. `GET` is ungated, and Zotero 7-9 have no such
rule. The helpers handle it in `zotero_auth.py`; nothing here is manual.

1. The server ID is read once per run from the `Zotero-Server-ID` response
   header of `GET /api/`. No header means Zotero 7-9, and nothing changes.
2. A key is obtained once per machine from `POST /api/local/authorize` with
   `{"appName": "denubis-academic"}`. **Zotero shows a modal — tell the user to
   choose "Always Allow".** "Allow" issues a single-use key that is consumed by
   its first write, so the next command prompts again.
3. Both travel on every write as `Zotero-Server-ID` and `Zotero-API-Key`.

Reusable keys are stored in
`~/.config/denubis-academic-research/zotero-local-api-keys.json`, mode `0600`,
keyed by server ID. That file is skill-owned; the neighbouring `config.toml` is
the user's and is never written. `DENUBIS_ZOTERO_KEY_STORE` overrides the path.

The prompt appears at the first *writing* command, which for `update_item.py`
and `copy_item.py` is the preview — both send a `POST` that changes nothing.
Say so before running one, so an unexpected Zotero modal is not a surprise.
The stock-API helpers below preview with `GET` only; their prompt appears at
`--apply`.

## Stock writes: preview, protect, report (0.19)

`item_collections.py`, `trash_item.py`, `create_item.py`, and the write verbs
of `collection.py` write through Zotero 10's own local API (ADR 0028). They
refuse before any request on a Zotero without a `Zotero-Server-ID` header
(`stock writes need Zotero 10`), resolve library and collection names through
zotero-api-plus `/api/plus/libraries`, and share one gate:

- **Preview** is the default and sends only `GET`s. It prints the object as
  read, its `version`, the resulting state, and the exact apply command.
- **Apply** is `--apply` plus the expected-state flag of the operation class.
  The *modify* class (membership, trash, restore, rename) carries
  `--expect-version N`: apply re-reads the object and stops with `changed
  since preview` if its version differs, then writes with
  `If-Unmodified-Since-Version: N`, so a concurrent edit in the window after
  the read is a `conflict` (Zotero's 412) that prints Zotero's current object
  and is never retried. The *create* and *register* classes carry
  `--expect-collection KEY`, `--expect-parent KEY`, `--expect-library ID` and
  stop with `target changed` if a re-resolved key differs. There is no
  universal `--expect-version`.
- **Report**: the final line is `accepted; verified`, `accepted; not
  verified: <reason>`, or `not accepted: <reason>`. `accepted` means Zotero
  took the request (204 with `Last-Modified-Version`, or a `successful` entry
  from a `POST`); `verified` means the helper read the object back and saw
  the change. Only `accepted; verified` exits 0.

No helper sends `DELETE`, which erases permanently: delete means trash
(`PATCH {"deleted": true}`), and emptying the trash stays a human action in
Zotero.

Copy the apply command the preview printed rather than retyping it. Before
running it, state the object, the change, and the version to the user and
obtain confirmation.

## File an existing item into a collection

```bash
uv run "$BIB/item_collections.py" --key <item-key> --add "<collection name or key>"
uv run "$BIB/item_collections.py" --key <item-key> --remove "<collection name or key>"
```

The preview shows the item's title, library, version, and its `collections`
before and after, with names. After confirmation run the printed command:

```bash
uv run "$BIB/item_collections.py" --key <item-key> --add "<collection>" \
  --apply --expect-version <N>
```

Apply PATCHes the merged `collections` array and verifies by reading the item
back. This files one existing record; `copy_item.py` copies between libraries
with attachment top-up and must not be used to file an item.

## Trash or restore an item or attachment

```bash
uv run "$BIB/trash_item.py" --key <item-or-attachment-key>
uv run "$BIB/trash_item.py" --key <item-or-attachment-key> --restore
```

The preview shows the type, title, parent (for an attachment or note), the
file name and size, `owl:sameAs` relations, the child count (children follow a
parent into the trash), the current `deleted` flag, and the version. After
confirmation run the printed command with `--apply --expect-version <N>`.
Apply PATCHes `deleted` and verifies by reading the object back with the trash
included.

A child (attachment or note) is in the trash whenever its parent is, whatever
its own `deleted` flag says; that is Zotero's own `isInTrash()`, and the stock
API reports only the child's flag. The helper reads the parent, shows the
state on the `deleted:` line (`false (in the trash through parent KEY)`), and
`--restore` on such a child writes nothing: it prints the parent's restore
command and ends `not accepted: in the trash through parent KEY`. Restore the
parent first; a child whose own flag is set needs its own restore afterwards.

## List a collection (read-only)

Requires `zotero-api-plus` for name resolution only; the listing itself is the
stock local API with the trash included.

```bash
uv run "$BIB/collection.py" --list "<collection name or key>" --library "<library>"
```

`--library` defaults to My Library. An ambiguous name errors with every
candidate key and its parent key; pass the key instead. Each row is
`key  citekey  title  [in trash]  attachments: n (names)`, and the last line is
the total with the trashed count. This is the way to check what a collection
holds before filing into it, and it writes nothing. `update_item.py --list`
prints the same membership as a triage table (type, title, `NO AUTHOR`,
`IN TRASH`).

## Fetch a genuinely missing paper

Requires `zotero-api-plus` 0.3.0+.

1. Search Zotero with the resolver by DOI, an author surname, and a distinctive
   title token. A single no-match is not absence, and a `could not be
   searched` warning makes it inconclusive.
2. Preview the identifier list and resolved destination without writing:

   ```bash
   uv run "$BIB/fetch.py" \
     --group "<group name or ID>" --collection "<collection name>" \
     <DOI-or-other-identifier>
   ```

   Omit `--group` for My Library and `--collection` for the library root. Use
   `--collection-key` only with a key returned by Zotero; never guess it.
3. Ask: “This paper is not in Zotero. Fetch `<identifier/title>` into
   `<collection>` in `<library>` and attach an available PDF? This writes a new
   Zotero item.”
4. Only after yes, repeat the previewed command with `--fetch`:

   ```bash
   uv run "$BIB/fetch.py" \
     --group "<group name or ID>" --collection "<collection name>" \
     --fetch <DOI-or-other-identifier>
   ```

`present` and `fetched` mean an attachment is available; `unavailable` means
metadata was created but no open-access PDF was attached. Paywalled sources may
still require the user's authenticated Zotero connector. The endpoint does not
deduplicate, which is why the absence check and confirmation are mandatory.

For a batch, preview the complete missing set and target, ask once for that exact
set, then fetch it in one call. Do not infer consent from “ingest these DOIs.”

## Copy an item between libraries

Requires `zotero-api-plus` 0.5.0+.

```bash
uv run "$BIB/copy_item.py" --find "<title words>"
uv run "$BIB/copy_item.py" --key <item-key> --from "<source>" \
  --to "<destination>" --to-collection "<collection>"
```

The second command is a no-write preview. Show its resolved source,
destination, item, attachment plan, and duplicate warnings. After confirmation:

```bash
uv run "$BIB/copy_item.py" --key <item-key> --from "<source>" \
  --to "<destination>" --to-collection "<collection>" --copy
```

Use the Zotero item key returned by `--find`, not the attachment storage key.

## Repair metadata

Requires `zotero-api-plus` 0.6.0+.

```bash
uv run "$BIB/update_item.py" --find "<title words>"
uv run "$BIB/update_item.py" --key <item-key> --library "<library>" \
  --type bookSection --set pages=53-82
```

Without `--apply`, the helper prints a dry-run diff. Confirm that exact diff,
including creator order and fields being cleared. Then apply the same change:

```bash
uv run "$BIB/update_item.py" --key <item-key> --library "<library>" \
  --type bookSection --set pages=53-82 --apply
```

Repeat `--set FIELD=VALUE`, `--clear FIELD`, `--author 'Last, First'`, or
`--creator TYPE='Last, First'` as required. Creator flags replace the creator
list; do not omit creators that should remain. Read the item back after success.

## Create an item

```bash
uv run "$BIB/create_item.py" --type book --set title="<title>" --set date=2026 \
  --author "Last, First" --creator editor="Last, First" \
  --collection "<collection name or key>" --library "<library>"
```

Create class: the preview prints the full JSON body (`itemType`, fields,
`creators`, `collections`), the resolved library (name and libraryID), the
resolved collection key, and the apply command carrying `--expect-collection
KEY` (when a collection is named) and `--expect-library ID`. After
confirmation run that command. Apply re-resolves both names and stops with
`target changed` if a key differs, POSTs one item, reads it back, and verifies
the fields, the creator list and the collection; it prints the new key and the
citekey, or `citekey: not yet assigned` while Better BibTeX has not yet set
one (not a verification failure). The field grammar is `update_item.py`'s;
`--author` and `--creator` give the complete creator list in order.

## Create, rename, trash, or restore a collection

```bash
uv run "$BIB/collection.py" --create "<name>" [--parent "<name or key>"]
uv run "$BIB/collection.py" --rename <key> "<new name>"
uv run "$BIB/collection.py" --trash <key>
uv run "$BIB/collection.py" --restore <key> [--descendants K1,K2,...]
```

`--create` is the create class: the preview prints the body and the resolved
parent and library, and apply carries `--expect-library ID` and, when a
parent is named, `--expect-parent KEY`. The other three are the modify class
with `--expect-version N`.

Trash semantics, read in the installed Zotero 10.0.6 source on 2026-10-12:
Zotero trashes a collection's descendants with it, restores non-recursively,
and its collection listings and `numCollections` exclude the trash; only a
direct key read returns a trashed collection. So:

- `--trash` lists the live descendant collections and the member item count
  in the preview; apply PATCHes `deleted` on the parent, verifies the parent
  and every listed descendant by direct key read, and ends with the exact
  restore command, `--restore KEY --descendants K1,K2,...`. Keep that line: it
  is the record of what went into the trash.
- `--restore` with `--descendants` clears `deleted` on the parent and then on
  each listed descendant, shallowest first, each protected by its own read
  version, and verifies every one by read-back together with the parent's
  item count. Without `--descendants` it restores the parent only and prints
  `descendants unknown: Zotero's collection listings exclude the trash; pass
  --descendants from the trash output or restore them in Zotero`; it never
  claims to have restored what it could not see.

Member items are not trashed with their collection and keep their membership.

## Annotate a cited passage

Requires the `zotero-api-plus` annotation endpoints. An annotation is a Zotero
write even though the tool is idempotent. Resolve the exact physical PDF page,
then preview:

```bash
uv run "$BIB/annotate.py" <citekey> --page <physical-page> \
  --quote "<verbatim passage>" --note "<claim supported>" --dry-run
```

After explicit instruction to annotate, omit `--dry-run`. The tool normally
computes highlight rectangles with PyMuPDF. If the PDF has no matching text
layer, it writes a page-anchored note instead and reports `noted` rather than
`highlighted`.

Batch input is JSONL with `citekey`, `page`, `quote`, and optional `note`:

```bash
uv run "$BIB/annotate.py" --batch <passages.jsonl> --dry-run
```

Inspect existing annotations read-only:

```bash
uv run "$BIB/annotate.py" --list <citekey>
```

The physical PDF page is 1-based and may differ from printed pagination. The
machine marker prevents duplicate annotations on rerun; it does not remove the
need to confirm the intended write.
