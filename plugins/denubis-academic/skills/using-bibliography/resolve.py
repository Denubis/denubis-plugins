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

Exit codes: 0 the paper resolved (rendered or ready); 1 genuinely absent or an
error; 2 no exact citekey match but NEAR matches were surfaced — re-run with the
real key shown (a near match is never rendered).

Endpoint contracts verified live against Zotero 9.0.4 + BBT, not transcribed.
"""

# /// script
# requires-python = ">=3.14"  # uses PEP 758 parenthesis-less `except` (3.14+)
# dependencies = ["httpx", "bibtexparser>=2.0.0b9"]  # v2 (beta) for failed_blocks
# ///

from __future__ import annotations

import argparse
import difflib
import json
import logging
import re
import subprocess
import sys
import time
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
# zotero-api-plus >= 0.4.0 forces a registered BBT auto-export to run on demand.
RUN_AUTOEXPORT_ENDPOINT = "http://localhost:23119/api/plus/run-autoexport"
CONFIG_PATH = Path.home() / ".config" / "denubis-academic-research" / "config.toml"
RENDER_SCRIPT = Path(__file__).resolve().parent / "render.py"

# bibtexparser logs each malformed/truncated block to its own logger. During
# polling we deliberately read mid-write (briefly truncated) files, so silence
# that expected noise process-wide, once. getLogger works whether or not
# bibtexparser is importable, so this stays safe without the PEP 723 deps.
logging.getLogger("bibtexparser").setLevel(logging.CRITICAL)

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


# Trailing disambiguator: BBT breaks a citekey collision by appending a/b/...
# after the 4-digit year (chengGenerativeAIRequirements2026a).
_DISAMBIGUATOR_RE = re.compile(r"([0-9]{4})[a-z]+$")
# Leading author component: lowercase surname, possibly hyphenated, before the
# first capitalised title word (malsiner-walliModel... -> "malsiner-walli").
_CITEKEY_AUTHOR_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*")
_CITEKEY_KIND_RANK = {"exact": 0, "variant": 1, "prefix": 2, "fuzzy": 3}


def citekey_base(ck: str) -> str:
    """The citekey without BBT's trailing disambiguation suffix.

    BBT appends a/b/... after the year to break a citekey collision, so
    'chengGenerativeAIRequirements2026' (what a human types) and '...2026a' (what
    BBT stored) share a base. A key with no 4-digit year is returned unchanged.
    """
    return _DISAMBIGUATOR_RE.sub(r"\1", ck)


def citekey_author(ck: str) -> str:
    """The leading author component of a BBT citekey (lowercase, may be hyphenated).

    Used to widen search recall: a mid-string typo in the title portion of a
    citekey still surfaces the neighbourhood when we also search the surname.
    """
    m = _CITEKEY_AUTHOR_RE.match(ck)
    return m.group(0) if m else ""


def classify_citekey(
    query: str, candidate: str, *, fuzzy_threshold: float = 0.85
) -> tuple[str, float]:
    """Classify a candidate citekey against the query. Returns (kind, score).

    kind, in decreasing confidence:
      exact   - byte-identical (1.0); the ONLY render-eligible kind.
      variant - same base, differing only by disambiguation suffix (…2026 vs
                …2026a, or sibling …a vs …b): the missing-suffix bug and the
                duplicate signal.
      prefix  - one key is a prefix of the other (a query truncated before year).
      fuzzy   - difflib similarity of the bases ≥ fuzzy_threshold (a typo).
      none    - below threshold; not a candidate.
    """
    if query == candidate:
        return ("exact", 1.0)
    qb, cb = citekey_base(query), citekey_base(candidate)
    if qb == cb:
        return ("variant", 0.98)
    if candidate.startswith(query) or query.startswith(candidate):
        return ("prefix", 0.95)
    ratio = difflib.SequenceMatcher(None, qb, cb).ratio()
    if ratio >= fuzzy_threshold:
        return ("fuzzy", ratio)
    return ("none", ratio)


@dataclass(frozen=True)
class ScoredHit:
    """A BBT item.search hit tagged with how its citekey matched the query."""

    hit: dict
    kind: str
    score: float


def _candidate_sort_key(s: ScoredHit) -> tuple[int, float, str]:
    """Kind confidence, then score descending, then citekey for stable output."""
    return (_CITEKEY_KIND_RANK[s.kind], -s.score, s.hit.get("citation-key") or "")


def rank_citekey_candidates(
    hits: list[dict], query: str, *, fuzzy_threshold: float = 0.85
) -> list[ScoredHit]:
    """Classify every hit's citekey against query, drop non-candidates, rank them.

    Ordered by kind confidence (exact, variant, prefix, fuzzy), then score
    descending, then citekey for stable output. This is the near-match layer the
    shell RETURNS without rendering; only kind == 'exact' is render-eligible, so a
    near match hands back the real citekey for the caller to re-run against.
    """
    scored: list[ScoredHit] = []
    for h in hits:
        kind, score = classify_citekey(
            query, h.get("citation-key") or "", fuzzy_threshold=fuzzy_threshold
        )
        if kind != "none":
            scored.append(ScoredHit(hit=h, kind=kind, score=score))
    scored.sort(key=_candidate_sort_key)
    return scored


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


# --- make-citeable consumer: pure core ---------------------------------------


@dataclass(frozen=True)
class BibCheck:
    """Whether one citekey is safely citeable in a bib's text.

    well_formed: the whole file parsed with ZERO failed blocks. bibtexparser v2
      collects malformed/truncated/duplicate blocks in `failed_blocks` rather than
      raising, so a partial write that truncates an entry surfaces here.
    citekey_present: an entry whose key is EXACTLY citekey exists. Keyed on the
      parsed entry key, so the citekey appearing inside a field value (a grep
      false-positive) does not count.
    citeable: both hold — the only state in which the paper is safely citeable.
    """

    well_formed: bool
    citekey_present: bool
    failed_count: int
    entry_count: int

    @property
    def citeable(self) -> bool:
        return self.well_formed and self.citekey_present


def check_bib(bib_text: str, citekey: str) -> BibCheck:
    """Parse a bib's text and report whether `citekey` is citeable in it.

    A grep is necessary but not sufficient: a truncated write can contain the
    citekey string yet be broken BibLaTeX. So we require the file to parse with no
    failed blocks AND the citekey to resolve to a real entry. bibtexparser is
    imported lazily so the module stays importable without the PEP 723 deps (the
    httpx idiom); its per-failed-block logging is silenced at module load (a
    briefly truncated mid-write file during polling is expected, not news).
    """
    import bibtexparser  # noqa: PLC0415

    library = bibtexparser.parse_string(bib_text)
    entry_keys = {e.key for e in library.entries}
    return BibCheck(
        well_formed=not library.failed_blocks,
        citekey_present=citekey in entry_keys,
        failed_count=len(library.failed_blocks),
        entry_count=len(library.entries),
    )


@dataclass(frozen=True)
class AutoexportOutcome:
    """Semantic reading of a /api/plus/run-autoexport HTTP response.

    kind is one of: triggered | no-autoexport | bbt-unavailable | bbt-starting |
    endpoint-absent | error.
    """

    kind: str
    registered_paths: tuple[str, ...] = ()
    detail: str = ""


def classify_autoexport_response(status_code: int, body_text: str) -> AutoexportOutcome:
    """Map the endpoint's (status, body) to a semantic outcome.

    The two 404s never collide: a path-bearing request that finds no registered
    export returns JSON `{"status": "no-autoexport", ...}`, while an unregistered
    route returns Zotero's generic plain-text 'No endpoint found'. We tell them
    apart by parsing the body as a JSON object carrying a `status`.
    """
    body = (body_text or "").strip()
    try:
        obj = json.loads(body)
    except ValueError:
        obj = None
    parsed = obj if isinstance(obj, dict) else None
    status = parsed.get("status") if parsed else None

    if status_code == 200 and status == "triggered":
        return AutoexportOutcome(kind="triggered", detail=body)
    if status == "no-autoexport":
        paths = parsed.get("registeredPaths") or [] if parsed else []
        return AutoexportOutcome(
            kind="no-autoexport",
            registered_paths=tuple(str(p) for p in paths),
            detail=body,
        )
    if status == "bbt-unavailable":
        return AutoexportOutcome(kind="bbt-unavailable", detail=body)
    if status == "bbt-starting":
        return AutoexportOutcome(kind="bbt-starting", detail=body)
    if status_code == 404:
        # A 404 without our JSON status means the route is not registered.
        return AutoexportOutcome(kind="endpoint-absent", detail=body)
    return AutoexportOutcome(kind="error", detail=body)


def bib_arg_error(bib: str | None, citekey: str | None) -> str | None:
    """Validate the --bib/--citekey pair for make-citeable mode (None = ok).

    The bib path must be ABSOLUTE — the caller supplies the exact path from the
    project's `bibliography:` declaration, never a guessed or relative name. A
    citekey is required: make-citeable verifies one specific key, never inferred.
    """
    if not bib or not bib.strip():
        return "Error: --bib requires an absolute path to the project bib file."
    if not Path(bib).is_absolute():
        return f"Error: --bib must be an absolute path, got {bib!r}."
    if not citekey or not citekey.strip():
        return "Error: --bib requires --citekey (the exact key to make citeable)."
    return None


def explain_autoexport_failure(outcome: AutoexportOutcome, bib_path: Path) -> str:
    """The human-facing message for a non-`triggered` run-autoexport outcome.

    endpoint-absent directs the user to install/upgrade the plugin — there is no
    faithful collection-scoped force-refresh without it, and a library pull-export
    would clobber the project bib with whole-library content. no-autoexport
    surfaces the setup gap and lists the paths BBT actually holds.
    """
    if outcome.kind == "endpoint-absent":
        return (
            "  the run-autoexport endpoint is not installed (HTTP 404, no route).\n"
            "  Install/upgrade zotero-api-plus to >= 0.4.0 (it adds\n"
            "  POST /api/plus/run-autoexport), then retry. There is no faithful\n"
            "  collection-scoped force-refresh without it — a library pull-export\n"
            "  would clobber this project bib with whole-library content."
        )
    if outcome.kind == "no-autoexport":
        lines = [
            "  no registered 'Keep updated' auto-export targets this bib path.",
            "  Set one up in Zotero (Export Collection -> Keep updated) pointing at",
            f"  {bib_path}. Polling will never succeed until it exists.",
        ]
        lines += [f"    registered: {p}" for p in outcome.registered_paths]
        return "\n".join(lines)
    if outcome.kind == "bbt-unavailable":
        return "  Better BibTeX is not installed in this Zotero."
    if outcome.kind == "bbt-starting":
        return "  Better BibTeX is still starting; retry shortly."
    return f"  unexpected run-autoexport response: {outcome.detail[:200]}"


def _timeout_message(
    last: BibCheck | None, bib_path: Path, citekey: str, poll_timeout: float
) -> str:
    """Explain a verification timeout from the last bib check seen.

    poll_timeout is quoted only in the citekey-absent branch: there the elapsed
    wait is the salient fact ("it didn't show up in time"). For "never appeared"
    and "malformed" the file/parse problem is what matters, not the duration, so
    it is deliberately omitted.
    """
    if last is None:
        return f"  timed out: bib never appeared at {bib_path}."
    if not last.well_formed:
        return (
            f"  timed out: bib still has {last.failed_count} malformed block(s) — "
            "the write may be mid-flight or the export failed."
        )
    return (
        f"  timed out: {citekey} did not appear after {poll_timeout:.0f}s. "
        "Either the export is still running, or the paper sits in a different "
        "collection than this bib exports."
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
                    "denubis-academic/0.1 (mailto:brian.ballsun-stanton@mq.edu.au)"
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


def post_run_autoexport(bib_path: str, timeout: float = 30.0) -> tuple[int, str] | None:
    """POST the bib path to the run-autoexport endpoint; return (status, body).

    Returns None when the endpoint is unreachable (an httpx transport error —
    connect failure or timeout); any OTHER error propagates rather than being
    mislabelled as unreachable, so a real bug surfaces. The endpoint forces BBT's
    own registered auto-export for this path to run. Trigger-only: a 200 means it
    fired, NOT that the export succeeded — the caller proves success against the
    written file (check_bib).
    """
    import httpx  # noqa: PLC0415

    try:
        r = httpx.post(
            RUN_AUTOEXPORT_ENDPOINT, json={"path": bib_path}, timeout=timeout
        )
    except httpx.TransportError:
        return None
    return r.status_code, r.text


def _read_bib_text(bib_path: Path) -> str | None:
    """Read the bib file's text; None if it does not exist yet."""
    try:
        return bib_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _trigger_autoexport(
    bib_path: Path, *, starting_retries: int = 3, retry_delay: float = 2.0
) -> AutoexportOutcome | None:
    """POST the trigger, retrying briefly while BBT reports it is still starting.

    Returns the classified outcome, or None when the endpoint is unreachable
    (post_run_autoexport returns None on an httpx transport error). `bbt-starting`
    is the one outcome BBT expects the caller to retry (the spec), so we re-POST a
    few times — handles the common cold-start-after-launch case.
    """
    attempt = 0
    while True:
        result = post_run_autoexport(str(bib_path))
        if result is None:
            return None
        outcome = classify_autoexport_response(*result)
        if outcome.kind != "bbt-starting" or attempt >= starting_retries:
            return outcome
        attempt += 1
        print(
            f"  Better BibTeX is still starting; retry {attempt}/{starting_retries} "
            f"in {retry_delay:.0f}s ...",
            flush=True,
        )
        time.sleep(retry_delay)


def _poll_until_citeable(
    bib_path: Path, citekey: str, poll_timeout: float, poll_interval: float
) -> BibCheck | None:
    """Poll the bib until `citekey` is citeable or the timeout elapses.

    Returns the last BibCheck seen (None if the bib never appeared). The wait
    lives here, caller-side: the endpoint only triggers, the written file is the
    truth.
    """
    deadline = time.monotonic() + poll_timeout
    last: BibCheck | None = None
    while True:
        text = _read_bib_text(bib_path)
        if text is not None:
            last = check_bib(text, citekey)
            if last.citeable:
                return last
        if time.monotonic() >= deadline:
            return last
        time.sleep(poll_interval)


def ensure_citeable(
    bib_path: Path,
    citekey: str,
    *,
    poll_timeout: float = 30.0,
    poll_interval: float = 1.0,
) -> int:
    """Force `citekey` to be citeable in `bib_path`, then verify it landed.

    Trigger-then-verify: the endpoint only fires BBT's registered auto-export, so
    the truth is the written file, checked with the parser (check_bib), never the
    endpoint's response. Returns 0 iff the citekey ends up present in a well-formed
    bib, non-zero otherwise. The branchy parts (failure messaging, the poll loop)
    live in pure/extracted helpers so this stays a thin orchestrator.
    """
    print(f"\n=== make citeable: {citekey} ===", flush=True)
    print(f"  bib: {bib_path}", flush=True)

    # Pre-check: the configured auto-export may already have written it on its own
    # debounce, in which case no trigger is needed.
    pre_text = _read_bib_text(bib_path)
    if pre_text is None:
        print("  bib not on disk yet.", flush=True)
    else:
        pre = check_bib(pre_text, citekey)
        if pre.citeable:
            print("  already citeable: present in a well-formed bib.", flush=True)
            return 0
        if not pre.well_formed:
            print(
                f"  bib currently has {pre.failed_count} malformed block(s); "
                "a fresh export should replace it.",
                flush=True,
            )

    # Trigger the registered auto-export (retrying briefly while BBT is starting).
    outcome = _trigger_autoexport(bib_path)
    if outcome is None:
        print(
            "  could not reach the run-autoexport endpoint (connection failed).\n"
            "  Is Zotero running with zotero-api-plus >= 0.4.0?",
            flush=True,
        )
        return 1
    if outcome.kind != "triggered":
        print(explain_autoexport_failure(outcome, bib_path), flush=True)
        return 1

    # Triggered: poll the written file for the citekey in a well-formed bib.
    print("  triggered; verifying the written bib ...", flush=True)
    last = _poll_until_citeable(bib_path, citekey, poll_timeout, poll_interval)
    if last is not None and last.citeable:
        print(
            f"  citeable: {citekey} is present in a well-formed bib "
            f"({last.entry_count} entries).",
            flush=True,
        )
        return 0
    print(_timeout_message(last, bib_path, citekey, poll_timeout), flush=True)
    return 1


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


def report_near_matches(
    near: list[ScoredHit],
    library_map: dict[str, int],
    papers_dir: Path,
    *,
    requested: str,
) -> None:
    """Report near citekey matches for a query that had NO exact hit.

    These are returned, never rendered: BBT held the paper under a slightly
    different key (a missing disambiguation suffix, a truncation, a typo), so we
    surface the real key, its library, and its PDF/render state, and let the
    caller re-run resolve with the exact key. Each candidate is enriched for its
    live PDF status, then printed with the same block as an exact match.
    """
    print(
        f"\nNo exact citekey match for {requested!r}. "
        "Nearest paper(s) in Zotero — NOT rendered:",
        flush=True,
    )
    for cand in near:
        paper = normalize_bbt_hit(cand.hit)
        info = enrich_paper(paper, library_map)
        info = check_rendered(info, papers_dir)
        state = classify_state(
            found=True,
            has_pdf=info["pdf_status"] == "present",
            pdf_exists=info["pdf_exists"],
            rendered=info["rendered"],
        )
        if info["pdf_status"] == "unknown":
            state = "pdf-unknown"
        print(f"\n  near match: {cand.kind} (score {cand.score:.2f})", flush=True)
        print_match(info, state)
    print(
        "\n  Re-run resolve with the exact citekey shown above to render it "
        "(near matches are never auto-rendered).",
        flush=True,
    )


def print_duplicate_note(near: list[ScoredHit]) -> None:
    """List base-variant siblings of an exact match as possible duplicates.

    A citekey that resolved exactly can still have disambiguation siblings (…a,
    …b) sitting in Zotero — the trace of a duplicate. Surface where they live so
    the human can merge them; we never touch Zotero. Only the `variant` kind
    counts: a fuzzy or prefix near-match is not a duplicate of this paper.
    """
    variants = [c for c in near if c.kind == "variant"]
    if not variants:
        return
    print("\n  possible duplicate(s) of this citekey in Zotero:", flush=True)
    for c in variants:
        lib = c.hit.get("library") or "(unknown library)"
        print(f"    {c.hit.get('citation-key')}  in {lib}", flush=True)
    print("    merge these in Zotero if they are the same paper.", flush=True)


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
    parser.add_argument(
        "--bib",
        help=(
            "Make --citekey citeable in this project bib: force its registered BBT "
            "auto-export to run (POST /api/plus/run-autoexport, zotero-api-plus "
            ">= 0.4.0), then verify the citekey lands in a well-formed bib. Pass "
            "the ABSOLUTE path you read from the project's bibliography: "
            "declaration, never a guessed filename. Requires --citekey."
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

    # --- Validate the make-citeable pair early (before going live) -----------
    if args.bib is not None:
        bib_err = bib_arg_error(args.bib, args.citekey)
        if bib_err:
            parser.error(bib_err)

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
    near: list[ScoredHit] = []
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
        # Widen recall for citekey near-matching: BBT prefix-matches the base key
        # (surfacing disambiguation siblings) and the author surname reaches a
        # typo'd key's neighbourhood. rank_citekey_candidates filters precision back.
        if args.citekey:
            for extra in (citekey_base(args.citekey), citekey_author(args.citekey)):
                if extra and extra not in tokens:
                    tokens.append(extra)
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

        # A citekey query: exact matches are render-eligible (the unchanged happy
        # path via select_citekey_matches). The NEAR matches (variant/prefix/fuzzy)
        # are surfaced without rendering when no exact hit exists, and flagged as
        # possible duplicates when one does.
        if args.citekey:
            near = [
                c
                for c in rank_citekey_candidates(raw_hits, args.citekey)
                if c.kind != "exact"
            ]
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
        if near:
            # Found under a near key (missing suffix / truncation / typo): surface
            # the real key WITHOUT rendering (the no-render-on-near rule), so the
            # caller re-runs with the exact key.
            report_near_matches(near, library_map, papers_dir, requested=args.citekey)
            if args.bib:
                print(
                    "\n  cannot make citeable: no EXACT citekey match, so the "
                    "registered export cannot target it.\n"
                    "  Re-run --bib with the exact citekey shown above.",
                    flush=True,
                )
            # Distinct from no-match (1): the paper IS here under a near key, so a
            # caller can branch on 2 to re-run with the real key printed above.
            return 2
        print_no_match(tokens, doi=args.doi, search_errors=search_errors)
        if args.bib:
            print(
                "\n  cannot make citeable: the paper did not resolve in Zotero, so a\n"
                "  registered export will not include it. Get it into the exported\n"
                "  collection first, then retry --bib.",
                flush=True,
            )
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

    # An exact match can still have disambiguation siblings — surface them so the
    # human can merge the duplicate in Zotero (we never touch Zotero).
    if args.citekey and near:
        print_duplicate_note(near)

    # --- Make citeable (trigger the registered export + verify the bib) ------
    # Runs only after the paper resolved in Zotero (above): a registered export
    # writes what BBT holds, so the paper must already be in the exported
    # collection. The citekey is the validated --bib companion (bib_arg_error).
    cite_failed = False
    if args.bib:
        cite_failed = ensure_citeable(Path(args.bib), args.citekey) != 0

    return 1 if (render_errors or cite_failed) else 0


if __name__ == "__main__":
    sys.exit(main())
