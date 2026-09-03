"""Tests for using-bibliography/zotero_auth.py.

Zotero 10 authenticates every local-API write (POST/PUT/PATCH/DELETE) in the
base class each endpoint inherits, before the endpoint's own code runs:

  - no `Zotero-Server-ID` header      -> 428 'Zotero-Server-ID not provided'
  - a server ID that is not this one  -> 412
  - no key, or a consumed/expired one -> 401

Verified in Zotero 10.0.1's own source, `_validateServerID` and
`_authenticateWriteRequest` in chrome/content/zotero/xpcom/server/
server_localAPI.js (extracted from omni.ja on 2026-09-03). The key comes from
`POST /api/local/authorize`, whose 200 body that source builds as
`JSON.stringify({ key, remember: !!remember })`; a Deny answers 403
`{"denied":true}` and the rate limiter answers 429 text/plain.

Zotero 7-9 have none of this and emit no `Zotero-Server-ID` response header,
which is the only signal that separates the generations. Every assertion below
is written literally rather than imported from the module, so a change to a
header name, the store path, or the app name fails here instead of quietly
agreeing with itself.

No test touches the network or the real home directory: the httpx seams are
monkeypatched and the store path is redirected through the documented
environment override.
"""

from __future__ import annotations

import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest

_MODULE = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
    / "zotero_auth.py"
)

# The uv test environment has no httpx. Importing the module at all therefore
# proves the transport stays lazily imported inside the shell functions, the
# same rule the rest of this skill's helpers follow.
_SPEC = importlib.util.spec_from_file_location("zotero_auth_under_test", _MODULE)
assert _SPEC and _SPEC.loader
auth = importlib.util.module_from_spec(_SPEC)
sys.modules["zotero_auth_under_test"] = auth
_SPEC.loader.exec_module(auth)

AUTHORIZE = "http://localhost:23119/api/local/authorize"
JSON_CT = {"content-type": "application/json"}
ALWAYS_ALLOW = '{"key": "fresh-key", "remember": true}'


class Reply:
    """The subset of an httpx.Response the write path reads."""

    def __init__(self, status_code: int, text: str = "", headers: dict | None = None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """No cached probe leaks between tests, and no test writes to $HOME."""
    monkeypatch.setenv("DENUBIS_ZOTERO_KEY_STORE", str(tmp_path / "keys.json"))
    auth.reset_cache()
    yield
    auth.reset_cache()


# --- write headers (pure) ----------------------------------------------------


class TestWriteHeaders:
    def test_no_server_id_sends_nothing(self):
        # Zotero 7-9: the generation with no write gate must stay byte-for-byte
        # unchanged, so the header set is empty rather than partially filled.
        assert auth.write_headers(None, None) == {}
        assert auth.write_headers(None, "somekey") == {}
        assert auth.write_headers("", "somekey") == {}

    def test_server_id_alone_when_no_key_yet(self):
        assert auth.write_headers("g6bzZS56RsjG", None) == {
            "Zotero-Server-ID": "g6bzZS56RsjG"
        }

    def test_both_headers_when_authorised(self):
        assert auth.write_headers("g6bzZS56RsjG", "K3Y") == {
            "Zotero-Server-ID": "g6bzZS56RsjG",
            "Zotero-API-Key": "K3Y",
        }


# --- failure classification (pure) -------------------------------------------


class TestClassifyWriteStatus:
    def test_428_missing_server_id(self):
        assert auth.classify_write_status(428) == "server-id"

    def test_412_wrong_server_id(self):
        # Zotero restarted and minted a new ID; the cached one is now stale.
        assert auth.classify_write_status(412) == "server-id"

    def test_401_missing_or_consumed_key(self):
        assert auth.classify_write_status(401) == "key"

    @pytest.mark.parametrize("status", [200, 400, 403, 404, 422, 500])
    def test_everything_else_is_the_endpoint_talking(self, status):
        # 400/404/500 are the plugin's own answers and must reach the caller
        # unretried; retrying them would double a write that already landed.
        assert auth.classify_write_status(status) == "none"


# --- authorize response (pure) -----------------------------------------------


class TestParseAuthorizeResponse:
    def test_always_allow_returns_key_and_remember(self):
        body = json.dumps({"key": "abc123", "remember": True})
        assert auth.parse_authorize_response(200, body, "application/json") == (
            "abc123",
            True,
        )

    def test_single_use_allow_is_reported_as_not_remembered(self):
        body = json.dumps({"key": "abc123", "remember": False})
        assert auth.parse_authorize_response(200, body, "application/json") == (
            "abc123",
            False,
        )

    def test_deny_raises_with_the_reason(self):
        with pytest.raises(auth.AuthorizationError) as e:
            auth.parse_authorize_response(
                403, json.dumps({"denied": True}), "application/json"
            )
        assert "denied" in str(e.value).lower()

    def test_rate_limit_raises_with_the_status(self):
        with pytest.raises(auth.AuthorizationError) as e:
            auth.parse_authorize_response(
                429, "Too many authorization requests", "text/plain"
            )
        assert "429" in str(e.value)

    def test_bad_request_surfaces_the_body(self):
        with pytest.raises(auth.AuthorizationError) as e:
            auth.parse_authorize_response(400, "appName is required", "text/plain")
        assert "appName is required" in str(e.value)

    def test_unparseable_success_body_raises(self):
        with pytest.raises(auth.AuthorizationError):
            auth.parse_authorize_response(200, "<html>", "text/html")

    def test_success_without_a_key_raises(self):
        with pytest.raises(auth.AuthorizationError):
            auth.parse_authorize_response(
                200, json.dumps({"remember": True}), "application/json"
            )


# --- credential store --------------------------------------------------------


class TestStore:
    def test_default_path_sits_beside_the_user_config(self, monkeypatch):
        # config.toml is user-owned and must never be written; the key store is
        # skill-owned, JSON because the stdlib cannot write TOML.
        monkeypatch.delenv("DENUBIS_ZOTERO_KEY_STORE", raising=False)
        assert auth.store_path() == (
            Path.home()
            / ".config"
            / "denubis-academic-research"
            / "zotero-local-api-keys.json"
        )

    def test_environment_override_redirects_the_store(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DENUBIS_ZOTERO_KEY_STORE", str(tmp_path / "elsewhere.json"))
        assert auth.store_path() == tmp_path / "elsewhere.json"

    def test_round_trips_a_key_per_server_id(self):
        auth.save_key("SERVER-A", "key-a")
        auth.save_key("SERVER-B", "key-b")
        assert auth.load_key("SERVER-A") == "key-a"
        assert auth.load_key("SERVER-B") == "key-b"

    def test_unknown_server_id_has_no_key(self):
        auth.save_key("SERVER-A", "key-a")
        assert auth.load_key("SERVER-B") is None

    def test_absent_store_has_no_key(self):
        assert auth.load_key("SERVER-A") is None

    def test_store_is_private_to_the_user(self, monkeypatch, tmp_path):
        store = tmp_path / "nested" / "keys.json"
        monkeypatch.setenv("DENUBIS_ZOTERO_KEY_STORE", str(store))
        auth.save_key("SERVER-A", "key-a")
        mode = stat.S_IMODE(store.stat().st_mode)
        assert mode == 0o600, f"key store mode {mode:o}"

    def test_forget_removes_only_the_named_entry(self):
        auth.save_key("SERVER-A", "key-a")
        auth.save_key("SERVER-B", "key-b")
        auth.forget_key("SERVER-A")
        assert auth.load_key("SERVER-A") is None
        assert auth.load_key("SERVER-B") == "key-b"

    def test_forgetting_an_absent_entry_is_quiet(self):
        auth.forget_key("SERVER-A")
        assert auth.load_key("SERVER-A") is None

    def test_a_corrupt_store_reads_as_no_key(self, monkeypatch, tmp_path):
        # A truncated or hand-edited store must send the caller back through
        # authorisation, not abort a write with a JSON error.
        store = tmp_path / "keys.json"
        store.write_text("{not json", encoding="utf-8")
        monkeypatch.setenv("DENUBIS_ZOTERO_KEY_STORE", str(store))
        assert auth.load_key("SERVER-A") is None

    def test_a_corrupt_store_is_replaced_rather_than_appended_to(
        self, monkeypatch, tmp_path
    ):
        store = tmp_path / "keys.json"
        store.write_text("{not json", encoding="utf-8")
        monkeypatch.setenv("DENUBIS_ZOTERO_KEY_STORE", str(store))
        auth.save_key("SERVER-A", "key-a")
        assert json.loads(store.read_text(encoding="utf-8")) == {"SERVER-A": "key-a"}


# --- server ID probe ---------------------------------------------------------


class TestServerID:
    def test_reads_the_header_from_the_api_root(self, monkeypatch):
        seen: list[str] = []

        def fake(url, timeout):
            seen.append(url)
            assert timeout > 0
            return {"Zotero-Server-ID": "g6bzZS56RsjG"}

        monkeypatch.setattr(auth, "_get_response_headers", fake)
        assert auth.server_id() == "g6bzZS56RsjG"
        assert seen == ["http://localhost:23119/api/"]

    def test_probes_once_per_process(self, monkeypatch):
        calls = []

        def fake(url, timeout):
            calls.append(url)
            return {"Zotero-Server-ID": "g6bzZS56RsjG"}

        monkeypatch.setattr(auth, "_get_response_headers", fake)
        auth.server_id()
        auth.server_id()
        auth.server_id()
        assert len(calls) == 1

    def test_absent_header_is_zotero_7_to_9_and_is_also_cached(self, monkeypatch):
        calls = []

        def fake(url, timeout):
            calls.append(url)
            return {"Zotero-API-Version": "3"}

        monkeypatch.setattr(auth, "_get_response_headers", fake)
        assert auth.server_id() is None
        assert auth.server_id() is None
        assert len(calls) == 1

    def test_refresh_reprobes(self, monkeypatch):
        ids = iter(["OLD", "NEW"])

        def fake(url, timeout):
            return {"Zotero-Server-ID": next(ids)}

        monkeypatch.setattr(auth, "_get_response_headers", fake)
        assert auth.server_id() == "OLD"
        assert auth.server_id(refresh=True) == "NEW"
        assert auth.server_id() == "NEW"

    def test_header_lookup_is_case_insensitive(self, monkeypatch):
        # httpx.Headers is case-insensitive; a plain dict from a stub or a
        # different client is not, and the header's case is the server's choice.
        def fake(url, timeout):
            return {"zotero-server-id": "g6bzZS56RsjG"}

        monkeypatch.setattr(auth, "_get_response_headers", fake)
        assert auth.server_id() == "g6bzZS56RsjG"


# --- credentials -------------------------------------------------------------


def _forbid_post(monkeypatch, why):
    def explode(*a, **k):
        raise AssertionError(why)

    monkeypatch.setattr(auth, "_http_post", explode)


class TestCredentials:
    def test_zotero_7_to_9_sends_nothing_and_never_authorises(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: None)
        _forbid_post(monkeypatch, "Zotero 7-9 must not be asked to authorise")
        assert auth.credentials() == {}

    def test_zotero_7_to_9_creates_no_store_file(self, monkeypatch, tmp_path):
        store = tmp_path / "keys.json"
        monkeypatch.setenv("DENUBIS_ZOTERO_KEY_STORE", str(store))
        monkeypatch.setattr(auth, "fetch_server_id", lambda: None)
        auth.credentials()
        assert not store.exists()

    def test_a_stored_key_is_reused_without_prompting(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        auth.save_key("SERVER-A", "stored-key")
        _forbid_post(monkeypatch, "a stored key must not re-prompt the user")
        assert auth.credentials() == {
            "Zotero-Server-ID": "SERVER-A",
            "Zotero-API-Key": "stored-key",
        }

    def test_first_write_authorises_and_persists_an_always_allow_key(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        posts = []

        def fake_post(url, *, json, headers, timeout):
            posts.append((url, json, headers, timeout))
            return Reply(200, ALWAYS_ALLOW, JSON_CT)

        monkeypatch.setattr(auth, "_http_post", fake_post)

        assert auth.credentials() == {
            "Zotero-Server-ID": "SERVER-A",
            "Zotero-API-Key": "fresh-key",
        }

        assert len(posts) == 1
        url, body, headers, timeout = posts[0]
        assert url == AUTHORIZE
        assert body == {"appName": "denubis-academic"}
        # AuthorizeLocal still runs _validateServerID, so the header is required
        # on the authorisation request itself.
        assert headers == {"Zotero-Server-ID": "SERVER-A"}
        # The request blocks on a human clicking a modal.
        assert timeout >= 120

        assert auth.load_key("SERVER-A") == "fresh-key"

    def test_the_user_is_told_to_choose_always_allow(self, monkeypatch, capsys):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")

        def fake_post(url, *, json, headers, timeout):
            return Reply(200, ALWAYS_ALLOW, JSON_CT)

        monkeypatch.setattr(auth, "_http_post", fake_post)
        auth.credentials()
        captured = capsys.readouterr()
        assert "Always Allow" in captured.err
        assert "Zotero" in captured.err
        # The notice must not pollute a helper's stdout contract.
        assert captured.out == ""

    def test_a_single_use_key_is_used_but_not_persisted(self, monkeypatch):
        # "Allow" keys are consumed by their first successful use, so writing
        # one to disk would guarantee a stale entry on the next run.
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")

        def fake_post(url, *, json, headers, timeout):
            return Reply(200, '{"key": "once-only", "remember": false}', JSON_CT)

        monkeypatch.setattr(auth, "_http_post", fake_post)
        assert auth.credentials()["Zotero-API-Key"] == "once-only"
        assert auth.load_key("SERVER-A") is None

    def test_a_denied_prompt_raises_rather_than_writing_unauthenticated(
        self, monkeypatch
    ):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")

        def fake_post(url, *, json, headers, timeout):
            return Reply(403, '{"denied": true}', JSON_CT)

        monkeypatch.setattr(auth, "_http_post", fake_post)
        with pytest.raises(auth.AuthorizationError):
            auth.credentials()


# --- the write helper --------------------------------------------------------


class TestPost:
    def test_zotero_7_to_9_posts_bare_and_returns_the_reply(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: None)
        sent = []

        def fake_post(url, *, json, headers, timeout):
            sent.append((url, json, headers, timeout))
            return Reply(200, "{}")

        monkeypatch.setattr(auth, "_http_post", fake_post)
        url = "http://localhost:23119/api/plus/update-item"
        assert auth.post(url, json={"a": 1}, timeout=30).status_code == 200
        assert sent == [(url, {"a": 1}, {}, 30)]

    def test_a_successful_write_sends_both_headers_once(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        auth.save_key("SERVER-A", "stored-key")
        sent = []

        def fake_post(url, *, json, headers, timeout):
            sent.append(headers)
            return Reply(200, "{}")

        monkeypatch.setattr(auth, "_http_post", fake_post)
        auth.post("http://x.test/w", json={}, timeout=5)
        assert sent == [
            {"Zotero-Server-ID": "SERVER-A", "Zotero-API-Key": "stored-key"}
        ]

    def test_428_refetches_the_server_id_and_retries_once(self, monkeypatch):
        auth.save_key("SERVER-A", "stored-key")
        auth.save_key("SERVER-B", "other-key")
        probes = iter(["SERVER-A", "SERVER-B"])

        def fake_get(url, timeout):
            return {"Zotero-Server-ID": next(probes)}

        monkeypatch.setattr(auth, "_get_response_headers", fake_get)
        replies = iter([Reply(428, "Zotero-Server-ID not provided"), Reply(200, "{}")])
        sent = []

        def fake_post(url, *, json, headers, timeout):
            sent.append(headers)
            return next(replies)

        monkeypatch.setattr(auth, "_http_post", fake_post)
        assert auth.post("http://x.test/w", json={}, timeout=5).status_code == 200
        assert sent == [
            {"Zotero-Server-ID": "SERVER-A", "Zotero-API-Key": "stored-key"},
            {"Zotero-Server-ID": "SERVER-B", "Zotero-API-Key": "other-key"},
        ]

    def test_412_refetches_the_server_id_and_retries_once(self, monkeypatch):
        auth.save_key("SERVER-A", "stored-key")
        auth.save_key("SERVER-B", "other-key")
        probes = iter(["SERVER-A", "SERVER-B"])

        def fake_get(url, timeout):
            return {"Zotero-Server-ID": next(probes)}

        monkeypatch.setattr(auth, "_get_response_headers", fake_get)
        replies = iter(
            [
                Reply(412, "Zotero-Server-ID does not match this server"),
                Reply(200, "{}"),
            ]
        )

        def fake_post(url, *, json, headers, timeout):
            return next(replies)

        monkeypatch.setattr(auth, "_http_post", fake_post)
        assert auth.post("http://x.test/w", json={}, timeout=5).status_code == 200

    def test_401_reauthorises_and_retries_once(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        auth.save_key("SERVER-A", "consumed-key")
        write_replies = iter(
            [Reply(401, "Invalid or expired API key"), Reply(200, "{}")]
        )
        sent = []

        def fake_post(url, *, json, headers, timeout):
            if url == AUTHORIZE:
                return Reply(200, ALWAYS_ALLOW, JSON_CT)
            sent.append(headers)
            return next(write_replies)

        monkeypatch.setattr(auth, "_http_post", fake_post)
        assert auth.post("http://x.test/w", json={}, timeout=5).status_code == 200
        assert sent == [
            {"Zotero-Server-ID": "SERVER-A", "Zotero-API-Key": "consumed-key"},
            {"Zotero-Server-ID": "SERVER-A", "Zotero-API-Key": "fresh-key"},
        ]
        assert auth.load_key("SERVER-A") == "fresh-key"

    def test_401_discards_the_stale_key_before_reauthorising(self, monkeypatch):
        # The consumed key must not be handed back to the retry from the store.
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        auth.save_key("SERVER-A", "consumed-key")
        keys_at_authorize = []

        def fake_post(url, *, json, headers, timeout):
            if url == AUTHORIZE:
                keys_at_authorize.append(auth.load_key("SERVER-A"))
                return Reply(200, ALWAYS_ALLOW, JSON_CT)
            return Reply(401, "Invalid or expired API key")

        monkeypatch.setattr(auth, "_http_post", fake_post)
        auth.post("http://x.test/w", json={}, timeout=5)
        assert keys_at_authorize == [None]

    def test_a_second_failure_is_returned_rather_than_retried_again(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        auth.save_key("SERVER-A", "stored-key")
        writes = []

        def fake_post(url, *, json, headers, timeout):
            writes.append(url)
            return Reply(428, "Zotero-Server-ID not provided")

        monkeypatch.setattr(auth, "_http_post", fake_post)
        reply = auth.post("http://x.test/w", json={}, timeout=5)
        assert reply.status_code == 428
        assert reply.text == "Zotero-Server-ID not provided"
        assert writes == ["http://x.test/w", "http://x.test/w"]

    def test_a_repeated_401_authorises_only_once_more(self, monkeypatch):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        authorizations = []

        def fake_post(url, *, json, headers, timeout):
            if url == AUTHORIZE:
                authorizations.append(url)
                return Reply(200, ALWAYS_ALLOW, JSON_CT)
            return Reply(401, "API key required")

        monkeypatch.setattr(auth, "_http_post", fake_post)
        assert auth.post("http://x.test/w", json={}, timeout=5).status_code == 401
        # One authorisation to obtain the missing key, one as the 401 remedy;
        # the loop must not keep re-prompting the human after that.
        assert len(authorizations) == 2

    @pytest.mark.parametrize("status", [200, 400, 404, 422, 500])
    def test_an_endpoint_answer_is_never_retried(self, monkeypatch, status):
        monkeypatch.setattr(auth, "fetch_server_id", lambda: "SERVER-A")
        auth.save_key("SERVER-A", "stored-key")
        writes = []

        def fake_post(url, *, json, headers, timeout):
            writes.append(url)
            return Reply(status, "body")

        monkeypatch.setattr(auth, "_http_post", fake_post)
        assert auth.post("http://x.test/w", json={}, timeout=5).status_code == status
        assert len(writes) == 1
