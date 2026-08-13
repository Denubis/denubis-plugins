import importlib.util
import json
import subprocess
import sys
from pathlib import Path


_PATH = Path(__file__).resolve().parent.parent / "plugins/denubis-academic/skills/using-bibliography/renderer.py"
spec = importlib.util.spec_from_file_location("snapshot_renderer", _PATH)
assert spec and spec.loader
renderer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = renderer
spec.loader.exec_module(renderer)


def test_render_snapshot_extracts_readable_text(tmp_path):
    source = tmp_path / "index.html"
    source.write_text("<style>noise</style><h1>Title</h1><p>Hello <b>world</b>.</p><script>bad()</script>")
    out = tmp_path / "out"

    meta = renderer.render_snapshot(source, out)

    assert (out / "pages/001.md").read_text() == "Title\n\nHello world."
    assert "<!-- page:1 -->" in (out / "full.md").read_text()
    assert meta["renderer"] == "html.parser"
    assert json.loads((out / "meta.json").read_text())["source_attachment"] == str(source)


def test_unknown_attachment_uses_pandoc(tmp_path, monkeypatch):
    source = tmp_path / "notes.docx"
    source.write_bytes(b"fake")
    monkeypatch.setattr(
        renderer.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "# Notes\n", ""),
    )

    meta = renderer.render_attachment(source, tmp_path / "out")

    assert meta["renderer"] == "pandoc"
    assert (tmp_path / "out/pages/001.md").read_text() == "# Notes"
