# Resolve and render

All helper commands run from the installed plugin, not a repository checkout:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
```

## Resolve first

`resolve.py` queries the running Zotero database through Better BibTeX JSON-RPC
and the stock local API. It does not use a potentially stale project `.bib` as
evidence that an item exists.

```bash
uv run "$BIB/resolve.py" <bare-doi-or-citekey>
uv run "$BIB/resolve.py" --citekey <exact-key>
uv run "$BIB/resolve.py" --author <first-author> --year <year>
uv run "$BIB/resolve.py" --title "<distinctive title words>"
uv run "$BIB/resolve.py" --doi <exact-doi>
uv run "$BIB/resolve.py" --citekey <key> --library "<exact library>" --no-render
```

The resolver searches every supplied key and unions candidates before applying
strict filters. `--doi` uses Zotero's DOI field because BBT `item.search` does
not index DOI. `--author` handles diacritic folding and hyphen components, but
BBT's search remains first-author-oriented. If a lookup fails, retry with a
distinctive title word before concluding anything about absence.

Always copy the exact `citation-key` returned by Zotero. BBT disambiguation
suffixes cannot be safely guessed. Exit `2` means near matches were surfaced but
no exact citekey was accepted; nothing was rendered.

The states are:

- `rendered`: current render exists;
- `ready-to-render`: attachment exists and rendering was suppressed;
- `no-pdf`: item is resolved but has no renderable attachment;
- `pdf-unknown`: lookup could not prove attachment state;
- `needs-ocr-escalation`: ordinary rendering failed quality checks.

Copies in several libraries share one `papers/<citekey>/` render. Pin
`--library` if the copies hold genuinely different documents.

## Batch DOI ingest

For papers already in Zotero:

```bash
uv run "$BIB/ingest.py" 10.1145/1273445.1273458 10.1111/jels.12413
uv run "$BIB/ingest.py" --force 10.1145/1273445.1273458
```

From stdin:

```bash
uv run "$BIB/ingest.py" - < dois.txt
```

`ingest.py` is idempotent and uses a source hash to skip current renders.
`--force` re-renders. A missing Zotero item is reported, not fetched. Use the
write-gated procedure in `zotero-writes.md` if the user wants to add it.

## Render cascade

Normal resolution auto-renders. For a known attachment path, the standalone
entry point is:

```bash
uv run --with pymupdf4llm --with docling --with easyocr \
  "$BIB/render.py" "<absolute-attachment-path>" \
  "<zettelkasten-root>/papers/<citekey>"
```

Do not substitute `pdftotext`, Tesseract, or a one-off converter. The bundled
cascade owns quality checks and provenance:

1. PDF: `pymupdf4llm`;
2. PDF fallback: Docling without OCR;
3. PDF fallback: Docling with pinned EasyOCR;
4. optional, confirmed escalation: configured `dots.mocr` via `--allow-mocr`;
5. Zotero HTML snapshot: Python HTML parser;
6. other attachments: Pandoc to GitHub-flavoured Markdown.

The PDF gate rejects excessive empty pages, replacement characters, and
near-empty OCR output. `NEEDS MOCR` is a decision point, not permission to start
a GPU service. Ask before re-running:

```bash
uv run "$BIB/resolve.py" --citekey <key> --force --allow-mocr
```

The optional tier requires:

```toml
[mocr]
repo = "~/path/to/dots.mocr"
# port = 8000
# startup_timeout = 300
```

## Output contract

Every successful render directory contains:

- `full.md`: combined text with `<!-- page:N -->` markers;
- `pages/NNN.md`: one file per physical attachment page;
- `meta.json`: source path/hash, renderer, page count, OCR flag, and warnings.

Verify positive files, not just a success message:

```bash
test -s "<zettelkasten-root>/papers/<citekey>/full.md"
test -s "<zettelkasten-root>/papers/<citekey>/meta.json"
test -d "<zettelkasten-root>/papers/<citekey>/pages"
```

Read `meta.json` before quoting. `ocr: true` changes rendered text from exact
quotation authority to a locator requiring visual PDF verification.

## Dependencies

`resolve.py` declares Python 3.14+ and its lightweight dependencies through PEP
723. `ingest.py` declares Python 3.11+ plus the rendering stack; use Python 3.14+
for one consistent installation. `render.py` is invoked with explicit `uv
--with` dependencies above. Pandoc is an external executable for non-PDF,
non-HTML attachments.

The first Docling/OCR run can be large and may download model data. Use the
configured uv and model caches exactly as provided; never redirect them to a
temporary or repository-local location. `pymupdf4llm` is AGPL-3, Docling and
EasyOCR are Apache-2.0, and `dots.mocr` retains its own deployment licence.
