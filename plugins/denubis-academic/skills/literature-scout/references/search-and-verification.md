# Search and verification

The bundled helper makes one read-only request and emits a JSON envelope with
the URL, retrieval time, HTTP status and original response. It uses Python's
standard library. It does not write to Zotero or turn API success into a
verification verdict.

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
SCOUT="$PLUGIN_DIR/skills/literature-scout/search.py"
uv run "$SCOUT" crossref search "latent interaction measurement" --limit 10
uv run "$SCOUT" crossref metadata "10.1037/1082-989X.9.3.275"
uv run "$SCOUT" semantic-scholar references "DOI:10.1037/1082-989X.9.3.275" --limit 20
uv run "$SCOUT" semantic-scholar citations "DOI:10.1037/1082-989X.9.3.275" --limit 20
uv run "$SCOUT" datacite metadata "10.48550/arXiv.1706.03762"
```

Crossref and DataCite support `search` and `metadata`; Semantic Scholar also
supports `references` and `citations`. Crossref metadata may contain a
`reference` list for backward chaining. Incomplete references are leads, not
verified identities. The helper returns one page; use `--offset` for Crossref
or Semantic Scholar lists, or `--page` (starting at 1) for DataCite search.
Retain the response's paging/total fields and record truncation. Do not infer
exhaustiveness from the helper's exit status.

Configure the per-user file
`~/.config/denubis-academic-research/scholar-api.json` with `mailto` and, when
issued, `s2_api_key` string fields. Keep it outside Git with permissions `0600`.
The helper reads it directly in any shell; restarting the host is unnecessary.
Environment overrides are `LIT_SCOUT_MAILTO` (fallback `CROSSREF_MAILTO`) and
`S2_API_KEY` (fallback `SEMANTIC_SCHOLAR_API_KEY`). Use the actual
operator's address before routine use. Both Crossref and DataCite accept it in
the `mailto` parameter for identified access; unset means unidentified access.
These public metadata APIs do not require a paid or member key for this workflow.
`S2_API_KEY` is sent only to Semantic Scholar; obtain a personal key through its
[API application](https://www.semanticscholar.org/product/api).
Store credentials outside the repository and inject them through the local
credential/environment setup. Never put keys in reports. Provider-specific accounts/tools are optional;
use available scholarly search and publisher sites to cover service gaps.

| Result | Meaning | Action |
|---|---|---|
| exit 0, `ok` | Received JSON | Inspect its contents and field coverage; an empty list is only this query's result |
| exit 2, `not-found-here` | This endpoint returned HTTP 404 | Check identifier/version and another appropriate registry or publisher |
| exit 1, `unavailable` | Throttle, authentication, server/network error, invalid JSON or unexpected payload | Preserve the candidate and mark the check incomplete |

On Linux/macOS, the helper serialises Semantic Scholar requests across this
user's local Scout processes using
`~/.cache/denubis-academic-research/semantic-scholar.lock`. It waits 1.05 seconds
inside the lock before the first attempt and holds it through all retries.
All endpoints share this allowance. Other clients or machines using the same key
must be coordinated separately; leave the lock file in place while Scout runs.
Crossref and DataCite requests should also be paced serially.
For HTTP 429, 500, 502, 503 and 504, the helper retries up to three times with
exponential waits of 2, 4 and 8 seconds. A longer `Retry-After` (seconds or HTTP
date) takes precedence. Semantic Scholar's shared lock remains held during these
waits, so other local Scout processes also pause. The response records `attempts`.
Authentication failures, missing records, malformed responses and network errors
are returned without automatic retries. After exhausted retries, preserve any
remaining `retry_after` before another invocation; report the gap or use another
source rather than starting another immediate retry cycle. Never delete a candidate because
the provider could not answer. Do not treat a null reference list as an attested
zero. The helper does not automatically follow all citation links.

## Scout collection and reading gate

Keep speculative search hits in the candidate log. Promote a candidate when its
metadata or abstract gives a concrete reason to read it for the research question;
full-text usefulness is not a prerequisite for acquisition.

1. Resolve promoted candidates against Zotero first. Put sources worth reading
   in a dedicated scout subcollection under the project's collection, for example
   `Scout — <topic> — <date>`. Reuse existing items by collection membership rather
   than creating duplicates. Record the actual library and collection keys; never
   guess keys or silently fall back to the library root. If the destination is
   unclear or collection management is unavailable, resolve that before acquisition.
2. Acquire through [using-bibliography](../../using-bibliography/SKILL.md), within
   the user's authorised scope and destination. Preview the batch; ask only for
   authorisation not already given. Use `fetch.py --no-render` for this phase.
   For DOI-less sources or existing items missing attachments, use the supported
   Zotero import/attachment workflow or ask the user to attach them. Direct PDF
   downloads to scratch, project evidence folders or a browser/PDF tool are not
   substitutes, even from open publisher URLs or just to inspect a byline. Full
   HTML papers follow the same managed-source workflow; ordinary metadata pages
   and abstracts remain available for discovery.
3. Account for every promoted candidate's attachment state before starting the
   reading phase. Keep plausible sources without full text on the shortlist and
   escalate them together: citation, DOI/publisher URL, Zotero item if present,
   reason to read, and missing/failed/unknown access state. Ask the user to supply
   attachments through Zotero or decide which to defer. Pause full-text reading
   until that decision or the missing attachments arrive; metadata work may
   continue. A failed lookup is not proof that no full text exists. Apply the gate
   again when later citation tracing adds sources worth reading.
4. Read from Zotero-managed sources through using-bibliography. Evidence records
   reference the item, managed render and page locators rather than copying PDFs
   or full-text extractions into the project. Record deferred sources and their
   effect on coverage. Sources found unhelpful after reading may be nominated for
   later cleanup, with a reason; do not automatically remove collection membership
   or trash items. Any approved cleanup must account for use elsewhere in Zotero.

Pass these acquisition constraints and the unresolved shortlist to every delegated
reviewer. Independent verification does not authorise independent downloading.

## Candidate and verification records

Use a stable row ID and record: supplied and resolved identifiers; full metadata
or its saved response path; source/version; relevance and the passage/abstract
that supports it; known Zotero citekey or unresolved state; discovery route;
per-field verification status and evidence URL/date.

Build the identity handoff from the candidate table and all inspected metadata
sources, rather than copying one provider response. Include each proposed identity
field with its observed value and evidence URL or saved-response location. Preserve
missing or conflicting provider values separately: a registry null must not erase
an author or date found on a publisher page. Leave genuinely unknown fields unknown.
Compare the packet with the table before handing it over. Include bibliographic
observations as claims to check; omit relevance arguments, preferred verdicts and
hints about which rows the verifier should challenge.

The verifier re-fetches metadata without the proposer's reasoning. Return each
field as supported, corrected, conflicting or unchecked, with its observed value.
An alternative metadata provider is useful where errors may be shared, but do not
force agreement between registries describing different versions. Distinguish
online-first and issue years. Correcting metadata may require reopening the
relevance assessment, not merely editing one table cell.

Completion requires every candidate to have an explicit disposition, including
unchecked ones. Report an empty search as zero candidates, not as a successful
verification. Narrative claims about methods/results require source reading via
using-bibliography. No metadata-only verdict may be promoted to source fidelity.

API contracts checked 2026-09-22:
[Crossref REST](https://api.crossref.org/swagger-ui/index.html),
[Semantic Scholar Graph](https://api.semanticscholar.org/api-docs/graph),
[DataCite queries](https://support.datacite.org/docs/api-queries).
Identified access: [Crossref access](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)
and [DataCite rate limits](https://support.datacite.org/docs/rate-limit).
