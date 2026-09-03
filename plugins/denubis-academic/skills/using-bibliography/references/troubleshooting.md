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

## Render failures

| Symptom | Correct response |
|---|---|
| Excessive empty/garbled pages | Let the bundled cascade escalate; do not run a one-off extractor |
| `NEEDS MOCR` | Explain the optional GPU tier and ask before `--allow-mocr` |
| `--allow-mocr` but no `[mocr]` config | Configure the existing deployment with user approval or stop |
| Non-PDF/non-HTML attachment fails | Verify `pandoc` is installed and on `PATH` |
| First OCR run downloads large dependencies/models | Use configured caches; never redirect package or model cache locations |
| Claimed render but no paper text | Positively check non-empty `full.md`, `meta.json`, and `pages/` |

Docling is deliberately pinned to EasyOCR by `renderer.py`; bypassing that code
can select a different engine and unexpected model host. The normal cascade is
the reproducible route.

## Quotation failures

`blockquote.py` performs whitespace and common-hyphen normalisation, then looks
for a substring in page Markdown. `NO MATCH` can mean extraction drift, a table
boundary, a paraphrase mistaken for a quotation, or genuinely absent wording.
Try a shorter exact substring and inspect the matching page; never invent text.

For `meta.json` with `ocr: true`, a Markdown match is still only a locator. The
exact quote is unverified until visually checked against the physical PDF page.

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
SSL, or verify OCR quotations without visual source inspection. State the limit
instead of improvising another toolchain.
