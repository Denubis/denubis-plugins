#!/usr/bin/env python3
"""List, create, rename, trash, or restore a Zotero collection.

Read-only listing (trashed rows marked):
    uv run collection.py --list "<collection name or key>" [--library "<library>"]

Writes, each a preview until `--apply` is added with the flag the preview
printed (design 2026-10-12, ADR 0028; Zotero 10 only; never `DELETE`):
    uv run collection.py --create NAME [--parent <name or key>]
        --apply --expect-library ID [--expect-parent KEY]        (create class)
    uv run collection.py --rename KEY NAME   --apply --expect-version N  (modify)
    uv run collection.py --trash KEY         --apply --expect-version N  (modify)
    uv run collection.py --restore KEY [--descendants K1,K2,...]
                                             --apply --expect-version N  (modify)

The listing is Zotero's own stock local API (`/collections/<key>/items`,
`includeTrashed=1`, paginated to the end), so what it prints is what Zotero
holds, trash included. Names are resolved through zotero-api-plus
`/api/plus/libraries`, the same resolver `copy_item.py`, `fetch.py` and
`update_item.py --list` use: an ambiguous name is an error listing the
candidate keys and their parents, and a bare eight-character key is accepted
as given. `--library` defaults to My Library.

Trash semantics: Zotero trashes a collection's descendants with it, but
restores non-recursively, and its collection listings exclude the trash
(server_localAPI.js:993-995, collection.js:776, read 2026-10-12). So `--trash`
lists the descendants while they are still live, verifies each by direct key
read afterwards, and prints the exact `--restore KEY --descendants ...`
command; `--restore` clears `deleted` on the parent and then on each listed
descendant, shallowest first, and without `--descendants` restores the parent
only and says the descendants are unknown.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import write_gate
import zotero_auth
from copy_item import (
    ResolutionError,
    find_collection,
    find_library,
    get_libraries,
    probe_api_plus,
)
from zotero_local_api import (
    LibraryQueryError,
    StockWriteUnavailable,
    create_objects,
    get_collection_items,
    get_subcollections,
    read_object,
    require_stock_writes,
    summarise_collection,
    write_object,
)

_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")

DESCENDANTS_UNKNOWN = (
    "descendants unknown: Zotero's collection listings exclude the trash; pass "
    "--descendants from the trash output or restore them in Zotero"
)


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


def collection_deleted(envelope: dict) -> bool:
    return bool((envelope.get("data") or {}).get("deleted"))


def collection_version(envelope: dict) -> int | None:
    return envelope.get("version", (envelope.get("data") or {}).get("version"))


def order_by_depth(descendants: dict[str, dict], root: str) -> list[str]:
    """Descendant keys shallowest first, by walking `parentCollection` up to
    `root` through the given envelopes (a key whose chain leaves the known
    set is treated as deepest, so it is still restored, last)."""

    def depth(key: str) -> int:
        steps = 0
        current = key
        while current != root and steps <= len(descendants):
            parent = (descendants.get(current, {}).get("data") or {}).get(
                "parentCollection"
            )
            if not parent:
                return len(descendants) + 1
            current = parent
            steps += 1
        return steps

    return sorted(descendants, key=lambda k: (depth(k), k))


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
    verbs.add_argument("--create", metavar="NAME", help="create a collection")
    verbs.add_argument(
        "--rename", nargs=2, metavar=("KEY", "NAME"), help="rename a collection"
    )
    verbs.add_argument("--trash", metavar="KEY", help="move a collection to the trash")
    verbs.add_argument(
        "--restore", metavar="KEY", help="bring a collection back from the trash"
    )
    parser.add_argument(
        "--parent",
        metavar="COLLECTION",
        help="with --create: the parent collection (name or key); omit for top level",
    )
    parser.add_argument(
        "--descendants",
        metavar="K1,K2,...",
        help="with --restore: descendant collection keys from the trash output",
    )
    parser.add_argument(
        "--library",
        help="library holding the collection: name, numeric groupID, or 'My Library'",
    )
    write_gate.add_gate_arguments(parser, "create", "modify")
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


def _finish(line_and_code: tuple[str, int]) -> int:
    line, code = line_and_code
    print(line, flush=True)
    return code


def _read_collection(library: dict, key: str) -> dict | None:
    try:
        return read_object(library, "collections", key)
    except LibraryQueryError as error:
        print(f"Error: {error}", file=sys.stderr)
        return None


def create_collection(args: argparse.Namespace, library: dict) -> int:  # noqa: PLR0911 - one return per outcome the user must tell apart
    parent_key = None
    if args.parent:
        try:
            parent_key = resolve_collection(library, args.parent)
        except ResolutionError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2
    body = {"name": args.create, "parentCollection": parent_key or False}
    library_id = library.get("libraryID")
    expected = {}
    if parent_key:
        expected["parent"] = parent_key
    expected["library"] = library_id

    print("=== create collection ===", flush=True)
    print(f"  payload: {json.dumps(body)}", flush=True)
    print(f"  library: {library.get('name')} (libraryID {library_id})", flush=True)
    if parent_key:
        names = {c.get("key"): c.get("name") for c in library.get("collections", [])}
        print(f"  parent:  {names.get(parent_key, '?')} ({parent_key})", flush=True)
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
        return _finish(write_gate.report(accepted=False, verified=None, reason=refusal))

    try:
        outcome = create_objects(library, "collections", [body])
    except LibraryQueryError as error:
        return _finish(
            write_gate.report(accepted=False, verified=None, reason=str(error))
        )
    key = _created_key(outcome)
    if key is None:
        return _finish(
            write_gate.report(
                accepted=False, verified=None, reason=f"Zotero reported {outcome}"
            )
        )
    print(f"  key: {key}", flush=True)
    back = _read_collection(library, key)
    if back is None:
        return _finish(
            write_gate.report(accepted=True, verified=False, reason="read-back failed")
        )
    data = back.get("data") or {}
    problems = []
    if data.get("name") != args.create:
        problems.append(f"name is {data.get('name')!r}")
    if (data.get("parentCollection") or False) != (parent_key or False):
        problems.append(f"parentCollection is {data.get('parentCollection')!r}")
    return _finish(
        write_gate.report(
            accepted=True, verified=not problems, reason="; ".join(problems) or None
        )
    )


def _created_key(outcome: dict) -> str | None:
    successful = outcome.get("successful") or {}
    for entry in successful.values():
        if isinstance(entry, dict):
            key = entry.get("key") or (entry.get("data") or {}).get("key")
            if key:
                return key
    return None


def rename_collection(args: argparse.Namespace, library: dict) -> int:
    key, name = args.rename
    envelope = _read_collection(library, key)
    if envelope is None:
        return 1
    data = envelope.get("data") or {}
    version = collection_version(envelope)
    print("=== rename collection ===", flush=True)
    print(f"  key:     {key}", flush=True)
    print(f"  library: {library.get('name')}", flush=True)
    print(f"  name:    {data.get('name')!r}  ->  {name!r}", flush=True)
    print(f"  version: {version}", flush=True)
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
        print(f"  {refusal}\n  Re-run the preview and copy its apply command.")
        return _finish(write_gate.report(accepted=False, verified=None, reason=refusal))
    result = write_object(library, "collections", key, {"name": name}, version)
    if result.status != "accepted":
        return _finish(
            write_gate.report(accepted=False, verified=None, reason=_describe(result))
        )
    back = _read_collection(library, key)
    now = (back or {}).get("data", {}).get("name") if back else None
    return _finish(
        write_gate.report(
            accepted=True,
            verified=now == name,
            reason=None if now == name else f"read-back name is {now!r}",
        )
    )


def _describe(result) -> str:
    if result.status == "conflict" and result.current:
        cur = result.current
        return (
            f"conflict (412): Zotero now holds version {cur.get('version')}, "
            f"deleted={(cur.get('data') or {}).get('deleted', False)}, "
            f"name={(cur.get('data') or {}).get('name')!r}"
        )
    return f"{result.status}: {result.body}"


def descendant_collections(library: dict, key: str) -> list[dict]:
    """Every live descendant, depth first, through the sub-collection listing."""
    out: list[dict] = []
    for child in get_subcollections(library, key):
        out.append(child)
        out.extend(descendant_collections(library, child.get("key", "")))
    return out


def trash_collection(args: argparse.Namespace, library: dict) -> int:  # noqa: PLR0911 - one return per outcome the user must tell apart
    key = args.trash
    envelope = _read_collection(library, key)
    if envelope is None:
        return 1
    data = envelope.get("data") or {}
    version = collection_version(envelope)
    try:
        descendants = descendant_collections(library, key)
    except LibraryQueryError as error:
        print(f"Error: cannot list descendants: {error}", file=sys.stderr)
        return 1
    print("=== trash collection ===", flush=True)
    print(f"  key:     {key}", flush=True)
    print(f"  name:    {data.get('name')}", flush=True)
    print(f"  library: {library.get('name')}", flush=True)
    print(f"  items:   {(envelope.get('meta') or {}).get('numItems', '?')}", flush=True)
    print(f"  descendants: {len(descendants)} (they are trashed with it)", flush=True)
    for child in descendants:
        cdata = child.get("data") or {}
        print(
            f"    {child.get('key')}  {cdata.get('name')}  "
            f"(parent {cdata.get('parentCollection')})",
            flush=True,
        )
    print(
        f"  deleted: {'true' if collection_deleted(envelope) else 'false'}", flush=True
    )
    print(f"  version: {version}", flush=True)
    if collection_deleted(envelope):
        print("\n  No change: the collection is already in the trash.", flush=True)
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
        print(f"  {refusal}\n  Re-run the preview and copy its apply command.")
        return _finish(write_gate.report(accepted=False, verified=None, reason=refusal))
    result = write_object(library, "collections", key, {"deleted": True}, version)
    if result.status != "accepted":
        return _finish(
            write_gate.report(accepted=False, verified=None, reason=_describe(result))
        )
    still_live = []
    for check_key in [key, *(c.get("key", "") for c in descendants)]:
        back = _read_collection(library, check_key)
        if back is None or not collection_deleted(back):
            still_live.append(check_key)
    descendant_keys = [c.get("key", "") for c in descendants]
    restore = [sys.argv[0], "--restore", key]
    if descendant_keys:
        restore += ["--descendants", ",".join(descendant_keys)]
    if args.library:
        restore += ["--library", args.library]
    print(
        "  To bring it back (Zotero restores non-recursively; the helper "
        "restores the listed descendants):\n    uv run " + shlex.join(restore),
        flush=True,
    )
    return _finish(
        write_gate.report(
            accepted=True,
            verified=not still_live,
            reason=(
                f"read-back shows not in the trash: {', '.join(still_live)}"
                if still_live
                else None
            ),
        )
    )


def restore_collection(args: argparse.Namespace, library: dict) -> int:  # noqa: PLR0911, PLR0912 - one return per outcome; parent, descendants and membership are each checked
    key = args.restore
    envelope = _read_collection(library, key)
    if envelope is None:
        return 1
    data = envelope.get("data") or {}
    version = collection_version(envelope)
    listed = [k.strip() for k in (args.descendants or "").split(",") if k.strip()]
    descendants: dict[str, dict] = {}
    for dkey in listed:
        child = _read_collection(library, dkey)
        if child is None:
            return 1
        descendants[dkey] = child
    ordered = order_by_depth(descendants, key)
    print("=== restore collection ===", flush=True)
    print(f"  key:     {key}", flush=True)
    print(f"  name:    {data.get('name')}", flush=True)
    print(f"  library: {library.get('name')}", flush=True)
    print(f"  items:   {(envelope.get('meta') or {}).get('numItems', '?')}", flush=True)
    print(
        f"  deleted: {'true' if collection_deleted(envelope) else 'false'}", flush=True
    )
    print(f"  version: {version}", flush=True)
    if ordered:
        print("  descendants to restore after it, shallowest first:", flush=True)
        for dkey in ordered:
            cdata = descendants[dkey].get("data") or {}
            print(
                f"    {dkey}  {cdata.get('name')}  deleted="
                f"{'true' if collection_deleted(descendants[dkey]) else 'false'}  "
                f"version {collection_version(descendants[dkey])}",
                flush=True,
            )
    else:
        print(f"  {DESCENDANTS_UNKNOWN}", flush=True)
    if not collection_deleted(envelope) and not ordered:
        print("\n  No change: the collection is not in the trash.", flush=True)
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
        print(f"  {refusal}\n  Re-run the preview and copy its apply command.")
        return _finish(write_gate.report(accepted=False, verified=None, reason=refusal))

    items_before = (envelope.get("meta") or {}).get("numItems")
    result = write_object(library, "collections", key, {"deleted": False}, version)
    if result.status != "accepted":
        return _finish(
            write_gate.report(accepted=False, verified=None, reason=_describe(result))
        )
    not_accepted = []
    for dkey in ordered:
        child_version = collection_version(descendants[dkey])
        child_result = write_object(
            library, "collections", dkey, {"deleted": False}, child_version
        )
        if child_result.status != "accepted":
            not_accepted.append(f"{dkey}: {_describe(child_result)}")
    problems = list(not_accepted)
    for check_key in [key, *ordered]:
        back = _read_collection(library, check_key)
        if back is None or collection_deleted(back):
            problems.append(f"{check_key} still in the trash")
        elif check_key == key:
            items_after = (back.get("meta") or {}).get("numItems")
            print(f"  items:   {items_after} (was {items_before})", flush=True)
            if items_after != items_before:
                problems.append(
                    f"item membership changed: {items_before} -> {items_after}"
                )
    if not ordered:
        print(f"  {DESCENDANTS_UNKNOWN}", flush=True)
    return _finish(
        write_gate.report(
            accepted=True, verified=not problems, reason="; ".join(problems) or None
        )
    )


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.list:
        return list_collection(args.list, args.library)

    cls = "create" if args.create else "modify"
    foreign = write_gate.foreign_expectations(args, cls)
    if foreign:
        parser.error(f"this verb does not take {' '.join(foreign)}")
    required = ["--expect-version"]
    if cls == "create":
        required = ["--expect-library"] + (["--expect-parent"] if args.parent else [])
    missing = write_gate.missing_expectations(args, required)
    if missing:
        parser.error(f"--apply requires {' '.join(missing)} from the preview")

    try:
        require_stock_writes()
    except StockWriteUnavailable as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    probe_api_plus()
    try:
        library = find_library(get_libraries(), args.library)
    except ResolutionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    verb = next(
        handler
        for flag, handler in (
            (args.create, create_collection),
            (args.rename, rename_collection),
            (args.trash, trash_collection),
            (args.restore, restore_collection),
        )
        if flag
    )
    return verb(args, library)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except zotero_auth.AuthorizationError as exc:
        # Zotero answered the authorisation request with a denial or a rate
        # limit. Retrying only re-prompts, so report it and stop.
        sys.exit(str(exc))
