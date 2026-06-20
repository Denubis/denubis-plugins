#!/usr/bin/env python3
"""Ask a paper to be found. Resolve a Zotero item by ANY key — author, year,
title, date, citekey, or DOI — report the truth about where it lives and its
state, and (by default) render it so it can be asked questions.

This is the front door for "ask a paper a question": it makes *a paper*
available. It is citekey-capable and fully live — resolution queries the
*running* Zotero database via BBT JSON-RPC, never the cached
`.bib` export. That removes both failure modes of the old DOI-only path: the
Crossref dependency (empty-author DOIs, whole journal-DOI classes) and
stale-file ghosts (a paper present in Zotero reported as missing because the
on-disk `.bib` lagged).

For each match it reports the libraries AND collections the paper is in, whether
a PDF is attached and on disk, and whether it has been rendered — and renders it
when it hasn't. An optional library constraint narrows the search.

Endpoint contracts verified live against Zotero 9.0.4 + BBT, not transcribed.
"""

# /// script
# requires-python = ">=3.14"  # uses PEP 758 parenthesis-less `except` (3.14+)
# dependencies = ["httpx"]
# ///

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# httpx is imported lazily inside the shell functions (rpc / probe_zotero /
# crossref_first_author_family) so the pure functional core stays importable
# without the PEP 723 deps — unit tests load this module and exercise pure
# functions directly. This mirrors fetch.py's idiom.

BBT_ENDPOINT = "http://localhost:23119/better-bibtex/json-rpc"
PING_ENDPOINT = "http://localhost:23119/connector/ping"
CONFIG_PATH = Path.home() / ".config" / "denubis-academic-research" / "config.toml"
RENDER_SCRIPT = Path(__file__).resolve().parent / "render.py"

# Regex for auto-classifying a bare positional QUERY argument.
_CITEKEY_RE = re.compile(r"^[a-z]+[A-Z]\w+\d{4}")
_DOI_RE = re.compile(r"^10\.\d+/")


# --- Functional core (pure, unit-tested) ------------------------------------


def _ascii_fold(s: str) -> str:
    """Strip diacritics via NFKD, dropping combining marks. Case preserved.

    BBT item.search matches against an ASCII-folded index, so the correctly
    spelled "Frühwirth" misses the folded "fruhwirth" record while the paper is
    present. Folding both the search token and the matches_query comparison makes
    the accented name and its ASCII form resolve to the same paper. NFKD handles
    the Latin diacritics this corpus carries (ü, é, ñ, ä); the rarer non-composing
    letters (ø, ß) pass through unchanged, which is acceptable here.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def select_citekey_matches(hits: list[dict], citekey: str) -> list[dict]:
    """From BBT item.search hits, return only those whose citekey matches exactly.

    item.search is AND-token fuzzy and returns near-misses; the citekey is the
    one exact key. A citekey can legitimately match in more than one library
    (My Library + a group), so this returns every exact-match hit, not just one.
    """
    return [h for h in hits if h.get("citation-key") == citekey]


def search_tokens(
    *,
    citekey: str | None = None,
    author: str | None = None,
    freeterm: str | None = None,
    title: str | None = None,
) -> list[str]:
    """Every token worth driving a BBT item.search on, in priority order, deduped.

    BBT item.search indexes only the FIRST author surname and is AND-fuzzy, so
    choosing ONE key to search (the old elif chain) silently returned zero
    whenever that key was a co-author (Ghahramani in "Wade, Ghahramani") or a
    title that had drifted — reporting present papers as absent. We instead
    search EVERY supplied key and union the hits in the shell; matches_query then
    applies the strict AND filter. Recall comes from the union, precision from
    the filter. A multi-word title is searched as the whole string: BBT
    AND-matches the words within the single title field, and any title that
    survives matches_query's substring check is, by construction, found by that
    search — so no per-word fallback is needed.
    """
    tokens: list[str] = []

    def add(raw: str | None) -> None:
        tok = (raw or "").strip()
        if not tok:
            return
        if tok not in tokens:
            tokens.append(tok)
        # BBT's index is ASCII-folded, so search the folded form too — otherwise
        # a query carrying diacritics ("Frühwirth") never surfaces the paper.
        folded = _ascii_fold(tok)
        if folded != tok and folded not in tokens:
            tokens.append(folded)

    for raw in (citekey, author, freeterm, title):
        add(raw)
    return tokens


@dataclass(frozen=True)
class Paper:
    """A Zotero item normalised from whichever live API returned it."""

    citekey: str
    doi: str
    title: str
    authors: tuple[str, ...]  # surnames, in document order
    year: int | None
    library: str  # human library name
    library_id: int | None  # the id from the API that produced this record
    collection_keys: tuple[str, ...]


def _year_from_date(date: str | None) -> int | None:
    """Pull a 4-digit year off a Zotero date string ('2017-09', '2017', ...)."""
    if not date:
        return None
    for i in range(len(date) - 3):
        chunk = date[i : i + 4]
        if chunk.isdigit():
            return int(chunk)
    return None


def matches_query(
    paper: Paper,
    *,
    citekey: str | None = None,
    author: str | None = None,
    year: int | str | None = None,
    title: str | None = None,
    doi: str | None = None,
) -> bool:
    """True iff the paper satisfies EVERY supplied constraint (AND).

    Unsupplied keys are ignored. citekey and DOI are exact (DOI case-insensitive),
    author is an exact surname (any creator, case-insensitive), title is a
    case-insensitive substring, year is exact.
    """
    if citekey is not None and paper.citekey != citekey:
        return False
    if doi is not None and paper.doi.lower() != doi.lower():
        return False
    if author is not None:
        # Fold diacritics on both sides so "Frühwirth" and "Fruhwirth" both match.
        wanted = _ascii_fold(author).lower()
        surnames = {_ascii_fold(a).lower() for a in paper.authors}
        # A hyphen-component also matches, so "Malsiner" finds "Malsiner-Walli"
        # and "Frühwirth" finds "Frühwirth-Schnatter" — the partial surname BBT
        # surfaces but the old exact-equality filter dropped. Hyphen only:
        # space-splitting would make "van" match every "van X", and we never do
        # arbitrary substring, so "Veh" never matches "Vehtari".
        components = {part for s in surnames for part in s.split("-")}
        if wanted not in surnames and wanted not in components:
            return False
    if year is not None and paper.year != int(year):
        return False
    if title is None:
        return True
    return _ascii_fold(title).lower() in _ascii_fold(paper.title).lower()


def classify_state(
    *, found: bool, has_pdf: bool, pdf_exists: bool, rendered: bool
) -> str:
    """The paper's place in the pipeline.

    One of: not-in-zotero | no-pdf | ready-to-render | rendered.
    """
    if not found:
        return "not-in-zotero"
    if not (has_pdf and pdf_exists):
        return "no-pdf"
    if not rendered:
        return "ready-to-render"
    return "rendered"


def collection_names(keys, key_to_name: dict[str, str]) -> list[str]:
    """Map collection keys to human names; pass an unknown key through verbatim."""
    return [key_to_name.get(k, k) for k in keys]


def _year_from_issued(issued: dict | None) -> int | None:
    """Extract a 4-digit year from a CSL 'issued' object.

    CSL shape: {"date-parts": [[YYYY, MM, DD], ...]}. The year is the first
    element of the first inner list. Returns None for any missing, empty, or
    non-integer value — never raises.
    """
    if not issued:
        return None
    parts = issued.get("date-parts")
    if not parts:
        return None
    first = parts[0]
    if not first:
        return None
    try:
        return int(first[0])
    except TypeError, ValueError, IndexError:
        return None


def normalize_bbt_hit(hit: dict) -> Paper:
    """Normalise a BBT item.search hit into a Paper.

    BBT item.search hits use CSL field names: 'citation-key' (not 'citationKey'),
    'author' (list of {'family': str, 'given': str}), 'issued' (CSL date object),
    'DOI', 'title', 'library' (the human library NAME string).

    library_id is always None here — search hits carry no numeric ID; resolve
    it later via user.groups. collection_keys is always () — search hits carry
    no collection membership.
    """
    authors = tuple(a["family"] for a in (hit.get("author") or []) if a.get("family"))
    return Paper(
        citekey=hit.get("citation-key", "") or "",
        doi=hit.get("DOI", "") or "",
        title=hit.get("title", "") or "",
        authors=authors,
        year=_year_from_issued(hit.get("issued")),
        library=hit.get("library", "") or "",
        library_id=None,
        collection_keys=(),
    )


# --- Imperative shell (HTTP + filesystem) ------------------------------------


def _classify_query(query: str) -> tuple[str, str]:
    """Return (field, value) for a bare positional query.

    DOI shape (10.NNNN/...) -> ('doi', query)
    Citekey shape (authorWordYear) -> ('citekey', query)
    Anything else -> ('freeterm', query)  [used as BBT search token only]
    """
    if _DOI_RE.match(query):
        return ("doi", query)
    if _CITEKEY_RE.match(query):
        return ("citekey", query)
    return ("freeterm", query)


def load_config() -> dict:
    """Load ~/.config/denubis-academic-research/config.toml (mirrors ingest.py)."""
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


def render_is_present(out_dir: Path) -> bool:
    """True iff papers/<citekey>/ holds a valid render (full.md + parseable meta.json).

    A render is keyed on the PAPER (citekey), not on any one copy's PDF bytes:
    copies of the same citekey across libraries share this one dir, so the paper
    renders once and is never re-rendered or clobbered by another copy. Use
    --force to re-render (e.g. after a PDF genuinely changes).
    """
    meta = out_dir / "meta.json"
    if not (out_dir / "full.md").exists() or not meta.exists():
        return False
    try:
        json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return False
    return True


def rpc(method: str, params: list, timeout: float = 30.0):
    """POST to the BBT JSON-RPC endpoint (mirrors ingest.py)."""
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
    """Confirm Zotero is reachable; exit with a clear message if not.

    Mirrors ingest.py.
    """
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


def crossref_first_author_family(doi: str) -> str | None:
    """DOI -> first-author family name via Crossref (mirrors ingest.py).

    BBT item.search does NOT index the DOI field, so a DOI search returns
    nothing. Crossref gives a name token; we search Zotero with that, then
    filter hits by exact DOI match.
    """
    import httpx  # noqa: PLC0415

    try:
        r = httpx.get(
            f"https://api.crossref.org/works/{doi}",
            headers={
                "User-Agent": (
                    "denubis-bibliography/0.1 (mailto:brian.ballsun-stanton@mq.edu.au)"
                )
            },
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


def search_by_doi(doi: str) -> list[Paper]:
    """Locate Zotero items by DOI via the Crossref fallback.

    Mirrors ingest.py's find_by_doi. Returns all hits whose DOI matches exactly
    (case-insensitive). A DOI can appear in more than one library.
    """
    candidates_seen: set[str] = set()
    papers: list[Paper] = []

    surname = crossref_first_author_family(doi)
    queries: list[str] = []
    if surname:
        queries.append(surname)
    queries.append(doi)
    last_segment = doi.rsplit("/", maxsplit=1)[-1]
    if last_segment not in queries:
        queries.append(last_segment)

    for q in queries:
        try:
            hits = rpc("item.search", [q]) or []
        except Exception:  # noqa: S112
            # Best-effort: a failed query variant must not abort the others.
            continue
        for h in hits:
            key = h.get("citation-key") or ""
            lib = h.get("library") or ""
            dedup_key = f"{key}|{lib}"
            if dedup_key in candidates_seen:
                continue
            candidates_seen.add(dedup_key)
            if (h.get("DOI") or "").lower() == doi.lower():
                papers.append(normalize_bbt_hit(h))
    return papers


def build_library_map() -> dict[str, int]:
    """Call user.groups and return {library_name: bbt_library_id}."""
    groups = rpc("user.groups", []) or []
    return {g["name"]: g["id"] for g in groups}


def enrich_paper(paper: Paper, library_map: dict[str, int]) -> dict:
    """Fetch collections + attachments for one paper; return an enriched info dict.

    collections come from item.collections([[citekey]]), which BBT aggregates by
    citekey (NOT per library copy). pdf_status is one of:
      'present' - a PDF attachment was found on this copy,
      'none'    - the attachment query ran and returned no PDF,
      'unknown' - we could not check (library name didn't resolve to a BBT id, or
                  the RPC failed) -> reported honestly, never collapsed to a
                  confident 'no PDF'.
    """
    # Collections: item.collections([[citekey]]) -> {citekey: [{"name": str, ...}]},
    # aggregated per citekey across libraries, not per-copy.
    try:
        col_result = rpc("item.collections", [[paper.citekey]]) or {}
        col_entries = col_result.get(paper.citekey) or []
        cols = [c["name"] for c in col_entries if c.get("name")]
    except Exception:
        cols = []

    # PDF: item.attachments(citekey, libraryID). Resolve the library NAME to a BBT
    # id; an unresolved name (collision/unexpected) or a failed RPC is 'unknown',
    # never a false 'no PDF'.
    library_id = library_map.get(paper.library)
    pdf_path: Path | None = None
    if library_id is None:
        pdf_status = "unknown"
    else:
        try:
            attachments = rpc("item.attachments", [paper.citekey, library_id]) or []
            pdf_paths = [
                Path(a["path"])
                for a in attachments
                if a.get("path", "").lower().endswith(".pdf")
            ]
            pdf_path = pdf_paths[0] if pdf_paths else None
            pdf_status = "present" if pdf_path is not None else "none"
        except Exception:
            pdf_status = "unknown"

    pdf_exists = pdf_path is not None and pdf_path.is_file()
    return {
        "paper": paper,
        "collections": cols,
        "pdf_path": pdf_path,
        "pdf_exists": pdf_exists,
        "pdf_status": pdf_status,
        "rendered": False,  # filled in by check_rendered once we know out_dir
        "out_dir": None,
    }


def check_rendered(info: dict, papers_dir: Path, *, force: bool = False) -> dict:
    """Fill in rendered + out_dir. 'rendered' is per-citekey: True iff the render
    dir is present and valid (full.md + meta.json), independent of which copy's
    PDF this is. --force treats it as not-rendered so it re-renders."""
    paper = info["paper"]
    out_dir = papers_dir / paper.citekey
    rendered = (not force) and render_is_present(out_dir)
    return {**info, "rendered": rendered, "out_dir": out_dir}


def _render_cmd(pdf: Path, out_dir: Path, *, allow_mocr: bool = False) -> list[str]:
    """Build the uv command that renders via render.py.

    render.py has NO PEP 723 header — it requires its render deps passed on the
    command line (SKILL.md: `uv run --with pymupdf4llm --with docling --with
    easyocr python render.py ...`). Plain `uv run render.py` would die on
    ModuleNotFoundError, so the --with flags are not optional.
    """
    cmd = [
        "uv",
        "run",
        "--with",
        "pymupdf4llm",
        "--with",
        "docling",
        "--with",
        "easyocr",
        "python",
        str(RENDER_SCRIPT),
        str(pdf),
        str(out_dir),
    ]
    if allow_mocr:
        cmd.append("--allow-mocr")
    return cmd


def render_via_subprocess(pdf: Path, out_dir: Path, *, allow_mocr: bool = False) -> str:
    """Render a PDF by delegating to render.py as a subprocess.

    Keeps resolve.py's PEP 723 header httpx-only — heavy render deps (pymupdf4llm,
    docling, easyocr) load only in render.py's own uv environment.

    Returns one of: 'rendered' | 'needs-mocr' | 'failed'.
    Exit codes from render.py: 0 = success, 3 = NeedsMocr, 1 = hard failure.
    """
    cmd = _render_cmd(pdf, out_dir, allow_mocr=allow_mocr)
    proc = subprocess.run(cmd, check=False)  # returncode inspected below
    if proc.returncode == 0:
        return "rendered"
    if proc.returncode == 3:
        return "needs-mocr"
    return "failed"


def print_no_match(
    tokens: list[str], *, doi: str | None, search_errors: list[str]
) -> None:
    """Report a no-match honestly: a no-match here is NOT proof of absence.

    item.search is AND-fuzzy and (live-verified) indexes only the first author
    surname, so a query keyed on a co-author, or on a title that has drifted from
    how it is filed, returns zero while the paper is present. State that, show what
    was searched, and point at the move that works — rather than asserting the
    paper is absent, which is the overclaim this resolver exists to avoid.
    """
    print("No matches surfaced in Zotero for this query.", flush=True)
    searched = ", ".join(repr(t) for t in tokens) or "(nothing searchable)"
    print(f"  searched: {searched}", flush=True)
    if search_errors:
        print(
            f"  WARNING: {len(search_errors)} search call(s) errored "
            f"({'; '.join(search_errors)}).",
            flush=True,
        )
        print(
            "  Zotero/BBT may be unreachable, so this result is inconclusive, "
            "not a confirmed absence.",
            flush=True,
        )
    if doi:
        print(
            "  DOI path: BBT cannot search the DOI field, so this used a Crossref\n"
            "  surname lookup; some journal and chapter DOIs return no author there,\n"
            "  leaving the search nothing to query. This is NOT proof of absence —\n"
            "  retry with --author or a distinctive --title word.",
            flush=True,
        )
    else:
        print(
            "  A no-match is NOT proof of absence: item.search is AND-fuzzy and\n"
            "  indexes only the FIRST author surname, so a query keyed on a\n"
            "  co-author, or on a title filed differently than typed, returns zero\n"
            "  while the paper is present. Retry with the first author's surname,\n"
            "  or a distinctive single word from the title (e.g. --title BayesLCA).",
            flush=True,
        )


def print_match(info: dict, state: str) -> None:
    """Print a truthful per-match block to stdout."""
    p = info["paper"]
    print(f"\n=== {p.citekey} ===", flush=True)
    print(f"  title:      {p.title or '(no title)'}", flush=True)
    print(f"  authors:    {', '.join(p.authors) or '(none)'}", flush=True)
    print(f"  year:       {p.year or '(unknown)'}", flush=True)
    print(f"  doi:        {p.doi or '(none)'}", flush=True)
    print(f"  library:    {p.library}", flush=True)
    cols = info["collections"]
    print(f"  collections: {', '.join(cols) if cols else '(none)'}", flush=True)
    pdf = info["pdf_path"]
    status = info.get("pdf_status", "none")
    if status == "unknown":
        print(
            "  pdf:        (could not check — library name unresolved "
            "or attachment lookup failed)",
            flush=True,
        )
    elif pdf is not None:
        exists = info["pdf_exists"]
        print(
            f"  pdf:        {pdf}  [{'EXISTS' if exists else 'MISSING ON DISK'}]",
            flush=True,
        )
    else:
        print("  pdf:        (no PDF attachment)", flush=True)
    print(f"  state:      {state}", flush=True)
    # Only advertise a render dir when a render actually exists there.
    if state == "rendered" and info.get("out_dir"):
        print(f"  render dir: {info['out_dir']}", flush=True)


# main() is the CLI orchestrator (parse → search → filter → enrich → render); the
# shell has no unit tests, so it is not split here — that is a separate refactor.
def main() -> int:  # noqa: PLR0912, PLR0915
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "query",
        nargs="?",
        help=(
            "Optional bare query, auto-classified: DOI shape (10.NNNN/...) -> --doi; "
            "citekey shape (authorWordYear) -> --citekey; anything else -> free search "
            "term (used as the BBT search token only, not a strict filter)."
        ),
    )
    parser.add_argument("--citekey", help="Exact citekey to resolve.")
    parser.add_argument(
        "--author",
        help="Author surname: case-insensitive, matches a hyphen-component "
        "(Malsiner finds Malsiner-Walli) and folds diacritics (Frühwirth = Fruhwirth).",
    )
    parser.add_argument("--year", type=int, help="Publication year (exact).")
    parser.add_argument(
        "--date",
        help="Date string to extract a year from (e.g. '2017-09'). "
        "--year wins if both given.",
    )
    parser.add_argument(
        "--title",
        help="Title substring (case-insensitive, diacritic-insensitive).",
    )
    parser.add_argument("--doi", help="DOI (exact, case-insensitive).")
    parser.add_argument(
        "--library",
        help="Restrict matches to this library name (case-insensitive exact match).",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Report state but do not render ready-to-render papers.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-render even if a render already exists for this citekey.",
    )
    parser.add_argument(
        "--allow-mocr",
        action="store_true",
        help=(
            "Escalate to dots.mocr (GPU) if the render cascade cannot produce a "
            "usable render. Passed through to render.py. Requires [mocr] in "
            "config.toml."
        ),
    )
    args = parser.parse_args()

    # --- Classify the bare positional query (if given) -----------------------
    freeterm: str | None = None
    if args.query:
        field, value = _classify_query(args.query)
        if field == "doi" and not args.doi:
            args.doi = value
        elif field == "citekey" and not args.citekey:
            args.citekey = value
        else:
            freeterm = value  # used as BBT search token, not a strict filter

    # --- Resolve year from --date when --year not supplied -------------------
    effective_year: int | None = args.year
    if effective_year is None and args.date:
        effective_year = _year_from_date(args.date)

    # --- Validate: need at least one searchable key --------------------------
    # year/date alone can't drive a BBT search.
    searchable = bool(args.citekey or args.author or args.title or args.doi or freeterm)
    if not searchable:
        parser.error(
            "At least one searchable key is required: "
            "--citekey, --author, --title, --doi, or a bare QUERY. "
            "(--year/--date alone cannot drive a Zotero search.)"
        )

    # --- Go live -------------------------------------------------------------
    cfg = load_config()
    papers_dir = cfg["zettelkasten_root"] / "papers"
    probe_zotero()

    # Build library_map once (needed for attachments).
    library_map = build_library_map()

    # --- Search --------------------------------------------------------------
    # Recall comes from searching EVERY supplied key and unioning the hits;
    # precision comes from matches_query below. The old code searched a single
    # key chosen by priority (citekey > author > freeterm > title), which
    # silently returned zero whenever that key was a co-author (BBT item.search
    # indexes only the first author surname) or a title that had drifted — the
    # bug that reported present papers as absent.
    papers: list[Paper]
    tokens: list[str]
    search_errors: list[str] = []
    if args.doi:
        # BBT can't search the DOI field — use the Crossref-surname fallback.
        tokens = [args.doi]
        papers = search_by_doi(args.doi)
    else:
        tokens = search_tokens(
            citekey=args.citekey,
            author=args.author,
            freeterm=freeterm,
            title=args.title,
        )
        seen: set[tuple[str, str]] = set()
        raw_hits: list[dict] = []
        for tok in tokens:
            try:
                hits = rpc("item.search", [tok]) or []
            except Exception as e:
                # One token's RPC failing must not sink the whole resolve — the
                # other tokens may still find the paper. Record it so the
                # no-match message can flag an inconclusive (vs absent) result.
                search_errors.append(f"{tok!r}: {e}")
                continue
            for h in hits:
                dedup = (h.get("citation-key") or "", h.get("library") or "")
                if dedup in seen:
                    continue
                seen.add(dedup)
                raw_hits.append(h)

        # A citekey query keeps only exact matches (search is fuzzy near-miss).
        if args.citekey:
            raw_hits = select_citekey_matches(raw_hits, args.citekey)

        papers = [normalize_bbt_hit(h) for h in raw_hits]

    # --- Filter by matches_query (AND of all supplied strict keys) -----------
    papers = [
        p
        for p in papers
        if matches_query(
            p,
            citekey=args.citekey,
            author=args.author,
            year=effective_year,
            title=args.title,
            doi=args.doi,
        )
    ]

    # --- Optional library constraint -----------------------------------------
    if args.library:
        lib_lower = args.library.lower()
        papers = [p for p in papers if p.library.lower() == lib_lower]

    if not papers:
        print_no_match(tokens, doi=args.doi, search_errors=search_errors)
        return 1

    # --- Enrich, classify, optionally render ---------------------------------
    render_errors = 0
    for paper in papers:
        info = enrich_paper(paper, library_map)
        info = check_rendered(info, papers_dir, force=args.force)

        state = classify_state(
            found=True,
            has_pdf=info["pdf_status"] == "present",
            pdf_exists=info["pdf_exists"],
            rendered=info["rendered"],
        )
        # An unknown PDF status (unresolved library / failed lookup) must not
        # masquerade as a confident 'no-pdf'.
        if info["pdf_status"] == "unknown":
            state = "pdf-unknown"

        # Auto-render when ready and not suppressed.
        if state == "ready-to-render" and not args.no_render:
            pdf = info["pdf_path"]
            out_dir = info["out_dir"]
            assert pdf is not None and out_dir is not None  # noqa: S101
            print(f"\n  [rendering {paper.citekey} via render.py ...]", flush=True)
            render_result = render_via_subprocess(
                pdf, out_dir, allow_mocr=args.allow_mocr
            )
            if render_result == "rendered":
                state = "rendered"
                info = {**info, "rendered": True}
            elif render_result == "needs-mocr":
                state = "needs-ocr-escalation"
                print(
                    "  NEEDS MOCR: render cascade exhausted. "
                    "Re-run with --allow-mocr to escalate to GPU OCR.",
                    flush=True,
                )
                render_errors += 1
            else:
                print("  render FAILED — see render.py output above.", flush=True)
                render_errors += 1

        print_match(info, state)

    return 1 if render_errors else 0


if __name__ == "__main__":
    sys.exit(main())
