# Notes and bibliographies

Project rules own note locations and write permissions. Inspect `AGENTS.md`,
`CLAUDE.md`, and named `.notes/` files before proposing a write.

```bash
BIB="${CLAUDE_PLUGIN_ROOT}/skills/using-bibliography"
```

## Literature notes

The default project location is `notes/literature/<citekey>.md`: one source per
file, named with the exact Zotero citekey. Do not put literature notes in the
central `permanent/` directory.

A minimal draft is:

```markdown
---
citekey: exactZoteroCitekey2026
title: Paper title
authors: Family; Family
year: 2026
doi: 10.x/example
source: zotero
rendered: ~/zettelkasten/papers/exactZoteroCitekey2026/
ai-generated: true
verified-by: null
---

# Paper title

## TL;DR

## Key claims

## Verified quotes

## Questions, critique, and connections

## Linked permanent notes
```

Use `ai-generated: true` for agent-written prose and leave `verified-by: null`
until a human actually verifies it. Preserve disagreement and uncertainty; a
literature note is not a licence to smooth the paper into a stronger claim.

Generate quotation blocks from rendered pages:

```bash
uv run "$BIB/blockquote.py" \
  "<zettelkasten-root>/papers/<citekey>/pages" \
  "<citekey>" "<verbatim substring>"
```

For a clean text-layer render, retain the emitted physical page and exact text.
For `meta.json` with `ocr: true`, label the output as a candidate and visually
check it against the source PDF before placing it under “Verified quotes.”

## Permanent notes

Permanent notes are atomic ideas in the central zettelkasten, usually under
`~/zettelkasten/permanent/`. They are user intellectual property. Draft them only
when requested, and follow the zettelkasten's own instructions. Link back to the
project literature note and cite the source with Pandoc syntax such as
`[@exactZoteroCitekey2026, p. 7]`.

Do not silently invent a central bibliography builder. The plugin does not yet
construct `~/zettelkasten/references.bib` from permanent-note citations.

## Bootstrap a project bibliography

If a project has no registered bibliography or literature-note layout, stop and
show the user the proposed setup. Do not silently choose a Zotero collection or
create project directories.

The supported Better BibTeX setup is:

1. In Zotero, right-click the project collection and choose **Export
   Collection…**.
2. Choose **Better BibLaTeX**.
3. Enable **Keep updated** and disable attachment/note export.
4. Save to the project's intended absolute `references.bib` path.
5. Configure BBT to omit `file` so local Zotero storage paths do not enter Git.
6. Confirm the automatic export trigger is **On change**.
7. With user approval, create the project's `notes/literature/` and any local
   structure directory its instructions require.

Read the bibliography path from project configuration or document metadata.
Never guess that it is `references.bib` merely because that name is common.

## Force and verify a BBT refresh

Requires `zotero-api-plus` 0.4.0+ and an already registered **Keep updated** BBT
export for the exact file. Use the resolver's one sanctioned path:

```bash
uv run "$BIB/resolve.py" --citekey <exact-key> \
  --bib /absolute/path/read/from/project/config.bib
```

The helper triggers BBT's registered auto-export and then positively verifies
that the resulting file parses as BibLaTeX and contains the exact citekey. A
successful HTTP response alone is not success because BBT can swallow an export
failure.

If the helper reports `no-autoexport`, fix the Zotero registration for that
exact path. Do not replace it with either of these unsafe shortcuts:

- pulling a whole library export over `/better-bibtex/library`, which changes
  the bibliography's collection scope;
- hand-splicing an `item.export` fragment, which can leave malformed or stale
  bytes.

Never hand-edit a BBT-managed file. After any metadata repair, use the registered
refresh and verify the exact citekey again.

## Pandoc projects

Use the bibliographies actually declared by the project. If a document needs
both project and central sources, pass both explicitly to Pandoc or list both in
document metadata. Keep the citekey identical across rendered paper, note, and
bibliography; do not create local aliases to make a citation compile.
