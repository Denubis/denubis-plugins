---
name: using-bibliography
description: Use for Zotero resolution, rendering, quote verification, annotations, item copying or repair, bib refresh, literature notes, and academic plugin install or migration errors.
---

# Using Bibliography

Use Zotero as the bibliographic source of truth and
`~/zettelkasten/papers/<citekey>/` as the rendered-paper cache. Resolve every
paper through the bundled resolver; never invent a citekey, infer absence from
one failed search, or reimplement the render pipeline.

The installed plugin is `denubis-academic@denubis-plugins`. The callable skill
is `/denubis-academic:using-bibliography`. `denubis-bibliography` is the retired
plugin name; `denubis-bib` is not a valid marketplace or skill name.

## Read the relevant procedure

| Task | Read before acting |
|---|---|
| Install, upgrade, migrate a retired name, or diagnose plugin loading | [Setup and migration](references/setup-and-migration.md) |
| Resolve, batch-ingest, render, or inspect render state | [Resolve and render](references/resolve-and-render.md) |
| Read papers in parallel, extract quotations, or verify exact wording | [Reading and quoting](references/reading-and-quoting.md) |
| Fetch, copy, repair, or annotate Zotero items | [Zotero writes](references/zotero-writes.md) |
| Create literature/permanent notes or refresh a project bibliography | [Notes and bibliographies](references/notes-and-bibliographies.md) |
| Diagnose failures, platform differences, or exit codes | [Troubleshooting](references/troubleshooting.md) |

Do not preload every reference. Read only the procedure that owns the requested
operation, then return here for the shared safety rules.

## Installed paths

Claude Code copies installed plugins into its cache. Commands must therefore be
anchored to the plugin root exposed by Claude, never to a source checkout or the
caller's working directory:

```bash
BIB="${CLAUDE_PLUGIN_ROOT}/skills/using-bibliography"
uv run "$BIB/resolve.py" --help
```

When a skill subprocess is the only context available, `${CLAUDE_SKILL_DIR}` is
this skill directory and is also safe. Prefer `${CLAUDE_PLUGIN_ROOT}` in shared
instructions because it makes the plugin boundary explicit.

## Preconditions

Before any bibliography operation:

1. Read the project `AGENTS.md`, `CLAUDE.md`, and named `.notes/` files. The
   project may tighten write or note conventions.
2. Confirm Zotero is running. Better BibTeX (BBT) is required for citekey and
   library resolution.
3. Confirm `~/.config/denubis-academic-research/config.toml` exists and its
   `zettelkasten_root` exists. Do not silently create either.
4. Use Python 3.14+ and `uv`. The resolver declares Python 3.14 in its inline
   metadata. Rendering dependencies are acquired from the script metadata;
   never override the configured package or model caches.
5. Treat `zotero-api-plus` as an optional, capability-probed extension. Pure
   resolution and rendering do not require it; Zotero writes and forced BBT
   refreshes do.

## Front door

Start every paper lookup with `resolve.py`:

```bash
BIB="${CLAUDE_PLUGIN_ROOT}/skills/using-bibliography"
uv run "$BIB/resolve.py" <known-citekey>
uv run "$BIB/resolve.py" --author Vehtari --year 2017
uv run "$BIB/resolve.py" --title "scoping studies"
uv run "$BIB/resolve.py" --doi 10.1007/s13347-024-00760-w
```

A bare DOI is classified as a DOI; a citekey-shaped value is classified as a
citekey. Prefer an exact citekey once the resolver has returned it. BBT search
is first-author-oriented and can miss co-author or multi-token searches, so a
no-match is not proof that Zotero lacks the paper. Retry with the first author's
surname or one distinctive title token before classifying it absent.

Interpret exit status and state explicitly:

| Result | Meaning | Next action |
|---|---|---|
| exit `0`; `rendered` | Exact item resolved and render is ready | Verify `full.md` and `meta.json` exist |
| exit `0`; `ready-to-render` | Attachment exists but rendering was suppressed | Render through the resolver/cascade |
| exit `2`; near matches | Supplied citekey was not exact | Re-run with the returned real citekey |
| `no-pdf` | Item exists without a usable attachment | Ask the user to attach it or consider confirmed fetch |
| `pdf-unknown` | Attachment truth could not be established | Diagnose; never report `no-pdf` |
| `needs-ocr-escalation` | Normal cascade could not produce usable text | Ask before optional GPU OCR |
| exit `1`; no match/error | Search failed or returned no exact item | Follow the bounded negative-result checks |

After a claimed render, positively verify the files:

```bash
test -s "<zettelkasten-root>/papers/<citekey>/full.md"
test -s "<zettelkasten-root>/papers/<citekey>/meta.json"
```

## Source-fidelity rule

`meta.json` decides what a quotation claim can mean:

- With `"ocr": false`, rendered page Markdown is the controlled reading text.
  Copy exact quotations from the matching `pages/NNN.md` and retain its physical
  page number.
- With `"ocr": true`, rendered Markdown is a locator, not authoritative exact
  wording. It may support a paraphrase or a candidate quotation, but the exact
  quotation must be visually checked against the source PDF before it is called
  verified.
- `blockquote.py` proves that a string occurs in rendered Markdown. It does not
  independently prove an OCR transcription against the PDF.

Never fabricate wording after `NO MATCH`. Mark it unverified and surface the
gap.

## Write boundary

Read-only operations may run after preconditions pass. The following operations
change user-owned state and require the procedure's preview and confirmation:

| Operation | Preview | Write gate |
|---|---|---|
| Fetch missing paper | `fetch.py` without `--fetch` | Explicit confirmation, then `--fetch` |
| Copy item/library attachment | `copy_item.py` without `--copy` | Explicit confirmation, then `--copy` |
| Repair metadata | `update_item.py` without `--apply` | Show diff and receive approval, then `--apply` |
| Add PDF annotation | `annotate.py --dry-run` | Explicit instruction to annotate; then omit `--dry-run` |
| Create zettelkasten/project notes | Draft path and content | Follow project rules and obtain any required confirmation |
| Create config or zettelkasten layout | Explain exact paths | User creates them or explicitly authorises creation |

Never treat a request to ingest, read, or cite papers as consent to add items to
Zotero. Never hand-edit a BBT-generated bibliography.

## Completion evidence

Report only evidence appropriate to the operation:

- resolution: exact returned citekey, library, attachment state, and exit code;
- render: non-empty `full.md`, `pages/`, and `meta.json`, including renderer and
  OCR flag;
- quote: page-keyed text match plus PDF visual verification when OCR was used;
- Zotero write: approved preview, endpoint result, and post-write read-back;
- bib refresh: the registered auto-export ran and the exact citekey parsed from
  the resulting well-formed bibliography;
- install/migration: current marketplace entry, installed plugin name/version,
  and successful `/denubis-academic:using-bibliography` invocation after restart.
