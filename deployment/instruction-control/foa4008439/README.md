# Instruction-control deployment on `foa4008439`

This directory contains the exact global Claude, global Codex, and settings candidates
consumed by the deployment. `candidate-manifest.json` binds their bytes, the changed
plugin source trees, content-digested human-source records, action-to-authority mappings,
the observed live baselines, and the parsed Codex history-retention contract.

The Codex config is not copied into this repository because it contains unrelated local
configuration and credentials. The verifier instead parses `/home/brian/.codex/config.toml`
and requires `history.persistence = "save-all"` with `history.max_bytes` absent.

This candidate does not install `denubis-project-notes`. Direct `.notes/` inspection in
the global candidate replaces the retiring advisor without depending on unfinished
cross-vendor search. Install the project-notes skill only in a later candidate that can
verify provider-qualified exact resolution. PostgreSQL receipt correlation is not a
prerequisite for that resolver.

The manifest state is `source-candidate`. It does not authorise a commit, publication, or
live write. Plugin installation must wait until the reviewed source commit is available
to the installed `denubis-plugins` marketplace.

## Preconditions

From the repository root:

```fish
uv run python deployment/instruction-control/verify_candidate.py source deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
uv run python deployment/instruction-control/verify_candidate.py baseline deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
scripts/pre-commit
```

Both verifier records must report `"ok": true`. The repository test runner must pass.
Any baseline change invalidates the candidate; inspect and rebuild it rather than forcing
the deployment.

The manifest's parsed settings contract rejects `CLAUDE_CODE_SUBAGENT_MODEL` because it
overrides per-invocation and agent-frontmatter model selection, and rejects
`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` while crash recovery depends on host PID visibility.
These effects were rechecked against Anthropic's [environment-variable reference](https://code.claude.com/docs/en/env-vars)
and [model-configuration reference](https://code.claude.com/docs/en/model-config) on
2026-08-12. The verifier, not this prose, enforces the candidate boundary.

The source change must then be reviewed, committed, pushed, and present in the local
marketplace checkout. Those transitions require their own explicit human authority.

## Project integration boundary

The project `CLAUDE.md` is repository-owned, not a live user-level deployment file. After
the reviewed source change is integrated into the main checkout, verify that consumer:

```fish
uv run python deployment/instruction-control/verify_candidate.py project deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
```

This check must report `"ok": true` before changing the global file, settings, plugin
registry, or cache. Its present red result is the deliberate integration block, not
evidence that the source candidate is malformed. The project baseline records the
pre-integration file, so do not rerun the all-baselines check after successful project
integration. Do not start an intervening Claude session between the pre-integration
baseline check and the live transition.

## Live transition

Before changing state, create one backup directory containing:

- `/home/brian/.claude/CLAUDE.md`;
- `/home/brian/.claude/settings.json`;
- `/home/brian/.codex/AGENTS.md`;
- `/home/brian/.claude/plugins/installed_plugins.json`; and
- the currently selected cache trees for every plugin named under `plugin_releases`.

Then, without starting an intervening Claude session:

1. Run `claude plugin marketplace update denubis-plugins` and verify that its checkout
   contains the reviewed commit.
2. Update the seven existing changed plugins named in the manifest.
3. Atomically replace the live global `CLAUDE.md`, global Codex `AGENTS.md`, and Claude
   `settings.json` with the three bound candidates, preserving the live files' modes.
4. Uninstall the three retired plugins at user scope with their persistent data kept.
5. Reapply the bound settings candidate after the plugin CLI finishes, because install
   and uninstall commands may rewrite that file.
6. Run the deployed verifier:

```fish
uv run python deployment/instruction-control/verify_candidate.py deployed deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
```

The deployed verifier recomputes the global/project/settings digests, selected registry
versions, and installed cache-tree digests. A green source check is not a substitute.

## Rollback

On any failed transition or post-deployment check, restore the three backed-up live files
atomically and restore any removed cache trees before starting another Claude session.
Rerun the baseline verifier against a rollback manifest produced from those restored
files. Do not claim rollback from a settings-only restoration when the plugin registry or
selected cache path still differs.
