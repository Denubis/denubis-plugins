#!/usr/bin/env python3
"""Resolve a target library/collection and fetch a missing paper into Zotero
via the zotero-api-plus local API.

This replaces the fragile, hand-written `python3 -c "..."` JSON-parsing that the
SKILL used to leave to improvisation. The brittle step was turning a human group
+ collection name ("Project group", "Bayesian / Methods") into the numeric groupID
and collectionKey that add-item-by-id requires. That lives in `resolve_target`,
a pure function with unit tests.

Usage (resolve + preview only — NO write):
    uv run fetch.py --group 6549571 --collection "Bayesian / Methods" \
        10.1007/s11136-018-1798-3

Usage (DOI in, working paper out — fetch then render, gated behind --fetch):
    uv run fetch.py --group 6549571 --collection "Bayesian / Methods" \
        --fetch 10.1007/s11136-018-1798-3

With --fetch the item is written to the library and then rendered to per-page
markdown under <zettelkasten_root>/papers/<citekey>/ (via ingest.py). Pass
--no-render to fetch without rendering.

Target selection:
  --group           group name OR numeric groupID. Omit for My Library.
  --collection      collection name within the resolved library.
  --collection-key  explicit collection key (bypasses name resolution; use this
                    when --collection reports an ambiguous name).
  --no-render       fetch only; skip the render step.

The default run (no --fetch) resolves and previews the target without writing.
add-item-by-id does NOT deduplicate, so confirm each identifier is genuinely
absent from Zotero (e.g. `ingest.py` prints NOT FOUND) before re-running with
--fetch.

Endpoint contracts read from ~/people/Brian/zotero-api-plus/src/addon.ts and
utils/pdf-status.ts, not transcribed from documentation.
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
from pathlib import Path

# Zotero 10 authenticates every local-API write in the base class each endpoint
# inherits, so the write goes out through zotero_auth.post, which attaches the
# credentials and owns the retry. Zotero 7-9 are unaffected: no server ID header
# means no credential headers, and the request is what it always was.
import zotero_auth

# httpx is imported lazily inside the shell functions (probe_plus /
# get_libraries) so the functional core stays importable without the PEP 723
# deps — the unit tests load this module and exercise the pure functions
# directly. zotero_auth follows the same rule.

PLUS_PROBE = "http://localhost:23119/api/plus"
LIBRARIES_ENDPOINT = "http://localhost:23119/api/plus/libraries"
ADD_ITEM_ENDPOINT = "http://localhost:23119/api/plus/add-item-by-id"

# A fetched item is worth rendering only when a PDF is actually on disk.
RENDERABLE_PDF_STATUSES = ("present", "fetched")
# Rendering reuses ingest.py (DOI -> per-page markdown) via a subprocess, so its
# heavy deps (pymupdf4llm/docling/easyocr) load in their own uv env and never
# burden the lightweight resolve/preview path.
INGEST_SCRIPT = Path(__file__).resolve().parent / "ingest.py"


# --- Functional core (pure, unit-tested) ------------------------------------


class ResolutionError(Exception):
    """A group or collection name could not be resolved to an unambiguous key."""


class FetchError(Exception):
    """add-item-by-id returned an error or an unparseable response."""


@dataclass(frozen=True)
class ResolvedTarget:
    library_name: str
    group_id: int | None  # None => My Library (user library)
    collection_name: str | None
    collection_key: str | None  # None => library root, no collection


def _group_listing(libraries: list[dict]) -> str:
    groups = [
        f"{lib.get('name')!r} (groupID {lib.get('groupID')})"
        for lib in libraries
        if lib.get("type") == "group"
    ]
    return ", ".join(groups) if groups else "(no group libraries)"


def _find_library(libraries: list[dict], group: str | None) -> dict:
    """Resolve `group` to one library dict from a /libraries response.

    `group` is None or "My Library" => the user library; a digit string =>
    match by groupID; otherwise => exact (case-insensitive) group name match.
    """
    if group is None or group.strip().lower() == "my library":
        for lib in libraries:
            if lib.get("type") == "user":
                return lib
        raise ResolutionError(
            "No user library ('My Library') in the /libraries response."
        )

    g = group.strip()
    if g.isdigit():
        gid = int(g)
        for lib in libraries:
            if lib.get("groupID") == gid:
                return lib
        raise ResolutionError(
            f"No group with ID {gid}. Available: {_group_listing(libraries)}"
        )

    matches = [
        lib
        for lib in libraries
        if lib.get("type") == "group" and lib.get("name", "").lower() == g.lower()
    ]
    if not matches:
        raise ResolutionError(
            f"No group named {group!r}. Available groups: {_group_listing(libraries)}"
        )
    if len(matches) > 1:
        ids = [m.get("groupID") for m in matches]
        raise ResolutionError(
            f"Group name {group!r} is ambiguous ({len(matches)} matches, "
            f"groupIDs {ids}). Pass the numeric groupID instead."
        )
    return matches[0]


def _find_collection(
    lib: dict, collection: str | None
) -> tuple[str | None, str | None]:
    """Resolve a collection name within one library to (name, key).

    Returns (None, None) when no collection is requested. Collection names are
    not guaranteed unique (sub-collections can share a name), so a name that
    matches more than one collection is an error — the caller is told to use an
    explicit key.
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
            f"({len(matches)} matches: {detail}). Pass --collection-key to choose one."
        )
    c = matches[0]
    return (c.get("name"), c.get("key"))


def resolve_target(
    libraries: list[dict], *, group: str | None, collection: str | None
) -> ResolvedTarget:
    """Resolve human group + collection names to a ResolvedTarget with the
    numeric groupID and collectionKey that add-item-by-id needs."""
    lib = _find_library(libraries, group)
    cname, ckey = _find_collection(lib, collection)
    return ResolvedTarget(
        library_name=lib.get("name", ""),
        group_id=lib.get("groupID"),  # absent for the user library => None
        collection_name=cname,
        collection_key=ckey,
    )


def parse_add_item_response(status_code: int, body: str, content_type: str) -> dict:
    """Interpret an add-item-by-id HTTP response per the addon.ts contract.

    200 returns a JSON object {status, addedCount, titles, items}. 400/404/500
    return a plain-text error which we surface verbatim.
    """
    if status_code == 200:
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise FetchError(
                f"add-item-by-id returned 200 but the body was not JSON "
                f"({content_type}): {body[:200]!r}"
            ) from e
    raise FetchError(f"add-item-by-id failed ({status_code}): {body.strip()}")


def should_render(pdf_status: str) -> bool:
    """A fetched item is worth rendering only when a PDF is on disk."""
    return pdf_status in RENDERABLE_PDF_STATUSES


def renderable_dois(results: dict) -> list[str]:
    """Select DOIs whose add-item result has at least one renderable PDF.

    `results` maps a fetched DOI to its parsed add-item-by-id response. Input
    order is preserved so the render pass follows fetch order.
    """
    out: list[str] = []
    for doi, res in results.items():
        items = res.get("items", []) if isinstance(res, dict) else []
        if any(should_render(it.get("pdf", "")) for it in items):
            out.append(doi)
    return out


# --- Imperative shell (HTTP) ------------------------------------------------


def probe_plus() -> None:
    import httpx

    try:
        r = httpx.get(PLUS_PROBE, timeout=3)
    except Exception as e:
        sys.exit(
            f"zotero-api-plus not reachable on {PLUS_PROBE} ({e}).\n"
            "The fetch path requires Zotero running with the zotero-api-plus "
            "plugin (v0.3.0+). Without it, add papers via the Zotero connector."
        )
    if "Zotero Local API Plus is running" not in r.text:
        sys.exit(
            f"zotero-api-plus capability probe returned unexpected body: "
            f"{r.text[:200]!r}\nExpected the plugin's running banner."
        )


def get_libraries() -> list[dict]:
    import httpx

    r = httpx.get(LIBRARIES_ENDPOINT, timeout=8)
    r.raise_for_status()
    return r.json().get("libraries", [])


def add_item(identifier: str, group_id: int | None, collection_key: str | None) -> dict:
    payload: dict = {"identifier": identifier}
    if group_id is not None:
        payload["groupID"] = group_id
    if collection_key is not None:
        payload["collectionKey"] = collection_key
    r = zotero_auth.post(ADD_ITEM_ENDPOINT, json=payload, timeout=60)
    return parse_add_item_response(
        r.status_code, r.text, r.headers.get("content-type", "")
    )


def render_dois(
    dois: list[str],
    *,
    allow_mocr: bool = False,
    retries: int = 1,
    retry_wait: float = 4.0,
) -> int:
    """Render freshly fetched papers by delegating to ingest.py (DOI -> per-page
    markdown under <zettelkasten_root>/papers/<citekey>/).

    Runs ingest.py in a subprocess so its render dependencies resolve in their
    own uv environment. BBT can lag a few seconds indexing a just-added item, so
    a failed run is retried once. `allow_mocr` is passed through to ingest.py.
    Returns ingest.py's exit code (0 = success).
    """
    import subprocess
    import time

    cmd = ["uv", "run", str(INGEST_SCRIPT)]
    if allow_mocr:
        cmd.append("--allow-mocr")
    cmd += dois
    attempt = 0
    while True:
        print(f"\n=== render {dois} (via ingest.py) ===", flush=True)
        proc = subprocess.run(cmd, check=False)
        if proc.returncode == 0:
            return 0
        attempt += 1
        if attempt > retries:
            print(
                f"  render failed (ingest.py exit {proc.returncode}). The item "
                "may still be indexing in BBT; re-run the render once it appears.",
                flush=True,
            )
            return proc.returncode
        print(
            f"  ingest.py exit {proc.returncode}; retrying in {retry_wait:.0f}s "
            "(BBT may still be indexing the new item)",
            flush=True,
        )
        time.sleep(retry_wait)


def _print_target(target: ResolvedTarget, identifiers: list[str]) -> None:
    print("=== resolved target ===", flush=True)
    if target.group_id is not None:
        print(
            f"  library:    {target.library_name} (groupID {target.group_id})",
            flush=True,
        )
    else:
        print(f"  library:    {target.library_name} (My Library)", flush=True)
    if target.collection_key:
        label = target.collection_name or "(explicit key)"
        print(f"  collection: {label} (key {target.collection_key})", flush=True)
    else:
        print("  collection: (library root — no collection)", flush=True)
    print(f"  identifiers: {identifiers}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "identifiers", nargs="+", help="DOIs/ISBNs/PMIDs/arXiv IDs to fetch."
    )
    parser.add_argument(
        "--group", help="Target group: name or numeric groupID. Omit for My Library."
    )
    parser.add_argument(
        "--collection", help="Target collection name within the resolved library."
    )
    parser.add_argument(
        "--collection-key",
        help="Explicit collection key (bypasses --collection name resolution).",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Write to the library. Without it, only resolves the target and previews.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="After --fetch, do NOT render. Default is to render each fetched "
        "paper to per-page markdown via ingest.py.",
    )
    parser.add_argument(
        "--allow-mocr",
        action="store_true",
        help="Pass through to the render step: permit GPU escalation to dots.mocr "
        "when the cascade can't produce a usable render.",
    )
    args = parser.parse_args()

    if args.collection and args.collection_key:
        sys.exit(
            "Pass either --collection (resolve by name) or --collection-key "
            "(explicit), not both."
        )

    probe_plus()
    libraries = get_libraries()

    try:
        if args.collection_key is not None:
            base = resolve_target(libraries, group=args.group, collection=None)
            target = ResolvedTarget(
                library_name=base.library_name,
                group_id=base.group_id,
                collection_name=None,
                collection_key=args.collection_key,
            )
        else:
            target = resolve_target(
                libraries, group=args.group, collection=args.collection
            )
    except ResolutionError as e:
        sys.exit(f"Target resolution failed: {e}")

    _print_target(target, args.identifiers)

    if not args.fetch:
        print(
            "\nPreview only (no write). add-item-by-id does NOT dedup — confirm each\n"
            "identifier is absent from Zotero first, then re-run with --fetch"
            " to write.",
            flush=True,
        )
        return 0

    results_by_doi: dict = {}
    failures = 0
    for ident in args.identifiers:
        print(f"\n=== fetch {ident} ===", flush=True)
        try:
            result = add_item(ident, target.group_id, target.collection_key)
        except FetchError as e:
            print(f"  ERROR: {e}", flush=True)
            failures += 1
            continue
        items = result.get("items", [])
        if not items:
            print("  no items added", flush=True)
            failures += 1
            continue
        results_by_doi[ident] = result
        for item in items:
            print(
                f"  added: {item.get('title')!r} (key {item.get('key')}) "
                f"pdf={item.get('pdf')}",
                flush=True,
            )
            if item.get("pdf") in ("unavailable", "error"):
                print(
                    "    -> no PDF on disk; attach via the Zotero connector,"
                    " then render.",
                    flush=True,
                )

    to_render = renderable_dois(results_by_doi)
    render_rc = 0
    if args.no_render:
        if to_render:
            print(f"\n--no-render: skipping render of {to_render}", flush=True)
    elif to_render:
        render_rc = render_dois(to_render, allow_mocr=args.allow_mocr)
    elif results_by_doi:
        print(
            "\nNothing to render — no PDF landed on disk for the fetched items.",
            flush=True,
        )

    render_note = ""
    if not args.no_render and to_render:
        render_note = f", render {'ok' if render_rc == 0 else 'FAILED'}"
    print(
        f"\n=== summary: {len(args.identifiers) - failures} fetched, "
        f"{failures} failed{render_note} ==="
    )
    return 1 if (failures or render_rc) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except zotero_auth.AuthorizationError as exc:
        # Zotero answered the authorisation request with a denial or a rate
        # limit. Retrying only re-prompts, so report it and stop.
        sys.exit(str(exc))
