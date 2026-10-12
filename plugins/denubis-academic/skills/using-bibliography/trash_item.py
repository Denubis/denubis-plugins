#!/usr/bin/env python3
"""Move one Zotero item or attachment to the trash, or restore it.

Usage (preview, writes nothing):
    uv run trash_item.py --key ATTACH01 [--library "<library>"]
    uv run trash_item.py --key ATTACH01 --restore

Usage (apply, exactly the command the preview printed):
    uv run trash_item.py --key ATTACH01 --apply --expect-version 12

Delete means trash (ADR 0029): the helper PATCHes `{"deleted": true}` through
Zotero 10's stock local API and never sends `DELETE`, which erases the object
and its storage permanently. Emptying the trash stays a human action in
Zotero. Trashing a parent takes its children with it in Zotero's own
semantics; the preview counts them. Restoring brings an item's children back.
A child's trash state comes through its parent (Zotero's `isInTrash()`), and
the stock API reports only the child's own `deleted` flag, so the helper reads
the parent: `--restore` on a child whose parent is in the trash writes nothing
and prints the parent's restore command instead.

Modify class (design 2026-10-12): the preview reads the object and prints its
version; `--apply --expect-version N` re-reads, refuses `changed since
preview`, PATCHes with `If-Unmodified-Since-Version: N`, reads the object back
with the trash included and reports `accepted` and `verified` separately.
Zotero 10 only. The library name is resolved through zotero-api-plus.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import write_gate
import zotero_auth
from copy_item import ResolutionError, find_library, get_libraries, probe_api_plus
from zotero_local_api import (
    LibraryQueryError,
    StockWriteUnavailable,
    get_item_children,
    item_in_trash,
    read_object,
    require_stock_writes,
    write_object,
)

# Where Zotero keeps attachment files on this machine; the size shown in a
# preview is read from here when the file exists. An observation, not a
# lookup through Zotero, so a missing file is reported as such.
STORAGE_ROOT = Path.home() / "Zotero" / "storage"


# --- Functional core (pure) ------------------------------------------------------


def same_as_relations(data: dict) -> list[str]:
    """The `owl:sameAs` URIs in an item's relations (a str or a list)."""
    value = (data.get("relations") or {}).get("owl:sameAs")
    if not value:
        return []
    return [value] if isinstance(value, str) else list(value)


def storage_path(key: str, filename: str, root: Path) -> Path | None:
    """The attachment file under Zotero's storage directory, if present."""
    path = root / key / filename
    return path if filename and path.is_file() else None


def in_trash_via_parent(parent: dict | None) -> bool:
    """True when the parent envelope is in the trash.

    Zotero's own `isInTrash()` counts a child as trashed when its parent is,
    whatever the child's own `deleted` flag says; the stock API only reports
    the child's own flag, so the parent has to be read.
    """
    return parent is not None and item_in_trash(parent)


def deleted_label(item: dict, parent: dict | None) -> str:
    """The `deleted:` preview value, naming the parent when it matters."""
    own = item_in_trash(item)
    parent_key = (parent or {}).get("key", "?")
    if not in_trash_via_parent(parent):
        return "true" if own else "false"
    if own:
        return f"true (parent {parent_key} is in the trash too)"
    return f"false (in the trash through parent {parent_key})"


# --- Imperative shell -------------------------------------------------------


def read_parent(library: dict, item: dict) -> dict | None:
    """The parent envelope for a child item, or None for a top-level item.

    Raises LibraryQueryError when the parent exists but cannot be read.
    """
    parent_key = (item.get("data") or {}).get("parentItem")
    if not parent_key:
        return None
    return read_object(library, "items", parent_key, include_trashed=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--key", required=True, help="the item or attachment key")
    parser.add_argument(
        "--library",
        help="library holding the item: name, numeric groupID, or 'My Library'",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="bring the object back from the trash instead of trashing it",
    )
    write_gate.add_gate_arguments(parser, "modify")
    return parser


def print_preview(
    library: dict, item: dict, parent: dict | None, *, restore: bool
) -> None:
    data = item.get("data") or {}
    kind = data.get("itemType", "?")
    print(f"=== {'restore' if restore else 'trash'} {item.get('key')} ===", flush=True)
    print(f"  type:     {kind}", flush=True)
    print(f"  title:    {data.get('title') or '(untitled)'}", flush=True)
    if data.get("citationKey"):
        print(f"  citekey:  {data['citationKey']}", flush=True)
    print(f"  library:  {library.get('name')}", flush=True)
    parent_key = data.get("parentItem")
    if parent_key:
        parent_title = ((parent or {}).get("data") or {}).get("title") or "(untitled)"
        print(f"  parent:   {parent_key}  {parent_title}", flush=True)
    if kind == "attachment":
        filename = data.get("filename") or ""
        path = storage_path(item.get("key", ""), filename, STORAGE_ROOT)
        size = f"{path.stat().st_size} bytes at {path}" if path else "file not found"
        print(f"  file:     {filename or '(no filename)'}  ({size})", flush=True)
    for uri in same_as_relations(data):
        print(f"  relation: owl:sameAs {uri}", flush=True)
    try:
        children = get_item_children(library, item.get("key", ""))
    except LibraryQueryError as error:
        print(f"  children: (could not list: {error})", flush=True)
    else:
        note = " (they follow it into the trash)" if children and not restore else ""
        print(f"  children: {len(children)}{note}", flush=True)
    print(f"  deleted:  {deleted_label(item, parent)}", flush=True)
    print(f"  version:  {item.get('version', data.get('version'))}", flush=True)


def refuse_restore_under_trashed_parent(
    item: dict, parent: dict, library_arg: str | None
) -> tuple[str, int]:
    """Explain that the parent owns the trash state; the write is not expanded."""
    parent_key = parent.get("key", "?")
    command = [sys.argv[0], "--key", parent_key, "--restore"]
    if library_arg:
        command += ["--library", library_arg]
    afterwards = (
        "then re-run this restore, because this object's own flag is set too"
        if item_in_trash(item)
        else "and this object comes back with it"
    )
    print(
        f"\n  Restoring this object alone would leave it in the trash: Zotero "
        f"counts a child as trashed while its parent {parent_key} is. Restore the "
        f"parent first, {afterwards}:\n    uv run {shlex.join(command)}",
        flush=True,
    )
    return write_gate.report(
        accepted=False,
        verified=None,
        reason=f"in the trash through parent {parent_key}",
    )


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
    try:
        library = find_library(get_libraries(), args.library)
    except ResolutionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    try:
        item = read_object(library, "items", args.key)
        parent = read_parent(library, item)
    except LibraryQueryError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    via_parent = in_trash_via_parent(parent)

    if not args.apply or (args.restore and via_parent):
        print_preview(library, item, parent, restore=args.restore)
    if args.restore and via_parent and parent is not None:
        line, code = refuse_restore_under_trashed_parent(item, parent, args.library)
        print(line, flush=True)
        return code
    if not args.apply:
        return preview_outcome(item, parent, restore=args.restore)

    version = item.get("version", (item.get("data") or {}).get("version"))
    refusal = write_gate.state_refusal(
        {"version": args.expect_version}, {"version": version}
    )
    if refusal:
        line, code = write_gate.report(accepted=False, verified=None, reason=refusal)
        print(f"  {refusal}\n  Re-run the preview and copy its apply command.")
        print(line, flush=True)
        return code

    line, code = apply_change(library, args.key, version, restore=args.restore)
    print(line, flush=True)
    return code


def preview_outcome(item: dict, parent: dict | None, *, restore: bool) -> int:
    """Print the no-change notice or the exact apply command; never writes."""
    want_deleted = not restore
    via_parent = in_trash_via_parent(parent)
    if (item_in_trash(item) or via_parent) == want_deleted:
        state = "not in the trash"
        if via_parent:
            parent_key = (parent or {}).get("key", "?")
            state = f"already in the trash through its parent {parent_key}"
        elif want_deleted:
            state = "already in the trash"
        print(f"\n  No change: the object is {state}. Nothing to apply.", flush=True)
        return 0
    version = item.get("version", (item.get("data") or {}).get("version"))
    print(
        "\nPreview only (no write). To apply exactly this change:\n  "
        + write_gate.format_apply_command(sys.argv, {"version": version}),
        flush=True,
    )
    return 0


def apply_change(
    library: dict, key: str, version: int, *, restore: bool
) -> tuple[str, int]:
    """PATCH `deleted`, read back with the trash included, and report."""
    want_deleted = not restore
    result = write_object(library, "items", key, {"deleted": want_deleted}, version)
    if result.status != "accepted":
        detail = result.body
        if result.status == "conflict" and result.current:
            cur = result.current
            detail = (
                f"conflict (412): Zotero now holds version {cur.get('version')}, "
                f"deleted={(cur.get('data') or {}).get('deleted', False)}"
            )
        return write_gate.report(
            accepted=False, verified=None, reason=f"{result.status}: {detail}"
        )

    try:
        back = read_object(library, "items", key, include_trashed=True)
        parent_back = read_parent(library, back) if restore else None
    except LibraryQueryError as error:
        return write_gate.report(
            accepted=True, verified=False, reason=f"read-back failed: {error}"
        )
    now_deleted = item_in_trash(back) or in_trash_via_parent(parent_back)
    verified = now_deleted == want_deleted
    reason = None if verified else f"read-back shows deleted={now_deleted}"
    if not verified and parent_back is not None and in_trash_via_parent(parent_back):
        reason = f"read-back shows the parent {parent_back.get('key')} in the trash"
    print(
        f"  Zotero accepted the write (version {result.version}); "
        f"read-back deleted={now_deleted}",
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
