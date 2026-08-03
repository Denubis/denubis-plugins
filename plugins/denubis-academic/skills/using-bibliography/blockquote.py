"""Find a verbatim quote in rendered per-page markdown and emit a pandoc-style
blockquote with the page number.

Usage:
    python blockquote.py <pages_dir> <citekey> "<quote substring>"

Exits non-zero with NO MATCH if the quote is not found. Per the zettelkasten
AGENTS.md rule, never invent a quote — flag with `> [unverified]` instead.
"""

import re
import sys
from pathlib import Path


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
        return 2

    for page_num, snippet in hits:
        clean = re.sub(r"\s+", " ", snippet).strip()
        print(f"> {clean}")
        print()
        print(f"[@{citekey}, p. {page_num}]")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
