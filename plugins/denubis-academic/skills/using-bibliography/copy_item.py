#!/usr/bin/env python3
"""Copy an item, with its attachments, between Zotero libraries via the
zotero-api-plus local API (POST /api/plus/copy-item).

Zotero exposes no headless cross-library copy: the capability lives only in
CollectionTree._copyItem(), which needs a UI targetTreeRow. zotero-api-plus
wraps the underlying primitives; this script is the consumer, so nobody has to
hand-roll the HTTP call.

The brittle step is the same one fetch.py exists to remove: turning a human
library name into the numeric id the endpoint needs. Note that copy-item takes a
**targetLibraryID** (a Zotero libraryID), NOT the groupID that add-item-by-id and
create-collection take. They are different number spaces, and mixing them is the
mistake this module's resolution exists to prevent.

Usage (find the source item's key — read-only):
    uv run copy_item.py --find "Game Theoretic"

Usage (resolve + preview only, NO write):
    uv run copy_item.py --key ABCD1234 --to "My Library"

Usage (perform the copy, gated behind --copy):
    uv run copy_item.py --key ABCD1234 --from "2025-MQ-Teaching-the-Unknown" \
        --to "My Library" --copy

Source selection:
  --key         the Zotero item key to copy (see --find).
  --from        source library: name, numeric groupID, or "My Library".
                Omit to let the endpoint sweep My Library then each group.

Target selection:
  --to              target library: name, numeric groupID, or "My Library".
  --to-collection   collection name within the target library. The endpoint
                    NEVER creates a collection; an unknown name is an error.
  --to-collection-key   explicit key (bypasses name resolution when ambiguous).

The copy is idempotent by design: if the target already holds a linked
counterpart it is returned rather than duplicated, and any attachment it lacks
is topped up. Re-running after a partial copy repairs it.

Endpoint contract read from ~/people/Brian/zotero-api-plus/src/addon.ts and
utils/copy-item.ts, not transcribed from documentation.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

# httpx is imported lazily inside the shell functions so the functional core
# stays importable without the PEP 723 deps — the unit tests load this module
# and exercise the pure functions directly.

PLUS_PROBE = "http://localhost:23119/api/plus"
LIBRARIES_ENDPOINT = "http://localhost:23119/api/plus/libraries"
COPY_ITEM_ENDPOINT = "http://localhost:23119/api/plus/copy-item"
STOCK_API = "http://localhost:23119/api"

# Attachment statuses the endpoint reports, per utils/copy-item.ts. Only
# "copied" and "imported" mean bytes landed in the target.
SUCCESS_STATUSES = ("copied", "imported")


# --- Functional core (pure, unit-tested) ------------------------------------


class ResolutionError(Exception):
    """A library or collection name could not be resolved unambiguously."""


class CopyError(Exception):
    """copy-item returned an error or an unparseable response."""


@dataclass(frozen=True)
class CopyTarget:
    library_name: str
    library_id: int  # a Zotero libraryID, NOT a groupID
    collection_name: str | None
    collection_key: str | None  # None => library root


def _library_listing(libraries: list[dict]) -> str:
    return (
        ", ".join(
            f"{lib.get('name')!r} (libraryID {lib.get('libraryID')}"
            + (
                f", groupID {lib.get('groupID')})"
                if lib.get("groupID") is not None
                else ")"
            )
            for lib in libraries
        )
        or "(no libraries)"
    )


def find_library(libraries: list[dict], spec: str | None) -> dict:
    """Resolve `spec` to one library dict from a /libraries response.

    None or "My Library" => the user library. A digit string is matched against
    groupID first and then libraryID, because the two number spaces overlap and
    the caller most often has a groupID to hand. Otherwise an exact
    (case-insensitive) name match.
    """
    if spec is None or spec.strip().lower() == "my library":
        for lib in libraries:
            if lib.get("type") == "user":
                return lib
        raise ResolutionError("No user library ('My Library') in /libraries.")

    s = spec.strip()
    if s.isdigit():
        n = int(s)
        for lib in libraries:
            if lib.get("groupID") == n:
                return lib
        for lib in libraries:
            if lib.get("libraryID") == n:
                return lib
        raise ResolutionError(
            f"No library with groupID or libraryID {n}. "
            f"Available: {_library_listing(libraries)}"
        )

    matches = [lib for lib in libraries if lib.get("name", "").lower() == s.lower()]
    if not matches:
        raise ResolutionError(
            f"No library named {spec!r}. Available: {_library_listing(libraries)}"
        )
    if len(matches) > 1:
        ids = [m.get("libraryID") for m in matches]
        raise ResolutionError(
            f"Library name {spec!r} is ambiguous ({len(matches)} matches, "
            f"libraryIDs {ids}). Pass the numeric id instead."
        )
    return matches[0]


def find_collection(lib: dict, collection: str | None) -> tuple[str | None, str | None]:
    """Resolve a collection name within one library to (name, key).

    (None, None) when none is requested. A name matching more than one
    collection is an error, because sub-collections may share a name.
    """
    if collection is None:
        return (None, None)
    target = collection.strip().lower()
    cols = lib.get("collections", [])
    matches = [c for c in cols if c.get("name", "").lower() == target]
    if not matches:
        avail = sorted(c.get("name", "") for c in cols)
        raise ResolutionError(
            f"No collection named {collection!r} in {lib.get('name')!r}. "
            f"Available: {avail}"
        )
    if len(matches) > 1:
        detail = [
            {"key": c.get("key"), "parentKey": c.get("parentKey")} for c in matches
        ]
        raise ResolutionError(
            f"Collection name {collection!r} is ambiguous in {lib.get('name')!r} "
            f"({len(matches)} matches: {detail}). Pass --to-collection-key."
        )
    c = matches[0]
    return (c.get("name"), c.get("key"))


def resolve_copy_target(
    libraries: list[dict], *, to: str | None, collection: str | None
) -> CopyTarget:
    """Resolve a human target library + collection to the numeric libraryID and
    collectionKey that copy-item needs."""
    lib = find_library(libraries, to)
    library_id = lib.get("libraryID")
    if not isinstance(library_id, int):
        raise ResolutionError(
            f"Library {lib.get('name')!r} has no usable libraryID: {library_id!r}"
        )
    cname, ckey = find_collection(lib, collection)
    return CopyTarget(
        library_name=lib.get("name", ""),
        library_id=library_id,
        collection_name=cname,
        collection_key=ckey,
    )


def build_copy_payload(
    *,
    key: str,
    source_library_id: int | None,
    target: CopyTarget,
) -> dict:
    """Build the copy-item request body. Optional fields are omitted rather than
    sent as null, because the endpoint distinguishes absent from invalid."""
    payload: dict = {"key": key, "targetLibraryID": target.library_id}
    if source_library_id is not None:
        payload["libraryID"] = source_library_id
    if target.collection_key is not None:
        payload["targetCollectionKey"] = target.collection_key
    return payload


def parse_copy_response(status_code: int, body: str, content_type: str) -> dict:
    """Interpret a copy-item HTTP response per the addon.ts contract.

    200 returns {ok, key, created, attachments}. Structured failures return
    JSON {ok:false, code, message}; item/library resolution failures return
    plain text (404/400) without a code. Both are surfaced verbatim.
    """
    if status_code == 200:
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise CopyError(
                f"copy-item returned 200 but the body was not JSON "
                f"({content_type}): {body[:200]!r}"
            ) from e
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        raise CopyError(f"copy-item failed ({status_code}): {body.strip()}") from None
    code = parsed.get("code", "?")
    message = parsed.get("message", body.strip())
    raise CopyError(f"copy-item failed ({status_code} {code}): {message}")


def summarise_attachments(response: dict) -> dict[str, int]:
    """Count attachment results by status, preserving first-seen order."""
    counts: dict[str, int] = {}
    for att in response.get("attachments", []) or []:
        status = att.get("status", "?")
        counts[status] = counts.get(status, 0) + 1
    return counts


def copy_succeeded(response: dict) -> bool:
    """True when the parent landed AND no attachment failed.

    A copy whose parent exists but whose attachments partially failed is
    reported as a partial rather than a success, because ruling 6 makes a
    partial copy a normal outcome that a re-run tops up.
    """
    if not response.get("ok") or response.get("key") is None:
        return False
    counts = summarise_attachments(response)
    return all(s in SUCCESS_STATUSES or s == "already-present" for s in counts)


# --- Imperative shell (HTTP) ------------------------------------------------


def probe_copy_item() -> None:
    """Confirm the endpoint exists. An empty body yields 400 when present and
    Zotero's generic 404 when the installed build predates it."""
    import httpx

    try:
        httpx.get(PLUS_PROBE, timeout=3).raise_for_status()
    except Exception as e:
        sys.exit(
            f"zotero-api-plus not reachable on {PLUS_PROBE} ({e}).\n"
            "Start Zotero with the zotero-api-plus plugin installed."
        )
    try:
        r = httpx.post(COPY_ITEM_ENDPOINT, json={}, timeout=5)
    except Exception as e:
        sys.exit(f"copy-item probe failed: {e}")
    if r.status_code == 404:
        sys.exit(
            "copy-item is not in the installed zotero-api-plus build (404).\n"
            "Build and install a version that registers /api/plus/copy-item."
        )


def get_libraries() -> list[dict]:
    import httpx

    r = httpx.get(LIBRARIES_ENDPOINT, timeout=15)
    r.raise_for_status()
    return r.json().get("libraries", [])


def find_items(query: str) -> list[dict]:
    """Search every library for `query` via the stock local API and return
    candidate top-level items with their keys.

    qmode=fields searches item data fields (ADR 0001). It does not set
    noChildren, so attachments arrive beside parents and are filtered here.
    """
    import httpx

    out: list[dict] = []
    libs = get_libraries()
    for lib in libs:
        lid = lib.get("libraryID")
        path = (
            "users/0"
            if lib.get("type") == "user"
            else f"groups/{lib.get('groupID')}"
        )
        try:
            r = httpx.get(
                f"{STOCK_API}/{path}/items",
                params={"q": query, "qmode": "fields", "format": "json", "limit": 25},
                timeout=20,
            )
            r.raise_for_status()
        except Exception:
            continue
        for it in r.json():
            d = it.get("data", {})
            if d.get("itemType") in ("attachment", "note", "annotation"):
                continue
            creators = d.get("creators") or []
            out.append(
                {
                    "key": d.get("key"),
                    "libraryID": lid,
                    "library": lib.get("name"),
                    "itemType": d.get("itemType"),
                    "creator": (creators[0].get("lastName") if creators else "?"),
                    "date": (d.get("date") or "")[:4],
                    "title": d.get("title", ""),
                }
            )
    return out


def copy_item(payload: dict) -> dict:
    import httpx

    r = httpx.post(COPY_ITEM_ENDPOINT, json=payload, timeout=120)
    return parse_copy_response(
        r.status_code, r.text, r.headers.get("content-type", "")
    )


def _print_plan(payload: dict, target: CopyTarget, source_label: str) -> None:
    print("=== copy plan ===", flush=True)
    print(f"  source item: {payload['key']} (from {source_label})", flush=True)
    print(
        f"  target:      {target.library_name} (libraryID {target.library_id})",
        flush=True,
    )
    if target.collection_key:
        label = target.collection_name or "(explicit key)"
        print(f"  collection:  {label} (key {target.collection_key})", flush=True)
    else:
        print("  collection:  (library root)", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--find", help="Search all libraries and print item keys.")
    parser.add_argument("--key", help="Zotero item key of the item to copy.")
    parser.add_argument(
        "--from",
        dest="source",
        help="Source library: name, groupID, or 'My Library'. Omit to sweep.",
    )
    parser.add_argument("--to", help="Target library: name, groupID, or 'My Library'.")
    parser.add_argument("--to-collection", help="Target collection name.")
    parser.add_argument("--to-collection-key", help="Explicit target collection key.")
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Perform the copy. Without it, only resolves and previews.",
    )
    args = parser.parse_args()

    if args.find:
        for hit in find_items(args.find):
            print(
                f"  key={hit['key']} | libraryID={hit['libraryID']:<4} "
                f"| {hit['library'][:32]:32} | {hit['creator'][:16]:16} "
                f"{hit['date']:5} | {hit['title'][:52]}",
                flush=True,
            )
        return 0

    if not args.key or not args.to:
        sys.exit("Both --key and --to are required (or use --find to locate a key).")
    if args.to_collection and args.to_collection_key:
        sys.exit("Pass either --to-collection or --to-collection-key, not both.")

    probe_copy_item()
    libraries = get_libraries()

    try:
        target = resolve_copy_target(
            libraries, to=args.to, collection=args.to_collection
        )
        if args.to_collection_key is not None:
            target = CopyTarget(
                library_name=target.library_name,
                library_id=target.library_id,
                collection_name=None,
                collection_key=args.to_collection_key,
            )
        source_library_id = None
        source_label = "any library (sweep)"
        if args.source is not None:
            src = find_library(libraries, args.source)
            source_library_id = src.get("libraryID")
            source_label = f"{src.get('name')} (libraryID {source_library_id})"
    except ResolutionError as e:
        sys.exit(f"Resolution failed: {e}")

    payload = build_copy_payload(
        key=args.key, source_library_id=source_library_id, target=target
    )
    _print_plan(payload, target, source_label)

    if not args.copy:
        print(
            "\nPreview only (no write). Re-run with --copy to perform it.\n"
            "The copy is idempotent: an existing linked counterpart is returned\n"
            "and any missing attachment topped up, never duplicated.",
            flush=True,
        )
        return 0

    try:
        result = copy_item(payload)
    except CopyError as e:
        sys.exit(f"\n{e}")

    print("\n=== result ===", flush=True)
    print(
        f"  target item: {result.get('key')} "
        f"({'created' if result.get('created') else 'reused existing counterpart'})",
        flush=True,
    )
    attachments = result.get("attachments", []) or []
    if not attachments:
        print("  attachments: (none on the source)", flush=True)
    for att in attachments:
        line = f"  attachment {att.get('key')}: {att.get('status')}"
        if att.get("message"):
            line += f" — {att['message']}"
        print(line, flush=True)

    counts = summarise_attachments(result)
    if counts:
        print(f"\n  summary: {counts}", flush=True)
    if not copy_succeeded(result):
        print(
            "\n  PARTIAL: at least one attachment did not land. Re-running tops up\n"
            "  what failed without duplicating what succeeded.",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
