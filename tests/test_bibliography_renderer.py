"""Tests for plugins/denubis-bibliography/skills/using-bibliography/renderer.py.

Quality-heuristic coverage: empty pages, marker-only pages (Levenson 1973
case), marker + content pages (Vanlissa 2024 case), U+FFFD ratio
(Stephens 2000 case), threshold edges.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_RENDERER = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-bibliography"
    / "skills"
    / "using-bibliography"
    / "renderer.py"
)


def _load_renderer():
    spec = importlib.util.spec_from_file_location("renderer_under_test", _RENDERER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["renderer_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


renderer = _load_renderer()
qa = renderer.quality_assessment

MARKER = "**==> picture [480 x 720] intentionally omitted <==**"
MARKER_SMALL = "**==> picture [12 x 19] intentionally omitted <==**"
MARKER_NO_BOLD = "==> picture [228 x 63] intentionally omitted <=="


# --- Empty / minimal pages ------------------------------------------------


def test_no_pages_is_fail():
    assert qa([])["verdict"] == "fail"


def test_all_empty_pages_is_fail():
    result = qa(["", "  ", "\n\n"])
    assert result["verdict"] == "fail"
    assert result["empty_pages"] == 3


def test_one_real_page_passes_with_short_tail():
    # 1 real page (lots of content) + 1 near-empty back cover.
    # Empty fraction 1/2 = 50% which is NOT > 50%, so passes.
    result = qa(["a" * 5000, ""])
    assert result["verdict"] == "pass"


def test_majority_empty_fails():
    # 1 real + 2 empty = 67% empty > 50% threshold.
    result = qa(["a" * 5000, "", ""])
    assert result["verdict"] == "fail"


# --- Picture-marker handling (Levenson 1973 regression) -------------------


def test_marker_only_page_counts_as_empty():
    """The bug 0.2.2 missed: marker is ~53 chars, slips above 50-char
    threshold, so a marker-only page looked 'non-empty' to the naive count.
    After stripping, it correctly registers as empty."""
    result = qa([MARKER] * 8)
    assert result["verdict"] == "fail"
    assert result["empty_pages"] == 8


def test_marker_only_with_bold_and_without():
    """Marker may appear with or without `**` bold delimiters."""
    pages = [MARKER, MARKER_NO_BOLD, MARKER_SMALL]
    result = qa(pages)
    assert result["empty_pages"] == 3


def test_marker_plus_real_content_passes():
    """Vanlissa 2024 page 1: 3 markers embedded in a 1908-char real page.
    Stripping markers should leave plenty of content above threshold."""
    content = (
        f"{MARKER_SMALL}\n\n"
        "## **Structural Equation Modeling: A Multidisciplinary Journal**\n\n"
        + ("Real journal content. " * 80)
        + f"\n{MARKER_SMALL}\n"
    )
    result = qa([content] * 4)
    assert result["verdict"] == "pass"
    assert result["empty_pages"] == 0


def test_marker_plus_tiny_caption_still_empty():
    """A marker + 2-word caption shouldn't be enough to claim a real page."""
    content = f"{MARKER}\n\nFigure 1."
    result = qa([content] * 8)
    assert result["verdict"] == "fail"
    assert result["empty_pages"] == 8


def test_multiple_markers_one_page_still_empty():
    """Some PDFs have several image regions per page; pymupdf emits one
    marker each. A page that's only markers, however many, is still empty."""
    content = "\n\n".join([MARKER_SMALL, MARKER, MARKER_NO_BOLD])
    result = qa([content] * 8)
    assert result["empty_pages"] == 8


# --- U+FFFD ratio (Stephens 2000 regression) ------------------------------


def test_no_fffd_is_clean():
    result = qa(["a" * 1000] * 3)
    assert result["fffd_count"] == 0
    assert result["verdict"] == "pass"


def test_high_fffd_ratio_fails():
    # 100 chars total, 10 are FFFD = 10% > 0.5% threshold.
    page = ("a" * 90) + ("�" * 10)
    result = qa([page] * 3)
    assert result["verdict"] == "fail"
    assert any("U+FFFD" in r for r in result["reasons"])


def test_marker_stripping_does_not_affect_fffd_count():
    """FFFD count is measured on raw pages; marker stripping only affects
    the empty-page count."""
    page = MARKER + ("�" * 50) + ("a" * 200)
    result = qa([page] * 3)
    assert result["fffd_count"] == 150  # 50 per page * 3


# --- Threshold edges ------------------------------------------------------


def test_exactly_at_threshold_is_not_empty():
    page = "x" * renderer.EMPTY_PAGE_CHAR_THRESHOLD
    result = qa([page] * 4)
    assert result["empty_pages"] == 0


def test_one_below_threshold_is_empty():
    page = "x" * (renderer.EMPTY_PAGE_CHAR_THRESHOLD - 1)
    result = qa([page] * 4)
    assert result["empty_pages"] == 4
