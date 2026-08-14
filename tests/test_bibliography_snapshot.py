import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins/denubis-academic/skills/using-bibliography/renderer.py"
)
spec = importlib.util.spec_from_file_location("snapshot_renderer", _PATH)
assert spec and spec.loader
renderer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = renderer
spec.loader.exec_module(renderer)


def _rendered_output(out):
    """Parse the renderer's output contract into one structured result."""
    return {
        "page": (out / "pages/001.md").read_text(),
        "full": (out / "full.md").read_text(),
        "meta": json.loads((out / "meta.json").read_text()),
    }


def test_render_snapshot_extracts_readable_text(tmp_path):
    source = tmp_path / "index.html"
    source.write_text(
        "<style>noise</style><h1>Title</h1>"
        "<p>Hello <b>world</b>.</p><script>bad()</script>"
    )
    out = tmp_path / "out"

    renderer.render_snapshot(source, out)
    rendered = _rendered_output(out)

    assert rendered["page"] == "Title\n\nHello world."
    assert "<!-- page:1 -->" in rendered["full"]
    assert rendered["meta"]["renderer"] == "html.parser"
    assert rendered["meta"]["source_attachment"] == str(source)


def test_unknown_attachment_uses_pandoc(tmp_path, monkeypatch):
    source = tmp_path / "notes.docx"
    source.write_bytes(b"fake")
    monkeypatch.setattr(
        renderer.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "# Notes\n", ""
        ),
    )

    out = tmp_path / "out"
    renderer.render_attachment(source, out)
    rendered = _rendered_output(out)

    assert rendered["meta"]["renderer"] == "pandoc"
    assert rendered["page"] == "# Notes"
