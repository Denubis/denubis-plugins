"""Stock Zotero local API helpers — DOI-field search.

Shared by `resolve.py` and `ingest.py` so the exact-match, drop-children,
per-library and pagination rules live in ONE place. Duplicating them is how the
two consumers drift, and every rule here exists because getting it wrong
silently reports a paper that IS in Zotero as absent.

Why this is not in `bbt.py`: BBT `item.search` does **not** index the DOI field.
Re-verified against Zotero 9.0.6 + BBT on 2026-08-03 with a positive control —
searching the first author's surname returns hits that carry the DOI in their
own output, while searching that same DOI string returns zero. The stock local
API is a different server on the same port, and it *can* search the field.

The mode is `qmode=fields`, which Zotero expands (see `search.js`, condition
`quicksearch-fields`) to a `field contains` condition over EVERY item data
field, plus tags, notes, annotations and creators. Three consequences are
handled here rather than server-side:

  1. `contains` over-matches, so a query for a DOI prefix also returns items
     whose DOI merely starts with it. Comparison is therefore equality.
  2. The mode does not set `noChildren` (unlike `quicksearch-titleCreatorYear`),
     so attachment children arrive beside their parents. A child carries no DOI
     and is never a resolved paper.
  3. `/api/users/0/` is My Library ALONE. Groups are swept explicitly.

Do NOT reach for `qmode=everything` here. It adds PDF fulltext, so a DOI query
returns hundreds of attachment hits with the parent below the first page.
Reading the first few results of that set is what recorded DOI-field search as
impossible for six weeks, and the capability was there the whole time.
"""

from __future__ import annotations

import sys

LOCAL_API_BASE = "http://localhost:23119/api"

# Zotero's item read API caps a page at 100.
_PAGE = 100


def select_doi_matches(items: list[dict], doi: str) -> list[dict]:
    """Keep the parent items whose DOI field equals `doi`, case-insensitively.

    Input is stock local API item envelopes (fields under `data`). Attachment
    children are dropped, and an empty query matches nothing so a blank DOI
    cannot sweep up every item that also has no DOI.
    """
    want = doi.strip().lower()
    if not want:
        return []
    matches = []
    for item in items:
        data = item.get("data") or {}
        if data.get("itemType") == "attachment":
            continue
        if (data.get("DOI") or "").strip().lower() == want:
            matches.append(item)
    return matches


def doi_citekeys(items: list[dict], doi: str) -> list[str]:
    """Distinct citekeys of the exact DOI matches, in first-seen order.

    One citekey legitimately appears once per library holding a copy, and BBT
    resolves a citekey across every library at once, so the duplicates would
    only cost repeated queries.
    """
    seen: set[str] = set()
    citekeys: list[str] = []
    for item in select_doi_matches(items, doi):
        citekey = ((item.get("data") or {}).get("citationKey") or "").strip()
        if citekey and citekey not in seen:
            seen.add(citekey)
            citekeys.append(citekey)
    return citekeys


def library_item_urls(timeout: float = 30.0) -> list[str]:
    """Item-search URLs for every library the stock local API exposes.

    A failure to list the groups is allowed to raise. Searching My Library
    alone and calling that a complete answer is the failure this path exists to
    remove, so under-searching silently is worse than stopping.
    """
    import httpx  # noqa: PLC0415

    r = httpx.get(
        f"{LOCAL_API_BASE}/users/0/groups", params={"format": "json"}, timeout=timeout
    )
    r.raise_for_status()
    return [f"{LOCAL_API_BASE}/users/0/items"] + [
        f"{LOCAL_API_BASE}/groups/{g['id']}/items" for g in r.json()
    ]


def fetch_doi_page(url: str, doi: str, timeout: float = 30.0) -> list[dict]:
    """Every item matching `doi` at `url`, following pagination to the end.

    Reading only the first page is the error this module's docstring describes,
    so pages are followed until one comes back short.
    """
    import httpx  # noqa: PLC0415

    start = 0
    items: list[dict] = []
    while True:
        r = httpx.get(
            url,
            params={
                "q": doi,
                "qmode": "fields",
                "limit": _PAGE,
                "start": start,
                "format": "json",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        batch = r.json()
        items.extend(batch)
        if len(batch) < _PAGE:
            return items
        start += _PAGE


def search_doi_field(doi: str) -> list[str]:
    """Distinct citekeys whose DOI field is exactly `doi`, across all libraries.

    A library whose query fails is counted and reported on stderr. An empty
    result from a library that was never successfully searched is
    indistinguishable from a genuine absence.
    """
    import httpx  # noqa: PLC0415

    citekeys: list[str] = []
    seen: set[str] = set()
    failed = 0
    for url in library_item_urls():
        try:
            items = fetch_doi_page(url, doi)
        except httpx.HTTPError:
            failed += 1
            continue
        for citekey in doi_citekeys(items, doi):
            if citekey not in seen:
                seen.add(citekey)
                citekeys.append(citekey)
    if failed:
        plural = "library" if failed == 1 else "libraries"
        print(
            f"  warning: {failed} {plural} could not be searched, so a no-match "
            "below is inconclusive rather than a confirmed absence.",
            file=sys.stderr,
            flush=True,
        )
    return citekeys
