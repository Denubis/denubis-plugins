#!/usr/bin/env python3
"""Create one regular Zotero item, optionally filed into a collection.

Usage (preview, writes nothing):
    uv run create_item.py --type book --set title="A title" --set date=2026 \\
        --author "Last, First" [--creator editor="Last, First"] \\
        [--collection "<name or key>"] [--library "<library>"]

Usage (apply, exactly the command the preview printed):
    ... --apply --expect-collection KEY --expect-library ID

Create class (design 2026-10-12, ADR 0029): a new object has no prior
version, so the preview prints the full JSON body, the resolved library
(name and libraryID) and collection key, and the apply command carrying
`--expect-collection KEY` (when a collection is named) and
`--expect-library ID`. Apply re-resolves both names and stops with `target
changed` if a key differs, POSTs through Zotero 10's stock local API, reads
the new item back, and reports `accepted` and `verified` separately: the
fields set, the creator list, and the collection key must all read back. The
citekey is Better BibTeX's to assign; its absence is reported, not treated as
a failure. The field grammar is `update_item.py`'s. Zotero 10 only.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import write_gate
import zotero_auth
from collection import resolve_collection
from copy_item import (
    ResolutionError,
    find_library,
    get_libraries,
    probe_api_plus,
)
from update_item import parse_creator_name, parse_creator_spec, parse_field_assignment
from zotero_local_api import (
    LibraryQueryError,
    StockWriteUnavailable,
    create_objects,
    read_object,
    require_stock_writes,
)

# --- Functional core (pure) ------------------------------------------------------


def build_item_body(
    item_type: str,
    fields: dict[str, str],
    creators: list[dict],
    collection_key: str | None,
) -> dict:
    """The POST body: itemType, the fields, the creators, and the collection."""
    body: dict = {"itemType": item_type, **fields}
    if creators:
        body["creators"] = creators
    if collection_key:
        body["collections"] = [collection_key]
    return body


def verification_problems(back: dict, body: dict) -> list[str]:
    """What the read-back does not show of what was asked for."""
    data = back.get("data") or {}
    problems = []
    for name, value in body.items():
        if name in {"creators", "collections"}:
            continue
        if data.get(name) != value:
            problems.append(f"{name} is {data.get(name)!r}, asked {value!r}")
    wanted = body.get("creators") or []
    got = [
        {
            k: v
            for k, v in c.items()
            if k in {"creatorType", "firstName", "lastName", "name"}
        }
        for c in data.get("creators") or []
    ]
    if wanted and got != wanted:
        problems.append(f"creators are {got}, asked {wanted}")
    for key in body.get("collections") or []:
        if key not in (data.get("collections") or []):
            problems.append(f"collection {key} not in {data.get('collections')}")
    return problems


def created_key(outcome: dict) -> str | None:
    for entry in (outcome.get("successful") or {}).values():
        if isinstance(entry, dict):
            key = entry.get("key") or (entry.get("data") or {}).get("key")
            if key:
                return key
    return None


# --- Imperative shell -------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--type", dest="item_type", required=True, help="Zotero item type"
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        required=True,
        help="set a field (repeatable; at least one)",
    )
    parser.add_argument(
        "--author",
        action="append",
        default=[],
        metavar="'Last, First'",
        help="an author, in order (repeatable); no comma means a single-field name",
    )
    parser.add_argument(
        "--creator",
        action="append",
        default=[],
        metavar="TYPE='Last, First'",
        help="a creator of another type (repeatable)",
    )
    parser.add_argument(
        "--collection", metavar="COLLECTION", help="file into (name or key)"
    )
    parser.add_argument(
        "--library",
        help="target library: name, numeric groupID, or 'My Library'",
    )
    write_gate.add_gate_arguments(parser, "create")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    required = ["--expect-library"] + (
        ["--expect-collection"] if args.collection else []
    )
    missing = write_gate.missing_expectations(args, required)
    if missing:
        parser.error(f"--apply requires {' '.join(missing)} from the preview")

    try:
        fields = dict(parse_field_assignment(spec) for spec in args.set)
        creators = [
            {"creatorType": "author", **parse_creator_name(value)}
            for value in args.author
        ]
        creators.extend(parse_creator_spec(spec) for spec in args.creator)
    except ValueError as error:
        parser.error(str(error))

    try:
        require_stock_writes()
    except StockWriteUnavailable as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    probe_api_plus()
    try:
        library = find_library(get_libraries(), args.library)
        collection_key = (
            resolve_collection(library, args.collection) if args.collection else None
        )
    except ResolutionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    body = build_item_body(args.item_type, fields, creators, collection_key)
    expected: dict = {}
    if collection_key:
        expected["collection"] = collection_key
    expected["library"] = library.get("libraryID")

    print("=== create item ===", flush=True)
    print(f"  payload: {json.dumps(body, indent=2)}", flush=True)
    print(
        f"  library: {library.get('name')} (libraryID {library.get('libraryID')})",
        flush=True,
    )
    if collection_key:
        print(f"  collection: {args.collection} ({collection_key})", flush=True)
    if not args.apply:
        print(
            "\nPreview only (no write). To apply exactly this change:\n  "
            + write_gate.format_apply_command(sys.argv, expected),
            flush=True,
        )
        return 0

    refusal = write_gate.state_refusal(
        write_gate.expected_from_args(args, "create"), expected
    )
    if refusal:
        print(f"  {refusal}\n  Re-run the preview and copy its apply command.")
        line, code = write_gate.report(accepted=False, verified=None, reason=refusal)
        print(line, flush=True)
        return code

    line, code = apply_create(library, body)
    print(line, flush=True)
    return code


def apply_create(library: dict, body: dict) -> tuple[str, int]:
    """POST the body, read the new item back, and return the report line."""
    try:
        outcome = create_objects(library, "items", [body])
    except LibraryQueryError as error:
        return write_gate.report(accepted=False, verified=None, reason=str(error))
    key = created_key(outcome)
    if key is None:
        failed = outcome.get("failed") or {}
        return write_gate.report(
            accepted=False,
            verified=None,
            reason=f"Zotero reported failed={json.dumps(failed)}",
        )
    print(f"  key: {key}", flush=True)

    try:
        back = read_object(library, "items", key)
    except LibraryQueryError as error:
        return write_gate.report(
            accepted=True, verified=False, reason=f"read-back failed: {error}"
        )
    citekey = (back.get("data") or {}).get("citationKey")
    print(f"  citekey: {citekey or 'not yet assigned'}", flush=True)
    problems = verification_problems(back, body)
    return write_gate.report(
        accepted=True, verified=not problems, reason="; ".join(problems) or None
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except zotero_auth.AuthorizationError as exc:
        # Zotero answered the authorisation request with a denial or a rate
        # limit. Retrying only re-prompts, so report it and stop.
        sys.exit(str(exc))
