#!/usr/bin/env python3
"""Register a Better BibTeX "Keep updated" auto-export for one collection.

Usage (preview, writes nothing):
    uv run register_export.py --collection "My Library/Sage SRM Guide" \\
        --path /absolute/project/references.bib [--translator "Better BibLaTeX"]

Usage (apply, exactly the command the preview printed):
    ... --apply --expect-collection KEY [--replace]

Register class (design 2026-10-12): the preview resolves the library and the
collection path segment by segment through zotero-api-plus `/api/plus/libraries`
(a missing segment is an error; this helper never lets BBT create a
collection), prints the key, translator, absolute path, whether a file exists
there with its size, mtime and sha256, `registration state: unknown` with the
`autoexport.add` semantics, and the apply command. Apply re-resolves, refuses
`target changed`, and calls BBT's `autoexport.add` over JSON-RPC with the
NUMERIC absolute collection path `/<libraryID>/<name>/<subname>`: BBT's parser
(`content/collection.ts`) requires a leading slash and matches an all-digit
first segment against libraryID or groupID and a non-numeric one against the
library name, so the numeric form is the unambiguous one; the CLI's
"My Library/..." string never reaches BBT.

Contract 3: three observations are reported separately and none is inferred
from another:

  accepted    BBT returned the expected collection key (anything else, or a
              BBT error, is printed verbatim and reported `not accepted`);
  completion  `observed` when zotero-api-plus is present, `run-autoexport`
              answered `triggered`, and the file's modification time advanced
              past the trigger within 30 s; otherwise `not observed` with the
              reason (zotero-api-plus itself never reports export success);
  content     `satisfied` when the file parses as a bibliography and holds one
              citekey from the collection's listing; else `not satisfied`.

The final line is `accepted; completion <state>; content <state>; verified`
only when both observations are positive; any other combination exits 1.
The previewed size and hash are printed beside the new ones as an observation,
never as the verdict (a correct repeat export can write identical bytes).

`autoexport.add` semantics (BBT 9.0.71, read 2026-10-12): registers an enabled
collection export, reschedules an existing one at the same path and translator
with its settings untouched, errors when the path is registered to a different
collection or translator unless `replace` is true, cannot register a
library-level export, and has no list or remove counterpart. Zotero 10 only,
for uniformity with the other write helpers.
"""

# /// script
# requires-python = ">=3.14"  # imports resolve.py, which uses PEP 758 except clauses
# dependencies = ["httpx", "bibtexparser>=2.0.0b9"]
# ///

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import write_gate
import zotero_auth
from copy_item import ResolutionError, find_library, get_libraries, probe_api_plus
from resolve import check_bib, classify_autoexport_response, post_run_autoexport, rpc
from zotero_local_api import (
    LibraryQueryError,
    StockWriteUnavailable,
    get_collection_items,
    item_citekey,
    item_in_trash,
    require_stock_writes,
    select_parent_items,
)

DEFAULT_TRANSLATOR = "Better BibLaTeX"
COMPLETION_TIMEOUT = 30.0
POLL_INTERVAL = 1.0

# Injected clocks so the completion poll is instant under test.
now = time.time
sleep = time.sleep


# --- Functional core (pure, unit-tested) ------------------------------------


def parse_collection_spec(spec: str) -> tuple[str, list[str]]:
    """Split "<library>/<name>/<subname>" into the library spec and the path."""
    parts = [part.strip() for part in spec.split("/")]
    if len(parts) < 2 or not all(parts):
        raise ValueError(
            f"--collection expects '<library>/<collection>[/<subcollection>...]', "
            f"got {spec!r}"
        )
    return parts[0], parts[1:]


def resolve_collection_path(library: dict, names: list[str]) -> list[tuple[str, str]]:
    """Resolve each segment under the previous one; (name, key) per level.

    A segment that does not exist is an error: the helper never lets BBT
    create a collection on its way to registering an export.
    """
    out: list[tuple[str, str]] = []
    parent: str | None = None
    collections = library.get("collections", [])
    for name in names:
        matches = [
            c
            for c in collections
            if (c.get("name") or "").lower() == name.lower()
            and (c.get("parentKey") or None) == parent
        ]
        if not matches:
            where = (
                f"under {parent}"
                if parent
                else f"at the top of {library.get('name')!r}"
            )
            raise ResolutionError(f"Missing collection {name!r} {where}")
        if len(matches) > 1:
            raise ResolutionError(
                f"Collection name {name!r} is ambiguous "
                f"({[m.get('key') for m in matches]})"
            )
        parent = matches[0].get("key")
        out.append((matches[0].get("name") or name, parent or ""))
    return out


def bbt_collection_path(library_id: int, names: list[str]) -> str:
    """BBT's absolute collection path, numeric library form."""
    return "/" + "/".join([str(library_id), *names])


def describe_file(path: Path) -> dict | None:
    """Size, mtime and sha256 prefix of the file at `path`, or None."""
    if not path.is_file():
        return None
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return {"size": stat.st_size, "mtime": stat.st_mtime, "sha256": digest}


def _stamp(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def collection_citekey(items: list[dict]) -> str | None:
    """One citekey from the listing to look for in the export: the first live
    parent item that carries one."""
    for item in select_parent_items(items):
        if item_in_trash(item):
            continue
        citekey = item_citekey(item)
        if citekey:
            return citekey
    return None


# --- Imperative shell -------------------------------------------------------


def observe_completion(path: Path, trigger_time: float) -> tuple[bool, str]:
    """(observed, reason): trigger the registered export and wait for the
    file's mtime to advance past `trigger_time`."""
    reply = post_run_autoexport(str(path))
    if reply is None:
        return False, "no zotero-api-plus"
    outcome = classify_autoexport_response(*reply)
    if outcome.kind != "triggered":
        return False, f"trigger refused: {outcome.kind}"
    deadline = now() + COMPLETION_TIMEOUT
    while True:
        described = describe_file(path)
        if described and described["mtime"] > trigger_time:
            return True, f"mtime {_stamp(described['mtime'])} after the trigger"
        if now() >= deadline:
            return False, f"no modification seen within {COMPLETION_TIMEOUT:.0f} s"
        sleep(POLL_INTERVAL)


def check_content(path: Path, citekey: str | None) -> tuple[bool, str]:
    """(satisfied, reason): the file parses and holds `citekey`."""
    if citekey is None:
        return False, "no live item with a citekey in the collection to look for"
    if not path.is_file():
        return False, f"no file at {path}"
    result = check_bib(path.read_text(encoding="utf-8"), citekey)
    if result.citeable:
        return (
            True,
            f"{citekey} present in a well-formed bib ({result.entry_count} entries)",
        )
    if not result.well_formed:
        return (
            False,
            f"{result.failed_count} malformed block(s); {citekey} not citeable",
        )
    return False, f"{citekey} absent ({result.entry_count} entries)"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--collection",
        required=True,
        metavar="'<library>/<collection>[/<sub>]'",
        help="the collection to export, as a path from the library name",
    )
    parser.add_argument(
        "--path", required=True, metavar="FILE.bib", help="absolute output path"
    )
    parser.add_argument(
        "--translator",
        default=DEFAULT_TRANSLATOR,
        help=f"BBT translator name (default {DEFAULT_TRANSLATOR!r})",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="let BBT re-point a path registered to another collection or translator",
    )
    write_gate.add_gate_arguments(parser, "register")
    return parser


def _print_preview(
    args: argparse.Namespace,
    library: dict,
    path_segments: list[tuple[str, str]],
    out: Path,
) -> dict | None:
    key = path_segments[-1][1]
    described = describe_file(out)
    print("=== register auto-export ===", flush=True)
    print(
        f"  collection: {' / '.join(n for n, _k in path_segments)} ({key}) "
        f"in {library.get('name')} (libraryID {library.get('libraryID')})",
        flush=True,
    )
    print(f"  translator: {args.translator}", flush=True)
    print(f"  path:       {out}", flush=True)
    if described:
        stamp = _stamp(described["mtime"])
        print(
            f"  file:       {described['size']} bytes, mtime {stamp}, "
            f"sha256 {described['sha256']}",
            flush=True,
        )
    else:
        print("  file:       no file at that path yet", flush=True)
    print(
        "  registration state: unknown (BBT has no listing; autoexport.add registers "
        "a new export, reschedules an existing one at the same path and translator "
        "with its settings untouched, and errors if the path belongs to another "
        "collection or translator unless --replace)",
        flush=True,
    )
    print(
        "  removal:    manual; no helper can take a registration back. Delete it in "
        "Zotero under Settings > Better BibTeX > Automatic export",
        flush=True,
    )
    return described


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    missing = write_gate.missing_expectations(args, ["--expect-collection"])
    if missing:
        parser.error(f"--apply requires {' '.join(missing)} from the preview")
    out = Path(args.path)
    if not out.is_absolute():
        parser.error(f"--path must be absolute, got {args.path!r}")
    try:
        library_spec, names = parse_collection_spec(args.collection)
    except ValueError as error:
        parser.error(str(error))

    try:
        require_stock_writes()
    except StockWriteUnavailable as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    probe_api_plus()
    try:
        library = find_library(get_libraries(), library_spec)
        segments = resolve_collection_path(library, names)
    except ResolutionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    key = segments[-1][1]
    previewed = _print_preview(args, library, segments, out)

    if not args.apply:
        print(
            "\nPreview only (no registration). To apply exactly this change:\n  "
            + write_gate.format_apply_command(sys.argv, {"collection": key}),
            flush=True,
        )
        return 0

    refusal = write_gate.state_refusal(
        {"collection": args.expect_collection}, {"collection": key}
    )
    if refusal:
        print(f"  {refusal}\n  Re-run the preview and copy its apply command.")
        line, code = write_gate.report(accepted=False, verified=None, reason=refusal)
        print(line, flush=True)
        return code

    return apply_registration(args, library, segments, out, previewed)


def apply_registration(
    args: argparse.Namespace,
    library: dict,
    segments: list[tuple[str, str]],
    out: Path,
    previewed: dict | None,
) -> int:
    """Register through BBT, then report acceptance, completion and content."""
    key = segments[-1][1]
    bbt_path = bbt_collection_path(library.get("libraryID"), [n for n, _k in segments])
    trigger_time = now()
    try:
        result = rpc(
            "autoexport.add", [bbt_path, args.translator, str(out), {}, args.replace]
        )
    except RuntimeError as error:
        line, code = write_gate.report(
            accepted=False, verified=None, reason=f"autoexport.add error: {error}"
        )
        print(line, flush=True)
        return code
    returned_key = result.get("key") if isinstance(result, dict) else None
    if returned_key != key:
        line, code = write_gate.report(
            accepted=False,
            verified=None,
            reason=f"autoexport.add returned {result!r}, expected key {key}",
        )
        print(line, flush=True)
        return code
    print(f"  accepted: autoexport.add returned {result}", flush=True)

    observed, why = observe_completion(out, trigger_time)
    print(
        f"  completion {'observed' if observed else 'not observed'}: {why}", flush=True
    )
    try:
        citekey = collection_citekey(get_collection_items(library, key))
    except LibraryQueryError as error:
        citekey = None
        print(f"  could not list the collection for a citekey: {error}", flush=True)
    satisfied, detail = check_content(out, citekey)
    print(
        f"  content {'satisfied' if satisfied else 'not satisfied'}: {detail}",
        flush=True,
    )
    described = describe_file(out)
    if previewed or described:
        before = (
            f"{previewed['size']} bytes, sha256 {previewed['sha256']}"
            if previewed
            else "no file"
        )
        after = (
            f"{described['size']} bytes, sha256 {described['sha256']}"
            if described
            else "no file"
        )
        print(f"  file before: {before}; after: {after} (observation only)", flush=True)

    verified = observed and satisfied
    print(
        f"accepted; completion {'observed' if observed else 'not observed'}; "
        f"content {'satisfied' if satisfied else 'not satisfied'}; "
        f"{'verified' if verified else 'not verified'}",
        flush=True,
    )
    return 0 if verified else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except zotero_auth.AuthorizationError as exc:
        # Zotero answered the authorisation request with a denial or a rate
        # limit. Retrying only re-prompts, so report it and stop.
        sys.exit(str(exc))
