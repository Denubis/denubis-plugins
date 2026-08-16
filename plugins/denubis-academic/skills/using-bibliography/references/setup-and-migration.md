# Setup and migration

This is the colleague-facing installation and recovery runbook. Keep plugin,
marketplace, and skill identifiers distinct:

| Kind | Current identifier |
|---|---|
| Marketplace | `denubis-plugins` |
| Plugin | `denubis-academic@denubis-plugins` |
| Skill command | `/denubis-academic:using-bibliography` |
| Retired plugin to remove | `denubis-bibliography@denubis-plugins` |

`denubis-bib` is not a valid current identifier. If an error displays that
string, locate the exact config, registry, prompt, or cached manifest that emits
it rather than creating an alias for a typo.

## Prerequisites

- Claude Code with plugin support.
- Git and `uv` on `PATH`.
- Python 3.14+ for `resolve.py`.
- Zotero running with Better BibTeX installed.
- `~/.config/denubis-academic-research/config.toml` containing at least:

  ```toml
  zettelkasten_root = "~/zettelkasten"
  ```

- An existing zettelkasten root. Do not create or relocate it silently.
- `pandoc` when rendering non-PDF, non-HTML attachments. PDF and HTML paths do
  not require it.
- Optional `zotero-api-plus`, by capability:

  | Capability | Minimum known version |
  |---|---|
  | Fetch by DOI/ISBN/PMID/arXiv | 0.3.0 |
  | Force a registered BBT auto-export | 0.4.0 |
  | Copy an item between libraries | 0.5.0 |
  | Repair item metadata | 0.6.0 |
  | PDF annotations | Build exposing the annotation endpoints; probe them |

Do not infer extension capability from a remembered version. The helpers probe
the endpoint they require and halt if it is absent.

## Fresh install

Inside Claude Code:

```text
/plugin marketplace add https://github.com/Denubis/denubis-plugins.git
/plugin marketplace update denubis-plugins
/plugin install denubis-academic@denubis-plugins
```

The default install scope is `user`. If the plugin belongs to one project, use
the shell CLI with `--scope project` or `--scope local` instead; do not silently
move an existing installation between scopes.

Restart Claude Code after installation, then invoke:

```text
/denubis-academic:using-bibliography
```

The installed plugin is copied into Claude's plugin cache. It must not depend on
the marketplace checkout, a developer source checkout, or the current working
directory.

## Migrate a retired or broken install

Begin read-only. Have Claude report, without changing anything:

1. the exact error text and the path that emitted it;
2. installed plugin IDs and versions;
3. the `denubis-plugins` marketplace source and revision;
4. every active reference to `denubis-bib`, `denubis-bibliography`, and
   `denubis-academic` in Claude plugin configuration and registries;
5. the available Zotero, Better BibTeX, `zotero-api-plus`, `uv`, Python, and
   Pandoc versions/capabilities.

Start with the CLI's structured inventory:

```bash
claude plugin list --json
claude plugin marketplace list --json
```

Use the returned scope, install/cache path, marketplace location, and source as
primary evidence. Standard user paths are
`~/.claude/plugins/installed_plugins.json`,
`~/.claude/plugins/marketplaces/denubis-plugins/`, and
`~/.claude/plugins/cache/denubis-plugins/`, but do not assume them when the CLI
reports another scope or path. Inspect only relevant fields and matches, not
whole credential-bearing files.

Do not paste API keys, OAuth tokens, cookies, or full credential files into the
report.

Classify every stale-name hit before changing it:

- an installed registry/cache entry is owned by the plugin CLI; use uninstall
  and install, not a manual JSON edit;
- an active user/project setting or permission requires an exact proposed diff,
  a backup, and separate confirmation before replacing the retired identifier;
- a historical log, review, changelog, or inactive old cache is evidence, not
  active configuration, and normally needs no edit.

After reviewing that inventory, preserve the discovered scope. For a user-scope
installation that contains the retired plugin but not the current one, update
the marketplace, remove only the retired plugin, and install the current one:

```text
/plugin marketplace update denubis-plugins
/plugin uninstall denubis-bibliography@denubis-plugins
/plugin install denubis-academic@denubis-plugins
```

The slash-command sequence above uses Claude's default user scope. If inventory
reports `project` or `local`, use the shell CLI with that exact scope instead.

The explicit user-scope shell sequence is:

```bash
claude plugin marketplace update denubis-plugins
claude plugin uninstall denubis-bibliography@denubis-plugins --scope user --keep-data
claude plugin install denubis-academic@denubis-plugins --scope user
```

For an existing `project` or `local` install, substitute that same supported
scope on both uninstall and install. Skip the uninstall when the retired plugin
is absent. Do not uninstall a literal `denubis-bib`: it is not a valid plugin ID;
repair the specific active setting that contains it behind the diff gate above.

If `denubis-academic@denubis-plugins` is already installed at an older version,
do not route through the retired-plugin sequence. Update that exact current ID
at its discovered scope (this example is user scope):

```bash
claude plugin marketplace update denubis-plugins
claude plugin update denubis-academic@denubis-plugins --scope user
```

Restart and compare the installed version with the refreshed marketplace. If
the update still selects stale cached code, show the exact mismatch and ask
before the narrower current-ID reinstall:

```bash
claude plugin uninstall denubis-academic@denubis-plugins --scope user --keep-data
claude plugin install denubis-academic@denubis-plugins --scope user
```

Again, substitute the discovered `project` or `local` scope on both commands.
Use the full `plugin-refresh` branch only when the intended target is the whole
user-scope marketplace.

Restart Claude Code. Do not diagnose an old process against newly installed
files. Verify that the current plugin version matches the marketplace and that
`/denubis-academic:using-bibliography` loads.

## Maintainer refresh script

On machines that carry this repository's marketplace tooling,
`~/.claude/bin/plugin-refresh` is the authoritative full-refresh command:

```bash
~/.claude/bin/plugin-refresh denubis-plugins
```

Run it from a normal terminal, not from the Claude Code process whose plugins it
will replace, then restart Claude Code. Before running it, Claude must explain
and obtain confirmation for its effects: it hard-resets the marketplace clone,
deletes that marketplace's plugin cache, removes installed registry entries,
and reinstalls every plugin from the marketplace at **user scope**. It will
discard local edits inside the marketplace clone or cache. Do not use it to
repair a project/local-scope install. Use the narrower
update/uninstall/install sequence above when a full user-scope marketplace
refresh is not intended.

## Smoke test

After restart, first test skill discovery, then the installed helper path:

```text
/denubis-academic:using-bibliography
```

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
test -f "$BIB/resolve.py"
uv run "$BIB/resolve.py" --help
```

Then, with Zotero running and config present, resolve one citekey known to exist:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
BIB="${PLUGIN_DIR}/skills/using-bibliography"
uv run "$BIB/resolve.py" --citekey <known-citekey> --no-render
```

Success means the current skill loads, the helper is found through the installed
plugin root, and the resolver positively returns the known Zotero item. A search
that merely returns nothing is not a valid smoke test.

## Prompt for a colleague's Claude

Use this as the handoff after the release has been pushed:

> Diagnose my `denubis-bib`/bibliography plugin error using the
> `denubis-academic` setup-and-migration runbook. If the installed plugin
> cannot expose its bundled copy, read the runbook from
> <https://github.com/Denubis/denubis-plugins/blob/main/plugins/denubis-academic/skills/using-bibliography/references/setup-and-migration.md>.
> Start with a read-only
> inventory of the exact error source, marketplace source/revision, installed
> plugin names and versions, stale-name references, and local Zotero/tool
> capabilities. Do not expose credentials. Show me the evidence and ask before
> uninstalling, clearing caches, or running `plugin-refresh`. Migrate to
> `denubis-academic@denubis-plugins`, restart Claude Code, and prove
> `/denubis-academic:using-bibliography` and the installed `resolve.py` path work.
