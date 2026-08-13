"""Render a Zotero-stored PDF to per-page markdown.

Outputs into <out_dir>:
  full.md             Combined document with `<!-- page:N -->` boundary markers.
  pages/NNN.md        One file per 1-based page (zero-padded to 3 digits).
  meta.json           page_count, source_pdf, sha256_prefix, renderer, ocr.

Tries pymupdf4llm first, then escalates to docling (no OCR), then docling+OCR
if earlier passes produce empty/garbled output. If even docling+OCR drops too
many pages (>30% near-empty), the render is refused: pass --allow-mocr to
escalate to dots.mocr (GPU OCR), which the cascade starts and stops itself.
See renderer.py for thresholds.

Usage:
    python render.py <pdf_path> <out_dir>
    python render.py <pdf_path> <out_dir> --allow-mocr

Requires pymupdf4llm (AGPL-3). docling (Apache-2.0) loads only when the fallback
fires; dots.mocr (configured via [mocr] in config.toml) only with --allow-mocr.
"""

import argparse
import sys
import tomllib
from contextlib import nullcontext
from pathlib import Path

from renderer import NeedsMocr, mocr_server, render_attachment

CONFIG_PATH = Path.home() / ".config" / "denubis-academic-research" / "config.toml"


def load_mocr_cfg() -> dict | None:
    """Read the optional [mocr] section from config.toml; None if absent."""
    if not CONFIG_PATH.exists():
        return None
    try:
        with CONFIG_PATH.open("rb") as f:
            cfg = tomllib.load(f)
    except Exception:
        return None
    m = cfg.get("mocr")
    if isinstance(m, dict) and m.get("repo"):
        return {
            "repo": Path(m["repo"]).expanduser(),
            "port": int(m.get("port", 8000)),
            "startup_timeout": float(m.get("startup_timeout", 300)),
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("out_dir")
    parser.add_argument(
        "--allow-mocr",
        action="store_true",
        help="Escalate to dots.mocr (GPU) if the cascade can't produce a usable "
        "render. Requires [mocr] in config.toml.",
    )
    args = parser.parse_args()

    pdf = Path(args.pdf)
    out = Path(args.out_dir)
    if not pdf.is_file():
        print(f"PDF not found: {pdf}", file=sys.stderr)
        return 1

    mocr_cfg = load_mocr_cfg() if args.allow_mocr else None
    if args.allow_mocr and not mocr_cfg:
        print(
            "--allow-mocr given but [mocr] is not configured in config.toml.",
            file=sys.stderr,
        )
    ctx = (
        mocr_server(
            mocr_cfg["repo"],
            port=mocr_cfg["port"],
            startup_timeout=mocr_cfg["startup_timeout"],
        )
        if (args.allow_mocr and mocr_cfg)
        else nullcontext(None)
    )

    try:
        with ctx as session:
            meta = render_attachment(
                pdf, out, allow_mocr=args.allow_mocr, mocr_session=session
            )
    except NeedsMocr as e:
        print(f"NEEDS MOCR: {e}", file=sys.stderr)
        return 3
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
