#!/usr/bin/env python3
"""Fix an item's metadata in place via the zotero-api-plus local API
(POST /api/plus/update-item), behind a diff you approve before anything writes.

Zotero's own local API is read-only: PATCH on an item returns 501. This is the
write side, and it is a *patch*: only the fields you name are touched. That
matters because the obvious primitive, Zotero.Item.fromJSON(), is a replace —
it clears every field you did not send, and a payload without a "collections"
key removes the item from its collections (item.js:5684-5694). None of that
happens here.

The diff is Zotero's, not this script's. The endpoint applies your change to a
detached Zotero.Item.clone(), asks Zotero what the clone became, and reports the
difference. So an item type change shows what it really does: setType() migrates
values through base-field mappings and special-cases book <-> bookSection
(item.js:470-524), so going book -> bookSection moves the title into bookTitle
rather than losing it, while a field with no counterpart on the new type is
genuinely cleared. Both show up in the diff, under separate headings, because
one is a consequence and the other is what you asked for.

Usage (find the item's key — read-only):
    uv run update_item.py --find "Ethnography and Virtual Worlds"

Usage (dry run: show the diff, write nothing — this is the default):
    uv run update_item.py --key ABCD1234 --type bookSection --set pages=53-82

Usage (apply, gated behind --apply):
    uv run update_item.py --key ABCD1234 --type bookSection --set pages=53-82 \
        --author "Boellstorff, Tom" --author "Nardi, Bonnie" --apply

Changes:
  --type TYPE           new Zotero item type (e.g. bookSection).
  --set FIELD=VALUE     set one field. Repeatable. The first '=' splits.
  --clear FIELD         clear one field. Repeatable.
  --author "Last, First"  add an author, in order. Repeatable. A value with no
                        comma is treated as a single-field name (an organisation).
  --creator TYPE="Last, First"  a creator of some other type (editor, translator).

  --author and --creator REPLACE the whole creator list, because Zotero stores
  creators as an ordered list rather than a set. Pass every creator you want, not
  just the new ones. The diff shows both sides so this is visible before it lands.

Nothing writes without --apply. The gate is boolean on the wire and the endpoint
rejects the string "false" rather than coercing it.

Endpoint contract read from ~/people/Brian/zotero-api-plus/src/addon.ts and
utils/update-item.ts, not transcribed from documentation.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import json
import sys

# Zotero 10 authenticates every local-API write in the base class each endpoint
# inherits, and the dry run is a POST too (the endpoint computes the diff on a
# clone), so BOTH the preview and the apply need credentials. zotero_auth.post
# attaches them; on Zotero 7-9 there is no server ID and nothing changes.
import zotero_auth

# Library resolution is shared with copy_item.py rather than reimplemented: the
# name -> libraryID mapping is the step that used to be hand-rolled and broke.
from copy_item import ResolutionError, find_library, get_libraries, find_items

UPDATE_ITEM_ENDPOINT = "http://localhost:23119/api/plus/update-item"
STOCK_API = "http://localhost:23119/api"

# Shown in place of an empty value, so "set to nothing" is never mistaken for
# "unchanged" when reading the diff.
EMPTY = "(empty)"


# --- Functional core (pure, unit-tested) ------------------------------------


class UpdateError(Exception):
    """update-item returned an error or an unparseable response."""


def parse_field_assignment(spec: str) -> tuple[str, str]:
    """Split "pages=53-82" into ("pages", "53-82").

    Splits on the FIRST '=' only, so a value may contain '=' (URLs and DOIs do).
    An empty value is legal and clears the field, matching --clear.
    """
    name, sep, value = spec.partition("=")
    if not sep:
        raise ValueError(f"--set expects FIELD=VALUE, got {spec!r}")
    name = name.strip()
    if not name:
        raise ValueError(f"--set has an empty field name: {spec!r}")
    return name, value.strip()


def parse_creator_name(value: str) -> dict[str, str]:
    """Turn a citation-style name into the endpoint's creator shape.

    "Boellstorff, Tom" is a two-field name. A value with no comma is a
    single-field name, which is how Zotero stores organisations.
    """
    value = value.strip()
    if not value:
        raise ValueError("creator name is empty")
    if "," not in value:
        return {"name": value}
    last, _, first = value.partition(",")
    last, first = last.strip(), first.strip()
    if not last:
        raise ValueError(f"creator name has no surname: {value!r}")
    return {"firstName": first, "lastName": last}


def parse_creator_spec(spec: str) -> dict[str, str]:
    """Split 'editor=Nardi, Bonnie' into a creator dict with its type."""
    creator_type, sep, name = spec.partition("=")
    if not sep:
        raise ValueError(f"--creator expects TYPE=NAME, got {spec!r}")
    creator_type = creator_type.strip()
    if not creator_type:
        raise ValueError(f"--creator has an empty type: {spec!r}")
    return {"creatorType": creator_type, **parse_creator_name(name)}


def build_update_payload(
    key: str,
    library_id: int | None,
    item_type: str | None,
    fields: dict[str, str],
    creators: list[dict] | None,
    apply: bool,
) -> dict:
    """Assemble the request body, omitting every channel not being changed.

    Omission matters: the endpoint patches only what it is sent, so an absent
    "creators" key leaves the creator list alone while an empty list clears it.
    """
    payload: dict = {"key": key}
    if library_id is not None:
        payload["libraryID"] = library_id
    if item_type is not None:
        payload["itemType"] = item_type
    if fields:
        payload["fields"] = fields
    if creators is not None:
        payload["creators"] = creators
    # Sent as a real boolean. The endpoint rejects the string "false".
    payload["apply"] = apply
    return payload


def parse_update_response(status: int, body: str, content_type: str) -> dict:
    """Return the parsed body for a 200, or raise UpdateError with the reason.

    Structured failures are {ok:false, code, message}; item resolution failures
    come back as text/plain with no code (addon.ts resolveItemByKey).
    """
    if status == 200:
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise UpdateError(f"update-item returned unparseable JSON: {body!r}") from exc

    if "json" in content_type:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            raise UpdateError(f"HTTP {status}: {body!r}") from None
        code = parsed.get("code", "unknown")
        message = parsed.get("message", "")
        raise UpdateError(f"HTTP {status} [{code}]: {message}")

    raise UpdateError(f"HTTP {status}: {body.strip()}")


def _display(value: str) -> str:
    return value if value else EMPTY


def render_change(change: dict, width: int) -> str:
    """One line of the diff: field, current value, proposed value."""
    if change.get("kind") == "creators":
        return "  creators\n" + _render_creator_lists(change)
    field = change.get("field", "?")
    return (
        f"  {field:<{width}}  {_display(change.get('from', ''))}"
        f"  ->  {_display(change.get('to', ''))}"
    )


def _format_creator(creator: dict) -> str:
    if "name" in creator:
        who = creator["name"]
    else:
        first = creator.get("firstName", "")
        last = creator.get("lastName", "")
        who = f"{last}, {first}".strip().rstrip(",")
    return f"{who} ({creator.get('creatorType', '?')})"


def _render_creator_lists(change: dict) -> str:
    before = change.get("from") or []
    after = change.get("to") or []
    lines = []
    for creator in before:
        lines.append(f"    - {_format_creator(creator)}")
    for creator in after:
        lines.append(f"    + {_format_creator(creator)}")
    return "\n".join(lines) if lines else "    (none)"


def _field_width(changes: list[dict]) -> int:
    widths = [len(c.get("field", "")) for c in changes if c.get("kind") == "field"]
    return max(widths) if widths else 0


def render_diff(response: dict) -> str:
    """The human-readable diff that the --apply gate exists to protect.

    Collateral is reported under its own heading because it is Zotero's doing
    rather than the caller's, and a field cleared as a side effect of a type
    change is exactly the thing someone approving a change needs to see.
    """
    lines: list[str] = []
    key = response.get("key", "?")
    lines.append(f"Item {key} (libraryID {response.get('libraryID', '?')})")

    if not response.get("hasChanges"):
        lines.append("")
        lines.append("  No change: the item already holds these values.")
        return "\n".join(lines)

    type_change = response.get("typeChange")
    if type_change:
        lines.append("")
        lines.append("  Item type")
        lines.append(f"    {type_change.get('from')}  ->  {type_change.get('to')}")

    collateral = response.get("collateral") or []
    if collateral:
        width = _field_width(collateral)
        lines.append("")
        lines.append(
            "  Consequences of that type change (Zotero's, not requested):"
        )
        for change in collateral:
            lines.append(render_change(change, width))

    requested = response.get("requested") or []
    if requested:
        width = _field_width(requested)
        lines.append("")
        lines.append("  Requested:")
        for change in requested:
            lines.append(render_change(change, width))

    return "\n".join(lines)


def summarise_items(api_items: list[dict]) -> list[dict]:
    """Reduce stock-API item JSON to the triage columns.

    The stock local API returns Zotero Web API v3 shape, so the metadata sits
    under "data". Creators are counted rather than listed because the question
    at triage time is "which of these has none".
    """
    rows = []
    for entry in api_items:
        data = entry.get("data") or {}
        creators = data.get("creators") or []
        rows.append(
            {
                "key": data.get("key") or entry.get("key") or "",
                "itemType": data.get("itemType", ""),
                "creators": len(creators),
                "title": data.get("title", ""),
                "publicationTitle": data.get("publicationTitle", ""),
            }
        )
    return rows


def render_item_table(rows: list[dict]) -> str:
    """A fixed-width triage table. Zero creators is called out, not left to be
    inferred from a 0 in a column."""
    if not rows:
        return "(no items)"
    type_width = max(len(r["itemType"]) for r in rows)
    lines = []
    for row in rows:
        flag = "  NO AUTHOR" if row["creators"] == 0 else ""
        title = row["title"] or "(untitled)"
        if len(title) > 64:
            title = title[:61] + "..."
        lines.append(
            f"  {row['key']}  {row['itemType']:<{type_width}}  {title}{flag}"
        )
    return "\n".join(lines)


def cleared_fields(response: dict) -> list[str]:
    """Fields the change empties, across both collateral and requested.

    Surfaced separately because a clear is the one outcome that loses data, and
    in the collateral section it is a loss nobody asked for.
    """
    lost = []
    for section in ("collateral", "requested"):
        for change in response.get(section) or []:
            if (
                change.get("kind") == "field"
                and change.get("from")
                and not change.get("to")
            ):
                lost.append(change["field"])
    return lost


# --- Imperative shell -------------------------------------------------------


def get_collection_items(library: dict, collection_key: str) -> list[dict]:
    """Top-level items of one collection, via Zotero's own read-only local API.

    Paginated to the end rather than capped, so a long collection is never
    silently truncated into a partial triage.
    """
    import httpx

    if library.get("type") == "user":
        base = f"{STOCK_API}/users/0"
    else:
        base = f"{STOCK_API}/groups/{library['groupID']}"
    url = f"{base}/collections/{collection_key}/items/top"

    items: list[dict] = []
    start, limit = 0, 100
    while True:
        try:
            reply = httpx.get(
                url,
                params={"format": "json", "limit": limit, "start": start},
                timeout=30.0,
            )
            reply.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpdateError(f"cannot list collection items: {exc}") from exc
        page = reply.json()
        items.extend(page)
        if len(page) < limit:
            return items
        start += limit


def update_item(payload: dict) -> dict:
    import httpx

    try:
        reply = zotero_auth.post(UPDATE_ITEM_ENDPOINT, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        raise UpdateError(
            f"cannot reach update-item at {UPDATE_ITEM_ENDPOINT}: {exc}. "
            "Is Zotero running with zotero-api-plus >= 0.6.0 installed?"
        ) from exc
    return parse_update_response(
        reply.status_code, reply.text, reply.headers.get("content-type", "")
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Patch a Zotero item's metadata behind a diff you approve.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--find", metavar="QUERY", help="search for an item key")
    parser.add_argument(
        "--list",
        dest="list_collection",
        metavar="COLLECTION",
        help="list a collection's top-level items for triage (read-only)",
    )
    parser.add_argument("--key", help="the Zotero item key to update")
    parser.add_argument(
        "--library",
        help="library holding the item: name, numeric groupID, or 'My Library'",
    )
    parser.add_argument("--type", dest="item_type", help="new Zotero item type")
    parser.add_argument(
        "--set", action="append", default=[], metavar="FIELD=VALUE",
        help="set a field (repeatable)",
    )
    parser.add_argument(
        "--clear", action="append", default=[], metavar="FIELD",
        help="clear a field (repeatable)",
    )
    parser.add_argument(
        "--author", action="append", default=[], metavar="'Last, First'",
        help="add an author, in order (repeatable); replaces the creator list",
    )
    parser.add_argument(
        "--creator", action="append", default=[], metavar="TYPE='Last, First'",
        help="add a non-author creator (repeatable); replaces the creator list",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="write the change. Without this nothing is written.",
    )
    parser.add_argument("--json", action="store_true", help="print the raw response")
    return parser


def collect_changes(args: argparse.Namespace) -> tuple[dict[str, str], list[dict] | None]:
    """Turn the CLI's change flags into the two payload channels."""
    fields: dict[str, str] = {}
    for spec in args.set:
        name, value = parse_field_assignment(spec)
        fields[name] = value
    for name in args.clear:
        name = name.strip()
        if not name:
            raise ValueError("--clear expects a field name")
        fields[name] = ""

    creators: list[dict] | None = None
    if args.author or args.creator:
        creators = [
            {"creatorType": "author", **parse_creator_name(value)}
            for value in args.author
        ]
        creators.extend(parse_creator_spec(spec) for spec in args.creator)
    return fields, creators


def main() -> int:
    args = build_arg_parser().parse_args()

    if args.find:
        for hit in find_items(args.find):
            print(
                f"{hit.get('key')}  {hit.get('library')}  {hit.get('title', '')}",
                flush=True,
            )
        return 0

    if args.list_collection:
        # find_collection is copy_item.py's, so an ambiguous name fails the same
        # way here as it does there rather than silently picking one.
        from copy_item import find_collection

        try:
            library = find_library(get_libraries(), args.library)
            _, collection_key = find_collection(library, args.list_collection)
        except ResolutionError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        if collection_key is None:
            print("Error: --list needs a collection name.", file=sys.stderr)
            return 2

        try:
            rows = summarise_items(get_collection_items(library, collection_key))
        except UpdateError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(
            f"{args.list_collection} in {library.get('name')} "
            f"(libraryID {library.get('libraryID')}): {len(rows)} top-level items\n",
            flush=True,
        )
        print(render_item_table(rows), flush=True)
        return 0

    if not args.key:
        print("Error: --key is required (or use --find).", file=sys.stderr)
        return 2

    try:
        fields, creators = collect_changes(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.item_type is None and not fields and creators is None:
        print(
            "Error: nothing to change. Pass --type, --set, --clear, --author "
            "or --creator.",
            file=sys.stderr,
        )
        return 2

    library_id = None
    if args.library:
        try:
            library_id = find_library(get_libraries(), args.library)["libraryID"]
        except ResolutionError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    payload = build_update_payload(
        key=args.key,
        library_id=library_id,
        item_type=args.item_type,
        fields=fields,
        creators=creators,
        apply=args.apply,
    )

    try:
        response = update_item(payload)
    except UpdateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(response, indent=2), flush=True)
        return 0

    print(render_diff(response), flush=True)

    lost = cleared_fields(response)
    if lost:
        print(
            f"\n  Cleared by this change: {', '.join(lost)}",
            flush=True,
        )

    print("", flush=True)
    if response.get("applied"):
        print("  APPLIED. The item has been written.", flush=True)
    elif response.get("hasChanges"):
        print(
            "  Nothing has been written. Re-run with --apply to write it.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except zotero_auth.AuthorizationError as exc:
        # Zotero answered the authorisation request with a denial or a rate
        # limit. Retrying only re-prompts, so report it and stop.
        sys.exit(str(exc))
