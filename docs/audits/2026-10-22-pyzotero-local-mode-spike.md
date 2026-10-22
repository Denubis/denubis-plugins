# pyzotero local mode spike, 2026-10-22

Brian asked whether the bibliography skill should use pyzotero for its Zotero local-API
transport, `zotero_local_api.py` and `zotero_auth.py` in
`plugins/denubis-academic/skills/using-bibliography/`. This is an assessment, not a
migration. No code, configuration or test changed, and pyzotero was not added to the
project. Scratch probes live under `/tmp/pyzspike-probes/`.

- Repository: `brian-ed3d-plugins`, branch `main`, HEAD `4b67540`. The two modules are
  unchanged since `8a0962b` (`git diff --stat 8a0962b 4b67540` over the skill is empty).
- Zotero: 10.0.6 (flatpak), server ID `g6bzZS56RsjG`, probed live on 2026-10-22.
- pyzotero: 1.15.2 for every probe. 1.16.0 is the current release, but the configured
  uv cooldown (`exclude-newer = "14 days"` in `~/.config/uv/uv.toml`) filters it until
  about 2026-10-27, so 1.16.0 was inspected as wheel contents only.
- Author: the `pyzotero-spike` teammate (Claude Opus 5.5), dispatched by `team-lead`.
- Out of scope, as briefed: Better BibTeX JSON-RPC and every `/api/plus/*` endpoint.
  ADR 0029 stands: writes use the stock local API, and delete means trash.

Evidence labels: **Observed** is a command run for this spike, named with its output.
**Source** is code read in an installed artefact. **Documented** is a claim in pyzotero's
own docs. **Inferred** gives its reasoning. **Not checked** is said wherever it applies.

## Recommendation

Do not swap. The deciding evidence is a hard dependency conflict. Every pyzotero
release with local writes, 1.14.0 through 1.16.0 and `main` on 2026-10-22, pins
`bibtexparser<2.0.0`. `resolve.py` and `register_export.py` pin `bibtexparser>=2.0.0b9`
and import `zotero_local_api`. Under PEP 723, uv refuses `pyzotero>=1.14` beside them,
and an unpinned `pyzotero` silently resolves to 1.6.11, which cannot write at all. Even
without that block the swap does not pay. pyzotero reproduced every read, trash and
conflict behaviour probed. But replacing the transport saves about 21 of 207 code lines.
It keeps all of `zotero_auth.py`, because the `/api/plus/*` writers need it. It keeps raw
httpx for collection PATCHes, because pyzotero has no collection PATCH and its batch
update rejects a rename body. And it adds nine distributions, about 1.1 MiB, plus a
second HTTP stack. Revisit only if pyzotero lifts its bibtexparser pin. Nothing here
needs a ruling from Brian.

Partial swaps were considered and also fail. Swapping only the writes grows the code: the
measured write path goes from 83 to 100 code lines. Swapping only the reads, for the
seven scripts that can take pyzotero, leaves two read transports for the same endpoints.

## 1. Release history and the local-mode surface

pyzotero has no changelog file. The repository root and `doc/` hold none, and 64 of 65
GitHub release bodies are empty (observed, GitHub contents and releases API). The
versions below therefore come from bisecting the released wheels with a signature probe
(observed):

```bash
uv run --no-project --quiet --with "pyzotero==$v" python -I surface.py
# prints: version, 'local' in __init__, hasattr authorize_local, local_api_key, server_id
```

```text
1.5.25: 1.5.25 False False False False
1.5.27: 1.5.27 True False False False
1.13.7: 1.13.7 True False False False
1.14.0: 1.14.0 True True True True
1.15.2: 1.15.2 True True True True
```

| Version | PyPI upload | What it added | Label |
|---|---|---|---|
| 1.5.27 | 2024-11-29 | `local=True`, read-only local mode. 1.5.25 lacks it; PyPI has no 1.5.26. | Observed |
| 1.14.0 | 2026-08-18 | `authorize_local()`, `server_id`, `local_api_key`, local writes. 1.13.7 lacks them. | Observed |
| 1.15.2 | 2026-09-18 | Newest version the uv cooldown permits. All probes ran on it. | Observed |
| 1.16.0 | 2026-10-13 | Current release. Adds a key file under `~/.config/pyzotero/` in the private `_helpers` module, used by its CLI and MCP server. | Observed (wheel contents) |

Stated limitations of local mode, from `doc/index.rst` on `main` and the context7 library
`/urschrei/pyzotero`, both read 2026-10-22 (documented):

- The local API has no `/items/new`. So `item_template()`, `attachment_simple()` and
  `attachment_both()` raise `CallDoesNotExistError`.
- Keyed writes need a `version` on each object or an explicit `last_modified`.
- The `locale` parameter is ignored, and Atom is unsupported.
- Requests go to `127.0.0.1`, and the default client ignores proxy settings.
- Local reads need Zotero 7.0.10 or later. Writes need a Zotero that sends
  `Zotero-Server-ID`, which is Zotero 10 on this machine.
- `delete_item` erases outright. The plugin would never call it under ADR 0029.

## 2. Live probes against Zotero 10.0.6

```bash
curl -sS --max-time 3 -D - -o /dev/null http://localhost:23119/api/
# HTTP/1.0 200 OK ... X-Zotero-Version: 10.0.6 ... Zotero-Server-ID: g6bzZS56RsjG
```

The probes compare pyzotero against the plugin's own functions on the same queries.
They were run with `uv run --no-project --with httpx --with pyzotero==1.15.2 python -I`.

| Probe | Result | Evidence |
|---|---|---|
| `Zotero(0, 'user', local=True)` lists My Library | Pass | `probe_reads.py` [1] |
| `library_type='group'` lists a real group's items | Pass | [1], group 5778122 of 36 |
| Query sweep over 37 libraries equals `search_items` | Pass | [3], 1804 parents each, identical key sets |
| noChildren under `titleCreatorYear` | Pass, same as the plugin | `probe_children.py` |
| DOI field search via `qmode='fields'` | Pass, same as the plugin | [4] |
| `includeTrashed` reaches a trashed item | Pass | [5], `D7IV2YRB` |
| `itemType` filter passes through | Pass | [6] |
| Collection items, children, subcollections | Pass, identical keys | [7] and `probe_children.py` |
| `authorize_local()` sends the server ID, and its key is sent on writes | Pass on a mock transport. Live not testable. | `probe_writes.py` [A1] [A2] |
| Keyless write carries the real server ID | Pass | [B1], 401 rather than 428 |
| 412 on a stale version surfaces separately from a server-ID 412 | Pass | [B2] [B3] [B4] |
| No mutation from any probe | Pass | [B6] |

Read probe output (observed):

```text
[1] user items(limit=5): 5 returned; endpoint=http://127.0.0.1:23119/api
[1] server_id captured from a read: 'g6bzZS56RsjG'
[1] groups(): 36 groups; first id=5778122
[1] group 5778122 items(limit=5): 5 returned; library.type=group
[2] items(q='the') without everything(): 100 returned; Total-Results=322; has next link=True; limit sent=100
[2] everything(items(q='the')): 322 returned
[3] plugin search_items('the'): 1804 parents; failed=0
[3] pyzotero sweep 'the': 1807 raw, 3 children server-side, 1804 parents
[3] key sets equal: True; only-plugin=0 only-pyz=0
[4] plugin search_doi_items: 2 exact matches
[4] pyzotero qmode=fields: 6 raw (4 children), 2 after the plugin's equality filter; sets equal=True
[4] same DOI via titleCreatorYear (control): 0 raw hits
[5] item(D7IV2YRB) direct read: deleted=True version=429
[5] quicksearch without includeTrashed: False (1 hits)
[5] quicksearch with includeTrashed=1: True (3 hits)
[5] plugin include_trashed=True finds it: True; default finds it: False
[6] fields + itemType=-attachment: 2 raw; attachments left=0; sent itemType=-attachment
[7] collections_sub(7YW829ID): 3 (meta.numCollections=3)
[7] plugin get_subcollections: 3; equal keys=True
```

The three child-type rows under `titleCreatorYear` are standalone attachments with
`parentItem=None` (observed, `probe_children.py`). Plain httpx returns the same three.
So the module docstring's claim that `titleCreatorYear` excludes children server-side
holds. `select_parent_items` drops standalone attachments by type in either transport.

```text
QFFS9864 itemType=attachment parentItem=None
2NHAALEJ itemType=attachment parentItem=None
6PA4K4XA itemType=attachment parentItem=None
collection TEX7GUUQ: pyzotero 7, plugin 7, equal keys=True; summarise_collection rows equal: True
children H8EJNCQW: pyzotero 1, plugin 1, equal keys=True
```

`D7IV2YRB` was confirmed trashed before use (observed, `curl .../users/0/items/D7IV2YRB`:
`"version":429,"deleted":true`). Nothing was untrashed or modified.

### Write path

**Safety argument (source).** Before any live write-path request, the installed
`server_localAPI.js` was read, extracted from the flatpak `omni.ja` to
`/tmp/pyzspike-zotero-src/`. Zotero checks the server ID in `init`, then the key in
`_authenticateWriteRequest`, then the per-object version in `writeSingleObject` at lines
2168-2200. All three come before `mergePatchJSON` and `saveTx`. Line 2232 saves only
`if (obj.hasChanged())`.

Each live PATCH therefore carried a stale precondition or no key, and it also re-sent the
item's current title. Even a passed precondition would have saved nothing. The target was
`SQDDD7ZE`, a live item at version 590. The key was the plugin's existing persistent key
for this server, read from its store and never printed. `authorize_local()` was not
called live, because it opens a consent dialog on Brian's screen and Zotero rate-limits
it.

```text
[A1] authorize_local -> {'key': 'MOCKKEY', 'remember': True}; request carried Zotero-Server-ID='MOCKSID', body={"appName":"denubis-academic"}
[A2] update_item returned True; PATCH headers: Zotero-Server-ID='MOCKSID' Zotero-API-Key='MOCKKEY' If-Unmodified-Since-Version='7'
[A2] PATCH body: {"key":"ABCD2345","version":7,"title":"x"}
[A3] last_modified=5 with payload version 7: header='5' body={"key":"ABCD2345","version":7,"title":"x"}
[A4] minimal trash payload (no version, last_modified=5): header='5' body={"key":"ABCD2345","deleted":true}
[B1] no key -> LocalAPIKeyRequiredError; server-id sent='g6bzZS56RsjG'
     body: 'Response: API key required -- POST /api/local/authorize to obtain one'
[B2] wrong server id -> ServerIDMismatchError (subclass of PreConditionFailedError: True); refused request was GET /api/itemFields
[B3 header path] -> PreConditionFailedError; ServerIDMismatchError=False; Response: item has been modified since specified version (expected 589, found 590)
[B4 body path] -> PreConditionFailedError; ServerIDMismatchError=False; Response: item version mismatch: expected 1590, found 590
[B5] plugin write_object stale -> status=conflict; current.version=590
[B6] after: version=590 (before 590); dateModified unchanged=True; title unchanged=True
```

What this establishes (observed unless labelled):

- pyzotero sends `If-Unmodified-Since-Version` and raises `PreConditionFailedError` on a
  version 412. It raises the subclass `ServerIDMismatchError` only when the body says
  `Zotero-Server-ID does not match`. The plugin's conflict-versus-refused split maps
  onto those two classes.
- A trash PATCH shaped like the plugin's, `{"deleted": true}` with `last_modified`, passes
  pyzotero's `check_items` field filter, which allows `deleted`.
- On success, `update_item` returns `True` and the `Last-Modified-Version` is only on
  `zot.request.headers`. On failure `zot.request` still holds the previous response, so
  an adapter must read status from the exception, not from `zot.request`.
- `update_item` issues one extra `GET /itemFields` per client for `check_items`.
- pyzotero sends `Zotero-Server-ID` on reads too, once it has captured it. A stale ID
  therefore fails reads, as [B2] shows, while the plugin's reads never send it.
- There is no 401 re-authorisation, server-ID refresh, or conflict re-read in pyzotero.
  An adapter keeps all three.
- pyzotero has no HTTP PATCH for collections (source, `_client.py:1384-1525`).
  `update_collection` is a full PUT. `update_collections` POSTs a batch, which Zotero
  merges like a PATCH (source, `server_localAPI.js:2078`). But pyzotero filters each
  payload against item fields, and it rejects `collection.py`'s rename body
  `{"name": ...}` with `InvalidItemFieldsError` (observed, `check_items` against the
  live `/itemFields`). It accepts a `{"deleted": true}` body. So renames, at least, stay
  on raw httpx. Whether a merging POST would satisfy ADR 0029's "PATCH with
  `deleted: true`" is a reading of that ruling. This spike does not make it, and the
  recommendation does not depend on it.

### Contradictions between docs and behaviour

1. **Pagination.** pyzotero's local-API section says "Results are not paginated by
   default, so `Zotero.everything()` is rarely needed" (documented). pyzotero sends
   `limit=100` on every read, and a 322-hit query returned 100 without `everything()`
   (observed, [2]). An adapter that trusted the doc would silently under-report, which
   is the failure `zotero_local_api.py`'s docstring exists to prevent.
2. **`last_modified` as an override.** pyzotero documents `last_modified` as overriding
   the version for the concurrency check. pyzotero always copies the payload's `version`
   into the body ([A3], observed). Zotero 10.0.6 checks a body `version` and then ignores
   the header (source, `server_localAPI.js:2170-2200`). The override is ineffective
   whenever the payload carries `version`. An accepted write in that combination was
   not tested live.
3. **When a single-use key is spent.** pyzotero's docs and this plugin's `zotero_auth.py`
   docstring both say an "Allow" key is consumed by the first successful write. Zotero
   10.0.6 consumes it in `_authenticateWriteRequest` (source, lines 189-202 and 676),
   before the version check. So a write that ends in a 412 or 403 also spends it. Not
   tested live, since it needs an "Allow" click. The plugin's handling still copes,
   because it forgets the key on 401 and re-asks.

## 3. What a swap would and would not remove

### Function mapping, `zotero_local_api.py`

| Function | pyzotero replacement | Outcome |
|---|---|---|
| `item_citekey`, `item_library`, `item_in_trash`, `library_base`, `select_parent_items`, `select_doi_matches`, `doi_citekeys`, `summarise_collection`, `warn_unsearched_libraries`, `search_doi_field` | None needed. They act on envelopes, which pyzotero returns unchanged. | Stay |
| `LibraryQueryError`, `LibrarySearch`, `StockWriteUnavailable`, `WriteResult`, `require_stock_writes` | None | Stay |
| `library_item_urls` | `Zotero(0,'user',local=True).groups()`, then one `Zotero(gid,'group',local=True)` per group | Replaced |
| `_fetch_all_pages` | `zot.everything(...)` | Removed |
| `fetch_search_page` | `zot.items(q=, qmode=, includeTrashed=1)` inside `everything()` | Rewritten, with exception translation |
| `get_collection_items` | `zot.collection_items(key, includeTrashed=1)` inside `everything()` | Rewritten |
| `_sweep`, `search_items`, `search_doi_items` | Loop over clients instead of URLs | Stay |
| `read_object` | `zot.item(key, includeTrashed=1)` or `zot.collection(...)` | Rewritten |
| `get_item_children` | `zot.children(key, includeTrashed=1)` inside `everything()` | Rewritten |
| `get_subcollections` | `zot.collections_sub(key)` inside `everything()` | Rewritten |
| `_http_request`, `_object_url`, `classify_write_reply` | No collection PATCH in pyzotero | Stay, for collections |
| `write_object` | Items: `zot.update_item({"key": k, **body}, last_modified=v)`. Collections: no PATCH, and `update_collections` rejects a rename body. | Split in two, plus an exception classifier |
| `create_objects` | `zot.create_items(bodies)` or `zot.create_collections(bodies)` | Rewritten, 401 retry kept |

### Function mapping, `zotero_auth.py`

Every function stays. `post()` serves the five `/api/plus/*` writers, which pyzotero cannot
address through its public API. The key store has no public pyzotero equivalent.
1.15.2 has no store. 1.16.0's store is in the private `_helpers` module, holds one server
ID, and uses a different path. `authorize_local()` could replace the HTTP half of
`request_key`, but only by importing pyzotero into `zotero_auth.py`. `resolve.py` imports
`zotero_auth.py`, so that hits the block in section 4.

### Line counts

Code lines exclude docstrings, comments and blank lines (measured with `ast` and
`tokenize`, `/tmp/pyzspike-probes/codelines.py`). The replacement figure comes from an
adapter sketch, `/tmp/pyzspike-probes/sketch/pyz_transport.py`, which keeps every public
signature. Its sweeps matched the plugin live on 2026-10-22 (observed): 1804 and 2288
parents for `the`, 2 and 4 for the trashed title, 2 for the DOI, and `deleted=True` for
`D7IV2YRB`. Its write path was parsed but never executed.

| Quantity | Code lines |
|---|---|
| Two modules in total (997 physical lines): 323 plus 163 | 486 |
| Transport-bound definitions in `zotero_local_api.py`, 13 of them | 207 |
| Removed outright: `_fetch_all_pages` and `library_item_urls` | 28 |
| Sketch replacement for the 13 definitions | 150 |
| Raw collection PATCH path still needed: `_http_request`, `_object_url`, `classify_write_reply` | 36 |
| New adapter inside the 150: client factory, exception translation, error classifier, item PATCH | 56 |
| Net saving | about 21, about 10 percent of the transport code |
| `zotero_auth.py` removed | 0 of 163 |

### Consumer scripts

| Script | Uses | Change under a swap |
|---|---|---|
| `annotate.py` | `search_items`, and `zotero_auth.post` to `/api/plus/*` | Dependency line gains `pyzotero>=1.14`. Resolves (observed). |
| `collection.py` | reads, writes, creates, subcollections | Dependency line only |
| `copy_item.py` | `zotero_auth` only, for `/api/plus/*` | None |
| `create_item.py` | `create_objects`, `read_object` | Dependency line only |
| `fetch.py` | `zotero_auth` only, for `/api/plus/*` | None |
| `ingest.py` | `search_doi_items` | Dependency line. Resolves beside docling and easyocr (observed). |
| `item_collections.py` | `read_object`, `write_object` | Dependency line only |
| `register_export.py` | `get_collection_items` | **Blocked**: bibtexparser v2 |
| `resolve.py` | `search_items`, `search_doi_items` | **Blocked**: bibtexparser v2 |
| `trash_item.py` | `read_object`, `write_object`, `get_item_children` | Dependency line only |
| `update_item.py` | `get_collection_items`, and `zotero_auth.post` | Dependency line only |

If signatures are kept, no consumer's Python changes. Exceptions must still be translated
into `LibraryQueryError`, and one-clause-per-exception style is required. The scripts
declare `>=3.11`, and the 3.14 formatter would rewrite a parenthesised tuple into
PEP 758 syntax.

Tests would need rework. `test_bibliography_zotero_local_api.py` holds 36 tests, with 13
references to `_http_request`, 5 to `fetch_search_page`, 2 to `library_item_urls`, and 4
`sys.modules` injections. Four consumer test files each reference `_http_request` once:
collection, create_item, item_collections and trash_item. How many tests depend on those
references was not checked.

## 4. Dependencies and runtime

Resolved trees, from `uv tree --script` on one-line PEP 723 scripts (observed):

```text
httpx v0.28.1: anyio, idna, typing-extensions, certifi, httpcore, h11
pyzotero v1.15.2: bibtexparser v1.4.4 (pyparsing), feedparser v6.0.14 (feedparser-sgmllib),
  httpx2 v2.13.1 (anyio, httpcore2, h11, idna, truststore), whenever v0.11.0
```

- `httpx2` is not httpx. It is a separate package, "The next generation HTTP client",
  from `pydantic/httpx2`. Under a swap, httpx stays for `/api/plus/*` and collection
  PATCHes, so scripts would carry both stacks.
- Download size, from PyPI file sizes for the wheel uv would pick on CPython 3.14 Linux
  x86_64 (observed). bibtexparser 1.4.4 is sdist-only, so uv builds it on first install.

| Tree | Distributions | Bytes |
|---|---|---|
| httpx today | 7 | 574,032 |
| pyzotero 1.15.2 | 13 | 1,429,379 |
| Added by pyzotero | 9 | 1,144,631 |

- `requires-python` is `>=3.10` for pyzotero and httpx2. pyzotero 1.15.2 imports and
  resolves under CPython 3.11.15 (observed, `uv run --no-python-downloads --python 3.11`).
- PEP 723 under `uv run --script` (observed):

```text
>=3.11, ["httpx", "pyzotero>=1.14"]                        -> pyzotero 1.15.2, authorize_local True
>=3.14, ["httpx", "bibtexparser>=2.0.0b9", "pyzotero>=1.14"] -> No solution found: pyzotero>=1.14.0
         depends on bibtexparser>=1.4.3,<2.0.0 and you require bibtexparser>=2.0.0b9
>=3.14, ["httpx", "bibtexparser>=2.0.0b9", "pyzotero"]      -> silently resolves pyzotero 1.6.11
```

- The block is not a resolver artefact. Both bibtexparser majors install as the
  `bibtexparser` package, and pyzotero imports it at module load
  (`_decorators.py:17`). It parses with `bibtexparser.bparser` (`_decorators.py:129`),
  which bibtexparser 2.1.0 does not ship and 1.4.4 does (observed, `find_spec`). pyzotero's `main`
  `pyproject.toml` still pins `<2.0.0` (observed 2026-10-22). The pin came from issue
  #230, closed 2025-09-20. GitHub issue search found zero open issues mentioning
  bibtexparser, and a second search over all issues found nine, all closed.

## 5. Not checked

- A live `authorize_local()` call, and Zotero's handling of a single-use key.
- Any accepted pyzotero write. Whether Zotero accepts a body carrying `key` on an
  accepted PATCH was read in source only: `mergePatchJSON` overlays it on JSON that
  already holds the same key.
- pyzotero's `create_items` and `create_collections` against this Zotero, including its
  `Zotero-Write-Token` header.
- Writes to a read-only group, which should be a 403 `UserNotAuthorisedError`.
- Trashed subcollections through pyzotero. The endpoint is the same, so behaviour should
  match, but this is inferred.
- Zotero 7 to 9, and pyzotero 1.16.0 at runtime. The uv cooldown blocks the latter.

## Outside this spike's scope

`copy_item.py:331-339`, inside `find_items`, runs its own `qmode=fields` sweep. It reads one page with
`limit=25` and skips a failing library with `except Exception: continue` (observed by
reading the source). Ticket L11 covers the skipped-library message. The single-page read
is a separate truncation risk that no ticket covers.
