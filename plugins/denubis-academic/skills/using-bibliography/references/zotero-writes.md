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
