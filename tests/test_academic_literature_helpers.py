"""Executable checks for portable discovery and annotation evidence helpers."""

import importlib.util
import io
import json
import shutil
import subprocess
import sys
from itertools import pairwise
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

SKILLS = Path(__file__).resolve().parents[1] / "plugins/denubis-academic/skills"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


search = load("literature_search", SKILLS / "literature-scout/search.py")


def test_scout_private_settings(tmp_path, monkeypatch):
    path = tmp_path / "scholar-api.json"
    monkeypatch.setattr(search, "CONFIG_PATH", path)
    for name in (
        "LIT_SCOUT_MAILTO",
        "CROSSREF_MAILTO",
        "S2_API_KEY",
        "SEMANTIC_SCHOLAR_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    assert search.settings() == {}
    path.write_text(
        json.dumps({"mailto": "operator@example.org", "s2_api_key": "saved-key"})
    )
    assert search.settings()["s2_api_key"] == "saved-key"
    request = search.build_request("datacite", "metadata", "10.1/test")
    assert request.get_header("X-api-key") is None
    assert "saved-key" not in request.full_url
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "legacy-env-key")
    assert search.settings()["s2_api_key"] == "legacy-env-key"
    monkeypatch.setenv("S2_API_KEY", "override-key")
    assert search.settings()["s2_api_key"] == "override-key"
    path.write_text('{"s2_api_key": "secret-but-malformed')
    with pytest.raises(ValueError, match="Invalid scholarly API configuration"):
        search.settings()


def test_search_requests_and_failures(monkeypatch):
    monkeypatch.setattr(search.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("LIT_SCOUT_MAILTO", "operator@example.org")
    monkeypatch.setenv("S2_API_KEY", "test-key")
    request = search.build_request("crossref", "metadata", "https://doi.org/10.1/a/b")
    assert "/10.1%2Fa%2Fb" in request.full_url
    assert request.get_header("X-api-key") is None
    assert parse_qs(urlparse(request.full_url).query)["mailto"] == [
        "operator@example.org"
    ]
    request = search.build_request("semantic-scholar", "references", "DOI:10.1/a")
    assert request.get_header("X-api-key") == "test-key"
    assert "/DOI%3A10.1%2Fa/references?" in request.full_url
    assert "mailto" not in request.full_url
    request = search.build_request("datacite", "search", "maps", page=2, limit=3)
    assert parse_qs(urlparse(request.full_url).query)["page[number]"] == ["2"]
    assert parse_qs(urlparse(request.full_url).query)["mailto"] == [
        "operator@example.org"
    ]
    assert request.get_header("X-api-key") is None
    with pytest.raises(ValueError):
        search.build_request("crossref", "citations", "10.1/a")
    for code, expected in [(404, "not-found-here"), (429, "unavailable")]:

        def fail(*args, code=code, **kwargs):
            raise HTTPError(request.full_url, code, "test", {"Retry-After": "60"}, None)

        monkeypatch.setattr(search, "urlopen", fail)
        result = search.query(request)
        assert result["status"] == expected
        assert result["retry_after"] == "60"
    for payload, expected in [(b'{"data": []}', "ok"), (b"broken", "unavailable")]:

        def response(*args, payload=payload, **kwargs):
            stream = io.BytesIO(payload)
            stream.status = 200
            return stream

        monkeypatch.setattr(search, "urlopen", response)
        assert search.query(request)["status"] == expected


def test_retry_backoff_is_bounded_and_honours_provider(monkeypatch):
    from urllib.request import Request

    request = Request("https://api.datacite.org/dois/test")
    waits = []
    calls = []
    monkeypatch.setattr(search.time, "sleep", waits.append)

    def fail(*args, **kwargs):
        calls.append(1)
        raise HTTPError(request.full_url, 429, "busy", {"Retry-After": "3"}, None)

    monkeypatch.setattr(search, "urlopen", fail)
    result = search.query(request)
    assert result["status"] == "unavailable"
    assert len(calls) == 4
    assert waits == [3, 4, 8]
    waits.clear()
    calls.clear()

    def recover(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 503, "busy", {}, None)
        response = io.BytesIO(b'{"data": []}')
        response.status = 200
        return response

    monkeypatch.setattr(search, "urlopen", recover)
    assert search.query(request)["status"] == "ok"
    assert waits == [2]
    assert search.retry_delay("Wed, 21 Oct 2015 07:28:00 GMT", 2) == 2
    assert search.retry_delay("invalid", 4) == 4
    assert search.retry_delay("120", 2) == 120
    waits.clear()

    def denied(*args, **kwargs):
        raise HTTPError(request.full_url, 403, "forbidden", {}, None)

    monkeypatch.setattr(search, "urlopen", denied)
    assert search.query(request)["attempts"] == 1
    assert waits == []


def test_semantic_requests_are_spaced_across_processes(tmp_path):
    runner = tmp_path / "request.py"
    runner.write_text("""
import importlib.util, io, sys, time
from pathlib import Path
from urllib.request import Request
from urllib.error import HTTPError
spec = importlib.util.spec_from_file_location("scout", sys.argv[1])
scout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scout)
scout.RATE_LOCK_PATH = Path(sys.argv[2])
def respond(request, **kwargs):
    print(time.monotonic(), flush=True)
    if sys.argv[3] == "references":
        raise HTTPError(request.full_url, 403, "test", {}, None)
    response = io.BytesIO(b'{"data": []}')
    response.status = 200
    return response
scout.urlopen = respond
scout.query(Request("https://api.semanticscholar.org/graph/v1/paper/" + sys.argv[3]))
""")
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                str(runner),
                str(SKILLS / "literature-scout/search.py"),
                str(tmp_path / "rate.lock"),
                endpoint,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for endpoint in ("search", "references", "citations")
    ]
    starts = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr
        starts.append(float(stdout.strip()))
    starts.sort()
    assert all(b - a >= 1.0 for a, b in pairwise(starts))


def test_annotation_cli_checks_source_page_and_ocr(tmp_path):
    # Copy the actual package and run elsewhere to exercise relative helper imports.
    installed = tmp_path / "installed"
    shutil.copytree(
        SKILLS / "annotated-bibliography", installed / "annotated-bibliography"
    )
    (installed / "using-bibliography").mkdir()
    shutil.copyfile(
        SKILLS / "using-bibliography/renderer.py",
        installed / "using-bibliography/renderer.py",
    )
    paper = tmp_path / "resolvedKey"
    (paper / "pages").mkdir(parents=True)
    (paper / "pages/001.md").write_text("The precise quotation.\n")
    (paper / "pages/002.md").write_text("A different page.\n")
    meta = {
        "renderer": "docling",
        "render_version": 2,
        "page_count": 2,
        "ocr": True,
        "sha256_prefix": "0123456789abcdef",
    }
    entry = {
        "citekey": paper.name,
        "source_sha256_prefix": meta["sha256_prefix"],
        "coverage": "Both pages read",
        "summary": "Summary",
        "positioning": "Context",
        "points": [
            {
                "physical_page": 1,
                "quote": "The precise quotation.",
                "paraphrase": "Paraphrase",
                "relevance": "Relevance",
            }
        ],
    }
    entry_path = tmp_path / "entry.json"

    def run():
        (paper / "meta.json").write_text(json.dumps(meta))
        entry_path.write_text(json.dumps(entry))
        result = subprocess.run(
            [
                sys.executable,
                str(installed / "annotated-bibliography/check.py"),
                str(entry_path),
                str(paper),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        return result.returncode, json.loads(result.stdout)

    code, result = run()
    assert code == 0 and result["matched"] == 1
    assert result["visual_verification_required"] is True
    assert result["interpretation_review"] == "not assessed by this tool"
    for page, quote in [
        (2, "The precise quotation."),
        (1, "the precise quotation."),
        (1, ""),
        (True, "The precise quotation."),
        (3, "The precise quotation."),
    ]:
        entry["points"][0].update(physical_page=page, quote=quote)
        assert run()[0] == 1
    entry["points"][0].update(physical_page=1, quote="The precise quotation.")
    for field, value in [
        ("sha256_prefix", "fedcba9876543210"),
        ("render_version", 1),
        ("ocr", None),
        ("page_count", 0),
    ]:
        old = meta[field]
        meta[field] = value
        assert run()[0] == 1
        meta[field] = old
    meta["ocr"] = False
    assert run()[1]["visual_verification_required"] is False
