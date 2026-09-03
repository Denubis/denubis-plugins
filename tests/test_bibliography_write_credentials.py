"""Every zotero-api-plus write in using-bibliography carries credentials.

Zotero 10 refuses a local-API write that arrives without `Zotero-Server-ID`
(428) and without a key from `POST /api/local/authorize` (401), in the base
class before the endpoint's own code runs. A bare `httpx.post` therefore fails
on Zotero 10 no matter what the endpoint would have done; `zotero_auth.post`
is the one place that attaches the headers and owns the retry policy.

These tests pin the seam rather than the transport: each script's write shell
is called with `zotero_auth.post` stubbed, and a stub `httpx` module whose
`post` raises stands in the module cache. A helper that still posts directly
fails on that stub instead of silently reaching a live Zotero.

The stub `httpx` also supplies the exception classes the shells catch, because
the uv test environment does not install httpx (it is a PEP 723 dependency of
the scripts themselves).

Read paths are deliberately not covered here: `GET` is ungated on every Zotero
generation, so adding headers to reads would be unverified ceremony.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

_SKILL_DIR = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
)


class _StubResponse:
    def __init__(self, status_code=200, text="{}", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {"content-type": "application/json"}

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self.text)


def _install_stub_httpx(monkeypatch):
    """Put an httpx in the module cache whose write verbs are forbidden.

    `get` is left working: reads are ungated on every Zotero generation, so a
    capability probe's GET is not what these tests are about.
    """
    stub = types.ModuleType("httpx")

    class HTTPError(Exception):
        pass

    class TransportError(HTTPError):
        pass

    def forbidden(*a, **k):
        raise AssertionError(
            "a Zotero write went out through httpx directly; it must go "
            "through zotero_auth.post so Zotero 10 credentials are attached"
        )

    def benign_get(*a, **k):
        return _StubResponse(200, "Zotero Local API Plus is running.")

    stub.HTTPError = HTTPError
    stub.TransportError = TransportError
    stub.HTTPStatusError = HTTPError
    stub.post = forbidden
    stub.put = forbidden
    stub.patch = forbidden
    stub.delete = forbidden
    stub.get = benign_get
    monkeypatch.setitem(sys.modules, "httpx", stub)
    return stub


def _load(name: str, filename: str):
    if str(_SKILL_DIR) not in sys.path:
        sys.path.insert(0, str(_SKILL_DIR))
    spec = importlib.util.spec_from_file_location(name, _SKILL_DIR / filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def recorder(monkeypatch):
    """Record the writes a script routes through zotero_auth.post."""
    _install_stub_httpx(monkeypatch)
    calls: list[dict] = []

    def fake_post(url, *, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _StubResponse()

    return calls, fake_post


def _route(monkeypatch, module, fake_post):
    monkeypatch.setattr(module.zotero_auth, "post", fake_post)


def test_fetch_add_item_goes_through_the_credentialed_post(monkeypatch, recorder):
    calls, fake_post = recorder
    fetch = _load("fetch_credentials_under_test", "fetch.py")
    _route(monkeypatch, fetch, fake_post)

    fetch.add_item("10.1234/abc", None, None)

    assert [c["url"] for c in calls] == [
        "http://localhost:23119/api/plus/add-item-by-id"
    ]
    assert calls[0]["json"] == {"identifier": "10.1234/abc"}


def test_copy_item_goes_through_the_credentialed_post(monkeypatch, recorder):
    calls, fake_post = recorder
    copy_item = _load("copy_credentials_under_test", "copy_item.py")
    _route(monkeypatch, copy_item, fake_post)

    copy_item.copy_item({"key": "ABCD1234", "toLibraryID": 1})

    assert [c["url"] for c in calls] == ["http://localhost:23119/api/plus/copy-item"]


def test_copy_item_capability_probe_goes_through_the_credentialed_post(
    monkeypatch, recorder
):
    # The probe is itself a POST, so on Zotero 10 it is gated too. Routing it
    # keeps a 428 from being mistaken for a diagnosis of the installed build.
    calls, fake_post = recorder
    copy_item = _load("copy_probe_credentials_under_test", "copy_item.py")
    _route(monkeypatch, copy_item, fake_post)

    copy_item.probe_copy_item()

    assert [c["url"] for c in calls] == ["http://localhost:23119/api/plus/copy-item"]


def test_update_item_dry_run_goes_through_the_credentialed_post(monkeypatch, recorder):
    # The preview is a POST as well: the endpoint computes the diff on a clone,
    # so `update_item.py` without --apply is gated exactly like the apply.
    calls, fake_post = recorder
    update = _load("update_credentials_under_test", "update_item.py")
    _route(monkeypatch, update, fake_post)

    update.update_item({"key": "VJD9K42D", "apply": False})

    assert [c["url"] for c in calls] == ["http://localhost:23119/api/plus/update-item"]
    assert calls[0]["json"] == {"key": "VJD9K42D", "apply": False}


def test_add_highlight_goes_through_the_credentialed_post(monkeypatch, recorder):
    calls, fake_post = recorder
    annotate = _load("annotate_hl_credentials_under_test", "annotate.py")
    _route(monkeypatch, annotate, fake_post)

    annotate.post_highlight({"key": "ABCD1234", "page": 3})

    assert [c["url"] for c in calls] == [
        "http://localhost:23119/api/plus/add-highlight"
    ]


def test_add_note_goes_through_the_credentialed_post(monkeypatch, recorder):
    calls, fake_post = recorder
    annotate = _load("annotate_note_credentials_under_test", "annotate.py")
    _route(monkeypatch, annotate, fake_post)

    annotate.post_note("ABCD1234", 3, "a note", None, None)

    assert [c["url"] for c in calls] == ["http://localhost:23119/api/plus/add-note"]


def test_run_autoexport_goes_through_the_credentialed_post(monkeypatch, recorder):
    calls, fake_post = recorder
    resolve = _load("resolve_credentials_under_test", "resolve.py")
    _route(monkeypatch, resolve, fake_post)

    assert resolve.post_run_autoexport("/tmp/p.bib") == (200, "{}")
    assert [c["url"] for c in calls] == [
        "http://localhost:23119/api/plus/run-autoexport"
    ]


def test_bbt_json_rpc_is_not_credentialed(monkeypatch, recorder):
    # Better BibTeX serves /better-bibtex/json-rpc from its own endpoint, not
    # from Zotero's LocalAPIEndpoint base class, so it has no write gate and
    # must not be dragged through the authorisation path.
    calls, fake_post = recorder
    resolve = _load("resolve_bbt_credentials_under_test", "resolve.py")
    _route(monkeypatch, resolve, fake_post)

    sent = []

    def bbt_post(url, *, json, timeout):
        sent.append(url)
        return _StubResponse(200, '{"result": []}')

    monkeypatch.setattr(sys.modules["httpx"], "post", bbt_post)
    resolve.rpc("item.search", ["x"])

    assert sent == ["http://localhost:23119/better-bibtex/json-rpc"]
    assert calls == []
