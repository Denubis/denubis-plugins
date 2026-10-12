"""Tests for plugins/denubis-academic/skills/using-bibliography/renderer.py.

Quality-heuristic coverage: empty pages, marker-only pages (Levenson 1973
case), marker + content pages (Vanlissa 2024 case), U+FFFD ratio
(Stephens 2000 case), threshold edges.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

_RENDERER = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
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


def test_pymupdf_disables_implicit_ocr_and_checks_page_identity(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "pymupdf",
        SimpleNamespace(
            open=lambda _: nullcontext([1, 2]),
        ),
    )
    chunks = [
        {"metadata": {"page_number": n}, "text": f"Printed page {n}. " * 10}
        for n in (1, 2)
    ]

    def to_markdown(doc, **options):
        assert options == {
            "page_chunks": True,
            "use_ocr": False,
            "header": True,
            "footer": True,
        }
        return chunks

    monkeypatch.setitem(
        sys.modules, "pymupdf4llm", SimpleNamespace(to_markdown=to_markdown)
    )
    out = tmp_path / "out"
    meta = renderer.render_pdf_with_fallback(_fake_pdf(tmp_path), out)
    assert meta["ocr"] is False
    assert (
        json.loads((out / "meta.json").read_text())["render_version"]
        == renderer.RENDER_VERSION
    )
    assert renderer._render_with_pymupdf4llm(tmp_path / "x.pdf") == [
        chunk["text"] for chunk in chunks
    ]
    chunks.reverse()
    with pytest.raises(RuntimeError, match="misordered"):
        renderer._render_with_pymupdf4llm(tmp_path / "x.pdf")
    chunks.pop()
    with pytest.raises(RuntimeError, match="incomplete"):
        renderer._render_with_pymupdf4llm(tmp_path / "x.pdf")


def test_docling_isolates_pages_before_paragraph_merge_and_keeps_furniture(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "pymupdf",
        SimpleNamespace(
            open=lambda _: nullcontext([1, 2]),
        ),
    )
    calls = []
    ocr_options = []
    texts = {1: "A paragraph ending on page 296.", 2: "Its continuation on page 297."}

    class Converter:
        def __init__(self, **kwargs):
            ocr_options.append(
                kwargs["format_options"]["pdf"]["pipeline_options"]["ocr_options"]
            )

        def convert(self, path, *, page_range):
            calls.append(page_range)
            first, last = page_range
            assert first == last  # merging must never see adjacent pages

            def export_to_markdown(**options):
                assert options["included_content_layers"] == {"body", "furniture"}
                assert "page_footer" in options["labels"]
                assert options["traverse_pictures"] is True
                return texts[first] + f"\n{295 + first}"

            return SimpleNamespace(
                document=SimpleNamespace(
                    pages={first: object()},
                    export_to_markdown=export_to_markdown,
                )
            )

    modules = {
        "docling.datamodel.base_models": SimpleNamespace(
            InputFormat=SimpleNamespace(PDF="pdf")
        ),
        "docling.datamodel.pipeline_options": SimpleNamespace(
            EasyOcrOptions=lambda **kw: kw,
            OcrMode=SimpleNamespace(FULL_PAGE="full_page"),
            PdfPipelineOptions=lambda **kw: kw,
        ),
        "docling.document_converter": SimpleNamespace(
            DocumentConverter=Converter,
            PdfFormatOption=lambda **kw: kw,
        ),
        "docling_core.types.doc": SimpleNamespace(
            ContentLayer={"body", "furniture"},
            DocItemLabel={"text", "page_footer"},
        ),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    pages = renderer._render_with_docling(Path("paper.pdf"), ocr=False)
    assert calls == [(1, 1), (2, 2)]
    assert pages == [texts[1] + "\n296", texts[2] + "\n297"]
    # The ordinary OCR tier keeps Docling's default mode, which OCRs bitmap
    # regions and keeps programmatic text cells. The forced tier OCRs the whole
    # page so an embedded (third-party OCR) layer is replaced, not merged.
    assert ocr_options[0] == {"lang": ["en"]}
    renderer._render_with_docling(Path("paper.pdf"), ocr=True, full_page_ocr=True)
    assert ocr_options[1] == {"lang": ["en"], "mode": "full_page"}


# Every renderer that has ever written a meta.json. A pre-0.19 record of ANY of
# them lacks the extraction record, so the version test exempts none of them.
_EVERY_RENDERER = ["pymupdf4llm", "docling", "mocr", "html.parser", "pandoc"]


@pytest.mark.parametrize("backend", _EVERY_RENDERER)
def test_pre_019_render_is_stale_for_every_renderer(backend):
    assert not renderer.render_metadata_is_current({"renderer": backend, "ocr": False})
    assert not renderer.render_metadata_is_current(
        {"renderer": backend, "ocr": True, "render_version": 2}
    )
    assert renderer.render_metadata_is_current(
        {"renderer": backend, "render_version": renderer.RENDER_VERSION}
    )


def test_render_version_is_three():
    assert renderer.RENDER_VERSION == 3


@pytest.mark.parametrize("backend", _EVERY_RENDERER)
def test_both_cache_readers_reject_pre_019_metadata(tmp_path, monkeypatch, backend):
    monkeypatch.syspath_prepend(str(_RENDERER.parent))
    import ingest
    import resolve

    pdf = _fake_pdf(tmp_path)
    out = tmp_path / "cache"
    out.mkdir()
    (out / "full.md").write_text("Cached paper")
    meta = {
        "renderer": backend,
        "ocr": backend == "mocr",
        "render_version": 2,
        "sha256_prefix": hashlib.sha256(pdf.read_bytes()).hexdigest()[:16],
    }
    (out / "meta.json").write_text(json.dumps(meta))
    assert not resolve.render_is_present(out)
    assert not ingest.current_render_matches(out, pdf)
    meta["render_version"] = renderer.RENDER_VERSION
    (out / "meta.json").write_text(json.dumps(meta))
    assert resolve.render_is_present(out)
    assert ingest.current_render_matches(out, pdf)


def test_explicit_ocr_fallback_is_labelled(tmp_path, monkeypatch):
    monkeypatch.setattr(renderer, "_render_with_pymupdf4llm", lambda pdf: [""])
    monkeypatch.setattr(
        renderer,
        "_render_with_docling",
        lambda pdf, ocr: ["Recovered scanned text. " * 10] if ocr else [""],
    )
    meta = renderer.render_pdf_with_fallback(_fake_pdf(tmp_path), tmp_path / "out")
    assert meta["renderer"] == "docling"
    assert meta["ocr"] is True
    assert meta["extraction"] == "ocr"
    assert meta["forced"] is False


# --- extraction record (0.19, Contract 1) ------------------------------------
# meta.json describes how the text was extracted and what the renderer could
# cheaply observe about the source. It never says the text is safe to quote.


def _stub_describe(monkeypatch, description):
    monkeypatch.setattr(renderer, "describe_pdf", lambda pdf: description)


def test_write_outputs_records_extraction_forced_and_limitations(tmp_path):
    out = tmp_path / "out"
    meta = renderer._write_outputs(
        ["Page one text. " * 10],
        _fake_pdf(tmp_path),
        out,
        "pymupdf4llm",
        False,
        [],
        extraction="text-layer",
        forced=False,
        limitations=["7 pages have no extractable text"],
    )
    on_disk = json.loads((out / "meta.json").read_text())
    for record in (meta, on_disk):
        assert record["extraction"] == "text-layer"
        assert record["forced"] is False
        assert record["limitations"] == ["7 pages have no extractable text"]
        assert record["render_version"] == 3
        # Existing readers keep their keys.
        assert record["renderer"] == "pymupdf4llm"
        assert record["ocr"] is False


def test_unforced_text_layer_render_records_text_layer(tmp_path, monkeypatch):
    _stub_describe(monkeypatch, None)
    monkeypatch.setattr(
        renderer, "_render_with_pymupdf4llm", lambda pdf: ["Clean text. " * 10]
    )
    meta = renderer.render_pdf_with_fallback(
        _fake_pdf(tmp_path), tmp_path / "out", progress=lambda *_: None
    )
    assert meta["extraction"] == "text-layer"
    assert meta["forced"] is False
    assert meta["limitations"] == []


def test_forced_ocr_skips_the_non_ocr_tiers(tmp_path, monkeypatch):
    _stub_describe(monkeypatch, None)
    called: list[str] = []

    def pymupdf(pdf):
        called.append("pymupdf4llm")
        return ["Embedded layer. " * 10]

    def docling(pdf, ocr, *, full_page_ocr=False):
        called.append(f"docling ocr={ocr} full_page={full_page_ocr}")
        return ["OCR read text. " * 10]

    monkeypatch.setattr(renderer, "_render_with_pymupdf4llm", pymupdf)
    monkeypatch.setattr(renderer, "_render_with_docling", docling)
    meta = renderer.render_pdf_with_fallback(
        _fake_pdf(tmp_path), tmp_path / "out", progress=lambda *_: None, force_ocr=True
    )
    assert called == ["docling ocr=True full_page=True"]
    assert meta["renderer"] == "docling"
    assert meta["ocr"] is True
    assert meta["extraction"] == "ocr"
    assert meta["forced"] is True
    # Only the OCR tier ran (asserted on `called` above), so its pages are the
    # ones written; page_count confirms the single stubbed page landed.
    assert meta["page_count"] == 1


def test_forced_ocr_with_mocr_goes_straight_to_mocr(tmp_path, monkeypatch):
    _stub_describe(monkeypatch, None)
    called: list[str] = []
    monkeypatch.setattr(
        renderer,
        "_render_with_pymupdf4llm",
        lambda pdf: called.append("pymupdf4llm") or ["x" * 500],
    )
    monkeypatch.setattr(
        renderer,
        "_render_with_docling",
        lambda pdf, ocr: called.append(f"docling ocr={ocr}") or ["x" * 500],
    )

    class FakeSession:
        def render(self, pdf):
            called.append("mocr")
            return (["Mocr page text. " * 10], "/tmp/x_nohf.md")

    meta = renderer.render_pdf_with_fallback(
        _fake_pdf(tmp_path),
        tmp_path / "out",
        progress=lambda *_: None,
        force_ocr=True,
        allow_mocr=True,
        mocr_session=FakeSession(),
    )
    assert called == ["mocr"]
    assert meta["renderer"] == "mocr"
    assert meta["extraction"] == "ocr"
    assert meta["forced"] is True


def test_forced_ocr_without_allow_mocr_still_raises_needs_mocr(tmp_path, monkeypatch):
    _stub_describe(monkeypatch, None)
    monkeypatch.setattr(renderer, "_render_with_pymupdf4llm", lambda pdf: ["x" * 500])
    monkeypatch.setattr(renderer, "_render_with_docling", lambda pdf, ocr: [""] * 5)
    with pytest.raises(renderer.NeedsMocr):
        renderer.render_pdf_with_fallback(
            _fake_pdf(tmp_path),
            tmp_path / "out",
            progress=lambda *_: None,
            force_ocr=True,
        )


def test_limitations_for_the_paper_capture_scan():
    # Borgmann 2006 (Q1): every page is a page-sized image under an Acrobat
    # Paper Capture producer; the text layer is that plug-in's OCR.
    description = {
        "page_count": 311,
        "producer": "Adobe Acrobat 9.55 Paper Capture Plug-in",
        "full_page_image_pages": 311,
        "no_text_pages": 7,
    }
    out = renderer.limitations_for(description, ["ok"] * 311)
    assert out[0] == (
        "311 of 311 pages carry a page-sized image; the text layer is likely "
        "third-party OCR (producer: Adobe Acrobat 9.55 Paper Capture Plug-in)"
    )
    assert "7 pages have no extractable text" in out
    assert renderer.suggests_forced_ocr(
        {"extraction": "text-layer", "limitations": out}
    )
    # Once the text came from OCR the suggestion no longer applies.
    assert not renderer.suggests_forced_ocr({"extraction": "ocr", "limitations": out})


def test_limitations_for_a_clean_word_pdf_has_no_page_image_sentence():
    # Borgmann 1987 (Q2): 16 pages, no page-sized images, text on every page.
    description = {
        "page_count": 16,
        "producer": "Adobe PDF Library 19.12.68",
        "full_page_image_pages": 0,
        "no_text_pages": 0,
    }
    out = renderer.limitations_for(description, ["ok"] * 16)
    assert out == []
    assert not renderer.suggests_forced_ocr(
        {"extraction": "text-layer", "limitations": out}
    )


def test_limitations_for_a_minority_of_page_images_does_not_infer_ocr():
    # One full-page figure in a born-digital paper is reported, not diagnosed.
    description = {
        "page_count": 20,
        "producer": "LaTeX with hyperref",
        "full_page_image_pages": 1,
        "no_text_pages": 0,
    }
    out = renderer.limitations_for(description, ["ok"] * 20)
    assert out == ["1 of 20 pages carry a page-sized image"]
    assert not renderer.suggests_forced_ocr(
        {"extraction": "text-layer", "limitations": out}
    )


def test_limitations_for_counts_replacement_character_pages():
    out = renderer.limitations_for(None, ["fine", "bad �", "also ��"])
    assert out == ["replacement characters on 2 pages"]


def test_limitations_for_reports_an_unreadable_description():
    out = renderer.limitations_for({"error": "not a PDF"}, ["fine"])
    assert out == ["source could not be described: not a PDF"]


def test_describe_pdf_counts_page_sized_images_and_textless_pages(monkeypatch):
    class Page:
        def __init__(self, bbox, text):
            self.rect = SimpleNamespace(width=432.0, height=648.0)
            self._bbox = bbox
            self._text = text

        def get_image_info(self):
            return [{"bbox": self._bbox}] if self._bbox else []

        def get_text(self, kind):
            assert kind == "text"
            return self._text

    pages = [
        Page((0.0, 0.0, 432.0, 648.0), "ocr layer"),  # full-page image + text
        Page((10.0, 10.0, 100.0, 100.0), "a figure"),  # small image
        Page(None, "   "),  # no image, no text
    ]

    class Doc:
        def __init__(self):
            self.metadata = {"producer": "Adobe Acrobat 9.55 Paper Capture Plug-in"}

        def __iter__(self):
            return iter(pages)

        def __len__(self):
            return len(pages)

    monkeypatch.setitem(
        sys.modules, "pymupdf", SimpleNamespace(open=lambda _: nullcontext(Doc()))
    )
    assert renderer.describe_pdf(Path("x.pdf")) == {
        "page_count": 3,
        "producer": "Adobe Acrobat 9.55 Paper Capture Plug-in",
        "full_page_image_pages": 1,
        "no_text_pages": 1,
    }


def test_snapshot_and_pandoc_records_say_converted(tmp_path, monkeypatch):
    snapshot = tmp_path / "page.html"
    snapshot.write_text("<html><body><p>Snapshot body text.</p></body></html>")
    meta = renderer.render_snapshot(snapshot, tmp_path / "html-out")
    assert meta["extraction"] == "converted"
    assert meta["forced"] is False
    assert meta["limitations"] == []

    docx = tmp_path / "paper.docx"
    docx.write_bytes(b"fake")
    monkeypatch.setattr(
        renderer.subprocess,
        "run",
        lambda *_a, **_k: SimpleNamespace(stdout="Converted body text.\n"),
    )
    meta = renderer.render_attachment(docx, tmp_path / "docx-out")
    assert meta["renderer"] == "pandoc"
    assert meta["extraction"] == "converted"


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
