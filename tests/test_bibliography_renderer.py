"""Tests for plugins/denubis-bibliography/skills/using-bibliography/renderer.py.

Quality-heuristic coverage: empty pages, marker-only pages (Levenson 1973
case), marker + content pages (Vanlissa 2024 case), U+FFFD ratio
(Stephens 2000 case), threshold edges.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

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


def test_low_empty_fraction_passes():
    # 4 real pages + 1 near-empty back cover = 20% empty, under the 30% gate.
    result = qa(["a" * 5000] * 4 + [""])
    assert result["verdict"] == "pass"


def test_majority_empty_fails():
    # 1 real + 2 empty = 67% empty > 30% threshold.
    result = qa(["a" * 5000, "", ""])
    assert result["verdict"] == "fail"


# --- Near-empty-page fraction gate (Polanyi docling+OCR regression) --------
# The bad docling+OCR render of Polanyi's Tacit Dimension dropped 40/102 pages
# to near-empty (39%), losing ~46% of the book, yet passed the old 50% gate.
# The gate is now 30%: clean renders sit at 0-3%, that failure at 39%.


def test_thirty_percent_empty_passes_boundary():
    # 3 empty of 10 = exactly 30%, which is NOT > 0.30, so passes.
    result = qa(["a" * 5000] * 7 + [""] * 3)
    assert result["verdict"] == "pass"
    assert result["empty_pages"] == 3


def test_above_thirty_percent_empty_fails():
    # 4 empty of 10 = 40% > 30% gate.
    result = qa(["a" * 5000] * 6 + [""] * 4)
    assert result["verdict"] == "fail"
    assert any("pages have <" in r for r in result["reasons"])


def test_polanyi_like_fraction_fails():
    # ~39% near-empty (40 of 102), the real docling+OCR failure that used to
    # slip under the 50% gate.
    result = qa(["a" * 2000] * 62 + [""] * 40)
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


# --- fold_mocr_markdown (dots.mocr _nohf.md -> per-page list) --------------
# dots.mocr emits a combined markdown with `<!-- ===== page N ===== -->`
# markers. fold_mocr_markdown splits it into the per-page list the papers/
# writer expects, replacing the throwaway /tmp/convert_polanyi.py.

fold = renderer.fold_mocr_markdown


def test_fold_splits_on_page_markers():
    text = (
        "<!-- ===== page 1 ===== -->\nAlpha\n"
        "<!-- ===== page 2 ===== -->\nBeta\n"
        "<!-- ===== page 3 ===== -->\nGamma\n"
    )
    assert fold(text) == ["Alpha", "Beta", "Gamma"]


def test_fold_drops_preamble_before_first_marker():
    # The deploy's _nohf.md has lines before the first page marker; they are
    # document preamble, not page 1 content.
    text = (
        "# Some Title\nrun metadata\n"
        "<!-- ===== page 1 ===== -->\nReal page one\n"
        "<!-- ===== page 2 ===== -->\nReal page two\n"
    )
    assert fold(text) == ["Real page one", "Real page two"]


def test_fold_preserves_multiline_content():
    text = (
        "<!-- ===== page 1 ===== -->\nLine A\n\nLine B\n"
        "<!-- ===== page 2 ===== -->\nOnly\n"
    )
    pages = fold(text)
    assert pages[0] == "Line A\n\nLine B"
    assert pages[1] == "Only"


def test_fold_no_markers_returns_single_page():
    # Defensive: unexpected marker-less input becomes one page, not a crash.
    assert fold("just some text\nno markers") == ["just some text\nno markers"]


def test_fold_empty_input_returns_no_pages():
    assert fold("") == []


def test_fold_strips_base64_data_images():
    # dots.mocr embeds a full-page PNG atop each page (~86% of bytes on COSMIN);
    # keep the OCR text, drop the base64 bloat that would swamp papers/ and
    # wreck quote-matching.
    text = (
        "<!-- ===== page 1 ===== -->\n"
        "![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAQUJD==)\n"
        "# Real Title\nReal body text here.\n"
        "<!-- ===== page 2 ===== -->\nPlain page two\n"
    )
    pages = fold(text)
    assert "base64" not in pages[0]
    assert "data:image" not in pages[0]
    assert "# Real Title" in pages[0]
    assert "Real body text here." in pages[0]
    assert pages[1] == "Plain page two"


def test_fold_image_only_page_becomes_empty():
    # A page whose only content was a full-page image strips to empty (correct:
    # no extractable text), which the quality gate then counts as near-empty.
    text = (
        "<!-- ===== page 1 ===== -->\n"
        "![](data:image/png;base64,iVBORw0KGgoAAAANSU== )\n"
        "<!-- ===== page 2 ===== -->\nText\n"
    )
    pages = fold(text)
    assert pages[0] == ""
    assert pages[1] == "Text"


# --- mocr escalation control flow (render_pdf_with_fallback) ---------------
# The lower renderers are monkeypatched to fail the quality gate; we assert the
# escalation contract without invoking pymupdf4llm/docling/the GPU server.


def _fake_pdf(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4 fake bytes")
    return p


def _patch_lower_tiers_to_fail(monkeypatch):
    monkeypatch.setattr(renderer, "_render_with_pymupdf4llm", lambda pdf: [""] * 5)
    monkeypatch.setattr(renderer, "_render_with_docling", lambda pdf, ocr: [""] * 5)


def test_needs_mocr_when_cascade_exhausts_and_not_allowed(tmp_path, monkeypatch):
    _patch_lower_tiers_to_fail(monkeypatch)
    with pytest.raises(renderer.NeedsMocr):
        renderer.render_pdf_with_fallback(
            _fake_pdf(tmp_path),
            tmp_path / "out",
            progress=lambda *_: None,
            allow_mocr=False,
        )


def test_allow_mocr_without_session_still_needs_mocr(tmp_path, monkeypatch):
    # The flag alone is not enough; a live session must be supplied by the caller.
    _patch_lower_tiers_to_fail(monkeypatch)
    with pytest.raises(renderer.NeedsMocr):
        renderer.render_pdf_with_fallback(
            _fake_pdf(tmp_path),
            tmp_path / "out",
            progress=lambda *_: None,
            allow_mocr=True,
            mocr_session=None,
        )


def test_escalates_to_mocr_session_when_allowed(tmp_path, monkeypatch):
    _patch_lower_tiers_to_fail(monkeypatch)

    class FakeSession:
        def render(self, pdf):
            return (["Real readable page content here. " * 5] * 5, "/tmp/x_nohf.md")

    meta = renderer.render_pdf_with_fallback(
        _fake_pdf(tmp_path),
        tmp_path / "out",
        progress=lambda *_: None,
        allow_mocr=True,
        mocr_session=FakeSession(),
    )
    assert meta["renderer"] == "mocr"
    assert meta["ocr"] is True
    assert meta["source_md"] == "/tmp/x_nohf.md"
    assert (tmp_path / "out" / "full.md").exists()
    assert "mocr" in meta.get("renderer_note", "")


def test_mocr_session_output_still_quality_checked(tmp_path, monkeypatch):
    # If even mocr returns garbage, it's a hard RuntimeError, not a silent write.
    _patch_lower_tiers_to_fail(monkeypatch)

    class BadSession:
        def render(self, pdf):
            return ([""] * 5, None)

    with pytest.raises(RuntimeError):
        renderer.render_pdf_with_fallback(
            _fake_pdf(tmp_path),
            tmp_path / "out",
            progress=lambda *_: None,
            allow_mocr=True,
            mocr_session=BadSession(),
        )
