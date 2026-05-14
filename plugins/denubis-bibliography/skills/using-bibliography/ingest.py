#!/usr/bin/env python3
"""Ingest a set of DOIs from Zotero: locate via BBT JSON-RPC, render the
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
# dependencies = ["pymupdf4llm", "httpx", "docling"]
# ///

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from renderer import render_pdf_with_fallback  # noqa: E402

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
    return {"zettelkasten_root": zk}


def rpc(method: str, params: list, timeout: float = 30.0):
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
    try:
        r = httpx.get(PING_ENDPOINT, timeout=3)
        if "Zotero is running" not in r.text:
            sys.exit(f"Zotero ping returned unexpected body: {r.text[:200]}")
    except Exception as e:
        sys.exit(
            f"Zotero local API not reachable on {PING_ENDPOINT} ({e}).\n"
            "Start Zotero (e.g. `flatpak run org.zotero.Zotero`) and retry."
        )


def crossref_first_author_family(doi: str) -> str | None:
    """Resolve DOI to the first author's family name via Crossref (free, no auth).

    BBT item.search does NOT index the DOI field, so we cannot search Zotero
    by DOI directly. Crossref gives us a name token to search Zotero with.
    """
    try:
        r = httpx.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "denubis-bibliography/0.1 (mailto:brian.ballsun-stanton@mq.edu.au)"},
            timeout=10,
        )
        r.raise_for_status()
        msg = r.json().get("message", {})
        authors = msg.get("author", [])
        if authors and "family" in authors[0]:
            return authors[0]["family"]
    except Exception:
        return None
    return None


def find_by_doi(doi: str) -> dict | None:
    """Locate an item in Zotero by DOI.

    BBT item.search does not index DOIs, so we resolve the DOI to an author
    surname via Crossref, then search Zotero by that surname, then filter
    results by exact DOI match. Falls back to direct DOI search (which usually
    returns nothing) if Crossref is unreachable.
    """
    candidates_seen: set[str] = set()

    surname = crossref_first_author_family(doi)
    queries: list[str] = []
    if surname:
        queries.append(surname)
    queries.append(doi)
    last_segment = doi.split("/")[-1]
    if last_segment not in queries:
        queries.append(last_segment)

    for q in queries:
        try:
            hits = rpc("item.search", [q]) or []
        except Exception:
            continue
        for h in hits:
            key = h.get("citation-key") or h.get("id") or ""
            if key in candidates_seen:
                continue
            candidates_seen.add(key)
            if (h.get("DOI") or "").lower() == doi.lower():
                return h
    return None


def parse_pdf_paths(bib: str) -> list[Path]:
    """Extract PDF file paths from a BibLaTeX entry's `file = {...}` field.

    BBT format: `<label>:<path>:<mime>` separated by `;`. We pick entries
    whose path ends `.pdf`, regardless of label or mime.
    """
    m = re.search(r"file\s*=\s*\{([^}]*)\}", bib)
    if not m:
        return []
    paths: list[Path] = []
    for entry in m.group(1).split(";"):
        parts = entry.strip().split(":")
        if len(parts) < 2:
            continue
        path_str = parts[1].strip() if len(parts) >= 3 else ":".join(parts[1:]).strip()
        if path_str.lower().endswith(".pdf"):
            paths.append(Path(path_str))
    return paths


def resolve_pdf(item: dict, library_map: dict[str, int]) -> Path | None:
    citekey = item["citation-key"]
    library_name = item["library"]
    library_id = library_map.get(library_name)
    if library_id is None:
        raise RuntimeError(
            f"Library {library_name!r} not in user.groups response. "
            f"Known: {list(library_map)}"
        )
    bibs = rpc("item.export", [[citekey], "Better BibLaTeX", library_id])
    bib = bibs[0] if isinstance(bibs, list) else bibs
    paths = parse_pdf_paths(bib)
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


def render_pdf(pdf: Path, out_dir: Path) -> dict:
    """Render PDF -> markdown with auto-escalation (pymupdf4llm -> docling -> +OCR).

    Returns the meta dict written to meta.json. Raises RuntimeError if every
    renderer's output fails the quality check.
    """
    return render_pdf_with_fallback(pdf, out_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dois", nargs="*", help="DOIs to ingest. Use '-' to read from stdin.")
    parser.add_argument("--force", action="store_true", help="Re-render even if cached output is current.")
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

    successes = 0
    failures = 0
    skipped = 0

    for doi in dois:
        print(f"\n=== {doi} ===", flush=True)
        try:
            item = find_by_doi(doi)
            if item is None:
                print("  NOT FOUND in Zotero", flush=True)
                failures += 1
                continue
            citekey = item["citation-key"]
            library = item["library"]
            print(f"  cite key: {citekey}", flush=True)
            print(f"  library:  {library}", flush=True)
            pdf = resolve_pdf(item, library_map)
            if pdf is None:
                print("  no PDF attachment in this item", flush=True)
                failures += 1
                continue
            if not pdf.is_file():
                print(f"  PDF path on disk missing: {pdf}", flush=True)
                failures += 1
                continue
            out = papers_dir / citekey
            if not args.force and current_render_matches(out, pdf):
                print(f"  cache current — skipped (use --force to re-render)", flush=True)
                skipped += 1
                continue
            meta = render_pdf(pdf, out)
            label = meta["renderer"] + (" +OCR" if meta.get("ocr") else "")
            print(f"  rendered {meta['page_count']} pages via {label} → {out}", flush=True)
            successes += 1
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            failures += 1

    print(f"\n=== summary: {successes} rendered, {skipped} cached, {failures} failed ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
