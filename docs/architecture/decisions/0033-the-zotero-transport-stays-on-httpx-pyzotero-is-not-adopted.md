# ADR 0033 — The Zotero local-API transport stays on httpx; pyzotero is not adopted

**Status:** Accepted (2026-10-22). Closes ticket L3 of the lint baseline paydown. Spike:
`docs/audits/2026-10-22-pyzotero-local-mode-spike.md`.

## Authority evidence

Original human messages in session `f30676a7-e08c-43cb-86f8-9dc704202a5a`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/`):

- `ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:bc93324d-b038-4724-9415-932203b97ff7`
  (2026-10-22T07:12Z), after the spike's "do not swap" recommendation and the
  proposal to add httpx to the dev group: "yep, add it to dev group".

Resolver:

```sh
cc-search-chats resolve ccchat:v1:claude:f30676a7-e08c-43cb-86f8-9dc704202a5a:uuid:bc93324d-b038-4724-9415-932203b97ff7 --reference-only --json
```

## Context

Brian asked whether the bibliography skill's hand-written Zotero local-API transport
(`zotero_local_api.py`, `zotero_auth.py`) should be replaced by pyzotero. An Opus xhigh
spike probed pyzotero 1.15.2 against the live Zotero 10.0.6 and found that it reproduces
every read, trash and version-conflict behaviour the plugin relies on. It also found
that every pyzotero release with local writes (1.14.0 to 1.16.0 and `main`) pins
`bibtexparser<2.0.0`, while `resolve.py` and `register_export.py` require bibtexparser 2
and import the transport module; uv refuses to resolve them together under PEP 723. A
swap would remove about 21 of 207 transport lines, keep all of `zotero_auth.py` for the
zotero-api-plus writers, keep raw httpx for collection PATCHes, and add nine packages.

## Decision

1. The transport stays as written, on httpx. pyzotero is not adopted, in whole or part.
2. httpx joins the root dev group so ty checks the transport's call sites. The scripts
   keep httpx in their PEP 723 dependency lists; the dev-group entry is for the type
   checker, not a runtime change.
3. Revisit only if pyzotero lifts its bibtexparser pin.

## Consequences

- The 19 `unresolved-import` diagnostics for httpx become real type checks.
- The plugin keeps owning the observed Zotero behaviours its docstrings record
  (noChildren, DOI field search, trash semantics); nothing delegates them to a library.
- `copy_item.py`'s single-page DOI search, noted by the spike, is a separate defect and
  is not addressed here.
