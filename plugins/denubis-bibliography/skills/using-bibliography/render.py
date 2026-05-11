"""Render a Zotero-stored PDF to per-page markdown using pymupdf4llm.

Outputs into <out_dir>:
  full.md             Combined document with `<!-- page:N -->` boundary markers.
  pages/NNN.md        One file per 1-based page (zero-padded to 3 digits).
  meta.json           page_count, source_pdf, sha256_prefix.

Usage:
    python render.py <pdf_path> <out_dir>

Requires pymupdf4llm (AGPL-3) installed in the active Python environment.
"""

import hashlib
import json
import sys
from pathlib import Path

import pymupdf4llm


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2])

    if not pdf.is_file():
        print(f"PDF not found: {pdf}", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    pages_dir = out / "pages"
    pages_dir.mkdir(exist_ok=True)

    # page_chunks=True returns one dict per page with 'text' key.
    pages = pymupdf4llm.to_markdown(str(pdf), page_chunks=True)

    full_parts = []
    for i, page in enumerate(pages, start=1):
        text = page["text"] if isinstance(page, dict) else page
        full_parts.append(f"\n\n<!-- page:{i} -->\n\n{text}")
        (pages_dir / f"{i:03d}.md").write_text(text, encoding="utf-8")

    (out / "full.md").write_text("".join(full_parts), encoding="utf-8")

    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]
    (out / "meta.json").write_text(
        json.dumps(
            {
                "source_pdf": str(pdf),
                "page_count": len(pages),
                "sha256_prefix": sha,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Rendered {len(pages)} pages from {pdf.name}")
    print(f"  Combined: {out / 'full.md'}")
    print(f"  Per-page: {pages_dir}/")
    print(f"  Metadata: {out / 'meta.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
