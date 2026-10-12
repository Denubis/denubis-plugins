# Troubleshooting

Anchor every helper to the installed plugin root:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
uv run "$BIB/resolve.py" --help
```

If neither provider root is set, the command is not running in an installed plugin
context. Invoke the skill from the installed plugin and inspect the provider's plugin
listing. Do not fall back to a source-tree-relative command.

## Plugin load errors

| Symptom | Bounded check | Corrective action |
|---|---|---|
| Error names `denubis-bib` | Locate and classify the exact emitting config/registry/cache file | CLI-manage registry/cache state; for an active setting, show the exact diff, back it up, and ask before replacing it; never create that alias |
| `denubis-bibliography` still installed | Inspect installed IDs and marketplace revision | Follow the retired-name migration in `setup-and-migration.md` |
| Marketplace says current but old code runs | Compare marketplace and installed versions; remember installs are cached copies | Run `claude plugin update denubis-academic@denubis-plugins --scope <discovered scope>`, restart, and compare again; if still stale, confirm the current-ID uninstall/reinstall branch |
| Skill command not found | Verify manifest name `denubis-academic` and skill directory/frontmatter `using-bibliography` | Invoke `/denubis-academic:using-bibliography` |
| Helper file not found | Print the resolved plugin root and test for the file | Use `$BIB`, resolved from the provider plugin root and independent of cwd |

Only use `~/.claude/bin/plugin-refresh denubis-plugins` for an intended full
**user-scope** refresh after reviewing its destructive cache/marketplace effects
and obtaining confirmation. Run it outside Claude Code, then restart.

## Resolver and Zotero failures

| Symptom | Meaning | Next check |
|---|---|---|
| Zotero ping fails | Desktop app/local API unavailable | Start Zotero and verify `http://localhost:23119/connector/ping` |
| Config missing | Skill does not know the zettelkasten root | Ask the user to create the documented config; do not create it silently |
| Exit `2` with near matches | Citekey is inexact | Copy and retry the exact returned key |
| No match by author or title word | Zotero's quicksearch ANDs every word over title, creators, year and citekey; a title filed differently returns nothing | Retry with one distinctive title token, a surname, or the exact citekey from the `.bib` |
| `warning: … could not be searched` | Part of the corpus was unreachable, so a no-match is inconclusive | Check the failing library URL in the message, then retry |
| `pdf-unknown` | Attachment truth was not established | Diagnose library/attachment lookup; do not collapse to `no-pdf` |
| `state: in trash`, exit `1` | The exact citekey is in Zotero's trash | Treat the item as trashed, not live. If it should be live, restore it in Zotero (or with `trash_item.py --restore`) and resolve again |
| No match by author/title/DOI, message names the trash exclusion | Those searches keep Zotero's trash exclusion | Resolve by the exact citekey, which does look in the trash |
| `no-pdf` | Item exists without a usable attachment | Ask for connector attachment or preview a confirmed fetch |
| API Plus helper reports endpoint absent | Installed extension is too old or unavailable | Upgrade the extension or use the non-writing fallback; do not hand-roll the endpoint |

`resolve.py` exits `0` for an exact resolved paper, `2` when it only surfaces
near citekey matches, and `1` for absence or error. Always interpret its printed
state with the exit code.

## Zotero 10 write credentials

Zotero 10 refuses an uncredentialed local-API write in the base class each
endpoint inherits. `zotero_auth.py` handles all three refusals, retrying once
and only for a refusal a credential can fix. Seeing one in a helper's output
means the retry also failed.

| Symptom | Meaning | What the helper did, and what to check |
|---|---|---|
| `HTTP 428: Zotero-Server-ID not provided` | The write carried no server ID | Re-read the ID from `GET /api/` and retried once. A repeat means the probe found no `Zotero-Server-ID` header on a Zotero that gates writes; check `curl -s -D - -o /dev/null http://localhost:23119/api/` |
| `HTTP 412: Zotero-Server-ID does not match this server` | The cached ID is not this Zotero's | Re-read the ID and retried once. A repeat usually means two Zotero instances on one port; confirm which is answering 23119 |
| `HTTP 401: API key required …` or `Invalid or expired API key` | No key, or a single-use key already consumed | Discarded the stored key, re-authorised (a Zotero modal), and retried once. A repeat means the prompt was denied or unanswered — re-run and choose "Always Allow" |
| `Zotero denied local API access … (403)` | Deny was clicked | Nothing was written. Re-run and choose "Always Allow" |
| `could not obtain a Zotero local API key (HTTP 429)` | Zotero's authorise rate limit | Wait for its `Retry-After` and re-run; do not loop the command |
| Zotero prompts on a *preview* | `update_item.py` and `copy_item.py` preview through a `POST` | Expected. Approve it; the preview still writes nothing |

The stored key lives in
`~/.config/denubis-academic-research/zotero-local-api-keys.json` (mode `0600`).
Deleting it only forces one more prompt. Zotero 7-9 never reach this path.

## Stock-API write helpers

| Symptom | Meaning | Next step |
|---|---|---|
| `stock writes need Zotero 10` | `GET /api/` sent no `Zotero-Server-ID`; this Zotero has no local-API write routes | Upgrade Zotero, or use the zotero-api-plus helpers that exist for Zotero 7-9; nothing was sent |
| `changed since preview: version is N, expected M` | The object changed between the preview and `--apply` | Re-run the preview and copy its new apply command; nothing was written |
| `target changed: collection is K, expected X` | A name resolved to a different key than the preview showed | Re-run the preview; nothing was written |
| `not accepted: conflict: … Zotero now holds version N` | Zotero answered 412 to `If-Unmodified-Since-Version` in the window after the re-read | Inspect the printed current object, re-run the preview; the helper never retries a conflict |
| `not accepted: refused: HTTP 403 …` | The library is not editable by this Zotero user | Check the group's permissions in Zotero |
| `accepted; not verified: <reason>` | Zotero took the request but the read-back did not show the change | Check the object in Zotero before repeating; the change may have landed |
| `--apply requires --expect-version` (usage error, exit 2) | The apply command was retyped without the expected-state flag | Copy the apply command the preview printed |

## Render failures

| Symptom | Correct response |
|---|---|
| Excessive empty/garbled pages | Let the bundled cascade escalate; do not run a one-off extractor |
| `NEEDS MOCR` | Explain the optional GPU tier and ask before `--allow-mocr` |
| `--allow-mocr` but no `[mocr]` config | Configure the existing deployment with user approval or stop |
| Non-PDF/non-HTML attachment fails | Verify `pandoc` is installed and on `PATH` |
| First OCR run downloads large dependencies/models | Use configured caches; never redirect package or model cache locations |
| Claimed render but no paper text | Positively check non-empty `full.md`, `meta.json`, and `pages/` |
| `advice: … re-run with --force-ocr` | The text layer sits under page-sized images on most pages (likely third-party OCR). Decide whether to re-render through OCR; either render still needs the source-page check for quotations |
| A paper rendered before 0.19 re-renders on next use | Expected: records below `render_version` 3 lack the extraction record |
| `limitation: source could not be described: …` | `describe_pdf` failed (PyMuPDF missing or an unreadable file); the render stands, the limitations list is incomplete |

Docling is deliberately pinned to EasyOCR by `renderer.py`; bypassing that code
can select a different engine and unexpected model host. The normal cascade is
the reproducible route.

## Quotation failures

`blockquote.py` performs whitespace and common-hyphen normalisation, then looks
for a substring in page Markdown. `NO MATCH` can mean extraction drift, a table
boundary, a paraphrase mistaken for a quotation, or genuinely absent wording.
Try a shorter exact substring and inspect the matching page; never invent text.

A Markdown match is `located`, whatever `meta.json` records about extraction.
The quotation is `verified` only after the physical source page has been
inspected; `NO MATCH` leaves it `unverified`.

## Platform notes

- Linux is the primary tested platform; macOS should use the same installed
  paths and commands.
- In PowerShell, `curl` is commonly an alias. Use `curl.exe` or
  `Invoke-RestMethod` for local Zotero probes.
- Windows Zotero attachment paths may contain drive-letter colons. Current code
  handles escaped and unescaped forms; a very old plugin reporting false
  `no-pdf` should be upgraded before further diagnosis.
- PowerShell stdin equivalent for DOI ingest is
  `Get-Content dois.txt | uv run "$env:CLAUDE_PLUGIN_ROOT/skills/using-bibliography/ingest.py" -`.
- Do not move config or zettelkasten paths to platform-specific locations merely
  to silence an error; first compare them with the user's intended shared setup.

## Unsupported operations

The skill does not automatically build the central zettelkasten bibliography,
generate permanent notes without an explicit request, bypass publisher/EZProxy
SSL, or verify a quotation without inspecting the source page. State the limit
instead of improvising another toolchain.
