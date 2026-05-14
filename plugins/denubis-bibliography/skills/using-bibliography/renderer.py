"""PDF -> per-page markdown with auto-escalation between renderers.

The cascade tries renderers in increasing cost/capability order and uses the
first one whose output passes a basic quality check:

  1. pymupdf4llm (AGPL-3, fast) - handles most papers with embedded text
  2. docling, no OCR (Apache-2.0, slower) - handles broken text layers
     and Unicode-replacement-character PDFs (e.g. Stephens 2000)
  3. docling + OCR (Apache-2.0, slowest, GPU-friendly) - handles scanned
     PDFs and old PDFWriter output with no text layer (e.g. Schraw 1994)

The quality check fails a render if either:
  - more than 50% of pages have <50 chars of stripped content, OR
  - U+FFFD ('replacement character') is more than 0.5% of all chars.

If every renderer fails the quality check, render_pdf_with_fallback raises
RuntimeError - the caller decides whether to log-and-continue (ingest.py
treats it as a per-paper failure) or surface the error.

docling is lazy-imported: papers that pymupdf4llm handles cleanly never pay
docling's startup tax.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

EMPTY_PAGE_CHAR_THRESHOLD = 50
EMPTY_PAGE_FRACTION_THRESHOLD = 0.5
REPLACEMENT_CHAR_RATIO_THRESHOLD = 0.005

Progress = Callable[[str], None]


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
    empty_count = sum(1 for p in pages if len(p.strip()) < EMPTY_PAGE_CHAR_THRESHOLD)
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
        reasons.append(
            f"{fffd_count} U+FFFD chars ({fffd_ratio:.2%} of {total_chars})"
        )

    return {
        "verdict": "fail" if reasons else "pass",
        "reasons": reasons,
        "empty_pages": empty_count,
        "total_pages": len(pages),
        "fffd_count": fffd_count,
        "total_chars": total_chars,
    }


def _write_outputs(
    pages: list[str],
    pdf: Path,
    out_dir: Path,
    renderer: str,
    ocr: bool,
    attempts: list[dict],
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

    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def render_pdf_with_fallback(
    pdf: Path,
    out_dir: Path,
    progress: Progress = print,
) -> dict:
    """Render a PDF to per-page markdown, escalating renderers on failure.

    Writes pages/NNN.md, full.md, and meta.json under out_dir. Returns the
    meta dict. Raises RuntimeError if every renderer's output fails the
    quality check.
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
                {"renderer": renderer, "ocr": ocr, "verdict": "import-error", "error": str(e)}
            )
            continue
        except Exception as e:
            progress(f"    {label} crashed: {e}")
            attempts.append(
                {"renderer": renderer, "ocr": ocr, "verdict": "crashed", "error": str(e)}
            )
            continue

        qa = quality_assessment(pages)
        attempts.append({"renderer": renderer, "ocr": ocr, "verdict": qa["verdict"], **qa})
        if qa["verdict"] == "pass":
            progress(
                f"    {label} OK: {qa['total_pages']} pages, "
                f"{qa['empty_pages']} near-empty, {qa['fffd_count']} U+FFFD"
            )
            return _write_outputs(pages, pdf, out_dir, renderer, ocr, attempts)
        progress(f"    {label} quality failed: {'; '.join(qa['reasons'])}; escalating")

    raise RuntimeError(
        f"All renderers failed for {pdf.name}; attempts: "
        + "; ".join(
            f"{a['renderer']}{'+ocr' if a['ocr'] else ''}={a['verdict']}"
            for a in attempts
        )
    )
