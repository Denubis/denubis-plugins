#!/usr/bin/env python3
"""Ingest a set of DOIs from Zotero: locate each by DOI field through the stock
local API, export the attachment path through Better BibTeX, and render the
attached PDFs to per-page markdown under <zettelkasten_root>/papers/<citekey>/.

Usage:
    uv run ingest.py 10.1111/jels.12413 10.1145/1273445.1273458 ...
    cat dois.txt | uv run ingest.py -

Reads config from ~/.config/denubis-academic-research/config.toml. Halts with a
clear error if the config is missing or Zotero is not reachable.

Per the using-bibliography SKILL.md and ~/zettelkasten/AGENTS.md:
  - Reads only from Zotero. Never fetches papers from the internet.
  - Skips items missing a PDF attachment with a warning, not a fabrication.
  - Renders deterministically — re-running on the same PDF produces the same
    output. Use --force to re-render even if the cached render is current.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf4llm", "httpx", "docling", "easyocr"]
# ///

import argparse
import hashlib
import json
import sys
import tomllib
from contextlib import nullcontext
from pathlib import Path

# httpx is imported lazily inside the shell functions (rpc / probe_zotero) so
# this module stays importable without the PEP 723 deps, which is what lets the
# unit tests load it. Mirrors resolve.py's idiom.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bbt import parse_attachment_paths
from renderer import NeedsMocr, mocr_server, render_attachment
from zotero_local_api import (
    LibrarySearch,
    item_citekey,
    item_library,
    search_doi_items,
    warn_unsearched_libraries,
)

CONFIG_PATH = Path.home() / ".config" / "denubis-academic-research" / "config.toml"
BBT_ENDPOINT = "http://localhost:23119/better-bibtex/json-rpc"
PING_ENDPOINT = "http://localhost:23119/connector/ping"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(
            f"Config missing: {CONFIG_PATH}\n"
            "Create it with at minimum:\n"
            '    zettelkasten_root = "~/zettelkasten"'
        )
    with CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    zk = Path(cfg["zettelkasten_root"]).expanduser()
    if not zk.is_dir():
        sys.exit(
            f"zettelkasten_root does not exist on disk: {zk}\n"
            "Create the directory first; this script will not create it silently."
        )
    result: dict = {"zettelkasten_root": zk}
    mocr = cfg.get("mocr")
    if isinstance(mocr, dict) and mocr.get("repo"):
        result["mocr"] = {
            "repo": Path(mocr["repo"]).expanduser(),
            "port": int(mocr.get("port", 8000)),
            "startup_timeout": float(mocr.get("startup_timeout", 300)),
        }
    return result


def rpc(method: str, params: list, timeout: float = 30.0):
    import httpx  # noqa: PLC0415

    r = httpx.post(
        BBT_ENDPOINT,
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
        timeout=timeout,
    )
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"])
    return d.get("result")


def probe_zotero() -> None:
    import httpx  # noqa: PLC0415

    try:
        r = httpx.get(PING_ENDPOINT, timeout=3)
        if "Zotero is running" not in r.text:
            sys.exit(f"Zotero ping returned unexpected body: {r.text[:200]}")
    except Exception as e:
        sys.exit(
            f"Zotero local API not reachable on {PING_ENDPOINT} ({e}).\n"
            "Start Zotero (e.g. `flatpak run org.zotero.Zotero`) and retry."
        )


def find_by_doi(doi: str) -> dict | None:
    """Locate an item in Zotero by exact DOI field; return its stock envelope.

    The stock local API is the only search that reaches the DOI field
    (`qmode=fields`, see zotero_local_api), and its envelope already carries
    the citekey and library name the rest of this script needs, so the first
    exact match is returned as-is. Better BibTeX is reached only later, for
    the export that carries the attachment path: its `item.search` errors on
    every query under Zotero 10 (BBT issue #3587) and never indexed DOI.

    No Crossref round trip. The old chain resolved the DOI to a first-author
    surname and searched that, which returned nothing whenever Crossref carried
    no author (Wiley chapter DOIs such as 10.1002/<book>.chN) and reported
    papers that ARE in Zotero as absent.

    A library that could not be searched is reported on stderr: an empty
    result over a partly unsearched corpus is inconclusive, not the
    "NOT FOUND" the caller prints.
    """
    found: LibrarySearch = search_doi_items(doi)
    warn_unsearched_libraries(found)
    want = doi.strip().lower()
    for item in found.items:
        data = item.get("data") or {}
        if (data.get("DOI") or "").strip().lower() == want:
            return item
    return None


def resolve_pdf(item: dict, library_map: dict[str, int]) -> Path | None:
    citekey = item_citekey(item)
    library_name = item_library(item)
    library_id = library_map.get(library_name)
    if library_id is None:
        raise RuntimeError(
            f"Library {library_name!r} not in user.groups response. "
            f"Known: {list(library_map)}"
        )
    bibs = rpc("item.export", [[citekey], "Better BibLaTeX", library_id])
    bib = bibs[0] if isinstance(bibs, list) else bibs
    paths = parse_attachment_paths(bib)
    return paths[0] if paths else None


def current_render_matches(out_dir: Path, pdf: Path) -> bool:
    meta = out_dir / "meta.json"
    if not (out_dir / "full.md").exists() or not meta.exists():
        return False
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return False
    expected = hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]
    return m.get("sha256_prefix") == expected


def render_pdf(
    pdf: Path, out_dir: Path, *, allow_mocr: bool = False, mocr_session=None
) -> dict:
    """Render an attachment; PDFs escalate through OCR, snapshots use HTML text.

    Returns the meta dict written to meta.json. Raises NeedsMocr if the cascade
    is exhausted and mocr is not enabled; RuntimeError if a render genuinely
    fails (including mocr).
    """
    return render_attachment(
        pdf, out_dir, allow_mocr=allow_mocr, mocr_session=mocr_session
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dois", nargs="*", help="DOIs to ingest. Use '-' to read from stdin."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-render even if cached output is current.",
    )
    parser.add_argument(
        "--allow-mocr",
        action="store_true",
        help="Permit GPU escalation to dots.mocr when the cascade cannot produce "
        "a usable render. Starts the vLLM server once and stops it after. "
        "Requires a [mocr] section in config.toml.",
    )
    args = parser.parse_args()

    if args.dois == ["-"]:
        dois = [line.strip() for line in sys.stdin if line.strip()]
    else:
        dois = args.dois
    if not dois:
        parser.print_help()
        return 2

    cfg = load_config()
    papers_dir = cfg["zettelkasten_root"] / "papers"

    probe_zotero()

    try:
        groups = rpc("user.groups", [])
    except Exception as e:
        sys.exit(f"user.groups failed: {e}")
    library_map = {g["name"]: g["id"] for g in groups}

    mocr_cfg = cfg.get("mocr")
    if args.allow_mocr and not mocr_cfg:
        print(
            "  --allow-mocr given but [mocr] is not configured in config.toml; "
            "escalation unavailable.",
            flush=True,
        )
    if args.allow_mocr and mocr_cfg:
        mocr_ctx = mocr_server(
            mocr_cfg["repo"],
            port=mocr_cfg["port"],
            startup_timeout=mocr_cfg["startup_timeout"],
        )
    else:
        mocr_ctx = nullcontext(None)

    successes = 0
    failures = 0
    skipped = 0

    with mocr_ctx as mocr_session:
        for doi in dois:
            print(f"\n=== {doi} ===", flush=True)
            try:
                item = find_by_doi(doi)
                if item is None:
                    print("  NOT FOUND in Zotero", flush=True)
                    failures += 1
                    continue
                citekey = item_citekey(item)
                library = item_library(item)
                print(f"  cite key: {citekey}", flush=True)
                print(f"  library:  {library}", flush=True)
                pdf = resolve_pdf(item, library_map)
                if pdf is None:
                    print(
                        "  no PDF or HTML snapshot attachment in this item", flush=True
                    )
                    failures += 1
                    continue
                if not pdf.is_file():
                    print(f"  PDF path on disk missing: {pdf}", flush=True)
                    failures += 1
                    continue
                out = papers_dir / citekey
                if not args.force and current_render_matches(out, pdf):
                    print(
                        "  cache current — skipped (use --force to re-render)",
                        flush=True,
                    )
                    skipped += 1
                    continue
                meta = render_pdf(
                    pdf, out, allow_mocr=args.allow_mocr, mocr_session=mocr_session
                )
                label = meta["renderer"] + (" +OCR" if meta.get("ocr") else "")
                print(
                    f"  rendered {meta['page_count']} pages via {label} → {out}",
                    flush=True,
                )
                successes += 1
            except NeedsMocr as e:
                print(f"  NEEDS MOCR: {e}", flush=True)
                failures += 1
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                failures += 1

    print(
        f"\n=== summary: {successes} rendered, {skipped} cached, {failures} failed ==="
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
