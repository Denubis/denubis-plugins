"""Zotero 10 local-API write credentials, shared by every writing helper.

Zotero 10 authenticates writes in `LocalAPIEndpoint`, the base class every
local-API endpoint inherits — including every `zotero-api-plus` endpoint — so
the check runs before the endpoint's own code and no plugin change can opt out
of it. Read in Zotero 10.0.1's own
`chrome/content/zotero/xpcom/server/server_localAPI.js` (`_validateServerID`,
`_authenticateWriteRequest`, `AuthorizeLocal`), extracted from omni.ja on
2026-09-03:

  - a POST/PUT/PATCH/DELETE without a `Zotero-Server-ID` header is refused
    with 428 `Zotero-Server-ID not provided`;
  - a header that is not this server's ID is refused with 412;
  - no key, or a consumed/expired one, is refused with 401.

GET is not gated on any generation, so reads stay untouched.

Zotero 7-9 have none of this and send no `Zotero-Server-ID` response header.
That absence is the only signal separating the generations, so it is what this
module branches on: no header means no credentials, no key store, and a write
that goes out exactly as it did before.

The contract, end to end:

  1. `GET /api/` once per process; its `Zotero-Server-ID` header is the ID.
  2. `POST /api/local/authorize` with `{"appName": "denubis-academic"}` and
     that header. Zotero shows the human an Allow / Always Allow / Deny modal
     and answers `{"key": …, "remember": true|false}`. "Always Allow" keys are
     reusable and are written to the store; "Allow" keys are consumed by their
     first successful use, so they are kept in memory only — persisting one
     would guarantee a stale entry.
  3. Every write carries `Zotero-Server-ID` and `Zotero-API-Key`.

The store is skill-owned: `~/.config/denubis-academic-research/`
`zotero-local-api-keys.json`, mode 0600, mapping server ID to key. It sits
beside the user-owned `config.toml`, which this skill must never create or
alter. JSON rather than TOML because the standard library reads TOML but
cannot write it. `DENUBIS_ZOTERO_KEY_STORE` overrides the path.

httpx is imported inside the shell functions, like the rest of this skill's
helpers, so the pure core stays importable without the script dependencies.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

API_ROOT = "http://localhost:23119/api/"
AUTHORIZE_ENDPOINT = "http://localhost:23119/api/local/authorize"

SERVER_ID_HEADER = "Zotero-Server-ID"
API_KEY_HEADER = "Zotero-API-Key"

# Identifies this skill in Zotero's authorisation prompt and in its key list.
APP_NAME = "denubis-academic"

STORE_ENV = "DENUBIS_ZOTERO_KEY_STORE"
DEFAULT_STORE = (
    Path.home() / ".config" / "denubis-academic-research" / "zotero-local-api-keys.json"
)

# The probe is a local GET against an app that is either running or not.
PROBE_TIMEOUT = 5.0

# Authorisation blocks on a human noticing a modal and clicking it.
AUTHORIZE_TIMEOUT = 180.0


class AuthorizationError(RuntimeError):
    """Zotero would not issue a local API key, so no write can be attempted.

    Distinct from a transport failure: Zotero answered, and the answer was a
    denial, a rate limit, or something this module could not read. Callers
    surface it rather than retrying, because every retry re-prompts the human.
    """


# --- Functional core (pure) --------------------------------------------------


def write_headers(server_id: str | None, key: str | None) -> dict[str, str]:
    """The headers a write must carry for this server, if any.

    Empty on Zotero 7-9 (no server ID), which keeps that generation's requests
    byte-for-byte what they were. Server ID alone is the authorisation request
    itself, which `AuthorizeLocal` gates on the ID but not on a key.
    """
    if not server_id:
        return {}
    if not key:
        return {SERVER_ID_HEADER: server_id}
    return {SERVER_ID_HEADER: server_id, API_KEY_HEADER: key}


def classify_write_status(status: int) -> str:
    """Which credential, if either, a refused write is complaining about.

    `server-id` (428 absent, 412 mismatched) is fixed by re-reading the header;
    `key` (401) by authorising again. Everything else is the endpoint's own
    answer and must reach the caller untouched — retrying a 400 or a 500 could
    repeat a write that already landed.
    """
    if status in (428, 412):
        return "server-id"
    if status == 401:
        return "key"
    return "none"


def parse_authorize_response(
    status: int, body: str, content_type: str
) -> tuple[str, bool]:
    """The key and its reusability from `POST /api/local/authorize`.

    Zotero builds the 200 body as `JSON.stringify({ key, remember })`; a Deny
    answers 403 `{"denied": true}` and the rate limiter 429 text/plain. Every
    non-200 raises, because a write attempted without a key would only earn a
    401 whose meaning is harder to explain than this one.
    """
    if status == 200:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AuthorizationError(
                f"Zotero returned 200 from {AUTHORIZE_ENDPOINT} but the body "
                f"was not JSON ({content_type}): {body[:200]!r}"
            ) from exc
        key = parsed.get("key") if isinstance(parsed, dict) else None
        if not isinstance(key, str) or not key:
            raise AuthorizationError(
                f"Zotero returned 200 from {AUTHORIZE_ENDPOINT} without a key: "
                f"{body[:200]!r}"
            )
        return key, bool(parsed.get("remember"))

    if status == 403:
        raise AuthorizationError(
            f"Zotero denied local API access for {APP_NAME!r} (403). Re-run the "
            'command and choose "Always Allow" in Zotero to authorise writes.'
        )

    raise AuthorizationError(
        f"could not obtain a Zotero local API key (HTTP {status}): {body.strip()}"
    )


def server_id_from_headers(headers) -> str | None:
    """The `Zotero-Server-ID` value in a response's headers, if present.

    Matched case-insensitively: httpx's own Headers mapping is, a plain dict is
    not, and the header's case is the server's choice rather than ours. Absent
    means Zotero 7-9.
    """
    for name, value in headers.items():
        if name.lower() == SERVER_ID_HEADER.lower():
            return value.strip() or None
    return None


# --- Credential store --------------------------------------------------------


def store_path() -> Path:
    """Where the server-ID-to-key map lives; `DENUBIS_ZOTERO_KEY_STORE` wins.

    Read on every call rather than captured at import, so a test or a caller
    can redirect it without the module having been imported afterwards.
    """
    override = os.environ.get(STORE_ENV)
    return Path(override) if override else DEFAULT_STORE


def _read_store() -> dict[str, str]:
    """The store as a mapping, or empty when it is absent or unreadable.

    A truncated or hand-edited file reads as "no key", which sends the caller
    back through authorisation. Refusing to write because the cache is corrupt
    would be a worse answer than re-asking the human once.
    """
    path = store_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        # Absent, unreadable, or a path that is not a file. One clause rather
        # than a tuple of its subclasses: the repository formatter targets 3.14
        # and would rewrite a parenthesised tuple into PEP 758 syntax, which is
        # a SyntaxError for the >=3.11 scripts that import this module.
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {k: v for k, v in parsed.items() if isinstance(v, str)}


def _write_store(entries: dict[str, str]) -> None:
    """Replace the store with `entries`, readable only by this user.

    Created through os.open with the mode set at creation so the key is never
    briefly world-readable, then chmod'd so an existing loose file is tightened
    too. The parent directory is created only if missing and is not chmod'd:
    it also holds the user-owned config.toml.
    """
    path = store_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def load_key(server_id: str) -> str | None:
    """The stored reusable key for `server_id`, or None."""
    return _read_store().get(server_id)


def save_key(server_id: str, key: str) -> None:
    """Persist a reusable ("Always Allow") key for `server_id`."""
    entries = _read_store()
    entries[server_id] = key
    _write_store(entries)


def forget_key(server_id: str) -> None:
    """Drop `server_id`'s key from the store and from this process.

    Called when Zotero rejects the key, so the retry cannot pick the same dead
    key back up out of the cache it was just refused from.
    """
    _MEMORY_KEYS.pop(server_id, None)
    entries = _read_store()
    if entries.pop(server_id, None) is not None:
        _write_store(entries)


# --- Imperative shell --------------------------------------------------------


class _Cache:
    """Per-process probe state. An instance so no function needs `global`."""

    server_id: str | None = None
    probed: bool = False


_CACHE = _Cache()

# Single-use ("Allow") keys live here and nowhere else: they are consumed by
# their first successful write, so a stored copy would always be stale.
_MEMORY_KEYS: dict[str, str] = {}


def reset_cache() -> None:
    """Forget the probed server ID and any in-memory key."""
    _CACHE.server_id = None
    _CACHE.probed = False
    _MEMORY_KEYS.clear()


def _get_response_headers(url: str, timeout: float):
    """The response headers of a GET. The httpx seam for the server-ID probe."""
    import httpx

    return httpx.get(url, timeout=timeout).headers


def _http_post(url: str, *, json, headers: dict[str, str], timeout: float):
    """POST JSON with headers. The httpx seam every write goes through."""
    import httpx

    return httpx.post(url, json=json, headers=headers, timeout=timeout)


def fetch_server_id() -> str | None:
    """Read this Zotero's server ID from `GET /api/`; None on Zotero 7-9.

    Transport failures propagate: the caller's write was going to fail against
    the same unreachable Zotero, and its own error message says so better than
    a swallowed probe would.
    """
    headers = _get_response_headers(API_ROOT, timeout=PROBE_TIMEOUT)
    return server_id_from_headers(headers)


def server_id(*, refresh: bool = False) -> str | None:
    """The cached server ID, probing at most once unless `refresh` is set.

    Cached because a script may write several times and the ID is stable for a
    running Zotero; refreshed only when a 428/412 proves the cached value is
    wrong, which is what a Zotero restart mid-run looks like.
    """
    if refresh or not _CACHE.probed:
        _CACHE.server_id = fetch_server_id()
        _CACHE.probed = True
    return _CACHE.server_id


def request_key(server: str) -> str:
    """Ask Zotero for a local API key, prompting the human, and keep it.

    The notice goes to stderr before the request, because the request itself
    blocks until someone clicks the modal and an unexplained stall reads as a
    hang. A reusable key is stored; a single-use one is held in memory only.
    """
    print(
        f'Zotero is asking permission for "{APP_NAME}" to write through its '
        'local API. Approve the prompt in Zotero and choose "Always Allow" so '
        "this key can be reused.",
        file=sys.stderr,
        flush=True,
    )
    reply = _http_post(
        AUTHORIZE_ENDPOINT,
        json={"appName": APP_NAME},
        headers={SERVER_ID_HEADER: server},
        timeout=AUTHORIZE_TIMEOUT,
    )
    key, remember = parse_authorize_response(
        reply.status_code, reply.text, reply.headers.get("content-type", "")
    )
    if remember:
        save_key(server, key)
    else:
        _MEMORY_KEYS[server] = key
    return key


def credentials(*, refresh_server_id: bool = False) -> dict[str, str]:
    """The headers this Zotero requires on a write, authorising if needed.

    Empty on Zotero 7-9, and nothing is read from or written to the store
    there. On Zotero 10 a key is obtained eagerly rather than after a 401, so
    the human sees the modal before the write is attempted instead of between
    two attempts.
    """
    server = server_id(refresh=refresh_server_id)
    if not server:
        return {}
    key = _MEMORY_KEYS.get(server) or load_key(server)
    if not key:
        key = request_key(server)
    return write_headers(server, key)


def post(url: str, *, json, timeout: float):
    """POST a write to the local API with whatever credentials it requires.

    Retries at most once, and only for a refusal a credential can fix: a fresh
    server ID for 428/412, a fresh key for 401. The second response is returned
    as-is so the caller's own parser reports its status and body — retrying
    further would just re-prompt the human against a Zotero that has already
    said no twice.
    """
    headers = credentials()
    reply = _http_post(url, json=json, headers=headers, timeout=timeout)
    if not headers:
        # Zotero 7-9: there is no write gate here, so there is nothing to fix.
        return reply

    remedy = classify_write_status(reply.status_code)
    if remedy == "none":
        return reply
    if remedy == "server-id":
        server_id(refresh=True)
    else:
        stale = server_id()
        if stale:
            forget_key(stale)
    return _http_post(url, json=json, headers=credentials(), timeout=timeout)
