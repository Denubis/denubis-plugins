"""Check an annotated entry against its resolved paper cache; no semantic verdict."""

# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "using-bibliography"))
from renderer import render_metadata_is_current


def check(entry, paper_dir):  # noqa: PLR0912 -- linear record validation
    if not isinstance(entry, dict):
        raise ValueError("Entry must be a JSON object")
    for field in (
        "citekey",
        "source_sha256_prefix",
        "coverage",
        "summary",
        "positioning",
    ):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f"Missing nonempty string: {field}")
    if entry["citekey"] != paper_dir.name:
        raise ValueError("Citekey does not match the resolved paper directory")
    meta = json.loads((paper_dir / "meta.json").read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or not render_metadata_is_current(meta):
        raise ValueError(
            "Missing or legacy render metadata; resolve and re-render first"
        )
    if type(meta.get("ocr")) is not bool:
        raise ValueError("Render has no trustworthy OCR flag")
    if not isinstance(meta.get("renderer"), str) or not meta["renderer"]:
        raise ValueError("Render has no renderer identity")
    page_count = meta.get("page_count")
    if type(page_count) is not int or page_count < 1:
        raise ValueError("Render has no valid page count")
    digest = meta.get("sha256_prefix")
    if (
        not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{16}", digest)
        or digest != entry["source_sha256_prefix"]
    ):
        raise ValueError("Source hash missing or differs from the entry")
    points = entry.get("points")
    if not isinstance(points, list) or not points:
        raise ValueError("Entry must have at least one evidence point")
    failures = []
    for index, point in enumerate(points, start=1):
        if not isinstance(point, dict):
            failures.append(f"Point {index}: expected an object")
            continue
        page = point.get("physical_page")
        if type(page) is not int or not 1 <= page <= page_count:
            failures.append(
                f"Point {index}: physical_page must be within the rendered page count"
            )
            continue
        if any(
            not isinstance(point.get(field), str) or not point[field].strip()
            for field in ("quote", "paraphrase", "relevance")
        ):
            failures.append(
                f"Point {index}: quote, paraphrase and relevance "
                "must be nonempty strings"
            )
            continue
        path = paper_dir / "pages" / f"{page:03d}.md"
        if not path.is_file() or point["quote"] not in path.read_text(encoding="utf-8"):
            failures.append(f"Point {index}: no literal match on physical page {page}")
    return {
        "citekey": entry["citekey"],
        "status": "text-match" if not failures else "failed",
        "matched": len(points) - len(failures),
        "total": len(points),
        "failures": failures,
        "visual_verification_required": meta["ocr"],
        "interpretation_review": "not assessed by this tool",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", type=Path)
    parser.add_argument("paper_dir", type=Path)
    args = parser.parse_args()
    try:
        result = check(
            json.loads(args.entry.read_text(encoding="utf-8")), args.paper_dir
        )
    except (OSError, ValueError) as error:
        result = {"status": "failed", "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "text-match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
