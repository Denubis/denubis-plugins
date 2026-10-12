#!/usr/bin/env python3
"""File an existing Zotero item into a collection, or take it out, in place.

Usage (preview, writes nothing):
    uv run item_collections.py --key ABCD1234 --add "Sage SRM Guide"
    uv run item_collections.py --key ABCD1234 --remove SAGE0001 --library "<library>"

Usage (apply, exactly the command the preview printed):
    uv run item_collections.py --key ABCD1234 --add "Sage SRM Guide" \\
        --apply --expect-version 429

This is the way to file an item that already exists: one record, its
`collections` array PATCHed through Zotero 10's stock local API (ADR 0028).
`copy_item.py` is for copying between libraries and tops up attachments; it
duplicated a record when used for filing (the Sage SRM Guide defects of
2026-10-10).

Modify class (design 2026-10-12): the preview reads the item and prints its
version; `--apply --expect-version N` re-reads, refuses `changed since
preview` if the version moved, PATCHes with `If-Unmodified-Since-Version: N`
(Zotero answers 412 on a race, reported as `conflict`), reads the item back
and reports `accepted` and `verified` separately. Zotero 10 only. Names are
resolved through zotero-api-plus `/api/plus/libraries`.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
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
from zotero_local_api import (
    LibraryQueryError,
    StockWriteUnavailable,
    item_in_trash,
    read_object,
    require_stock_writes,
    write_object,
)

# --- Functional core (pure) ------------------------------------------------------


def merged_collections(current: list[str], target: str, *, add: bool) -> list[str]:
    """The `collections` array after adding or removing `target`, order kept."""
    if add:
        return current if target in current else [*current, target]
    return [key for key in current if key != target]


def collection_labels(keys: list[str], library: dict) -> str:
    names = {c.get("key"): c.get("name") for c in library.get("collections", [])}
    return ", ".join(f"{names.get(k, '?')} ({k})" for k in keys) if keys else "(none)"


# --- Imperative shell -------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--key", required=True, help="the Zotero item key")
    parser.add_argument(
        "--library",
        help="library holding the item: name, numeric groupID, or 'My Library'",
    )
    change = parser.add_mutually_exclusive_group(required=True)
    change.add_argument("--add", metavar="COLLECTION", help="file into (name or key)")
    change.add_argument(
        "--remove", metavar="COLLECTION", help="take out of (name or key)"
    )
    write_gate.add_gate_arguments(parser, "modify")
    return parser


def main() -> int:  # noqa: PLR0911 - one return per outcome the user must tell apart
    parser = build_arg_parser()
    args = parser.parse_args()
    missing = write_gate.missing_expectations(args, ["--expect-version"])
    if missing:
        parser.error(f"--apply requires {' '.join(missing)} from the preview")

    try:
        require_stock_writes()
    except StockWriteUnavailable as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    probe_api_plus()

    add = args.add is not None
    spec = args.add if add else args.remove
    try:
        library = find_library(get_libraries(), args.library)
        target = resolve_collection(library, spec)
    except ResolutionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    try:
        item = read_object(library, "items", args.key)
    except LibraryQueryError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    data = item.get("data") or {}
    version = item.get("version", data.get("version"))
    before = list(data.get("collections") or [])
    after = merged_collections(before, target, add=add)

    print_preview(
        args.key, library, item, target=target, before=before, after=after, add=add
    )

    if after == before:
        print(
            f"\n  No change: the item is already {'in' if add else 'out of'} "
            f"{target}. Nothing to apply.",
            flush=True,
        )
        return 0

    if not args.apply:
        print(
            "\nPreview only (no write). To apply exactly this change:\n  "
            + write_gate.format_apply_command(sys.argv, {"version": version}),
            flush=True,
        )
        return 0

    refusal = write_gate.state_refusal(
        {"version": args.expect_version}, {"version": version}
    )
    if refusal:
        line, code = write_gate.report(accepted=False, verified=None, reason=refusal)
        print(f"\n  {refusal}\n  Re-run the preview and copy its apply command.")
        print(line, flush=True)
        return code

    line, code = apply_change(library, args.key, after, version, target, add=add)
    print(line, flush=True)
    return code


def print_preview(
    key: str,
    library: dict,
    item: dict,
    *,
    target: str,
    before: list[str],
    after: list[str],
    add: bool,
) -> None:
    data = item.get("data") or {}
    print(f"=== {'file into' if add else 'take out of'} {target} ===", flush=True)
    print(f"  item:        {key}  {data.get('itemType', '?')}", flush=True)
    print(f"  title:       {data.get('title') or '(untitled)'}", flush=True)
    print(f"  citekey:     {data.get('citationKey') or '(none yet)'}", flush=True)
    print(f"  library:     {library.get('name')}", flush=True)
    if item_in_trash(item):
        print("  note:        this item is in the trash", flush=True)
    print(f"  version:     {item.get('version', data.get('version'))}", flush=True)
    print(f"  collections: {collection_labels(before, library)}", flush=True)
    print(f"  after:       {collection_labels(after, library)}", flush=True)


def apply_change(
    library: dict,
    key: str,
    after: list[str],
    version: int,
    target: str,
    *,
    add: bool,
) -> tuple[str, int]:
    """PATCH the merged array, read back, and return the report line and exit."""
    result = write_object(library, "items", key, {"collections": after}, version)
    if result.status != "accepted":
        detail = result.body
        if result.status == "conflict" and result.current:
            cur = result.current
            detail = (
                f"conflict (412): Zotero now holds version "
                f"{cur.get('version')} with collections "
                f"{(cur.get('data') or {}).get('collections')}"
            )
        return write_gate.report(
            accepted=False, verified=None, reason=f"{result.status}: {detail}"
        )

    try:
        back = read_object(library, "items", key)
    except LibraryQueryError as error:
        return write_gate.report(
            accepted=True, verified=False, reason=f"read-back failed: {error}"
        )
    now = list((back.get("data") or {}).get("collections") or [])
    present = target in now
    verified = present if add else not present
    reason = (
        None
        if verified
        else (
            f"read-back {'still lists' if not add else 'does not list'} {target}: {now}"
        )
    )
    print(
        f"  Zotero accepted the write (version {result.version}); "
        f"read-back collections: {collection_labels(now, library)}",
        flush=True,
    )
    return write_gate.report(accepted=True, verified=verified, reason=reason)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except zotero_auth.AuthorizationError as exc:
        # Zotero answered the authorisation request with a denial or a rate
        # limit. Retrying only re-prompts, so report it and stop.
        sys.exit(str(exc))
