"""PDF -> per-page markdown with auto-escalation between renderers.

The cascade tries renderers in increasing cost/capability order and uses the
first one whose output passes a basic quality check:

  1. pymupdf4llm (AGPL-3, fast) - handles most papers with embedded text
  2. docling, no OCR (Apache-2.0, slower) - handles broken text layers
     and Unicode-replacement-character PDFs (e.g. Stephens 2000)
  3. docling + OCR (Apache-2.0, slowest, GPU-friendly) - handles scanned
     PDFs and old PDFWriter output with no text layer (e.g. Schraw 1994)

The quality check fails a render if either:
  - more than 30% of pages have <50 chars of stripped content, OR
  - U+FFFD ('replacement character') is more than 0.5% of all chars.

The 30% near-empty gate (was 50%) catches renders that silently drop a large
fraction of pages. Polanyi's Tacit Dimension came out of docling+OCR with 40 of
102 pages near-empty (39%) - ~46% of the book lost - yet passed the old 50%
gate; mocr read those same pages (3% near-empty). Clean renders sit at 0-3%.

If every renderer fails the quality check, render_pdf_with_fallback raises
RuntimeError - the caller decides whether to log-and-continue (ingest.py
treats it as a per-paper failure) or surface the error.

docling is lazy-imported: papers that pymupdf4llm handles cleanly never pay
docling's startup tax.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

EMPTY_PAGE_CHAR_THRESHOLD = 50
# Tunable. 0.30 catches large-scale page loss (Polanyi docling+OCR at 39%) while
# clean renders (0-3% near-empty) pass comfortably. A render exceeding this is
# refused and escalated to mocr (see render_pdf_with_fallback / NeedsMocr).
EMPTY_PAGE_FRACTION_THRESHOLD = 0.30
REPLACEMENT_CHAR_RATIO_THRESHOLD = 0.005

# pymupdf4llm emits this placeholder for pages whose only content is an image
# (no text layer). Example: `**==> picture [480 x 720] intentionally omitted <==**`.
# The marker is ~50 chars - right at the EMPTY_PAGE_CHAR_THRESHOLD edge - so a
# page containing only one of these markers can sneak above the threshold and
# avoid escalation. Strip these before measuring "real" content length.
# Levenson 1973 (10.1037/h0035357) was the first paper that exposed this gap.
_PYMUPDF_PICTURE_MARKER_RE = re.compile(
    r"\*{0,2}\s*==>\s*picture\s*\[[^\]]*\]\s*intentionally\s*omitted\s*<==\s*\*{0,2}",
    re.IGNORECASE,
)

Progress = Callable[[str], None]


def _strip_structural_markers(page_text: str) -> str:
    """Remove renderer-emitted placeholders so the quality heuristic counts
    real content, not bookkeeping. Currently only pymupdf4llm's
    `==> picture [WxH] intentionally omitted <==` marker."""
    return _PYMUPDF_PICTURE_MARKER_RE.sub("", page_text)


def _render_with_pymupdf4llm(pdf: Path) -> list[str]:
    import pymupdf4llm

    pages = pymupdf4llm.to_markdown(str(pdf), page_chunks=True)
    return [p["text"] if isinstance(p, dict) else p for p in pages]


def _render_with_docling(pdf: Path, ocr: bool) -> list[str]:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    # Pin EasyOCR explicitly: recent docling builds default to RapidOCR, which
    # downloads models from modelscope.cn at first use - unreliable from
    # outside China. EasyOCR ships its own English models via PyPI.
    opts = PdfPipelineOptions(
        do_ocr=ocr,
        do_table_structure=True,
        ocr_options=EasyOcrOptions(lang=["en"]),
    )
    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )
    doc = conv.convert(str(pdf)).document
    page_numbers = sorted(doc.pages.keys())
    return [doc.export_to_markdown(page_no=i) for i in page_numbers]


def quality_assessment(pages: list[str]) -> dict:
    if not pages:
        return {
            "verdict": "fail",
            "reasons": ["no pages produced"],
            "empty_pages": 0,
            "total_pages": 0,
            "fffd_count": 0,
            "total_chars": 0,
        }
    # Empty-page count uses content after stripping renderer markers, so a
    # marker-only page (image-only PDF page) correctly registers as empty.
    # FFFD count uses raw page text - the marker doesn't contain U+FFFD.
    empty_count = sum(
        1
        for p in pages
        if len(_strip_structural_markers(p).strip()) < EMPTY_PAGE_CHAR_THRESHOLD
    )
    empty_fraction = empty_count / len(pages)
    total_chars = sum(len(p) for p in pages)
    fffd_count = sum(p.count("�") for p in pages)
    fffd_ratio = fffd_count / total_chars if total_chars else 0.0

    reasons: list[str] = []
    if empty_fraction > EMPTY_PAGE_FRACTION_THRESHOLD:
        reasons.append(
            f"{empty_count}/{len(pages)} pages have <{EMPTY_PAGE_CHAR_THRESHOLD} chars"
        )
    if fffd_ratio > REPLACEMENT_CHAR_RATIO_THRESHOLD:
        reasons.append(f"{fffd_count} U+FFFD chars ({fffd_ratio:.2%} of {total_chars})")

    return {
        "verdict": "fail" if reasons else "pass",
        "reasons": reasons,
        "empty_pages": empty_count,
        "total_pages": len(pages),
        "fffd_count": fffd_count,
        "total_chars": total_chars,
    }


# dots.mocr's combined `_nohf.md` marks page boundaries with
# `<!-- ===== page N ===== -->`. We split on these to recover per-page text.
_MOCR_PAGE_MARKER_RE = re.compile(r"<!--\s*=+\s*page\s+\d+\s*=+\s*-->", re.IGNORECASE)
# dots.mocr embeds a full-page PNG atop each page as a markdown data-image
# (~86% of the file's bytes on COSMIN). Strip these so papers/ keeps only the
# OCR text — base64 bloat swamps the files and wrecks blockquote matching.
_MOCR_DATA_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*data:image/[^)]+\)")


def _strip_data_images(page: str) -> str:
    return _MOCR_DATA_IMAGE_RE.sub("", page)


def fold_mocr_markdown(nohf_text: str) -> list[str]:
    """Split a dots.mocr combined `_nohf.md` into per-page markdown, dropping
    embedded base64 page images.

    Content before the first page marker is document preamble and is dropped.
    Marker-less input is returned as a single page (defensive); empty input
    yields no pages. Replaces the throwaway converter hand-written for the
    Polanyi mocr render.
    """
    if not nohf_text.strip():
        return []
    parts = _MOCR_PAGE_MARKER_RE.split(nohf_text)
    # split() yields [preamble, page1, page2, ...]; with no marker it yields
    # the whole text as a single element.
    if len(parts) == 1:
        return [_strip_data_images(nohf_text).strip()]
    return [_strip_data_images(p).strip() for p in parts[1:]]


def _write_outputs(
    pages: list[str],
    pdf: Path,
    out_dir: Path,
    renderer: str,
    ocr: bool,
    attempts: list[dict],
    extra_meta: dict | None = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(exist_ok=True)

    full_parts: list[str] = []
    for i, text in enumerate(pages, start=1):
        full_parts.append(f"\n\n<!-- page:{i} -->\n\n{text}")
        (pages_dir / f"{i:03d}.md").write_text(text, encoding="utf-8")
    (out_dir / "full.md").write_text("".join(full_parts), encoding="utf-8")

    meta: dict = {
        "source_pdf": str(pdf),
        "page_count": len(pages),
        "sha256_prefix": hashlib.sha256(pdf.read_bytes()).hexdigest()[:16],
        "renderer": renderer,
        "ocr": ocr,
    }
    if len(attempts) > 1:
        chain = " -> ".join(
            f"{a['renderer']}{'+ocr' if a['ocr'] else ''}({a['verdict']})"
            for a in attempts
        )
        meta["renderer_note"] = f"escalated: {chain}"
    if extra_meta:
        meta.update(extra_meta)

    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


class NeedsMocr(Exception):
    """The cascade (pymupdf4llm -> docling -> docling+OCR) could not produce a
    usable render and mocr escalation was not enabled. Callers surface this as
    're-run with --allow-mocr'. Distinct from RuntimeError (a genuinely failed
    render, including mocr) so callers can message the two differently."""

    def __init__(self, pdf: Path, attempts: list[dict]):
        self.pdf = pdf
        self.attempts = attempts
        fracs = [
            a["empty_pages"] / a["total_pages"]
            for a in attempts
            if a.get("total_pages")
        ]
        frac = min(fracs) if fracs else None
        detail = (
            f" ({frac:.0%} of pages near-empty on the best attempt)"
            if frac is not None
            else ""
        )
        super().__init__(
            f"{pdf.name}: cascade could not produce a usable render{detail}. "
            "Re-run with --allow-mocr to escalate to dots.mocr (GPU OCR)."
        )


# --- mocr escalation tier (external GPU vLLM server) ----------------------
# The dots.mocr deploy is a stateful vLLM server (GPU + multi-GB model), driven
# by the deploy's own fish wrappers. We call those wrappers by path rather than
# reimplementing the vLLM command, so the deploy keeps owning its model path and
# flags. Heavy/slow/expensive, so this tier is confirm-gated (allow_mocr) and the
# server is started once per run and stopped on exit.


def _free_gpu(_progress: Progress) -> None:
    """Release VRAM held by easyocr/docling before vLLM claims the GPU."""
    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: S110 (best-effort VRAM release before vLLM)
        pass


class _MocrSession:
    """A live (or lazily-started) dots.mocr server. `.render(pdf)` returns
    (pages, source_md_path). Starts vLLM on first use, reusing an
    already-running server; the owning context manager stops it on exit only
    if this session started it."""

    def __init__(
        self, repo: Path, port: int, startup_timeout: float, progress: Progress
    ):
        self.repo = Path(repo).expanduser()
        self.port = port
        self.startup_timeout = startup_timeout
        self.progress = progress
        self._started_by_us = False
        self._proc = None

    def _server_up(self) -> bool:
        import subprocess

        return (
            subprocess.run(
                ["curl", "-sf", f"http://localhost:{self.port}/v1/models"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0
        )

    def _ensure_server(self) -> None:
        import subprocess
        import time

        if self._server_up():
            self.progress(f"  reusing vLLM already running on :{self.port}")
            return
        serve = self.repo / "dots-serve.fish"
        if not serve.is_file():
            raise RuntimeError(
                f"mocr: {serve} not found — check [mocr].repo in config.toml"
            )
        _free_gpu(self.progress)
        self.progress("  starting vLLM (dots.mocr); model load takes minutes...")
        self._proc = subprocess.Popen(
            ["fish", str(serve)],
            cwd=str(self.repo),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._started_by_us = True
        start = time.monotonic()
        while not self._server_up():
            if self._proc.poll() is not None:
                raise RuntimeError(
                    "mocr: vLLM server exited during startup (check GPU/VRAM)"
                )
            if time.monotonic() - start > self.startup_timeout:
                raise RuntimeError(
                    f"mocr: server not ready within {self.startup_timeout:.0f}s"
                )
            time.sleep(3)
        self.progress(f"  vLLM ready on :{self.port}")

    def render(self, pdf: Path) -> tuple[list[str], str | None]:
        import subprocess
        import tempfile

        self._ensure_server()
        outdir = Path(tempfile.mkdtemp(prefix="mocr-"))
        self.progress(f"  OCR via dots.mocr: {pdf.name}")
        subprocess.run(
            ["fish", str(self.repo / "dots-ocr.fish"), str(pdf), str(outdir)],
            cwd=str(self.repo),
            check=True,
        )
        jsonls = list(outdir.glob("*.jsonl"))
        if not jsonls:
            raise RuntimeError(f"mocr: dots-ocr produced no .jsonl in {outdir}")
        subprocess.run(
            [
                "python3",
                str(self.repo / "tools" / "combine_markdown.py"),
                str(jsonls[0]),
            ],
            cwd=str(self.repo),
            check=True,
        )
        # combine writes <stem>_nohf.md at the outdir root; per-page _nohf files
        # live under the <stem>/ subdir, so a non-recursive glob picks the combined one.
        combined = list(outdir.glob("*_nohf.md"))
        if not combined:
            raise RuntimeError(f"mocr: no combined _nohf.md in {outdir}")
        text = combined[0].read_text(encoding="utf-8", errors="replace")
        return fold_mocr_markdown(text), str(combined[0])

    def stop(self) -> None:
        import subprocess

        if not self._started_by_us:
            return
        stopper = self.repo / "dots-stop.fish"
        if stopper.is_file():
            self.progress("  stopping vLLM (freeing VRAM)...")
            subprocess.run(["fish", str(stopper)], cwd=str(self.repo), check=False)


@contextmanager
def mocr_server(
    repo: str | Path,
    *,
    port: int = 8000,
    startup_timeout: float = 300,
    progress: Progress = print,
):
    """Yield a lazily-started dots.mocr session. vLLM boots on first `.render()`
    (reusing a server already on `port`), and is stopped on exit only if this
    context started it — so an error or Ctrl-C still frees VRAM."""
    session = _MocrSession(Path(repo), port, startup_timeout, progress)
    try:
        yield session
    finally:
        session.stop()


def render_pdf_with_fallback(
    pdf: Path,
    out_dir: Path,
    progress: Progress = print,
    *,
    allow_mocr: bool = False,
    mocr_session=None,
) -> dict:
    """Render a PDF to per-page markdown, escalating renderers on failure.

    Writes pages/NNN.md, full.md, and meta.json under out_dir. Returns the
    meta dict.

    On total cascade failure: if allow_mocr and a live mocr_session is supplied,
    escalate to dots.mocr (whose output is itself quality-checked); otherwise
    raise NeedsMocr. Raises RuntimeError if mocr is attempted and also fails.
    """
    cascade: list[tuple[str, bool, Callable[[], list[str]]]] = [
        ("pymupdf4llm", False, lambda: _render_with_pymupdf4llm(pdf)),
        ("docling", False, lambda: _render_with_docling(pdf, ocr=False)),
        ("docling", True, lambda: _render_with_docling(pdf, ocr=True)),
    ]

    attempts: list[dict] = []
    for renderer, ocr, run in cascade:
        label = f"{renderer}{' +OCR' if ocr else ''}"
        progress(f"  trying {label}...")
        try:
            pages = run()
        except ImportError as e:
            progress(f"    {label} not installed: {e}")
            attempts.append(
                {
                    "renderer": renderer,
                    "ocr": ocr,
                    "verdict": "import-error",
                    "error": str(e),
                }
            )
            continue
        except Exception as e:
            progress(f"    {label} crashed: {e}")
            attempts.append(
                {
                    "renderer": renderer,
                    "ocr": ocr,
                    "verdict": "crashed",
                    "error": str(e),
                }
            )
            continue

        qa = quality_assessment(pages)
        attempts.append(
            {"renderer": renderer, "ocr": ocr, "verdict": qa["verdict"], **qa}
        )
        if qa["verdict"] == "pass":
            progress(
                f"    {label} OK: {qa['total_pages']} pages, "
                f"{qa['empty_pages']} near-empty, {qa['fffd_count']} U+FFFD"
            )
            return _write_outputs(pages, pdf, out_dir, renderer, ocr, attempts)
        progress(f"    {label} quality failed: {'; '.join(qa['reasons'])}; escalating")

    if allow_mocr and mocr_session is not None:
        progress("  escalating to mocr (dots.mocr GPU OCR)...")
        pages, source_md = mocr_session.render(pdf)
        qa = quality_assessment(pages)
        attempts.append(
            {"renderer": "mocr", "ocr": True, "verdict": qa["verdict"], **qa}
        )
        if qa["verdict"] == "pass":
            progress(
                f"    mocr OK: {qa['total_pages']} pages,"
                f" {qa['empty_pages']} near-empty"
            )
            extra = {"source_md": source_md} if source_md else None
            return _write_outputs(
                pages, pdf, out_dir, "mocr", True, attempts, extra_meta=extra
            )
        raise RuntimeError(
            f"mocr also failed for {pdf.name}: {'; '.join(qa['reasons'])}"
        )

    raise NeedsMocr(pdf, attempts)
