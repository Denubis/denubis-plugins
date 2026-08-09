# Spec request: `GET /api/plus/resolve` — one live call to resolve a paper

> **STATUS as of 2026-08-03, read this before implementing anything below.**
> The spec's own prediction came true: the core fix shipped in the Python helper
> with no plugin change. `resolve.py` is now citekey-capable and fully live
> against BBT JSON-RPC, searching every supplied key and unioning the hits, with
> precision filtered client-side. The "Why now" paragraph immediately following
> describes a resolver that no longer exists.
>
> **What is still open is narrower than the whole document.** `--doi` is the one
> input that still routes through Crossref (`search_by_doi` →
> `crossref_first_author_family` → BBT surname search → DOI filter), because BBT
> `item.search` does not index the DOI field and stock `qmode=everything` matches
> the DOI string in PDF fulltext, returning attachments with `DOI: null` rather
> than the parent item. Server-side exact search on the DOI field is the live
> ask. Verify what the helper already derives about attachment paths before
> treating the second half of the ask as open too.
>
> Written 2026-06-17 against Zotero 9.0.4 + BBT. Re-verify that floor before
> implementing.

**For:** the `zotero-api-plus` plugin (`Zotero.Server.LocalAPI.*`).
**Why now:** the bibliography skill's current resolver keys on **DOI** and goes
through a fragile Crossref → author-surname → BBT `item.search` → DOI-filter
chain. It fails, repeatedly and recently, on whole classes of real papers — and
when it fails it reports a paper that *is in Zotero* as `NOT FOUND`.

**Scope of the ask (verified against live Zotero 9.0.4 + BBT — see floor below).**
The *core* fix the skill needs — resolve by **citekey / title+author+year instead
of DOI** — is shippable in the Python helper **today**, no plugin change: the stock
Local API already searches title/creator/year (`qmode=titleCreatorYear`) and
already returns the BBT `citationKey`, the `DOI` value, and author/year
(`meta.creatorSummary` / `meta.parsedDate`). This endpoint is the **narrow
enhancement** that stock genuinely *cannot* do — both verified empirically:

  (a) **search by the DOI *field*** (exact, server-side, no Crossref). Stock's
      `qmode=everything` matches the DOI string in PDF *fulltext* and returns the
      *attachments* (`DOI: null`), not the parent item; there is no DOI qmode.
  (b) **return the resolved on-disk attachment path + existence.** Stock item JSON
      carries no local path at all — only a `/items/<key>/file` download route.

So the endpoint is: one live call that does DOI-field search **and** bundles the
on-disk PDF path, removing the Crossref detour and the `item.export` +
`file = {…}` regex parse. One call, no `.bib` cache. It does **not** add citekey
resolution — stock already has that, and the helper should use it now.

## Grounding — real failures this fixes (use as acceptance fixtures)

All observed in production sessions, not hypotheticals:

| Case | DOI | What happened | Key that resolves it |
|---|---|---|---|
| Vehtari (BJET, 2026-05-12) | `10.1007/s11222-016-9696-4` (present, populated) | `vehtariPracticalBayesianModel2017` **is** in Zotero, DOI ingest reported `NOT FOUND` / `0 rendered` — the Crossref→surname→BBT pipeline failed | `citekey` (sure); `doi`-field also matches, since the item's DOI is populated |
| Collins & Lanza chapters (BJET) | `10.1002/9780470567333.ch7` | `NOT FOUND` — Wiley chapter DOIs return **empty `author`** from Crossref, so the surname step has nothing to query | `citekey` (and `doi` if the item carries it). **Not** author-surname. |
| Lombardo (Amanda, 2026-06-15) | `10.32614/RJ-2016-039` | item exists by citekey, `NOT FOUND` by DOI — **DOI drift**: the item's DOI field ≠ the `.bib` DOI | `citekey` / `author`+`year` **only** — `?doi=` returns `[]` *even with this endpoint* |

**Fixture caveat for the implementer:** test each row with the key named in the
last column, not by DOI blindly. **Lombardo by `?doi=` must legitimately return
`[]`** — that is correct behaviour, not a failure. And the one irreducible case:
when the **only input is a DOI** and that DOI has drifted from the item's field,
*no* query key resolves it without external metadata (Crossref title/author, or
the `.bib`'s citekey). This endpoint does **not** fix DOI-only input under drift;
the skill's answer there is to carry the citekey from the `.bib`, not the DOI.

Common thread: **every one of these resolves by citekey** (and most by a populated
`doi` field); the resolver must not key *solely* on a DOI run through Crossref.

## Verified floor (stock Local API + BBT, this box, 2026-06-17)

Reproduce before building — confirms what stock already does, so the endpoint
adds only the verified gap:

```bash
# (a) DOI-field search — stock CANNOT: matches the DOI in PDF fulltext, returns
#     ATTACHMENTS with DOI:null, not the parent item. No DOI qmode exists.
curl -sS "http://localhost:23119/api/users/0/items?q=10.32614/RJ-2016-039&qmode=everything&limit=3&format=json"

# title/creator/year search — stock CAN, and the hit already carries the citekey:
curl -sS "http://localhost:23119/api/users/0/items?q=Vehtari&qmode=titleCreatorYear&limit=3&format=json"
#   → data.citationKey = "vehtariPracticalBayesianModel2017"   (citekey: NOT a gap)
#   → data.DOI         = "10.1007/s11222-016-9696-4"           (DOI value present)
#   → meta.creatorSummary / meta.parsedDate                    (author+year present)
#   → NO local file path anywhere in the response              (the (b) gap)
```

Net floor: citekey, DOI *value*, author, year, title-search — all already
available. Missing: DOI-*field* search, and the resolved on-disk PDF path. That
pair is the whole endpoint.

## Contract

`GET /api/plus/resolve` — pure read, no writes (same shape as the existing
`libraries` / `selected-collection` / `open-pdf` GET endpoints, extending
`Zotero.Server.LocalAPI.Schema`, `supportedMethods = ["GET"]`).

### Query parameters (all optional; AND-combined when more than one given)

| Param | Meaning | Match |
|---|---|---|
| `citekey` | BBT citation key | exact |
| `doi` | DOI | exact, case-insensitive, against the item's **DOI field** (no Crossref) |
| `title` | title | normalized substring (case/whitespace-insensitive) |
| `author` | creator surname | exact surname, case-insensitive, any creator |
| `year` | publication year | exact, parsed from the item's `date` field |
| `groupID` / `libraryID` | scope | optional; **omitted → search all libraries** (My Library + every group) |

- At least one of `citekey/doi/title/author/year` is required.
- Multiple keys narrow (AND). This lets the helper try `citekey` first, then
  fall back to `author`+`year`+`title` for the DOI-drift / empty-author cases.

### Response `200 application/json`

Return **every** matching item across the searched libraries — do **not**
pre-pick one. The same citekey/DOI legitimately exists in My Library *and* a
group as separate items, only some with the PDF attached; the caller selects.

```json
{
  "query": {"citekey": "lombardo...", "doi": null, "title": null, "author": null, "year": null},
  "matches": [
    {
      "key": "WXYZ5678",
      "libraryID": 1,
      "groupID": null,
      "library": "My Library",
      "citekey": "lombardoVariantsSimpleCorrespondence2016",
      "DOI": "10.32614/RJ-2016-039",
      "title": "Variants of Simple Correspondence Analysis",
      "itemType": "journalArticle",
      "creators": [{"lastName": "Lombardo", "firstName": "R.", "creatorType": "author"}],
      "year": "2016",
      "dateAdded": "2026-06-10T04:12:00Z",
      "version": 1234,
      "attachments": [
        {
          "key": "ATT12345",
          "path": "/home/brian/Zotero/storage/ATT12345/paper.pdf",
          "contentType": "application/pdf",
          "linkMode": "imported_file",
          "exists": true
        }
      ]
    }
  ]
}
```

- `attachments[].path` is the **resolved absolute path** (`attachment.getFilePath()`),
  and `exists` is a **live filesystem check**. This replaces `item.export`
  (`Better BibLaTeX`) + the `file = {…}` regex parse (`bbt.parse_pdf_paths`)
  entirely — including the Windows drive-letter-colon parsing that helper carries.
- `matches: []` (still `200`) when nothing matched. This is the key signal that
  lets the caller distinguish **"endpoint ran, genuinely absent"** from
  **"endpoint not present"** (see probe).

### Probe / errors

- **Bare `GET /api/plus/resolve` with no params → `400`** with a one-line usage
  string. The caller uses `400`-present / `404`-absent to detect the endpoint
  (same probe trick `annotate.py` uses against `read-annotations`).
- Unknown `groupID` → `400` listing available libraries (match `add-item-by-id`).
- Malformed `year` → `400`.

## Implementation hints (Zotero internals)

- **DOI:** `Zotero.Search` with a `DOI` field condition, or iterate and compare
  `item.getField('DOI')` (normalize case). Do **not** use the fulltext index —
  that is exactly what BBT `item.search` lacks, and the bug we are routing around.
- **citekey:** stock already injects `data.citationKey` into the Local API item
  JSON, so reuse that path (`Zotero.BetterBibTeX.KeyManager`) rather than
  reimplementing. BBT is a hard precondition of this skill.
- **attachment path:** `item.getBestAttachments()` → `attachment.getFilePath()`;
  `exists` via Zotero's file API. Return *all* PDF attachments, not just one.
  This is the one fact stock does not expose and the main reason for the endpoint.
- **all-libraries scan:** `Zotero.Libraries.getAll()` when unscoped.
- **year:** parse from `item.getField('date')` (use `Zotero.Date` to extract the
  year robustly across date formats).
- **Library IDs — three different spaces, do not conflate.** Verified on this box:
  stock `/api/users/0/...` reports My Library as user id **305867**; **BBT**
  numbers My Library as **1** (what `item.export` needs); groups carry a separate
  **`groupID`** (what `add-item-by-id` needs). Return **BBT's `libraryID`** (1 for
  My Library) *and* `groupID` so both downstream consumers are served; do **not**
  surface the stock user-id. Scope params: omitted ⇒ all libraries; `groupID` or
  `libraryID` ⇒ that library only; if both are given, prefer the explicit
  `libraryID` and ignore `groupID` (or 400 — implementer's call, just define it).
- **Version-sensitive internals.** `KeyManager` and `attachment.getFilePath()` are
  internal APIs; confirm signatures against the running **Zotero 9.0.4 + current
  BBT** before relying on them — they drift between releases.

## What the skill side will do with this (not your concern, for context)

A thin Python helper (the `fetch.py` shape: pure core + httpx shell, unit-tested)
calls this endpoint as **primary**, with the current BBT `item.search`/`item.export`
+ `.bib` HTTP pull-export path as **fallback** when the endpoint is absent. It
adds the pipeline-state classification per match — *in Zotero? PDF on disk?
rendered under `papers/<citekey>/`?* — so one call answers "where is this paper in
the pipeline," including the not-fetched and not-rendered cases. None of that
needs to live in the plugin; the plugin just returns the structured facts above.

## Operational note

A new endpoint isn't live until the plugin is rebuilt and Zotero reloaded (the
`endpoint NOT yet live in running Zotero` / `No endpoint found` loop). The helper
probes and falls back, so the skill keeps working through the rebuild.
