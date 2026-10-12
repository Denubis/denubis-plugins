# Resolve and render

All helper commands run from the installed plugin, not a repository checkout:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
```

## Resolve first

`resolve.py` queries the running Zotero database through the stock local API
for search, and through Better BibTeX JSON-RPC for collections, attachments and
exports. It does not use a potentially stale project `.bib` as evidence that an
item exists.

```bash
uv run "$BIB/resolve.py" <bare-doi-or-citekey>
uv run "$BIB/resolve.py" --citekey <exact-key>
uv run "$BIB/resolve.py" --author <author-surname> --year <year>
uv run "$BIB/resolve.py" --title "<distinctive title words>"
uv run "$BIB/resolve.py" --doi <exact-doi>
uv run "$BIB/resolve.py" --citekey <key> --library "<exact library>" --no-render
```

The resolver searches every supplied key and unions candidates before applying
strict filters. Search is Zotero's quicksearch (title, any creator, year and
citekey, word-ANDed; verified on Zotero 9.0.6 and 10.0.1), so `--author`
accepts a co-author's surname; `--doi` searches the DOI field. Diacritics are
searched folded and unfolded. If a lookup fails, retry with a distinctive title
word before concluding anything about absence, and treat a `could not be
searched` warning as an inconclusive result rather than a no-match.

Always copy the exact `citation-key` returned by Zotero. BBT disambiguation
suffixes cannot be safely guessed. Exit `2` means near matches were surfaced but
no exact citekey was accepted; nothing was rendered.

The states are:

- `rendered`: current render exists; the line continues with the extraction
  label and the first limitation from `meta.json`, for example
  `rendered (text-layer; 311 of 311 pages carry a page-sized image; …)`, and an
  `advice:` line names `--force-ocr` when the text layer looks like third-party
  OCR;
- `ready-to-render`: attachment exists and rendering was suppressed;
- `in trash`: the exact citekey resolved to an item in Zotero's trash; that
  copy's collections and attachment are reported as not checked (Better BibTeX
  aggregates them by citekey) and it is never rendered. The resolver exits `1`
  when every copy is in the trash; a live copy beside trashed ones resolves
  normally with the trashed rows shown. Only the exact-citekey search looks in
  the trash: `--author`, `--title`, and `--doi` keep Zotero's exclusion and say
  so in their no-match message;
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
`--force` re-renders; `--force-ocr` re-renders through the OCR tier (below). A
missing Zotero item is reported, not fetched. Use the write-gated procedure in
`zotero-writes.md` if the user wants to add it.

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

### Forced OCR

A scan with an embedded OCR layer (a Paper Capture PDF, for instance) passes
tier 1 and is recorded `extraction: text-layer`; the cascade never reaches OCR
on its own. `--force-ocr` on `resolve.py`, `ingest.py`, and `render.py` skips
the text-layer tiers and starts at Docling with EasyOCR; with `--allow-mocr` it
goes straight to `dots.mocr`. It also bypasses the render cache, because such a
scan has a current render. The record then says `extraction: ocr, forced:
true`. The resolver advises it when the limitations show page-sized images on
most pages under a text layer; the advice is about which render to read, not
about whether a quotation is verified.

```bash
uv run "$BIB/resolve.py" --citekey <key> --force-ocr
uv run "$BIB/resolve.py" --citekey <key> --force-ocr --allow-mocr
```

## Output contract

Every successful render directory contains:

- `full.md`: combined text with `<!-- page:N -->` markers;
- `pages/NNN.md`: one file per physical attachment page;
- `meta.json`: the extraction record.

`meta.json` carries `render_version` (3 since 0.19), `page_count`,
`sha256_prefix`, the source path, `renderer`, `ocr`, and:

- `extraction`: `text-layer` (the PDF's own layer was read), `ocr` (an OCR tier
  produced the text), or `converted` (HTML snapshot or Pandoc);
- `forced`: `true` when `--force-ocr` chose the tier;
- `limitations`: advisory observations such as `311 of 311 pages carry a
  page-sized image; the text layer is likely third-party OCR (producer: …)`,
  `7 pages have no extractable text`, or `replacement characters on 3 pages`.
  Nothing grants or withholds quotation authority on their basis.

Every record written before 0.19 (any `render_version` below 3, for every
renderer) is stale: the next resolve or ingest re-renders it and writes the
record above.

Verify positive files, not just a success message:

```bash
test -s "<zettelkasten-root>/papers/<citekey>/full.md"
test -s "<zettelkasten-root>/papers/<citekey>/meta.json"
test -d "<zettelkasten-root>/papers/<citekey>/pages"
```

Read `meta.json` before quoting. It describes how the text was extracted; the
quoting rule in `SKILL.md` (every exact quotation checked against the source
page before it is `verified`) applies whatever it says.

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
