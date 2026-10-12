#!/usr/bin/env python3
"""List a Zotero collection, read-only, with trashed rows marked.

Usage:
    uv run collection.py --list "<collection name or key>" [--library "<library>"]

The listing is Zotero's own stock local API (`/collections/<key>/items`,
`includeTrashed=1`, paginated to the end), so what it prints is what Zotero
holds, trash included. Names are resolved through zotero-api-plus
`/api/plus/libraries`, the same resolver `copy_item.py`, `fetch.py` and
`update_item.py --list` use (ruling of 2026-10-12, ADR 0028): an ambiguous name
is an error listing the candidate keys and their parents, and a bare
eight-character key is accepted as given. `--library` defaults to My Library.

Each row: `key  citekey  title  [in trash]  attachments: n (names)`, then a
total line. Nothing here writes.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copy_item import (
    ResolutionError,
    find_collection,
    find_library,
    get_libraries,
    probe_api_plus,
)
from zotero_local_api import (
    LibraryQueryError,
    get_collection_items,
    summarise_collection,
)

_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")


# --- Functional core (pure, unit-tested) ------------------------------------


def resolve_collection(library: dict, spec: str) -> str:
    """The collection key for `spec` within one zotero-api-plus library record.

    A bare eight-character key is returned as given, so a key Zotero printed
    (or an ambiguous-name error listed) can be used directly. Otherwise the
    name is matched exactly, case-insensitively; more than one match is an
    error that names every candidate key with its parent key.
    """
    spec = spec.strip()
    if _KEY_RE.match(spec):
        return spec
    try:
        _name, key = find_collection(library, spec)
    except ResolutionError as error:
        raise ResolutionError(
            str(error).replace("--to-collection-key", "the key")
        ) from None
    if key is None:
        raise ResolutionError("a collection name or key is required")
    return key


def render_rows(rows: list[dict]) -> str:
    """One line per parent item plus a total line."""
    lines = []
    for row in rows:
        cells = [
            row["key"],
            row["citekey"] or "(no citekey)",
            row["title"] or "(untitled)",
        ]
        if row["in_trash"]:
            cells.append("[in trash]")
        attachments = row["attachments"]
        names = ", ".join(
            a["filename"] + (" [in trash]" if a["in_trash"] else "")
            for a in attachments
        )
        cells.append(
            f"attachments: {len(attachments)}" + (f" ({names})" if names else "")
        )
        lines.append("  ".join(cells))
    trashed = sum(1 for row in rows if row["in_trash"])
    noun = "item" if len(rows) == 1 else "items"
    lines.append(f"{len(rows)} {noun} ({trashed} in trash)")
    return "\n".join(lines)


# --- Imperative shell -------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    verbs = parser.add_mutually_exclusive_group(required=True)
    verbs.add_argument(
        "--list",
        metavar="COLLECTION",
        help="list every item of the collection (name or key), trash marked",
    )
    parser.add_argument(
        "--library",
        help="library holding the collection: name, numeric groupID, or 'My Library'",
    )
    return parser


def list_collection(spec: str, library_spec: str | None) -> int:
    probe_api_plus()
    try:
        library = find_library(get_libraries(), library_spec)
        key = resolve_collection(library, spec)
    except ResolutionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    try:
        items = get_collection_items(library, key, include_trashed=True)
    except LibraryQueryError as error:
        print(f"Error: cannot list collection items: {error}", file=sys.stderr)
        return 1
    rows = summarise_collection(items)
    print(f"{spec} ({key}) in {library.get('name')}", flush=True)
    print(render_rows(rows), flush=True)
    return 0


def main() -> int:
    args = build_arg_parser().parse_args()
    return list_collection(args.list, args.library)


if __name__ == "__main__":
    sys.exit(main())
