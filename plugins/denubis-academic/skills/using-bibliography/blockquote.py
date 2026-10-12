"""Find a verbatim quote in rendered per-page markdown and emit a pandoc-style
blockquote with the page number.

Usage:
    python blockquote.py <pages_dir> <citekey> "<quote substring>"

A hit proves the string occurs in the render, which LOCATES the passage; it
does not verify the wording against the source document. Every hit is
therefore labelled `located`; the reader checks the physical page (the PDF
page image, or the snapshot or attachment for non-PDF sources) before calling
a quotation `verified`. Exits 2 with NO MATCH and `unverified` if the quote is
not found. Per the zettelkasten AGENTS.md rule, never invent a quote.
"""

import re
import sys
from pathlib import Path

# The state a render match can establish. `verified` is reserved for a check
# against the source page, which this helper cannot perform.
LOCATED = (
    "Verification: located (render match; check the source page before "
    "calling it verified)"
)


def normalise(s: str) -> str:
    """Collapse whitespace and normalise common PDF-extraction noise."""
    return re.sub(r"\s+", " ", s.replace("\u2010", "-")).strip().lower()


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2

    pages_dir = Path(sys.argv[1])
    citekey = sys.argv[2]
    query = sys.argv[3]

    if not pages_dir.is_dir():
        print(f"Pages dir not found: {pages_dir}", file=sys.stderr)
        return 1

    needle = normalise(query)
    hits = []

    for page_md in sorted(pages_dir.glob("*.md")):
        text = page_md.read_text(encoding="utf-8")
        if needle in normalise(text):
            page_num = int(page_md.stem)
            m = re.search(re.escape(query), text, re.IGNORECASE | re.DOTALL)
            snippet = m.group(0) if m else query
            hits.append((page_num, snippet))

    if not hits:
        print(f"NO MATCH for query in {pages_dir}", file=sys.stderr)
        print("Verification: unverified", file=sys.stderr)
        return 2

    for page_num, snippet in hits:
        clean = re.sub(r"\s+", " ", snippet).strip()
        print(f"> {clean}")
        print()
        print(f"[@{citekey}, p. {page_num}]")
        print()
        print(LOCATED)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
