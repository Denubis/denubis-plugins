---
name: using-bibliography
description: Use when resolving a paper in Zotero by any key, rendering a Zotero PDF to per-page markdown, surfacing page-keyed blockquotes, or fetching a missing paper behind explicit confirmation.
user-invocable: true
last-reviewed: 2026-06-20
---

# Using Bibliography

Render PDFs from the user's Zotero corpus into per-page markdown stored under
`~/zettelkasten/papers/<citekey>/`, and emit page-keyed blockquotes that future
Claude sessions (or pandoc) can use as verified citations.

**Status:** WIP. Documents only the path proven end-to-end on
`yimTeachersPerceptionsAttitudes2024` on 2026-05-11. Anything not here is not
yet validated.

## When to use

- "Render this paper to markdown" — given a cite key in Zotero.
- "Find this quote in <paper> with a page number" — span verification against
  rendered output.
- "Make a permanent note from <quote> in <paper>" — emit the blockquote;
  human (or human-supervised agent) writes the surrounding atomic note in
  `~/zettelkasten/permanent/`.

**When NOT to use:**

- Fetching papers from the internet — supported **only** when the
  `zotero-api-plus` plugin is installed (v0.3.0+), and **only** behind explicit
  user confirmation (see "Fetching a missing paper"). Even then, a paywalled
  paper with no open-access copy comes back metadata-only; the Zotero connector
  (EZProxy, SSL, publisher quirks) remains the path for those. Without the
  plugin, the user adds papers via the connector and you render only what is
  already in Zotero with a PDF attached.
- Editing the user's permanent notes without explicit instruction — the
  zettelkasten's `AGENTS.md` rules apply (treat permanent notes as user IP;
  draft, don't assert).

## Hard preconditions (verify before acting)

1. **Zotero is running** and Better BibTeX is installed:
   ```bash
   curl -sS --max-time 3 http://localhost:23119/connector/ping
   ```
   Expects `<!DOCTYPE html><html><body>Zotero is running</body></html>`.
   If not running, ask the user to start Zotero (`flatpak run org.zotero.Zotero`
   on this machine; on first run from SSH set `XDG_RUNTIME_DIR` and
   `WAYLAND_DISPLAY=wayland-0` to put it on the existing graphical session).

2. **Config exists** at `~/.config/denubis-academic-research/config.toml`.
   If missing, halt and instruct the user to create it (see `bootstrap`
   section below).

3. **Zettelkasten root exists** at the path in config (default `~/zettelkasten/`).
   If missing, halt — do not create it silently. The user owns this directory.

4. **`pymupdf4llm` is installed** in a usable venv. `docling` is also
   required for the fallback path when pymupdf4llm produces empty or
   garbage output (see "Render cascade" and Dependencies below).

## Resolve a paper — the front door (`resolve.py`)

**Start here to find a paper in Zotero by anything you know about it.** `resolve.py`
is the live, citekey-first resolver: pass any of author, year, title, date,
citekey, or DOI and it reports the truth — which libraries *and* collections the
paper is in, whether a PDF is attached and on disk, and whether it has been
rendered — then renders it by default so it can be "asked questions".

It queries the **running Zotero DB** (BBT JSON-RPC: `item.search` /
`item.collections` / `item.attachments` / `user.groups`), never the cached `.bib`
export — so it cannot report a stale ghost. And because it resolves by
citekey/author/title, it does not inherit the DOI path's failure modes (Crossref
dependency, empty-author DOIs, DOI drift).

```bash
R=plugins/denubis-bibliography/skills/using-bibliography/resolve.py
# Bare query is auto-classified: DOI shape (10.NNNN/…) -> --doi; citekey shape -> --citekey
uv run $R vehtariPracticalBayesianModel2017
uv run $R --author Vehtari --year 2017
uv run $R --title "scoping studies"
uv run $R --doi 10.1007/s13347-024-00760-w        # DOI: Crossref-surname fallback (the one weak key)
uv run $R --citekey <key> --library "My Library" --no-render   # narrow + don't render
```

Per match it prints library, the paper's collections (aggregated per citekey by
BBT, **not** per library copy), PDF path (+ exists), and `state`: `not-in-zotero`
| `no-pdf` | `pdf-unknown` | `ready-to-render` | `rendered` | `needs-ocr-escalation`.
Auto-render is ON by default (`--no-render` suppresses; `--force` re-renders;
`--allow-mocr` escalates to GPU OCR).

**Truthful by construction:** a wrong/constructed citekey returns an honest "No
matches" rather than a guess; the same paper is listed once per library it lives
in; a PDF that can't be confirmed (unresolved library name / failed lookup) is
`pdf-unknown`, never a false `no-pdf`. `resolve.py` searches **every** supplied
key and unions the hits, so a query keyed on a co-author still resolves when
another key matches — BBT `item.search` indexes only the *first* author surname,
which is why the old single-key search reported present papers as absent.
`--author` matches a full surname or a **hyphen-component** of one (`Malsiner`
finds `Malsiner-Walli`, `Frühwirth` finds `Frühwirth-Schnatter`), and is
**diacritic-insensitive** (`Frühwirth` and `Fruhwirth` both resolve, because BBT's
index is ASCII-folded); initials and arbitrary substrings still do not match. A
genuine no-match prints what was searched and states plainly that, `item.search`
being AND-fuzzy and first-author-only, **a no-match is not proof of absence** —
retry with the first author's surname or a distinctive `--title` word.

**Known behaviour:** copies of one citekey across libraries share a single render
dir `papers/<citekey>/`. The paper renders **once** — render state is per-citekey,
not per-copy PDF, so other copies never re-render or clobber it (`--force`
re-renders). If two libraries genuinely hold *different* documents under one
citekey (e.g. a preprint vs the published version), the dir holds whichever
rendered first; that's a Zotero data-hygiene case, pinnable with `--library`.

`resolve.py` is the one call to use. The inline `item.search` → `item.export`
recipe under "The proven workflow" documents the same mechanism by hand for when
you need to drive it directly.

## Fanning out readers over a rendered corpus

When the user hands you a reading list of papers already in their Zotero corpus
and asks you to investigate them, render each paper once on the orchestrator
side, then dispatch one reader subagent per paper given only the rendered
markdown path. The corpus is curated, so every paper on the list is present by
construction, and the job is to read them rather than to litigate whether they
exist.

**Work by citekey.** The citekey is the stable handle for everything downstream:
the render directory `papers/<citekey>/`, the `[@citekey, p. N]` citation, the
`notes/literature/<citekey>.md` note, and the reader dispatch all key on it.
Resolve each paper by its citekey wherever you have one. When you do not yet have
the citekey, find it with the first-author surname plus a distinctive title word,
then switch to the citekey `resolve.py` returns. A bare co-author surname
surfaces nothing because `item.search` indexes only the first author, so
`resolve.py` reports an honest "no matches" while the paper sits in the library.
On a reading-list paper, treat that as a wrong key to retry, never as proof of
absence.

**Readers get a path, not a PDF and not inline text.** The point of fanning out
is to keep many papers' worth of text out of your own context, so each reader
reads its own paper in its own context. A reader handed only the rendered
markdown cannot reach for `pdftotext` or stand up its own extractor, because the
authoritative, quality-checked text is already on disk. The orchestrator owns the
one render, and the readers own the reading.

### Dispatch gate (per paper, before dispatching its reader)

```text
1. resolve.py <citekey>          # auto-renders. No citekey yet? Find it with
                                 #   --author <first-author> --title <word>, then use the citekey.
2. read `state` from the output:
     rendered                                    -> continue
     no-pdf | needs-ocr-escalation |
     pdf-unknown | render failed                 -> add to "could not prepare"
3. PROVE the file: stat <zk>/papers/<citekey>/full.md and confirm non-empty
4. render note := meta.json.ocr ? "OCR'd, flag garbled quotes" : "clean text layer"
5. dispatch one reader with the prompt below, interpolating {citekey, path, note, brief}
```

Step 3 is not optional: stat the file rather than trusting `resolve.py`'s word
that it rendered, which is the "claimed success without checking" mistake the
Common-mistakes table already names. After the fan-out, surface the "could not
prepare" list to the user, because a paper that needs `--allow-mocr` or a PDF
attached via the connector needs a human decision, and a reader must never be
pointed at a file that is not there.

### Reader prompt

Interpolate `{{CITEKEY}}`, the deterministic path `{{FULLMD_PATH}}` =
`<zk>/papers/<citekey>/full.md`, `{{RENDER_NOTE}}` from `meta.json`'s `ocr`
field, and the `{{BRIEF}}` for this paper.

```text
<role>
You are reading one paper from the user's curated Zotero corpus to answer a
specific brief. The PDF has already been rendered to per-page markdown by a
quality-checked cascade (pymupdf4llm, then docling, then OCR). That markdown is
the authoritative text of the paper, and it is the only source you read from.
</role>

<inputs>
- citekey: {{CITEKEY}}
- paper text: {{FULLMD_PATH}}
  (combined markdown; each page begins with a `<!-- page:N -->` marker)
- render note: {{RENDER_NOTE}}
  (either "clean text layer" or "OCR'd, so flag any quote that looks garbled")
</inputs>

<brief>
{{BRIEF}}
</brief>

<how_to_work>
Read the markdown file at the path above. Everything you need is in that file,
which is the already-extracted, quality-checked text of the paper and is better
than anything you could re-derive. To attribute a page, find the nearest
`<!-- page:N -->` marker preceding the passage. Copy every quote verbatim from
the markdown. To double-check a quote, re-read the markdown (and the matching
`pages/NNN.md`); that rendered text, not the PDF, is the source of truth here.
</how_to_work>

<constraints>
Read only the file you were given and its sibling `pages/NNN.md`. The extraction
is finished, so do not open, fetch, or convert a PDF, and do not run pdftotext,
tesseract, pymupdf4llm, docling, or any other extractor: re-running extraction
produces worse text than you already hold and wastes the render done for you.

The dispatcher already resolved and placed this file, so do not search Zotero,
run resolve.py, or render anything. If the file is not at the path, stop and
report exactly that. Do not go looking for the paper.

Quote only what is literally in the markdown. If the brief asks for something the
paper does not contain, say so plainly rather than inventing it.
</constraints>

<output_format>
## {{CITEKEY}} (<one line on what this paper is and does>)

### Findings (answering the brief)
- <finding stated in your own words> [p. N]

### Quotes (verbatim, for citation)
> <exact quote copied from the markdown>

[@{{CITEKEY}}, p. N]

### Gaps and caveats
- <anything the brief asked that the paper does not cover>
- <any passage that looks garbled, when the render note flagged OCR>
</output_format>
```

## Quickstart: ingest a list of DOIs

For batch ingest from DOIs (the most common case):

```bash
uv run plugins/denubis-bibliography/skills/using-bibliography/ingest.py \
    10.1145/1273445.1273458 \
    10.1111/jels.12413 \
    ...
```

Or pipe DOIs from a file:

```bash
cat dois.txt | uv run .../ingest.py -
```

PEP 723 inline metadata in the script handles dependency installation. Output
lands in `<zettelkasten_root>/papers/<citekey>/`. The script is idempotent —
re-runs skip cite keys whose SHA-prefix matches; pass `--force` to re-render.

Verified end-to-end on 2026-05-11 against 8 methodology DOIs (Keshav 2007,
Scherbakov 2025, Wohlin 2014, Arksey 2005, Levac 2010, Tricco 2018, Naeem
2024, Magesh 2025). 8/8 succeeded.

## Fetching a missing paper (requires zotero-api-plus)

The pipeline below renders papers **already in Zotero**. When a paper is *not*
in Zotero, the `zotero-api-plus` plugin (v0.3.0+) can fetch it by identifier and
attach the PDF. This **WRITES to the user's library**, so it is gated on
explicit confirmation. Without the plugin, fall back to the connector (see
"When NOT to use").

**Capability probe** — is the plugin present?

```bash
curl -sS --max-time 3 http://localhost:23119/api/plus
# → "Zotero Local API Plus is running."   (anything else: not available, fall back)
```

**The flow — the HALT in step 3 is not optional:**

1. **Confirm the paper is genuinely absent.** Resolve it first (`ingest.py`
   prints `NOT FOUND in Zotero`, or run the surname→DOI-filter search). The
   endpoint does **not** dedup — it always saves a new item — so fetching a
   paper that is already present creates a duplicate (this is how a second
   "Attention Is All You Need" appeared on 2026-06-02). Fetch only when
   resolution returns nothing.

2. **Resolve the target + preview with `fetch.py` — do not hand-parse JSON.**
   Turning a human group + collection name into the numeric `groupID` and
   `collectionKey` that `add-item-by-id` needs is exactly the step that used to
   be improvised as a multi-line `python3 -c "…"` block in bash and broke on
   quoting. Use the helper. A bare run resolves the target and previews
   **without writing**:

   ```bash
   uv run plugins/denubis-bibliography/skills/using-bibliography/fetch.py \
       --group "<group name or numeric groupID>" \
       --collection "<collection name>" \
       <DOI/ISBN/PMID/arXiv> ...
   ```

   - Omit `--group` for My Library; omit `--collection` to target the library root.
   - On an unknown or ambiguous name the helper lists the available groups /
     collections and exits non-zero. Copy the right name, or pass
     `--collection-key <KEY>` directly. Never guess a key.
   - To inspect targets by hand: `GET /api/plus/selected-collection` (the
     collection open in the UI; `500 "No Collection selected."` if none) and
     `GET /api/plus/libraries` (My Library + every group with `{key,name,
     parentKey}` collections and the group's `groupID`).

   Need a **new** collection? Create it idempotently first, then pass its key:

   ```bash
   curl -sS -X POST http://localhost:23119/api/plus/create-collection \
     -H 'Content-Type: application/json' \
     -d '{"name":"<name>","groupID":<groupID, or omit for My Library>}'
   # → {"created":true|false,"collection":{"key":"…",…}}
   ```

3. **HALT and confirm — both halves.** The preview from step 2 is what you
   confirm. State exactly what will be written and where: *"<title/DOI> is not in
   Zotero. Fetch it into <collection> (<library>) and attach the PDF? This adds
   an item to your library."* Proceed only on an explicit yes. **Do not infer
   consent** from an earlier "ingest these DOIs" instruction — adding to the
   library is a distinct write the user has not yet authorised.

4. **Fetch** — re-run the same command with `--fetch` to write:

   ```bash
   uv run plugins/denubis-bibliography/skills/using-bibliography/fetch.py \
       --group "<…>" --collection "<…>" --fetch <DOI> ...
   ```

   The helper POSTs `add-item-by-id` and prints `pdf=<status>` per added item,
   from the response `{status,addedCount,titles[],items:[{title,key,pdf,
   attachmentID?}]}`:

   - `present` — translator attached the PDF during this add. On disk; render.
   - `fetched` — translator gave metadata only; the `addAvailableFile` fallback
     attached an open-access PDF. On disk; render.
   - `unavailable` — item added, **no PDF** (no OA copy; likely paywalled with no
     institutional session). Attach via the connector, then re-run the render.
   - `error` — the helper surfaces the server message verbatim; do not retry blindly.

5. **Render** via the normal pipeline once a PDF is present. BBT may lag a few
   seconds indexing the new item; if the first `ingest.py` run reports
   `NOT FOUND`, retry once.

**Batch (a list of DOIs):** resolve them all first, surface the
missing-and-fetchable set as ONE list, confirm the set + target collection in a
single prompt, then fetch the confirmed set and render. One confirmation for the
batch — never silent per-item writes. `fetch.py` takes the whole identifier list
in a single invocation against one `--group`/`--collection`, so the no-`--fetch`
preview shows the entire batch and one `--fetch` run writes it after the single
confirmation.

**Verified end-to-end 2026-06-03:** `10.1007/s13347-024-00760-w` (Conradie &
Nagel, CC-BY) — `create-collection` "test" in a group → `add-item-by-id`
(`pdf: present`, PDF on disk) → `ingest.py` rendered 24 pages via pymupdf4llm.

## The proven workflow

### 1. Resolve cite key → PDF file path

```python
import requests

# (a) Find the item — fulltext or DOI search
resp = requests.post(
    "http://localhost:23119/better-bibtex/json-rpc",
    json={"jsonrpc": "2.0", "method": "item.search",
          "params": ["<citekey or DOI or fragment>"], "id": 1},
).json()
hit = resp["result"][0]
citekey = hit["citation-key"]
library_name = hit["library"]   # e.g. "My Library" or "2025-MQ-EALD_Vocab"

# (b) Map library name → numeric library_id (cache once per session)
groups = requests.post(
    "http://localhost:23119/better-bibtex/json-rpc",
    json={"jsonrpc": "2.0", "method": "user.groups", "params": [], "id": 2},
).json()["result"]
library_id = next(g["id"] for g in groups if g["name"] == library_name)

# (c) Export the bib entry — file = {...} field gives the PDF path
bib = requests.post(
    "http://localhost:23119/better-bibtex/json-rpc",
    json={"jsonrpc": "2.0", "method": "item.export",
          "params": [[citekey], "Better BibLaTeX", library_id], "id": 3},
).json()["result"][0]
# Parse `file = {<absolute path>}` from the bib string.
```

**Gotchas verified empirically (2026-05-11):**

- **`item.search` is AND-style across tokens.** Multi-word queries like
  `"Wohlin snowballing"` require BOTH terms to appear in the same searchable
  field — and no field combines author surname with title-word, so multi-token
  searches across these silently return zero hits even when the item exists.
  **Use single-token searches** (just an author surname OR just a title
  fragment) and refine programmatically. (`resolve.py` does this for you: it
  searches every supplied key separately and unions the hits, then filters.)
- **`item.search` indexes only the FIRST author surname.** A search for a
  co-author (`Ghahramani` in "Wade, Ghahramani"; `Kruschke` in "Liddell,
  Kruschke") returns zero — the paper is present, the search just can't see the
  second author. Search the first author, or a title word.
- **`item.search` matches an ASCII-folded index.** A query carrying diacritics
  (`Frühwirth`, `Grün`) returns zero against the folded record (`fruhwirth`,
  `grun`); the ASCII form finds it. `resolve.py` searches both the typed and the
  ASCII-folded form and compares folded on both sides, so either spelling
  resolves; by hand, fold the diacritics out of the query token.
- **`item.search` does NOT index the DOI field.** Searching `"10.1111/jels.12413"`
  returns zero hits even for the exact item with that DOI. To resolve a DOI to
  a Zotero item, look up the DOI's first-author surname via Crossref
  (`https://api.crossref.org/works/<doi>`, free, no auth), then search BBT
  by that surname, then filter results by `DOI` field exact-match. This is
  what `ingest.py` does.
- **Cite keys must be read from `item.search` results — never constructed.**
  BBT cite-key formats are deterministic but longer than they look. Tried
  `mageshHallucinationFreeAssessing2025` (truncated guess) → "not found."
  Actual key was `mageshHallucinationFreeAssessingReliability2025`. Always
  copy the `citation-key` field from the search response verbatim.
- **`item.export` needs the correct `library_id`.** My Library is `id: 1`.
  Group libraries get higher IDs. The library name in the search response
  maps to a numeric `id` via `user.groups`. Without the library_id, export
  returns "not found" even with a valid cite key.
- The directory name in `~/Zotero/storage/<KEY>/` is the **attachment** key,
  not the parent item key. Don't try to look items up by storage dir name.
- Some items may have multiple `file` entries (`Full Text:/path.pdf;` + a
  snapshot). Filter to paths ending `.pdf`. The format is
  `<label>:<path>:<mime>` separated by `;`.

### 2. Render PDF → per-page markdown (auto-escalating cascade)

Use the bundled `render.py`:

```bash
uv run --with pymupdf4llm --with docling --with easyocr \
    python render.py "<absolute-pdf-path>" ~/zettelkasten/papers/<citekey>/
```

> **PDF → text is ALWAYS this Python cascade. Never improvise.** Do not call
> `pdftotext`, `pdf2txt`, `tesseract`, `ocrmypdf`, hand-run `pymupdf4llm`/docling,
> or stand up an OCR tool by hand and write a one-off converter. The cascade
> below handles the whole escalation, including GPU OCR. If it reports
> `NEEDS MOCR`, confirm with the user and re-run with `--allow-mocr` — that is the
> escalation path; there is no other.

`render.py` and `ingest.py` both delegate to `renderer.py`, which tries
renderers in cost order and uses the first whose output passes a quality
check:

1. `pymupdf4llm` (AGPL-3, fast) — handles most papers with embedded text.
2. `docling` no-OCR (Apache-2.0, slower) — handles broken text layers
   and U+FFFD-saturated PDFs (e.g. Stephens 2000).
3. `docling` + EasyOCR (Apache-2.0, slowest, GPU-friendly) — handles
   scanned PDFs and old PDFWriter output with no text layer (e.g.
   Schraw 1994).
4. `dots.mocr` (VLM OCR on a local vLLM server) — **confirm-gated, off by
   default.** Only runs with `--allow-mocr`; for scanned books where even
   docling+OCR drops too many pages (e.g. Polanyi's *Tacit Dimension*).

Quality check fails a render if any of:

- more than **30%** of pages have <50 chars of *real content*. "Real content"
  is measured after stripping pymupdf4llm's `==> picture [WxH] intentionally
  omitted <==` image placeholder (Levenson 1973 case, 0.2.3). The gate was
  tightened from 50% in 0.5.0: docling+OCR rendered Polanyi with 40/102 pages
  near-empty (39%), losing ~46% of the book, and the old 50% gate let it pass.
- U+FFFD ('replacement character') covers more than 0.5% of all chars
  (broken-encoding case).

When tiers 1–3 are exhausted, the render is **refused** (no lossy pages
written):

- **without `--allow-mocr`** → `render.py` exits `3` / `ingest.py` logs
  `NEEDS MOCR`, reporting the near-empty fraction. Surface this to the user;
  on a yes, re-run the *same command* with `--allow-mocr`.
- **with `--allow-mocr`** → the cascade starts the `dots.mocr` vLLM server once,
  OCRs every flagged paper, folds the result into the standard `papers/`
  layout (`renderer: "mocr"`), and stops the server (freeing VRAM) on exit.
  Requires a `[mocr]` section in `config.toml` (see Dependencies); inert and
  reported if absent.

Output (verified on 28-page Yim 2024 via pymupdf4llm and 16-page Schraw
1994 via docling+OCR):

```
~/zettelkasten/papers/<citekey>/
├── full.md            # combined, page boundaries marked `<!-- page:N -->`
├── pages/
│   ├── 001.md
│   └── ... (one per page)
└── meta.json          # page_count, sha256_prefix, source_pdf, renderer,
                       # ocr, and renderer_note when escalation fired
```

`meta.json` records which renderer + OCR flag produced the file, plus a
`renderer_note` describing the escalation chain. Example for Schraw 1994:

```json
{
  "renderer": "docling",
  "ocr": true,
  "renderer_note": "escalated: pymupdf4llm(fail) -> docling(fail) -> docling+ocr(pass)"
}
```

**OCR performance and quality notes:**

- EasyOCR uses GPU if available (~500 MiB VRAM per concurrent doc). Force
  CPU by exporting `CUDA_VISIBLE_DEVICES=` (empty) before invoking.
- Approximate timing on a 16-page paper: <30 s pymupdf4llm, ~30-60 s
  docling no-OCR, ~1-3 min docling+OCR on a modern GPU.
- OCR output has expected substitutions (`0`↔`o`, `S`↔`5`, dropped short
  words like `to`/`of`). Use the rendered text to *locate* a quote, then
  re-verify against the source PDF before pasting verbatim. `blockquote.py`
  normalises whitespace but is brittle on OCR substitutions.

### 3. Surface a page-keyed blockquote

Use the bundled `blockquote.py`:

```bash
python blockquote.py ~/zettelkasten/papers/<citekey>/pages "<citekey>" "<verbatim quote substring>"
```

Emits markdown like:

```markdown
> teachers face challenges such as insufficient CK and experience with AI

[@yimTeachersPerceptionsAttitudes2024, p. 1]
```

The script normalises whitespace for fuzzy matching but emits the original
text from the page. **If no match is found, it exits non-zero and prints
NO MATCH** — do not invent a quote. Per the zettelkasten `AGENTS.md` rule,
unverified quotes are flagged with `> [unverified] ...` for human review.

## Annotating cited passages back onto the PDF (requires zotero-api-plus)

`blockquote.py` surfaces a verified quote *for* citing. `annotate.py` does the
inverse: it writes that passage back into the Zotero PDF as a **highlight whose
comment carries the citation**, so every passage you used is marked in the
source. In Zotero's reader you (or a collaborator) then see, on the page, which
of your writing each highlighted span supports.

**Requires** the zotero-api-plus build with the annotation endpoints
(`add-highlight`, `add-note`, `read-annotations`, `read-note`, `open-pdf`,
`delete-annotation`). `annotate.py` probes `GET /api/plus/read-annotations` on
startup (a bare GET returns `400 "No item key"` when present, `404` when the
build is too old) and halts with instructions if they are absent.

**It WRITES to your library**, and My Library annotations **sync to your other
devices** (verified). Writing is the point of the tool, so it is not gated the
way `fetch.py` gates `add-item`; the dedup marker (below) makes re-runs safe, and
`--dry-run` resolves and locates a span without writing.

### Why rects mode is the default (the 5-page cap)

Zotero's PDF worker caps `getRecognizerData` at **5 pages**, so the endpoint's
own text-anchored mode only reaches a quote in the first five pages. `annotate.py`
therefore computes the geometry locally with **PyMuPDF** (already a render
dependency): `page.search_for(quote)` for the rects, `page.rect.height` for the
page height. It posts *position (rects) mode*, which works on **any** page.
PyMuPDF's TOP-LEFT rects and page height feed the endpoint directly; it flips
them to Zotero's bottom-left space, so the consumer does no coordinate maths.
Verified live on Arksey & O'Malley 2005, physical p.8 (My Library): the
highlight landed on the right span and synced.

### Single passage

```bash
uv run annotate.py <citekey> --page <physical-page> \
    --quote "<verbatim passage>" --note "<why you cited it>"
```

- `--page` is the **physical** PDF page (page 1 = first page of the file), the
  same basis the render output uses — *not* the printed page number (e.g. Arksey
  physical p.8 is printed p.5).
- `--dry-run` resolves the item, checks for an existing annotation, and locates
  the span (reports the rect count) without writing.
- `--color #rrggbb` overrides Zotero's default highlight colour.

The same citekey can exist in several libraries, only some with the PDF
attached. `annotate.py` exports every copy and uses the one that has a PDF —
when calling the endpoints by hand, select that copy yourself (see Common
mistakes).

### Batch — annotate every passage you used

`annotate.py --batch passages.jsonl` loops the single-passage path over a JSONL
file, one object per line:

```json
{"citekey": "yim...", "page": 7, "quote": "the verbatim span", "note": "the claim it supports"}
```

Generating that list — walking a draft or the literature notes for every
`> quote` + `[@citekey, p. N]` pair — is the **caller's** job (have Claude
produce the JSONL). `annotate.py` only applies it. The batch is idempotent, so a
re-run after you add citations annotates only the new ones.

### Idempotency and the note fallback

Every annotation's comment carries a machine marker `⟦ax:<fingerprint>⟧`, the
fingerprint being a whitespace/case-normalised hash of the quote. Before
annotating, `annotate.py` reads existing annotations (`read-annotations` returns
notes **and** highlights) and skips any passage whose marker is already there —
so re-runs never duplicate, and a passage recorded either as a highlight or as a
note-fallback counts as done.

When PyMuPDF cannot locate the quote — a scanned/OCR'd page with no text layer,
or text drift between the rendered markdown and the live PDF — `annotate.py`
falls back to a **page-anchored sticky note** (`add-note`) carrying the same
citation + marker, so the citation is still recorded on the right page. Those
runs report `◐ noted` instead of `✓ highlighted`.

### Inspect / clean up

```bash
uv run annotate.py --list <citekey>          # show existing annotations
curl -sS -X POST http://localhost:23119/api/plus/delete-annotation \
     -H 'Content-Type: application/json' -d '{"key":"<annKey>","libraryID":<id>}'
```

`open-pdf` is a plain GET, so
`http://localhost:23119/api/plus/open-pdf?key=<itemKey>&page=<n>` is a clickable
citation link that opens the passage in Zotero's reader.

## Adding notes to the zettelkasten

Two note types, two locations, two purposes (per `~/zettelkasten/AGENTS.md`).
This section adds the operational steps; the conventions live in AGENTS.md.

### Literature notes — one per cite key, in the project

Path: `<project>/notes/literature/<citekey>.md`

After `ingest.py` renders a paper, scaffold a literature note. If Claude
drafts it, set `ai-generated: true` until the human reviews:

```markdown
---
citekey: <citekey>
title: <paper title>
authors: <surnames>
year: <year>
ai-generated: true   # remove after human review
---

# <Paper title>

## TL;DR
<your own paraphrase, NOT the abstract>

## Key claims
- <claim 1> [@<citekey>, p. N]
- <claim 2> [@<citekey>, p. N]

## Verified quotes

> <verified blockquote from blockquote.py>

[@<citekey>, p. N]

## Questions / critique / connections
- ...

## Linked permanent notes
- [[<id>]] - <slug>
```

**Verify every blockquote with `blockquote.py`** before writing it:

```bash
python plugins/denubis-bibliography/skills/using-bibliography/blockquote.py \
    ~/zettelkasten/papers/<citekey>/pages \
    <citekey> \
    "<verbatim substring>"
```

If it returns `NO MATCH`, do not invent a quote. Mark `> [unverified] ...`
and flag for the human, per AGENTS.md rule 1.

### Permanent notes — atomic ideas, in the central zettelkasten

Path: `~/zettelkasten/permanent/<YYYYMMDDHHMM>-<slug>.md`

Generate the timestamp ID with `date +%Y%m%d%H%M`. The slug is human-readable
and may change later; the ID never does.

```markdown
---
id: <YYYYMMDDHHMM>
title: <slug>
created: <YYYY-MM-DD>
tags: [t1, t2]
ai-generated: true   # remove after human review
---

# <slug>

<one atomic idea, 100-400 words, in the user's own voice>

> <verified blockquote, if any>

[@<citekey>, p. N]

Related: [[<other-id>]]
```

A permanent note **never** references project-local files. Project notes link
*to* permanent notes; permanent notes link only to other permanent notes
(by ID) and to stable cite keys (`[@key]`). Projects move and disappear;
the central zettelkasten survives them.

## Cross-reference between project and central

Three resolution paths, each handled by a different layer:

1. **Project literature note → Permanent note** — wikilink `[[<id>]]`.
   Resolves when both project and `~/zettelkasten/` are open in your editor
   (Obsidian, Foam, etc.). For pandoc rendering of a project draft, use a
   relative markdown link instead:
   ```markdown
   See [three-pass reading](../../../zettelkasten/permanent/202605111512-three-pass-reading.md).
   ```

2. **Note → Source citation** — pandoc cite syntax `[@citekey, p. N]`.
   Resolves at pandoc render time against whichever `.bib` you pass via
   `--bibliography`. Two bibs in play:
   - `<project>/references.bib` — BBT auto-export of the project's Zotero
     collection. Covers in-project citations.
   - `~/zettelkasten/references.bib` — auto-built union of cite keys
     appearing across `permanent/`. Covers cross-zettelkasten citations
     when rendering the zettelkasten as a standalone document.

3. **Permanent note → Permanent note** — wikilinks `[[<id>]]` only.

**For pandoc projects:** include both bibs:
```bash
pandoc draft.md \
    --bibliography=<project>/references.bib \
    --bibliography=~/zettelkasten/references.bib \
    --citeproc -o draft.pdf
```

## Bootstrap a project (first invocation in a fresh project dir)

When the skill is invoked from a project that does not yet have
`references.bib` or `notes/literature/`, halt and prompt the user with the
following setup steps. **Do not silently create these directories** — the
user owns the project layout.

> This project does not yet have a `references.bib` or notes scaffolding.
> To wire up Zotero auto-export and create the notes layout:
>
> 1. In Zotero, right-click the collection that backs this project →
>    **Export Collection…**
> 2. Translator: **Better BibLaTeX**
> 3. Check **Keep updated**, leave Export Files / Notes unchecked
> 4. Save to: `<absolute path to project>/references.bib`
> 5. In **Preferences → Export → Fields to omit**, add `file` (so absolute
>    `~/Zotero/storage/...` paths don't leak into git)
> 6. In **Preferences → Better BibTeX → Automatic Exports**, confirm the
>    trigger is **On change**
> 7. Create the notes layout: `mkdir -p notes/literature notes/structure`
>
> Once that's done, re-invoke the skill.

The Zotero collection name is the user's choice; the SKILL does not assume
a naming convention.

## Refreshing the on-disk bib

BBT's "Automatic Exports" ("Keep updated") writes the project bib on every Zotero
change, but the debounce is opaque: the file can lag Zotero state by seconds to
minutes after edits/syncs. As of **zotero-api-plus 0.4.0** there is an on-demand
trigger — `POST /api/plus/run-autoexport {"path": "<bib>"}` forces BBT's own
registered auto-export for that exact path to run. It is **trigger-only**: a 200
means it fired, not that the export succeeded (BBT swallows export failures —
`status` always reaches `done`, `error` always `""`), so success is proven against
the written file, never claimed by the response.

**Use `resolve.py --bib` — the only sanctioned refresh.** It triggers the
registered export, then verifies the citekey landed in a WELL-FORMED bib (a real
BibLaTeX parse via bibtexparser, not a grep that a truncated write could fool),
with the wait/timeout living caller-side:

```bash
uv run resolve.py --citekey <key> --bib /abs/path/to/project/references.bib
```

- Pass the **absolute** bib path you read from the project's own `bibliography:`
  declaration — never a guessed filename.
- `no-autoexport` (no "Keep updated" export registered for that path) → it
  surfaces the setup gap and lists the paths BBT actually holds, rather than
  polling forever. Fix the registration in Zotero (Export Collection → Keep
  updated); do not paper over it.
- Endpoint absent (Zotero without zotero-api-plus >= 0.4.0) → it tells you to
  install/upgrade. There is **no faithful collection-scoped force-refresh without
  it**, so set up the endpoint rather than improvising.

**Do not hand-roll a refresh.** The library pull-export
(`/better-bibtex/library?/<libraryID>/library.biblatex`) dumps the WHOLE library,
not the project collection the bib targets, so it clobbers `references.bib` with
wrong-scope content. And hand-rolling `item.export` + a diff to splice one entry in
is the exact improvisation that left a bib in an uncertain state before a freeze —
the failure this endpoint exists to remove.

## Bootstrap (when config or zettelkasten missing)

If the user has not yet set up the central zettelkasten or config:

1. Halt with a clear error explaining what's missing.
2. Direct them to create `~/.config/denubis-academic-research/config.toml`
   with at minimum:
   ```toml
   zettelkasten_root = "~/zettelkasten"
   ```
3. Direct them to create `~/zettelkasten/` (and ideally `git init` it for
   cross-machine sync). The conventions live in
   `~/zettelkasten/AGENTS.md` once it exists.

Do **not** create the zettelkasten silently. The user owns it.

## Dependencies

A Python venv with `pymupdf4llm` (primary) and `docling` + `easyocr`
(fallback). `ingest.py`'s PEP 723 header pulls all three via `uv run`.
For standalone invocation of `render.py`:

```bash
uv run --with pymupdf4llm --with docling --with easyocr python render.py \
    "<pdf>" "<out>"
```

First docling install is heavy (~1-2 GB: torch + CUDA wheels + EasyOCR
models) and cached afterward in `~/.cache/uv/`. EasyOCR English models
download from JaidedAI on first OCR run (~50 MB).

**mocr tier (optional, `--allow-mocr`).** The fourth renderer escalates to a
local `dots.mocr` vLLM server — a machine-specific GPU deploy, not bundled. The
plugin calls the deploy's own `dots-serve.fish` / `dots-ocr.fish` /
`dots-stop.fish` wrappers, so configure its path in
`~/.config/denubis-academic-research/config.toml`:

```toml
[mocr]
repo = "~/people/Brian/dots.mocr"   # the dots.mocr deploy checkout
# port = 8000                       # vLLM server port (default)
# startup_timeout = 300             # seconds to wait for model load (default)
```

Without `[mocr]`, `--allow-mocr` is inert (reported, not silent). `dots.mocr`
carries its own licence (see the deploy); it is invoked, never redistributed.

License summary:

- `pymupdf4llm` is **AGPL-3** — propagates to anything that ships it. Do
  not bundle in CC-BY-SA-4.0 distributions; require user-side install.
- `docling` is **Apache-2.0**. Safe to depend on.
- `easyocr` is **Apache-2.0**. Safe to depend on.

**docling OCR-engine pin:** `renderer.py` pins
`EasyOcrOptions(lang=["en"])` explicitly. Recent docling builds default to
RapidOCR, which downloads ONNX models from `modelscope.cn` at first use —
that endpoint fails behind some firewalls / outside China. If you bypass
`renderer.py` (e.g. one-off scripts), pin EasyOCR the same way.

## Platform notes

Linux is the primary development platform; macOS should behave the same.
The skill is portable on Windows from 0.2.2 onward but has some PowerShell
quirks worth knowing:

- **`curl` in PowerShell is an alias for `Invoke-WebRequest`**, not the BSD
  `curl` with `-sS`/`--max-time` flags. Use either:
  ```powershell
  curl.exe -sS --max-time 3 http://localhost:23119/connector/ping
  Invoke-RestMethod -Uri http://localhost:23119/connector/ping -TimeoutSec 3
  ```
  …or just open the URL in a browser.
- **Paths.** Config and zettelkasten live at `$HOME\.config\denubis-academic-research\config.toml` and `$HOME\zettelkasten\` respectively. These are
  outside Windows app-data conventions (`%APPDATA%`) but the path is shared
  across platforms by design so cross-machine sync stays simple. Don't move
  them.
- **Zotero storage paths** on Windows include a drive-letter colon
  (`C:\Users\...\Zotero\storage\KEY\paper.pdf`). `bbt.parse_pdf_paths`
  handles this from 0.2.2 onward — both unescaped (`C:\...`) and
  BibLaTeX-escaped (`C\:\...`) forms. If 0.2.1 or earlier ever surfaces,
  the symptom is `no PDF attachment in this item` for items that clearly
  have a PDF.
- **stdin pattern for batch DOIs.** Linux/macOS: `cat dois.txt | uv run
  ingest.py -`. PowerShell: `Get-Content dois.txt | uv run ingest.py -`.
- **Git Bash / WSL** are reasonable alternatives if PowerShell quoting and
  alias quirks pile up — they accept the Linux-style commands verbatim.

## What this skill does NOT do (yet)

- **Fetches papers only via `zotero-api-plus` (v0.3.0+), behind confirmation.**
  Without that plugin it does not fetch — the Zotero connector is the only thing
  that talks to publishers. With it, see "Fetching a missing paper"; a paywalled
  paper with no open-access copy still returns metadata-only.
- **Does not build the central `references.bib`.** The zettelkasten's
  auto-build of `references.bib` from `[@key]` tokens in `permanent/` is
  designed but not implemented here.
- **Does not auto-generate literature notes** in `<project>/notes/literature/`.
  The template and process are documented above (see "Adding notes to the
  zettelkasten") but you write the file by hand or have Claude scaffold it
  marked `ai-generated: true`. There is no `note new` command yet.
- **Does not verify quotes against source PDFs after-the-fact.** The
  `note verify` operation is designed but not implemented; for now use
  `blockquote.py` at quote-creation time as the verification step.
- **Does not handle SSL bypass for EZProxy.** Designed (dated stamp file in
  project) but not implemented.
- **Does not generate the batch passage list itself.** `annotate.py --batch`
  consumes a JSONL of `{citekey, page, quote, note}`; walking a draft or the
  literature notes to *produce* that list is the caller's job (have Claude do
  it). The script only applies a list it is given.
- **Cannot span-highlight scanned/OCR'd sources.** `annotate.py` locates a quote
  via the PDF text layer (PyMuPDF); a page with no text layer (e.g. Schraw 1994,
  Polanyi) has nothing to anchor on, so it falls back to a page-anchored note
  rather than a highlight on the span.

When asked to do any of these, halt and say so explicitly. Do not improvise.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Calling `item.export` without `library_id` | Always look up `library_id` via `user.groups`. My Library = 1; groups vary. |
| Constructing cite keys by hand or truncating them | Copy `citation-key` verbatim from `item.search` response. BBT keys are longer than they look. |
| Searching by a remembered/constructed citekey, getting "not found", and concluding the paper is absent | The real key can differ from what you'd guess: a paper authored "Imre Lakatos" was filed with given/family swapped, so its key is `imreFalsificationMethodologyScientific1970`, not `lakatos…1970a`. Resolve with `resolve.py --title`/`--author` (or fix the misfiled creator in Zotero) — never trust a remembered citekey. |
| Multi-token `item.search` queries returning zero hits | Search is AND-style. Use single tokens (author surname OR title fragment), then refine. |
| Treating a `resolve.py` / `item.search` "no match" as proof a paper is absent | It is not. `item.search` is AND-fuzzy, **first-author-only**, and **ASCII-folded** — three independent ways a present paper returns zero. `resolve.py` now compensates (unions every supplied key, folds diacritics, matches hyphen-components), but if it still says no-match, query the API directly for a distinctive title word before concluding absence. The honest no-match message says exactly this. |
| Searching `--author` for a co-author (`Ghahramani` in "Wade, Ghahramani"; `Kruschke` in "Liddell, Kruschke") and getting zero | `item.search` indexes only the FIRST author surname. Pass the first author, or add a `--title` word — `resolve.py` unions all supplied keys, so `--author <coauthor> --title <word>` resolves. |
| Searching `--author Frühwirth` (diacritics) and getting zero | BBT's index is ASCII-folded, so `Frühwirth` misses `fruhwirth`. `resolve.py` searches the folded form too and compares folded on both sides; by hand, strip diacritics from the query token. |
| Searching by DOI directly (`item.search("10.1234/x.5")`) and getting zero hits | DOI field is not indexed for fulltext search. Resolve DOI → surname via Crossref, then search by surname, then filter results by exact DOI match. |
| Using the storage directory name (e.g. `2367YXMF`) as the item key | That's the attachment key. The parent item has a different key; use cite-key based lookups. |
| Inventing a quote when `blockquote.py` reports NO MATCH | Don't. Mark `> [unverified]` and flag for the human. |
| Asserting "I rendered N papers" without showing the file paths | Verify by `ls ~/zettelkasten/papers/<citekey>/`. Don't claim success without checking. |
| Treating research-agent suggestions as verified options | They're inputs, not conclusions. Verify with a real call before asserting capability. |
| Bouncing the user to the Zotero UI to trigger a stale auto-export refresh | Force the registered export on demand: `resolve.py --citekey <key> --bib <abs path>` (POST /api/plus/run-autoexport, zotero-api-plus >= 0.4.0), which triggers then verifies. See "Refreshing the on-disk bib" above. |
| Hand-rolling `item.export` + a diff to splice one new citekey into a project bib | That improvisation left a bib in an uncertain state before a freeze — the failure this endpoint exists to remove. Use `resolve.py --citekey <key> --bib <abs path>`: it triggers the registered "Keep updated" export (BBT's own bytes) then verifies the citekey is present in a well-formed bib. Never construct or patch bib entries by hand. |
| Refreshing a project bib with the library pull-export (`/better-bibtex/library?/<id>/library.biblatex`) | That dumps the WHOLE library, not the project collection the bib targets, so it clobbers `references.bib` with wrong-scope content. Use `resolve.py --bib` (forces the registered collection export); if the endpoint is absent, install/upgrade zotero-api-plus to >= 0.4.0 rather than pulling the whole library. |
| Searching for an item that lives in multiple libraries and assuming the first `item.search` hit is the canonical copy | The same paper can exist in My Library AND a group library as separate Zotero items with the same cite key. Always pass the explicit `library_id` to `item.attachments` / `item.export` for the library you actually want. |
| Assuming Wiley chapter DOIs (`10.1002/<bookdoi>.chN`) work in `ingest.py` | Crossref returns empty `author` for those DOIs, so the surname-search step has nothing to query and lookup fails. Bypass DOI: get the PDF path via `item.attachments` by cite key, then call `render.py` directly. |
| Verifying a quote with `blockquote.py` and giving up at the first NO MATCH | Try adjusted substrings before flagging unverified: strip Unicode apostrophes, drop fragments that fall inside an HTML-rendered table cell, check whether the "quote" is actually a paraphrase of source text. The real text is usually present — match logic is brittle. |
| Treating docling+OCR output as faithful transcription | OCR introduces substitutions (`0`/`o`, `S`/`5`, dropped short words). For a paper rendered via docling+OCR (`meta.json: "renderer": "docling", "ocr": true`), use the markdown to *locate* a quote, then verify the exact wording against the source PDF before pasting verbatim. |
| Assuming docling defaults to EasyOCR | Recent docling builds default to RapidOCR, which downloads ONNX models from `modelscope.cn` at first OCR use — that endpoint is unreliable outside China. `renderer.py` pins `EasyOcrOptions(lang=["en"])` explicitly. Match that in any one-off script that calls docling directly. |
| Bypassing the cascade by hand-running pymupdf4llm and missing the empty-page case | The render functions in `renderer.py` quality-check output (>50% empty pages, or >0.5% U+FFFD) and escalate. If you skip the cascade, you silently get empty pages on no-text-layer PDFs (Schraw 1994 case) or U+FFFD-saturated text (Stephens 2000 case). Use `render_pdf_with_fallback` rather than calling `pymupdf4llm.to_markdown` directly. |
| Reaching for PowerShell's `curl` to ping Zotero on Windows | `curl` in PowerShell is `Invoke-WebRequest` with different syntax; the `-sS --max-time` flags don't exist. Use `curl.exe ...` (real curl, shipped with Windows 10+) or `Invoke-RestMethod -Uri ... -TimeoutSec 3`. |
| Running 0.2.1 or earlier on Windows and getting "no PDF attachment" for items that clearly have one | `parse_pdf_paths` in 0.2.1 and earlier collided with the Windows drive-letter colon (`C:\...`) and returned no path. Upgrade to 0.2.2+. |
| Hand-writing a multi-line `python3 -c "…"` block in bash to dig a `collectionKey` out of `/api/plus/libraries` | That improvisation is what broke (shell mangled the multi-line quoting). Use `fetch.py --group … --collection …` — it resolves the key in one call and previews before writing. |
| Reaching for `pdftotext`/`tesseract`/manual docling, or standing up an OCR tool by hand + a one-off converter, when a render looks bad | PDF→text is always the `renderer.py` cascade. On `NEEDS MOCR`, confirm with the user and re-run with `--allow-mocr` — the cascade drives the dots.mocr spinup/OCR/spindown and folds output into `papers/` itself. |
| Passing the printed page number to `annotate.py --page` | Use the **physical** PDF page (page 1 = first page of the file). Printed and physical pages differ (Arksey physical p.8 = printed p.5). |
| Calling `add-highlight`/`add-note` directly with the first `item.search` hit | The citekey may exist in several libraries, only some with the PDF attached. `annotate.py` exports every copy and uses the one with a PDF; by hand, resolve to that copy and pass its `libraryID`. |
| Expecting `add-highlight` text mode to highlight past page 5 | `getRecognizerData` caps at 5 pages. Use rects (position) mode — `annotate.py` computes the rects with PyMuPDF, so any page works. |

## Provenance

This skill documents the path demonstrated end-to-end on 2026-05-10–11 in
the academic-bibliography design conversation. The render and blockquote
scripts are the same scripts used in that demo, lightly cleaned. Anything
beyond what the demo proved is marked explicitly above.

**2026-05-12 addenda** (the project, 42-paper rendering pass):

- "Refreshing the on-disk bib" section added — HTTP pull-export URL pattern
  discovered after the BBT JSON-RPC method-list probe confirmed no
  `autoexport.run`-style trigger exists.
- Common-mistakes additions: stale-bib UI bounce; multi-library item
  disambiguation; Wiley chapter DOIs failing in `ingest.py`; brittle
  `blockquote.py` matching on Unicode apostrophes, HTML-rendered table cells,
  and paraphrased "quotes".
- Confirmed `ingest.py` end-to-end on a methodology corpus (35
  journal articles + 8 burst chapter PDFs + 7 late adds → 42 papers; 0
  render failures with the HTTP-pull-export-driven workflow).

**2026-05-14 addenda** (docling+OCR fallback integration):

- Auto-escalating renderer cascade landed in `renderer.py`:
  `pymupdf4llm` → `docling` (no OCR) → `docling`+OCR. Quality heuristic
  (>50% near-empty pages or >0.5% U+FFFD chars) decides escalation.
  `render.py` and `ingest.py` both delegate to `renderer.py`; the
  previously duplicated render logic is now single-sourced.
- Verified end-to-end on Schraw 1994
  (`schrawAssessingMetacognitiveAwareness1994`) — 1980s Acrobat PDFWriter
  output with no embedded text layer. pymupdf4llm and docling-no-OCR each
  produced 16/16 empty pages; docling+OCR produced 43 KB of clean text
  across 16 pages, structurally usable for quote location.
- Regression-tested on Arksey & O'Malley 2005 — pymupdf4llm path still
  fires on the first try; no spurious escalation.
- `EasyOcrOptions(lang=["en"])` pinned explicitly because recent docling
  builds default to RapidOCR (downloads models from `modelscope.cn` at
  first use; unreliable outside China).
- `meta.json` schema additions: `renderer`, `ocr`, and `renderer_note`
  (only set when escalation fired). The pre-2026-05-14 fields
  (`source_pdf`, `page_count`, `sha256_prefix`) are unchanged.

**2026-05-14 third pass** (image-only page detection, Levenson 1973
discovery):

- Quality heuristic now strips pymupdf4llm's `==> picture [WxH]
  intentionally omitted <==` placeholder before measuring page content
  length. The marker is ~50 chars - right at the empty-page threshold -
  so previously a marker-only page (image-only PDF, no text layer)
  appeared "non-empty" and the cascade did not escalate. Levenson 1973
  (10.1037/h0035357) exposed this; a manual one-off docling+OCR pass
  was needed to render it under 0.2.2.
- Renderer module's `quality_assessment` is now covered by 14 unit tests
  under `tests/test_bibliography_renderer.py` (empty pages, marker-only,
  marker+content, multi-marker, U+FFFD ratio, threshold edges).
- Renderer-emitted placeholders are renderer-specific; only
  pymupdf4llm's is stripped (docling and EasyOCR don't emit one for
  image-only pages - they produce actual empty pages, which the existing
  heuristic catches).

**2026-05-14 second pass** (Windows hardening for a collaborator's project):

- `parse_pdf_paths` extracted into `bbt.py` and hardened for Windows
  drive-letter colons (`C:\Users\...`). Both unescaped and `\:`-escaped
  BibLaTeX forms now parse correctly; 14 new unit tests under
  `tests/test_bibliography_bbt.py` cover Linux/macOS, Windows in both
  forms, multi-attachment entries, mixed PDF+HTML attachments, case
  variations, and negative cases.
- 0.2.1 -> 0.2.2: parser hardening + SKILL.md Platform-notes section
  documenting PowerShell quirks (`curl.exe`/`Invoke-RestMethod`, `Get-Content`
  stdin pattern, drive-letter colon handling). No behaviour change on
  Linux/macOS; previously broken Windows path becomes the no-op happy
  case there.
- Still untested live on Windows. Hardening done defensively from the
  Linux side based on mental simulation of the parser against
  `<label>:C:\path:application/pdf` shape; if Windows BBT emits something
  unexpected, the unit tests under `tests/test_bibliography_bbt.py` are
  the place to add the new case before another parser change.

**2026-06-03 addendum** (zotero-api-plus fetch integration):

- New section "Fetching a missing paper" documents the confirm-gated fetch path
  via `zotero-api-plus` v0.3.0 (`add-item-by-id`, `create-collection`,
  `libraries`, `selected-collection`). The skill no longer claims "never fetches
  papers" — it fetches behind explicit confirmation when the plugin is present,
  and resolves-first to avoid duplicates (the endpoint does not dedup).
- Verified end-to-end on `10.1007/s13347-024-00760-w` (Conradie & Nagel,
  CC-BY): `create-collection` "test" in the `bbs-cat-agent` group →
  `add-item-by-id` (`pdf: present`, PDF on disk) → `ingest.py` rendered 24 pages
  via pymupdf4llm. Endpoint contracts read from
  `~/people/Brian/zotero-api-plus/src/addon.ts`, not transcribed from a summary.

**2026-06-03 second pass** (`fetch.py` helper for the resolve + fetch step):

- Added `fetch.py`. The group/collection-name → `groupID`+`collectionKey`
  resolution and the `add-item-by-id` call now live in one tested helper instead
  of being improvised as raw curl + a multi-line `python3 -c "…"` block in bash.
  That improvisation broke on shell quoting (`/bin/bash: eval: line 15: syntax
  error near unexpected token '('` while fetching `10.1007/s11136-018-1798-3`
  into group 6549571) — the resolution intent was correct; only the hand-written
  bash failed.
- `fetch.py` separates a pure functional core (`resolve_target`,
  `parse_add_item_response`) from a thin httpx shell. The core is covered by 13
  unit tests under `tests/test_bibliography_fetch.py` (group by name / numeric
  ID / My Library, collection found / missing / ambiguous, case-insensitivity,
  and the 200/400/404 response contract).
- The confirm-gate is now structural: a bare run resolves and previews without
  writing; `--fetch` is required to POST to the library. Verified the live
  preview resolves `Bayesian / Methods` → key `VPN6BBUC` in group 6549571.
- Endpoint and `pdf`-status contracts read from
  `~/people/Brian/zotero-api-plus/src/addon.ts` and `utils/pdf-status.ts`.

**0.5.0** (DOI-in-paper-out + mocr escalation tier):

- `fetch.py --fetch` now renders by default (DOI in → fetched item → per-page
  markdown out), delegating to `ingest.py` in a subprocess so render deps stay
  off the lightweight resolve/preview path. `--no-render` opts out. Verified
  live: fetched COSMIN (`10.1007/s11136-018-1798-3`) → handed to `ingest.py`,
  which resolved the PDF and produced an 11-page render.
- Near-empty-page gate tightened 50% → 30% after the Polanyi *Tacit Dimension*
  failure: docling+OCR came out 39% near-empty (40/102 pages, ~46% of the book
  lost) and passed the old gate. Empirically grounded: clean renders sit at
  0–3% near-empty, the bad docling render at 39%. Word-likeness was tried first
  and discarded — the garbled docling output scored 0.96, *higher* than clean,
  because the failure was lost pages, not garbled words.
- Added the `dots.mocr` escalation tier (`renderer.mocr_server` + the `mocr`
  branch in `render_pdf_with_fallback`). On cascade exhaustion the render is
  refused (`NeedsMocr`, exit 3) unless `--allow-mocr`, which starts the vLLM
  server once, OCRs, folds the combined `_nohf.md` into `papers/` via
  `fold_mocr_markdown` (replacing the throwaway `convert_polanyi.py`), and stops
  the server on exit. Calls the deploy's own fish wrappers; output contract read
  from `dots_mocr/parser.py` + `tools/combine_markdown.py`, not assumed.
- Live-verified end-to-end on 2026-06-04: `mocr_server` spun vLLM up, OCR'd
  COSMIN (11 pages, 0 near-empty), folded, and stopped the server (VRAM freed),
  total ~63 s. The run surfaced that dots.mocr's `_nohf.md` embeds a full-page
  PNG atop each page (~86% of the file's bytes on COSMIN); `fold_mocr_markdown`
  now strips those base64 data-images, keeping only the OCR text.

**2026-06-13 addendum** (annotate cited passages back onto the PDF):

- New `annotate.py`: writes a cited passage back into the Zotero PDF as a
  highlight carrying the citation, via zotero-api-plus position (rects) mode.
  Pure core (item-key extraction, quote fingerprint, comment/marker building,
  payload construction, response parsing, and multi-library copy selection)
  covered by 26 unit tests in `tests/test_bibliography_annotate.py`; the httpx +
  PyMuPDF shell is verified live, in the FCIS shape `fetch.py` established.
- Geometry is computed locally with PyMuPDF (`page.search_for` +
  `page.rect.height`) and posted as TOP-LEFT rects + pageHeight; the endpoint
  flips to Zotero's bottom-left space. This sidesteps the recogniser's 5-page cap
  (corrected from a stale "50" in the endpoint's own comment — the PDF worker
  caps at 5), so highlights work on any page.
- Idempotent: every comment carries `⟦ax:<fingerprint>⟧`; a run reads existing
  annotations (`read-annotations`, which returns highlights too) and skips
  already-marked passages. A quote PyMuPDF cannot locate (OCR'd page / text
  drift) falls back to a page-anchored `add-note`.
- Verified end-to-end 2026-06-13 on `arkseyScopingStudiesMethodological2005`
  (My Library): resolve → dedup → rects-mode highlight on physical p.8 landed on
  the right span and synced; the re-run skipped (idempotent); `delete-annotation`
  removed the test annotation. Endpoint contracts read from
  `~/people/Brian/zotero-api-plus/src/{addon.ts,utils/highlight.ts,
  utils/annotations.ts}`, not transcribed from the API thread's summary.

**2026-06-17 addendum** (`resolve.py` — the any-key, live, truthful front door):

- New `resolve.py`: resolve a paper by author / year / title / date / citekey /
  DOI against the **running** Zotero DB (BBT `item.search` / `item.collections` /
  `item.attachments` / `user.groups`), never the cached `.bib`. Reports
  libraries, collections, PDF path + existence, and pipeline `state`, and
  auto-renders `ready-to-render` matches via a `render.py` subprocess. Pure core
  (`select_citekey_matches`, `normalize_bbt_hit`, `matches_query`,
  `classify_state`, `collection_names`, `_render_cmd`) covered by unit tests in
  `tests/test_bibliography_resolve.py`; the httpx/subprocess shell verified live in
  the FCIS shape `fetch.py` established.
- Motivation: the DOI-only resolver reported papers that ARE in Zotero as
  `NOT FOUND` (Crossref→surname→BBT pipeline failing on Wiley chapter DOIs, R
  Journal DOIs, and DOI drift — vehtari/Collins/Lombardo cases across multiple
  project sessions). Resolving by citekey/author/title removes that whole class.
- The "Lakatos is missing" ghost that motivated this was a constructed citekey
  (`lakatos…1970a`) for an item filed under `imre…1970` with no PDF — not a stale
  cache. `resolve.py` reports the wrong key as honestly absent and finds the paper
  by `--title`/`--author`.
- Bug caught at live verification, not in tests: the render subprocess must pass
  `--with pymupdf4llm --with docling --with easyocr` because `render.py` has no
  PEP 723 header; `_render_cmd` now encodes that and is regression-tested. Live
  render confirmed end-to-end (Vehtari, 28 pages via pymupdf4llm).
- DOI remains the one weak key (BBT can't search the DOI field): `--doi` uses the
  same Crossref-surname fallback as `ingest.py`. A clean DOI-field search + bundled
  on-disk path is specced for a future `zotero-api-plus` `GET /api/plus/resolve`
  endpoint, which would let `resolve.py` demote the BBT/Crossref path to a fallback.
- Critical-peer-review pass (2026-06-17) hardened truthfulness: render state is now
  **per-citekey** (a paper renders once; copies never re-render or clobber the
  shared `papers/<citekey>/` dir; `--force` re-renders) — replacing a per-copy
  sha256 check that bounced state and clobbered across library copies. An
  unconfirmable PDF is `pdf-unknown`, not a false `no-pdf` (an unresolved library
  name or failed attachment RPC no longer collapses to a confident "no PDF").
  Collections are reported per-citekey (BBT aggregates them), not per-library. The
  dead stock-API normaliser and its "identical content — harmless" claim were
  removed: the claim was live-falsified — copies of one citekey can be
  byte-different PDF files (the rare genuinely-different-document case is a Zotero
  data-hygiene matter, not arbitrated here).

**2026-06-19 addendum** (`resolve.py` false-negative fixes — three live-caught bugs):

- Motivation: six papers genuinely present in a group library
  (`2026-mq-amanda-annotation-survey`) resolved as "No matches", and the negatives
  were treated as proof of absence. Querying BBT directly proved the papers were
  there and exposed three independent false-negative bugs, each fixed with a
  failing test first.
- **Bug B — single-key search.** The old token-picker searched ONE key by priority
  (citekey > author > freeterm > title); a query keyed on a co-author returned zero
  because `item.search` indexes only the first author surname, and the title that
  would have found it was used only as a post-filter. New pure `search_tokens`
  returns every supplied key; the shell unions the hits and `matches_query` filters.
  Recall from the union, precision from the filter.
- **Bug A — exact author filter.** `matches_query` demanded an exact surname, so
  `--author Malsiner` found then dropped `Malsiner-Walli`. Now a hyphen-component
  matches (hyphen only — space-splitting would make "van" match every "van X"; no
  arbitrary substring, so "Veh" never matches "Vehtari").
- **Bug C — diacritics.** BBT's `item.search` index is ASCII-folded, so the
  correctly-spelled `Frühwirth` returned zero against `fruhwirth` while the paper
  was present. New `_ascii_fold` (stdlib NFKD, drop combining marks) is applied to
  the search token (the folded variant is searched too) and on both sides of the
  `matches_query` author/title comparison, so `Frühwirth` and `Fruhwirth` resolve
  to the same paper.
- The bare "No matches found" was replaced with an honest message: it lists the
  tokens searched and states that `item.search` being AND-fuzzy and first-author-only
  means a no-match is not proof of absence, pointing at the retry that works. This is
  the keystone fix — the bug was a session treating a flaky negative as fact.
- 15 new unit tests in `tests/test_bibliography_resolve.py` cover `search_tokens`
  (union, order, dedup, blanks, ASCII-fold variant), the author hyphen-component and
  space/substring guards, and diacritic folding on author and title. All six papers
  verified resolving live via natural queries (co-author and accented-surname
  included).

**2026-06-24 addenda** (on-demand bib refresh — run-autoexport endpoint + consumer):

- **zotero-api-plus 0.4.0 adds `POST /api/plus/run-autoexport`**, the on-demand
  trigger stock BBT never exposed (only `autoexport.add` exists over JSON-RPC). It
  forces BBT's own registered "Keep updated" auto-export for a given output path to
  run. It is trigger-only — it makes no success claim, because BBT swallows export
  failures (`status` always reaches `done`, `error` always `""`). Confirmed live
  against BBT 9.0.31.
- **`resolve.py --bib <abs path> --citekey <key>`** is the sanctioned
  trigger-plus-verify path: it triggers the registered export, then verifies the
  citekey landed in a WELL-FORMED bib using a real BibLaTeX parse (bibtexparser v2
  `failed_blocks`, not a grep a truncated write could fool), with the wait/timeout
  caller-side. On `no-autoexport` it surfaces the setup gap and lists the registered
  paths; when the endpoint is absent it directs you to install/upgrade rather than
  doing a wrong-scope library pull.
- The previous guidance (force a refresh with the library pull-export, or that no
  force-run exists) is retired: a library pull dumps the whole library, not the
  project collection, and clobbers `references.bib` with wrong-scope content.
- New unit tests in `tests/test_bibliography_resolve.py` cover the parser validity
  check (well-formed + citekey-present, truncation caught, substring-not-an-entry),
  the HTTP-response classifier (triggered / no-autoexport / endpoint-absent /
  bbt-*), and the `--bib`/`--citekey` argument validation. The `--bib` shell flow
  was verified live.
