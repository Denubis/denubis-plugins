# denubis-academic

Academic writing, manuscript review, and Zotero-backed bibliography workflows
for Claude Code.

## Install

Add or update the `denubis-plugins` marketplace, then install:

```text
/plugin install denubis-academic@denubis-plugins
```

Restart Claude Code after installation. For a retired-name error, stale cache,
or a colleague-machine migration, use the
[setup and migration runbook](skills/using-bibliography/references/setup-and-migration.md).

## Skills

| Skill | Invocation | Purpose |
|---|---|---|
| `academic-writing` | `/denubis-academic:academic-writing` | Draft and revise academic prose after reading project register rules |
| `paper-review` | `/denubis-academic:paper-review` | Critical-friend and adversarial manuscript review |
| `using-bibliography` | `/denubis-academic:using-bibliography` | Resolve and render Zotero papers, verify quotations, manage confirmed Zotero writes, refresh bibliographies, and create source-grounded notes |

The plugin name comes from `.claude-plugin/plugin.json`; each skill name comes
from its skill directory and frontmatter. `denubis-bibliography` is retired and
`denubis-bib` is not a valid marketplace or skill identifier.

## Bibliography requirements

The bibliography skill requires Zotero, Better BibTeX, `uv`, Python 3.14+, a
configured zettelkasten root, and rendering dependencies acquired through the
bundled scripts. Pandoc is additionally required for non-PDF, non-HTML
attachments. `zotero-api-plus` is optional and required only for its documented
write and forced-refresh capabilities.

Start with the
[`using-bibliography` skill](skills/using-bibliography/SKILL.md); it routes each
operation to a bounded procedure.
