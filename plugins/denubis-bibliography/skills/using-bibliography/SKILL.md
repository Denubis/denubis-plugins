---
name: using-bibliography
description: Use when the user wants to render a Zotero PDF into per-page markdown, or surface page-keyed blockquotes from a rendered paper. Reads from Zotero via Better BibTeX; optionally fetches a missing paper via zotero-api-plus behind explicit user confirmation.
user-invocable: true
last-reviewed: 2026-06-03
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

2. **Choose the target collection — never assume one.**

   ```bash
   curl -sS http://localhost:23119/api/plus/selected-collection
   # → {"name","key","libraryID","groupID"}  — the collection open in the UI
   # → 500 "No Collection selected."         — nothing selected; pick explicitly
   ```

   List targets with `GET /api/plus/libraries` (My Library + every group, each
   with `{key,name,parentKey}` collections and the group's `groupID`). Create a
   new target idempotently:

   ```bash
   curl -sS -X POST http://localhost:23119/api/plus/create-collection \
     -H 'Content-Type: application/json' \
     -d '{"name":"<name>","groupID":<groupID, or omit for My Library>}'
   # → {"created":true|false,"collection":{"key":"…",…}}
   ```

3. **HALT and confirm — both halves.** State exactly what will be written and
   where: *"<title/DOI> is not in Zotero. Fetch it into <collection> (<library>)
   and attach the PDF? This adds an item to your library."* Proceed only on an
   explicit yes. **Do not infer consent** from an earlier "ingest these DOIs"
   instruction — adding to the library is a distinct write the user has not yet
   authorised.

4. **Fetch.**

   ```bash
   curl -sS -X POST http://localhost:23119/api/plus/add-item-by-id \
     -H 'Content-Type: application/json' \
     -d '{"identifier":"<DOI/ISBN/PMID/arXiv>","groupID":<groupID?>,"collectionKey":"<key?>"}'
   ```

   → `{status,addedCount,titles[],items:[{title,key,pdf,attachmentID?}]}` (`404`
   if nothing could be saved). Read each item's `pdf`:

   - `present` — translator attached the PDF during this add. On disk; render.
   - `fetched` — translator gave metadata only; the `addAvailableFile` fallback
     attached an open-access PDF. On disk; render.
   - `unavailable` — item added, **no PDF** (no OA copy; likely paywalled with no
     institutional session). Tell the user; they attach via the connector, then
     re-run the render.
   - `error` — report verbatim; do not retry blindly.

5. **Render** via the normal pipeline once a PDF is present. BBT may lag a few
   seconds indexing the new item; if the first `ingest.py` run reports
   `NOT FOUND`, retry once.

**Batch (a list of DOIs):** resolve them all first, surface the
missing-and-fetchable set as ONE list, confirm the set + target collection in a
single prompt, then fetch the confirmed set and render. One confirmation for the
batch — never silent per-item writes.

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
  fragment) and refine programmatically.
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

`render.py` and `ingest.py` both delegate to `renderer.py`, which tries
renderers in cost order and uses the first whose output passes a quality
check:

1. `pymupdf4llm` (AGPL-3, fast) — handles most papers with embedded text.
2. `docling` no-OCR (Apache-2.0, slower) — handles broken text layers
   and U+FFFD-saturated PDFs (e.g. Stephens 2000).
3. `docling` + EasyOCR (Apache-2.0, slowest, GPU-friendly) — handles
   scanned PDFs and old PDFWriter output with no text layer (e.g.
   Schraw 1994).

Quality check fails a render if either:

- more than 50% of pages have <50 chars of *real content* (no-text-layer
  case). "Real content" is measured after stripping pymupdf4llm's
  `==> picture [WxH] intentionally omitted <==` image placeholder, so a
  page whose only content is one or more such markers correctly registers
  as empty (Levenson 1973 case, added in 0.2.3).
- U+FFFD ('replacement character') covers more than 0.5% of all chars
  (broken-encoding case).

If every renderer fails the quality check (unlikely outside corrupt PDFs),
`render.py` exits non-zero and `ingest.py` logs the paper as a per-paper
failure rather than writing empty pages.

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

BBT's "Automatic Exports" feature writes the project bib on every change, but
the debounce is opaque: the on-disk file can lag Zotero state by anything from
seconds to many minutes after edits/syncs. BBT JSON-RPC exposes **no method**
to force a configured auto-export to run on demand (verified empirically
against `system.listMethods`, `autoexport.list`, `autoexport.run`, and the
published method list at <https://retorque.re/zotero-better-bibtex/exporting/json-rpc/>
on 2026-05-12 — only `autoexport.add` exists, for adding new auto-export
configurations).

**To force a fresh bib on disk without bouncing the user to the Zotero UI**,
use BBT's HTTP pull-export endpoint:

```bash
curl -sS "http://localhost:23119/better-bibtex/library?/<libraryID>/library.biblatex" \
     -o <project>/references.bib
```

- `<libraryID>` is the numeric ID from `user.groups` (My Library = 1; group
  libraries get higher IDs).
- Output is byte-identical to BBT's auto-export — verified against
  `2026-bbs-jt-em-bjet-AI-metacognitive-1` (libraryID = 27, 42 entries,
  47 KB BibLaTeX) on 2026-05-12.
- Alternative translator suffixes work too: `.bibtex` for classic BibTeX,
  `.csljson` for CSL-JSON, etc. — same pattern.

The URL pattern is *not* documented in the JSON-RPC reference; it lives in
BBT's CGI-style HTTP export server, which the JSON-RPC docs do not cover.

Use this whenever you'd otherwise ask the user to open Zotero → Preferences
→ Better BibTeX → Automatic Exports → "Reset" / "Force run". That UI roundtrip
is never necessary for a bib refresh.

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

When asked to do any of these, halt and say so explicitly. Do not improvise.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Calling `item.export` without `library_id` | Always look up `library_id` via `user.groups`. My Library = 1; groups vary. |
| Constructing cite keys by hand or truncating them | Copy `citation-key` verbatim from `item.search` response. BBT keys are longer than they look. |
| Multi-token `item.search` queries returning zero hits | Search is AND-style. Use single tokens (author surname OR title fragment), then refine. |
| Searching by DOI directly (`item.search("10.1234/x.5")`) and getting zero hits | DOI field is not indexed for fulltext search. Resolve DOI → surname via Crossref, then search by surname, then filter results by exact DOI match. |
| Using the storage directory name (e.g. `2367YXMF`) as the item key | That's the attachment key. The parent item has a different key; use cite-key based lookups. |
| Inventing a quote when `blockquote.py` reports NO MATCH | Don't. Mark `> [unverified]` and flag for the human. |
| Asserting "I rendered N papers" without showing the file paths | Verify by `ls ~/zettelkasten/papers/<citekey>/`. Don't claim success without checking. |
| Treating research-agent suggestions as verified options | They're inputs, not conclusions. Verify with a real call before asserting capability. |
| Bouncing the user to the Zotero UI to trigger a stale auto-export refresh | Use the HTTP pull-export URL: `curl "http://localhost:23119/better-bibtex/library?/<id>/library.biblatex" -o <path>`. See "Refreshing the on-disk bib" above. |
| Searching for an item that lives in multiple libraries and assuming the first `item.search` hit is the canonical copy | The same paper can exist in My Library AND a group library as separate Zotero items with the same cite key. Always pass the explicit `library_id` to `item.attachments` / `item.export` for the library you actually want. |
| Assuming Wiley chapter DOIs (`10.1002/<bookdoi>.chN`) work in `ingest.py` | Crossref returns empty `author` for those DOIs, so the surname-search step has nothing to query and lookup fails. Bypass DOI: get the PDF path via `item.attachments` by cite key, then call `render.py` directly. |
| Verifying a quote with `blockquote.py` and giving up at the first NO MATCH | Try adjusted substrings before flagging unverified: strip Unicode apostrophes, drop fragments that fall inside an HTML-rendered table cell, check whether the "quote" is actually a paraphrase of source text. The real text is usually present — match logic is brittle. |
| Treating docling+OCR output as faithful transcription | OCR introduces substitutions (`0`/`o`, `S`/`5`, dropped short words). For a paper rendered via docling+OCR (`meta.json: "renderer": "docling", "ocr": true`), use the markdown to *locate* a quote, then verify the exact wording against the source PDF before pasting verbatim. |
| Assuming docling defaults to EasyOCR | Recent docling builds default to RapidOCR, which downloads ONNX models from `modelscope.cn` at first OCR use — that endpoint is unreliable outside China. `renderer.py` pins `EasyOcrOptions(lang=["en"])` explicitly. Match that in any one-off script that calls docling directly. |
| Bypassing the cascade by hand-running pymupdf4llm and missing the empty-page case | The render functions in `renderer.py` quality-check output (>50% empty pages, or >0.5% U+FFFD) and escalate. If you skip the cascade, you silently get empty pages on no-text-layer PDFs (Schraw 1994 case) or U+FFFD-saturated text (Stephens 2000 case). Use `render_pdf_with_fallback` rather than calling `pymupdf4llm.to_markdown` directly. |
| Reaching for PowerShell's `curl` to ping Zotero on Windows | `curl` in PowerShell is `Invoke-WebRequest` with different syntax; the `-sS --max-time` flags don't exist. Use `curl.exe ...` (real curl, shipped with Windows 10+) or `Invoke-RestMethod -Uri ... -TimeoutSec 3`. |
| Running 0.2.1 or earlier on Windows and getting "no PDF attachment" for items that clearly have one | `parse_pdf_paths` in 0.2.1 and earlier collided with the Windows drive-letter colon (`C:\...`) and returned no path. Upgrade to 0.2.2+. |

## Provenance

This skill documents the path demonstrated end-to-end on 2026-05-10–11 in
the academic-bibliography design conversation. The render and blockquote
scripts are the same scripts used in that demo, lightly cleaned. Anything
beyond what the demo proved is marked explicitly above.

**2026-05-12 addenda** (BJET-RR project, 42-paper rendering pass):

- "Refreshing the on-disk bib" section added — HTTP pull-export URL pattern
  discovered after the BBT JSON-RPC method-list probe confirmed no
  `autoexport.run`-style trigger exists.
- Common-mistakes additions: stale-bib UI bounce; multi-library item
  disambiguation; Wiley chapter DOIs failing in `ingest.py`; brittle
  `blockquote.py` matching on Unicode apostrophes, HTML-rendered table cells,
  and paraphrased "quotes".
- Confirmed `ingest.py` end-to-end on the BJET methodology corpus (35
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

**2026-05-14 second pass** (Windows hardening for Jodie's BJET project):

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
