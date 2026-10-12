"""Stock Zotero local API helpers: quicksearch and DOI-field search.

Shared by `resolve.py`, `ingest.py` and `annotate.py` so the per-library sweep,
pagination, child-dropping and exact-DOI rules live in ONE place. Duplicating
them is how the consumers drift, and every rule here exists because getting it
wrong silently reports a paper that IS in Zotero as absent.

Why the stock API and not Better BibTeX's JSON-RPC `item.search`:

  - Zotero 10 removed the `blockStart` quicksearch marker that BBT's
    `item.search` still emits, so every query errors with "Invalid condition
    'blockStart'" (BBT issue #3587; the call is still present in release 9.0.63
    and on master, checked 2026-09-02).
  - BBT `item.search` never indexed the DOI field (verified 2026-08-03 with a
    positive control) and indexed only the FIRST author surname.
  - Zotero's own `quicksearch-titleCreatorYear` expands each word over title,
    publicationTitle, shortTitle, court, year, citationKey and EVERY creator,
    and sets noChildren. Verified in `search.js` for Zotero 9.0.6 and 10.0.1;
    earlier versions are unverified.

Two modes are used:

  - `titleCreatorYear` (the default) for citekeys, authors, titles and free
    terms. Words are tokenised and ANDed server-side; precision is the caller's
    job (`matches_query` in resolve.py). Children are excluded server-side, and
    dropped again here defensively.
  - `fields` for DOIs: `field contains` over EVERY item data field, plus tags,
    notes, annotations and creators. It is the only mode that reaches the DOI
    field, it over-matches (a DOI prefix also hits the longer DOI), and it does
    not set noChildren, so the DOI path compares for equality and drops
    children itself.

`/api/users/0/` is My Library ALONE. Groups are swept explicitly.

Trash (0.19): Zotero's item listings and quicksearch exclude trashed items
unless `includeTrashed=1`; a direct key read returns them, and every envelope
carries `data.deleted` when the item is in the trash. The exact-citekey sweep
asks for the trash so a trashed paper is reported as such instead of being
reported as absent or, worse, as a live render; author, title, and DOI searches
keep Zotero's exclusion and the resolver says so. Verified live on Zotero 10.0.6
on 2026-10-12 against D7IV2YRB.

Do NOT reach for `qmode=everything`. It adds PDF fulltext, so a DOI query
returns hundreds of attachment hits with the parent below the first page.
Reading the first few results of that set is what recorded DOI-field search as
impossible for six weeks, and the capability was there the whole time.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))
# The write primitive carries zotero_auth's credentials; its pure core stays
# importable without httpx, like the rest of this module.
import zotero_auth

if TYPE_CHECKING:
    from collections.abc import Callable

LOCAL_API_BASE = "http://localhost:23119/api"

# Zotero's writeMultipleObjects accepts at most this many objects per POST.
_CREATE_BATCH_LIMIT = 50

# Zotero's item read API caps a page at 100.
_PAGE = 100

# Item types that are children of a paper, never a paper.
_CHILD_TYPES = frozenset({"attachment", "note", "annotation"})


class LibraryQueryError(RuntimeError):
    """One library's search request failed (transport or non-2xx status).

    The sweep records it against the library's URL and carries on, so the
    caller can tell "no item matched" from "part of the corpus was never
    searched". Raised by fetch_search_page in place of the transport's own
    exception so the sweep, and its tests, need no httpx.
    """


def item_citekey(item: dict) -> str:
    """The Better BibTeX citekey a stock local API envelope carries."""
    return ((item.get("data") or {}).get("citationKey") or "").strip()


def item_library(item: dict) -> str:
    """The human library name a stock local API envelope carries.

    This is the same name BBT's user.groups reports, so it is the join key
    between the two APIs; the envelope's numeric id is Zotero's user/group id,
    not the BBT library id.
    """
    return (item.get("library") or {}).get("name") or ""


def item_in_trash(item: dict) -> bool:
    """True when a stock envelope says the item is in Zotero's trash."""
    return bool((item.get("data") or {}).get("deleted"))


def library_base(library: dict) -> str:
    """The stock local API path prefix for a zotero-api-plus library record.

    `/users/0` is My Library; a group is addressed by its groupID, not by the
    libraryID that the write endpoints take (the two number spaces differ).
    """
    if library.get("type") == "user":
        return "/users/0"
    return f"/groups/{library['groupID']}"


def select_parent_items(items: list[dict]) -> list[dict]:
    """Keep the top-level items; drop attachment, note and annotation children.

    A child carries no citekey, title or creators of its own and is never a
    resolved paper. titleCreatorYear excludes them server-side; fields does not.
    """
    return [
        i for i in items if (i.get("data") or {}).get("itemType") not in _CHILD_TYPES
    ]


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
    for item in select_parent_items(items):
        data = item.get("data") or {}
        if (data.get("DOI") or "").strip().lower() == want:
            matches.append(item)
    return matches


def doi_citekeys(items: list[dict], doi: str) -> list[str]:
    """Distinct citekeys of the exact DOI matches, in first-seen order.

    One citekey legitimately appears once per library holding a copy; the
    duplicates would only cost repeated work downstream.
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


def _fetch_all_pages(url: str, params: dict, *, timeout: float) -> list[dict]:
    """Follow Zotero's `start`/`limit` pagination to the end of a listing.

    Reading only the first page is the error this module's docstring describes,
    so pages are followed until one comes back short. A transport failure or a
    non-2xx status is raised as LibraryQueryError.
    """
    import httpx  # noqa: PLC0415

    start = 0
    items: list[dict] = []
    while True:
        try:
            r = httpx.get(
                url,
                params={**params, "limit": _PAGE, "start": start, "format": "json"},
                timeout=timeout,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise LibraryQueryError(str(e)) from e
        batch = r.json()
        items.extend(batch)
        if len(batch) < _PAGE:
            return items
        start += _PAGE


def fetch_search_page(
    url: str,
    query: str,
    *,
    qmode: str,
    include_trashed: bool = False,
    timeout: float = 30.0,
) -> list[dict]:
    """Every item matching `query` at `url` in `qmode`, following pagination.

    `include_trashed` adds `includeTrashed=1`, which is the only way a
    quicksearch returns a trashed item.
    """
    params: dict = {"q": query, "qmode": qmode}
    if include_trashed:
        params["includeTrashed"] = 1
    return _fetch_all_pages(url, params, timeout=timeout)


def get_collection_items(
    library: dict,
    collection_key: str,
    *,
    include_trashed: bool = True,
    timeout: float = 30.0,
) -> list[dict]:
    """Every item of one collection, children included, via the stock API.

    Lists `/collections/<key>/items` (not `/items/top`) so attachments and
    notes arrive beside their parents and can be grouped by summarise_collection;
    the trash is included by default so a listing can MARK trashed rows rather
    than silently omit them. Paginated to the end. Raises LibraryQueryError.
    """
    url = f"{LOCAL_API_BASE}{library_base(library)}/collections/{collection_key}/items"
    params: dict = {}
    if include_trashed:
        params["includeTrashed"] = 1
    return _fetch_all_pages(url, params, timeout=timeout)


def summarise_collection(items: list[dict]) -> list[dict]:
    """Reduce a collection listing to one row per parent item, attachments
    grouped beneath, with the trash state of each. Pure; listing order kept.

    A child whose parent is not in the listing is dropped: it is not a member
    of the collection in its own right.
    """
    rows: list[dict] = []
    by_key: dict[str, dict] = {}
    for item in select_parent_items(items):
        data = item.get("data") or {}
        row = {
            "key": data.get("key") or item.get("key") or "",
            "citekey": item_citekey(item),
            "title": data.get("title") or "",
            "itemType": data.get("itemType") or "",
            "in_trash": item_in_trash(item),
            "attachments": [],
        }
        rows.append(row)
        by_key[row["key"]] = row
    for item in items:
        data = item.get("data") or {}
        if data.get("itemType") != "attachment":
            continue
        parent = by_key.get(data.get("parentItem") or "")
        if parent is None:
            continue
        # A linked-URL attachment has no filename; its title is the next best
        # name. Observed live on J4CUUEHW (two such attachments), 2026-10-12.
        name = data.get("filename") or data.get("title") or "(unnamed attachment)"
        parent["attachments"].append(
            {"filename": name, "in_trash": item_in_trash(item)}
        )
    return rows


@dataclass(frozen=True)
class LibrarySearch:
    """Matches across every library, and the libraries that failed.

    items: the matching PARENT envelopes in first-seen order, one per library
      copy. Children are already dropped; the DOI sweep has also applied its
      equality rule, so every element is a candidate paper.
    failed_libraries: '<url>: <error>' for each library whose query raised.

    Both fields are needed to answer honestly. An empty `items` means "no item
    matched" ONLY when `failed_libraries` is empty; otherwise the search never
    saw part of the corpus and the result is inconclusive. Returning the count
    alone (or printing it and discarding it) leaves the caller unable to tell
    those two apart, which is how a present paper gets reported as absent.
    """

    items: tuple[dict, ...]
    failed_libraries: tuple[str, ...]


def _sweep(
    query: str,
    *,
    qmode: str,
    keep: Callable[[list[dict]], list[dict]],
    include_trashed: bool = False,
) -> LibrarySearch:
    """Run one query against every library, keeping what `keep` selects."""
    items: list[dict] = []
    failed: list[str] = []
    for url in library_item_urls():
        try:
            page = fetch_search_page(
                url, query, qmode=qmode, include_trashed=include_trashed
            )
        except LibraryQueryError as e:
            failed.append(f"{url}: {e}")
            continue
        items.extend(keep(page))
    return LibrarySearch(items=tuple(items), failed_libraries=tuple(failed))


def search_items(
    query: str, *, qmode: str = "titleCreatorYear", include_trashed: bool = False
) -> LibrarySearch:
    """Every parent item matching `query` in `qmode`, across all libraries.

    This is the token search that replaced BBT `item.search`. The server ANDs
    the query's words over title, creators, year and citekey, so a citekey, a
    surname (first author or not), a title fragment or a free term all work; an
    exact object key is matched too. The caller applies its own precision
    filter to the envelopes, which carry title, creators, date, DOI, citekey,
    collections, the library's human name, and `deleted` (item_in_trash).
    `include_trashed` asks Zotero for trashed items too.

    A failure to list the groups still raises, per library_item_urls.
    """
    return _sweep(
        query, qmode=qmode, keep=select_parent_items, include_trashed=include_trashed
    )


def search_doi_items(doi: str) -> LibrarySearch:
    """Every item whose DOI field is exactly `doi`, across all libraries.

    Returns the full stock envelopes rather than only their citekeys: the
    envelope already carries everything a Paper needs, so no second lookup is
    required to report the copies this search has proved exist.

    A failure to list the groups still raises, per library_item_urls.
    """
    return _sweep(doi, qmode="fields", keep=lambda page: select_doi_matches(page, doi))


def warn_unsearched_libraries(found: LibrarySearch) -> None:
    """Report on stderr any library a sweep could not search.

    An empty result from a library that was never successfully searched is
    indistinguishable from a genuine absence to a caller that only sees the
    items, so the warning is the signal that a no-match is inconclusive.
    """
    if not found.failed_libraries:
        return
    failed = len(found.failed_libraries)
    plural = "library" if failed == 1 else "libraries"
    print(
        f"  warning: {failed} {plural} could not be searched, so a no-match "
        "below is inconclusive rather than a confirmed absence.",
        file=sys.stderr,
        flush=True,
    )


def search_doi_field(doi: str) -> list[str]:
    """Distinct citekeys whose DOI field is exactly `doi`, across all libraries.

    A library whose query fails is reported on stderr; this signature cannot
    hand that distinction back, so a caller that must branch on it uses
    search_doi_items and reports the failures itself.
    """
    found = search_doi_items(doi)
    warn_unsearched_libraries(found)
    return doi_citekeys(found.items, doi)


# --- Stock write primitive (Zotero 10, ADR 0028) -------------------------------
#
# Zotero 10's local API writes items and collections behind the server-ID and
# API-key gate zotero_auth already satisfies. Read in the installed 10.0.6
# server_localAPI.js (2026-10-12): PATCH /items/<key> and /collections/<key>
# merge the body over the object's JSON, require If-Unmodified-Since-Version,
# answer 412 on a mismatch and 204 with Last-Modified-Version on success; POST
# /items and /collections take up to 50 objects and return {successful,
# unchanged, failed}. DELETE erases permanently and is never sent (delete
# means trash: PATCH {"deleted": true}).
#
# Stock 412 collides with zotero_auth's server-ID-mismatch 412, so this
# primitive sends its own request rather than going through zotero_auth.post:
# a 412 whose body names the server ID is `refused`; any other 412 is a
# `conflict`, reported with Zotero's current object and never retried.

ObjectKind = Literal["items", "collections"]
WriteStatus = Literal["accepted", "conflict", "refused", "failed"]


class StockWriteUnavailable(RuntimeError):
    """This Zotero has no server ID, so it has no stock write routes (7-9)."""


@dataclass(frozen=True)
class WriteResult:
    """What Zotero said to one PATCH.

    accepted: 204; `version` is Last-Modified-Version.
    conflict: 412 on If-Unmodified-Since-Version; `current` is the object as
      Zotero now holds it. Never retried.
    refused: a credential or permission answer (401 after one retry, 403,
      412 naming the server ID, 428).
    failed: anything else, with Zotero's body.
    """

    status: WriteStatus
    version: int | None
    body: str
    current: dict | None = None


def require_stock_writes() -> None:
    """Refuse, before any request, on a Zotero without a server ID."""
    if not zotero_auth.server_id():
        raise StockWriteUnavailable(
            "stock writes need Zotero 10: this Zotero sends no Zotero-Server-ID "
            "header, so it has no local-API write routes."
        )


def _http_request(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    json=None,
    params: dict | None = None,
    timeout: float = 30.0,
):
    """The one httpx seam every read and write of this primitive goes through."""
    import httpx  # noqa: PLC0415

    return httpx.request(
        method, url, headers=headers, json=json, params=params, timeout=timeout
    )


def _object_url(library: dict, kind: ObjectKind, key: str | None = None) -> str:
    url = f"{LOCAL_API_BASE}{library_base(library)}/{kind}"
    return f"{url}/{key}" if key else url


def read_object(
    library: dict,
    kind: ObjectKind,
    key: str,
    *,
    include_trashed: bool = True,
    timeout: float = 30.0,
) -> dict:
    """GET one item or collection envelope; trashed objects included by default.

    Raises LibraryQueryError on a non-2xx status.
    """
    params: dict = {"format": "json"}
    if include_trashed:
        params["includeTrashed"] = 1
    reply = _http_request(
        "GET", _object_url(library, kind, key), params=params, timeout=timeout
    )
    if not 200 <= reply.status_code < 300:
        raise LibraryQueryError(
            f"GET {kind}/{key}: HTTP {reply.status_code}: {reply.text.strip()[:200]}"
        )
    return reply.json()


def get_item_children(library: dict, key: str, *, timeout: float = 30.0) -> list[dict]:
    """`/items/<key>/children` with the trash included; [] when it has none."""
    url = f"{_object_url(library, 'items', key)}/children"
    reply = _http_request(
        "GET", url, params={"format": "json", "includeTrashed": 1}, timeout=timeout
    )
    if not 200 <= reply.status_code < 300:
        raise LibraryQueryError(f"GET items/{key}/children: HTTP {reply.status_code}")
    body = reply.json()
    return body if isinstance(body, list) else []


def get_subcollections(library: dict, key: str, *, timeout: float = 30.0) -> list[dict]:
    """`/collections/<key>/collections`: the LIVE direct children only.

    The installed local API builds this listing without `includeTrashed`
    (server_localAPI.js:993-995, read 2026-10-12), so a trashed child never
    appears here; only a direct key read returns it. Callers that need
    trashed descendants must already know their keys.
    """
    url = f"{_object_url(library, 'collections', key)}/collections"
    reply = _http_request("GET", url, params={"format": "json"}, timeout=timeout)
    if not 200 <= reply.status_code < 300:
        raise LibraryQueryError(
            f"GET collections/{key}/collections: HTTP {reply.status_code}"
        )
    body = reply.json()
    return body if isinstance(body, list) else []


def classify_write_reply(
    status: int, version_header: str | None, body: str, *, library_name: str
) -> WriteResult:
    """Map one PATCH reply to a WriteResult (pure; `current` is filled by the
    shell on a conflict)."""
    text = (body or "").strip()
    if status == 204:
        version = None
        if version_header and version_header.strip().isdigit():
            version = int(version_header.strip())
        return WriteResult("accepted", version, text)
    if status == 412 and "zotero-server-id" not in text.lower():
        return WriteResult("conflict", None, text)
    refusals = {
        412: f"server id: {text}",
        401: f"HTTP 401: {text}",
        403: f"HTTP 403: {library_name!r} is not editable by this Zotero user ({text})",
        428: f"HTTP 428: {text}",
    }
    if status in refusals:
        return WriteResult("refused", None, refusals[status])
    return WriteResult("failed", None, f"HTTP {status}: {text}")


def write_object(
    library: dict,
    kind: ObjectKind,
    key: str,
    body: dict,
    expected_version: int,
    *,
    timeout: float = 30.0,
) -> WriteResult:
    """PATCH one item or collection, protected by `expected_version`.

    Carries zotero_auth's credentials and If-Unmodified-Since-Version. A 401
    discards the stored key and retries once (as zotero_auth.post does); a 412
    is classified by classify_write_reply and a conflict is returned with the
    object Zotero now holds. Nothing is retried after that.
    """
    url = _object_url(library, kind, key)

    def send() -> WriteResult:
        headers = {
            **zotero_auth.credentials(),
            "If-Unmodified-Since-Version": str(expected_version),
        }
        reply = _http_request("PATCH", url, headers=headers, json=body, timeout=timeout)
        return classify_write_reply(
            reply.status_code,
            reply.headers.get("Last-Modified-Version"),
            reply.text,
            library_name=library.get("name", "?"),
        ), reply.status_code

    result, status = send()
    if status == 401:
        stale = zotero_auth.server_id()
        if stale:
            zotero_auth.forget_key(stale)
        result, _status = send()
    if result.status == "conflict":
        try:
            current = read_object(library, kind, key, timeout=timeout)
        except LibraryQueryError as error:
            current = {"error": str(error)}
        result = WriteResult("conflict", None, result.body, current)
    return result


def create_objects(
    library: dict, kind: ObjectKind, bodies: list[dict], *, timeout: float = 30.0
) -> dict:
    """POST up to 50 new items or collections; return Zotero's
    `{successful, unchanged, failed}` report.

    A 401 discards the stored key and retries once. Any other non-200 raises
    LibraryQueryError with the status and body: nothing about a refused POST
    is a partial success.
    """
    if len(bodies) > _CREATE_BATCH_LIMIT:
        raise ValueError(
            f"Zotero accepts at most {_CREATE_BATCH_LIMIT} objects per POST, "
            f"got {len(bodies)}"
        )
    url = _object_url(library, kind)
    reply = _http_request(
        "POST", url, headers=zotero_auth.credentials(), json=bodies, timeout=timeout
    )
    if reply.status_code == 401:
        stale = zotero_auth.server_id()
        if stale:
            zotero_auth.forget_key(stale)
        reply = _http_request(
            "POST",
            url,
            headers=zotero_auth.credentials(),
            json=bodies,
            timeout=timeout,
        )
    if reply.status_code != 200:
        raise LibraryQueryError(
            f"POST {kind}: HTTP {reply.status_code}: {reply.text.strip()[:300]}"
        )
    return reply.json()
