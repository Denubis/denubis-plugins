"""Render a Zotero-stored PDF to per-page markdown.

Outputs into <out_dir>:
  full.md             Combined document with `<!-- page:N -->` boundary markers.
  pages/NNN.md        One file per 1-based page (zero-padded to 3 digits).
  meta.json           page_count, source_pdf, sha256_prefix, renderer, ocr.

Tries pymupdf4llm first, then escalates to docling (no OCR), then docling+OCR
if earlier passes produce empty/garbled output. See renderer.py for thresholds.

Usage:
    python render.py <pdf_path> <out_dir>

Requires pymupdf4llm (AGPL-3). docling (Apache-2.0) is optional - only loaded
when the fallback fires.
"""

import sys
from pathlib import Path

from renderer import render_pdf_with_fallback


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2])

    if not pdf.is_file():
        print(f"PDF not found: {pdf}", file=sys.stderr)
        return 1

    try:
        meta = render_pdf_with_fallback(pdf, out)
    except RuntimeError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1

    label = meta["renderer"] + (" +OCR" if meta.get("ocr") else "")
    print(f"Rendered {meta['page_count']} pages from {pdf.name} via {label}")
    print(f"  Combined: {out / 'full.md'}")
    print(f"  Per-page: {out / 'pages'}/")
    print(f"  Metadata: {out / 'meta.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
