#!/usr/bin/env python3
"""Annotate the passages we cited back onto the source PDF in Zotero.

Given a citation (citekey, page, verbatim quote, optional note), highlight that
passage in the Zotero PDF with the note attached, via the zotero-api-plus
add-highlight endpoint. The batch mode walks every cited passage and annotates
each — re-runnable without duplicating, because every annotation carries a
machine-readable dedup marker the run reads back first.

Primary path is rects (position) mode: the recogniser-driven text mode only
reaches the first 5 pages (Zotero's PDF worker caps getRecognizerData at 5), so
we compute the highlight geometry locally with PyMuPDF — which the plugin
already depends on for rendering — and post the rects. That works on any page.

The pure functional core (marker construction, payload building, response
parsing) is unit-tested in tests/test_bibliography_annotate.py. The HTTP +
PyMuPDF shell is verified live against a running Zotero.

Endpoint contracts read from ~/people/Brian/zotero-api-plus/src/{addon.ts,
utils/highlight.ts,utils/annotations.ts}, not transcribed from documentation.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "pymupdf"]
# ///

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# The stock local API sweep is shared with resolve.py and ingest.py; it imports
# httpx lazily, so the pure core here stays importable without the PEP 723 deps.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zotero_local_api import LibrarySearch, item_citekey, item_library, search_items

# httpx and pymupdf (fitz) are imported lazily inside the shell functions so the
# pure core stays importable without the PEP 723 deps — the unit tests load this
# module and exercise the pure functions directly.

# Dedup marker embedded in every annotation comment. `ax` = annotate. The
# fingerprint identifies the passage independent of spacing/case drift between
# the rendered markdown (where the quote was verified) and the live PDF text
# layer (where it is highlighted).
_MARKER_OPEN = "⟦ax:"
_MARKER_CLOSE = "⟧"


# --- Functional core (pure, unit-tested) ------------------------------------


class HighlightError(Exception):
    """add-highlight / add-note returned a failure.

    `code` is the structured error code from the {ok:false, code, message}
    envelope when the API supplied one (span_not_found, no_text_layer,
    page_beyond_cap, page_beyond_document, ...); None for the plain-text errors
    resolveItemByKey returns (unknown key/library, no PDF attachment).
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ResolveError(Exception):
    """A citekey could not be resolved to a Zotero item with an attached PDF."""


def _normalise_quote(quote: str) -> str:
    return " ".join(quote.lower().split())


def quote_fingerprint(quote: str) -> str:
    """Stable 8-hex-char fingerprint of a passage.

    Normalises case and runs of whitespace first, so the same passage produces
    the same fingerprint whether it came from the rendered markdown or the live
    PDF text layer — the two differ in spacing and line breaks.
    """
    norm = _normalise_quote(quote).encode("utf-8")
    return hashlib.sha1(norm, usedforsecurity=False).hexdigest()[:8]


def build_annotation_comment(*, note: str, citekey: str, page: int, quote: str) -> str:
    """Compose an annotation comment: the human note, the pandoc citation, and a
    machine dedup marker carrying the quote fingerprint.

    The marker (⟦ax:<fp>⟧) lets marker_present recognise a passage already
    annotated on a later run, so the batch mode is idempotent.
    """
    marker = f"{_MARKER_OPEN}{quote_fingerprint(quote)}{_MARKER_CLOSE}"
    citation = f"[@{citekey}, p. {page}] {marker}"
    note = note.strip()
    return f"{note}\n\n{citation}" if note else citation


def marker_present(annotations: list[dict], fingerprint: str) -> bool:
    """True if any existing annotation already carries this passage's marker.

    `annotations` is read-annotations output (note + highlight); both types
    carry the marker in their `comment`, so a passage recorded either as a
    highlight or as a note-fallback counts as already done.
    """
    marker = f"{_MARKER_OPEN}{fingerprint}{_MARKER_CLOSE}"
    return any(marker in (a.get("comment") or "") for a in annotations)


def build_highlight_payload(
    *,
    key: str,
    page: int,
    rects: list[list[float]],
    page_height: float,
    text: str,
    comment: str,
    library_id: int | None = None,
    color: str | None = None,
) -> dict:
    """The rects-mode add-highlight POST body.

    Including `rects` is what selects position (rects) mode server-side
    (addon.ts dispatches on `"rects" in data`). `rects` are PyMuPDF TOP-LEFT
    [x0,y0,x1,y1] in PDF points and `page_height` is the page height; the
    endpoint flips them to Zotero's bottom-left space, so the consumer does no
    coordinate maths.
    """
    payload: dict = {
        "key": key,
        "page": page,
        "rects": rects,
        "pageHeight": page_height,
        "text": text,
        "comment": comment,
    }
    if library_id is not None:
        payload["libraryID"] = library_id
    if color is not None:
        payload["color"] = color
    return payload


def parse_highlight_response(status_code: int, body: str, content_type: str) -> dict:
    """Interpret an add-highlight (or add-note) HTTP response.

    200 returns the parsed JSON ({ok, key, page, rects}). A non-200 carrying the
    structured {ok:false, code, message} envelope raises HighlightError with the
    code; a plain-text error (resolveItemByKey 400/404) raises with code=None.
    """
    if status_code == 200:
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise HighlightError(
                f"add-highlight returned 200 but the body was not JSON "
                f"({content_type}): {body[:200]!r}"
            ) from e
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HighlightError(
            body.strip() or f"add-highlight failed ({status_code})"
        ) from None
    raise HighlightError(data.get("message", body.strip()), code=data.get("code"))


def choose_resolution(candidates: list[dict]) -> tuple[str, int, Path]:
    """Pick the citekey copy that actually has a PDF.

    A paper can exist in several libraries under one citekey, and only some
    copies have the PDF attached (e.g. one citekey can live in both a
    workshop group with no PDF and another group with the PDF). Prefer the
    first candidate in search order whose pdf_paths is non-empty. Pure, so the
    multi-library selection is unit-tested apart from the BBT export I/O that
    fills pdf_paths.
    """
    for c in candidates:
        paths = c.get("pdf_paths") or []
        if paths:
            return c["item_key"], c["library_id"], paths[0]
    libs = ", ".join(repr(c.get("library", "")) for c in candidates) or "(none)"
    raise ResolveError(
        f"no copy of the citekey has a PDF attachment (tried libraries: {libs})"
    )


# --- Imperative shell (HTTP + PyMuPDF) --------------------------------------

RPC_ENDPOINT = "http://localhost:23119/better-bibtex/json-rpc"
PLUS_PROBE = "http://localhost:23119/api/plus"
ADD_HIGHLIGHT_ENDPOINT = "http://localhost:23119/api/plus/add-highlight"
ADD_NOTE_ENDPOINT = "http://localhost:23119/api/plus/add-note"
READ_ANNOTATIONS_ENDPOINT = "http://localhost:23119/api/plus/read-annotations"


def _rpc(method: str, params: list):
    import httpx

    r = httpx.post(
        RPC_ENDPOINT,
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
        timeout=15,
    )
    r.raise_for_status()
    payload = r.json()
    if "error" in payload:
        raise ResolveError(f"{method} failed: {payload['error']}")
    return payload.get("result")


def probe_plus() -> None:
    """Fail fast unless Zotero + zotero-api-plus (with the annotation endpoints)
    are reachable. The annotate path WRITES to the library, so a clear up-front
    error beats a half-applied batch."""
    import httpx

    try:
        banner = httpx.get(PLUS_PROBE, timeout=3).text
    except Exception as e:
        sys.exit(
            f"zotero-api-plus not reachable on {PLUS_PROBE} ({e}).\n"
            "Annotating requires Zotero running with the zotero-api-plus plugin "
            "(the open-pdf/add-note/read-note/add-highlight build)."
        )
    if "Zotero Local API Plus is running" not in banner:
        sys.exit(f"unexpected /api/plus banner: {banner[:200]!r}")
    # The annotation endpoints post-date the base plugin; probe one. A bare GET
    # with no key returns 400 'No item key' when present, 404 when absent.
    probe = httpx.get(READ_ANNOTATIONS_ENDPOINT, timeout=3)
    if probe.status_code == 404:
        sys.exit(
            "this zotero-api-plus build lacks /api/plus/read-annotations.\n"
            "Update the plugin to the build that adds the annotation endpoints."
        )


def resolve_item(citekey: str) -> tuple[str, int, Path]:
    """Resolve a citekey to (item_key, libraryID, pdf_path).

    The same citekey can exist in several libraries. Each stock envelope
    carries the Zotero item key and the library's human name, which
    user.groups maps to the BBT libraryID that item.export needs. Every copy
    is exported and choose_resolution picks the one with a PDF — the same file
    Zotero has attached, so PyMuPDF and Zotero's reader share a coordinate
    basis. Search is Zotero's own quicksearch (zotero_local_api.search_items):
    BBT's item.search errors on every query under Zotero 10 (issue #3587).
    """
    import bbt

    found: LibrarySearch = search_items(citekey)
    matches = [item for item in found.items if item_citekey(item) == citekey]
    if not matches:
        detail = (
            f"search returned {len(found.items)} item(s), none an exact citekey match"
        )
        if found.failed_libraries:
            # This path WRITES to the library, so a miss over a partly
            # unsearched corpus must not read as a confirmed absence.
            unsearched = "; ".join(found.failed_libraries)
            detail += f"; inconclusive, could not search: {unsearched}"
        raise ResolveError(f"no Zotero item with citekey {citekey!r} ({detail})")

    groups = _rpc("user.groups", []) or []
    name_to_id = {g["name"]: g["id"] for g in groups}

    candidates: list[dict] = []
    for item in matches:
        library_name = item_library(item)
        library_id = name_to_id.get(library_name)
        if library_id is None:
            continue  # cannot export without a libraryID; skip this copy
        bibs = _rpc("item.export", [[citekey], "Better BibLaTeX", library_id]) or []
        bib = bibs[0] if isinstance(bibs, list) else bibs
        candidates.append(
            {
                "item_key": item.get("key") or "",
                "library_id": library_id,
                "library": library_name,
                "pdf_paths": bbt.parse_pdf_paths(bib or ""),
            }
        )
    return choose_resolution(candidates)


def existing_annotations(item_key: str, library_id: int | None) -> list[dict]:
    """All annotations (note + highlight) on the item's PDF, for dedup."""
    import httpx

    params: dict = {"key": item_key, "type": "all"}
    if library_id is not None:
        params["libraryID"] = library_id
    r = httpx.get(READ_ANNOTATIONS_ENDPOINT, params=params, timeout=15)
    if r.status_code != 200:
        raise HighlightError(
            f"read-annotations failed ({r.status_code}): {r.text.strip()}"
        )
    return r.json().get("annotations", [])


def highlight_rects(
    pdf_path: Path, page: int, quote: str
) -> tuple[list[list[float]], float]:
    """Locate `quote` on `page` with PyMuPDF, returning TOP-LEFT rects (one or
    more, in PDF points) and the page height. Empty rects => not found (the
    caller falls back to a page-anchored note)."""
    import pymupdf

    with pymupdf.open(pdf_path) as doc:
        pg = doc[page - 1]
        found = pg.search_for(quote)
        rects = [[r.x0, r.y0, r.x1, r.y1] for r in found]
        return rects, pg.rect.height


def post_highlight(payload: dict) -> dict:
    import httpx

    r = httpx.post(ADD_HIGHLIGHT_ENDPOINT, json=payload, timeout=30)
    return parse_highlight_response(
        r.status_code, r.text, r.headers.get("content-type", "")
    )


def post_note(
    item_key: str, page: int, text: str, library_id: int | None, color: str | None
) -> dict:
    import httpx

    payload: dict = {"key": item_key, "page": page, "text": text}
    if library_id is not None:
        payload["libraryID"] = library_id
    if color is not None:
        payload["color"] = color
    r = httpx.post(ADD_NOTE_ENDPOINT, json=payload, timeout=30)
    return parse_highlight_response(
        r.status_code, r.text, r.headers.get("content-type", "")
    )


def annotate_one(
    citekey: str,
    page: int,
    quote: str,
    note: str = "",
    *,
    color: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Annotate one cited passage. Idempotent: a passage already marked (as a
    highlight or a note-fallback) is skipped. A quote PyMuPDF can't locate (OCR
    page / text drift) falls back to a page-anchored note so the citation is
    still recorded."""
    item_key, library_id, pdf_path = resolve_item(citekey)
    fingerprint = quote_fingerprint(quote)
    if marker_present(existing_annotations(item_key, library_id), fingerprint):
        return {"status": "skipped", "citekey": citekey, "page": page}

    comment = build_annotation_comment(
        note=note, citekey=citekey, page=page, quote=quote
    )
    rects, page_height = highlight_rects(pdf_path, page, quote)

    if dry_run:
        return {
            "status": "dry-run",
            "citekey": citekey,
            "page": page,
            "would": "highlight" if rects else "note",
            "rects": rects,
        }

    if rects:
        resp = post_highlight(
            build_highlight_payload(
                key=item_key,
                page=page,
                rects=rects,
                page_height=page_height,
                text=quote,
                comment=comment,
                library_id=library_id,
                color=color,
            )
        )
        return {
            "status": "highlighted",
            "citekey": citekey,
            "page": page,
            "key": resp.get("key"),
        }

    resp = post_note(item_key, page, comment, library_id, color)
    return {
        "status": "noted",
        "citekey": citekey,
        "page": page,
        "key": resp.get("key"),
        "reason": "quote not found in the PDF text layer — placed a page-anchored note",
    }


def _print_result(res: dict) -> None:
    status = res["status"]
    where = f"{res['citekey']} p.{res['page']}"
    if status == "highlighted":
        print(f"  ✓ highlighted {where} (annotation {res['key']})", flush=True)
    elif status == "noted":
        print(
            f"  ◐ noted {where} (annotation {res['key']}) — {res['reason']}", flush=True
        )
    elif status == "skipped":
        print(f"  · skipped {where} (already annotated)", flush=True)
    elif status == "dry-run":
        print(
            f"  ? {where}: would {res['would']} ({len(res['rects'])} rect(s))",
            flush=True,
        )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("citekey", nargs="?", help="Zotero citekey of the cited paper.")
    parser.add_argument(
        "--page", type=int, help="1-based physical PDF page of the quote."
    )
    parser.add_argument("--quote", help="The verbatim quoted passage to highlight.")
    parser.add_argument("--note", default="", help="Note to attach to the highlight.")
    parser.add_argument("--color", help="Highlight colour #rrggbb (default: Zotero's).")
    parser.add_argument(
        "--batch",
        help="JSONL file; each line {citekey, page, quote, note?}. Loops annotate_one.",
    )
    parser.add_argument(
        "--list",
        metavar="CITEKEY",
        help="List existing annotations on a paper and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve + locate the span but write nothing.",
    )
    args = parser.parse_args()

    probe_plus()

    if args.list:
        item_key, library_id, _ = resolve_item(args.list)
        for a in existing_annotations(item_key, library_id):
            print(
                f"  [{a['type']}] p.{a['page']} {a['comment']!r} (key {a['key']})",
                flush=True,
            )
        return 0

    if args.batch:
        results: list[dict] = []
        for raw_line in Path(args.batch).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            item = json.loads(line)
            res = annotate_one(
                item["citekey"],
                int(item["page"]),
                item["quote"],
                item.get("note", ""),
                color=item.get("color") or args.color,
                dry_run=args.dry_run,
            )
            _print_result(res)
            results.append(res)
        counts: dict = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(f"\n=== {counts} ===", flush=True)
        return 0

    if not (args.citekey and args.page and args.quote):
        parser.error("single-passage mode needs citekey, --page and --quote")
    res = annotate_one(
        args.citekey,
        args.page,
        args.quote,
        args.note,
        color=args.color,
        dry_run=args.dry_run,
    )
    _print_result(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
