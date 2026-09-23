"""Read-only scholarly API queries; stdout is evidence, never a verification verdict.

No third-party dependencies. Example: search.py crossref search "latent interaction"
"""

# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

import argparse
import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

CONFIG_PATH = Path.home() / ".config/denubis-academic-research/scholar-api.json"
RATE_LOCK_PATH = Path.home() / ".cache/denubis-academic-research/semantic-scholar.lock"


@contextmanager
def request_slot(request):
    """Share the Semantic Scholar allowance across this user's local processes."""
    if urlsplit(request.full_url).hostname != "api.semanticscholar.org":
        yield
        return
    RATE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with RATE_LOCK_PATH.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # ponytail: one local lock; other machines/clients need shared coordination.
        # Wait inside the lock before every request, including after a worker dies.
        time.sleep(1.05)
        yield


def settings():
    """Load per-user settings; explicit environment values take precedence."""
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        config = {}
    except ValueError:
        raise ValueError("Invalid scholarly API configuration JSON") from None
    if not isinstance(config, dict) or any(
        not isinstance(value, str) or not value.strip() for value in config.values()
    ):
        raise ValueError("Invalid scholarly API configuration values")
    for field, names in {
        "mailto": ("LIT_SCOUT_MAILTO", "CROSSREF_MAILTO"),
        "s2_api_key": ("S2_API_KEY", "SEMANTIC_SCHOLAR_API_KEY"),
    }.items():
        value = next((os.environ[name] for name in names if os.environ.get(name)), None)
        if value:
            config[field] = value
    return config


def build_request(provider, action, value, *, limit=20, offset=0, page=1):
    """Restrict requests and credentials to the selected scholarly service."""
    headers = {"Accept": "application/json", "User-Agent": "denubis-literature-scout/1"}
    params = {}
    config = settings()
    contact = config.get("mailto")
    if provider in {"crossref", "datacite"}:
        if action not in {"search", "metadata"}:
            raise ValueError(f"{provider} supports search and metadata only")
        host, resource = (
            ("api.crossref.org", "works")
            if provider == "crossref"
            else ("api.datacite.org", "dois")
        )
        url = f"https://{host}/{resource}"
        if action == "search":
            params = {"query": value}
            params.update(
                {"rows": limit, "offset": offset}
                if provider == "crossref"
                else {"page[size]": limit, "page[number]": page}
            )
        else:
            doi = value.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
            url += "/" + quote(doi, safe="")
        if contact:
            params["mailto"] = contact
    elif provider == "semantic-scholar":
        url = "https://api.semanticscholar.org/graph/v1/paper/"
        fields = "title,authors,year,venue,externalIds,url,citationCount"
        if action == "search":
            url += "search"
            params = {"query": value, "limit": limit, "offset": offset}
        else:
            url += quote(value, safe="")
            if action in {"references", "citations"}:
                url += "/" + action
                params = {"limit": limit, "offset": offset}
        params["fields"] = fields
        if config.get("s2_api_key"):
            headers["x-api-key"] = config["s2_api_key"]
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return Request(  # noqa: S310 -- fixed HTTPS hosts
        url + ("?" + urlencode(params) if params else ""), headers=headers
    )


def retry_delay(header, minimum):
    """Retry-After may be a delay in seconds or an HTTP date."""
    if header:
        try:
            seconds = int(header)
        except ValueError:
            try:
                seconds = (
                    parsedate_to_datetime(header) - datetime.now(UTC)
                ).total_seconds()
            except ValueError, TypeError, OverflowError:
                seconds = 0
        return max(minimum, seconds)
    return minimum


def query(request):
    try:
        # Hold the shared allowance throughout backoff, so other Scout workers wait.
        with request_slot(request):
            for attempt in range(4):
                result = query_once(request)
                result["attempts"] = attempt + 1
                if (
                    result["http_status"] not in {429, 500, 502, 503, 504}
                    or attempt == 3
                ):
                    return result
                time.sleep(retry_delay(result.get("retry_after"), 2 ** (attempt + 1)))
    except OSError as error:
        return {
            "url": request.full_url,
            "status": "unavailable",
            "http_status": None,
            "error": str(error),
        }


def query_once(request):
    result = {"url": request.full_url, "retrieved_at": datetime.now(UTC).isoformat()}
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 -- fixed HTTPS hosts
            payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            return result | {
                "status": "ok",
                "http_status": response.status,
                "data": payload,
            }
    except HTTPError as error:
        error.close()
        return result | {
            "status": "not-found-here" if error.code == 404 else "unavailable",
            "http_status": error.code,
            "retry_after": error.headers.get("Retry-After"),
            "error": str(error.reason),
        }
    except (URLError, OSError, ValueError) as error:
        return result | {
            "status": "unavailable",
            "http_status": None,
            "error": str(error),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "provider", choices=["crossref", "datacite", "semantic-scholar"]
    )
    parser.add_argument(
        "action", choices=["search", "metadata", "references", "citations"]
    )
    parser.add_argument("value")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()
    if (
        not args.value.strip()
        or not 1 <= args.limit <= 100
        or args.offset < 0
        or args.page < 1
    ):
        parser.error(
            "Use a nonempty query/identifier, limit 1-100, offset >= 0 and page >= 1"
        )
    try:
        request = build_request(
            args.provider,
            args.action,
            args.value,
            limit=args.limit,
            offset=args.offset,
            page=args.page,
        )
    except (ValueError, OSError) as error:
        parser.error(str(error))
    result = query(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"ok": 0, "not-found-here": 2, "unavailable": 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
